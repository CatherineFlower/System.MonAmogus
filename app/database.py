"""SQLAlchemy database configuration and session utilities."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./demo.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _apply_sqlite_compat_migrations() -> None:
    """Add missing columns for legacy SQLite files created before new schema fields."""
    inspector = inspect(engine)
    if "services" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("services")}
    alterations: list[str] = []

    if "description" not in columns:
        alterations.append("ALTER TABLE services ADD COLUMN description TEXT")
    if "is_active" not in columns:
        alterations.append("ALTER TABLE services ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
    if "sort_order" not in columns:
        alterations.append("ALTER TABLE services ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
    if "updated_at" not in columns:
        alterations.append("ALTER TABLE services ADD COLUMN updated_at DATETIME")

    if not alterations:
        return

    with engine.begin() as conn:
        for statement in alterations:
            conn.execute(text(statement))
        if "updated_at" not in columns:
            conn.execute(text("UPDATE services SET updated_at = created_at WHERE updated_at IS NULL"))


def init_db() -> None:
    """Create all configured tables and apply lightweight compatibility migrations."""
    # Local import prevents circular imports.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_compat_migrations()


if __name__ == "__main__":
    init_db()
    print("Database schema initialized")
