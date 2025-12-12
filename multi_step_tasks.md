# Multi-step task handling ideas

Goal: allow the CLI to handle small multi-step requests (e.g., "what is the largest file in this folder") with a bounded step budget and graceful fallback.

## CLI knobs
- `--steps` / `--max-steps` (default: 3) to limit the number of tool uses/iterations.
- Optional `--verbose` to stream intermediate steps/tool outputs; default stays quiet for quick UX.

## Enforcement approach
- Wrap `agent.run()` with a thin driver that counts tool calls/assistant turns; stop when:
  - Final content is produced, or
  - Step budget is reached → emit concise refusal: "Didn’t finish within N steps. Try: …".
- If Agno exposes `max_loops`/step limits, use it; otherwise, intercept tool invocations and cap.

## Prompt shaping
- Inject the budget: "You may take up to N steps (tool uses or reasoning turns). If you reach N without an answer, respond: 'I don’t have enough information within N steps. Try: …'."
- Encourage minimal steps: "Prefer the smallest number of steps; avoid unnecessary re-checks."
- Keep instructions concise to control cost.

## Behavioral guidelines
- Order: gather → decide → answer. Example for "largest file":
  1) List files with sizes (`du -sh *` or `ls -l`).
  2) Pick the max from the output.
  3) Reply with filename and size.
- On tool failure or ambiguity, spend one step to report and suggest a manual command.

## Output UX
- Default: only final answer. Use `--verbose` to show intermediate steps/tool outputs.
- Refusal style: short, actionable. Example: "Couldn’t identify largest file within 3 steps. Try rerunning with `--steps 5` or run `du -sh * | sort -h`."

## Integration sketch
- CLI adds `--steps` int; pass to an agent driver.
- Driver loop counts tool calls/messages and enforces budget.
- Prompt includes the budget hint and graceful refusal instruction.
- Tools: keep shell/fs tools enabled; rely on blocklist-based policy later for safety.
