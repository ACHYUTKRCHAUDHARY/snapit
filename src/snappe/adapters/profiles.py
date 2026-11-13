"""In-memory profile repository for local execution and tests."""

from snappe.domain.profile import BusinessProfile


class InMemoryProfileRepository:
    """Store profile versions in process memory until durable persistence is added."""

    def __init__(self) -> None:
        self._profiles: dict[tuple[str, int], BusinessProfile] = {}

    def save(self, profile: BusinessProfile) -> None:
        self._profiles[(profile.business_id, profile.version)] = profile

    def get(self, business_id: str, version: int) -> BusinessProfile | None:
        return self._profiles.get((business_id, version))

    def list_for_business(self, business_id: str) -> list[BusinessProfile]:
        return sorted(
            (
                profile
                for (stored_business_id, _), profile in self._profiles.items()
                if stored_business_id == business_id
            ),
            key=lambda profile: profile.version,
        )

    def set_active(self, business_id: str, version: int) -> None:
        for profile in self.list_for_business(business_id):
            self._profiles[(business_id, profile.version)] = BusinessProfile(
                business_id=profile.business_id,
                version=profile.version,
                display_name=profile.display_name,
                languages=profile.languages,
                approved_facts=profile.approved_facts,
                active=False,
                approved_at=None,
            )
