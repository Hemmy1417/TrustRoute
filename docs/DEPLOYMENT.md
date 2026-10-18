# Deployment

Every deployment this contract has had on Studionet, what each one taught,
and how to reproduce the canonical one.

## The canonical deployment

| | |
|---|---|
| Network | GenLayer Studionet, chain **61999** |
| RPC | `https://studio.genlayer.com/api` |
| Contract | [`0xB70040Bca306122b795F7Cd9d7623aCe9175067B`](https://explorer-studio.genlayer.com/address/0xB70040Bca306122b795F7Cd9d7623aCe9175067B) |
| Deploy transaction | [`0xfb6e29ca7ba7439701c147b25575282abb32fa91d243274b09751c4ad364d134`](https://explorer-studio.genlayer.com/tx/0xfb6e29ca7ba7439701c147b25575282abb32fa91d243274b09751c4ad364d134) |
| Source | `contracts/trustroute.py` @ `5a464a2` |
| sha256 | `197fba21c20d17eb81c24e19eecd88025be61355623ab31fca303f41057ce9ca` |
| Size | 136,524 bytes |
| Lifecycle | FINALIZED |
| Execution | SUCCESS |
| Consensus | 3 agree / 0 disagree / 2 idle of 5 |

Idle validators are not disagreement. A round with three agreeing and two
idle reached a majority; nothing about it is weaker than five of five.

### That the deployed bytes are this source

`scripts/verify.py` asks the node for the contract code with
`gen_getContractCode`, base64-decodes it and hashes it. The result is
written into [`docs/proofs/live.md`](proofs/live.md) with every other
re-read fact, so the claim is checkable without trusting this file.

## Reproducing it

```bash
git clone https://github.com/Hemmy1417/TrustRoute.git
cd TrustRoute
pip install -r requirements.txt

gltest                                  # 359 Direct Mode tests
python scripts/preflight.py             # 216 invariants over the source
genvm-lint lint contracts/trustroute.py
genvm-lint check contracts/trustroute.py
```

The live driver deploys, runs the seven scenarios and writes the evidence:

```bash
python scripts/live.py --commit $(git rev-parse --short HEAD)
```

It needs the commit to be **pushed**, because the records it binds are
fetched by every validator from `raw.githubusercontent.com` at that exact
commit. It funds a freshly generated signer from the Studionet faucet, so
no key or balance is required.

To re-run the scenarios against a deployment that already exists:

```bash
python scripts/live.py --commit <sha> --address 0xB70040...067B
```

Ids carry a per-run tag, because a policy id is claimed once for the life
of a contract. Without it a second run against the same deployment would
collide on `register_policy`, which would have meant a fresh deployment
every time anyone wanted to reproduce the evidence. Pass `--tag <name>`
to name a run's ids instead of taking the generated one.

## Deployment history

Six deployments. Five are historical and are listed because what they
taught is the substance of the design — in particular that **every model
judgement in the consensus path is a way for a round to split**, which
only the live network demonstrates.

The hash column is the deployed bytes as the chain reports them, matched
against the committed source. It is evidence, not recollection.

<!-- HISTORY -->

### What each one taught

**1 — readings as positional pairs.** The first live round answered the
measurement series as `["2026-03-14T06:00Z", 48]` rather than
`{"time": …, "value_tenths": …}`. A positional pair carries the same
information in the same order, so it is a notation difference, like a
markdown fence. `_as_mapping` now reads either spelling, and nothing
semantic is normalised with it.

**2 — a prompt that described the answer without showing it.** The next
round answered every question correctly, in a structure of the model's own
invention: `log_record_id` for `record_id`, a `measurement_label` nobody
had asked for. Describing the questions is not the same as showing the
form, so the prompt now carries the exact JSON skeleton.

The same deployment exposed a second fault. The replay rule bound record
bytes to the *challenge*, so a bill of lading could not be evidence for
both a cold-chain requirement and a custody requirement on the same
shipment — which is a legitimate thing for a buyer and a carrier to do
separately. Evidence is now bound to the shipment or lot.

**3 — an explanation one sentence too long.** A complete, correct reading
was discarded because its `basis` ran past the bound. The basis is the one
field that is prose and nothing else: not compared between validators, not
derived from, not gated on. The bound is now applied to the text instead
of to the answer.

This deployment also taught the cheapest lesson in the list: the rejection
diagnostic was 160 characters of `repr`, which was not enough to act on.
One bug became three deployments for want of a usable error. The
diagnostic now prints the key set, the expected and actual row counts and
900 characters of the answer.

**4 — `NO_MAJORITY`.** Two validators were asked to copy the same
eleven-line temperature table out of a log, and summarised it differently.
Nothing was dishonest; the design was wrong. A model's extraction of a
measurement table had been made consensus-critical.

Code parses the log now. `_parse_series` reads one reading per line,
`_tenths_of` converts `4.8` to integer tenths without ever constructing a
float, and the range, excursion and ordering arithmetic are all
deterministic. The reading stage is no longer asked what the log says, or
whether the evidence is sufficient. A checkpoint's stated time must also
be an instant that occurs in the record relied on — previously any record
could be quoted, since `Lot number: LOT-4471/B` appears in all of them.

**5 — a question nobody asked.** Two faults, one of them mine.

The driver's own copy of the cold-chain requirement was missing the
`series_format` field the contract now requires, so the contract rejected
it — correctly. The driver was wrong, not the contract, and no redeploy
was needed to establish that: the reason was in the transaction receipt.

Then the real one. Four of seven scenarios were refused because a model
volunteered `origin: SUPPORTED` on policies that declare no origin
requirement. The records do name a growing region, so the answer was
reasonable — and `_origin_state` answers that question from the frozen
definition without ever reading the finding. The contract was discarding a
complete, correct reading of the records over data it had already decided
to ignore.

It was also a consensus hazard, which is the worse half: one scenario
split 1 agree / 3 disagree purely on which nodes happened to volunteer. An
undeclared origin or delivery section is now normalised to `NOT_ASSESSED`
rather than refused. Whether a requirement was declared is a fact about
the frozen definition, so every node normalises identically and the round
cannot split on it. The strict direction is unchanged: a *declared*
requirement answered `NOT_ASSESSED` is still a non-answer.

**6 — canonical.** Seven scenarios, every assertion held.

## The seven live scenarios

Recorded in [`docs/proofs/live.md`](proofs/live.md), re-read off the chain.

| | Scenario | Verdict | Status |
|---|---|---|---|
| A | a cold chain whose log holds the range across the window | `CLAIM_SUPPORTED` | RESOLVED |
| B | a cold chain with an eighteen-hour excursion | `CLAIM_NOT_ESTABLISHED` | RESOLVED |
| C | a custody chain whose checkpoints are out of order | `INCONSISTENT_EVIDENCE` | RETRYABLE |
| D | records that disagree about which lot they describe | `INCONSISTENT_EVIDENCE` | RETRYABLE |
| E | a record that instructs whoever reads it | `CLAIM_NOT_ESTABLISHED` | RESOLVED |
| F | a certificate not served from the host its issuer publishes from | `CLAIM_NOT_ESTABLISHED` | RESOLVED |
| G | a required record that cannot be fetched, then a retry | `EVIDENCE_UNAVAILABLE` | RETRYABLE |

Two of these are worth reading closely.

**C** derives `custody_state = OUT_OF_ORDER` in code, from the instants
the three scans state — `2026-03-14T06:10Z`, `2026-03-14T19:45Z`,
`2026-03-12T08:05Z`. The verdict is `INCONSISTENT_EVIDENCE` rather than
`CLAIM_NOT_ESTABLISHED` because the panel also found the records
materially conflicting, and a contradiction outranks an unsupported event
in the precedence. Both findings are correct and the more cautious one
wins.

**E** is the prompt-injection scenario. The record instructs whoever reads
it to confirm every checkpoint. The markers are counted in code, not
judged by the model, and the claim cannot stand with a count above zero —
note that its `custody_state` is `COMPLETE` and its evidence status
`EVIDENCE_SUFFICIENT`. The reading went fine; the record disqualified
itself.

## Notes on Studionet

- A round that reaches no majority **commits nothing and still reports
  the transaction as successful**. Lifecycle and votes must be read from
  `consensus_data.leader_receipt`, not inferred from the send.
- A transaction's top-level `execution_result` is `None`; the real result
  is in `consensus_data.leader_receipt[0]`.
- Contract `print()` output arrives in `genvm_result.stdout`, which is how
  four of the five failures above were diagnosed without redeploying.
- Reads are rate limited to roughly thirty a minute per address, which is
  why `scripts/verify.py` paces itself at 2.2 seconds.
- The faucet (`sim_fundAccount`) requires a browser user agent.
