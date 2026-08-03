"""Script d'import initial des 3 bases nettoyees (data/raw/) vers PostgreSQL.

Usage (depuis backend/, avec le venv active) :
    python scripts/run_initial_import.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import SessionLocal  # noqa: E402
from app.services.import_service import (  # noqa: E402
    import_compatibility_rules,
    import_drivers,
    import_lenses,
    import_modules,
)

DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

FILES = {
    "driver": DATA_RAW / "LED_Drivers_Database_Cleaned.xlsx",
    "led_module": DATA_RAW / "LED_Modules_Database_Cleaned.xlsx",
    "lens": DATA_RAW / "LED_Lenses_Database_Cleaned.xlsx",
}


def print_result(result) -> None:
    print(f"\n=== {result.entity_type.upper()} — {result.file_name} ===")
    print(f"  Lignes totales   : {result.rows_total}")
    print(f"  Importees (new)  : {result.rows_imported}")
    print(f"  Mises a jour     : {result.rows_updated}")
    print(f"  Rejetees         : {result.rows_rejected}")
    if result.issues:
        print(f"  Detail des rejets ({len(result.issues)}) :")
        for issue in result.issues[:15]:
            print(f"    - ligne {issue['row_number']} ({issue['external_ref']}) : {issue['description']}")
        if len(result.issues) > 15:
            print(f"    ... et {len(result.issues) - 15} de plus (voir audit.data_issues)")


def main() -> None:
    session = SessionLocal()
    try:
        result = import_drivers(session, str(FILES["driver"]), FILES["driver"].name)
        session.commit()
        print_result(result)

        result = import_modules(session, str(FILES["led_module"]), FILES["led_module"].name)
        session.commit()
        print_result(result)

        result = import_lenses(session, str(FILES["lens"]), FILES["lens"].name)
        session.commit()
        print_result(result)

        print("\n=== Regles de compatibilite ===")
        rule_entity_types = {"driver": "driver", "led_module": "module", "lens": "lens"}
        for files_key, rule_entity_type in rule_entity_types.items():
            n = import_compatibility_rules(session, str(FILES[files_key]), rule_entity_type)
            session.commit()
            print(f"  {rule_entity_type}: {n} regles chargees")

        print("\nImport initial termine.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
