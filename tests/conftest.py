from pathlib import Path

import pytest

from bot import config


@pytest.fixture
def isolated_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "ideabucket.db"))
    projects = tmp_path / "projects.yaml"
    projects.write_text("projects:\n  - hashtag: '#demo'\n    description: Demo\n", encoding="utf-8")
    monkeypatch.setattr(config, "PROJECTS_PATH", projects)
    monkeypatch.setattr(config, "OPEN_DASHBOARD", False)
    monkeypatch.setattr(config, "CAPTURE_TOKEN", "test-token-that-is-long-enough-123456")
    return tmp_path

