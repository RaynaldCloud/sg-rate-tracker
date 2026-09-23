"""Scrapers for UOB Singapore dollar fixed deposit rates (promotional and board)."""
import logging
import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, Rate

logger = logging.getLogger(__name__)


class UOBScraper(BaseScraper):
    """Scraper for UOB's short-term promotional fixed deposit rates."""
    bank_name = "UOB"
    url = "https://www.uob.com.sg/personal/save/fixed-deposits/singapore-dollar-fixed-deposit.page"

    def parse(self, response: requests.Response) -> List[Rate]:
        soup = BeautifulSoup(response.text, "html.parser")
        table = self._find_promo_table(soup)
        if table is None:
            logger.info("%s: no promotional rates listed right now", self.bank_name)
            return []

        rates = []
        min_deposit = None  # the deposit cell spans several rows, so carry it forward

        for row in table.find_all("tr")[1:]:  # skip the header row
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if not cells:
                continue

            tenure = self._parse_tenure(cells[0])
            if tenure is None:
                continue  # skips non-rate rows, like the notes at the bottom

            for text in cells[1:]:
                amount = self._parse_amount(text)
                if amount is not None:
                    min_deposit = amount

            rate = self._parse_rate(cells[-1])
            if rate is None:
                continue

            rates.append(Rate(
                bank=self.bank_name,
                product="Fixed Deposit",
                rate_percent=rate,
                tenure_months=tenure,
                min_deposit=min_deposit,
                is_promotional=True,
            ))

        if not rates:
            raise ValueError("Found the promotion table but could not read any rates")
        return rates

    @staticmethod
    def _find_promo_table(soup: BeautifulSoup):
        """Find the table whose header mentions both 'tenor' and 'interest'."""
        for table in soup.find_all("table"):
            header = table.find("tr")
            if header:
                text = header.get_text(" ", strip=True).lower()
                if "tenor" in text and "interest" in text:
                    return table
        return None

    @staticmethod
    def _parse_tenure(text: str) -> Optional[int]:
        """Turn '6-month' into 6."""
        match = re.search(r"(\d+)\s*-?\s*month", text.lower())
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_amount(text: str) -> Optional[float]:
        """Turn 'Minimum S$10,000' into 10000.0."""
        match = re.search(r"S\$\s*([\d,]+)", text)
        return float(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _parse_rate(text: str) -> Optional[float]:
        """Turn '1.60% p.a.' into 1.6."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        return float(match.group(1)) if match else None


class UOBBoardScraper(BaseScraper):
    """Scraper for UOB's standard (board) SGD fixed deposit rates."""
    bank_name = "UOB"
    url = "https://www.uob.com.sg/personal/online-rates/singapore-dollar-time-fixed-deposit-rates.page"

    def parse(self, response: requests.Response) -> List[Rate]:
        soup = BeautifulSoup(response.text, "html.parser")
        rows, header_index = self._find_board_rows(soup)

        # Header row: "Tenor (% p.a.)", "Below S$50,000", "S$50,000 - S$249,999", ...
        header_cells = rows[header_index].find_all(["th", "td"])
        tiers = [self._parse_tier(c.get_text(" ", strip=True)) for c in header_cells[1:]]

        rates = []
        for row in rows[header_index + 1:]:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            tenure = UOBScraper._parse_tenure(cells[0].get_text(" ", strip=True))
            if tenure is None:
                continue
            for (min_dep, max_dep), cell in zip(tiers, cells[1:]):
                try:
                    rate = float(cell.get_text(strip=True))
                except ValueError:
                    continue
                rates.append(Rate(
                    bank=self.bank_name,
                    product="Fixed Deposit",
                    rate_percent=rate,
                    tenure_months=tenure,
                    min_deposit=min_dep,
                    max_deposit=max_dep,
                    is_promotional=False,
                ))

        if not rates:
            raise ValueError("Found the board rates table but could not read any rates")
        return rates

    @staticmethod
    def _find_board_rows(soup: BeautifulSoup):
        """Find the board rates table and the index of its header row.
        The header mentions 'tenor' and deposit amounts in S$, but not 'promotional'."""
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for index, row in enumerate(rows):
                text = row.get_text(" ", strip=True).lower()
                if "tenor" in text and "s$" in text and "promotional" not in text:
                    return rows, index
        raise ValueError("Could not find the board rates table")

    @staticmethod
    def _parse_tier(text: str):
        """'Below S$50,000' -> (None, 49999.0); 'S$50,000 - S$249,999' -> (50000.0, 249999.0)."""
        numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)]
        if not numbers:
            return None, None
        if "below" in text.lower():
            return None, numbers[0] - 1
        return numbers[0], (numbers[1] if len(numbers) > 1 else None)