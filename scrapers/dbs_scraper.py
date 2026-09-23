"""Scraper for DBS Singapore dollar fixed deposit board rates."""
import re
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, Rate


class DBSScraper(BaseScraper):
    bank_name = "DBS"
    url = "https://www.dbs.com.sg/personal/rates-online/fixed-deposit-rate-singapore-dollar.page"

    def parse(self, response: requests.Response) -> List[Rate]:
        soup = BeautifulSoup(response.text, "html.parser")
        rows = self._find_rates_table(soup).find_all("tr")

        # Header row: "Period", "$1,000 - $9,999", "$10,000 - $19,999", ...
        header_cells = rows[0].find_all(["th", "td"])
        tiers = [self._parse_tier(c.get_text(" ", strip=True)) for c in header_cells[1:]]

        rates = []
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            tenure = self._parse_tenure(cells[0].get_text(" ", strip=True))
            if tenure is None:
                continue
            for (min_dep, max_dep), cell in zip(tiers, cells[1:]):
                try:
                    rate = float(cell.get_text(strip=True))
                except ValueError:
                    continue  # skip blank or non-numeric cells
                rates.append(Rate(
                    bank=self.bank_name,
                    product="Fixed Deposit",
                    rate_percent=rate,
                    tenure_months=tenure,
                    min_deposit=min_dep,
                    max_deposit=max_dep,
                ))

        if not rates:
            raise ValueError("Found the rates table but could not read any rates")
        return rates

    @staticmethod
    def _find_rates_table(soup: BeautifulSoup):
        """Find the table whose first row starts with 'Period'."""
        for table in soup.find_all("table"):
            first_row = table.find("tr")
            if first_row and first_row.get_text(" ", strip=True).lower().startswith("period"):
                return table
        raise ValueError("Could not find the fixed deposit rates table")

    @staticmethod
    def _parse_tier(text: str) -> Tuple[Optional[float], Optional[float]]:
        """Turn '$1,000 - $9,999' into (1000.0, 9999.0)."""
        numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)]
        min_dep = numbers[0] if numbers else None
        max_dep = numbers[1] if len(numbers) > 1 else None
        return min_dep, max_dep

    @staticmethod
    def _parse_tenure(text: str) -> Optional[int]:
        """Turn '12 mths' into 12, or None if the row isn't a tenure."""
        match = re.search(r"(\d+)\s*mth", text.lower())
        return int(match.group(1)) if match else None