import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from tefas import Crawler


ROOT = Path(__file__).resolve().parents[1]
FUNDS_FILE = ROOT / "funds.txt"
DOCS_DIR = ROOT / "docs"
JSON_FILE = DOCS_DIR / "tefas_bulk.json"


def load_codes():
    codes = []
    for line in FUNDS_FILE.read_text(encoding="utf-8").splitlines():
        code = line.strip().upper()
        if code and not code.startswith("#"):
            codes.append(code)
    return codes


def to_float(v):
    if v is None:
        return None
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    codes = load_codes()
    crawler = Crawler()

    end = datetime.now()
    start = end - timedelta(days=10)

    items = []

    for code in codes:
        try:
            rows = crawler.fetch(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                name=code,
                columns=["code", "date", "price"]
            )

            if not rows or len(rows) < 1:
                items.append({
                    "code": code,
                    "price": None,
                    "daily_return": None,
                    "date": None,
                    "status": "no_data"
                })
                continue

            rows = sorted(rows, key=lambda x: str(x.get("date", "")))
            last_row = rows[-1]
            last_price = to_float(last_row.get("price"))

            prev_price = None
            if len(rows) >= 2:
                prev_price = to_float(rows[-2].get("price"))

            daily_return = None
            if last_price is not None and prev_price not in (None, 0):
                daily_return = (last_price / prev_price) - 1

            items.append({
                "code": code,
                "price": last_price,
                "daily_return": daily_return,
                "date": str(last_row.get("date")),
                "status": "ok" if last_price is not None else "parse_error"
            })

        except Exception as e:
            items.append({
                "code": code,
                "price": None,
                "daily_return": None,
                "date": None,
                "status": f"error: {e}"
            })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items
    }

    JSON_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
