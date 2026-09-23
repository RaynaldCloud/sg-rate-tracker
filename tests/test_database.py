"""Tests for the SQLite storage layer, using a temporary database."""
from datetime import datetime

import pytest

from database import db
from scrapers.base_scraper import Rate


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the database at a throwaway file so real data is never touched."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def make_rate(rate, day, promo=False):
    return Rate("DBS", "Fixed Deposit", rate, tenure_months=12, min_deposit=1000,
                is_promotional=promo, scraped_at=datetime(2026, 9, day))


def test_latest_rates_returns_only_the_newest(temp_db):
    db.save_rates([make_rate(1.0, day=1), make_rate(1.2, day=2)])
    latest = db.get_latest_rates()

    assert len(latest) == 1
    assert latest[0]["rate_percent"] == 1.2


def test_promo_and_board_rates_are_kept_separate(temp_db):
    db.save_rates([make_rate(1.0, day=1), make_rate(1.7, day=1, promo=True)])
    assert len(db.get_latest_rates()) == 2


def test_history_is_ordered_oldest_first(temp_db):
    db.save_rates([make_rate(1.2, day=2), make_rate(1.0, day=1)])
    history = db.get_rate_history("DBS", "Fixed Deposit", tenure_months=12, min_deposit=1000)

    assert [h["rate_percent"] for h in history] == [1.0, 1.2]