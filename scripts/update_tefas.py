import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import tefas

ROOT = Path(__file__).resolve().parents[1]
FUNDS_FILE = ROOT / "funds.txt"
DOCS_DIR = ROOT / "docs"
JSON_FILE = DOCS_DIR / "tefas_bulk.json"

def load_codes():
    codes = []
    for line in FUNDS_FILE.read_text().splitlines():
        code = line.strip().upper()
        if code:
            codes.append(code)
    return codes

def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    codes = load_codes()

    df = tefas.get_data(*codes, verbose=False)

    records = []

    for code in codes:
        if code not in df.columns:
            continue

        s = df[code].dropna()
        if len(s) < 2:
            continue

        last_price = float(s.iloc[-1])
        prev_price = float(s.iloc[-2])

        daily_return = (last_price / prev_price) - 1

        records.append({
            "code": code,
            "price": last_price,
            "daily_return": daily_return,
            "date": str(s.index[-1])
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": records
    }

    JSON_FILE.write_text(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()
