"""Запуск: python -m pricemon --pages 3 --out prices.xlsx"""
import argparse
import asyncio
import logging
import os
import sys

import httpx

from pricemon import report, storage
from pricemon.fetch import crawl
from pricemon.site import BOOKS_TO_SCRAPE


def notify_telegram(text: str) -> None:
    token, chat = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_CHAT_ID")
    if token and chat:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat, "text": text}, timeout=20)


def main() -> int:
    parser = argparse.ArgumentParser(prog="pricemon", description="Сбор цен из каталога и отчёт об изменениях")
    parser.add_argument("--pages", type=int, default=3, help="сколько страниц каталога обойти (по умолчанию 3)")
    parser.add_argument("--db", default="prices.db", help="файл базы с историей цен")
    parser.add_argument("--out", default="prices.xlsx", help="куда сохранить отчёт Excel")
    parser.add_argument("--delay", type=float, default=0.5, help="пауза между запросами, секунды")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        products = asyncio.run(crawl(BOOKS_TO_SCRAPE, args.pages, args.delay))
    except (RuntimeError, httpx.HTTPError) as error:
        print(f"Сбор не удался: {error}", file=sys.stderr)
        return 1
    if not products:
        print("Товары не найдены: возможно, на сайте изменилась вёрстка.", file=sys.stderr)
        return 1

    conn = storage.connect(args.db)
    run_id = storage.save_run(conn, products)
    found = storage.changes(conn, run_id)
    report.export_xlsx(conn, run_id, found, args.out)
    text = report.summary(found)
    print(f"Собрано товаров: {len(products)}. Отчёт: {args.out}\n{text}")
    if found:
        notify_telegram(f"{BOOKS_TO_SCRAPE.name}\n{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
