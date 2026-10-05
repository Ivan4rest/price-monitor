"""Загрузка страниц: повторы при сбоях и пауза между запросами, чтобы не нагружать сайт."""
import asyncio
import logging

import httpx

from pricemon.parse import Product, parse_catalogue
from pricemon.site import Site

log = logging.getLogger("pricemon")
HEADERS = {"User-Agent": "pricemon-demo/1.0 (+https://github.com/Ivan4rest/price-monitor)"}
RETRY_STATUSES = {429, 500, 502, 503, 504}


async def get(client: httpx.AsyncClient, url: str, attempts: int = 4) -> str:
    for attempt in range(1, attempts + 1):
        try:
            response = await client.get(url)
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()
                return response.text
            problem = f"HTTP {response.status_code}"
        except httpx.TransportError as error:
            problem = type(error).__name__
        if attempt == attempts:
            raise RuntimeError(f"{url}: не удалось загрузить после {attempts} попыток ({problem})")
        delay = 2 ** attempt
        log.warning("%s: %s, повтор через %s с", url, problem, delay)
        await asyncio.sleep(delay)


async def crawl(site: Site, max_pages: int, delay: float = 0.5, client: httpx.AsyncClient | None = None) -> list[Product]:
    """Проходит каталог по ссылкам «следующая страница», но не больше max_pages страниц."""
    own_client = client is None
    client = client or httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True)
    products, url = [], site.start_url
    try:
        for page in range(1, max_pages + 1):
            found, next_url = parse_catalogue(await get(client, url), url, site)
            log.info("Страница %s: %s товаров", page, len(found))
            products += found
            if not next_url:
                break
            url = next_url
            await asyncio.sleep(delay)
    finally:
        if own_client:
            await client.aclose()
    return products
