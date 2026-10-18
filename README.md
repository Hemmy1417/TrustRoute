<p align="center">
  <img src="docs/assets/trustroute-mark.svg" alt="TrustRoute" width="96" height="96">
</p>

<h1 align="center">TrustRoute</h1>

<p align="center">
  <em>Do the records establish that the shipment's required events
  actually occurred?</em>
</p>

A supply-chain verification requirement is registered and frozen. Records
held by different parties — carrier scans, a bill of lading, a reefer
temperature log, a customs entry, an origin certificate — are committed by
hash and fetched independently by every validator. One consensus round
reads them, and code derives a verdict from what was read.

The question is not whether the paperwork is well-formed. It is whether
records held by **separate parties reconcile with each other and with the
physical sequence they claim**.

```
CLAIM_SUPPORTED · CLAIM_NOT_ESTABLISHED · INCONSISTENT_EVIDENCE · EVIDENCE_UNAVAILABLE
```

## Canonical deployment

| | |
|---|---|
| Network | GenLayer Studionet, chain **61999** |
| Contract | [`0xB70040Bca306122b795F7Cd9d7623aCe9175067B`](https://explorer-studio.genlayer.com/address/0xB70040Bca306122b795F7Cd9d7623aCe9175067B) |
| Deploy transaction | [`0xfb6e29ca7ba7439701c147b25575282abb32fa91d243274b09751c4ad364d134`](https://explorer-studio.genlayer.com/tx/0xfb6e29ca7ba7439701c147b25575282abb32fa91d243274b09751c4ad364d134) |
| Source | [`contracts/trustroute.py`](contracts/trustroute.py) @ [`5a464a2`](https://github.com/Hemmy1417/TrustRoute/commit/5a464a2) |
| sha256 of those bytes | `197fba21c20d17eb81c24e19eecd88025be61355623ab31fca303f41057ce9ca` |
| Size | 136,524 bytes |
| Deploy consensus | FINALIZED, SUCCESS, 3 agree / 0 disagree / 2 idle of 5 |

The deployed bytes are the committed file, and that is checked rather than
asserted: `scripts/verify.py` reads the contract back with
`gen_getContractCode`, decodes it and compares the hash. Its output is
[`docs/proofs/live.md`](docs/proofs/live.md), regenerated from the chain
with no keys and no writes.

## The problem

A buyer will not pay for a container of pharmaceuticals until someone
establishes that the cold chain held. The evidence for that sits with four
parties who do not trust each other and have no shared system: the
shipper's packing list, the carrier's scans, a reefer log written by a
datalogger, a customs entry. Each is a plain document. Each can be
produced truthfully, produced carelessly, or produced to order.

Today the reconciliation is done by a person reading PDFs, or by whichever
platform the parties happen to share — which means every downstream
consumer is trusting that reader rather than the records.

The hard part is not storing the documents. It is that **reading them is a
judgement**, the judgement decides money, and the party best placed to
make it is usually the party with an interest in the answer.

## Why this needs GenLayer

Two things have to be true at once: the records must be read by something
that can read prose, and nobody must be able to choose what the reading
says.

A validator here independently fetches every record over
`gl.nondet.web.get`, hashes it before anything interprets it, and asks the
same bounded questions over `gl.nondet.exec_prompt`. It then re-derives
every outcome from its own reading and compares. A leader cannot author
the answer, because a validator that fetched the same bytes and read them
honestly will refuse a payload whose findings are not grounded in those
bytes or whose verdict does not follow from its own findings.

### Delete GenLayer and what breaks

| Replace it with | What fails |
|---|---|
| An oracle | Someone must still read the records and decide whether a checkpoint is evidenced. The oracle is that someone, and now the whole question is "who runs the oracle" |
| A deterministic contract plus hashes | It can prove a document is the one committed. It cannot tell whether `Event: container loaded and custody accepted by the carrier` evidences the checkpoint `custody accepted by the carrier` |
| One LLM behind an API | The operator chooses which records to read and authors the answer. A purchased reading is indistinguishable from a true one |
| A multisig of human attestors | Works, slowly, and only while the attestors are disinterested — which is exactly what cannot be assumed of a carrier, a buyer or a platform |

What consensus does **not** do is prove a physical event. It establishes
whether the records produced for this shipment satisfy a requirement
frozen before they were produced. That is narrower and more honest.

## State machine

```
register_policy ──► publish_policy_version (v1, v2, …) ──► revoke_policy_version
                              │
                              ▼
                    open_verification_challenge ──► cancel_challenge
                              │
                              ▼
                        submit_records  ── PENDING
                              │
                              ▼
                      resolve_submission
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
        RESOLVED          RETRYABLE         (no majority:
   CLAIM_SUPPORTED    EVIDENCE_UNAVAILABLE   stays PENDING,
   CLAIM_NOT_         INCONSISTENT_EVIDENCE  nothing stored)
     ESTABLISHED            │
                            ├── retry_submission ──► PENDING
                            └── after 3 rounds ───► EXHAUSTED
```

A challenge is opened against **one frozen policy version**, and the
submission records the `definition_hash` it was judged under. Republishing
or revoking a version afterwards cannot change what an existing verdict
meant.

`CLAIM_SUPPORTED` and `CLAIM_NOT_ESTABLISHED` are terminal: the records
answered the question. `EVIDENCE_UNAVAILABLE` and `INCONSISTENT_EVIDENCE`
are recoverable — they say the records *could not* answer it, so another
round or a corrected record is the remedy.

## Contract surface

32 methods: 9 writes, 23 views.

### Writes

| Method | What it does |
|---|---|
| `register_policy` | claims a policy id for the sender |
| `publish_policy_version` | freezes a verification requirement; returns the version number |
| `revoke_policy_version` | stops new reliance on a version without rewriting history |
| `open_verification_challenge` | binds a shipment or lot claim to one frozen version |
| `cancel_challenge` | closes a challenge to further submissions |
| `submit_records` | commits up to 8 records by https location, sha256, kind and declared issuer |
| `resolve_submission` | the one nondeterministic round |
| `retry_submission` | another round after a recoverable outcome, up to 3 |
| `cancel_submission` | withdraws a pending submission |

### Views

`get_config`, `get_policy`, `get_policy_version`, `get_policy_hash`,
`get_policy_version_of`, `get_challenge`, `get_challenge_status`,
`get_submission`, `get_verdict`, `get_evidence_status`, `get_findings`,
`get_custody_chain`, `get_condition_report`, `get_receipt`,
`is_claim_supported`, `is_consumable`, `freshness`, `is_fresh`,
`claim_outcome`, `policy_record`, `list_submissions`, `record_first_seen`,
`get_stats`.

## Nondeterministic operations

One `gl.vm.run_nondet_unsafe` per round, with a custom validator.

| Call | Where | What comes back |
|---|---|---|
| `gl.nondet.web.get` | once per record | status and body, hashed before anything reads it |
| `gl.nondet.exec_prompt` | once per round | strict JSON answering six bounded questions |

The reading stage is asked only what requires reading prose: which record
evidences a checkpoint and what time that record states, what identifier
each record carries, whether a stated origin satisfies the claimed one,
whether a declared criterion is met, and whether two records materially
conflict.

## What code decides, not a model

| Question | Who answers it |
|---|---|
| did the checkpoints happen in the declared order? | code, from the instants the records state |
| what readings does the temperature log contain? | code, parsing the log itself |
| did the readings stay in range? | code, comparing integer tenths — no float is ever constructed |
| was an excursion short enough to allow? | code, summing minutes between readings |
| was delivery inside the window? | code |
| do the identifiers agree? | code, after normalising them |
| was the source authentic? | code, comparing the host the bytes came from with the host the requirement registers for that issuer |
| does this record instruct its reader? | code, counting markers |
| what is the verdict? | code, by precedence |

This split is the design, and it was not free. An earlier version asked
the model to copy the measurement series out of the log; a live round
reached `NO_MAJORITY` because two models summarised the same eleven-line
table differently. **Every judgement in the consensus path is a way for a
round to split**, so everything mechanical belongs in code.

The prompt is held to this: `scripts/preflight.py` asserts that the blob
sent to the model carries no condition range, no window boundary, no
declared checkpoint order, and not the word "verdict".

## Equivalence

Must match across validators: the schema and identifiers, the policy
version and `definition_hash`, the evidence digest, every record's status
and authenticity, each checkpoint's finding and stated instant, the
identity reconciliation, the custody, condition, delivery, origin,
compliance and authenticity states, the readings code parsed out of the
log, the four criteria, the evidence status and the verdict.

May differ: the sentence of reasoning, and which grounded span of the
right record was quoted.

In one line: **the facts must match, the outcome must match, and the
reasoning may differ.**

The gate is what makes that safe to keep narrow. `_parse_payload` refuses
a leader's payload unless every quote is grounded in *this node's* bytes
and every derived field — including the four criteria and the verdict — is
exactly what this contract's own code derives from the payload's own
findings. A validator that only checked JSON shape would not be a
validator. [`docs/CONSENSUS.md`](docs/CONSENSUS.md) has the full account.

## Failure semantics

| What failed | What happens |
|---|---|
| a record cannot be fetched, its hash does not match, or it is too large | that record is `RECORD_UNAVAILABLE` with a reason; if a required kind is lost with it, the reading stage is skipped entirely and the verdict is `EVIDENCE_UNAVAILABLE` |
| the model call itself fails | the round raises `[TRANSIENT]`; a validator agrees only if it cannot reach the reading stage either |
| the answer is unusable | `panel_state` is `INVALID`, findings are the one empty shape, verdict is `EVIDENCE_UNAVAILABLE`, retryable |
| a finding is not grounded in the bytes | it is downgraded to uncertainty, never to its opposite |
| validators disagree | nothing is stored; the submission stays `PENDING` and can be resolved again |
| the transaction is protocol-level `UNDETERMINED` | not a contract outcome; no state changed |

A protocol-level failure is not a finding about the world. An HTTP 503
does not mean a shipment never moved.

## Reuse surface

A consumer should never re-implement the reliance rules:

```python
is_claim_supported(submission_id, as_of)  # terminal + supported + fresh + not revoked
is_consumable(submission_id, as_of)       # safe to act on at all
freshness(submission_id, as_of)           # RELIABLE | STALE | BLOCKED | UNKNOWN
claim_outcome(submission_id, as_of)       # the whole reliance answer, one call
```

`get_receipt` returns everything needed to argue a dispute: the policy
version, the `definition_hash`, the evidence digest, the verdict, and the
findings with the words each rests on.
[`docs/INTEGRATION.md`](docs/INTEGRATION.md) has worked examples.

## Limitations

- **It judges records, not reality.** A perfectly forged, authentically
  hosted set of records that agree with each other will be
  `CLAIM_SUPPORTED`. The contract says so in those words rather than
  claiming to have verified a shipment.
- **Authenticity is host comparison, not signature verification.** The
  contract compares the host that served the bytes with the host the
  requirement registers for that issuer. It never claims a signature was
  checked.
- **The condition log must be machine-readable.** One reading per line,
  timestamp first and measurement last. A scanned PDF of a chart recorder
  is out of scope, and the contract reports `UNREADABLE` rather than
  guessing.
- **Bounded.** 8 records, 6 custody events, 4 identity keys, 4 compliance
  criteria, 48 readings, 16 versions, 3 rounds.
- **Very large, quote-heavy records can exhaust the prompt budget.** Eight
  records made of characters JSON must escape exceed the 60,000-character
  cap once escaped, and the blob truncates. It is deterministic and fails
  closed to `EVIDENCE_UNAVAILABLE`, so it cannot split a round or produce a
  wrong verdict, but a legitimate submitter gets no explanation naming the
  cause. Found in the final audit and documented rather than patched into a
  frozen deployment; `docs/SECURITY.md` has the reasoning.
- **Studionet only.** Not audited, not for production value.

## Verification

Everything below was measured at the deployed source,
sha256 `197fba21…57ce9ca`.

| Gate | Result | How to reproduce |
|---|---|---|
| Direct Mode suite | 366 passed | `gltest` |
| Preflight invariants | 216 / 216 | `python scripts/preflight.py` |
| GenVM lint | passed, 3 checks | `genvm-lint lint contracts/trustroute.py` |
| GenVM check | 32 methods, 23 view / 9 write | `genvm-lint check contracts/trustroute.py` |
| Mutation sweep | 83 / 85 killed, 2 equivalent by construction, 0 survived | `python -u scripts/mutate.py > sweep.log` |
| Live scenarios | 7 / 7, every assertion held | `python scripts/live.py --commit <sha>` |
| Live re-verification | 112 checks, 0 discrepancies, 51 reads | `python scripts/verify.py` |
| Clean-clone reproduction | 366 tests, 216/216, lint + check green, `live.md` reproduced byte-identical | clone, install, run the gates |

The mutation sweep is the gate worth explaining: a green suite says the
contract passes its tests, not that the tests would notice if a guard were
removed. The sweep removes one guard at a time in a scratch copy and runs
the whole suite against it. A mutant that survives is a hole in the tests,
and is reported as one rather than explained away.

**How that figure was reached, exactly.** The first full pass over the
frozen source killed 75, declared 3 equivalent by construction, and left 7
survivors. One was a real missing test. The other six were masked by a
correlated field that was still compared — which is precisely what an
integration test cannot distinguish — so `_first_difference` was given
direct, field-by-field tests. Re-running those 7 killed all of them, and
one of the 3 equivalents fell to the new test that pins the documented
comparison set. Combining the two runs is sound because tests were only
**added** between them, and an added test cannot un-kill a mutant; no
existing test was weakened and the contract was not touched. The 2
remaining equivalents are listed with their arguments in
`scripts/mutate.py`, and the sweep exits non-zero on any undocumented
survivor.

### The clean-clone gate

A fresh `git clone` of this repository, on a different path, with nothing
from the build environment: 366 tests passed, 216/216 preflight, lint and
check green, and `contracts/trustroute.py` hashed to
`197fba21…57ce9ca` — the same bytes the chain reports for the canonical
deployment. Running `scripts/verify.py` from that clone regenerated
`docs/proofs/live.md` **byte-identical** to the committed copy, which is
the part worth taking seriously: the live evidence in this repository is
not a transcript of my session, it is a document anyone can rebuild from
the chain.

Line endings are pinned by `.gitattributes` (`* text=auto eol=lf`), which
is what makes the deployed bytes platform-independent and the hash stable
on a Windows checkout.

## Reviewer fast path

Five minutes, in this order:

1. [`DECISION.md`](DECISION.md) — why this primitive, and the collision
   audit against every repository that came close.
2. [`docs/CONSENSUS.md`](docs/CONSENSUS.md) — what nodes must agree on,
   what they may differ on, and the freedoms removed after a live round
   split.
3. `_derive_verdict` in [`contracts/trustroute.py`](contracts/trustroute.py)
   — the whole decision, as a precedence list, in code.
4. [`docs/proofs/live.md`](docs/proofs/live.md) — the seven live scenarios,
   re-read off the chain rather than quoted from the run that made them.
5. [`tests/direct/test_live_lessons.py`](tests/direct/test_live_lessons.py)
   — the five things the live network did that the mocks did not.

## Layout

```
contracts/trustroute.py      the one deployable contract
tests/direct/                366 Direct Mode tests
scripts/preflight.py         216 invariants over the source itself
scripts/mutate.py            the mutation sweep
scripts/live.py              the seven live scenarios
scripts/verify.py            read-only re-verification from the chain
docs/CONSENSUS.md            equivalence, failure, why consensus is load-bearing
docs/SECURITY.md             the adversary model
docs/INTEGRATION.md          how a consumer uses this
docs/proofs/live.md          the live evidence
DECISION.md                  why this primitive
```

## Licence

MIT — see [LICENSE](LICENSE).
