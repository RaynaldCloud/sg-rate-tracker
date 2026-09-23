"""Base class that every bank scraper inherits from."""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class Rate:
    """One interest rate offered by a bank."""
    bank: str
    product: str                     
    rate_percent: float
    tenure_months: Optional[int] = None
    min_deposit: Optional[float] = None
    scraped_at: datetime = field(default_factory=datetime.now)


class BaseScraper(ABC):
    """Handles fetching politely; each bank subclass handles parsing."""

    bank_name: str = ""
    url: str = ""

    HEADERS = {
        "User-Agent": (
            "sg-rate-tracker/0.1 (personal project; "
            "github.com/RaynaldCloud/sg-rate-tracker)"
        )
    }
    REQUEST_DELAY_SECONDS = 2
    TIMEOUT_SECONDS = 15

    def fetch(self, url: Optional[str] = None) -> requests.Response:
        """Download a page, waiting first so we never delay the server."""
        time.sleep(self.REQUEST_DELAY_SECONDS)
        response = requests.get(
            url or self.url, headers=self.HEADERS, timeout=self.TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    @abstractmethod
    def parse(self, response: requests.Response) -> List[Rate]:
        """Extract rates from the page. Every bank must implement this."""

    def scrape(self) -> List[Rate]:
        """Fetch and parse, returning an empty list if anything fails."""
        try:
            rates = self.parse(self.fetch())
            logger.info("%s: scraped %d rates", self.bank_name, len(rates))
            return rates
        except requests.RequestException as error:
            logger.error("%s: request failed: %s", self.bank_name, error)
        except (ValueError, AttributeError) as error:
            logger.error("%s: page layout may have changed: %s", self.bank_name, error)
        return []
