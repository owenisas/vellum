"""aiosqlite connection helpers."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from .schema import SCHEMA

DB_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA synchronous=NORMAL",
)


def db_pragma() -> tuple[str, ...]:
    return DB_PRAGMAS


def _is_in_memory(db_path: str) -> bool:
    return db_path == ":memory:" or db_path.startswith("file::memory:")


@asynccontextmanager
async def get_db(db_path: str):
    """Open an aiosqlite connection, apply pragmas, autocommit on exit."""
    if not _is_in_memory(db_path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        for pragma in DB_PRAGMAS:
            try:
                await db.execute(pragma)
            except aiosqlite.Error:
                # WAL is unsupported on :memory: — ignore.
                pass
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def init_db(db_path: str) -> None:
    """Create tables if missing."""
    if not _is_in_memory(db_path):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    async with get_db(db_path) as db:
        await db.executescript(SCHEMA)
