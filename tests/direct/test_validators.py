"""The validator, run against forged leader results.

`run_validator` replays the contract's own validator closure, so these are
not a simulation of the gate - they are the gate. Each test stages what one
node would have seen, hands the validator a leader result, and asserts the
vote. True-controls are included so a False is never just a broken setup.
"""

import copy
import json
import sys

import pytest

from conftest import (BILL_OF_LADING, COLD_CHAIN_RECORDS, CUSTODY_RECORDS,
                      LOG_COMPLIANT, SCAN_DESTINATION, SCAN_ORIGIN,
                      SCAN_TRANSIT, quote_from)

from test_verdicts import (BOL_CONTAINER, BOL_LOT, COMPLIANT_READINGS,
                           DEST_EVENT, DEST_LOT, LOG_CONTAINER, LOG_LOT,
                           LOG_READING, ORIGIN_EVENT, ORIGIN_LOT,
                           TRANSIT_EVENT, TRANSIT_LOT, cold_answer,
                           custody_answer)


@pytest.fixture
def verified(harness, cold_chain):
    """One cold-chain submission read honestly, with the payload it
    produced."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    return harness, payload


@pytest.fixture
def chain(harness, custody):
    """One custody submission read honestly."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    return harness, payload


def _vote(harness, payload):
    return harness.vm.run_validator(leader_result=json.dumps(payload))


def _restate(harness, payload):
    """Make a forged payload internally consistent again.

    The gate refuses a payload whose derived fields do not follow from its
    own findings, so an incoherent forgery never reaches the comparison.
    These forgeries are coherent: the only thing wrong with them is that
    they are not what this node read.
    """
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get(payload["submission_id"])
    context = harness.contract._context(record)
    context["round"] = payload["round"]
    module._derive_into(payload, context)
    return payload


# == the honest cases ======================================================

def test_an_honest_leader_is_agreed_with(verified):
    harness, payload = verified
    assert harness.vm.run_validator() is True
    assert _vote(harness, payload) is True


def test_different_prose_is_not_disagreement(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["findings"]["basis"] = "the log spans the window and holds range"
    assert _vote(harness, forged) is True


def test_a_different_grounded_quote_is_not_disagreement(chain):
    """Two nodes may quote different words from the same record for the same
    checkpoint. What must match is the finding and the instant."""
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["quote"] = ORIGIN_LOT
    assert _vote(harness, forged) is True


def test_a_checkpoint_quote_must_come_from_the_record_that_times_it(chain):
    """This freedom is narrower than it was, deliberately.

    A node used to be free to ground a checkpoint in any record, because
    `Lot number: LOT-4471/B` appears in every scan. Since a checkpoint's
    stated time must now be an instant its own record states, a quote from
    another record no longer supports the finding - and that is the point:
    it was one more thing two honest nodes could do differently, and a live
    round reached NO_MAJORITY.
    """
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["record_id"] = "R2"
    forged["findings"]["checkpoints"][0]["quote"] = TRANSIT_LOT
    assert _vote(harness, forged) is False


def test_a_different_quote_from_the_same_record_still_agrees(chain):
    """What remains free: which words of the right record were quoted."""
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["quote"] = ORIGIN_LOT
    assert _vote(harness, forged) is True


def test_a_different_count_of_corroborating_records_agrees(chain):
    """How many records happened to repeat an identifier is not the
    reconciliation; whether it reconciled, and to what value, is."""
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["identity"][0]["values"] = \
        forged["findings"]["identity"][0]["values"][:2]
    forged = _restate(harness, forged)
    assert forged["identity_summary"][0]["state"] == "RECONCILED"
    assert forged["identity_summary"][0]["records"] == 2
    assert _vote(harness, forged) is True


# == forged findings =======================================================

@pytest.mark.parametrize("finding", ["NOT_EVIDENCED", "UNCLEAR"])
def test_a_forged_checkpoint_finding_is_rejected(chain, finding):
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["finding"] = finding
    forged = _restate(harness, forged)
    assert _vote(harness, forged) is False


def test_a_forged_checkpoint_time_is_rejected(chain):
    """The instant a record states is a fact, and changing it is how a
    chain out of order would be made to look ordered."""
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][2]["stated_time"] = "2026-03-10T08:00Z"
    forged = _restate(harness, forged)
    assert _vote(harness, forged) is False


def test_a_forged_identity_value_is_rejected(chain):
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["identity"][0]["values"][0]["value"] = "LOT-9999/Z"
    forged = _restate(harness, forged)
    assert forged["identity_state"] == "CONFLICTING"
    assert _vote(harness, forged) is False


def test_forged_readings_are_rejected(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["findings"]["condition"]["readings"] = [
        {"time": "2026-03-14T06:00Z", "value_tenths": 50},
        {"time": "2026-03-15T00:00Z", "value_tenths": 150},
        {"time": "2026-03-16T18:00Z", "value_tenths": 50},
    ]
    forged = _restate(harness, forged)
    assert forged["condition_state"] == "BREACHED"
    assert _vote(harness, forged) is False


def test_a_forged_contradiction_is_rejected(chain):
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["contradiction"] = {"found": True,
                                           "record_ids": ["R1", "R2"],
                                           "quote": ORIGIN_EVENT}
    forged = _restate(harness, forged)
    # The quote is real, so the payload survives grounding and is still
    # refused: this node read no contradiction.
    assert forged["verdict"] == "INCONSISTENT_EVIDENCE"
    assert _vote(harness, forged) is False


def test_an_invented_quote_is_rejected_even_when_the_finding_matches(chain):
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["quote"] = \
        "the container was received into terminal custody as described"
    assert _vote(harness, forged) is False


def test_a_quote_from_another_record_than_the_one_named_is_rejected(chain):
    harness, payload = chain
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["quote"] = DEST_EVENT
    assert _vote(harness, forged) is False


# == forged facts about the records ========================================

@pytest.mark.parametrize("field,value", [
    ("status", "RECORD_UNAVAILABLE"),
    ("reason", "HASH_MISMATCH"),
    ("byte_count", 1),
    ("authenticity", "SOURCE_UNVERIFIED"),
])
def test_a_forged_record_row_is_rejected(verified, field, value):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["rows"][0][field] = value
    forged = _restate(harness, forged)
    assert _vote(harness, forged) is False


def test_a_forged_authenticity_claim_is_rejected(harness, custody):
    """The other direction: a leader claiming a source was authenticated
    when this node resolved it to a different host."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    harness.resolve("sub-1")
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    forged = copy.deepcopy(payload)
    for row in forged["rows"]:
        row["authenticity"] = "SOURCE_UNVERIFIED"
    forged = _restate(harness, forged)
    assert forged["authenticity_state"] == "SOURCE_UNVERIFIED"
    assert _vote(harness, forged) is False


def test_a_forged_missing_kinds_list_is_rejected(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["missing_required_kinds"] = ["BILL_OF_LADING"]
    forged = _restate(harness, forged)
    assert _vote(harness, forged) is False


def test_a_forged_directed_text_count_is_rejected(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["directed_text_hits"] = 0 if payload["directed_text_hits"] else 3
    forged = _restate(harness, forged)
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("submission_id", "sub-2"),
    ("challenge_id", "chal-9"),
    ("policy_id", "pol-9"),
    ("shipment_or_lot_id", "LOT-OTHER"),
    ("definition_hash", "0" * 64),
    ("evidence_digest", "0" * 64),
    ("policy_version", 2),
    ("round", 2),
    ("claim_type", "CUSTODY"),
    ("schema", "trustroute/2"),
])
def test_a_rebound_payload_is_rejected(verified, field, value):
    """A payload must be bound to the submission, the requirement and the
    round it claims to answer."""
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged[field] = value
    assert _vote(harness, forged) is False


# == payloads of the wrong shape ===========================================

def test_a_payload_with_a_missing_field_is_rejected(verified):
    harness, payload = verified
    for field in ("rows", "findings", "criteria", "verdict", "panel_state"):
        forged = copy.deepcopy(payload)
        del forged[field]
        assert _vote(harness, forged) is False


def test_a_payload_with_an_extra_field_is_rejected(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["recommendation"] = "accept"
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_a_wrongly_typed_round_is_rejected(verified, value):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["round"] = value
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("field,value", [
    ("verdict", "CLAIM_PROBABLY_FINE"),
    ("evidence_status", "EVIDENCE_GOOD_ENOUGH"),
    ("panel_state", "MOSTLY_ASSESSED"),
    ("custody_state", "FINE"),
    ("identity_state", "AGREED"),
    ("condition_state", "OK"),
    ("delivery_state", "ARRIVED"),
    ("origin_state", "TRUE"),
    ("compliance_state", "PASSED"),
    ("authenticity_state", "TRUSTED"),
])
def test_an_unknown_enum_value_is_rejected(verified, field, value):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged[field] = value
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("value", [1, "True", None, 1.0])
def test_a_criterion_that_is_not_a_boolean_is_rejected(verified, value):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["criteria"]["required_event_supported"] = value
    assert _vote(harness, forged) is False


def test_a_criterion_set_with_the_wrong_keys_is_rejected(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["criteria"]["bonus_criterion"] = True
    assert _vote(harness, forged) is False
    forged = copy.deepcopy(payload)
    del forged["criteria"]["records_consistent"]
    assert _vote(harness, forged) is False


@pytest.mark.parametrize("value", [-1, 1.0, True, "30"])
def test_a_wrongly_typed_excursion_is_rejected(verified, value):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["condition_worst_excursion_minutes"] = value
    assert _vote(harness, forged) is False


def test_a_row_count_that_does_not_match_the_submission_is_rejected(
        verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["rows"] = forged["rows"][:1]
    assert _vote(harness, forged) is False
    forged = copy.deepcopy(payload)
    forged["rows"].append(dict(forged["rows"][0]))
    assert _vote(harness, forged) is False


def test_rows_in_another_order_are_rejected(verified):
    """Rows are matched by position against the submitted records, so a
    reordering is a different claim about which record is which."""
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["rows"] = [forged["rows"][1], forged["rows"][0]]
    assert _vote(harness, forged) is False


def test_an_unreadable_record_cannot_be_authenticated(harness, cold_chain):
    """A row may not say the bytes failed to arrive and were nevertheless
    served by the right host."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    harness.resolve("sub-1")
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    forged = copy.deepcopy(payload)
    forged["rows"][0]["authenticity"] = "AUTHENTICATED_ORIGIN"
    assert _vote(harness, forged) is False


# == outcomes that do not follow from the payload's own findings ===========

def test_a_verdict_that_does_not_follow_is_refused_by_the_gate(verified):
    """The gate re-derives every outcome. A leader cannot report a verdict
    its own findings contradict, which is what makes the comparison between
    validators safe to keep narrow."""
    harness, payload = verified
    for verdict in ("CLAIM_NOT_ESTABLISHED", "INCONSISTENT_EVIDENCE",
                    "EVIDENCE_UNAVAILABLE"):
        forged = copy.deepcopy(payload)
        forged["verdict"] = verdict
        assert _vote(harness, forged) is False


def test_a_criterion_that_does_not_follow_is_refused_by_the_gate(verified):
    harness, payload = verified
    for field in ("required_records_present", "records_consistent",
                  "source_authenticity_verified", "required_event_supported"):
        forged = copy.deepcopy(payload)
        forged["criteria"][field] = not forged["criteria"][field]
        assert _vote(harness, forged) is False


def test_a_derived_state_that_does_not_follow_is_refused(verified):
    harness, payload = verified
    forged = copy.deepcopy(payload)
    forged["condition_state"] = "BREACHED"
    assert _vote(harness, forged) is False
    forged = copy.deepcopy(payload)
    forged["condition_worst_excursion_minutes"] = 99
    assert _vote(harness, forged) is False


def test_an_unassessed_round_may_not_carry_findings(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    harness.resolve("sub-1")
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert payload["panel_state"] == "SKIPPED"
    forged = copy.deepcopy(payload)
    forged["findings"]["sufficient"] = True
    assert _vote(harness, forged) is False
    forged = copy.deepcopy(payload)
    forged["findings"]["basis"] = "the records were fine really"
    assert _vote(harness, forged) is False


def test_a_skipped_round_with_nothing_missing_is_refused(verified):
    """SKIPPED is only legal when a required kind was unreadable. Claiming
    it with every record in hand is a way to avoid reading them."""
    harness, payload = verified
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record)
    context["round"] = payload["round"]
    forged = copy.deepcopy(payload)
    forged["panel_state"] = "SKIPPED"
    forged["findings"] = module._unassessed(context)
    forged = _restate(harness, forged)
    assert _vote(harness, forged) is False


# == a coherent forgery: only the comparison can catch it ==================

def test_a_coherent_but_untrue_reading_is_rejected(chain):
    """The hardest case: a payload that passes every structural check, whose
    every derived field follows from its own findings, and which this node
    simply did not read."""
    harness, payload = chain

    missing = copy.deepcopy(payload)
    missing["findings"]["checkpoints"][2]["finding"] = "NOT_EVIDENCED"
    missing["findings"]["checkpoints"][2]["record_id"] = ""
    missing["findings"]["checkpoints"][2]["quote"] = ""
    missing["findings"]["checkpoints"][2]["stated_time"] = ""
    missing = _restate(harness, missing)
    assert missing["custody_state"] == "INCOMPLETE"
    assert missing["verdict"] == "CLAIM_NOT_ESTABLISHED"
    assert _vote(harness, missing) is False

    conflicting = copy.deepcopy(payload)
    conflicting["findings"]["identity"][0]["values"][1]["value"] = "LOT-1/A"
    conflicting = _restate(harness, conflicting)
    assert conflicting["verdict"] == "INCONSISTENT_EVIDENCE"
    assert _vote(harness, conflicting) is False


def test_a_coherent_claim_that_the_records_were_unreadable_is_rejected(
        verified):
    """A payload saying nothing could be read, consistent all the way
    through, from a node that read everything."""
    harness, payload = verified
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record)
    context["round"] = payload["round"]

    forged = copy.deepcopy(payload)
    for row in forged["rows"]:
        row["status"] = "RECORD_UNAVAILABLE"
        row["reason"] = "FETCH_FAILED"
        row["byte_count"] = 0
        row["authenticity"] = "SOURCE_UNVERIFIED"
    forged["panel_state"] = "SKIPPED"
    forged["findings"] = module._unassessed(context)
    forged["missing_required_kinds"] = ["CONDITION_LOG", "BILL_OF_LADING"]
    forged["directed_text_hits"] = 0
    forged = _restate(harness, forged)
    assert forged["verdict"] == "EVIDENCE_UNAVAILABLE"
    assert _vote(harness, forged) is False


# == leader failures =======================================================

def test_an_unexplained_leader_failure_is_rejected(verified):
    harness, _payload = verified
    assert harness.vm.run_validator(leader_error=Exception("boom")) is False
    assert harness.vm.run_validator(
        leader_error=Exception("[EXPECTED] no such submission")) is False


def test_a_transient_leader_failure_is_agreed_with_only_when_shared(
        verified):
    """A leader that could not reach the reading stage is believed only by a
    node that cannot reach it either. The round is captured by the honest
    resolve above; the mocks are then changed under it, which is how this
    node comes to see a different world."""
    harness, _payload = verified
    harness.clear()
    # The records are still reachable for this node, but no reading stage
    # is: the model mock is gone.
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    assert harness.vm.run_validator(
        leader_error=Exception("[TRANSIENT] the model call failed")) is True

    # And a node that CAN read is not entitled to agree that nobody could.
    harness.mock_panel(cold_answer(harness))
    assert harness.vm.run_validator(
        leader_error=Exception("[TRANSIENT] the model call failed")) is False


def test_a_panel_failure_claimed_by_the_leader_is_never_agreed_with(
        verified):
    """A reading-stage failure is never ratified: the next round can read
    the records again."""
    harness, _payload = verified
    assert harness.vm.run_validator(
        leader_error=Exception("[PANEL] the ratified payload failed the gate")
    ) is False
