from abc import ABC
from typing import Generic, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(ABC, Generic[T]):
    """Generic async CRUD repository for SQLAlchemy ORM models."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, entity_id: int) -> T | None:
        """Fetch a single entity by primary key."""
        return await self._session.get(self._model, entity_id)

    async def get_all(self) -> Sequence[T]:
        """Fetch all entities of this model."""
        result = await self._session.execute(select(self._model))
        return result.scalars().all()

    async def create(self, entity: T) -> T:
        """Persist a new entity."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        merged = await self._session.merge(entity)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, entity: T) -> None:
        """Remove an entity from the database."""
        await self._session.delete(entity)
        await self._session.flush()
