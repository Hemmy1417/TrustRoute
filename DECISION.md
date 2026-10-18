# Decision record

Why TrustRoute is the primitive in this repository, what it nearly collides
with, and why it is still a distinct primitive.

## The concept was supplied, not scouted

The build brief fixes the concept and says, in the Originality section, *"Do
not generate replacement ideas... preserve the concept unless a
near-identical collision is found. If a near-identical collision is found,
stop and report it rather than silently changing the concept."*

So the candidate-generation and scoring phase of the generic autopilot was
deliberately **not** run. Generating ten alternative primitives and scoring
them would have been work in direct conflict with the instruction. What was
run instead is the collision audit, in full, below.

## The trust question

> Given a declared supply-chain verification requirement, a specific
> shipment or lot claim, and independently fetchable records, do the records
> establish that the required custody, origin, condition or compliance
> events actually occurred?

Not *are these documents internally well-formed*, and not *do these
documents match the contract terms*. Whether the **records, held by
different parties, reconcile with each other and with the physical sequence
they claim**.

## Collision audit

Both accounts the owner builds under were listed in full
(`gh repo list Hemmy1417 --limit 200`, `gh repo list Olawalter --limit 100`)
and every repository whose domain or shape could plausibly overlap was
opened and read - README, and for the nearest one the contract source
itself. Names were not used as evidence; the decision model was.

### The nearest alternatives

| Repository | Its trust question | Evidence | Verdict model | Same primitive? |
|---|---|---|---|---|
| **Hemmy1417/Tradera** | Do these trade documents, **on their face**, conform to a frozen trade specification? | presenter-committed documents, hash-bound | `CONFORMING` / `NON_CONFORMING` / `INCONCLUSIVE` over 7 criteria: documents present, quantity tolerance, shipment date, currency, commodity, counterparties, destination | **No - the closest by domain.** Tradera compares documents against *contract terms*. It says "on their face" and means it. It has no cross-record reconciliation verdict, no source-authenticity state, and no time-series evidence |
| **Hemmy1417/ClaimCourt** | Does the evidence meet a versioned insurance policy's coverage conditions? | claimant documents, hash-bound | `COVERAGE_SUPPORTED` / `COVERAGE_NOT_ESTABLISHED` / `EXCLUSION_APPLIES` / `FRAUD_INDICATORS_FOUND` / `INCONCLUSIVE` / `EVIDENCE_UNAVAILABLE` | **No - the closest by engine.** Same family (versioned criteria + hash-bound evidence + one round + typed verdict). Different question: entitlement under a policy, from one party's papers, with no requirement that independent parties' records agree |
| **Hemmy1417/InsureShield** | Does committed claim evidence satisfy a versioned insurance policy, treating the claimant as hostile? | claimant documents | `VALID` / `SUSPICIOUS` / `INCONCLUSIVE` / `UNAVAILABLE` / `REJECTED` | No. Insurance entitlement again |
| **Olawalter/Cargoproof** | Should a cargo-insurance claim pay, and how much? | claim evidence | adjudication + **escrow settlement** | No. An application with money movement; the decision authorises a payout |
| **Olawalter/TradeLayer** | How should a trade escrow pay out when the parties disagree? | frozen evidence | findings → payout under pre-agreed remedies | No. Escrow settlement |
| **Olawalter/Proofline** | Does the real-world condition for releasing escrow still hold? | authoritative external alerts | `APPROVE` / `HOLD` / `FAIL` + escrow routing | No. Escrow release on a live external condition |
| **Hemmy1417/DiscoMile** | Did a researcher deliver the milestone committed to? | commit-pinned/Zenodo files | `QUALIFIED` / `NOT_QUALIFIED` / `INCONCLUSIVE` + reward | No. Acceptance of delivered work, with money |
| **Hemmy1417/Delivera** | Does delivered freelance work meet pre-signed acceptance criteria? | delivered work | settlement from escrow | No |
| **Hemmy1417/GroundTruth** | Did a real-world milestone happen, enough to release escrow? | public evidence | judgment → payout table | No. Escrow on a single event |
| **Olawalter/Trace** | Does public evidence satisfy a published compliance protocol? | public web pages | satisfied / not | Related in spirit, different object: a published protocol about an entity, not a shipment's records reconciling with each other |
| **Olawalter/PROVENANCE** | What is the current adjudicated state of a public claim, and is it stale? | public web evidence | time-bound semantic state | No. Public-claim state tracking |
| **Hemmy1417/Factora** | Is a receivable financeable? | invoice/PO/delivery trail | financing terms from a code table | No. Credit decision with money |

### The honest finding

The owner's portfolio is **saturated with one architecture**: frozen or
versioned criteria, hash-bound evidence, one consensus round, a typed
verdict, `is_*` consumer gates. TrustRoute is built in that family, and
saying otherwise would be false. Two repositories sit close enough to name
as risks rather than footnotes:

- **Tradera** is the nearest by domain - trade documents, shipping, the same
  commercial world.
- **ClaimCourt** is the nearest by machinery - a versioned policy, criteria,
  a verdict derived in code.

Neither is near-identical, so under the brief the concept is preserved. But
the overlap is close enough that a generic implementation *would* collapse
into "ClaimCourt with supply-chain nouns", and that risk is the main thing
this design is built to avoid.

### What makes TrustRoute a different primitive

Four things, each load-bearing rather than cosmetic:

1. **Records from different parties must reconcile with each other.** Every
   other primitive above checks a party's evidence against a *specification*.
   TrustRoute checks records against each other: a carrier's custody scan, a
   warehouse receipt and a customs entry must agree on which lot they
   describe. `INCONSISTENT_EVIDENCE` is a first-class terminal verdict, not
   a diagnostic note.
2. **A required sequence, not a set of independent criteria.** Custody
   checkpoints are ordered. Evidence can show every checkpoint and still
   fail, because the shipment reached the destination port before it cleared
   the origin terminal. Order is decided in code from timestamps the panel
   extracts.
3. **Time-series evidence.** A cold-chain log is not a document field. The
   panel extracts readings; **code** decides whether the series stayed in
   range across the required window and whether any excursion exceeded the
   allowed duration. No other build in the portfolio adjudicates a series.
4. **Source authenticity is a verified state or an explicitly unverified
   one.** A policy version registers which host each issuer publishes from.
   Code verifies that a record's bytes came from the registered host for its
   declared issuer; where it did not, the criterion is
   `SOURCE_AUTHENTICITY_UNVERIFIED` and can never read as verified. The
   contract never claims a signature was checked, because none is.

## Delete GenLayer: what breaks?

Without GenLayer, one party - the buyer's platform, the carrier, an auditor,
or whoever rents the AI service - becomes the authority that decides whether
a custody handoff described in one party's words is the same event described
differently in another's, whether "Apapa Terminal, Lagos" and "Lagos port
complex" are the same checkpoint, and whether two records describe the same
lot. That party also chooses which records to read. Every downstream
consumer then trusts that operator rather than the evidence.

Deterministic code genuinely cannot answer those questions. It can and does
answer everything else: hashes, host registration, ordering, the excursion
arithmetic, the delivery window, verdict precedence, and every lifecycle
transition.

## Three consumers, no contract change

1. **Procurement and goods-receipt systems** - read
   `is_claim_supported(submission_id, as_of)` before accepting a delivery
   against a purchase order.
2. **Cold-chain and logistics dispute handling** - read `get_findings` and
   `get_verdict` to see which checkpoint is unevidenced or which excursion
   breached the range, and what the records were quoted saying.
3. **Auditors, certification workflows and risk engines** - read
   `policy_record(policy_id, version)` for the accumulating record per
   policy version, and `get_evidence_status` to tell "we checked and it
   failed" from "nobody could read the records".

Nothing in the contract moves money, so a settlement contract is a fourth
consumer rather than a competing design.

## Hardest technical risk

**Equivalence.** The panel returns *facts* - which record evidences a
checkpoint, the timestamp it states, the readings in a log, the identifier
each record carries - and code derives everything from them. That is the
right division, but it means validators must agree on extracted values, and
honest nodes can read "14 Mar 2026 09:40 UTC" and "2026-03-14T09:40Z" as the
same instant while returning different strings. Timestamps and numbers are
therefore normalised in code before anything is compared, and the comparison
covers the derived state and the values code actually used - not prose, and
not which grounded span was quoted.

The second risk is the one the brief names directly: a record that instructs
whoever reads it. Reader-directed text is counted in code and caps the
outcome, so a shipment note telling its reader to confirm delivery cannot
produce `CLAIM_SUPPORTED`.

## Why this belongs in standalone Intelligent Contracts

It is one deployable contract, no frontend, no token, no value movement, and
its output is a typed verdict other contracts read in one view. The
judgment it makes cannot be made by a deterministic contract, and must not
be made by a single operator.
