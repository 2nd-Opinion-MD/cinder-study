---
title: Tuesday 2026-05-26 call — internal talking-points cheat sheet
status: working_document
audience: Dylan + Andras (internal; not for distribution to call participants)
related:
  - PRE_CALL_CHECKLIST.md (the structured field-list asks; bring this open in a tab)
  - packages/andras_pre_call_2026-05-26/STATUS_INGESTION_READINESS.md
  - confirmation_matching_rule.md (§13.2 caveats)
  - confirmation_omeract.md (§13.3 caveats)
  - confirmation_software.md (§13.4)
---

# Tuesday call — talking points

**When:** Tuesday 2026-05-26, 1:00 pm CDT (90-minute window held; assume 45–60 min effective).

**Who:**

| Person | Role | Track to drive |
|---|---|---|
| Andras Hangyal | 2OPMD co-PI | Opens; runs Rebecca/Kaleb tracks |
| Dylan McCapes | Pipeline architect | Runs Adam track; closes the technical decisions |
| Kaleb | FORWARD/UNMC, prospective lead author | ACR target + comparator availability |
| Adam Cornish | Head of IT, UNMC | Data format, delivery date, field availability |
| Rebecca Schumacher | Executive Director | Publication policy, authorship governance |

**Total speaking time you actually get** (rough): ~7–10 min for our questions, ~7–10 min for theirs, ~10 min for cross-discussion. **Optimize ruthlessly.** You will not get to everything.

---

## The three things we must walk out with

In priority order. **Every other agenda item is below the cut line.**

| # | Decision needed | Who owns it | Branch implications |
|---|---|---|---|
| 1 | **Data delivery date for the N=50 slice** | Adam | Anchors the ACR-2026 vs ACR-2027 fork |
| 2 | **Field availability for the §13.2 / §13.3 caveats** (3 specific yes/no questions below) | Adam + Kaleb | Locks the primary-vs-fallback comparator branches |
| 3 | **ACR submission target (year + category)** | Kaleb | Sets our calendar; everything downstream cascades |

If the call ends and we have these three, the call was a success. Everything else is bonus.

---

## Opening posture (first 5 minutes)

**What Andras leads with** (suggested):

> *"Thanks for making time. Three quick context points before we get into the asks. One: the protocol is pre-registered at v3.0-FINAL with §13.2, §13.3, §13.4 confirmed-with-caveats — those caveats are what we need three answers from Adam on today. Two: the receiving-side pipeline is running end-to-end against synthetic mock data today; pointing it at the real FORWARD column names is a one-place change. Three: we have six structured questions for Adam plus one calendar question for Kaleb plus one governance question for Rebecca, and we'd like to walk out with answers to all eight. Sound workable?"*

**What we lead WITH:**

- We are **further along** than they may expect. Pipeline runs end-to-end today. Bayes layer vendored. Schema + PII tripwire enforcing.
- We are **pre-registered**, which is uncommon for ACR submissions and is a credibility multiplier we should mention.
- We have **three branchable comparator paths**, all pre-registered. Not one fragile primary analysis.

**What we DON'T volunteer in the first 5 min:**

- N=50 power concerns (don't telegraph weakness up front; raise it as a question to them, not a confession from us)
- Our own ACR-2026-vs-2027 internal probability estimate (let Kaleb say his preference first)
- The "we're alone on this code" honesty (only if asked; have answer ready)

---

## Adam track — the technical asks

**Goal:** walk out with delivery date + format + the three caveat-resolving field confirmations + a sample-size sanity check.

### A1. Delivery date (the single most important question of the call)

**Verbatim ask:**

> *"What's your realistic ship date for the N=50 slice? Not the optimistic date — the date you'd put in writing. We're working back from ACR's mid-June abstract deadline."*

**Listen for:**

- "First week of June" → ACR 2026 is live. Lock it down with a calendar invite for the handoff.
- "Mid-to-late June" → ACR 2026 is at risk. Pivot to "what would it take to get a 5-patient pilot slice this week so we de-risk the pipeline?"
- "Early July or later" → ACR 2026 is realistically gone. Pivot to the methods-only ACR 2026 abstract OR ACR 2027 framing. Don't argue, just acknowledge.

**Follow-up if the date slips past mid-June:**

> *"Would a small pilot slice (5 patients, any waves) earlier in June be feasible? It de-risks our pipeline so when the full N=50 lands we're not debugging plumbing, we're producing numbers."*

### A2. File format and shape

Cross-ref `PRE_CALL_CHECKLIST.md §2` for the structured field-list. Don't read the whole list during the call; ask the meta-question and hand him the checklist as a follow-up.

**Verbatim ask:**

> *"Quick meta-question on format: Parquet, CSV, or JSON? And is it one file per wave or one aggregate export with `wave_number` + `wave_date` columns? We support all four combinations; we just need to know which one to point the adapter at."*

**Listen for:**

- "Parquet, aggregate" → ideal; minor tweak to adapter loader.
- "CSV, aggregate" → already supported; zero changes.
- "JSON, per-wave" → small ETL added but nothing structural.
- "We don't have it canonically — we'd build it for you" → ask what their default export format is and accept that.

**Follow-up:**

> *"And ISO 8601 dates with explicit timezone, or is it native UNMC date format we'll need to coerce?"*

### A3. The three caveat-resolving field questions

These are **the** questions. Without these we cannot lock the primary analysis. Ask all three even if Adam tries to lump them.

**A3.1 — Clinician-rated flare flag (§13.2 caveat 1):**

> *"In the FORWARD wave records — is there a clinician-rated flare flag? A field where the rheumatologist marks 'this patient was flaring at this wave'? Could be Boolean, could be a free-text field with structured values. We can adapt to anything; we just need to know if it's there."*

**Listen for:**

| Adam's answer | What it means | Action this week |
|---|---|---|
| "Yes, structured Boolean / structured value" | **Primary branch is live.** §4.6 matching rule unlocks. | Confirm the column name; close §13.2 caveat 1 in `governance/pre_registration_log.md` |
| "Yes, but it's free-text in clinician notes" | Primary branch with NLP cost. We can do it but adds 1 week. | Negotiate: can FORWARD's IT export the flag in structured form for our N=50 slice? If no, fall to OMERACT primary |
| "No, FORWARD doesn't carry that" | OMERACT becomes primary. **§13.2 caveat 1 → AMEND-1.** | Close as "FORWARD does not carry clinician-rated flare flag; OMERACT primary per pre-registered fallback" |

**A3.2 — Mollard smartphone subgroup size (§13.2 caveat 2):**

> *"How many of your N=50 patients have Mollard 2026 smartphone-signature data? We need ≥10 to have a defensible Mollard comparator branch; below that we drop it as a sensitivity analysis only."*

**Listen for:**

- "All N=50" → Mollard is a primary co-comparator. Excellent.
- "Maybe 15–25" → Subgroup analysis. Defensible.
- "<10 or none" → Drop Mollard from primary analysis; document in §13.2 caveat 2 as resolved.

**A3.3 — Patient Global VAS coverage + corticosteroid resolution (§13.3 caveats):**

> *"Two field-coverage questions for the OMERACT comparator. One: is Patient Global VAS captured in raw 0–100 form on every wave, or only when patients trigger it? Two: do your medication records distinguish oral corticosteroids from parenteral, and if so, is there a prednisone-equivalent dose computed somewhere upstream — or do we compute it ourselves from the raw drug + dose?"*

**Listen for:**

| Patient Global VAS coverage | Action |
|---|---|
| Every wave | OMERACT primary stays as written. §13.3 caveat 1 closed. |
| Sparse / triggered | OMERACT becomes "indeterminate" on missing-VAS waves. Pre-registered fallback handles this; flag the indeterminate rate post-Phase-4. |

| Corticosteroid resolution | Action |
|---|---|
| Distinguishes route + computes prednisone-equivalent | §13.3 caveats 2+3 closed. §4.5 state machine plugs in directly. |
| Distinguishes route, no equivalent dose | We compute equivalents from `analysis/detection/steroid_equivalents.yaml` (already specced). 1 day of work. |
| Doesn't distinguish route | Maintenance-vs-rescue rule degrades to dose-pattern only. Document as §13.3 caveat 3 amend. |

### A4. Sample size — push for >N=50 if possible

**Verbatim ask:**

> *"Last technical one: is N=50 a hard ceiling, or could we get N=100 or larger? Our sample-size simulation is in flight this week; if it says N=50 gives us a kappa CI wider than 0.3 we'd want to negotiate a larger slice now rather than after analysis. Does FORWARD have a larger feasible cohort under the same inclusion criteria?"*

**Listen for:**

- "Could go to N=100, similar effort" → Take it. Even if §6 simulation says N=50 is fine, larger is always better for a validation study.
- "N=50 is the ceiling" → Accept it; don't push twice. Note for §6 simulation that we're locked at N=50.
- "Could go higher but slower" → Ask "how much slower?" and weigh against the calendar.

---

## Kaleb track — the ACR & comparator asks

**Goal:** lock the ACR target + confirm he's the lead submitter + flag any FORWARD-side comparator data we don't know about.

### K1. ACR target year and category — the calendar anchor

**Verbatim ask** (Andras to ask, before the technical content):

> *"Kaleb, before we dive in — when you imagine the ACR submission, are you thinking ACR 2026 (this November) or ACR 2027? And methods abstract or clinical-findings abstract? It changes which deliverables we sequence in front of which."*

**Listen for:**

| Kaleb's answer | What it means | Calendar |
|---|---|---|
| "ACR 2026, clinical-findings" | We're sprinting. Mid-June abstract deadline. Numbers must exist by ~June 15. | Adam's date must be ≤ early June. Power simulation must say N=50 is enough. |
| "ACR 2026, methods-only" | Lower-stakes path: we submit the framework + synthetic-exemplar validation + planned FORWARD analysis. Numbers from FORWARD are a 2027 follow-up. | Doable regardless of when Adam ships. |
| "Aiming 2026 but flexible to 2027" | Optimal — gives us permission to slow down if data slips. | Plan for 2026, soft-target 2027. |
| "ACR 2027" | Calm pace. Full FORWARD analysis with v3.0-AMEND-1 if needed. | Plenty of buffer for §6 simulation, methods refinement, manuscript. |

**Don't argue with his preference.** It's his name on the submission.

### K2. Clinician-rated comparator (cross-check with Adam)

If Adam said "FORWARD doesn't carry clinician-rated flare flag," verify with Kaleb:

> *"Kaleb, just to triangulate — is there an alternate route to clinician-rated flares for our N=50 cohort? Chart review by a rheum fellow, retrospective clinician adjudication, anything? The pre-registration accommodates either FORWARD-native or post-hoc adjudicated; we just need to know which we're working with."*

**Listen for:**

- "I could adjudicate them myself in [N] hours" → Bring this up as a real plan; it's the gold standard and Kaleb's name on it strengthens the paper.
- "Possible but slow" → Reserve for sensitivity analysis only.
- "Not feasible" → OMERACT-primary path is locked.

### K3. FORWARD-side dataset details we don't know about

**Verbatim ask:**

> *"Anything in the FORWARD dataset that's not in the structured field-list we sent — registries, imaging, biomarker panels, prior trial enrollments — that you think we'd want to know about? We don't want to over-engineer the adapter, but we don't want to discover a useful field three weeks in either."*

**Listen for:** anything that suggests existing flare-relevant variables we haven't enumerated. Take notes; don't try to absorb them on the call.

---

## Rebecca track — governance & publication policy

**Goal:** confirm FORWARD's publication policy *now*, not in October. Confirm authorship structure. Confirm review lead time.

### R1. Publication policy and lead time

**Verbatim ask** (Andras to lead):

> *"Rebecca, one governance question we'd like to settle today rather than later. When Kaleb submits a derivative-analysis abstract or paper using a FORWARD slice, what's FORWARD's review process and lead time? We want to make sure our calendar accommodates whatever pre-publication review you require."*

**Listen for:**

| Rebecca's answer | Calendar impact |
|---|---|
| "Brief courtesy review, ~1 week" | Trivial; just budget 1 week before each submission. |
| "Formal review, 2–4 weeks" | **Big** — eats most of the ACR-2026 buffer. Build it into the timeline now. |
| "Approval required from FORWARD board" | Could be 1–3 months. ACR 2026 may become infeasible regardless of data delivery. Need to know now. |
| "We'd need to discuss specifics" | Pin down a follow-up call this week. Don't leave it ambiguous. |

### R2. Authorship structure

**Verbatim ask:**

> *"And on authorship — for the ACR submission and the eventual full paper, how does FORWARD typically structure authorship for derivative analyses? We want to make sure Kaleb's lead-author position is solid and the team is set up correctly from the start."*

This is mostly informational; let Rebecca state FORWARD's norms. Push back only if it would be unworkable for our team. Andras handles any negotiation here.

### R3. Data use agreement / institutional approvals

**Verbatim ask:**

> *"Last governance one — are there any IRB amendments, DUAs, or institutional approvals on FORWARD's side that need to be in place before Adam ships the slice? We'd rather know now if there's a 30-day approval window."*

If yes, pin the timeline. This can silently kill ACR-2026 if it appears late.

---

## §13 caveat-branch decision tree (post-call quick-action)

After the call, before EOD Tuesday, run through:

| Caveat | Adam's answer | Action by EOW |
|---|---|---|
| §13.2 — clinician-rated comparator | Available structured | Close caveat 1; proceed with primary |
| §13.2 — clinician-rated comparator | Available unstructured | Negotiate structured export OR file v3.0-AMEND-1 selecting OMERACT primary |
| §13.2 — clinician-rated comparator | Not available | File v3.0-AMEND-1 selecting OMERACT primary |
| §13.2 — Mollard subgroup ≥10 | Yes | Mollard stays as co-primary; no amendment |
| §13.2 — Mollard subgroup ≥10 | No | Amend §13.2 caveat 2 to "Mollard sensitivity-only"; close |
| §13.3 — Pat. Global VAS coverage | Every wave | Close §13.3 caveat 1 |
| §13.3 — Pat. Global VAS coverage | Sparse/triggered | Close caveat 1 with "indeterminate rate flagged post-Phase-4" amend |
| §13.3 — corticosteroid route+equivalent | Both available | Close §13.3 caveats 2+3 |
| §13.3 — corticosteroid route+equivalent | Route only | Close caveat 2; we compute equivalents (no amend needed) |
| §13.3 — corticosteroid route+equivalent | Neither | File v3.0-AMEND-1 degrading §4.5 state machine to dose-pattern only |

Each "amend" path is **already pre-registered as a branch** — these aren't surprises, they're scheduled fork resolutions. Frame them that way to FORWARD: *"the pre-registered branch we're activating per §13.X is..."*

---

## What to listen for that we don't ask about directly

**Green flags** (good news, capture it):

- Adam mentions a field we didn't ask about that sounds useful (e.g., "we also have BASDAI scores" or "there's a treatment-response field")
- Rebecca volunteers that FORWARD has a fast-track review for pre-registered studies
- Kaleb mentions a co-author who's done ACR submissions before
- Anyone says "there's a larger cohort we could include if we expand inclusion criteria"

**Red flags** (warning signs, capture privately):

- Adam hedges on the delivery date or describes it as "we'll see"
- Rebecca mentions "additional review" or "board approval" without a timeline
- Kaleb sounds uncommitted to ACR specifically (mentions other venues, suggests we wait for "more data")
- Anyone questions whether Bayesian methods are "what reviewers want" — defer politely; don't argue
- Mention of confounding institutional politics (FORWARD vs UNMC, IT-vs-clinical, etc.)
- Discussion of consent/IRB scope changes — IRB modifications can be 30-90 days

**If a red flag fires, don't react in-call.** Let Andras absorb it diplomatically. Discuss internally Tuesday evening.

---

## What to defer / not commit to during the call

**Things to NOT promise on the call:**

| Topic | Reason | What to say instead |
|---|---|---|
| A specific delivery date for our analysis output | We don't have §6 power simulation results yet | *"We'll send a written timeline by end of week, after the sample-size simulation completes."* |
| Exact authorship list | Not our call; FORWARD-driven | *"Whatever structure FORWARD typically uses for derivative analyses works for us."* |
| Exact ACR abstract title | Premature; depends on numbers | *"We'll share a draft title with Kaleb once we know whether it's methods-track or clinical-findings."* |
| Whether we'll produce additional analyses beyond the protocol | Scope creep risk | *"Anything beyond the v3.0-FINAL protocol would be a separate amendment we'd want to discuss."* |
| Specific numbers from the synthetic exemplars | Could be misread as real findings | *"The synthetic exemplars are protocol-validation only; we don't quote numbers from them as study results."* |
| Software / methodology changes | Pre-registered locks | *"§13.4 is locked at PyMC + ArviZ + seed=2026; that's part of the pre-registration."* |

**Things to commit to in writing during the call** (Andras emails the recap by EOD Tuesday):

- The data delivery date Adam confirmed (or "TBD by [date]")
- The three §13.2/§13.3 caveat resolutions
- The ACR target year + submission category Kaleb confirmed
- The FORWARD review timeline Rebecca described
- Action items per person with dates

---

## The receiving-side state — what to say if asked

If anyone asks about our readiness, the canonical line:

> *"Repository scaffold is landed. PTV input contract is published with the 632-event real-EHR reference fixture validated against it. PII tripwire enforces on every commit and every CI run. The Bayesian kernel layer is vendored from our internal codebase at a pinned commit (Phase 4.A, landed Monday). The FORWARD WebQuest adapter is running end-to-end against synthetic mock data and emitting schema-validated PTVs (Phase 4.A.2, also landed Monday). Pointing it at your real column names is a one-place change — instantiate one Python dataclass with Adam's confirmed names and the same code path absorbs the real wave."*

If asked about the team / who's doing the work:

> *"Dylan is the pipeline architect. Andras is co-PI and reviews the methodology. Kaleb is prospective lead author. The codebase is open, replicable, and pre-registered, which means we're set up so that if a reviewer or replicator wants to verify any analytic decision, they can rerun the entire pipeline deterministically from the public repo."*

(Honest, concise, doesn't oversell.)

If asked about Bayesian methodology rationale:

> *"The Bayesian framework gives us posterior credible intervals on every flare detection — not just point estimates. That means we can report not just whether a flare was detected, but with what confidence, and we can detect uncertainty widening in advance of clinical confirmation. It's also the only framework where we can pre-register the prior, the likelihood, and the inference target separately and have each be auditable. Frequentist mixed-effects models are still in the pre-registered sensitivity analysis (Sensitivity Analysis 1) so reviewers who prefer that framing have a parallel result."*

---

## Closing — what good looks like at the 50-minute mark

**Andras-led closeout** (suggested):

> *"Quick recap before we wrap. We heard: data ships [date]. Format is [format]. The three caveat questions resolved as [resolution 1, 2, 3]. ACR target is [year + category]. FORWARD's publication review timeline is [duration]. I'll send a written recap with action items by EOD today. Anything we missed?"*

If they have questions for us we couldn't answer — note them, commit to a written follow-up, don't speculate live.

If a topic ran out of time — flag it for a 15-min Friday follow-up call with the relevant subset (don't try to push the meeting long).

---

## Post-call: Tuesday evening checklist

By midnight Tuesday:

- [ ] Andras's recap email sent to all attendees with action items + dates
- [ ] `governance/pre_registration_log.md` updated for the §13.2/§13.3 caveat resolutions
- [ ] Wednesday morning's task list:
  - [ ] If §13.2 amendment needed: draft `governance/amendments/v3.0-AMEND-1.md`
  - [ ] If column names confirmed: update `ForwardFieldSpec` defaults; rerun adapter tests
  - [ ] Update `IMPLEMENTATION_PLAN.md` Phase 4 sequencing per the new calendar
- [ ] Internal Wednesday-morning sync (Dylan + Andras, 30 min) to align on any pivots
- [ ] If ACR 2026 was confirmed: pre-write the abstract template by Friday
- [ ] If §6 power simulation hasn't started: bump to top of Wednesday queue

---

## One-paragraph summary (read this last, 30 seconds before the call)

The receiving side is real and runs end-to-end against synthetic data today. We need three answers from Adam (delivery date, format, three caveat-resolving fields), one answer from Kaleb (ACR target year + category), one answer from Rebecca (FORWARD review timeline + authorship structure). Every other agenda item is below the cut. Don't volunteer N=50 power concerns. Don't argue if Kaleb prefers ACR 2027. Frame any caveat that resolves "no" as activating a pre-registered fallback branch, not as a problem. Andras runs Rebecca and the opening; Dylan runs Adam and closes the technical decisions. Email recap by EOD owned by Andras.
