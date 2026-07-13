import json

import httpx
import pytest
import respx

from openclaw_gateway.plane_tools import (
    PlaneCommentToolRequest,
    PlaneToolAuth,
    PlaneToolClient,
    PlaneToolError,
    PlaneWorkItemCreateToolRequest,
    PlaneWorkItemUpdateToolRequest,
)


AUTH = PlaneToolAuth(
    gateway_url="http://gateway.example",
    gateway_token="gateway-secret",
)


@pytest.mark.asyncio
async def test_search_uses_gateway_auth_and_returns_items():
    with respx.mock(assert_all_called=True) as router:
        route = router.get("http://gateway.example/v1/workflow/plane/search").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"id": "work-item-1", "name": "Wire Plane tools"}]},
            )
        )

        result = await PlaneToolClient(AUTH).search_work_items(
            query="Plane",
            project_id="project-1",
            limit=5,
        )

    assert result == {"items": [{"id": "work-item-1", "name": "Wire Plane tools"}]}
    assert route.calls.last.request.headers["Authorization"] == "Bearer gateway-secret"
    assert "X-API-Key" not in route.calls.last.request.headers
    assert dict(route.calls.last.request.url.params) == {
        "q": "Plane",
        "project_id": "project-1",
        "limit": "5",
    }


@pytest.mark.asyncio
async def test_list_and_read_operations_use_gateway_routes():
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects").mock(
            return_value=httpx.Response(200, json={"items": [{"id": "project-1", "name": "Openclaw"}]})
        )
        router.get("http://gateway.example/v1/workflow/plane/projects/project-1/labels").mock(
            return_value=httpx.Response(200, json={"items": [{"id": "label-1", "name": "tag:codex"}]})
        )
        router.get("http://gateway.example/v1/workflow/plane/projects/project-1/work-items").mock(
            return_value=httpx.Response(200, json={"items": [{"id": "work-item-1", "name": "One"}]})
        )
        router.get(
            "http://gateway.example/v1/workflow/plane/projects/project-1/work-items/work-item-1"
        ).mock(
            return_value=httpx.Response(200, json={"id": "work-item-1", "name": "One"})
        )

        client = PlaneToolClient(AUTH)
        projects = await client.list_projects()
        labels = await client.list_labels("project-1")
        work_items = await client.list_project_work_items(project_id="project-1", limit=10)
        work_item = await client.get_work_item(project_id="project-1", work_item_id="work-item-1")

    assert projects["items"][0]["name"] == "Openclaw"
    assert labels["items"][0]["name"] == "tag:codex"
    assert work_items["items"][0]["id"] == "work-item-1"
    assert work_item["id"] == "work-item-1"


@pytest.mark.asyncio
async def test_create_resolves_todo_state_by_default():
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects/project-1/states").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"id": "state-todo", "name": "Todo", "group": "backlog"}]},
            )
        )
        create_route = router.post(
            "http://gateway.example/v1/workflow/plane/projects/project-1/work-items"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "work-item-1",
                    "name": "[SMOKE][OPN-272] Chat-created ticket",
                    "project_id": "project-1",
                    "state_id": "state-todo",
                    "labels": [],
                },
            )
        )

        result = await PlaneToolClient(AUTH).create_work_item(
            project_id="project-1",
            request=PlaneWorkItemCreateToolRequest(
                name="[SMOKE][OPN-272] Chat-created ticket",
                description_html="<p>Smoke ticket.</p>",
            ),
        )

    assert result["state_id"] == "state-todo"
    assert json.loads(create_route.calls.last.request.content)["state_id"] == "state-todo"


@pytest.mark.asyncio
async def test_create_rejects_ready_for_agent_state():
    client = PlaneToolClient(AUTH)

    with pytest.raises(PlaneToolError, match="must not auto-enter Ready for Agent"):
        await client.create_work_item(
            project_id="project-1",
            request=PlaneWorkItemCreateToolRequest(
                name="Unsafe create",
                state_name="Ready for Agent",
            ),
        )


@pytest.mark.asyncio
async def test_ready_for_agent_requires_explicit_confirmation_and_checklist():
    client = PlaneToolClient(AUTH)

    with pytest.raises(PlaneToolError, match="Ready for Agent requires explicit confirmation"):
        await client.update_work_item(
            project_id="project-1",
            work_item_id="work-item-1",
            request=PlaneWorkItemUpdateToolRequest(state_name="Ready for Agent"),
        )


@pytest.mark.asyncio
async def test_ready_for_agent_update_resolves_state_when_confirmed():
    checklist = (
        "repo:docker label present; acceptance criteria present; verification command listed; "
        "rollback note present"
    )
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects/project-1/states").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"id": "state-ready", "name": "Ready for Agent"}]},
            )
        )
        patch_route = router.patch(
            "http://gateway.example/v1/workflow/plane/projects/project-1/work-items/work-item-1"
        ).mock(
            return_value=httpx.Response(
                200,
                json={"id": "work-item-1", "name": "Ready ticket", "state_id": "state-ready", "labels": []},
            )
        )

        result = await PlaneToolClient(AUTH).update_work_item(
            project_id="project-1",
            work_item_id="work-item-1",
            request=PlaneWorkItemUpdateToolRequest(
                state_name="Ready for Agent",
                ready_for_agent_confirmed=True,
                ready_for_agent_checklist=checklist,
            ),
        )

    assert result["state_id"] == "state-ready"
    assert json.loads(patch_route.calls.last.request.content)["state_id"] == "state-ready"


@pytest.mark.asyncio
async def test_comment_posts_to_explicit_target_work_item():
    with respx.mock(assert_all_called=True) as router:
        route = router.post(
            "http://gateway.example/v1/workflow/plane/projects/project-1/work-items/work-item-1/comments"
        ).mock(
            return_value=httpx.Response(200, json={"id": "comment-1", "comment_html": "<p>Progress</p>"})
        )

        result = await PlaneToolClient(AUTH).add_comment(
            project_id="project-1",
            work_item_id="work-item-1",
            request=PlaneCommentToolRequest(comment_html="<p>Progress</p>"),
        )

    assert result["id"] == "comment-1"
    assert json.loads(route.calls.last.request.content) == {"comment_html": "<p>Progress</p>"}


@pytest.mark.asyncio
async def test_gateway_auth_failure_is_reported_without_secret():
    with respx.mock(assert_all_called=True) as router:
        router.get("http://gateway.example/v1/workflow/plane/projects").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid bearer token"})
        )

        with pytest.raises(PlaneToolError) as exc_info:
            await PlaneToolClient(AUTH).list_projects()

    assert "gateway returned 401" in str(exc_info.value)
    assert "gateway-secret" not in str(exc_info.value)
