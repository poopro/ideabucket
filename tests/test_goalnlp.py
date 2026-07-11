from bot import goalnlp


def test_parse_goal_uses_explicit_hashtag_without_llm(monkeypatch):
    monkeypatch.setattr(goalnlp.summarize, "load_projects", lambda: [])
    monkeypatch.setattr(goalnlp.db, "get_goals", lambda: {})

    data = goalnlp.parse_goal("#ideabucket make the dashboard useful")

    assert data["tag"] == "#ideabucket"
    assert data["goal"] == "make the dashboard useful"
    assert data["is_new"] is True
    assert data["source"] == "explicit"
