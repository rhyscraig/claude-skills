#!/usr/bin/env python3
"""MCP server for Confluence skill."""

import json
import sys
from typing import Any

from skills.confluence import ConfluenceSkill
from skills.confluence.models import (
    SkillConfig,
    ConfluenceConfig,
    DocumentationConfig,
    MetadataConfig,
    JiraConfig,
)


def get_skill_config(repo_path: str = ".") -> SkillConfig:
    """Load skill configuration."""
    confluence = ConfluenceConfig(
        instance_url="https://darkmothcreative.atlassian.net",
        space_key="Engineering",
        auth_token_env="CONFLUENCE_TOKEN"
    )

    documentation = DocumentationConfig(
        space_key="Engineering",
        auto_title=True,
        metadata=MetadataConfig(
            owner="craig",
            audience=["engineers"]
        )
    )

    jira = JiraConfig(
        enabled=True,
        instance_url="https://darkmothcreative.atlassian.net",
        auth_token_env="JIRA_TOKEN",
        default_project="TPC",
        auto_link_related=True,
        create_tasks_for_gaps=True,
    )

    return SkillConfig(
        confluence=confluence,
        documentation=documentation,
        jira=jira
    )


def document_tool(task: str, repo_path: str = ".", doc_type: str = None, dry_run: bool = True) -> dict:
    """Generate documentation using Confluence skill."""
    try:
        config = get_skill_config(repo_path)
        skill = ConfluenceSkill(config)
        result = skill.document(task=task, repo_path=repo_path, doc_type=doc_type, dry_run=dry_run)
        return {
            "success": result.success,
            "title": result.title,
            "document_url": result.document_url,
            "document_id": result.document_id,
            "preview": result.content_preview,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_pages_tool(space_key: str, query: str = "", limit: int = 50) -> dict:
    """Search for pages in Confluence."""
    try:
        config = get_skill_config()
        skill = ConfluenceSkill(config)
        pages = skill.search_pages(space_key, query, limit)
        return {"success": True, "pages": pages, "count": len(pages)}
    except Exception as e:
        return {"success": False, "error": str(e)}


TOOLS = [
    {
        "name": "confluence_document",
        "description": "Generate documentation from code and publish to Confluence. Uses repo's .confluence.yaml for space/Jira bindings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What documentation to generate"},
                "repo_path": {"type": "string", "description": "Repository path (default: '.')", "default": "."},
                "doc_type": {"type": "string", "enum": ["api", "architecture", "runbook", "adr", "feature", "infrastructure", "troubleshooting", "custom"]},
                "dry_run": {"type": "boolean", "description": "Preview without changes (default: true)", "default": True},
            },
            "required": ["task"]
        }
    },
    {
        "name": "confluence_search",
        "description": "Search for pages in a Confluence space",
        "input_schema": {
            "type": "object",
            "properties": {
                "space_key": {"type": "string", "description": "Confluence space key"},
                "query": {"type": "string", "description": "Search query", "default": ""},
                "limit": {"type": "integer", "description": "Max results", "default": 50},
            },
            "required": ["space_key"]
        }
    }
]


if __name__ == "__main__":
    print(json.dumps({"type": "server", "tools": TOOLS}, indent=2))
