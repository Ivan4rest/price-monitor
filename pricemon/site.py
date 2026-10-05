"""Описание сайта-источника: адрес каталога и CSS-селекторы.

Чтобы подключить другой магазин, достаточно описать его здесь — код сбора не меняется.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    name: str
    start_url: str
    item: str          # карточка товара
    title: str         # элемент с названием (берётся атрибут title или текст)
    link: str          # ссылка на страницу товара
    price: str         # элемент с ценой
    in_stock: str      # элемент, наличие которого означает «в наличии»
    next_page: str     # ссылка на следующую страницу каталога


# Учебный магазин, созданный специально для отработки парсинга
BOOKS_TO_SCRAPE = Site(
    name="books.toscrape.com",
    start_url="https://books.toscrape.com/catalogue/page-1.html",
    item="article.product_pod",
    title="h3 a",
    link="h3 a",
    price="p.price_color",
    in_stock="p.instock",
    next_page="li.next a",
)
