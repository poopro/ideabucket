import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_dashboard_uses_scoped_timeline_handlers_and_authenticated_api(tmp_path: Path) -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    assert 'document.querySelectorAll("#filters .chip")' in html
    assert "X-Ideabucket-Token" in html
    assert "__IDEABUCKET_CAPTURE_TOKEN__" in html

    script = re.search(r"<script>([\s\S]*?)</script>", html).group(1)
    script = script.replace("__IDEABUCKET_CAPTURE_TOKEN__", json_string("test-token"))
    path = tmp_path / "dashboard.js"
    path.write_text(script, encoding="utf-8")
    subprocess.run(["node", "--check", str(path)], check=True)


def json_string(value: str) -> str:
    import json

    return json.dumps(value)

