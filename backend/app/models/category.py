from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Relationship, Field

from .link_models import CategoryCreatorLink

if TYPE_CHECKING:
    # This runs ONLY during static analysis/IDE linting.
    # Python completely ignores this block at runtime, breaking the circular import.
    from .creator import Creator

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)

    creators: list["Creator"] = Relationship(
        back_populates="categories", link_model=CategoryCreatorLink
    )
