"""Tests written because the mutation sweep found them missing.

Every test here closes a specific mutation that survived a sweep: the
contract was right, and the suite would not have noticed if it had been
wrong. The mutation each one kills is named in its docstring, so a later
reader can check the claim rather than take it on trust.
"""

import copy
import json
import sys

import pytest

from conftest import (AS_OF, BILL_OF_LADING, COLD_CHAIN_RECORDS,
                      COMPLIANCE_CLAIM, CUSTODY_RECORDS, CARRIER, CUSTOMS,
                      CUSTOMS_ENTRY, INSPECTION, LOG_COMPLIANT,
                      ORIGIN_CERTIFICATE, ORIGIN_CLAIM, WAREHOUSE_RECEIPT,
                      record, record_sha, url_for)
from test_verdicts import (BOL_LOT, CERT_LOT, CERT_REGION, ENTRY_LOT,
                           ENTRY_ORIGIN, INSPECTION_FINDING, INSPECTION_LOT,
                           LOG_LOT, cold_answer, resolved)


# == grounding: the two findings no test reached ===========================

def test_an_ungrounded_compliance_finding_is_downgraded(harness):
    """Kills `grounding: an ungrounded compliance finding keeps its force`.

    A criterion read as met, with words that are not in the record named,
    becomes unclear - not met, and not its opposite either.
    """
    harness.register("pol-k")
    harness.publish("pol-k", COMPLIANCE_CLAIM)
    harness.open_challenge("pol-k", 1, "chal-k")
    harness.mock_records(INSPECTION, CUSTOMS_ENTRY)
    records = [record("R1", INSPECTION, "INSPECTION_CERTIFICATE", CUSTOMS),
               record("R2", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS)]
    harness.submit("chal-k", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", INSPECTION_LOT),
                           ("R2", "LOT-4471/B", ENTRY_LOT)])],
        compliance=[("K1", "MET", "R1",
                     "the consignment was found entirely fit for export")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["compliance_state"] == "UNCLEAR"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["compliance"][0]["finding"] == "UNCLEAR"
    assert findings["compliance"][0]["quote"] == ""


def test_an_ungrounded_refusal_of_a_criterion_is_also_downgraded(harness):
    """The same rule in the other direction: an ungrounded NOT_MET must not
    stand either, or an unfounded refusal would carry as much weight as a
    grounded one."""
    harness.register("pol-k")
    harness.publish("pol-k", COMPLIANCE_CLAIM)
    harness.open_challenge("pol-k", 1, "chal-k")
    harness.mock_records(INSPECTION, CUSTOMS_ENTRY)
    records = [record("R1", INSPECTION, "INSPECTION_CERTIFICATE", CUSTOMS),
               record("R2", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS)]
    harness.submit("chal-k", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", INSPECTION_LOT),
                           ("R2", "LOT-4471/B", ENTRY_LOT)])],
        compliance=[("K1", "NOT_MET", "R1",
                     "the inspection found live infestation in the lot")]))
    harness.resolve("sub-1")
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["compliance"][0]["finding"] == "UNCLEAR"


def test_an_ungrounded_origin_finding_is_downgraded(harness):
    """Kills `grounding: an ungrounded origin finding keeps its force`."""
    harness.register("pol-o")
    harness.publish("pol-o", ORIGIN_CLAIM)
    harness.open_challenge("pol-o", 1, "chal-o")
    harness.mock_records(CUSTOMS_ENTRY, ORIGIN_CERTIFICATE)
    records = [record("R1", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS),
               record("R2", ORIGIN_CERTIFICATE, "ORIGIN_CERTIFICATE",
                      CUSTOMS)]
    harness.submit("chal-o", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", ENTRY_LOT),
                           ("R2", "LOT-4471/B", CERT_LOT)])],
        origin={"finding": "SUPPORTED", "record_id": "R1",
                "quote": "the lot was grown in the region as declared"}))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["origin_state"] == "UNCLEAR"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["origin_state"] == "UNCLEAR"


# == a record that is not required, and not readable =======================

def test_an_unreadable_record_fails_the_claim_even_when_not_required(
        harness, cold_chain):
    """Kills `verdict: unreadable records are a reading`.

    Every other test reached that branch with a *required* record missing,
    which also skips the reading stage - so the panel-state branch was
    doing the work and the records-present branch was never tested. Here
    the unreadable record is an extra one, the reading stage runs normally,
    and the claim still cannot be established on records nobody could read.
    """
    harness, _policy_id, challenge_id = cold_chain
    extra = record("R3", WAREHOUSE_RECEIPT, "WAREHOUSE_RECEIPT", CUSTOMS)
    harness.submit(challenge_id, "sub-1",
                   list(COLD_CHAIN_RECORDS) + [extra])
    harness.clear()
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    harness.mock_record(WAREHOUSE_RECEIPT, status=404, body="not found")
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    stored = resolved(harness)
    # The reading stage did run: this is not the missing-kinds path.
    assert stored["panel_state"] == "ASSESSED"
    # The required kinds were all readable, so this is not the missing-kinds
    # path: the receipt proves that list was empty.
    receipt = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert receipt["missing_required_kinds"] == []
    assert stored["criteria"]["required_records_present"] is False
    assert stored["evidence_status"] == "EVIDENCE_UNAVAILABLE"
    assert stored["records"][2]["reason"] == "FETCH_FAILED"
    assert harness.contract.is_claim_supported("sub-1",
                                               "2026-03-21T09:30Z") is False


# == a disagreement about the origin =======================================

def test_two_nodes_that_read_the_origin_differently_do_not_agree(harness):
    """Kills `validator: the origin state is not compared`.

    The origin finding itself is not compared row by row, so `origin_state`
    is the only field that carries a disagreement about it. Without it, a
    leader could report a supported origin to a node that read the opposite.
    """
    harness.register("pol-o")
    harness.publish("pol-o", ORIGIN_CLAIM)
    harness.open_challenge("pol-o", 1, "chal-o")
    harness.mock_records(CUSTOMS_ENTRY, ORIGIN_CERTIFICATE)
    records = [record("R1", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS),
               record("R2", ORIGIN_CERTIFICATE, "ORIGIN_CERTIFICATE",
                      CUSTOMS)]
    harness.submit("chal-o", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", ENTRY_LOT),
                           ("R2", "LOT-4471/B", CERT_LOT)])],
        origin={"finding": "SUPPORTED", "record_id": "R1",
                "quote": ENTRY_ORIGIN}))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))

    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1

    # A coherent payload that read the origin the other way. Its quote is
    # real, so it survives grounding, and every other compared fact matches.
    forged = copy.deepcopy(payload)
    forged["findings"]["origin"] = {"finding": "NOT_SUPPORTED",
                                    "record_id": "R1",
                                    "quote": ENTRY_ORIGIN}
    module._derive_into(forged, context)
    assert forged["origin_state"] == "NOT_SUPPORTED"
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


def test_two_nodes_that_read_a_criterion_differently_do_not_agree(harness):
    """The same for the compliance state, which the criterion rows do carry
    - this fixes that both routes refuse it."""
    harness.register("pol-k")
    harness.publish("pol-k", COMPLIANCE_CLAIM)
    harness.open_challenge("pol-k", 1, "chal-k")
    harness.mock_records(INSPECTION, CUSTOMS_ENTRY)
    records = [record("R1", INSPECTION, "INSPECTION_CERTIFICATE", CUSTOMS),
               record("R2", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS)]
    harness.submit("chal-k", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", INSPECTION_LOT),
                           ("R2", "LOT-4471/B", ENTRY_LOT)])],
        compliance=[("K1", "MET", "R1", INSPECTION_FINDING)]))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))

    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    forged = copy.deepcopy(payload)
    forged["findings"]["compliance"][0]["finding"] = "NOT_MET"
    module._derive_into(forged, context)
    assert forged["compliance_state"] == "NOT_MET"
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


# == guards that nothing else can reach ====================================
#
# These two are defence in depth: grounding and the gate's normalisation
# check both stand in front of them, so no round can deliver the input they
# refuse. That is exactly why a mutation removing them survived a whole-suite
# sweep - and why they are tested directly here instead. A guard worth
# keeping is worth proving.

def test_the_custody_state_refuses_an_untimed_evidenced_checkpoint(
        staged_module):
    """Kills `custody: an untimed checkpoint is tolerated`."""
    module, context, findings = staged_module
    findings["checkpoints"][1]["stated_time"] = ""
    assert module._custody_state(context, findings) == "UNREADABLE"


def test_the_custody_state_refuses_an_unnormalised_time(staged_module):
    module, context, findings = staged_module
    findings["checkpoints"][1]["stated_time"] = "the 14th of March"
    assert module._custody_state(context, findings) == "UNREADABLE"


@pytest.mark.parametrize("field,value", [
    ("submission_id", "sub-9"),
    ("challenge_id", "chal-9"),
    ("policy_id", "pol-9"),
    ("shipment_or_lot_id", "LOT-SOMETHING-ELSE"),
])
def test_the_gate_itself_refuses_a_rebound_payload(harness, cold_chain,
                                                   field, value):
    """Kills `gate: the payload need not be bound to this submission`.

    The existing test forged these fields and voted through the validator,
    where the comparison catches them - so the gate's own binding check was
    never what refused them. A consumer reading a ratified receipt relies on
    the gate, not on the comparison, so the gate is tested directly here.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    forged = copy.deepcopy(payload)
    forged[field] = value
    assert module._parse_payload(json.dumps(forged), context, None) is None


def test_an_assessed_round_cannot_claim_to_have_read_a_missing_record(
        harness, cold_chain):
    """Kills `gate: an assessed round with a missing record is accepted`.

    The test in `test_gate_units.py` for this rule was masked: it forged
    `panel_state` to ASSESSED while leaving the empty findings in place, and
    the findings check refused the payload before the missing-record rule
    was reached. This one carries *real* findings, grounded in the one
    record that was readable, so every other rule passes and only this one
    is left standing.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"

    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert payload["panel_state"] == "SKIPPED"

    forged = copy.deepcopy(payload)
    forged["panel_state"] = "ASSESSED"
    forged["findings"] = {
        "checkpoints": [],
        "identity": [{"ref": "LOT",
                      "values": [{"record_id": "R2", "value": "LOT-4471/B",
                                  "quote": BOL_LOT}]},
                     {"ref": "CONTAINER", "values": []}],
        "origin": {"finding": "NOT_ASSESSED", "record_id": "", "quote": ""},
        "condition": {"state": "NOT_FOUND", "record_id": "",
                      "readings": [], "quote": ""},
        "delivery": {"state": "NOT_ASSESSED", "record_id": "",
                     "stated_time": "", "quote": ""},
        "compliance": [],
        "contradiction": {"found": False, "record_ids": [], "quote": ""},
        "sufficient": True,
        "basis": "read from the one record that arrived",
    }
    module._derive_into(forged, context)
    # Everything else about this payload is in order: the findings parse,
    # they are normalised, and the quote is in the bytes this node verified.
    texts = {"R2": module._fetch_record(context["records"][1]["location"],
                                        context["records"][1]["sha256"])[2]}
    assert module._read_answer(forged["findings"], context) is not None
    assert module._apply_grounding(forged["findings"], context, texts) == \
        forged["findings"]
    # And it is still refused, because a required record was never read.
    assert module._parse_payload(json.dumps(forged), context, texts) is None
    assert module._parse_payload(json.dumps(forged), context, None) is None


def test_the_gate_refuses_findings_of_the_wrong_shape(staged_module_payload):
    """Kills `gate: the findings need not be the declared shape`.

    On the ratified path the gate is called with no texts, so the
    re-grounding step cannot run and the structural read is the only thing
    standing between a malformed set of findings and storage. An unknown
    checkpoint finding is the cleanest case: every derived field can be
    restated around it consistently, and nothing else objects.
    """
    module, context, payload = staged_module_payload
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][1]["finding"] = "DEFINITELY"
    forged["findings"]["checkpoints"][1]["record_id"] = ""
    forged["findings"]["checkpoints"][1]["quote"] = ""
    forged["findings"]["checkpoints"][1]["stated_time"] = ""
    module._derive_into(forged, context)
    assert forged["custody_state"] == "UNREADABLE"
    assert module._parse_payload(json.dumps(forged), context, None) is None


@pytest.fixture
def staged_module_payload(harness, custody):
    from test_verdicts import custody_answer
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert module._parse_payload(json.dumps(payload), context,
                                 None) is not None
    return module, context, payload


def test_the_custody_state_refuses_an_unevidenced_checkpoint(staged_module):
    """Kills `custody: an unevidenced checkpoint is tolerated`.

    Grounding empties the time of any checkpoint that is not evidenced, and
    the gate refuses a payload where one carries a time anyway - so this
    guard and the untimed-checkpoint guard each shield the other from every
    round. Both are still tested, because "some other rule happens to catch
    it" is not the same as "this rule is right".
    """
    module, context, findings = staged_module
    findings["checkpoints"][1]["finding"] = "UNCLEAR"
    findings["checkpoints"][1]["stated_time"] = "2026-03-14T19:45Z"
    assert module._custody_state(context, findings) == "UNREADABLE"


def test_the_condition_report_sorts_the_readings_itself(harness, cold_chain):
    """Kills `condition: readings are not sorted before the arithmetic`.

    Grounding sorts the readings before they ever reach a payload, so the
    sort inside the arithmetic is never load-bearing in a round. It is
    load-bearing for the arithmetic itself: an excursion measured over
    reversed readings is measured over negative spans.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    readings = [
        {"time": "2026-03-16T18:00Z", "value_tenths": 50},
        {"time": "2026-03-15T00:30Z", "value_tenths": 50},
        {"time": "2026-03-15T00:00Z", "value_tenths": 95},
        {"time": "2026-03-14T06:00Z", "value_tenths": 50},
    ]
    findings = {"condition": {"state": "READ", "record_id": "R1",
                              "readings": readings, "quote": LOG_LOT}}
    state, worst, used = module._condition_report(context, findings)
    assert state == "HELD"
    assert worst == 30
    assert used == 4


def test_the_authenticity_state_refuses_an_unreadable_record(harness,
                                                             cold_chain):
    """Kills `authenticity: an unreadable record is treated as verified`.

    The gate refuses a row that is both unreadable and authenticated, so a
    payload can never carry this combination. The function still has to be
    right about it.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    rows = [{"record_id": "R1", "kind": "CONDITION_LOG",
             "status": "RECORD_UNAVAILABLE", "reason": "FETCH_FAILED",
             "byte_count": 0, "authenticity": "AUTHENTICATED_ORIGIN"},
            {"record_id": "R2", "kind": "BILL_OF_LADING",
             "status": "RECORD_READABLE", "reason": "NONE",
             "byte_count": 690, "authenticity": "AUTHENTICATED_ORIGIN"}]
    assert module._authenticity_state(context, rows) == "SOURCE_UNVERIFIED"
    rows[0]["status"] = "RECORD_READABLE"
    assert module._authenticity_state(context, rows) == "AUTHENTICATED_ORIGIN"


@pytest.fixture
def staged_module(harness, custody):
    """The custody context and an honest set of findings, for testing a
    derivation directly."""
    from test_verdicts import custody_answer
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert module._custody_state(context, payload["findings"]) == "COMPLETE"
    return module, context, copy.deepcopy(payload["findings"])


# == comparisons that no fixture reached ===================================
#
# Each of these forges a payload that is coherent, grounded, and identical to
# this node's reading on every field except one. That one field is the only
# thing that can refuse it, which is what makes the test name honest.

def test_a_checkpoint_time_that_keeps_the_order_is_still_compared(
        chain_payload):
    """Kills `validator: the checkpoint findings are not compared`.

    Moving a checkpoint an hour later leaves the chain in order, so
    `custody_state` stays COMPLETE and every other compared field is
    unchanged. Only the per-checkpoint comparison can catch it - and it
    must, because the instant a record states is a fact about the record.
    """
    harness, module, context, payload = chain_payload
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][2]["stated_time"] = "2026-03-16T15:20Z"
    module._derive_into(forged, context)
    assert forged["custody_state"] == "COMPLETE"
    assert forged["verdict"] == "CLAIM_SUPPORTED"
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


def test_a_reconciled_value_that_differs_is_still_compared(chain_payload):
    """Kills `validator: the reconciliation is not compared`.

    Both nodes reconciled the lot number across three records; they
    reconciled it to different lots. `identity_state` is CONSISTENT on both
    sides, so only the summary comparison carries the disagreement.
    """
    harness, module, context, payload = chain_payload
    forged = copy.deepcopy(payload)
    for entry in forged["findings"]["identity"][0]["values"]:
        entry["value"] = "LOT-9000/Q"
    module._derive_into(forged, context)
    assert forged["identity_state"] == "CONSISTENT"
    assert forged["identity_summary"][0]["state"] == "RECONCILED"
    assert forged["identity_summary"][0]["value"] == "LOT9000Q"
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


def test_the_criteria_are_compared_between_nodes(chain_payload):
    """Kills `validator: the criteria are not compared`.

    A payload that drops a record's corroboration changes
    `records_consistent` - and `identity_state` with it - so this is caught
    twice over. The point of the test is that it is caught at all: the
    criteria are what a consumer reads out of `get_verdict`, so nodes have
    to agree on them and not merely on the verdict they imply.
    """
    harness, module, context, payload = chain_payload
    forged = copy.deepcopy(payload)
    forged["findings"]["identity"][0]["values"] = \
        forged["findings"]["identity"][0]["values"][:1]
    module._derive_into(forged, context)
    assert forged["criteria"]["records_consistent"] is False
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


def test_a_delivery_time_inside_the_window_is_still_compared(harness):
    """Kills `validator: the delivery time is not compared` and
    `validator: the delivery state is not compared`.

    Two nodes both read a delivery inside the window, an hour apart. The
    state is IN_WINDOW on both sides, so the instant itself is the only
    disagreement - and a consumer reads that instant.
    """
    from conftest import BILL_OF_LADING, DELIVERY_CLAIM, DELIVERY_NOTE
    harness.register("pol-d")
    harness.publish("pol-d", DELIVERY_CLAIM)
    harness.open_challenge("pol-d", 1, "chal-d")
    harness.mock_records(DELIVERY_NOTE, BILL_OF_LADING)
    records = [record("R1", DELIVERY_NOTE, "DELIVERY_CONFIRMATION", CARRIER),
               record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER)]
    harness.submit("chal-d", "sub-1", records)
    from test_verdicts import BOL_LOT, DELIVERY_LOT, DELIVERY_TIME
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", DELIVERY_LOT),
                           ("R2", "LOT-4471/B", BOL_LOT)])],
        delivery={"state": "READ", "record_id": "R1",
                  "stated_time": "2026-03-16T16:40Z",
                  "quote": DELIVERY_TIME}))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    forged = copy.deepcopy(payload)
    forged["findings"]["delivery"]["stated_time"] = "2026-03-16T17:40Z"
    module._derive_into(forged, context)
    assert forged["delivery_state"] == "IN_WINDOW"
    assert forged["delivery_time"] == "2026-03-16T17:40Z"
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


def test_an_excursion_length_that_stays_within_the_allowance_is_compared(
        harness, cold_chain):
    """Kills `validator: the excursion is not compared`.

    Both nodes read an excursion inside the thirty-minute allowance, so the
    condition state is HELD on both sides and the verdict is the same. How
    long the excursion ran is still a fact the records state, and it is
    still reported to consumers.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    from test_verdicts import cold_answer as answer
    readings = [
        {"time": "2026-03-14T06:00Z", "value_tenths": 50},
        {"time": "2026-03-15T00:00Z", "value_tenths": 95},
        {"time": "2026-03-15T00:20Z", "value_tenths": 50},
        {"time": "2026-03-16T18:00Z", "value_tenths": 50},
    ]
    harness.mock_panel(answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert payload["condition_worst_excursion_minutes"] == 20
    forged = copy.deepcopy(payload)
    forged["findings"]["condition"]["readings"][2]["time"] = \
        "2026-03-15T00:25Z"
    module._derive_into(forged, context)
    assert forged["condition_state"] == "HELD"
    assert forged["condition_worst_excursion_minutes"] == 25
    assert harness.vm.run_validator(leader_result=json.dumps(forged)) is False


# == guards behind guards ==================================================
#
# These four refuse states that the lifecycle cannot produce, because an
# earlier rule already refused the transition that would reach them. Each is
# tested by putting the record into that state directly - the only way to
# reach the rule at all - and the comment says so rather than implying the
# round could get there.

def test_resolving_refuses_a_submission_whose_rounds_are_spent(harness,
                                                               cold_chain):
    """Kills `lifecycle: rounds never run out`.

    `retry_submission` never returns a submission to PENDING with its rounds
    spent, so this state cannot arise through the public surface. The guard
    is what makes that true of `resolve_submission` independently.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    module = sys.modules[type(harness.contract).__module__]
    stored = harness.contract.submissions.get("sub-1")
    stored.rounds_used = module.u16(3)
    with harness.vm.expect_revert("used all 3 rounds"):
        harness.resolve("sub-1")


def test_the_counter_refuses_to_count_the_same_submission_twice(harness,
                                                                cold_chain):
    """Kills `record: a retried claim counts twice`.

    A terminal verdict ends the submission, so no round can follow one. The
    guard is what makes the counter idempotent regardless.
    """
    harness, policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    from test_verdicts import cold_answer as answer
    harness.mock_panel(answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    assert json.loads(harness.contract.policy_record(policy_id, 1))[
        "TOTAL"] == 1

    module = sys.modules[type(harness.contract).__module__]
    stored = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(stored)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    # Store the same round again. The record must not move.
    harness.contract._store_round(stored, context, payload)
    assert json.loads(harness.contract.policy_record(policy_id, 1))[
        "TOTAL"] == 1
    assert int(harness.contract.resolved_total) == 1


def test_freshness_refuses_an_unsettled_verdict_directly(harness,
                                                         cold_chain):
    """Kills `reliance: an unsettled claim is consumable` and
    `reliance: an unresolved submission is consumable`.

    RESOLVED and a terminal verdict always travel together, so each of the
    two checks in `_freshness` shields the other. Both are set here one at a
    time, which is the only way to tell that each works.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    from test_verdicts import cold_answer as answer
    harness.mock_panel(answer(harness))
    harness.resolve("sub-1")
    stored = harness.contract.submissions.get("sub-1")
    assert harness.contract.freshness("sub-1", AS_OF) == "RELIABLE"

    # Settled status, unsettled verdict.
    stored.verdict = "INCONSISTENT_EVIDENCE"
    assert harness.contract.freshness("sub-1", AS_OF) == "UNKNOWN"
    assert harness.contract.is_consumable("sub-1", AS_OF) is False

    # Terminal verdict, unsettled status.
    stored.verdict = "CLAIM_SUPPORTED"
    stored.status = "RETRYABLE"
    assert harness.contract.freshness("sub-1", AS_OF) == "UNKNOWN"
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False


@pytest.fixture
def chain_payload(harness, custody):
    """A custody submission read honestly, with the module, its context and
    the payload the round produced."""
    from test_verdicts import custody_answer
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record_row = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record_row)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    return harness, module, context, payload
