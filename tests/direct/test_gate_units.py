"""The gate, rule by rule.

`_parse_payload` is called directly here with one deliberately broken field
at a time, each staged so that exactly one rule stands between the payload
and acceptance. That matters: if two rules would both refuse a payload, a
test cannot show which one did the work, and removing either would leave the
suite green.
"""

import copy
import json
import sys

import pytest

from conftest import COLD_CHAIN_RECORDS, CUSTODY_RECORDS
from test_verdicts import COMPLIANT_READINGS, cold_answer, custody_answer


@pytest.fixture
def staged(harness, cold_chain):
    """An honest payload, the context it was produced against, and this
    node's own verified bytes."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    texts = {}
    for item in context["records"]:
        texts[item["record_id"]] = module._fetch_record(
            item["location"], item["sha256"])[2]
    return harness, module, context, payload, texts


def _gate(module, payload, context, texts=None):
    return module._parse_payload(json.dumps(payload), context, texts)


def test_the_control_payload_passes_the_gate(staged):
    """Without this, every rejection below could be a broken fixture."""
    _harness, module, context, payload, texts = staged
    assert _gate(module, payload, context) is not None
    assert _gate(module, payload, context, texts) is not None


def test_a_payload_that_is_not_an_object_is_refused(staged):
    _harness, module, context, _payload, _texts = staged
    assert module._parse_payload("[]", context, None) is None
    assert module._parse_payload("not json", context, None) is None
    assert module._parse_payload("null", context, None) is None


def test_a_foreign_schema_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["schema"] = "someone-elses/1"
    assert _gate(module, forged, context) is None


# == rows: the facts about each record =====================================

def test_a_readable_row_may_not_carry_a_reason(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["rows"][0]["reason"] = "HASH_MISMATCH"
    assert _gate(module, forged, context) is None


def test_an_unavailable_row_must_carry_a_reason(staged):
    """Staged so the row is the only problem: the derived fields are
    restated afterwards, so the verdict still follows from the findings."""
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["rows"][0]["status"] = "RECORD_UNAVAILABLE"
    forged["rows"][0]["reason"] = "NONE"
    forged["rows"][0]["authenticity"] = "SOURCE_UNVERIFIED"
    forged["missing_required_kinds"] = ["CONDITION_LOG"]
    forged["panel_state"] = "SKIPPED"
    forged["findings"] = module._unassessed(context)
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


def test_an_unreadable_row_may_not_be_authenticated(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["rows"][0]["status"] = "RECORD_UNAVAILABLE"
    forged["rows"][0]["reason"] = "FETCH_FAILED"
    forged["rows"][0]["authenticity"] = "AUTHENTICATED_ORIGIN"
    forged["missing_required_kinds"] = ["CONDITION_LOG"]
    forged["panel_state"] = "SKIPPED"
    forged["findings"] = module._unassessed(context)
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


@pytest.mark.parametrize("value", [-1, 1.5, True, "100"])
def test_a_byte_count_of_the_wrong_type_is_refused(staged, value):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["rows"][0]["byte_count"] = value
    assert _gate(module, forged, context) is None


def test_a_row_naming_another_record_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["rows"][0]["record_id"] = "R7"
    assert _gate(module, forged, context) is None


def test_a_row_claiming_another_kind_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["rows"][0]["kind"] = "PACKING_LIST"
    assert _gate(module, forged, context) is None


# == the missing-kinds list is derived, not trusted ========================

def test_the_missing_kinds_list_must_follow_from_the_rows(staged):
    """Staged so nothing else objects: the list is wrong and the rows are
    not. Only the derivation catches it."""
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["missing_required_kinds"] = ["BILL_OF_LADING"]
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


def test_an_unknown_kind_in_the_missing_list_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["missing_required_kinds"] = ["VIBES"]
    assert _gate(module, forged, context) is None


# == the reading stage's state ============================================

def test_a_skipped_round_with_every_record_in_hand_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["panel_state"] = "SKIPPED"
    forged["findings"] = module._unassessed(context)
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


def test_an_assessed_round_with_a_missing_record_is_refused(harness,
                                                            cold_chain):
    """The mirror: a round may not claim it read records it could not
    fetch."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(COLD_CHAIN_RECORDS[1]["record_id"] and
                        "bill-of-lading.txt")
    harness.mock_record("condition-log-compliant.txt", status=404,
                        body="gone")
    harness.resolve("sub-1")
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert payload["panel_state"] == "SKIPPED"
    forged = copy.deepcopy(payload)
    forged["panel_state"] = "ASSESSED"
    assert module._parse_payload(json.dumps(forged), context, None) is None


def test_an_unassessed_round_must_carry_the_empty_findings(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["panel_state"] = "INVALID"
    # Keeps the real findings, which an invalid round never has.
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


# == normalisation is a precondition, not a courtesy =======================

def test_an_unnormalised_reading_time_is_refused(staged):
    """Two nodes must not be able to disagree over a format, so the payload
    must already be in the one spelling the contract stores."""
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["findings"]["condition"]["readings"][0]["time"] = \
        "2026-03-14 06:00"
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


def test_readings_out_of_order_in_the_payload_are_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["findings"]["condition"]["readings"] = list(reversed(
        forged["findings"]["condition"]["readings"]))
    module._derive_into(forged, context)
    assert _gate(module, forged, context) is None


def test_an_unnormalised_checkpoint_time_is_refused(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    harness.resolve("sub-1")
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["stated_time"] = "2026-03-14 06:10"
    module._derive_into(forged, context)
    assert module._parse_payload(json.dumps(forged), context, None) is None


def test_a_checkpoint_that_was_not_evidenced_may_not_carry_a_time(harness,
                                                                   custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "NOT_EVIDENCED", "", "", ""),
        ("C2", "NOT_EVIDENCED", "", "", ""),
        ("C3", "NOT_EVIDENCED", "", "", "")]))
    harness.resolve("sub-1")
    module = sys.modules[type(harness.contract).__module__]
    record = harness.contract.submissions.get("sub-1")
    context = harness.contract._context(record)
    context["round"] = 1
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    forged = copy.deepcopy(payload)
    forged["findings"]["checkpoints"][0]["stated_time"] = "2026-03-14T06:10Z"
    module._derive_into(forged, context)
    assert module._parse_payload(json.dumps(forged), context, None) is None


# == grounding against this node's own bytes ===============================

def test_a_quote_not_in_this_nodes_bytes_is_refused(staged):
    """With `texts` supplied the gate re-grounds every finding. Grounding
    only ever downgrades, so any difference means the leader relied on words
    this node did not verify."""
    _harness, module, context, payload, texts = staged
    forged = copy.deepcopy(payload)
    forged["findings"]["condition"]["quote"] = \
        "the readings were all comfortably within the agreed range"
    module._derive_into(forged, context)
    # Without this node's bytes the payload is coherent and passes...
    assert _gate(module, forged, context) is not None
    # ...and against them it does not.
    assert _gate(module, forged, context, texts) is None


# == every derived field is re-derived =====================================

@pytest.mark.parametrize("field,value", [
    ("custody_state", "COMPLETE"),
    ("identity_state", "UNKNOWN"),
    ("condition_state", "BREACHED"),
    ("condition_worst_excursion_minutes", 45),
    ("condition_readings_used", 2),
    ("delivery_state", "IN_WINDOW"),
    ("delivery_time", "2026-03-16T16:40Z"),
    ("origin_state", "SUPPORTED"),
    ("compliance_state", "MET"),
    ("authenticity_state", "SOURCE_UNVERIFIED"),
    ("evidence_status", "EVIDENCE_INSUFFICIENT"),
    ("verdict", "CLAIM_NOT_ESTABLISHED"),
])
def test_a_derived_field_that_does_not_follow_is_refused(staged, field,
                                                         value):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    assert forged[field] != value, field
    forged[field] = value
    assert _gate(module, forged, context) is None


def test_an_identity_summary_of_the_wrong_length_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["identity_summary"] = forged["identity_summary"][:1]
    assert _gate(module, forged, context) is None


def test_a_forged_identity_summary_is_refused(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["identity_summary"][0]["value"] = "LOT9999Z"
    assert _gate(module, forged, context) is None


@pytest.mark.parametrize("field", ["required_records_present",
                                   "records_consistent",
                                   "source_authenticity_verified",
                                   "required_event_supported"])
def test_a_criterion_that_does_not_follow_is_refused(staged, field):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["criteria"][field] = not forged["criteria"][field]
    assert _gate(module, forged, context) is None


def test_the_findings_must_be_an_object(staged):
    _harness, module, context, payload, _texts = staged
    forged = copy.deepcopy(payload)
    forged["findings"] = []
    assert _gate(module, forged, context) is None


# == the comparison between two runs =======================================
#
# `_first_difference` had no direct test, and a mutation sweep showed what
# that cost: removing the comparison of the origin state, the compliance
# state, the delivery state, the excursion, the four criteria or the
# checkpoint findings left the whole suite green. None of those were real
# holes in the contract - each was masked by a correlated field that *was*
# compared, so an integration test could not tell which rule did the work.
# The honest test is this one: perturb exactly one field and require the
# comparison to name it.

def _perturb(value):
    """A different value of the same kind."""
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "-DIFFERENT"
    raise AssertionError("no perturbation for %r" % type(value))


# Written out rather than read from the contract. A table-driven test
# driven by the table under test cannot see a deletion from that table:
# the first version of this test iterated `module.DECISION_FIELDS`, so a
# mutation that dropped a field simply was not iterated and the mutant
# survived. The literal list is the test's own claim about what must be
# compared, and the contract is checked against it both ways.
MUST_BE_COMPARED = [
    "schema", "submission_id", "challenge_id", "round", "policy_id",
    "policy_version", "definition_hash", "evidence_digest",
    "shipment_or_lot_id", "claim_type", "directed_text_hits",
    "panel_state", "custody_state", "identity_state", "condition_state",
    "condition_worst_excursion_minutes", "delivery_state", "delivery_time",
    "origin_state", "compliance_state", "authenticity_state",
    "condition_readings_used", "evidence_status", "verdict",
]

CRITERIA_MUST_BE_COMPARED = [
    "required_records_present", "records_consistent",
    "source_authenticity_verified", "required_event_supported",
]


def test_the_contract_compares_exactly_the_documented_fields(staged):
    """Catches a field quietly dropped from the comparison, and a field
    added to the payload without being compared or documented."""
    _harness, module, _context, _payload, _texts = staged
    assert sorted(module.DECISION_FIELDS) == sorted(MUST_BE_COMPARED)
    assert sorted(module.CRITERIA_FIELDS) == sorted(
        CRITERIA_MUST_BE_COMPARED)


def test_every_decision_field_is_compared(staged):
    _harness, module, _context, payload, _texts = staged
    for field in MUST_BE_COMPARED:
        theirs = copy.deepcopy(payload)
        theirs[field] = _perturb(theirs[field])
        difference = module._first_difference(payload, theirs)
        assert difference != "", "%s is not compared" % field


def test_every_criterion_is_compared(staged):
    _harness, module, _context, payload, _texts = staged
    for field in CRITERIA_MUST_BE_COMPARED:
        theirs = copy.deepcopy(payload)
        theirs["criteria"][field] = not theirs["criteria"][field]
        difference = module._first_difference(payload, theirs)
        assert difference != "", "criteria.%s is not compared" % field
        assert field in difference


def test_two_identical_runs_report_no_difference(staged):
    """Without this, a comparison that returned a field name for every
    input would pass every test above."""
    _harness, module, _context, payload, _texts = staged
    assert module._first_difference(payload, copy.deepcopy(payload)) == ""


def test_each_checkpoint_finding_and_instant_is_compared(harness, custody):
    """A custody payload, because the cold-chain fixture has no
    checkpoints and so cannot show this rule working at all."""
    from conftest import CUSTODY_RECORDS
    from test_verdicts import custody_answer
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    payload = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert len(payload["findings"]["checkpoints"]) == 3

    for index in range(3):
        for field in ("ref", "finding", "stated_time"):
            theirs = copy.deepcopy(payload)
            theirs["findings"]["checkpoints"][index][field] = _perturb(
                theirs["findings"]["checkpoints"][index][field])
            difference = module._first_difference(payload, theirs)
            assert difference != "", \
                "checkpoints[%d].%s is not compared" % (index, field)

    # And the freedom that is deliberate: which record was quoted for a
    # checkpoint, and the span quoted, may differ between honest nodes.
    theirs = copy.deepcopy(payload)
    theirs["findings"]["checkpoints"][0]["quote"] = "a different span"
    assert module._first_difference(payload, theirs) == ""
