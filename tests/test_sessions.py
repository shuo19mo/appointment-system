from agents.session_store import SessionStore


def test_conversation_state_is_isolated_by_session_id():
    store = SessionStore(ttl_seconds=300)
    store.update("family-a", {"student_name": "小明", "subject": "数学"})
    store.update("family-b", {"student_name": "小红", "subject": "英语"})

    assert store.get("family-a")["student_name"] == "小明"
    assert store.get("family-b")["student_name"] == "小红"

    store.update("family-a", {"campus_name": "浦东校区"})
    assert "campus_name" not in store.get("family-b")


def test_session_reset_only_clears_target_session():
    store = SessionStore(ttl_seconds=300)
    store.update("a", {"subject": "数学"})
    store.update("b", {"subject": "英语"})

    store.reset("a")

    assert store.get("a") == {}
    assert store.get("b") == {"subject": "英语"}


def test_session_expires_by_ttl_and_rejects_blank_id():
    now = [100.0]
    store = SessionStore(ttl_seconds=10, clock=lambda: now[0])
    store.update("family", {"subject": "数学"})
    now[0] = 111.0

    assert store.get("family") == {}

    try:
        store.update("   ", {"subject": "英语"})
    except ValueError as exc:
        assert "session_id" in str(exc)
    else:
        raise AssertionError("blank session_id must be rejected")
