import argparse
import asyncio
import json
import os
import sys
from typing import Any

from openclaw_gateway.plane_tools import (
    PlaneCommentToolRequest,
    PlaneToolAuth,
    PlaneToolClient,
    PlaneToolError,
    PlaneWorkItemCreateToolRequest,
    PlaneWorkItemUpdateToolRequest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openclaw-plane-tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("projects")

    states = subparsers.add_parser("states")
    states.add_argument("--project-id", required=True)

    labels = subparsers.add_parser("labels")
    labels.add_argument("--project-id", required=True)

    search = subparsers.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--project-id")
    search.add_argument("--limit", type=int)

    read = subparsers.add_parser("read")
    read.add_argument("--project-id", required=True)
    read.add_argument("--work-item-id", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--project-id", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--description-html")
    create.add_argument("--state-name")
    create.add_argument("--priority")

    update = subparsers.add_parser("update")
    update.add_argument("--project-id", required=True)
    update.add_argument("--work-item-id", required=True)
    update.add_argument("--name")
    update.add_argument("--description-html")
    update.add_argument("--state-name")
    update.add_argument("--priority")
    update.add_argument("--ready-for-agent-confirmed", action="store_true")
    update.add_argument("--ready-for-agent-checklist")

    comment = subparsers.add_parser("comment")
    comment.add_argument("--project-id", required=True)
    comment.add_argument("--work-item-id", required=True)
    comment.add_argument("--comment-html", required=True)

    return parser


async def run(args: argparse.Namespace) -> dict[str, Any]:
    gateway_url = os.environ.get("GATEWAY_URL")
    gateway_token = os.environ.get("GATEWAY_AUTH_TOKEN")
    if not gateway_url or not gateway_token:
        raise PlaneToolError("GATEWAY_URL and GATEWAY_AUTH_TOKEN are required")

    client = PlaneToolClient(PlaneToolAuth(gateway_url=gateway_url, gateway_token=gateway_token))
    if args.command == "projects":
        return await client.list_projects()
    if args.command == "states":
        return await client.list_states(args.project_id)
    if args.command == "labels":
        return await client.list_labels(args.project_id)
    if args.command == "search":
        return await client.search_work_items(query=args.query, project_id=args.project_id, limit=args.limit)
    if args.command == "read":
        return await client.get_work_item(project_id=args.project_id, work_item_id=args.work_item_id)
    if args.command == "create":
        return await client.create_work_item(
            project_id=args.project_id,
            request=PlaneWorkItemCreateToolRequest(
                name=args.name,
                description_html=args.description_html,
                state_name=args.state_name,
                priority=args.priority,
            ),
        )
    if args.command == "update":
        return await client.update_work_item(
            project_id=args.project_id,
            work_item_id=args.work_item_id,
            request=PlaneWorkItemUpdateToolRequest(
                name=args.name,
                description_html=args.description_html,
                state_name=args.state_name,
                priority=args.priority,
                ready_for_agent_confirmed=args.ready_for_agent_confirmed,
                ready_for_agent_checklist=args.ready_for_agent_checklist,
            ),
        )
    if args.command == "comment":
        return await client.add_comment(
            project_id=args.project_id,
            work_item_id=args.work_item_id,
            request=PlaneCommentToolRequest(comment_html=args.comment_html),
        )
    raise PlaneToolError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except PlaneToolError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
