"""Query building for the search endpoints.

Two rules apply to every scope:
  * `text` is tokenised on whitespace and EVERY token must match somewhere
    (AND across tokens, OR across fields) -- that's what makes "fitness mumbai" work.
  * every sort ends with a unique tiebreaker, or rows repeat or vanish between pages.
"""

from typing import Optional, Sequence
import time

from sqlalchemy import ColumnElement
from sqlmodel import and_, or_, select, func
from sqlmodel.sql.expression import SelectOfScalar
from sqlmodel.ext.asyncio.session import AsyncSession


def tokens(text: Optional[str]) -> list[str]:
    return [t for t in (text or "").split() if t]


def text_clause(
    text: Optional[str], fields: Sequence[ColumnElement]
) -> Optional[ColumnElement]:
    toks = tokens(text)
    if not toks or not fields:
        return None
    return and_(*[or_(*[f.ilike(f"%{t}%") for f in fields]) for t in toks])


def clamp_page(total: int, page: int, page_size: int) -> tuple[int, int]:
    pages = max(1, (total + page_size - 1) // page_size)
    return min(page, pages), pages


async def count_of(session: AsyncSession, stmnt: SelectOfScalar) -> int:
    sub = stmnt.order_by(None).subquery()
    return (await session.exec(select(func.count()).select_from(sub))).one()


class Timer:
    def __enter__(self):
        self._t = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = int((time.perf_counter() - self._t) * 1000)
