# tests/test_migrations.py
"""
Verifica la integridad estructural de las migraciones de Alembic
sin necesitar conexión a una base de datos real.
"""
import ast
import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

VERSIONS_DIR = Path(__file__).parent.parent / "migrations" / "versions"


def _get_scripts() -> ScriptDirectory:
    cfg = Config("alembic.ini")
    return ScriptDirectory.from_config(cfg)


# ── Estructura de la cadena ───────────────────────────────────────


def test_single_head():
    """Debe existir exactamente un head para evitar ramas divergentes."""
    scripts = _get_scripts()
    heads = scripts.get_heads()
    assert len(heads) == 1, f"Se esperaba 1 head, encontrados: {heads}"


def test_no_orphaned_revisions():
    """
    Cada down_revision debe apuntar a una revisión existente o None.
    Un down_revision huérfano rompe alembic upgrade.
    """
    scripts = _get_scripts()
    revisions = {r.revision: r for r in scripts.walk_revisions()}

    for rev in revisions.values():
        if rev.down_revision is None:
            continue
        parents = (
            [rev.down_revision]
            if isinstance(rev.down_revision, str)
            else list(rev.down_revision)
        )
        for parent in parents:
            assert parent in revisions, (
                f"Revisión {rev.revision} apunta a down_revision '{parent}' "
                f"que no existe en la cadena."
            )


def test_linear_chain_no_branches():
    """
    Ninguna revisión debe tener múltiples padres (merge) a menos que sea
    intencional. La cadena de PISST debe ser lineal.
    """
    scripts = _get_scripts()
    for rev in scripts.walk_revisions():
        if isinstance(rev.down_revision, (list, tuple)):
            assert len(rev.down_revision) <= 1, (
                f"Revisión {rev.revision} tiene múltiples down_revisions: "
                f"{rev.down_revision}"
            )


def test_revision_count():
    """Verifica que haya al menos 15 migraciones (regresión: no se borraron accidentalmente)."""
    scripts = _get_scripts()
    revisions = list(scripts.walk_revisions())
    assert len(revisions) >= 15, f"Solo {len(revisions)} revisiones; se esperaban ≥15"


# ── Contenido de las migraciones ─────────────────────────────────


def test_no_op_migrations_removed():
    """
    Ningún archivo debe tener upgrade() con solo 'pass'.
    Las migraciones no-op se eliminan porque no aportan valor y
    añaden latencia en deployments.
    """
    for path in VERSIONS_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name == "upgrade"):
                continue
            body = [s for s in node.body if not isinstance(s, ast.Expr)]
            only_pass = len(body) == 1 and isinstance(body[0], ast.Pass)
            assert not only_pass, (
                f"{path.name}: upgrade() contiene solo 'pass' — "
                "migración no-op debe eliminarse."
            )


def test_no_anonymous_foreign_keys():
    """
    op.create_foreign_key(None, ...) genera FKs sin nombre en PostgreSQL,
    lo que hace imposible hacer downgrade limpio.
    """
    pattern = re.compile(r"op\.create_foreign_key\(\s*None\s*,")
    for path in VERSIONS_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not pattern.search(source), (
            f"{path.name}: contiene op.create_foreign_key(None, ...) — "
            "asigna un nombre explícito a la FK."
        )


def test_no_anonymous_drop_constraint():
    """
    op.drop_constraint(None, ...) falla en PostgreSQL con FKs sin nombre.
    """
    pattern = re.compile(r"op\.drop_constraint\(\s*None\s*,")
    for path in VERSIONS_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not pattern.search(source), (
            f"{path.name}: contiene op.drop_constraint(None, ...) — "
            "usa el nombre explícito de la FK."
        )


def test_migration_files_are_valid_python():
    """Todos los archivos de migración deben ser Python sintácticamente válido."""
    errors = []
    for path in VERSIONS_DIR.glob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as e:
            errors.append(f"{path.name}: {e}")
    assert not errors, "Migraciones con error de sintaxis:\n" + "\n".join(errors)


def test_head_migration_exists_as_file():
    """El head de alembic debe corresponder a un archivo en versions/."""
    scripts = _get_scripts()
    head_rev = scripts.get_heads()[0]
    matching = list(VERSIONS_DIR.glob(f"{head_rev}_*.py"))
    assert (
        matching
    ), f"No se encontró archivo para la revisión head '{head_rev}' en versions/"


# ── upgrade / downgrade vía alembic history (sin DB) ─────────────


def test_alembic_history_is_complete():
    """
    Verifica que alembic pueda recorrer toda la historia sin errores.
    Equivalente a 'alembic history' sin necesitar conexión a BD.
    """
    scripts = _get_scripts()
    revisions = list(scripts.walk_revisions())
    revision_ids = {r.revision for r in revisions}

    base_rev = next((r for r in revisions if r.down_revision is None), None)
    assert base_rev is not None, "No se encontró la revisión base (down_revision=None)"

    heads = scripts.get_heads()
    assert heads[0] in revision_ids, "El head no está en la lista de revisiones"
