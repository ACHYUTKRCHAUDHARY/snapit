import pytest

from snappe.adapters.database import Database
from snappe.config import Settings


def test_database_check_connection_and_dispose(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'snappe.db'}",
    )
    database = Database(settings)

    database.check_connection()
    database.create_tables()
    database.dispose()


def test_database_migrations_require_postgresql() -> None:
    database = Database(Settings(_env_file=None))

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        database.apply_migrations(None)

    database.dispose()
