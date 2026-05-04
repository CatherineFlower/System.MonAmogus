"""SQLAlchemy database configuration and session utilities."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import Service  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        demo_services = [
            ("MAX", "https://max.ru"),
            ("VK", "https://vk.ru"),
            ("Yandex", "https://yandex.ru"),
            ("Ya", "https://ya.ru"),
            ("OK", "https://ok.ru"),
        ]

        for name, url in demo_services:
            exists = db.query(Service).filter(Service.url == url).first()
            if not exists:
                db.add(Service(name=name, url=url, is_active=True))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Database schema initialized")