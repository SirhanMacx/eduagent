# v2.3.4 Pipeline Fix — Make Search + Generation Actually Work

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken search-to-generation pipeline so the bot surfaces teacher's existing materials and generates lessons grounded in their prior work.

**Architecture:** The bot's ingestion path (`handlers/ingest.py`) indexes KB chunks but skips asset registration, making 8,437 files invisible to the asset search. The agent system prompt doesn't enforce search-before-generate. Two Pydantic models crash on LLM output. Images are irrelevant. This plan fixes all 8 bugs in priority order with atomic commits.

**Tech Stack:** Python 3.10+, Pydantic v2, SQLite, httpx, python-pptx, python-docx

---

### Task 1: Add asset registration to bot ingestion path

**Files:**
- Modify: `clawed/handlers/ingest.py:98` (after KB indexing block)
- Modify: `clawed/agent_core/tools/ingest_materials.py:130` (after KB indexing block)

- [ ] **Step 1: Add asset registration to handlers/ingest.py**

After line 98 (after the KB indexing try/except block), add:

```python
            # Register assets (files, images, YouTube links) for search
            try:
                from clawed.asset_registry import AssetRegistry
                registry = AssetRegistry()
                asset_count = 0
                for doc in documents:
                    doc_type_val = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
                    extraction = None
                    if doc.source_path:
                        try:
                            from clawed.ingestor import extract_rich
                            extraction = extract_rich(Path(doc.source_path))
                        except Exception:
                            pass
                    aid = registry.register_asset(
                        teacher_id=teacher_id,
                        source_path=doc.source_path or "",
                        title=doc.title,
                        doc_type=doc_type_val,
                        text=doc.content,
                        extraction=extraction,
                    )
                    if aid:
                        asset_count += 1
                if asset_count:
                    kb_info += f" ({asset_count} files catalogued with images and links)"
            except Exception as e:
                logger.debug("Asset registration skipped: %s", e)
```

- [ ] **Step 2: Add asset registration to tools/ingest_materials.py**

After line 130 (after KB indexing try/except), add:

```python
            # Register assets for file-level search
            try:
                from clawed.asset_registry import AssetRegistry
                registry = AssetRegistry()
                asset_count = 0
                for doc in docs:
                    doc_type_val = (
                        doc.doc_type.value
                        if hasattr(doc.doc_type, "value")
                        else str(doc.doc_type)
                    )
                    extraction = None
                    if doc.source_path:
                        try:
                            from clawed.ingestor import extract_rich
                            extraction = extract_rich(Path(doc.source_path))
                        except Exception:
                            pass
                    aid = registry.register_asset(
                        teacher_id=context.teacher_id,
                        source_path=doc.source_path or "",
                        title=doc.title,
                        doc_type=doc_type_val,
                        text=doc.content,
                        extraction=extraction,
                    )
                    if aid:
                        asset_count += 1
                if asset_count:
                    summary += f" ({asset_count} files catalogued for search)"
            except Exception as e:
                logger.debug("Asset registration failed: %s", e)
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 4: Commit**

```bash
git add clawed/handlers/ingest.py clawed/agent_core/tools/ingest_materials.py
git commit -m "fix: add asset registration to bot/tool ingestion paths

Bot and tool ingestion paths indexed KB chunks but skipped
AssetRegistry.register_asset(), making files invisible to
search_my_materials. Now both paths register assets with
rich extraction (images, YouTube links, metadata)."
```

---

### Task 2: Enforce search-before-generate in agent system prompt

**Files:**
- Modify: `clawed/agent_core/prompt.py:84-102` (How you work section)
- Modify: `clawed/agent_core/tools/generate_lesson_bundle.py:25-26` (tool description)

- [ ] **Step 1: Update behavioral rules in prompt.py**

Replace lines 85-102 with:

```python
        "\n## How you work\n"
        "0. **Narrate before acting** — before calling any tool that takes time "
        "(generate_lesson_bundle, ingest_materials), tell the teacher what you're "
        "about to do in 1-2 sentences. Examples:\n"
        "  'Let me read through your files — this might take a minute.'\n"
        "  'Building your lesson package now — plan, handout, and slides coming up.'\n"
        "The teacher should always know you're working, not stuck.\n"
        "1. Read SOUL.md to know your voice and values\n"
        "2. **MANDATORY: Before calling generate_lesson_bundle, ALWAYS call "
        "search_my_materials first** with the lesson topic. This is non-negotiable. "
        "The teacher has uploaded materials — if you skip this step, you will "
        "generate generic content instead of building on their prior work. "
        "Tell the teacher what you found before generating.\n"
        "3. Generate complete packages (lesson plan + student handout + slideshow) "
        "using generate_lesson_bundle\n"
        "4. Never ask 'want me to create materials?' -- just create them\n"
        "5. After completing a task, suggest 1-2 next steps\n"
        "6. Update SOUL.md when you learn something new about the teacher "
        "(use update_soul tool)\n"
        "7. Give brief status updates while working on multi-step tasks"
    )
```

- [ ] **Step 2: Add cross-reference to generate_lesson_bundle tool description**

In `clawed/agent_core/tools/generate_lesson_bundle.py`, replace the tool description (lines 25-28):

```python
                "description": (
                    "Generate a COMPLETE teaching package for a topic: "
                    "a lesson plan (DOCX), a student handout (DOCX), and "
                    "a slideshow (PPTX). All three files are created at once. "
                    "IMPORTANT: Always call search_my_materials FIRST to find "
                    "the teacher's existing materials on this topic before "
                    "calling this tool."
                ),
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 4: Commit**

```bash
git add clawed/agent_core/prompt.py clawed/agent_core/tools/generate_lesson_bundle.py
git commit -m "fix: enforce search-before-generate in agent behavioral rules

Adopted Hermes Agent pattern: made search_my_materials MANDATORY
before generate_lesson_bundle in system prompt behavioral rules.
Added cross-reference in tool description so model sees the
instruction at decision time."
```

---

### Task 3: Fix Pydantic type coercion for SubPacket and WorksheetItem

**Files:**
- Modify: `clawed/sub_packet.py:40` (student_notes field)
- Modify: `clawed/models.py:489,500,674` (point_value fields)

- [ ] **Step 1: Fix SubPacket.student_notes — accept list or str**

In `clawed/sub_packet.py`, add a validator after the `student_notes` field (after line 40):

```python
    student_notes: str = ""

    @field_validator("student_notes", mode="before")
    @classmethod
    def _coerce_student_notes(cls, v):
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return v
```

Ensure `field_validator` is imported (check existing imports at top of file).

- [ ] **Step 2: Fix WorksheetItem.point_value — parse int from decorated strings**

In `clawed/models.py`, add a validator to `WorksheetItem` after the `point_value` field (line 489):

```python
    point_value: int = 1

    @field_validator("point_value", mode="before")
    @classmethod
    def _coerce_point_value(cls, v):
        if isinstance(v, str):
            import re
            match = re.match(r"(\d+)", v.strip())
            return int(match.group(1)) if match else 1
        return v
```

Apply the same validator to `AssessmentQuestion.point_value` (line 500) and the other `point_value` field at line 674. Use the same code — add the `_coerce_point_value` validator to each class.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 4: Commit**

```bash
git add clawed/sub_packet.py clawed/models.py
git commit -m "fix: coerce LLM output types for SubPacket and WorksheetItem

SubPacket.student_notes now accepts list[str] (joins with newlines).
WorksheetItem/AssessmentQuestion.point_value now parses leading int
from decorated strings like '5 (1+2+2)'. Both caused ValidationError
with minimax-m2.7:cloud which returns richer-than-expected data."
```

---

### Task 4: Fix persona name — use identity.md, not LLM inference

**Files:**
- Modify: `clawed/persona.py` (persona extraction — find where name is set)
- Modify: `clawed/commands/generate.py` (ingest command — set name from identity after extraction)

- [ ] **Step 1: Find and fix persona name source**

In the persona extraction flow, after the LLM returns a persona, override the name with the teacher's configured name from identity.md or AppConfig:

In `clawed/commands/generate.py`, after `persona = await extract_persona(documents, config)` and before `save_persona()`, add:

```python
        # Override LLM-inferred name with configured teacher name
        try:
            from clawed.models import AppConfig
            cfg = AppConfig.load()
            if cfg.teacher_profile and cfg.teacher_profile.name:
                persona.name = f"{cfg.teacher_profile.name} Teaching Persona"
        except Exception:
            pass
        # Also check identity.md
        try:
            identity_path = Path.home() / ".eduagent" / "workspace" / "identity.md"
            if identity_path.exists():
                content = identity_path.read_text(encoding="utf-8")
                import re
                name_match = re.match(r"^#\s+(.+)", content)
                if name_match:
                    teacher_name = name_match.group(1).strip()
                    if teacher_name and teacher_name != "Teacher":
                        persona.name = f"{teacher_name} Teaching Persona"
        except Exception:
            pass
```

Apply the same pattern in `clawed/handlers/ingest.py` after `extract_persona` and in `clawed/agent_core/tools/ingest_materials.py` after persona extraction.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 3: Commit**

```bash
git add clawed/commands/generate.py clawed/handlers/ingest.py clawed/agent_core/tools/ingest_materials.py
git commit -m "fix: use configured teacher name instead of LLM-inferred persona name

LLM persona extraction picked up colleague names from shared
materials (e.g., 'Mr. Maue' instead of 'Mr. Mac'). Now overrides
with name from AppConfig.teacher_profile or identity.md header."
```

---

### Task 5: Fix image relevance — raise threshold, remove generic fallbacks

**Files:**
- Modify: `clawed/slide_images.py:544` (raise minimum score)
- Modify: `clawed/slide_images.py:259-265` (remove unsplash from fallback chain)
- Modify: `clawed/slide_images.py:506` (add topic filter to SQL)

- [ ] **Step 1: Raise teacher image minimum score from 2 to 6**

In `clawed/slide_images.py`, change line 544:

```python
        # Require minimum score of 6 (exact phrase match or 3+ keyword hits)
        if best_path and best_score >= 6 and Path(best_path).exists():
```

- [ ] **Step 2: Remove Unsplash from all source chains**

Replace `_select_sources` (lines 251-265):

```python
def _select_sources(subject: str, topic: str = "") -> list[str]:
    """Pick the best image sources for this subject.

    Returns an ordered list of source identifiers to try.
    Teacher's own images are always checked first.
    Only uses academic sources (LOC, Wikimedia). No stock photos.
    """
    subject_lower = subject.strip().lower()
    if any(s in subject_lower for s in ("history", "social", "civics", "government")):
        return ["teacher_files", "loc", "wikimedia"]
    elif any(s in subject_lower for s in ("science", "biology", "chemistry", "physics")):
        return ["teacher_files", "wikimedia", "loc"]
    elif any(s in subject_lower for s in ("art", "music")):
        return ["teacher_files", "wikimedia", "loc"]
    else:
        return ["teacher_files", "loc", "wikimedia"]
```

- [ ] **Step 3: Add topic keyword filter to teacher image SQL query**

In `_fetch_teacher_image`, replace the SQL at line 501-507:

```python
            # Pre-filter by topic keywords in SQL for efficiency
            where_clauses = " OR ".join(
                f"(ai.context_text LIKE '%{kw}%' OR a.title LIKE '%{kw}%')"
                for kw in keywords[:5]
            )
            rows = conn.execute(
                f"SELECT ai.image_path, ai.context_text, a.title "
                f"FROM asset_images ai "
                f"JOIN assets a ON ai.asset_id = a.id "
                f"WHERE ai.image_path != '' AND ({where_clauses}) "
                f"LIMIT 100",
            ).fetchall()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 5: Commit**

```bash
git add clawed/slide_images.py
git commit -m "fix: raise image relevance threshold and remove stock photo fallback

Teacher image minimum score raised from 2 to 6 (requires exact
phrase or 3+ keywords). Removed Unsplash from all source chains
(stock photos are never relevant to lessons). Added SQL WHERE
filter to teacher image lookup for efficiency."
```

---

### Task 6: Wire teacher_materials into lesson generation

**Files:**
- Modify: `clawed/commands/generate.py` (CLI lesson command — search corpus before generating)

- [ ] **Step 1: Find the CLI lesson generation path**

In `clawed/commands/generate.py`, find where `generate_lesson()` is called for the `lesson` CLI command. Before that call, add asset + KB search:

```python
        # Search for teacher's existing materials on this topic
        teacher_materials = ""
        try:
            from clawed.asset_registry import AssetRegistry
            registry = AssetRegistry()
            assets = registry.search_assets("default", topic, top_k=5)
            yt_links = registry.get_youtube_links("default", topic, top_k=3)
            if assets or yt_links:
                teacher_materials = registry.format_asset_summary(assets, yt_links)
                for a in assets:
                    type_label = a["material_type"].replace("_", " ").title()
                    console.print(f"Found [{type_label}] \"{a['title']}\"")
                for link in yt_links:
                    console.print(f"Found YouTube: {link['url']}")
        except Exception:
            pass

        try:
            from clawed.agent_core.memory.curriculum_kb import CurriculumKB
            kb = CurriculumKB()
            kb_results = kb.search("default", topic, top_k=3)
            if kb_results:
                chunks = [r for r in kb_results if r.get("similarity", 0) > 0.1]
                if chunks:
                    chunk_text = "\n\n".join(
                        f"From \"{r['doc_title']}\":\n{r['chunk_text'][:500]}"
                        for r in chunks
                    )
                    if teacher_materials:
                        teacher_materials += "\n\n" + chunk_text
                    else:
                        teacher_materials = chunk_text
        except Exception:
            pass
```

Then pass `teacher_materials=teacher_materials` to the `generate_lesson()` call.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 3: Commit**

```bash
git add clawed/commands/generate.py
git commit -m "feat: CLI lesson generation now searches teacher's corpus first

The lesson command now searches AssetRegistry and CurriculumKB
before generating, passing found materials to the LLM prompt
via the teacher_materials parameter. Prints Found [Type] messages
to show which prior work is being referenced."
```

---

### Task 7: Wire record_ingestion_changes into ingest flow

**Files:**
- Modify: `clawed/commands/generate.py` (CLI ingest — after persona extraction)

- [ ] **Step 1: Add persona evolution tracking**

After persona extraction and save in the CLI ingest command, add:

```python
        # Track persona changes for evolution
        try:
            from clawed.persona_evolution import record_ingestion_changes
            record_ingestion_changes(old_persona=None, new_persona=persona)
        except Exception:
            pass
```

- [ ] **Step 2: Commit**

```bash
git add clawed/commands/generate.py
git commit -m "feat: wire record_ingestion_changes into CLI ingest flow

Persona evolution now tracks changes when new files are ingested,
comparing old and new persona to record candidates for review."
```

---

### Task 8: Version bump, ruff check, full test suite

**Files:**
- Modify: `pyproject.toml` (version bump to 2.3.4)
- Modify: `clawed/__init__.py` (if version is defined there)

- [ ] **Step 1: Bump version to 2.3.4**

Update `pyproject.toml`:
```
version = "2.3.4"
```

Update `clawed/__init__.py` if it has `__version__`.

- [ ] **Step 2: Run ruff check**

Run: `ruff check .`
Fix any issues found.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -q 2>&1 | tail -10`
Expected: All tests pass (1445+ passed)

- [ ] **Step 4: Commit, push, publish**

```bash
git add -A
git commit -m "chore: bump version to v2.3.4 — pipeline fix release

Fixes: bot asset registration, search-before-generate enforcement,
Pydantic type coercion, persona name, image relevance, teacher
materials injection, persona evolution tracking."

git push origin main
python -m build
twine upload dist/clawed-2.3.4*
```
