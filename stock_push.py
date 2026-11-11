#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сток Blox Fruits -> пуш на телефон через ntfy.sh.
Запускается на GitHub Actions по расписанию: ПК может быть выключен.

Зависимостей нет, только стандартная библиотека Python 3.
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.header import Header

STOCK_URL = os.environ.get(
    "STOCK_URL",
    "https://bloxvalues.net/wp-content/uploads/blox-fruits-calculator/stock.json",
)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
TZ_OFFSET_H = float(os.environ.get("TZ_OFFSET", "3"))
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
UA = "Mozilla/5.0 (compatible; BloxFruitStockPush/1.0)"

RU = {
    "Rocket": "Ракета", "Spin": "Спин", "Blade": "Клинок", "Spring": "Пружина",
    "Bomb": "Бомба", "Smoke": "Дым", "Spike": "Шип", "Flame": "Пламя",
    "Ice": "Лёд", "Sand": "Песок", "Dark": "Тьма", "Eagle": "Орёл",
    "Diamond": "Алмаз", "Light": "Свет", "Rubber": "Резина", "Ghost": "Призрак",
    "Magma": "Магма", "Quake": "Землетрясение", "Buddha": "Будда", "Love": "Любовь",
    "Creation": "Создание", "Spider": "Паук", "Sound": "Звук", "Phoenix": "Феникс",
    "Portal": "Портал", "Lightning": "Гром", "Pain": "Боль", "Blizzard": "Буря",
    "Gravity": "Гравитация", "Mammoth": "Мамонт", "T-Rex": "Тирекс", "Dough": "Тесто",
    "Shadow": "Тень", "Venom": "Яд", "Gas": "Газ", "Spirit": "Дух",
    "Tiger": "Тигр", "Yeti": "Йети", "Magnet": "Магнит", "Kitsune": "Кицунэ",
    "Control": "Контроль", "Dragon": "Дракон",
}


def log(*a):
    print(*a, flush=True)


def local_str(ts):
    return datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=TZ_OFFSET_H))).strftime("%H:%M")


def fmt(n):
    try:
        return "{:,}".format(int(n)).replace(",", " ")
    except Exception:
        return str(n)


def ascii_header(value):
    try:
        value.encode("ascii")
        return value
    except UnicodeEncodeError:
        return Header(value, "utf-8").encode()


def fetch_raw(url, timeout=25):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_stock():
    """Возвращает (сырой текст, разобранные списки). Пробует несколько раз."""
    last_err = None
    for attempt in range(1, 4):
        try:
            url = "%s?v=%d" % (STOCK_URL, int(time.time()))
            raw = fetch_raw(url)
            data = json.loads(raw)
            if not isinstance(data, list) or not data:
                raise ValueError("пустой ответ")
            regular, mirage = [], []
            for item in data:
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                kind = str(item.get("type", "Regular")).lower()
                entry = (item["name"], item.get("price", 0))
                (mirage if "mirage" in kind else regular).append(entry)
            if not regular and not mirage:
                raise ValueError("нет фруктов в ответе")
            return raw, regular, mirage
        except Exception as exc:
            last_err = exc
            log("попытка %d не удалась: %s" % (attempt, exc))
            time.sleep(15)
    raise RuntimeError("не смог получить сток: %s" % last_err)


def build_message(regular, mirage):
    now = time.time()
    lines = ["🟢 Обычный дилер:"]
    for name, price in regular:
        lines.append("• %s (%s) — %s Beli" % (RU.get(name, name), name, fmt(price)))
    if mirage:
        lines.append("")
        lines.append("🌀 Мираж:")
        for name, price in mirage:
            lines.append("• %s (%s) — %s Beli" % (RU.get(name, name), name, fmt(price)))
    lines.append("")
    lines.append("Сток обновлён в %s (UTC+%g)." % (local_str(now), TZ_OFFSET_H))
    return "\n".join(lines)


def push(text, title):
    if not NTFY_TOPIC:
        raise RuntimeError("NTFY_TOPIC не задан")
    req = urllib.request.Request(
        NTFY_SERVER + "/" + NTFY_TOPIC,
        data=text.encode("utf-8"),
        headers={
            "Title": ascii_header(title),
            "Priority": "high",
            "Tags": "grapes",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        log("ntfy ответил: %s" % resp.status)
        return 200 <= resp.status < 300


def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    force = os.environ.get("FORCE", "").lower() in ("1", "true", "yes")
    raw, regular, mirage = fetch_stock()

    digest = hashlib.sha256(
        json.dumps({"r": regular, "m": mirage}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    state = load_state()
    if not force and state.get("hash") == digest:
        log("сток не изменился с прошлого раза — не спамлю")
        return 0

    text = build_message(regular, mirage)
    push(text, "Сток Blox Fruits")
    log(text)

    save_state({"hash": digest, "updated": int(time.time())})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log("ОШИБКА: %s" % exc)
        sys.exit(1)
