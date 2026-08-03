"""Fixtures pytest partagees.

`db_session` utilise la vraie base PostgreSQL locale (lighting_decision_db) mais enveloppe
chaque test dans une transaction annulee (rollback) a la fin : aucune donnee de test n'est
jamais conservee en base.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.database import models  # noqa: F401  (peuple Base.metadata)
from app.main import app

settings = get_settings()
engine = create_engine(settings.database_url, future=True)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
