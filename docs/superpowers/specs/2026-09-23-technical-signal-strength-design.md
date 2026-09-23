# Fix 11: Technical Signal Strength Design

**Status:** Chat design approved; spec submitted for review
**Scope:** CandidateX backend hardening, Fix 11 from the supplied sequential hardening brief

## Understanding and success criteria

Analyzer values such as `async = 75`, `route = 80`, `dependency = 55`, and the other fixed or rule-derived values are hand-authored heuristic strengths assigned to detected technical observations. They are not measurements of a person's skill, calibrated proficiency scores, job-performance predictions, or certifications. The value describes how strongly the analyzer rule treats the observed artifact as support for a technical signal.

Success means:

- `technical_signal_strength` is the canonical name in backend domain and API contracts;
- existing `observed_score` input and `support_score` persisted/API names remain accepted or emitted as deprecated compatibility aliases during migration;
- every newly emitted analyzer observation identifies the specific rule and its version, separately from extractor version and observation family/type;
- persisted evidence provenance and API responses expose rule ID and version;
- every current heuristic emission is documented with its detection condition, emitted strength or range, rationale, and limitation;
- backend descriptions do not imply psychometric accuracy, job-performance prediction, mastery proof, or proficiency certification;
- the heuristic values and scoring math remain unchanged.

## Current code context

`EvidenceInput` currently names the analyzer value `observed_score`; live acquisition maps it to `EvidenceRecord.support_score`, which is also the persisted database column. Acquisition already records `extractor_version` in provenance. The API returns evidence records and their provenance, so rule metadata can flow through that existing JSON provenance without a database migration.

Analyzer strength assignments are distributed across the code, documentation, deployment, infrastructure, database, and testing analyzers. The source scan found 52 `observed_score` assignment sites in analyzer modules, including fixed values and values selected or capped from detected features. Several constructors already carry `observation_type`; that field identifies evidence modality/family correlation and must not be repurposed as a heuristic rule identifier.

Existing backend wording includes descriptions that call evidence proficiency, mastery, or deep hands-on mastery. The API contract and report text must use descriptive evidence language. The existing live-service disclaimer that static observations do not prove mastery or job performance should be retained and made consistent with the canonical terminology.

## Contract and naming

Use `technical_signal_strength` as the canonical domain and API field for the 0–100 heuristic value. Continue accepting legacy `observed_score` on analyzer inputs and legacy `support_score` on persisted-record inputs. During compatibility, serialize the existing `support_score` response key alongside the canonical `technical_signal_strength` key and mark the legacy name deprecated; do not remove or reinterpret the physical database column. All aliases refer to the same unchanged numeric value.

Each new `EvidenceInput` carries:

- `signal_rule_id`: a stable, namespaced identifier for the particular detection rule;
- `signal_rule_version`: the version of that rule, initially `1.0.0`;
- `extractor_version`: the existing version of the analyzer implementation, kept separate;
- `observation_type`: the existing modality/correlation label, kept separate.

Rule ID and version are copied to top-level evidence provenance and included in API evidence responses. Historical evidence without rule metadata remains readable and is labeled `legacy_unknown`; the system must not infer a rule from its numeric value or raw text. No database migration is required because provenance is JSON-backed.

Rule IDs are stable across refactors. A behavior change to the detection predicate or the meaning of its signal strength requires a rule-version change. A code-only refactor that preserves behavior does not. Extractor version can change independently.

## Heuristic rule catalog

Add a backend-maintained catalog that covers every analyzer emission. At minimum, each entry records:

| Field | Meaning |
|---|---|
| Rule ID and version | Stable identity and current semantics version |
| Analyzer and source location | Which backend analyzer emits the rule |
| Detection condition | The syntax, configuration, test result, or operational observation that triggers it |
| Signal strength | Fixed value or complete expression/range, including feature-dependent branches and caps |
| Rationale | Why this observation is treated as technical support and why the selected heuristic strength was chosen |
| Limitations | What the observation does not establish, including alternative explanations and missing execution/context evidence |

The initial catalog must inventory all current emit sites, including fixed code-pattern weights, language-specific route and concurrency rules, dependency declarations, database/ORM and migration features, test-structure rules, infrastructure configuration rules, documentation/architecture rules, and live deployment checks. Dynamic expressions must describe their branches and bounds, not merely one sample output. The catalog is explanatory documentation, not empirical calibration; it must state that the numeric values are policy heuristics without a measured human-performance interpretation.

## Language and scope

Revise backend API descriptions, dossier/report prose, docstrings, and backend documentation to describe detected evidence and technical signal strength. Remove claims that an index reflects proficiency or that a detected pattern indicates mastery. State clearly that the outputs do not certify proficiency or predict job performance and require human interpretation in evidence context.

This task is backend-only. It adds the canonical field and provenance to backend contracts but does not edit frontend source. Frontend adoption can happen separately; compatibility aliases prevent this backend change from breaking current consumers.

## Compatibility and non-goals

- Preserve all existing signal values, rule predicates, confidence calculations, capability estimates, and scoring behavior.
- Preserve database `support_score` and existing response field during the compatibility period.
- Preserve `extractor_version` and `observation_type` as distinct concepts.
- Do not claim or introduce empirical calibration, psychometric validity, hiring accuracy, job-performance prediction, or certification.
- Do not change frontend code, recalibrate score values, or change scoring weights in Fix 11.

## Acceptance criteria

- Analyzer contracts accept canonical `technical_signal_strength` and the legacy `observed_score` alias; evidence-record contracts accept the canonical name and legacy `support_score` alias.
- API evidence serialization includes canonical strength and preserves legacy `support_score` with equivalent values.
- Every analyzer emission supplies a known `signal_rule_id` and version; every ID has exactly one catalog entry, and no catalog entry is orphaned.
- Each rule's catalog record explains detection logic, assigned value or dynamic range, rationale, and limitations.
- Acquisition persists rule ID/version in evidence provenance independently of extractor version and observation type; API responses expose them.
- Records created before Fix 11 remain readable and show `legacy_unknown` rule metadata rather than fabricated attribution.
- Backend-facing prose no longer describes heuristic values as measured proficiency, certification, job-performance prediction, or proof of mastery.
- A regression check confirms unchanged rule outputs and downstream scoring values for existing analyzer fixtures.
- No database migration or frontend edit is needed.
