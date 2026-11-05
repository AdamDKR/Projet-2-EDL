import os
import sqlite3
from pathlib import Path

RACINE = Path(__file__).parent.parent
BASE = RACINE / "data.db"
BASE_SQL = RACINE / "base.sql"


def ensure_schema(conn):
    """Garantit la présence des colonnes ouverture et fermeture dans la table salles."""
    colonnes = [c["name"] for c in conn.execute("PRAGMA table_info(salles)").fetchall()]
    if "ouverture" not in colonnes:
        conn.execute("ALTER TABLE salles ADD COLUMN ouverture TEXT NOT NULL DEFAULT '08:00'")
    if "fermeture" not in colonnes:
        conn.execute("ALTER TABLE salles ADD COLUMN fermeture TEXT NOT NULL DEFAULT '20:00'")


def ouvrir_base(path=None):
    """Ouvre la base SQLite avec support de l'isolation pour les tests."""
    cible = path or os.environ.get("DATABASE_PATH") or BASE
    is_memory = (str(cible) == ":memory:")
    neuve = is_memory or (not Path(cible).exists()) or (Path(cible).stat().st_size == 0)
    conn = sqlite3.connect(cible)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if neuve:
        conn.executescript(BASE_SQL.read_text(encoding="utf-8"))
    else:
        ensure_schema(conn)
    return conn
