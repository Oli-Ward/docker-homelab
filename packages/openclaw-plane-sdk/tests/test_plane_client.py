import json

import httpx
import pytest
import respx

from openclaw_plane_sdk import PlaneApiError, PlaneClient, PlaneResponseError
from openclaw_plane_sdk.models import (
    PlaneCommentCreate,
    PlaneWorkItemCreate,
    PlaneWorkItemUpdate,
)


def make_client() -> PlaneClient:
    return PlaneClient(
        base_url="http://plane:8085",
        api_key="plane-secret",
        workspace_slug="openclaw",
        timeout_seconds=5.0,
    )


@pytest.mark.asyncio
@respx.mock
async def test_plane_search_work_items_sends_api_key_and_query_params():
    route = respx.get("http://plane:8085/api/v1/workspaces/openclaw/work-items/search/").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "work-item-1",
                        "name": "Wire Plane adapter",
                        "sequence_id": 264,
                        "project_id": "project-1",
                        "state_id": "state-started",
                        "priority": "medium",
                        "labels": [{"id": "label-openclaw", "name": "openclaw"}],
                    }
                ]
            },
        )
    )

    result = await make_client().search_work_items(
        query="Plane adapter",
        project_id="project-1",
        limit=5,
    )

    request = route.calls.last.request
    assert request.headers["X-API-Key"] == "plane-secret"
    assert request.url.params["search"] == "Plane adapter"
    assert request.url.params["project_id"] == "project-1"
    assert request.url.params["limit"] == "5"
    assert result.items[0].id == "work-item-1"
    assert result.items[0].name == "Wire Plane adapter"
    assert result.items[0].sequence_id == 264
    assert result.items[0].labels[0].name == "openclaw"


@pytest.mark.asyncio
@respx.mock
async def test_plane_list_project_work_items_handles_list_payload():
    route = respx.get(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/work-items/"
    ).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "work-item-1",
                    "name": "Imported ticket",
                    "sequence_id": 10,
                    "project_id": "project-1",
                }
            ],
        )
    )

    result = await make_client().list_project_work_items(project_id="project-1", limit=20)

    assert route.called
    assert route.calls.last.request.url.params["per_page"] == "20"
    assert result.items[0].id == "work-item-1"
    assert result.items[0].name == "Imported ticket"


@pytest.mark.asyncio
@respx.mock
async def test_plane_list_labels_uses_project_labels_endpoint():
    route = respx.get(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/labels/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "label-openclaw",
                        "name": "openclaw",
                    }
                ]
            },
        )
    )

    result = await make_client().list_labels(project_id="project-1")

    assert route.called
    assert route.calls.last.request.headers["X-API-Key"] == "plane-secret"
    assert result.items[0].id == "label-openclaw"
    assert result.items[0].name == "openclaw"


@pytest.mark.asyncio
@respx.mock
async def test_plane_create_work_item_posts_narrow_payload():
    route = respx.post(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/work-items/"
    ).mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "work-item-2",
                "name": "Created from OpenClaw",
                "sequence_id": 11,
                "project_id": "project-1",
                "state_id": "state-todo",
            },
        )
    )

    result = await make_client().create_work_item(
        project_id="project-1",
        work_item=PlaneWorkItemCreate(
            name="Created from OpenClaw",
            description_html="<p>Created by gateway test</p>",
            state_id="state-todo",
            label_ids=["label-openclaw"],
        ),
    )

    request = route.calls.last.request
    assert request.headers["X-API-Key"] == "plane-secret"
    assert json.loads(request.read()) == {
        "name": "Created from OpenClaw",
        "description_html": "<p>Created by gateway test</p>",
        "state": "state-todo",
        "label_ids": ["label-openclaw"],
    }
    assert result.id == "work-item-2"
    assert result.name == "Created from OpenClaw"


@pytest.mark.asyncio
@respx.mock
async def test_plane_create_work_item_omits_unset_optional_fields():
    route = respx.post(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/work-items/"
    ).mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "work-item-3",
                "name": "Created with defaults",
                "sequence_id": 12,
                "project_id": "project-1",
                "state_id": "state-todo",
            },
        )
    )

    result = await make_client().create_work_item(
        project_id="project-1",
        work_item=PlaneWorkItemCreate(
            name="Created with defaults",
            state_id="state-todo",
        ),
    )

    assert json.loads(route.calls.last.request.read()) == {
        "name": "Created with defaults",
        "state": "state-todo",
    }
    assert result.id == "work-item-3"


@pytest.mark.asyncio
@respx.mock
async def test_plane_update_work_item_patches_only_set_fields():
    route = respx.patch(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/work-items/work-item-2/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"id": "work-item-2", "name": "Updated", "project_id": "project-1"},
        )
    )

    result = await make_client().update_work_item(
        project_id="project-1",
        work_item_id="work-item-2",
        update=PlaneWorkItemUpdate(name="Updated"),
    )

    assert route.calls.last.request.read() == b'{"name":"Updated"}'
    assert result.name == "Updated"


@pytest.mark.asyncio
@respx.mock
async def test_plane_update_work_item_serializes_state_id_as_plane_state_field():
    route = respx.patch(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/work-items/work-item-2/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"id": "work-item-2", "name": "Blocked", "project_id": "project-1", "state": "state-needs-input"},
        )
    )

    result = await make_client().update_work_item(
        project_id="project-1",
        work_item_id="work-item-2",
        update=PlaneWorkItemUpdate(state_id="state-needs-input"),
    )

    assert route.calls.last.request.read() == b'{"state":"state-needs-input"}'
    assert result.state_id == "state-needs-input"


@pytest.mark.asyncio
@respx.mock
async def test_plane_add_comment_posts_comment_html():
    route = respx.post(
        "http://plane:8085/api/v1/workspaces/openclaw/projects/project-1/work-items/work-item-2/comments/"
    ).mock(
        return_value=httpx.Response(
            201,
            json={"id": "comment-1", "comment_html": "<p>Progress update</p>"},
        )
    )

    result = await make_client().add_comment(
        project_id="project-1",
        work_item_id="work-item-2",
        comment=PlaneCommentCreate(comment_html="<p>Progress update</p>"),
    )

    assert route.calls.last.request.read() == b'{"comment_html":"<p>Progress update</p>"}'
    assert result.id == "comment-1"
    assert result.comment_html == "<p>Progress update</p>"


@pytest.mark.asyncio
@respx.mock
async def test_plane_client_maps_empty_success_response_to_predictable_error():
    respx.get("http://plane:8085/api/v1/workspaces/openclaw/projects/").mock(
        return_value=httpx.Response(200, content=b"")
    )

    with pytest.raises(PlaneResponseError, match="empty response"):
        await make_client().list_projects()


@pytest.mark.asyncio
@respx.mock
async def test_plane_client_maps_invalid_json_response_to_predictable_error():
    respx.get("http://plane:8085/api/v1/workspaces/openclaw/projects/").mock(
        return_value=httpx.Response(200, content=b"not-json")
    )

    with pytest.raises(PlaneResponseError, match="invalid json"):
        await make_client().list_projects()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("status_code", "expected_kind"),
    [
        (401, "auth"),
        (403, "auth"),
        (404, "not_found"),
        (429, "rate_limited"),
        (500, "server"),
    ],
)
async def test_plane_client_maps_status_errors_to_predictable_error(status_code, expected_kind):
    respx.get("http://plane:8085/api/v1/workspaces/openclaw/projects/").mock(
        return_value=httpx.Response(
            status_code,
            json={"detail": "upstream body must not leak plane-secret"},
        )
    )

    with pytest.raises(PlaneApiError) as exc_info:
        await make_client().list_projects()

    assert exc_info.value.status_code == status_code
    assert exc_info.value.kind == expected_kind
    assert "plane-secret" not in str(exc_info.value)
