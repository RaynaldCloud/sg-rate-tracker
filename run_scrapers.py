"""Run every bank scraper and save the results to the database."""
import logging
import sys
from typing import List

from database.db import init_db, save_rates
from scrapers.base_scraper import BaseScraper
from scrapers.dbs_scraper import DBSScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_scrapers")

# Add new banks here as their scrapers are written
SCRAPERS: List[BaseScraper] = [
    DBSScraper(),
]


def main() -> int:
    init_db()
    total_saved = 0
    failed = []

    for scraper in SCRAPERS:
        rates = scraper.scrape()
        if rates:
            total_saved += save_rates(rates)
        else:
            failed.append(scraper.bank_name)

    succeeded = len(SCRAPERS) - len(failed)
    logger.info("Saved %d rates from %d of %d banks", total_saved, succeeded, len(SCRAPERS))
    if failed:
        logger.warning("No rates collected from: %s", ", ".join(failed))

    return 0 if total_saved else 1  


if __name__ == "__main__":
    sys.exit(main())