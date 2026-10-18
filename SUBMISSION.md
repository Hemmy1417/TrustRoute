# Submission

Copy-ready. Everything here is measured, not estimated.

## Project

**TrustRoute** — adversarial supply-chain evidence verification.

**Repository** — <https://github.com/Hemmy1417/TrustRoute>

**Network** — GenLayer Studionet, chain 61999

**Contract** —
[`0xf2Fc34063eab9Ca8f531fEb5A5BbAd81Bb450150`](https://explorer-studio.genlayer.com/address/0xf2Fc34063eab9Ca8f531fEb5A5BbAd81Bb450150)

**Deploy transaction** —
[`0x9729f8d74b3242d929ed0dfe72c096440a7f5027f4f9f6b4cc556b68f0acdf96`](https://explorer-studio.genlayer.com/tx/0x9729f8d74b3242d929ed0dfe72c096440a7f5027f4f9f6b4cc556b68f0acdf96)

**Source** — `contracts/trustroute.py` @ `471b56b`,
sha256 `8088723dc96fbaf8937b8de15a80318e997a10aea9d23acc254765d7bac9d783`,
136,826 bytes. The deployed bytes are that file: `scripts/verify.py` reads
the contract back off the chain and compares the hash.

## Portal description

> TrustRoute decides whether supply-chain records actually establish that a shipment's required events occurred. The verification requirement is frozen on chain first: required record kinds, custody checkpoints and their order, a temperature range and allowed excursion, the host each issuer publishes from. Records held by different parties are then committed by hash.
>
> Every validator fetches each record itself, hashes it before anything reads it, and asks one bounded reading round only what needs prose read: which record evidences a checkpoint and what time it states, whether two records conflict. Everything mechanical is code - the log is parsed, the order checked against the instants the records state, excursions summed in integer tenths, issuer hosts compared, the verdict derived by precedence. No model is told the range or the declared order.
>
> Verdicts: CLAIM_SUPPORTED, CLAIM_NOT_ESTABLISHED, INCONSISTENT_EVIDENCE, EVIDENCE_UNAVAILABLE. It judges records, not reality, and says so.

*(997 characters.)*

## Why it needs GenLayer

Two things must hold at once: something must read prose documents, and
nobody must be able to choose what the reading says.

A deterministic contract can prove a document is the one committed; it
cannot tell whether `Event: container loaded and custody accepted by the
carrier` evidences the checkpoint `custody accepted by the carrier`. An
oracle or a single LLM moves the question to "who runs it" — the operator
picks which records to read and authors the answer, and a purchased
reading is indistinguishable from a true one.

Here each validator re-fetches, re-hashes, re-reads and re-derives, and
rejects a payload whose findings are not grounded in its own bytes or
whose verdict does not follow from its own findings.

## Verification

| Gate | Result |
|---|---|
| Direct Mode tests | 366 passed |
| Preflight invariants | 216 / 216 |
| GenVM lint | passed, 3 checks |
| GenVM check | 32 methods, 23 view / 9 write |
| Mutation sweep | 83 / 85 killed, 2 equivalent by construction, 0 survived |
| Live scenarios | 7 / 7, every assertion held |
| Live re-verification off chain | 112 checks, 0 discrepancies, 52 reads |
| Clean-clone reproduction | 366 tests, 216/216, lint + check green, `live.md` reproduced byte-identical |

Evidence: [`docs/proofs/live.md`](docs/proofs/live.md), regenerated from
the chain read-only.

## The seven live scenarios

| | Scenario | Verdict |
|---|---|---|
| A | a cold chain whose log holds the range across the window | `CLAIM_SUPPORTED` |
| B | a cold chain with an eighteen-hour excursion | `CLAIM_NOT_ESTABLISHED` |
| C | a custody chain whose checkpoints are out of order | `INCONSISTENT_EVIDENCE` |
| D | records that disagree about which lot they describe | `INCONSISTENT_EVIDENCE` |
| E | a record that instructs whoever reads it | `CLAIM_NOT_ESTABLISHED` |
| F | a certificate not served from the host its issuer publishes from | `CLAIM_NOT_ESTABLISHED` |
| G | a required record that cannot be fetched, then a retry | `EVIDENCE_UNAVAILABLE` |

## What the build taught

Seven deployments. Six are historical, and
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) records what each one taught,
because the live network found things no local test produced.

The one worth repeating: **every model judgement in the consensus path is
a way for a round to split.** An early version asked the reading stage to
copy the temperature series out of the log, and a live round reached
`NO_MAJORITY` because two models summarised the same eleven-line table
differently. Nothing was dishonest — the design was wrong. Code parses the
log now, and the reading stage is not asked what the log says or whether
the evidence is sufficient.

The same principle caught a second fault later: a field code never reads
must not be able to fail a round. Models volunteered an origin finding on
policies declaring no origin requirement, and the contract refused
complete, correct readings over data it had already decided to ignore —
splitting one round 1 agree / 3 disagree on which nodes happened to
volunteer.

## Limitations, stated plainly

- It judges records, not reality. A forged but internally consistent,
  authentically hosted record set will be `CLAIM_SUPPORTED`.
- Authenticity is host comparison, not signature verification, and the
  contract never claims otherwise.
- The condition log must be machine-readable: one reading per line.
- Bounded at 8 records, 6 custody events, 4 identity keys, 4 compliance
  criteria, 48 readings, 16 versions, 3 rounds.
- Studionet only. Not audited, not for production value.

## Licence

MIT, © 2026 hemmy1417.
