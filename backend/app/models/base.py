from __future__ import annotations

from sqlalchemy import event, text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


@event.listens_for(Base.metadata, "after_create")
def _enable_sqlite_fk(target, connection, **kw):
    if connection.engine.dialect.name == "sqlite":
        connection.execute(text("PRAGMA foreign_keys=ON"))
