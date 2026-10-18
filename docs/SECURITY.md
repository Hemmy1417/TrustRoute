# Security

A threat model for one contract that reads supply-chain records and turns
them into a typed verdict. It holds no money, so the thing worth attacking
is the verdict itself.

## What is protected

| Asset | Why it is worth attacking |
|---|---|
| the verdict | downstream systems accept deliveries, release payments and close disputes on it |
| the frozen requirement | if it could be changed after a submission, any verdict could be made to mean anything |
| the bytes a finding rests on | a finding whose evidence can be swapped later is not evidence |
| `is_claim_supported` | the one boolean another contract reads, so the cheapest thing to attack |
| the accumulating record per policy version | an auditor reads it instead of replaying every submission |

## Actors

Policy owner, challenge opener, submitter, record issuer, the host serving a
record, a malicious leader, honest validators, a malicious validator
minority, and a downstream consumer. Anyone may call `resolve_submission`:
running a round is not a privilege, because the round cannot be steered.

## Trust assumptions

- an honest validator majority, as the protocol assumes;
- the hosts named in a requirement serve what their issuers publish - this is
  an **origin** assumption, not a signature check, and the contract says so;
- the reading stage is competent at reading, not trustworthy. Every finding
  it returns is re-grounded by every validator against bytes that validator
  verified itself;
- whoever opens a challenge chose its requirement honestly. A requirement
  that asks the wrong question will be answered faithfully.

## Input attacks, and what stops them

| Attack | What stops it |
|---|---|
| a record swapped after it was committed | the sha256 is bound at submission and re-verified by every node before anything reads the bytes; a mismatch is `HASH_MISMATCH`, never a reading |
| a record that instructs whoever reads it | markers are counted in **code**; any hit caps the outcome, so the claim cannot be supported however the reading went. One fixture does this deliberately |
| a quote invented to support a finding | every finding must carry words from the bytes *that node* verified; an ungrounded finding is downgraded to uncertainty, never flipped to its opposite |
| a quote lifted from a different record | grounding is per record |
| a forged leader payload | the gate re-derives every state, the criteria and the verdict from the payload's own findings, then the comparison checks it against this node's own reading |
| an unknown enum smuggled into a payload | enums are normalised only in case and whitespace; an unknown value is never repaired into a known one |
| a float or a boolean where an integer belongs | `type(x) is int` - a bool is not an integer here - and a float anywhere in a reading refuses the whole answer |
| a timestamp written to look earlier or later | times are normalised in code and compared as integers; the order of the checkpoints is never a model's opinion |
| an identifier spelled to look like another lot | identifiers are normalised, then reconciled across records; a disagreement is `INCONSISTENT_EVIDENCE` |
| one record repeated to fake corroboration | the same bytes cannot appear twice in a submission, and a key reconciles only when **two different records** state it |
| the same bytes reused for another shipment | the record registry binds bytes to their first challenge; reuse elsewhere is refused |
| a requirement weakened after a verdict | versions are immutable and hashed; a challenge binds one version and its hash, and a later version cannot reach it |
| a revoked requirement still relied on | every reliance gate reports `BLOCKED` once its version is revoked |
| an oversized record to exhaust a round | records are capped at 200,000 bytes, excerpts at 6,000, and the whole blob at 60,000 |
| a request to a private address | locations must be `https`, with a named non-numeric host, no credentials, no port, and not `localhost`/`.local`/`.internal` |
| replaying a settled submission | terminal verdicts refuse another round; retries are capped at three |
| an unresolved round left to look settled | nothing is stored unless a round carries, and `PENDING` is not consumable |

## Fail-open or fail-closed: every safety-critical default

| Situation | Outcome |
|---|---|
| a required record unreadable | `EVIDENCE_UNAVAILABLE`, retryable |
| an unusable answer from the reading stage | `EVIDENCE_UNAVAILABLE`, retryable |
| a contradiction, or identifiers that disagree | `INCONSISTENT_EVIDENCE`, retryable |
| a checkpoint nobody can time | the chain is `UNREADABLE`, not complete |
| a log that does not span the required window | `UNREADABLE`, not compliant |
| a source not from its issuer's registered host | `SOURCE_UNVERIFIED`, and the claim cannot be supported |
| an identifier only one record states | `UNCORROBORATED`, and the claim cannot be supported |
| any reader-directed text | the claim cannot be supported |
| an unknown value, a wrong type, a float | the answer or the payload is refused |
| rounds exhausted | `EXHAUSTED`, never consumable |
| an `as_of` the contract cannot read | freshness `UNKNOWN`, gates false |

There is no path on which uncertainty produces a supported claim.

## Privacy and commercial confidentiality

Nothing confidential belongs on chain, and nothing confidential is stored
here. What is persisted is: identifiers the caller chose, a bounded summary
they wrote, each record's public location and the sha256 of its bytes, the
issuer the submitter declared, and the findings - which include quotes of up
to 240 characters from records the submitter published publicly.

What is **not** persisted: the records themselves, prices, customer lists,
contract terms, or any personal data. A record is fetched, hashed, read
within one round and never stored.

Every demonstration record in `fixtures/` is synthetic and marked
`TEST / DEMONSTRATION ONLY` and `NOT FOR PRODUCTION`. No real shipment,
organisation, port or measurement is described in any of them.

A caller who needs to keep a record private should publish a redacted
extract and bind that, and should understand that a quote from it may appear
in the findings.

## What this does not protect against

- **It does not prove a physical event.** A hash proves bytes are the bytes
  that were committed. It says nothing about whether a container was ever
  cold, whether a lot came from anywhere, or whether a scan describes a real
  movement. Every party could produce internally consistent records of a
  shipment that never happened, and TrustRoute would adjudicate them as
  satisfying the requirement.
- **It is not a certification.** A verdict is not a regulatory approval, a
  phytosanitary clearance, or a substitute for physical inspection,
  independent audit or laboratory testing.
- **Source authenticity is an origin check.** It proves the bytes came from
  the host the requirement names for an issuer. It does not prove the issuer
  wrote them, and the contract never claims a signature was verified.
- **URL rules are defence in depth, not SSRF prevention.** Validator and
  runtime egress policy matter at least as much.
- **Prompt-injection handling is layered, not immune.** Marker counting,
  structured framing, quote grounding and code-owned outcomes each reduce the
  damage a hostile record can do. None of them is a proof.
- **Honest readings can differ.** A genuinely borderline record may be read
  as unclear, which produces `CLAIM_NOT_ESTABLISHED` rather than a decision.
  That is the intended direction of error.
- **Studionet, not production.** This is a demonstration deployment on a
  development network, not an audited production system.
