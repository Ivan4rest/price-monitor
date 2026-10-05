"""Разбор страницы каталога в список товаров."""
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from pricemon.site import Site


@dataclass(frozen=True)
class Product:
    url: str
    title: str
    price: float
    in_stock: bool


def parse_price(text: str) -> float:
    """«£1 234,50» → 1234.5. Запятая считается десятичной, только если после неё не три цифры."""
    digits = re.sub(r"[^\d.,]", "", text)
    if "," in digits and "." in digits:
        digits = digits.replace(",", "")
    elif re.search(r",\d{3}$", digits):
        digits = digits.replace(",", "")
    else:
        digits = digits.replace(",", ".")
    return float(digits)


def parse_catalogue(html: str, page_url: str, site: Site) -> tuple[list[Product], str | None]:
    """Возвращает товары страницы и адрес следующей страницы (или None на последней)."""
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for card in soup.select(site.item):
        title, link, price = card.select_one(site.title), card.select_one(site.link), card.select_one(site.price)
        if not (title and link and price):
            continue  # рекламный блок или карточка без цены
        products.append(
            Product(
                url=urljoin(page_url, link["href"]),
                title=title.get("title") or title.get_text(strip=True),
                price=parse_price(price.get_text()),
                in_stock=card.select_one(site.in_stock) is not None,
            )
        )
    next_link = soup.select_one(site.next_page)
    return products, urljoin(page_url, next_link["href"]) if next_link else None
