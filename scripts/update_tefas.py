import json
import time
from pathlib import Path
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


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


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=tr-TR")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def tr_to_float(text):
    text = (
        str(text)
        .strip()
        .replace("%", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )
    return float(text)


def extract_value_by_label(driver, label_text):
    xpath = (
        f"//*[contains(normalize-space(.), '{label_text}')]"
        "/following::*[self::span or self::div or self::td][1]"
    )
    elements = driver.find_elements(By.XPATH, xpath)
    for el in elements:
        txt = el.text.strip()
        if txt:
            return txt
    return None


def scrape_fund(driver, code):
    url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={code}"
    driver.get(url)
    time.sleep(5)

    page = driver.page_source

    if "Request Rejected" in page or "TSPD" in page or "failureConfig" in page:
        return {
            "code": code,
            "price": None,
            "daily_return": None,
            "date": None,
            "status": "blocked"
        }

    price_text = extract_value_by_label(driver, "Son Fiyat")
    daily_text = extract_value_by_label(driver, "Günlük Getiri")

    if not price_text or not daily_text:
        return {
            "code": code,
            "price": None,
            "daily_return": None,
            "date": None,
            "status": "not_found"
        }

    try:
        price = tr_to_float(price_text)
        daily_return = tr_to_float(daily_text) / 100.0
    except Exception:
        return {
            "code": code,
            "price": None,
            "daily_return": None,
            "date": None,
            "status": "parse_error"
        }

    return {
        "code": code,
        "price": price,
        "daily_return": daily_return,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": "ok"
    }


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_codes()

    driver = build_driver()
    items = []

    try:
      for code in codes:
          items.append(scrape_fund(driver, code))
    finally:
      driver.quit()

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
