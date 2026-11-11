from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture
def client(database_dsn, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_dsn)
    with TestClient(app) as instance:
        yield instance


def test_health_and_plans_use_database(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "database": "ok"}
    response = client.get("/plans")
    assert response.status_code == 200
    plans = response.json()
    assert [plan["name"] for plan in plans] == ["Student", "Basic", "Duo", "Premium", "Family"]
    premium = plans[3]
    assert premium["max_profiles"] == 1 and premium["max_streams"] == 3
    assert premium["monthly_price"] == "499.00"
    assert all(set(plan) == {"plan_id", "name", "monthly_price", "max_profiles", "max_streams", "max_quality"} for plan in plans)


def test_missing_configuration_keeps_liveness_and_returns_503(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        assert client.get("/plans").status_code == 503


def test_unreachable_database_does_not_leak_connection_details(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://private_user:private_password@127.0.0.1:1/unavailable")
    with TestClient(app) as client:
        for endpoint in ("/health/ready", "/plans"):
            response = client.get(endpoint)
            assert response.status_code == 503
            assert "private_" not in response.text
            assert "postgresql" not in response.text
