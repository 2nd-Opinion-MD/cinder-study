# CINDER pre-registration log

This log records the pre-registration commit for the CINDER study protocol per `PROTOCOL_DRAFT_v3 §2.4` and `KALEB_BRIEF_v2`. The pre-registration vehicle is **the GitHub commit hash of the `v3.0-FINAL` tag** of `PROTOCOL_v3.0-FINAL.md` in this repository, recorded in the ACR Convergence 2026 abstract supplemental field.

## Pre-registration status

| Field | Value |
|---|---|
| Status | **PENDING** — `v3.0-FINAL` tag has not yet been issued |
| Target tag | `protocol-v3.0-FINAL` |
| Target ACR submission deadline | 2026-06-09 |
| Required dependencies | §13 pre-delivery checklist closed (see below) |

## §13 pre-delivery checklist gate

The protocol cannot be tagged `v3.0-FINAL` until every line of the `PROTOCOL_DRAFT_v3 §13` checklist is confirmed. This log will record the gating events:

| Item | Status | Confirmation memo |
|---|---|---|
| §13.1 Sample size simulation closed | pending | `docs/CONFIRM_SAMPLE_SIZE.md` (Phase 2) |
| §13.2 Comparator matching rule confirmed | **confirmed-with-caveats (2026-05-24)** | `docs/confirmation_matching_rule.md` |
| §13.3 OMERACT comparator operationalization confirmed | **confirmed-with-caveats (2026-05-24)** | `docs/confirmation_omeract.md` |
| §13.4 Software platform confirmed (PyMC + vendored conjugate kernels) | **confirmed (2026-05-24)** | `docs/confirmation_software.md` |
| §13.5 Repository scaffold + open schemas published | **partially closed** | `docs/CONFIRM_REPO_SCAFFOLD.md` |
| §13.6 Mollard 2026 mapping confirmation | pending | `docs/CONFIRM_MOLLARD_MAPPING.md` (Phase 5) |

**Caveat carry-forward (§13.2 + §13.3).** Both confirmation memos are confirmed-with-caveats pending Adam Cornish's 2026-05-26 FORWARD/UNMC call answers on three FORWARD-side field characteristics:
- §13.2 Caveat 1 — clinician-rated flare flag availability and structure.
- §13.2 Caveat 2 — Mollard smartphone subgroup size.
- §13.3 Caveats A+B+C — Patient Global VAS coverage, RxNorm coding, oral/parenteral corticosteroid distinction.

The matching/OMERACT logic itself is implementable as written under all branches of these caveats; only the comparator status (primary vs sensitivity vs descriptive-only) and corner-case routing change. If Adam reports a structural gap that forces protocol §1.4/§4.6/§4.8/§5.1 micro-revision, the affected gate flips from "confirmed-with-caveats" back to "pending" and a v3.0-AMEND-1 protocol revision is committed before the v3.0-FINAL tag.

## Tagging procedure (when ready)

When all six §13 items are closed and confirmation memos land in `docs/`:

1. Update `IMPLEMENTATION_PLAN.md` Phase 6 entry to `done`.
2. Tag the protocol commit:
   ```bash
   git tag -a protocol-v3.0-FINAL -m "CINDER Study Protocol v3.0-FINAL — pre-registration commit"
   git push origin protocol-v3.0-FINAL
   ```
3. Record the resulting commit hash in this file (replacing the placeholder block below).
4. Submit the ACR abstract with the commit hash in the supplemental field.
5. Email the link to Kaleb + FORWARD/UNMC stakeholders per `KALEB_BRIEF_v2`.

## Pre-registration record (filled at tag time)

```
Tag:           protocol-v3.0-FINAL
Commit SHA:    <FILL AT TAG TIME>
Tagger:        Andras Hangyal / Dylan McCapes
Tag date:      <FILL AT TAG TIME>
Protocol file: PROTOCOL_v3.0-FINAL.md
SHA-256 of protocol file at tag: <FILL AT TAG TIME>
ACR abstract submission ID: <FILL AT SUBMISSION TIME>
```

## Amendment procedure

Once tagged, any change to the protocol requires:

1. A new commit on a separate `protocol-vN.M.md` file, leaving `protocol-v3.0-FINAL.md` untouched.
2. An entry in this log identifying the change, the rationale, and the new tag.
3. Notification to FORWARD/UNMC stakeholders if the change affects analysis, comparators, or sample size.

The `v3.0-FINAL` commit is immutable and is the binding pre-registration anchor regardless of subsequent amendments.
