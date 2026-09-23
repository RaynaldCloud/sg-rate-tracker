"""Tests for the bank scrapers, using small sample HTML instead of live websites."""
from types import SimpleNamespace

import requests

from scrapers.dbs_scraper import DBSScraper
from scrapers.ocbc_scraper import OCBCBoardScraper
from scrapers.uob_scraper import UOBBoardScraper, UOBScraper


def fake_response(html: str):
    """parse() only reads response.text, so a simple stand-in object is enough."""
    return SimpleNamespace(text=html)


def test_dbs_reads_tiers_and_tenures():
    html = """<table>
      <tr><th>Period</th><th>$1,000 - $9,999</th><th>$10,000 - $19,999</th></tr>
      <tr><td>1 mth</td><td>0.0500</td><td>0.0500</td></tr>
      <tr><td>12 mths</td><td>1.0000</td><td>0.8000</td></tr>
    </table>"""
    rates = DBSScraper().parse(fake_response(html))

    assert len(rates) == 4
    twelve_month_small = [r for r in rates if r.tenure_months == 12 and r.min_deposit == 1000]
    assert twelve_month_small[0].rate_percent == 1.0
    assert twelve_month_small[0].max_deposit == 9999


def test_uob_promo_carries_rowspan_deposit_forward():
    html = """<table>
      <tr><th>Tenor</th><th>Deposit Amount (Fresh Funds)</th><th>Base Promotional Interest rate</th></tr>
      <tr><td>6-month</td><td rowspan="3">Minimum S$10,000</td><td>1.60% p.a.</td></tr>
      <tr><td>10-month</td><td>1.65% p.a.</td></tr>
      <tr><td>12-month</td><td>1.70% p.a.</td></tr>
      <tr><td colspan="3">This promotion is available from 23 September to 30 September 2026.</td></tr>
    </table>"""
    rates = UOBScraper().parse(fake_response(html))

    assert [r.tenure_months for r in rates] == [6, 10, 12]
    assert all(r.min_deposit == 10000 for r in rates)  # rowspan value reused
    assert all(r.is_promotional for r in rates)


def test_uob_promo_returns_empty_when_no_promotion():
    assert UOBScraper().parse(fake_response("<p>No promotion right now</p>")) == []


def test_uob_board_handles_below_tier():
    html = """<table>
      <tr><td></td></tr>
      <tr><th>Tenor (% p.a.)</th><th>Below S$50,000</th><th>S$50,000 - S$249,999</th></tr>
      <tr><td>6-month</td><td>0.30</td><td>0.30</td></tr>
    </table>"""
    rates = UOBBoardScraper().parse(fake_response(html))

    assert len(rates) == 2
    assert (rates[0].min_deposit, rates[0].max_deposit) == (None, 49999)
    assert not rates[0].is_promotional


def test_ocbc_expands_ranges_and_skips_unavailable_and_na():
    html = """<table>
      <tr><th>Tenure (months)</th><th>S$5,000 - S$20,000</th><th>&gt;S$20,000 - S$50,000</th></tr>
      <tr><td>6 - 8</td><td>0.20%</td><td>0.10%</td></tr>
      <tr><td>20</td><td>1.05%</td><td>N.A</td></tr>
      <tr><td>24 (new placements not available*)</td><td>1.45%</td><td>0.20%</td></tr>
    </table>"""
    rates = OCBCBoardScraper().parse(fake_response(html))

    # 6-8 expands to 3 tenures x 2 tiers = 6; the 20-month row has one N.A = 1; 24-month skipped
    assert len(rates) == 7
    assert sorted({r.tenure_months for r in rates}) == [6, 7, 8, 20]
    assert min(r.min_deposit for r in rates if r.min_deposit > 5000) == 20001  # ">" tier


def test_scrape_returns_empty_list_when_layout_changes(monkeypatch):
    scraper = DBSScraper()
    monkeypatch.setattr(scraper, "fetch", lambda url=None: fake_response("<html></html>"))
    assert scraper.scrape() == []


def test_scrape_returns_empty_list_when_site_is_down(monkeypatch):
    scraper = DBSScraper()

    def broken_fetch(url=None):
        raise requests.ConnectionError("site unreachable")

    monkeypatch.setattr(scraper, "fetch", broken_fetch)
    assert scraper.scrape() == []