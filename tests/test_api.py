"""Tests for the Flask API, using Flask's built-in test client."""
import pytest

from api.app import create_app
from database import db
from scrapers.base_scraper import Rate


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_rates_can_be_filtered_by_product(client):
    db.save_rates([
        Rate("DBS", "Fixed Deposit", 1.0, tenure_months=12),
        Rate("DBS", "Savings", 0.05),
    ])
    data = client.get("/api/rates?product=Savings").get_json()

    assert data["count"] == 1
    assert data["rates"][0]["product"] == "Savings"


def test_history_requires_bank_and_product(client):
    response = client.get("/api/rates/history")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found"}