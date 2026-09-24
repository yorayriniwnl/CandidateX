"""Repository management for empirical calibration cases (Fix 21).

Enforces:
1. Strict consent requirement for all real-world candidate data.
2. Anonymization validation: reject un-anonymized identifiers or emails.
3. Explicit synthetic labeling: synthetic cases must have `is_synthetic=True`.
"""

import json
from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from cci.calibration.contracts import CalibrationCase
from cci.db.models.calibration import CalibrationCaseModel
from cci.domain.enums import CanonicalRole


class CalibrationCaseRepository:
    """Repository storing and querying calibration cases in memory and/or database."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._cases: dict[UUID, CalibrationCase] = {}

    def register_case(self, case: CalibrationCase) -> CalibrationCase:
        """Registers a new evaluation case with strict consent and anonymization enforcement.

        Invariants:
        - Real candidate data (`is_synthetic=False`) strictly requires `consent_granted=True`.
        - Subject identifier must be an anonymized token.
        """
        # 1. Invariant: real data requires consent
        if not case.is_synthetic and not case.consent_provenance.consent_granted:
            raise ValueError(
                f"Consent verification failed for case {case.case_id}: "
                f"real candidate evaluation cases require explicit consent_granted=True."
            )

        # 2. Invariant: anonymization
        if "@" in case.anonymized_subject_id:
            raise ValueError(
                f"Anonymization failure for case {case.case_id}: "
                f"subject ID must be strictly anonymized without raw emails or PII."
            )

        # 3. Store in memory
        self._cases[case.case_id] = case

        # 4. Persist to DB if session provided
        if self._session is not None:
            db_model = CalibrationCaseModel(
                id=case.case_id,
                anonymized_subject_id=case.anonymized_subject_id,
                role=case.role.value,
                is_synthetic=case.is_synthetic,
                consent_granted=case.consent_provenance.consent_granted,
                consent_version=case.consent_provenance.consent_version,
                data_source=case.consent_provenance.data_source,
                collected_at=case.consent_provenance.collected_at,
                payload_json=case.model_dump_json(),
            )
            self._session.merge(db_model)
            self._session.flush()

        return case

    def get_case(self, case_id: UUID) -> CalibrationCase | None:
        """Retrieves a single case by ID."""
        if case_id in self._cases:
            return self._cases[case_id]

        if self._session is not None:
            model = self._session.get(CalibrationCaseModel, case_id)
            if model is not None:
                data = json.loads(model.payload_json)
                case = CalibrationCase.model_validate(data)
                self._cases[case_id] = case
                return case

        return None

    def list_cases(
        self,
        role: CanonicalRole | None = None,
        is_synthetic: bool | None = None,
    ) -> list[CalibrationCase]:
        """Lists cases matching criteria."""
        results: list[CalibrationCase] = []

        if self._session is not None and not self._cases:
            query = self._session.query(CalibrationCaseModel)
            if role is not None:
                query = query.filter(CalibrationCaseModel.role == role.value)
            if is_synthetic is not None:
                query = query.filter(CalibrationCaseModel.is_synthetic == is_synthetic)
            for m in query.all():
                c = CalibrationCase.model_validate(json.loads(m.payload_json))
                self._cases[c.case_id] = c
                results.append(c)
            return results

        for case in self._cases.values():
            if role is not None and case.role != role:
                continue
            if is_synthetic is not None and case.is_synthetic != is_synthetic:
                continue
            results.append(case)

        return results

    def count(self, is_synthetic: bool | None = None) -> int:
        """Counts total registered cases."""
        return len(self.list_cases(is_synthetic=is_synthetic))

    def clear(self) -> None:
        """Clears in-memory storage (primarily for test resets)."""
        self._cases.clear()
