# Repo Research Findings — Features to Borrow for EDUagent

## PicoClaw (25K stars) — sipeed/picoclaw
Key patterns to borrow:
- **Sub-agent spawn_status query** — teachers can spawn a "generate full unit" background task and query its status
- **Channel auto-orchestration** — route teacher messages to the right skill automatically
- **MCP protocol support** — EDUagent as an MCP server, tools other agents can call
- **System tray UI** — desktop app mode for teachers who prefer GUI over terminal
- **Model routing** — auto-select best model per task (fast model for quick Q&A, better model for lesson generation)
- **JSONL memory store** — simple, portable memory format for teacher sessions

## ClawVault (617 stars) — Versatly/clawvault
"An elephant never forgets. Structured memory system for AI agents."
Key patterns:
- **Structured memory with TTL** — remember teacher preferences, frequently generated topics, student names
- **Memory namespacing** — teacher memory vs. student memory vs. class memory
- **Memory search** — "what did I teach about the civil war last semester?" → retrieve relevant past lessons

## karpathy/autoresearch (51K stars)
Key patterns:
- **Self-improving research loop** — EDUagent can iteratively improve its lesson generation by running experiments
- **Single-GPU friendly** — teaches us to keep the architecture lean
- **Autonomous iteration** — generate → evaluate → improve, no human in the loop

## ClawBio (490 stars) — ClawBio/ClawBio
"Domain-specific AI agent skill library. Local-first."
Key patterns:
- **Domain skill library** — subject-specific skills (Social Studies, Math, Science, ELA) with curated prompts
- **Local-first architecture** — teacher data stays on device
- **Reproducibility** — same inputs = same outputs (important for testing curriculum quality)

## microclaw (591 stars) — microclaw/microclaw
"Agentic AI assistant that lives in your chats"
Key patterns:
- **Chat-native design** — built for messaging apps first, not web apps
- **Rust performance** — consider a lightweight Rust worker for high-throughput schools

## Key Features to Build (from research):

1. **MCP server** — expose EDUagent tools as MCP endpoints so OpenClaw and other agents can call them
2. **Structured memory with search** — teacher's lesson history, student interaction logs, curriculum knowledge base
3. **Model routing** — use fast model (qwen3.5) for quick answers, strong model (minimax-m2.7) for lesson generation
4. **Self-improvement loop** — autoresearch pattern: generate lesson → teacher rates it → system learns → generates better next time
5. **Subject skill library** — curated prompt packs per subject (Social Studies, Math, Science, ELA, etc.)
6. **Background task queue** — teachers can say "generate all 10 lessons for my WWI unit tonight" and check back later
7. **Memory namespacing** — teacher/ student/ class/ school/ district scopes
