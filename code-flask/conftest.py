import pytest


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Garantit que chaque test s'exécute sur une base temporaire isolée, sans jamais toucher data.db."""
    db_file = tmp_path / "test_data.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    yield db_file
