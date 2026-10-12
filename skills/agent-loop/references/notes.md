# Notes — agent-loop

Interpretation rules for the phase state machine. Keep this short; load only when the engine's behaviour needs explaining.

## Phase order is enforced

`PHASES` = `bootstrap_agent, perceive, goal_contract, policy_check, capability_discovery, plan, execute_loop`.
`advance` always completes the *current* phase and moves to the next one. There is no way to select a phase directly, so out-of-order execution is impossible by construction.

## Gates

| Phase being completed | Requirement | Who provides it |
| --------------------- | ----------- | --------------- |
| `perceive` | `note` >= 10 chars | model |
| `goal_contract` | >= 1 `criteria` (accepted only in this phase) | model |
| `policy_check` | >= 1 rule loaded from AGENTS.md | engine (`load_policy`) |
| `capability_discovery` | >= 1 capability and the `note` names one discovered id | engine (`discover`) + model |
| `plan` | >= 1 `todos` (accepted only in this phase) | model |
| `execute_loop` | `note` >= 10 chars | model |

`criteria` and `todos` are phase-scoped: sending them while completing any other phase is rejected, so a gate can never be satisfied by pre-filling at `start`.

A blocked transition returns `{"ok": false, "phase": ..., "missing": [...], "blocked_attempts": n}` and exits 1. The attempt is appended to `history` with `"blocked": true` so the audit trail shows how many times a gate fired; the run does not advance and nothing is lost by retrying.

## What the engine resolves on its own

- `load_policy` reads `~/.config/opencode/AGENTS.md` plus `AGENTS.md` from the working directory up to the filesystem root, and extracts every `- ` bullet as a rule (capped at 40 in the result). Unreadable files are skipped.
- `discover` scans the filesystem only. Skills come from `.opencode/skills`, `.agents/skills`, `.claude/skills` (project) then the same three under `$HOME`; agents and commands come from `.opencode/<kind>` then `~/.config/opencode/<kind>`. A flat `*.md` at a source root counts as a skill **only if it has frontmatter**, so a stray `README.md` is ignored.
- Project directories are listed before `$HOME`, and first id seen wins — matching OpenCode's own precedence, so a project skill shadows a global one with the same id.
- No network, no credentials, no MCP.

## State file

`<dir>/.agent-loop/<run>.json` — fields: `id`, `task`, `created`, `updated`, `phase`, `completed`, `criteria`, `todos`, `policy`, `capabilities`, `blocked`, `history`, plus `finished` once the run completes.
Run ids are `<UTC timestamp>-<random hex>-<task slug>`; two runs in the same second do not collide.
Writes are atomic (`os.replace` over a `.json.tmp`) and `advance` takes a `.lock` file, so a crash or a concurrent call cannot truncate a record or double-apply a phase.
`status` never creates anything: a read on a directory without `.agent-loop` simply returns an empty list.

## Resuming

Read `status` first: `phase` is the phase in progress and `gate` says what is still needed. If a run is stale, start a new one — never hand-edit the JSON, it is the audit trail.

## Limits

- Discovery reflects the filesystem at call time; a newly installed skill is visible on the next call, no restart needed.
- `dir` must already exist (pass an OS-native path, or omit it for the current directory). A Git Bash style `/c/Users/...` path is translated on Windows.
- A run id must match `[A-Za-z0-9._-]{1,120}` and must resolve inside `.agent-loop/`; anything else is rejected.
- The engine never calls a model or a network service. Anything requiring judgement stays with the model.
