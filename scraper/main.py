import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEEN_BILLS_FILE = PROJECT_ROOT / "seen_bills.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape import fetch_bills
from pdf_extractor import extract
from summarizer import summarize
from notifier import send


def load_seen_bills() -> set:
    if not SEEN_BILLS_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_BILLS_FILE.read_text())
        return set(data.get("seen", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def save_seen_bills(seen: set) -> None:
    SEEN_BILLS_FILE.write_text(json.dumps({"seen": sorted(seen)}, indent=2))


def process_bill(bill: dict) -> bool:
    log.info("Processing: %s", bill["title"])
    try:
        extracted = extract(bill["url"])
    except Exception as e:
        log.error("PDF extraction failed for '%s': %s", bill["title"], e)
        return False
    try:
        summary = summarize(extracted)
    except Exception as e:
        log.error("Summarization failed for '%s': %s", bill["title"], e)
        return False
    try:
        send(summary, bill["url"])
    except Exception as e:
        log.error("Email sending failed for '%s': %s", bill["title"], e)
        return False
    log.info("Done: %s", bill["title"])
    return True


def main() -> None:
    seen = load_seen_bills()

    try:
        bills = fetch_bills()
    except Exception as e:
        log.error("Failed to fetch bills listing: %s", e)
        sys.exit(1)

    new_bills = [b for b in bills if b["id"] not in seen]

    if not new_bills:
        log.info("No new bills found.")
        return

    log.info("%d new bill(s) to process", len(new_bills))

    processed = []
    for bill in new_bills:
        if process_bill(bill):
            processed.append(bill["id"])

    if processed:
        seen.update(processed)
        save_seen_bills(seen)
        log.info("%d/%d bill(s) processed successfully", len(processed), len(new_bills))
    else:
        log.warning("No bills processed. seen_bills.json remains unchanged")


if __name__ == "__main__":
    main()