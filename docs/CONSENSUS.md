# Consensus

What each node does, what they must agree on, what they may differ on, and
why a deterministic contract cannot do this alone.

## The one nondeterministic round

One `gl.vm.run_nondet_unsafe` per round, with a custom validator. There is no
second round: the questions the reading stage answers are all about the same
snapshot of the same records, so splitting them would mean fetching twice and
risking a source changing in between.

### The two nondeterministic calls

| Call | Where | What enters | What comes back | Why code cannot do it |
|---|---|---|---|---|
| `gl.nondet.web.get` | `_fetch_record`, once per record | one committed https location | status and body | the records live off chain; the contract has no other way to see them |
| `gl.nondet.exec_prompt` | `_node_round`, once per round | the bounded questions plus the bytes this node verified | strict JSON | which record evidences a checkpoint, what identifier a record carries, whether an origin claim is supported, which readings a log contains, whether a criterion is met, whether two records contradict each other |

Everything else in the round is ordinary deterministic Python.

## What the leader does

1. fetch each record and hash it **before anything reads it**, classifying it
   `RECORD_READABLE` or `RECORD_UNAVAILABLE` with a reason
   (`FETCH_FAILED`, `HASH_MISMATCH`, `TOO_LARGE`, `UNREADABLE`);
2. resolve each record's authenticity in code by comparing the host the bytes
   came from with the host the requirement registers for that record's
   declared issuer;
3. count reader-directed text markers in code;
4. derive, in code, which required record kinds are actually readable - and
   if any is missing, **skip the reading stage entirely**;
5. convene one reading call with the bounded questions;
6. read the answer strictly, and hold every finding to a quote from the bytes
   this node verified;
7. derive, in code: the normalised instants, the checkpoint order, the
   identity reconciliation, the condition result, the delivery comparison,
   the four criteria, the evidence status and the verdict;
8. return the whole payload.

## What every validator does

The same eight steps, from its own fetches. Then, before comparing anything:

1. **the gate.** `_parse_payload` refuses the leader's payload unless every
   field is a known value of the right type, the rows describe the submitted
   records in order, the missing-kinds list is what the rows imply, the
   findings are in the one normalised spelling, every quote is grounded in
   **this node's** bytes, and every derived field - including the four
   criteria and the verdict - is exactly what this contract's own code
   derives from the payload's own findings.
2. **the comparison.** `_first_difference` returns the first
   decision-critical field on which the two runs differ.

A validator that only checked JSON shape would not be a validator. This one
re-fetches, re-hashes, re-reads, re-grounds and re-derives, and can reject a
perfectly well-formed leader result that is simply not true.

### Why the gate matters more than the comparison

The gate is what makes the comparison safe to keep narrow. Because a payload
whose outcome does not follow from its own findings is refused outright, the
comparison does not need to police the reasoning - it only needs to catch a
payload that is coherent but describes a different reading of the records.

## Equivalence: what must match, what may differ

Must match:

```text
schema, submission_id, challenge_id, round
policy_id, policy_version, definition_hash, evidence_digest
shipment_or_lot_id, claim_type
directed_text_hits, panel_state
custody_state, identity_state, condition_state,
condition_worst_excursion_minutes, delivery_state, delivery_time,
origin_state, compliance_state, authenticity_state
the four criteria
evidence_status
verdict
missing_required_kinds
per record: record_id, kind, status, reason, byte_count, authenticity
per checkpoint: ref, finding, the instant the record states
per criterion: ref, finding
per identifier: ref, whether it reconciled, and to what value
whether a contradiction was found, and whether the evidence was sufficient
```

May differ:

```text
the sentence of reasoning
which grounded span was quoted
which record a quote was taken from, when more than one evidences the same
  checkpoint
how many records happened to repeat an identifier
```

In one line: **the facts must match, the outcome must match, and the
reasoning may differ.**

### Two notes a reviewer should hold us to

**The four criteria are compared.** Some projects document them as free to
vary on the grounds that the verdict pins them. That is not true here and the
contract does not pretend it is: `_first_difference` walks `CRITERIA_FIELDS`.

**The verdict comparison is redundant, and that is deliberate.** The verdict
is a pure function of fields that are themselves compared, so two nodes
agreeing on all of them cannot differ on it. The mutation sweep reports the
mutation that removes it as `EQUIVALENT` rather than as a hole, with that
argument recorded in `scripts/mutate.py`. It stays because it makes a
disagreement message say what actually disagreed.

### Why the normalisation is load-bearing

Carriers, warehouses and customs agents write the same instant as
`2026-03-14T06:10Z`, `2026-03-14 06:10`, `2026/03/14 06:10` or
`2026-03-14T06:10:00Z`. Two honest nodes copying from the same record can
return different spellings of the same moment. Every timestamp is therefore
normalised in code before it is stored, compared or used in arithmetic, and
the gate refuses a payload that is not already in that one spelling - so a
disagreement about a format cannot become a disagreement about a shipment.
The same applies to identifiers: `LOT-4471/B`, `lot 4471 b` and `LOT4471B`
reconcile to one value.

## What the reading stage is never asked

It is never shown the condition range, the window boundaries, the delivery
window, the declared order of the checkpoints, or the word "verdict". The
prompt says so explicitly, and `scripts/preflight.py` asserts that the blob
sent to the model carries none of them.

| Question nobody asks a model | Who answers it |
|---|---|
| did the checkpoints happen in the right order? | code, from the instants the records state |
| did the readings stay in range? | code, comparing integer tenths |
| was an excursion short enough to allow? | code, summing minutes between readings |
| was delivery inside the window? | code |
| do the identifiers agree? | code, after normalising them |
| was the source authentic? | code, comparing hosts |
| does this record instruct its reader? | code, counting markers |
| what is the verdict? | code, by precedence |

## Failure

| What failed | What happens |
|---|---|
| a record cannot be fetched, or its hash does not match, or it is too large or unreadable | that record is `RECORD_UNAVAILABLE` with a reason; if a required kind is lost with it, the reading stage is skipped and the verdict is `EVIDENCE_UNAVAILABLE` |
| the reading call itself fails | the round raises `[TRANSIENT]`; a validator agrees only if it cannot reach the reading stage either |
| the answer is unusable - malformed, wrong row counts, unknown enum, wrong type | `panel_state` is `INVALID`, the findings are the one empty shape, and the verdict is `EVIDENCE_UNAVAILABLE`, retryable |
| a finding is not grounded in the bytes | it is downgraded to uncertainty, never to its opposite |
| validators disagree | nothing is stored; the submission stays `PENDING` and may be resolved again |
| the transaction is protocol-level `UNDETERMINED` | that is not a contract outcome; no state changed and the round can be run again |

`EVIDENCE_UNAVAILABLE` and `INCONSISTENT_EVIDENCE` are **recoverable**: they
say the records could not answer the question, so a new round or a corrected
record is the remedy. `CLAIM_SUPPORTED` and `CLAIM_NOT_ESTABLISHED` are
terminal: the records answered it. Rounds are capped at three, after which
the submission is `EXHAUSTED` and never consumable.

A protocol-level failure is not a finding about the world. An HTTP 503 does
not mean a shipment never moved.

## Why consensus is load-bearing

Remove consensus and the contract loses the only inputs it cannot compute:
which record evidences a checkpoint and what time it states, what identifier
each record carries, whether a stated origin satisfies the claimed one,
which readings a log contains, whether a criterion is met, and whether two
records materially conflict.

Keep a single reader instead of consensus and it loses something else: the
ability to tell a true reading from a purchased one. One operator - the
buyer's platform, the carrier, an auditor, or whoever rents the model - would
choose which records to read and author the answer, and every downstream
consumer would be trusting that operator rather than the evidence. One
demonstration record exists precisely to show the difference: it instructs
whoever reads it to confirm every checkpoint, and the contract counts those
instructions in code and refuses to let the claim stand.

What consensus does **not** do is prove a physical event. It establishes
whether the records produced for this shipment satisfy a requirement frozen
before they were produced. That is a narrower and more honest claim.
