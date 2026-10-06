import pytest

from forge.persistence.db import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    d.migrate()
    yield d
    d.close()
