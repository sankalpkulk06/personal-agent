from pathlib import Path

from app.config.settings import Settings


def test_settings_load_from_dotenv_and_env_override(tmp_path, monkeypatch):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "OLLAMA_BASE_URL=http://127.0.0.1:11434\n"
        "CHUNK_SIZE=900\n"
        "CHUNK_OVERLAP=100\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("CHUNK_SIZE", "1024")
    settings = Settings.from_env(project_root=tmp_path)

    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.chunk_size == 1024
    assert settings.chunk_overlap == 100


def test_settings_resolve_local_paths(tmp_path):
    settings = Settings.from_env(project_root=tmp_path)
    paths = settings.resolve_paths(project_root=tmp_path)

    assert paths.project_root == tmp_path.resolve()
    assert paths.data_dir == (tmp_path / "data").resolve()
    assert paths.chroma_dir == (tmp_path / "data" / "chroma").resolve()
    assert paths.sqlite_db_path == (tmp_path / "data" / "sqlite" / "registry.db").resolve()
    assert Path(paths.chroma_dir).exists()
    assert Path(paths.sqlite_dir).exists()

