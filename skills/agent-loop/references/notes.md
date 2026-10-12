# Notes — agent-loop

Interpretation rules for the phase state machine. Keep this short; load only when the engine's behaviour needs explaining.

## Phase order is enforced

`PHASES` = `bootstrap_agent, perceive, goal_contract, policy_check, capability_discovery, plan, execute_loop`.
`advance` always completes the *current* phase and moves to the next one. There is no way to select a phase directly, so out-of-order execution is impossible by construction.

## Gates

| Phase being completed | Requirement | Who provides it |
| --------------------- | ----------- | --------------- |
| `perceive` | `note` >= 10 chars | model |
| `goal_contract` | >= 1 `criteria` | model |
| `policy_check` | >= 1 rule loaded from AGENTS.md | engine (`load_policy`) |
| `capability_discovery` | >= 1 discoverable skill | engine (`discover`) |
| `plan` | >= 1 `todos` | model |
| `execute_loop` | `note` >= 10 chars | model |

A blocked transition returns `{"ok": false, "phase": ..., "missing": [...]}` and exits 1. Nothing is written to the run record, so retrying is safe and idempotent.

## What the engine resolves on its own

- `load_policy` reads `~/.config/opencode/AGENTS.md` plus `AGENTS.md` from the working directory up to the filesystem root, and extracts every `- ` bullet as a rule (capped at 40 in the result).
- `discover` scans the filesystem only (`~/.config/opencode/skills`, `~/.agents/skills`, `~/.claude/skills`, and the project equivalents, plus `agent/` and `command/` dirs). No network, no credentials, no MCP.
- Deduplication keeps the first id seen, so higher-precedence directories win.

## State file

`<dir>/.agent-loop/<run>.json` — fields: `id`, `task`, `created`, `updated`, `phase`, `completed`, `criteria`, `todos`, `policy`, `capabilities`, `history`.
Run ids are `<UTC timestamp>-<random hex>-<task slug>`; two runs in the same second do not collide.
`status` without a `run` lists the ids present.

## Resuming

Read `status` first: `phase` is the phase in progress and `gate` says what is still needed. If a run is stale, start a new one — never hand-edit the JSON, it is the audit trail.

## Limits

- Discovery reflects the filesystem at call time; a newly installed skill is visible on the next call, no restart needed.
- `dir` is resolved as given; pass an OS-native path (or omit it for the current directory).
- The engine never calls a model or a network service. Anything requiring judgement stays with the model.
