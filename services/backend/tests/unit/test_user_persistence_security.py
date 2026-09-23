from uuid import uuid4

import pytest

from cci.db.repository import save_user


def test_save_user_requires_an_explicit_password_hash():
    with pytest.raises(TypeError):
        save_user(
            session=None,
            organization_id=uuid4(),
            email="interviewer@example.invalid",
            full_name="Synthetic Interviewer",
        )
