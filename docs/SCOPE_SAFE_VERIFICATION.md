# Scope-Safe Inline Verification

`run_python_check` runs a bounded Python snippet without creating a helper script. It is
registered only for a real DockerExecutor, never for the host executor. It reuses the configured
image and timeout cleanup but adds a read-only workspace bind mount. It rejects profiles with
network access, root UID, writable root filesystem or host fallback before execution.

Example model-facing call:

```json
{
  "code": "from module import function\nassert function([]) == []\nprint('empty case passed')",
  "timeout": 20
}
```

## Boundary

- Nonempty code, at most 12000 UTF-8 bytes; integer timeout from 1 to 60 seconds.
- Python `-I -B -c` with the snippet supplied as one argv value, not a shell command. Workspace
  module imports are enabled explicitly. Shell parsing/allowlists are unchanged.
- Workspace and root filesystem read-only; non-root/no-network/capability/resource restrictions
  inherited from the existing Docker profile. Temporary data may use the container `/tmp` tmpfs.
- Provider environment variables are not forwarded. Files already present in the mounted
  workspace are not filtered; use a credential-free isolated workspace for untrusted checks.
  Pytest plugin autoload and cacheprovider are disabled for these
  checks; bytecode writes are disabled. No test helper or project cache needs a writable mount.
- Result records exit code, timeout, execution policy and output-truncation flag. Returned output
  is clipped to 8000 characters; underlying subprocess capture is not a bounded-output transport.
- The registry does not automatically retry this execution, including raised transient errors.
  The durable tool ledger still applies. Unknown interrupted executions need normal reconciliation.

Read-only mounts prevent the check from modifying source files, including helpers a snippet tries
to write. The parent agent still has its separately permission-checked file tools; it can choose
to create files, so the harness must not promise that every whole agent run leaves no residue.
The external submission scope verifier continues rejecting unauthorized files; there is no
post-hoc deletion or filtering to inflate scores.

This is arbitrary model-authored Python in a Docker boundary, not a Python language sandbox or
an attestation that the asserted behavior matches the user's requirements. A snippet can contain
weak assertions or exit early. Untrusted multi-tenant grading is out of scope.

## Plan Accounting

Summary schema v2 separates bounded historical observations from the complete current plan.
The history allowance remains 1800 by default and the total request ceiling remains 24000.
The plan is counted in the real request envelope, retained verbatim and refreshed after updates.
If the full protected envelope cannot fit, execution still stops rather than truncating clauses.
See [context-window management](CONTEXT_WINDOW.md) for the estimator and migration rules.

The richer requirement/turn guidance remains opt-in. When enabled and the inline tool exists,
the system prompt directs behavioral assertions to it instead of workspace helper scripts.
Adding this Docker-only tool changes Docker run schema hashes; incompatible older durable runs
remain protected by the existing schema guard. Historical experiment checkpoints are evidence,
not silently migrated active trials.

Focused tests and live probes cover rich-plan retention, legacy summary upgrades, plan refresh,
total-budget fail-closed behavior, read-only mount arguments, profile/input limits, no automatic
retry, assertion failures, timeout cleanup and no workspace changes for actual inline probes.
Stage evidence: `reports/SCOPE_SAFE_VERIFICATION_20261029.md`.
