"""Database connectivity and migration adapter."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, text

from snappe.adapters.models import Base
from snappe.config import Settings


class Database:
    """Own the SQLAlchemy engine used by the application."""

    def __init__(self, settings: Settings) -> None:
        connect_args = (
            {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        )
        self.engine: Engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

    def check_connection(self) -> None:
        """Raise when the configured database cannot execute a query."""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def apply_migrations(self, migrations_dir: Path) -> None:
        """Apply ordered PostgreSQL migrations exactly once."""
        if self.engine.dialect.name != "postgresql":
            raise RuntimeError("Supabase migrations require a PostgreSQL database")

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            applied = {
                row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))
            }
            for migration in sorted(migrations_dir.glob("*.sql")):
                if migration.name in applied:
                    continue
                connection.exec_driver_sql(migration.read_text(encoding="utf-8"))
                connection.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                    {"version": migration.name},
                )

    def create_tables(self) -> None:
        """Create all declarative tables if they do not exist."""
        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        """Release pooled database connections."""
        self.engine.dispose()
