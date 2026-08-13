"""Helper unique pour tracer un evenement dans `ProjectHistory`.

Vit dans `app/domain/` (generique, pas specifique au CPS) : `app/cps/` et `app/ai/`
l'utilisent tous les deux sans dependre l'un de l'autre.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models import ProjectHistory


def log_project_event(
    db: Session, project_id: int, action: str, actor: str | None = None, details: dict | None = None
) -> None:
    db.add(
        ProjectHistory(
            project_id=project_id,
            action=action,
            actor=actor,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
    )
