# AI Working Directory

This folder tracks ongoing Context Engineering Workflow activity for FormatIQ.

## Structure
- `feature-<slug>/`
  - `research/analysis.md` → entry points, code relationships, risks
  - `plan.md` → step-by-step plan with rollback + edge cases
  - `implementation.md` → live compactions (hourly status)

## Usage
1. **Start with Research**
   - Identify files, relationships, risks.
   - Always link frontend ↔ backend ↔ tests.

2. **Create a Plan**
   - Ordered steps, expected outcomes, rollback.
   - Record edge cases + tests.

3. **Implement with Compactions**
   - Update progress every 20 minutes or when user requests.
   - Use `/prompts/.templates/compaction.md`.

## Cadence
- Day 1: only compactions.
- Day 2: add research + plan.
- Repeat loop for each feature.

## Rotation
- At the end of each week:
  - Roll up `implementation.md` compactions into `summary.md`.
  - Archive old notes under `/archive/` to keep context small.

## Agents
- **Root `AGENTS.md`** defines repo-wide build/test rules.
- **Nested `AGENTS.md`** in frontend/backend override specifics.
- Many agents (Codex, Gemini, Aider) read these automatically.

