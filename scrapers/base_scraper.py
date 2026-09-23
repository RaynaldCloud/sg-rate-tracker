"""Base class that every bank scraper inherits from."""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

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
    max_deposit: Optional[float] = None   
    is_promotional: bool = False          
    scraped_at: datetime = field(default_factory=datetime.now)


class BaseScraper(ABC):
    """Handles fetching politely; each bank subclass handles parsing."""

    bank_name: str = ""
    url: str = ""

    HEADERS = {
        "User-Agent": (
            "sg-rate-tracker/0.1 (personal portfolio project; "
            "github.com/RaynaldCloud/sg-rate-tracker)"
        )
    }
    REQUEST_DELAY_SECONDS = 2
    TIMEOUT_SECONDS = 15

    def __init__(self) -> None:
        self._robots_cache: Dict[str, RobotFileParser] = {}

    def is_allowed(self, url: str) -> bool:
        """Check the site's robots.txt to see if we may scrape this page."""
        parts = urlparse(url)
        site = f"{parts.scheme}://{parts.netloc}"
        if site not in self._robots_cache:
            parser = RobotFileParser()
            response = requests.get(
                f"{site}/robots.txt", headers=self.HEADERS, timeout=self.TIMEOUT_SECONDS
            )
            if response.status_code == 404:
                parser.parse([])  # no robots.txt means no restrictions
            else:
                response.raise_for_status()
                parser.parse(response.text.splitlines())
            self._robots_cache[site] = parser
        return self._robots_cache[site].can_fetch(self.HEADERS["User-Agent"], url)

    def fetch(self, url: Optional[str] = None) -> requests.Response:
        """Download a page, only if robots.txt allows it, waiting first."""
        url = url or self.url
        if not self.is_allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        time.sleep(self.REQUEST_DELAY_SECONDS)
        response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT_SECONDS)
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
        except PermissionError as error:
            logger.warning("%s: skipped: %s", self.bank_name, error)
        except requests.RequestException as error:
            logger.error("%s: request failed: %s", self.bank_name, error)
        except (ValueError, AttributeError) as error:
            logger.error("%s: page layout may have changed: %s", self.bank_name, error)
        return []