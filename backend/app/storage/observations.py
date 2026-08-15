"""Repository helpers for raw observations."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.sources.observations import Observation
from app.storage.models import ObservationRecord


def save_observations(engine: Engine, observations: Iterable[Observation]) -> int:
    count = 0
    with Session(engine) as session:
        for observation in observations:
            session.merge(ObservationRecord.from_observation(observation))
            count += 1
        session.commit()
    return count


def list_observations(engine: Engine) -> list[Observation]:
    with Session(engine) as session:
        records = session.scalars(select(ObservationRecord)).all()
        return [record.to_observation() for record in records]
