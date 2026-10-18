# Integration

How another Intelligent Contract uses TrustRoute. The consumer needs no web
access, no model, no equivalence rule and no knowledge of how a round works.

## The smallest useful interface

```python
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


@gl.contract_interface
class ITrustRoute:
    class View:
        def is_claim_supported(self, submission_id: str,
                               as_of: str) -> bool: ...
        def claim_outcome(self, submission_id: str, as_of: str) -> str: ...
        def get_verdict(self, submission_id: str) -> str: ...
        def get_policy_hash(self, challenge_id: str) -> str: ...
        def freshness(self, submission_id: str, as_of: str) -> str: ...


TRUSTROUTE = Address("0x0000000000000000000000000000000000000000")
```

## A goods-receipt gate

The whole integration is one boolean. It is false for everything uncertain -
an unresolved submission, a contradiction, an unreadable record, a stale
verdict, a revoked requirement - so a consumer that forgets to handle a case
fails closed.

```python
class GoodsReceipt(gl.Contract):
    def _accept(self, submission_id: str, as_of: str) -> None:
        ok = ITrustRoute(TRUSTROUTE).view().is_claim_supported(
            submission_id, as_of)
        if not ok:
            raise gl.vm.UserError(
                "EXPECTED: the records do not establish this delivery")
        # ... book the receipt
```

## Checking which requirement answered the question

A consumer that cares *which* requirement a verdict was produced against -
and it should, because a buyer and a carrier may both open challenges with
different rules - binds the hash it expects:

```python
    def _accept_under(self, submission_id: str, challenge_id: str,
                      expected_definition_hash: str, as_of: str) -> None:
        view = ITrustRoute(TRUSTROUTE).view()
        if view.get_policy_hash(challenge_id) != expected_definition_hash:
            raise gl.vm.UserError("EXPECTED: not the agreed requirement")
        if not view.is_claim_supported(submission_id, as_of):
            raise gl.vm.UserError("EXPECTED: not established")
```

`definition_hash` covers the whole definition - the claim type, the required
record kinds, the checkpoints and their order, the identity keys, the
condition range and window, the delivery window, the compliance criteria and
the issuer-to-host registry. Any change to any of them is a different hash
and a different version.

## Reading the whole picture in one call

`claim_outcome(submission_id, as_of)` returns JSON for a consumer that needs
to route rather than simply gate:

```json
{
  "submission_id": "sub-cold-ok",
  "challenge_id": "chal-cold-ok",
  "shipment_or_lot_id": "LOT-4471-B",
  "status": "RESOLVED",
  "verdict": "CLAIM_SUPPORTED",
  "evidence_status": "EVIDENCE_SUFFICIENT",
  "criteria": {
    "required_records_present": true,
    "records_consistent": true,
    "source_authenticity_verified": true,
    "required_event_supported": true
  },
  "custody_state": "NOT_DECLARED",
  "identity_state": "CONSISTENT",
  "condition_state": "HELD",
  "delivery_state": "NOT_DECLARED",
  "origin_state": "NOT_ASSESSED",
  "compliance_state": "NOT_ASSESSED",
  "authenticity_state": "AUTHENTICATED_ORIGIN",
  "directed_text_hits": 0,
  "policy_id": "pol-cold-ok",
  "policy_version": 1,
  "definition_hash": "…",
  "freshness": "RELIABLE",
  "claim_supported": true,
  "consumable": true
}
```

### How to route on it

| What you read | What it means for you |
|---|---|
| `claim_supported` true | the records establish the required event under that exact requirement |
| `verdict` `CLAIM_NOT_ESTABLISHED` | they do not. **Not** a finding that the claim is false - ask for better records, or escalate |
| `verdict` `INCONSISTENT_EVIDENCE` | the records disagree with each other. A human or a corrected record is needed; this is not a judgement about the shipment |
| `verdict` `EVIDENCE_UNAVAILABLE` | nobody could read what was submitted. Retry, or ask for a reachable location |
| `consumable` false | do not rely on this at all yet - it is pending, unsettled, exhausted, stale or blocked |
| `freshness` `STALE` | the verdict is older than thirty days; re-adjudicate if the decision matters |
| `freshness` `BLOCKED` | the requirement it answered has been revoked |
| `directed_text_hits` above zero | a submitted record contained text addressed to its reader. Worth a human looking at it |

## Three consumers, one contract

1. **Procurement and goods receipt** - gate acceptance of a delivery against
   a purchase order on `is_claim_supported`.
2. **Cold-chain and logistics dispute handling** - read `get_findings` and
   `get_custody_chain` to see which checkpoint is unevidenced, which
   identifier disagrees, or how long an excursion ran, with the words each
   finding rests on.
3. **Auditors, certification workflows and risk engines** - read
   `policy_record(policy_id, version)` for the accumulating record of one
   requirement, and `get_evidence_status` to tell "we checked and it failed"
   from "nobody could read the records".

A settlement contract is a fourth: TrustRoute moves no money, so escrow
logic composes on top rather than competing with it.

## What a consumer must not do

- **Do not read raw storage fields and re-implement the semantics.** Use the
  views. `is_claim_supported` already folds in the verdict, the status,
  staleness and revocation.
- **Do not treat `CLAIM_NOT_ESTABLISHED` as proof of a false claim.** It
  means the records did not establish the event.
- **Do not cache a verdict indefinitely.** Pass your own `as_of` and respect
  `freshness`; a requirement can be revoked after a verdict.
- **Do not assume a hash proves a fact.** It proves the bytes are the bytes
  that were committed. Everything beyond that is what the adjudication is
  for, and even then it is a statement about records, not about the world.

## Writing side, for completeness

A consumer that also drives the lifecycle calls, in order:
`register_policy`, `publish_policy_version`,
`open_verification_challenge`, `submit_records`, `resolve_submission`, and -
only if the round could not answer - `retry_submission`.

Only the policy owner may publish or revoke a version; only the challenge
opener may cancel a challenge; the submitter or the opener may cancel or
retry a submission. **Anyone** may call `resolve_submission`, because running
a round confers no power over its outcome.
