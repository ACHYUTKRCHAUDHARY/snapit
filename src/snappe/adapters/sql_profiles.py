"""SQLAlchemy-backed implementation of ProfileRepository."""

from collections.abc import Iterable
from datetime import UTC

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from snappe.adapters.database import Database
from snappe.adapters.models import BusinessProfileModel
from snappe.application.profiles import ProfileRepository
from snappe.domain.profile import BusinessProfile


class SQLProfileRepository(ProfileRepository):
    """Persist and query business profiles using an existing SQLAlchemy Engine."""

    def __init__(self, database: Database) -> None:
        self._session_factory = sessionmaker(bind=database.engine, expire_on_commit=False)

    def _to_domain(self, model: BusinessProfileModel) -> BusinessProfile:
        approved_at = model.approved_at
        if approved_at is not None and approved_at.tzinfo is None:
            approved_at = approved_at.replace(tzinfo=UTC)
        return BusinessProfile(
            business_id=model.business_id,
            version=model.version,
            display_name=model.display_name,
            languages=tuple(model.languages),
            approved_facts=dict(model.approved_facts),
            active=model.active,
            approved_at=approved_at,
        )

    def save(self, profile: BusinessProfile) -> None:
        with self._session_factory() as session:
            stmt = select(BusinessProfileModel).where(
                BusinessProfileModel.business_id == profile.business_id,
                BusinessProfileModel.version == profile.version,
            )
            existing = session.scalar(stmt)
            if existing is None:
                record = BusinessProfileModel(
                    business_id=profile.business_id,
                    version=profile.version,
                    display_name=profile.display_name,
                    languages=list(profile.languages),
                    approved_facts=dict(profile.approved_facts),
                    active=profile.active,
                    approved_at=profile.approved_at,
                )
                session.add(record)
            else:
                existing.display_name = profile.display_name
                existing.languages = list(profile.languages)
                existing.approved_facts = dict(profile.approved_facts)
                existing.active = profile.active
                existing.approved_at = profile.approved_at
            session.commit()

    def get(self, business_id: str, version: int) -> BusinessProfile | None:
        with self._session_factory() as session:
            stmt = select(BusinessProfileModel).where(
                BusinessProfileModel.business_id == business_id,
                BusinessProfileModel.version == version,
            )
            model = session.scalar(stmt)
            if model is None:
                return None
            return self._to_domain(model)

    def list_for_business(self, business_id: str) -> Iterable[BusinessProfile]:
        with self._session_factory() as session:
            stmt = (
                select(BusinessProfileModel)
                .where(BusinessProfileModel.business_id == business_id)
                .order_by(BusinessProfileModel.version.asc())
            )
            models = session.scalars(stmt).all()
            return [self._to_domain(model) for model in models]

    def set_active(self, business_id: str, version: int) -> None:
        with self._session_factory() as session:
            # Set all profiles for this business to inactive
            session.execute(
                update(BusinessProfileModel)
                .where(BusinessProfileModel.business_id == business_id)
                .values(active=False, approved_at=None)
            )
            session.commit()
