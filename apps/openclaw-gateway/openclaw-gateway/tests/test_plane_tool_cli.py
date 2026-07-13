import json

import pytest

from openclaw_gateway import plane_tool_cli


class FakeClient:
    def __init__(self, auth, timeout_seconds=15.0):
        self.auth = auth
        self.timeout_seconds = timeout_seconds

    async def list_projects(self):
        return {"items": [{"id": "project-1", "name": "Openclaw"}]}

    async def list_states(self, project_id):
        return {"items": [{"id": "state-todo", "name": f"Todo for {project_id}"}]}

    async def list_labels(self, project_id):
        return {"items": [{"id": "label-1", "name": f"tag:codex:{project_id}"}]}

    async def search_work_items(self, **kwargs):
        return {"items": [{"id": "work-item-1", "name": kwargs["query"]}]}

    async def get_work_item(self, project_id, work_item_id):
        return {"id": work_item_id, "project_id": project_id, "name": "Read item"}

    async def create_work_item(self, project_id, request):
        return {
            "id": "work-item-2",
            "name": request.name,
            "project_id": project_id,
            "state_id": "state-todo",
        }

    async def update_work_item(self, project_id, work_item_id, request):
        return {
            "id": work_item_id,
            "name": request.name,
            "project_id": project_id,
        }

    async def add_comment(self, project_id, work_item_id, request):
        return {
            "id": "comment-1",
            "work_item_id": work_item_id,
            "project_id": project_id,
            "comment_html": request.comment_html,
        }


def test_cli_search_outputs_json_without_token(monkeypatch, capsys):
    monkeypatch.setenv("GATEWAY_URL", "http://gateway.example")
    monkeypatch.setenv("GATEWAY_AUTH_TOKEN", "gateway-secret")
    monkeypatch.setattr(plane_tool_cli, "PlaneToolClient", FakeClient)

    exit_code = plane_tool_cli.main(["search", "--query", "Plane", "--project-id", "project-1"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert json.loads(output)["items"][0]["name"] == "Plane"
    assert "gateway-secret" not in output


def test_cli_requires_gateway_env(monkeypatch, capsys):
    monkeypatch.delenv("GATEWAY_URL", raising=False)
    monkeypatch.delenv("GATEWAY_AUTH_TOKEN", raising=False)

    exit_code = plane_tool_cli.main(["projects"])

    assert exit_code == 2
    assert "GATEWAY_URL and GATEWAY_AUTH_TOKEN are required" in capsys.readouterr().err


def test_cli_create_requires_project_id(monkeypatch):
    monkeypatch.setenv("GATEWAY_URL", "http://gateway.example")
    monkeypatch.setenv("GATEWAY_AUTH_TOKEN", "gateway-secret")
    monkeypatch.setattr(plane_tool_cli, "PlaneToolClient", FakeClient)

    with pytest.raises(SystemExit) as exc_info:
        plane_tool_cli.main(["create", "--name", "Missing project"])

    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    ("argv", "expected_key", "expected_value"),
    [
        (["projects"], "name", "Openclaw"),
        (["states", "--project-id", "project-1"], "name", "Todo for project-1"),
        (["labels", "--project-id", "project-1"], "name", "tag:codex:project-1"),
        (
            ["read", "--project-id", "project-1", "--work-item-id", "work-item-1"],
            "id",
            "work-item-1",
        ),
        (
            ["create", "--project-id", "project-1", "--name", "Created by CLI"],
            "state_id",
            "state-todo",
        ),
        (
            [
                "update",
                "--project-id",
                "project-1",
                "--work-item-id",
                "work-item-1",
                "--name",
                "Updated by CLI",
            ],
            "name",
            "Updated by CLI",
        ),
        (
            [
                "comment",
                "--project-id",
                "project-1",
                "--work-item-id",
                "work-item-1",
                "--comment-html",
                "<p>Progress</p>",
            ],
            "comment_html",
            "<p>Progress</p>",
        ),
    ],
)
def test_cli_commands_route_to_tool_client(monkeypatch, capsys, argv, expected_key, expected_value):
    monkeypatch.setenv("GATEWAY_URL", "http://gateway.example")
    monkeypatch.setenv("GATEWAY_AUTH_TOKEN", "gateway-secret")
    monkeypatch.setattr(plane_tool_cli, "PlaneToolClient", FakeClient)

    exit_code = plane_tool_cli.main(argv)

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    if "items" in output:
        output = output["items"][0]
    assert output[expected_key] == expected_value
