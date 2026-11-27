# Skill self-evolution example — evidence-gated revisions

An opt-in Python plugin that demonstrates the roadmap deliverable from
[#7884](https://github.com/bytedance/deer-flow/issues/7884) ("Skills,
extensions, and reproducible agents"): a **proposed change**, the **regression
case it fixes**, the **old and new results**, and a **rollback to a known-good
version** — driven entirely through the host `SkillMutationService` contract
merged in [#5645](https://github.com/bytedance/deer-flow/pull/5645).

It uses extension API 0.2.11 with no host code changes. The host owns storage,
security scanning, revision identity and authorization; this package owns only
one policy: **a revision commits only when a recorded regression case
demonstrates it fixes something**.

## Why evidence-gated

With `skill_evolution.enabled`, the agent can already rewrite its own skills
through `skill_manage`. What is missing is a visible answer to "was that change
an improvement?". This example attaches one to every commit:

```
propose ──> stage()          freeze baseline + candidate bundles (host-side)
evaluate ─> recorded cases    run static checks against BOTH bundles
apply ────> check() + commit(assessment_ref)   host security gate, then commit
                                                  with the verdict attached
rollback ─> revert()          append-only return to the known-good revision
```

The `AssessmentRef` carried into `commit` binds the evidence to the exact
proposal (`candidate_hash` + `base_revision`); the host rejects a mismatched
assessment with `INVALID_ASSESSMENT`. Afterwards every committed `Operation`
answers: what changed, which recorded cases justified it, and how to undo it.

## Recorded regression cases

Cases are JSON files in `deerflow_extension_skill_evolution/cases/` (override
with `config.cases_dir`). One case per file:

```json
{
  "id": "converter-arg",
  "description": "SKILL.md must instruct the converter with --format json",
  "checks": [
    { "kind": "text_contains", "path": "SKILL.md", "needle": "--format json" },
    { "kind": "text_not_contains", "path": "SKILL.md", "needle": "--fmt " }
  ]
}
````

Check kinds: `file_exists`, `text_contains`, `text_not_contains`,
`referenced_files_exist` (bare `scripts/…` / `assets/…` tokens in a text file
must exist in the package), and `scripts_parse` (every `scripts/*.py` must pass
`ast.parse`).

**The evaluator never executes package content.** The candidate is an
agent-proposed revision that has not passed the host security `check` yet, so
the only safe operations are structural (presence, text, parse-only). A
malformed case file raises and stops the evaluation rather than silently
narrowing it.

### Verdicts

| Verdict | Meaning | Service behavior |
| --- | --- | --- |
| `justified` | every case passes on the candidate and at least one fails on the baseline | eligible for `apply` |
| `unjustified` | every case passes on both sides — nothing recorded was broken | proposal discarded, `apply` refuses |
| `failed` | some case still fails on the candidate (or none recorded) | proposal discarded, `apply` refuses |

## Install and configure

From the DeerFlow checkout root:

```sh
make extension-install SOURCE=examples/deerflow-extension-skill-evolution
```

The mutation capability requires an explicit operator grant in `config.yaml`
(restart required). Prerequisites are the same as any `skill_mutations`
consumer: durable database backend, `run_events.backend: db`, and a single
POSIX host with local disk:

```yaml
plugins:
  - name: skill-evolution
    package: deerflow-extension-skill-evolution
    use: deerflow_extension_skill_evolution:install
    enabled: true
    host_access:
      evidence:
        owners: ["your-user-id"]
      skill_mutations:
        owners: ["your-user-id"]          # subset of evidence.owners
        operations: [stage, check, commit, revert]
        trigger_agents: [lead_agent]
        target_skills: [example-skill]    # canonical names this plugin may revise
        topology: single_host_local
    config:
      cases_dir: null                     # optional: default bundled cases
```

Without the grant the service fails to start with a `NOT_GRANTED` diagnostic;
nothing else in the deployment changes.

## Review completed conversations in the background

Optionally add the following to the same plugin entry. Keep its existing
evidence and skill mutation grants. Choose a target in `target_skills` that
already exists as an enabled custom skill for the conversation owner.

```yaml
host_access:
  model_invocation:
    roles:
      review: my-configured-model
config:
  background_review:
    target_skill: example-skill
    creation_nudge_interval: 10
    model_role: review
```

The reviewer counts lead-agent model responses with tool calls across successful
interactive runs in each thread. A response with parallel calls counts as one
round. A direct `skill_manage` call resets the count and collected excerpts.
After the threshold, the worker reads the owner's current skill and asks the
granted model for a reusable correction. The model receives the skill and bounded
excerpts of user, assistant, and tool text, so choose a provider approved to
process that data. The default role is `default` if `model_role` is omitted.

The foreground run only queues a notification. The worker waits for sealed run
evidence and makes a single structured model call using the configured role.
Candidates use the same recorded cases and owner-scoped staging as manual
proposals. The proposal cites the triggering run and any earlier runs whose
excerpts entered the review. A justified proposal appears in the proposals endpoint. Applying it
still requires the owner's request and the host checks documented below.

The worker tracks up to 100 owner/thread pairs in memory and keeps the most
recent 16 text excerpts for each. Its bounded queue and counters reset on restart.
An unavailable seal, a saturated queue, or a failed review can cause a run to
be skipped. This prototype revises one configured existing skill and reads
completed runs observed since startup.

## HTTP surface

All routes are under `/api/extension-skill-evolution`:

| Route | Purpose |
| --- | --- |
| `GET /health` | readiness, evaluator identity, recorded case count |
| `POST /proposals` | resolve the sealed run evidence, stage a candidate, evaluate, return the verdict + report |
| `GET /proposals` · `GET /proposals/{id}` | list / inspect proposals and their reports |
| `POST /proposals/{id}/apply` | host `check`, then commit with the `AssessmentRef` attached |
| `POST /operations/{id}/revert` | roll back a committed revision |

`POST /proposals` takes `{skill_name, candidate_content, thread_id, run_id}`.
The run must be completed and sealed — it is the evidence anchor the host
requires for staging (`source_refs`), so every proposal records *which run
motivated the change*.

**Every route binds the caller.** The capability handles injected into the
service are scoped to the extension by the operator's grant, not to the
requesting user, so the routes resolve the host principal
(`deerflow_extension_api.auth.resolve_principal`) and refuse to act on a skill
owned by anyone else: `propose`, `apply` and `revert` answer 401 without a
principal and 403 (`FORBIDDEN`) across owners, and `GET /proposals` lists only
the caller's own proposals (another owner's proposal reads as 404, without
disclosing that it exists). When the host exposes a request-scoped run-evidence
reader, the evidence anchor must also be visible to the caller; hosts without
one fall back to the owner check.

## Offline walkthrough (tests)

The package ships the demonstration as tests; no Gateway, model, or network:

```sh
cd examples/deerflow-extension-skill-evolution
uv run --no-project --python 3.12 --with pytest --with pytest-asyncio \
    --with ../../backend/packages/extension-api \
    --with-editable . python -m pytest tests/ -q
```

`tests/test_lifecycle.py` drives the full loop against a fake host that
implements only the public contract: propose a fix for a broken converter
argument → verdict `justified` → apply → the committed operation carries the
report id → revert → the skill is byte-identical to the known-good baseline.
It also pins the refusal paths: `unjustified` and `failed` proposals are
discarded and cannot commit, a denied host `check` blocks the commit, and
double-commit is rejected.

## Scope and boundaries

- **This is an example, not a production engine.** The evaluator is a
  deterministic static checker. The optional reviewer uses a model to draft
  revisions from sealed run evidence.
- [#6954](https://github.com/bytedance/deer-flow/discussions/6954) proposes a
  distributable evolution plugin package with its own snapshot/versioning
  design; this example stops at the merged #5645 contract and should be
  revisited against that RFC if it lands.
- [#7066](https://github.com/bytedance/deer-flow/issues/7066) (eval-gated
  evolution) owns the broader signal → attribution → candidate → verification
  loop; the minimal evaluator here is deliberately smaller than that scope.
- The `skill_manage` direct-write path is unchanged. This plugin is additive
  and opt-in.

## A concrete evidence standard (input for the roadmap discussion)

The roadmap asks what evidence should be required before enabling automatic
publication. Rather than propose a standard in the abstract, this example makes
one concrete and reviewable:

1. **Every proposal names its motivating run.** Staging requires sealed
   completed-run evidence (`source_refs`); the host rejects stale or unsealed
   anchors.
2. **Evidence is recorded, not narrated.** A case is a versioned JSON file with
   deterministic checks; the verdict is computed from the frozen baseline and
   candidate bundles, not from the proposal text.
3. **The verdict travels with the commit.** `AssessmentRef` pins
   `evaluator`, `evaluator_version`, and a content-addressed `report_id`
   (SHA-256 over the canonical report JSON) to the exact `candidate_hash` and
   `base_revision`. The report bytes themselves are held in this service's
   in-memory cache, not persisted; the id lets anyone holding the report — or
   recomputing it from the same cases and frozen bundles — verify that it is
   the one this commit cites.
4. **Fail-closed by default.** `unjustified` and `failed` proposals are
   discarded before they can commit; a host `check` denial blocks the commit;
   an assessment mismatch is rejected by the host itself.
5. **Rollback is as auditable as the change.** `revert` appends a new
   operation referencing the one it undoes.

Automatic publication would additionally need: case authorship provenance (who
recorded the case, and was it derived from the same run that motivated the
change), a minimum case count, and a policy for `unjustified` proposals that
keep recurring. Those are deliberately out of scope here.
