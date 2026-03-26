"""Tool: search_my_materials — search the teacher's uploaded curriculum files.

This is the key tool that makes Claw-ED curriculum-aware. The agent calls
this before generating to find relevant prior work in the teacher's own
uploaded materials.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


class SearchMyMaterialsTool:
    """Search the teacher's curriculum knowledge base for relevant content."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_my_materials",
                "description": (
                    "Search the teacher's uploaded curriculum files for relevant "
                    "content. Use this BEFORE generating lessons, units, or materials "
                    "to ground your output in the teacher's own prior work. Returns "
                    "matching excerpts with source file attribution."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "What to search for — a topic, concept, or question. "
                                "Example: 'Civil War causes', 'photosynthesis lab', "
                                "'fractions worksheet'"
                            ),
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum results to return (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        from clawed.agent_core.memory.curriculum_kb import CurriculumKB

        query = params["query"]
        top_k = params.get("top_k", 5)
        teacher_id = context.teacher_id

        try:
            kb = CurriculumKB()
            results = kb.search(teacher_id, query, top_k=top_k)

            if not results:
                stats = kb.stats(teacher_id)
                if stats["doc_count"] == 0:
                    return ToolResult(
                        text="No curriculum files uploaded yet. Ask the teacher "
                             "to share their lesson plans, handouts, or other "
                             "teaching materials so you can reference them."
                    )
                return ToolResult(
                    text=f"No matches found for '{query}' in "
                         f"{stats['doc_count']} uploaded documents."
                )

            lines = [f"Found {len(results)} relevant excerpts from your files:\n"]
            for i, r in enumerate(results, 1):
                source = r["doc_title"]
                if r.get("source_path"):
                    fname = Path(r["source_path"]).name
                    source = f"{r['doc_title']} ({fname})"
                sim_pct = int(r["similarity"] * 100)
                text_preview = r["chunk_text"][:300]
                if len(r["chunk_text"]) > 300:
                    text_preview += "..."
                lines.append(
                    f"**{i}. From '{source}'** ({sim_pct}% match):\n"
                    f"{text_preview}\n"
                )

            return ToolResult(
                text="\n".join(lines),
                data={"results": results, "query": query},
            )
        except Exception as e:
            return ToolResult(text=f"Failed to search curriculum files: {e}")
