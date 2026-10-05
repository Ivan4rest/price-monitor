"""История цен в SQLite и сравнение текущего прохода с предыдущим."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from pricemon.parse import Product

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prices (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    in_stock INTEGER NOT NULL,
    PRIMARY KEY (run_id, url)
);
"""


@dataclass(frozen=True)
class Change:
    kind: str  # new | removed | price | stock
    title: str
    url: str
    old_price: float | None = None
    new_price: float | None = None
    in_stock: bool | None = None

    @property
    def percent(self) -> float | None:
        if self.kind != "price" or not self.old_price:
            return None
        return round((self.new_price - self.old_price) / self.old_price * 100, 1)


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_run(conn: sqlite3.Connection, products: list[Product]) -> int:
    with conn:
        run_id = conn.execute(
            "INSERT INTO runs (started_at) VALUES (?)", (datetime.now(timezone.utc).isoformat(),)
        ).lastrowid
        # Один и тот же товар может встретиться на двух страницах — оставляем первое вхождение
        conn.executemany(
            "INSERT OR IGNORE INTO prices VALUES (?, ?, ?, ?, ?)",
            [(run_id, p.url, p.title, p.price, int(p.in_stock)) for p in products],
        )
    return run_id


def load_run(conn: sqlite3.Connection, run_id: int) -> dict[str, sqlite3.Row]:
    return {row["url"]: row for row in conn.execute("SELECT * FROM prices WHERE run_id = ?", (run_id,))}


def changes(conn: sqlite3.Connection, run_id: int) -> list[Change]:
    """Что изменилось в проходе run_id по сравнению с предыдущим. Для первого прохода — пусто."""
    previous = conn.execute("SELECT MAX(id) FROM runs WHERE id < ?", (run_id,)).fetchone()[0]
    if previous is None:
        return []
    old, new = load_run(conn, previous), load_run(conn, run_id)
    result = []
    for url, row in new.items():
        before = old.get(url)
        if before is None:
            result.append(Change("new", row["title"], url, new_price=row["price"]))
        elif before["price"] != row["price"]:
            result.append(Change("price", row["title"], url, before["price"], row["price"]))
        elif before["in_stock"] != row["in_stock"]:
            result.append(Change("stock", row["title"], url, in_stock=bool(row["in_stock"])))
    result += [Change("removed", row["title"], url, old_price=row["price"]) for url, row in old.items() if url not in new]
    return result
