"""Verrouille l'independance architecturale demandee explicitement par le consultant :
`app/ai/` (assistant IA) et `app/cps/` (import CPS/CCTP) ne doivent JAMAIS s'importer
l'un l'autre. Les deux dependent uniquement de la couche neutre `app/domain/`. Un test
statique (analyse des imports, pas d'execution) plutot qu'une simple relecture de code,
pour que toute regression future soit detectee automatiquement."""

import ast
from pathlib import Path

AI_DIR = Path(__file__).resolve().parent.parent / "app" / "ai"
CPS_DIR = Path(__file__).resolve().parent.parent / "app" / "cps"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def test_ai_package_never_imports_from_cps_package():
    for py_file in AI_DIR.glob("*.py"):
        offending = {m for m in _imported_modules(py_file) if m == "app.cps" or m.startswith("app.cps.")}
        assert not offending, f"{py_file.name} importe {offending} depuis app.cps (l'IA doit rester independante)"


def test_cps_package_never_imports_from_ai_package():
    for py_file in CPS_DIR.glob("*.py"):
        offending = {m for m in _imported_modules(py_file) if m == "app.ai" or m.startswith("app.ai.")}
        assert not offending, f"{py_file.name} importe {offending} depuis app.ai"


def test_domain_package_never_imports_from_ai_or_cps():
    """La couche partagee doit rester neutre : si elle importait depuis ai/ ou cps/,
    l'independance des deux features reposerait sur une illusion (dependance cachee)."""
    domain_dir = Path(__file__).resolve().parent.parent / "app" / "domain"
    for py_file in domain_dir.glob("*.py"):
        modules = _imported_modules(py_file)
        offending = {m for m in modules if m.startswith("app.ai") or m.startswith("app.cps")}
        assert not offending, f"{py_file.name} importe {offending} : app/domain/ doit rester neutre"
