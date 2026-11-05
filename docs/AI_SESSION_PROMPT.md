# AI Session Starter Prompt

Copy and paste the template below into ChatGPT, Claude, Gemini, or any other AI assistant at the start of every coding session.

```markdown
I am <NAME: Sudhansu | Pratyush>.

Before writing any code:
1. Read AGENTS.md, shared/contracts.py, docs/api_contracts.md, and the files you will modify first.
2. Only modify my folders (Sudhansu: backend/, ai_engine/; Pratyush: frontend/, doc_engine/, graph_engine/) plus tests/ and docs/.
3. Do not change shared/contracts.py or any public engine function signatures.
4. Use only libraries listed in the approved tech stack in AGENTS.md.
5. Use raw parameterized SQL with %s only (no SQLAlchemy, no ORMs, no f-string SQL).
6. Provide complete, runnable files alongside corresponding pytest unit tests.
7. If my request conflicts with AGENTS.md, tell me immediately instead of complying.

My task now: <TASK>
```

---

## 3 Session Tips for Working with AI Agents
1. **One Task Per Session**: Break work down into small, single-purpose tasks. Do not ask an AI to build an entire subsystem in one prompt.
2. **Halt on Contract Suggestions**: If the AI suggests modifying `shared/contracts.py` or renaming fields to solve a problem, STOP. Check if the task can be completed using the existing contract models first.
3. **Run Pre-Push Verification**: Before committing or pushing code, ask the AI: *"Check the proposed git diff against the 6 checkboxes in AGENTS.md Section 8 and verify all pytest tests pass."*

