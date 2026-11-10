"""Agent behaviour: catalogue, orchestration, approval gate, error handling."""
from __future__ import annotations

from app.agents.base import AgentError
from app.agents.orchestrator import get_agent, list_agents


def test_six_agents_are_registered():
    names = {a["name"] for a in list_agents()}
    assert names == {"video_intelligence", "editing", "design", "seo", "analytics", "community"}
    for a in list_agents():
        assert a["description"] and a["capabilities"]


def test_unknown_agent_is_rejected(user_client):
    client, _ = user_client
    r = client.post("/api/agents/run", json={"agent": "does_not_exist", "params": {}})
    assert r.status_code == 422
    assert "Unknown agent" in r.json()["detail"]


def test_community_agent_never_publishes_without_approval(user_client):
    client, _ = user_client
    r = client.post("/api/agents/run", params={"sync": True},
                    json={"agent": "community",
                          "params": {"comment": "How did you measure the energy?"}})
    assert r.status_code == 202
    task = r.json()
    assert task["status"] == "awaiting_approval"
    assert task["output_data"]["awaiting_approval"] is True
    assert "Nothing is published" in task["output_data"]["note"]

    # Rejecting it is a valid terminal state.
    r = client.post(f"/api/agents/tasks/{task['id']}/approve",
                    json={"approve": False, "note": "too generic"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"


def test_agent_run_records_logs_and_progress(user_client):
    client, _ = user_client
    r = client.post("/api/agents/run", params={"sync": True},
                    json={"agent": "analytics", "params": {}})
    task = r.json()
    assert task["status"] == "succeeded"
    assert task["progress"] == 100
    assert task["logs"], "an agent run must leave a log trail"
    assert any("videos processed" in log["message"] for log in task["logs"])


def test_agent_with_missing_input_fails_cleanly(user_client):
    client, _ = user_client
    r = client.post("/api/agents/run", params={"sync": True},
                    json={"agent": "video_intelligence", "params": {}})
    task = r.json()
    assert task["status"] == "failed"
    assert "No video specified" in task["error"]


def test_approval_on_a_finished_task_is_a_conflict(user_client):
    client, _ = user_client
    task = client.post("/api/agents/run", params={"sync": True},
                       json={"agent": "analytics", "params": {}}).json()
    r = client.post(f"/api/agents/tasks/{task['id']}/approve", json={"approve": True})
    assert r.status_code == 409


def test_agent_classes_are_independently_importable():
    for name in ("video_intelligence", "editing", "design", "seo", "analytics", "community"):
        agent = get_agent(name)
        assert agent.name == name
        assert hasattr(agent, "run")


def test_not_authorised_is_distinct_from_a_plain_error():
    from app.agents.base import NotAuthorised
    assert issubclass(NotAuthorised, AgentError)
