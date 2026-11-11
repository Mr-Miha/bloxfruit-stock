#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Забирает сток Blox Fruits и кладёт его в data.json для приложения.
Запускается на GitHub Actions каждые 10 минут.
"""

import json
import os
import sys
import time
import urllib.request

SRC = os.environ.get(
    "STOCK_URL",
    "https://bloxvalues.net/wp-content/uploads/blox-fruits-calculator/stock.json",
)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
UA = "Mozilla/5.0 (compatible; BloxFruitStockApp/1.0)"


def fetch(url, timeout=25):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def main():
    last_err = None
    for attempt in range(1, 4):
        try:
            raw = fetch("%s?v=%d" % (SRC, int(time.time())))
            data = json.loads(raw)
            if not isinstance(data, list) or not data:
                raise ValueError("пустой ответ")

            regular, mirage = [], []
            for item in data:
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                kind = str(item.get("type", "Regular")).lower()
                entry = {"name": item["name"], "price": int(item.get("price") or 0)}
                (mirage if "mirage" in kind else regular).append(entry)

            if not regular and not mirage:
                raise ValueError("нет фруктов в ответе")

            payload = {"updated": int(time.time()), "regular": regular, "mirage": mirage}
            new_text = json.dumps(payload, ensure_ascii=False, indent=2)

            old_text = ""
            if os.path.exists(OUT):
                with open(OUT, "r", encoding="utf-8") as f:
                    old_text = f.read()

            if old_text.strip() == new_text.strip():
                print("данные не изменились")
                return 0

            with open(OUT, "w", encoding="utf-8") as f:
                f.write(new_text + "\n")

            print("обновлено: %d обычных, %d мираж" % (len(regular), len(mirage)))
            return 0
        except Exception as exc:
            last_err = exc
            print("попытка %d не удалась: %s" % (attempt, exc))
            time.sleep(10)

    print("ОШИБКА: %s" % last_err)
    return 1


if __name__ == "__main__":
    sys.exit(main())
