"""Stockage disque des fichiers CPS/CCTP importes.

Convention alignee sur `app/rag/index_default_documents.py` (`backend/data/...`).
Le nom de fichier utilisateur n'est JAMAIS utilise tel quel comme chemin filesystem :
il est assaini (`sanitize_filename`) et prefixe par l'id projet + un hash court, pour
eviter toute collision ou tentative de path traversal.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.reports.formatting import sanitize_filename

CPS_UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "cps_uploads"


def save_upload(project_id: int, original_filename: str, content: bytes) -> tuple[Path, str, str]:
    """Ecrit `content` sur disque sous un nom assaini. Renvoie (chemin, nom_stocke, sha256)."""
    project_dir = CPS_UPLOADS_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    file_hash = hashlib.sha256(content).hexdigest()
    stem = sanitize_filename(Path(original_filename).stem)
    stored_filename = f"{file_hash[:12]}_{stem}.pdf"

    path = project_dir / stored_filename
    path.write_bytes(content)
    return path, stored_filename, file_hash
