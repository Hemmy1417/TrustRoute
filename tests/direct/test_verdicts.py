"""Every verdict, every derived state, and the precedence between them.

The reading stage is mocked; everything it feeds - ordering, the condition
arithmetic, reconciliation, authenticity, precedence - is the contract's own
code, and these tests exist to pin exactly that.
"""

import json

import pytest

from conftest import (AS_OF, BILL_OF_LADING, COLD_CHAIN, COLD_CHAIN_RECORDS,
                      synthetic_log,
                      COMPLIANCE_CLAIM, CUSTODY_CHAIN, CUSTODY_RECORDS,
                      CARRIER, CUSTOMS, DELIVERY_CLAIM, DELIVERY_LATE,
                      DELIVERY_NOTE, CUSTOMS_ENTRY, INSPECTION,
                      LOG_COMPLIANT, LOG_EXCURSION, ORIGIN_CERTIFICATE,
                      ORIGIN_CLAIM, PORT, SCAN_DESTINATION, SCAN_DIRECTED,
                      SCAN_ORIGIN, SCAN_OUT_OF_ORDER, SCAN_TRANSIT, UNION,
                      WAREHOUSE_CONFLICTING, WAREHOUSE_RECEIPT, record,
                      quote_from, record_sha, url_for)


NL = chr(10)


# == quotes, taken verbatim from the fixtures ==============================

LOG_LOT = quote_from(LOG_COMPLIANT, "Lot number")
LOG_CONTAINER = quote_from(LOG_COMPLIANT, "Container:")
LOG_READING = quote_from(LOG_COMPLIANT, "2026-03-14T06:00Z")
EXC_LOT = quote_from(LOG_EXCURSION, "Lot number")
EXC_CONTAINER = quote_from(LOG_EXCURSION, "Container:")
EXC_READING = quote_from(LOG_EXCURSION, "2026-03-15T00:00Z")
BOL_LOT = quote_from(BILL_OF_LADING, "Lot number")
BOL_CONTAINER = quote_from(BILL_OF_LADING, "Container:")
ORIGIN_LOT = quote_from(SCAN_ORIGIN, "Lot number")
ORIGIN_EVENT = quote_from(SCAN_ORIGIN, "Event time:")
TRANSIT_LOT = quote_from(SCAN_TRANSIT, "Lot number")
TRANSIT_EVENT = quote_from(SCAN_TRANSIT, "Event time:")
DEST_LOT = quote_from(SCAN_DESTINATION, "Lot number")
DEST_EVENT = quote_from(SCAN_DESTINATION, "Event time:")
EARLY_LOT = quote_from(SCAN_OUT_OF_ORDER, "Lot number")
EARLY_EVENT = quote_from(SCAN_OUT_OF_ORDER, "Event time:")
DIRECTED_LOT = quote_from(SCAN_DIRECTED, "Lot number")
DIRECTED_EVENT = quote_from(SCAN_DIRECTED, "Event time:")
CONFLICTING_LOT = quote_from(WAREHOUSE_CONFLICTING, "Lot number")
RECEIPT_LOT = quote_from(WAREHOUSE_RECEIPT, "Lot number")
DELIVERY_TIME = quote_from(DELIVERY_NOTE, "Delivery time:")
DELIVERY_LOT = quote_from(DELIVERY_NOTE, "Lot number")
LATE_TIME = quote_from(DELIVERY_LATE, "Delivery time:")
LATE_LOT = quote_from(DELIVERY_LATE, "Lot number")
CERT_LOT = quote_from(ORIGIN_CERTIFICATE, "Lot number")
CERT_REGION = quote_from(ORIGIN_CERTIFICATE, "Ashanti region")
ENTRY_LOT = quote_from(CUSTOMS_ENTRY, "Lot number")
ENTRY_ORIGIN = quote_from(CUSTOMS_ENTRY, "Declared origin")
INSPECTION_LOT = quote_from(INSPECTION, "Lot number")
INSPECTION_FINDING = quote_from(INSPECTION, "Findings:")

COMPLIANT_READINGS = [
    {"time": "2026-03-14T06:00Z", "value_tenths": 48},
    {"time": "2026-03-15T06:00Z", "value_tenths": 52},
    {"time": "2026-03-16T18:00Z", "value_tenths": 50},
]

EXCURSION_READINGS = [
    {"time": "2026-03-14T06:00Z", "value_tenths": 49},
    {"time": "2026-03-15T00:00Z", "value_tenths": 114},
    {"time": "2026-03-15T06:00Z", "value_tenths": 119},
    {"time": "2026-03-15T12:00Z", "value_tenths": 52},
    {"time": "2026-03-16T18:00Z", "value_tenths": 49},
]


# == builders ==============================================================

def cold_answer(harness, identity=None, contradiction=None):
    """The reading stage's whole answer for a cold-chain claim.

    There is no measurement series in it. The contract reads that off the
    log's bytes, so a test that wants particular readings supplies a log -
    see `harness.submit_cold_log`.
    """
    return harness.panel(
        identity=identity if identity is not None else [
            ("LOT", [("R1", "LOT-4471/B", LOG_LOT),
                     ("R2", "LOT-4471/B", BOL_LOT)]),
            ("CONTAINER", [("R1", "MSKU-774120-3", LOG_CONTAINER),
                           ("R2", "MSKU-774120-3", BOL_CONTAINER)])],
        contradiction=contradiction,
    )


def custody_answer(harness, checkpoints=None, identity=None,
                   contradiction=None):
    return harness.panel(
        checkpoints=checkpoints if checkpoints is not None else [
            ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "2026-03-14T06:10Z"),
            ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
            ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")],
        identity=identity if identity is not None else [
            ("LOT", [("R1", "LOT-4471/B", ORIGIN_LOT),
                     ("R2", "LOT-4471/B", TRANSIT_LOT),
                     ("R3", "LOT-4471/B", DEST_LOT)])],
        contradiction=contradiction,
    )


def resolved(harness, submission_id="sub-1"):
    return json.loads(harness.contract.get_submission(submission_id))


# == the condition claim ===================================================

def test_a_series_that_held_its_range_supports_the_claim(harness,
                                                         cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    stored = resolved(harness)
    assert stored["condition_state"] == "HELD"
    assert stored["condition_worst_excursion_minutes"] == 0
    assert stored["evidence_status"] == "EVIDENCE_SUFFICIENT"


def test_a_breach_is_decided_by_code_not_by_a_model(harness):
    """No model reads the log at all: code parses it and code compares the
    range. The excursion here is eighteen hours against an allowance of
    thirty minutes."""
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1")
    harness.mock_records(LOG_EXCURSION, BILL_OF_LADING)
    records = [record("R1", LOG_EXCURSION, "CONDITION_LOG", CARRIER),
               record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER)]
    harness.submit("chal-1", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", EXC_LOT),
                           ("R2", "LOT-4471/B", BOL_LOT)]),
                  ("CONTAINER", [("R1", "MSKU-774120-3", EXC_CONTAINER),
                                 ("R2", "MSKU-774120-3",
                                  BOL_CONTAINER)])]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["condition_state"] == "BREACHED"
    # 2026-03-15T00:00Z out of range until 12:00Z: 720 minutes.
    assert stored["condition_worst_excursion_minutes"] == 720
    assert stored["evidence_status"] == "EVIDENCE_INSUFFICIENT"
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False
    # A negative result is still something a consumer may rely on.
    assert harness.contract.is_consumable("sub-1", AS_OF) is True


@pytest.mark.parametrize("gap,expected", [
    (30, "HELD"),        # exactly the allowance
    (31, "BREACHED"),    # one minute past it
])
def test_the_excursion_allowance_is_an_exact_boundary(harness, cold_chain,
                                                      gap, expected):
    harness, _policy_id, challenge_id = cold_chain
    body = synthetic_log([
        ("2026-03-14T06:00Z", "5.0"),
        ("2026-03-15T00:00Z", "9.5"),
        ("2026-03-15T00:" + str(gap).zfill(2) + "Z", "5.0"),
        ("2026-03-16T18:00Z", "5.0"),
    ])
    harness.submit_cold_log(body, challenge_id, "sub-1")
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    stored = resolved(harness)
    assert stored["condition_state"] == expected
    assert stored["condition_worst_excursion_minutes"] == gap


def test_a_zero_allowance_refuses_any_excursion(harness):
    harness.register("pol-1")
    strict = json.loads(json.dumps(COLD_CHAIN))
    strict["condition_requirement"]["max_excursion_minutes"] = 0
    harness.publish("pol-1", strict)
    harness.open_challenge("pol-1", 1, "chal-1")
    body = synthetic_log([("2026-03-14T06:00Z", "5.0"),
                          ("2026-03-16T18:00Z", "9.5")])
    harness.submit_cold_log(body, "chal-1", "sub-1")
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["condition_state"] == "BREACHED"


def test_a_log_that_does_not_span_the_window_is_unreadable(harness,
                                                           cold_chain):
    """Readings that start after the window opens cannot show the condition
    held across it. That is not compliance and it is not a breach."""
    harness, _policy_id, challenge_id = cold_chain
    body = synthetic_log([("2026-03-15T06:00Z", "5.0"),
                          ("2026-03-16T18:00Z", "5.0")])
    harness.submit_cold_log(body, challenge_id, "sub-1")
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["condition_state"] == "UNREADABLE"
    assert stored["condition_readings_used"] == 0


def test_a_log_with_no_readings_is_unreadable(harness, cold_chain):
    """A log whose lines are prose carries no readings, and prose is not a
    measurement. The claim is not established and no excursion is
    invented."""
    harness, _policy_id, challenge_id = cold_chain
    body = ("REEFER TEMPERATURE LOG" + NL + "Lot number: LOT-4471/B" + NL
            + "Container: MSKU-774120-3" + NL
            + "The probe was offline for the whole of the carriage window "
              "and no readings were recorded." + NL)
    harness.submit_cold_log(body, challenge_id, "sub-1")
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["condition_state"] == "UNREADABLE"
    assert stored["condition_readings_used"] == 0


def test_the_series_is_read_from_the_bytes_not_from_the_answer(harness,
                                                               cold_chain):
    """A live round split because a model was asked to copy eleven readings
    out of a log and two models copied different amounts of it. The reading
    stage is no longer asked, and an answer that volunteers a series is
    ignored rather than believed."""
    harness, _policy_id, challenge_id = cold_chain
    body = synthetic_log([("2026-03-14T06:00Z", "5.0"),
                          ("2026-03-16T18:00Z", "5.0")])
    harness.submit_cold_log(body, challenge_id, "sub-1")
    answer = json.loads(cold_answer(harness))
    answer["condition"] = {"state": "READ", "record_id": "R1",
                           "readings": [{"time": "2026-03-14T06:00Z",
                                         "value_tenths": 950}],
                           "quote": ""}
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    stored = resolved(harness)
    assert stored["condition_state"] == "HELD"
    assert stored["condition_readings_used"] == 2
    receipt = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert receipt["findings"]["condition"]["readings"] == [
        {"time": "2026-03-14T06:00Z", "value_tenths": 50},
        {"time": "2026-03-16T18:00Z", "value_tenths": 50}]


def test_the_condition_report_shows_the_requirement_and_the_arithmetic(
        harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    report = json.loads(harness.contract.get_condition_report("sub-1"))
    assert report["requirement"]["min_tenths"] == 20
    assert report["requirement"]["max_tenths"] == 80
    assert report["condition_state"] == "HELD"
    assert report["readings_used"] == 11


# == the custody claim =====================================================

def test_a_chain_evidenced_in_order_supports_the_claim(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    stored = resolved(harness)
    assert stored["custody_state"] == "COMPLETE"
    chain = json.loads(harness.contract.get_custody_chain("sub-1"))
    assert [row["ref"] for row in chain["checkpoints"]] == ["C1", "C2", "C3"]
    assert chain["checkpoints"][0]["stated_time"] == "2026-03-14T06:10Z"


def test_checkpoints_out_of_order_do_not_support_the_claim(harness):
    """Every checkpoint is evidenced and the chain is still impossible: the
    discharge scan is dated before the export lodgement. No model is asked
    about the order; code compares the instants."""
    harness.register("pol-c")
    harness.publish("pol-c", CUSTODY_CHAIN)
    harness.open_challenge("pol-c", 1, "chal-c")
    harness.mock_records(SCAN_ORIGIN, SCAN_TRANSIT, SCAN_OUT_OF_ORDER)
    records = [record("R1", SCAN_ORIGIN, "CUSTODY_SCAN", PORT),
               record("R2", SCAN_TRANSIT, "CUSTODY_SCAN", CARRIER),
               record("R3", SCAN_OUT_OF_ORDER, "CUSTODY_SCAN", CARRIER)]
    harness.submit("chal-c", "sub-1", records)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", EARLY_EVENT, "2026-03-12T08:05Z")],
        identity=[("LOT", [("R1", "LOT-4471/B", ORIGIN_LOT),
                           ("R2", "LOT-4471/B", TRANSIT_LOT),
                           ("R3", "LOT-4471/B", EARLY_LOT)])]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["custody_state"] == "OUT_OF_ORDER"
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False


def test_equal_timestamps_are_in_order(harness, custody):
    """Three checkpoints stamped at the same instant are in order: the rule
    is that time must not go backwards, not that it must advance.

    Tested on the derivation directly, because a round cannot deliver this
    input - a stated time has to be one its own record states, and no two
    of these records state the same instant. Claiming otherwise is what
    `test_a_checkpoint_time_must_occur_in_its_record` covers.
    """
    import sys
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    module = sys.modules[type(harness.contract).__module__]
    context = harness.contract._context(
        harness.contract.submissions.get("sub-1"))
    findings = json.loads(harness.contract.get_receipt("sub-1", 1))["findings"]
    for row in findings["checkpoints"]:
        row["stated_time"] = "2026-03-14T06:10Z"
    assert module._custody_state(context, findings) == "COMPLETE"


def test_a_checkpoint_time_must_occur_in_its_record(harness, custody):
    """A time nobody can find in the record it is attributed to is not a
    copied fact, so the checkpoint becomes unclear.

    This rule also keeps rounds together: it was added because a live round
    reached NO_MAJORITY, and a time taken on trust is one more thing two
    honest nodes can state differently.
    """
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "2026-03-14T06:10Z"),
        # The transit scan states 19:45, not 06:10.
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T06:10Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["checkpoints"][0]["finding"] == "EVIDENCED"
    assert findings["checkpoints"][1]["finding"] == "UNCLEAR"
    assert findings["checkpoints"][1]["stated_time"] == ""
    assert resolved(harness)["custody_state"] == "UNREADABLE"


def test_a_missing_checkpoint_makes_the_chain_incomplete(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "NOT_EVIDENCED", "", "", "")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["custody_state"] == "INCOMPLETE"


def test_an_unclear_checkpoint_makes_the_chain_unreadable(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "2026-03-14T06:10Z"),
        ("C2", "UNCLEAR", "", "", ""),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["custody_state"] == "UNREADABLE"


def test_a_definite_gap_outranks_an_unclear_one(harness, custody):
    """One checkpoint is definitely unevidenced and another is unclear. The
    chain is incomplete - the definite finding is the more informative."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "2026-03-14T06:10Z"),
        ("C2", "UNCLEAR", "", "", ""),
        ("C3", "NOT_EVIDENCED", "", "", "")]))
    harness.resolve("sub-1")
    assert resolved(harness)["custody_state"] == "INCOMPLETE"


def test_an_evidenced_checkpoint_with_no_readable_time_is_unclear(harness,
                                                                  custody):
    """A checkpoint nobody can time cannot be placed in the order, so it is
    downgraded to unclear rather than counted."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, "some time in March"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    harness.resolve("sub-1")
    stored = resolved(harness)
    assert stored["custody_state"] == "UNREADABLE"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["checkpoints"][0]["finding"] == "UNCLEAR"
    assert findings["checkpoints"][0]["quote"] == ""


@pytest.mark.parametrize("spelling", [
    "2026-03-14T06:10Z", "2026-03-14T06:10", "2026-03-14 06:10",
    "2026-03-14T06:10:00Z", "2026/03/14 06:10",
])
def test_one_instant_written_several_ways_is_one_instant(harness, custody,
                                                         spelling):
    """Carriers, warehouses and customs agents write times differently.
    Normalising in code is what stops honest validators splitting over a
    format."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", ORIGIN_EVENT, spelling),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    chain = json.loads(harness.contract.get_custody_chain("sub-1"))
    assert chain["checkpoints"][0]["stated_time"] == "2026-03-14T06:10Z"


# == reconciliation across records =========================================

def test_records_that_disagree_on_the_lot_are_inconsistent(harness):
    """The verdict the primitive exists for: two records, two lot numbers,
    no finding about the shipment at all."""
    harness.register("pol-c")
    harness.publish("pol-c", CUSTODY_CHAIN)
    harness.open_challenge("pol-c", 1, "chal-c")
    harness.mock_records(SCAN_ORIGIN, SCAN_TRANSIT, SCAN_DESTINATION,
                         WAREHOUSE_CONFLICTING)
    records = CUSTODY_RECORDS + [
        record("R4", WAREHOUSE_CONFLICTING, "WAREHOUSE_RECEIPT", UNION,
               location=url_for(WAREHOUSE_CONFLICTING))]
    # The union record is served from the raw host, not the union's own, so
    # this test also fixes that an inconsistency outranks an unverified
    # source.
    harness.submit("chal-c", "sub-1", records)
    harness.mock_panel(custody_answer(harness, identity=[
        ("LOT", [("R1", "LOT-4471/B", ORIGIN_LOT),
                 ("R2", "LOT-4471/B", TRANSIT_LOT),
                 ("R4", "LOT-5208/A", CONFLICTING_LOT)])]))
    assert harness.resolve("sub-1") == "INCONSISTENT_EVIDENCE"
    stored = resolved(harness)
    assert stored["identity_state"] == "CONFLICTING"
    assert stored["evidence_status"] == "EVIDENCE_CONTRADICTORY"
    assert stored["criteria"]["records_consistent"] is False
    assert stored["status"] == "RETRYABLE"
    # Inconsistent records are not a finding against the shipment, so
    # nothing is consumable and nothing is counted.
    assert harness.contract.is_consumable("sub-1", AS_OF) is False
    assert json.loads(harness.contract.policy_record("pol-c", 1))[
        "TOTAL"] == 0


def test_one_record_stating_an_identifier_is_not_corroboration(harness,
                                                               custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, identity=[
        ("LOT", [("R1", "LOT-4471/B", ORIGIN_LOT)])]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["identity_state"] == "UNKNOWN"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["identity"][0]["state"] == "UNCORROBORATED"
    assert findings["identity"][0]["records"] == 1


def test_an_identifier_written_differently_still_reconciles(harness,
                                                           custody):
    """`LOT-4471/B`, `lot 4471 b` and `LOT4471B` are the same lot."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, identity=[
        ("LOT", [("R1", "LOT-4471/B", ORIGIN_LOT),
                 ("R2", "lot 4471 b", TRANSIT_LOT),
                 ("R3", "LOT4471B", DEST_LOT)])]))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["identity"][0]["state"] == "RECONCILED"
    assert findings["identity"][0]["value"] == "LOT4471B"
    assert findings["identity"][0]["records"] == 3


def test_a_grounded_contradiction_is_inconsistent_evidence(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, contradiction={
        "found": True, "record_ids": ["R1", "R3"], "quote": ORIGIN_EVENT}))
    assert harness.resolve("sub-1") == "INCONSISTENT_EVIDENCE"
    assert resolved(harness)["evidence_status"] == "EVIDENCE_CONTRADICTORY"


def test_an_ungrounded_contradiction_does_not_stand(harness, custody):
    """An accusation nobody can point to in the bytes is dropped, and the
    round proceeds on the rest of the findings."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, contradiction={
        "found": True, "record_ids": ["R1"],
        "quote": "these records plainly contradict one another somewhere"}))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    assert resolved(harness)["identity_state"] == "CONSISTENT"


# == records that cannot be read ===========================================

@pytest.mark.parametrize("kwargs,reason", [
    ({"status": 404, "body": "not found"}, "FETCH_FAILED"),
    ({"status": 500, "body": "server error"}, "FETCH_FAILED"),
])
def test_an_unfetchable_record_is_never_a_finding(harness, cold_chain,
                                                  kwargs, reason):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, **kwargs)
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    stored = resolved(harness)
    assert stored["evidence_status"] == "EVIDENCE_UNAVAILABLE"
    assert stored["panel_state"] == "SKIPPED"
    assert stored["records"][0]["reason"] == reason
    assert stored["records"][0]["authenticity"] == "SOURCE_UNVERIFIED"
    assert stored["criteria"]["required_records_present"] is False
    assert stored["status"] == "RETRYABLE"


def test_substituted_bytes_are_refused_before_anything_reads_them(harness,
                                                                  cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT,
                        body="REEFER TEMPERATURE LOG\nedited after the fact\n")
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    assert resolved(harness)["records"][0]["reason"] == "HASH_MISMATCH"


def test_an_oversized_record_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    oversized = "x" * 200_001
    import hashlib
    entry = record("R1", LOG_COMPLIANT, "CONDITION_LOG", CARRIER,
                   sha=hashlib.sha256(oversized.encode("utf-8")).hexdigest())
    harness.submit(challenge_id, "sub-1", [entry, COLD_CHAIN_RECORDS[1]])
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, body=oversized)
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    assert resolved(harness)["records"][0]["reason"] == "TOO_LARGE"


def test_a_blank_record_is_unreadable(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    blank = "   \n\n  "
    import hashlib
    entry = record("R1", LOG_COMPLIANT, "CONDITION_LOG", CARRIER,
                   sha=hashlib.sha256(blank.encode("utf-8")).hexdigest())
    harness.submit(challenge_id, "sub-1", [entry, COLD_CHAIN_RECORDS[1]])
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, body=blank)
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    assert resolved(harness)["records"][0]["reason"] == "UNREADABLE"


# == authenticity ==========================================================

def test_a_record_not_from_its_issuers_host_is_unverified(harness):
    """The certificate says it was issued by the growers' union. The
    requirement says the union publishes from its own host. These bytes came
    from somewhere else, so the source is unverified - and the contract
    never claims a signature was checked."""
    harness.register("pol-o")
    harness.publish("pol-o", ORIGIN_CLAIM)
    harness.open_challenge("pol-o", 1, "chal-o")
    harness.mock_records(ORIGIN_CERTIFICATE, CUSTOMS_ENTRY)
    records = [record("R1", ORIGIN_CERTIFICATE, "ORIGIN_CERTIFICATE", UNION),
               record("R2", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS)]
    harness.submit("chal-o", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", CERT_LOT),
                           ("R2", "LOT-4471/B", ENTRY_LOT)])],
        origin={"finding": "SUPPORTED", "record_id": "R1",
                "quote": CERT_REGION}))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["authenticity_state"] == "SOURCE_UNVERIFIED"
    assert stored["evidence_status"] == "SOURCE_AUTHENTICITY_UNVERIFIED"
    assert stored["criteria"]["source_authenticity_verified"] is False
    # The origin itself was supported; authenticity is what stopped it.
    assert stored["origin_state"] == "SUPPORTED"
    assert stored["criteria"]["required_event_supported"] is True
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False


# == a record that instructs its reader ====================================

def test_a_record_that_instructs_its_reader_cannot_support_a_claim(harness):
    harness.register("pol-c")
    harness.publish("pol-c", CUSTODY_CHAIN)
    harness.open_challenge("pol-c", 1, "chal-c")
    harness.mock_records(SCAN_DIRECTED, SCAN_TRANSIT, SCAN_DESTINATION)
    records = [record("R1", SCAN_DIRECTED, "CUSTODY_SCAN", PORT),
               record("R2", SCAN_TRANSIT, "CUSTODY_SCAN", CARRIER),
               record("R3", SCAN_DESTINATION, "CUSTODY_SCAN", CARRIER)]
    harness.submit("chal-c", "sub-1", records)
    # The panel does exactly what the record told it to.
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", DIRECTED_EVENT, "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")],
        identity=[("LOT", [("R1", "LOT-4471/B", DIRECTED_LOT),
                           ("R2", "LOT-4471/B", TRANSIT_LOT),
                           ("R3", "LOT-4471/B", DEST_LOT)])]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    stored = resolved(harness)
    assert stored["directed_text_hits"] >= 4
    # Everything else read as fine. Code is what refused it.
    assert stored["custody_state"] == "COMPLETE"
    assert stored["identity_state"] == "CONSISTENT"
    assert stored["criteria"]["required_event_supported"] is True
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False


# == origin, delivery and compliance claims ================================

@pytest.mark.parametrize("finding,verdict,state", [
    ("SUPPORTED", "CLAIM_SUPPORTED", "SUPPORTED"),
    ("NOT_SUPPORTED", "CLAIM_NOT_ESTABLISHED", "NOT_SUPPORTED"),
    ("UNCLEAR", "CLAIM_NOT_ESTABLISHED", "UNCLEAR"),
])
def test_the_origin_claim(harness, finding, verdict, state):
    harness.register("pol-o")
    harness.publish("pol-o", ORIGIN_CLAIM)
    harness.open_challenge("pol-o", 1, "chal-o")
    harness.mock_records(CUSTOMS_ENTRY, ORIGIN_CERTIFICATE)
    # Both records are attributed to issuers that publish from the raw host,
    # so authenticity is not what decides this test.
    records = [record("R1", CUSTOMS_ENTRY, "CUSTOMS_ENTRY", CUSTOMS),
               record("R2", ORIGIN_CERTIFICATE, "ORIGIN_CERTIFICATE",
                      CUSTOMS)]
    harness.submit("chal-o", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", ENTRY_LOT),
                           ("R2", "LOT-4471/B", CERT_LOT)])],
        origin={"finding": finding,
                "record_id": "R1" if finding != "UNCLEAR" else "",
                "quote": ENTRY_ORIGIN if finding != "UNCLEAR" else ""}))
    assert harness.resolve("sub-1") == verdict
    assert resolved(harness)["origin_state"] == state


@pytest.mark.parametrize("name,time,verdict,state", [
    (DELIVERY_NOTE, "2026-03-16T16:40Z", "CLAIM_SUPPORTED", "IN_WINDOW"),
    (DELIVERY_LATE, "2026-03-21T09:15Z", "CLAIM_NOT_ESTABLISHED",
     "OUT_OF_WINDOW"),
])
def test_the_delivery_window_is_compared_in_code(harness, name, time,
                                                 verdict, state):
    harness.register("pol-d")
    harness.publish("pol-d", DELIVERY_CLAIM)
    harness.open_challenge("pol-d", 1, "chal-d")
    harness.mock_records(name, BILL_OF_LADING)
    records = [record("R1", name, "DELIVERY_CONFIRMATION", CARRIER),
               record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER)]
    harness.submit("chal-d", "sub-1", records)
    lot_quote = DELIVERY_LOT if name == DELIVERY_NOTE else LATE_LOT
    time_quote = DELIVERY_TIME if name == DELIVERY_NOTE else LATE_TIME
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", lot_quote),
                           ("R2", "LOT-4471/B", BOL_LOT)])],
        delivery={"state": "READ", "record_id": "R1", "stated_time": time,
                  "quote": time_quote}))
    assert harness.resolve("sub-1") == verdict
    stored = resolved(harness)
    assert stored["delivery_state"] == state
    assert stored["delivery_time"] == time


def test_a_delivery_time_nobody_found_is_unreadable(harness):
    harness.register("pol-d")
    harness.publish("pol-d", DELIVERY_CLAIM)
    harness.open_challenge("pol-d", 1, "chal-d")
    harness.mock_records(DELIVERY_NOTE, BILL_OF_LADING)
    records = [record("R1", DELIVERY_NOTE, "DELIVERY_CONFIRMATION", CARRIER),
               record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER)]
    harness.submit("chal-d", "sub-1", records)
    harness.mock_panel(harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", DELIVERY_LOT),
                           ("R2", "LOT-4471/B", BOL_LOT)])],
        delivery={"state": "NOT_FOUND", "record_id": "", "stated_time": "",
                  "quote": ""}))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["delivery_state"] == "UNREADABLE"


@pytest.mark.parametrize("finding,verdict,state", [
    ("MET", "CLAIM_SUPPORTED", "MET"),
    ("NOT_MET", "CLAIM_NOT_ESTABLISHED", "NOT_MET"),
    ("UNCLEAR", "CLAIM_NOT_ESTABLISHED", "UNCLEAR"),
])
def test_the_compliance_claim(harness, finding, verdict, state):
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
        compliance=[("K1", finding,
                     "R1" if finding != "UNCLEAR" else "",
                     INSPECTION_FINDING if finding != "UNCLEAR" else "")]))
    assert harness.resolve("sub-1") == verdict
    assert resolved(harness)["compliance_state"] == state


def test_a_claim_whose_event_is_not_supported_is_insufficient(harness,
                                                              cold_chain):
    """There is no longer a question asking a model whether the evidence was
    "enough": the evidence status follows from whether the required event
    was established, which is derived in code."""
    harness, _policy_id, challenge_id = cold_chain
    body = synthetic_log([("2026-03-14T06:00Z", "5.0"),
                          ("2026-03-15T00:00Z", "9.5"),
                          ("2026-03-16T18:00Z", "5.0")])
    harness.submit_cold_log(body, challenge_id, "sub-1")
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["evidence_status"] == "EVIDENCE_INSUFFICIENT"


# == lifecycle after a round ===============================================

def test_a_terminal_verdict_is_not_adjudicated_again(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    with harness.vm.expect_revert("that submission is resolved"):
        harness.resolve("sub-1")
    harness.vm.sender = harness.submitter
    with harness.vm.expect_revert("only a retryable submission"):
        harness.contract.retry_submission("sub-1")


def test_a_round_that_could_not_read_the_records_is_retried(harness,
                                                            cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=503, body="unavailable")
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    assert resolved(harness)["status"] == "RETRYABLE"

    harness.vm.sender = harness.submitter
    harness.contract.retry_submission("sub-1")
    assert resolved(harness)["status"] == "PENDING"

    harness.clear()
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    stored = resolved(harness)
    assert stored["rounds_used"] == 2
    assert stored["status"] == "RESOLVED"


def test_a_stranger_cannot_retry(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    harness.resolve("sub-1")
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the submitter or the challenge"):
        harness.contract.retry_submission("sub-1")


def test_rounds_run_out_and_the_result_stays_unusable(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    for round_number in (1, 2, 3):
        assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
        stored = resolved(harness)
        assert stored["rounds_used"] == round_number
        if round_number < 3:
            harness.vm.sender = harness.submitter
            harness.contract.retry_submission("sub-1")
    assert resolved(harness)["status"] == "EXHAUSTED"
    harness.vm.sender = harness.submitter
    with harness.vm.expect_revert("only a retryable submission"):
        harness.contract.retry_submission("sub-1")
    with harness.vm.expect_revert("that submission is exhausted"):
        harness.resolve("sub-1")
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False
    assert harness.contract.is_consumable("sub-1", AS_OF) is False


def test_every_round_leaves_a_receipt(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    harness.resolve("sub-1")
    harness.vm.sender = harness.submitter
    harness.contract.retry_submission("sub-1")
    harness.clear()
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")

    first = json.loads(harness.contract.get_receipt("sub-1", 1))
    second = json.loads(harness.contract.get_receipt("sub-1", 2))
    assert first["verdict"] == "EVIDENCE_UNAVAILABLE"
    assert first["round"] == 1
    assert second["verdict"] == "CLAIM_SUPPORTED"
    assert second["round"] == 2
    assert second["schema"] == "trustroute/1"


def test_the_record_counts_only_terminal_verdicts_and_only_once(harness,
                                                                cold_chain):
    harness, policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.clear()
    harness.mock_record(BILL_OF_LADING)
    harness.mock_record(LOG_COMPLIANT, status=404, body="gone")
    harness.resolve("sub-1")
    assert json.loads(harness.contract.policy_record(policy_id, 1))[
        "TOTAL"] == 0

    harness.vm.sender = harness.submitter
    harness.contract.retry_submission("sub-1")
    harness.clear()
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    record_now = json.loads(harness.contract.policy_record(policy_id, 1))
    assert record_now["CLAIM_SUPPORTED"] == 1
    assert record_now["TOTAL"] == 1
    stats = json.loads(harness.contract.get_stats())
    assert stats["resolved"] == 1


# == reliance ==============================================================

def test_a_verdict_goes_stale(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    assert harness.contract.freshness("sub-1", "2026-03-25T09:30Z") == \
        "RELIABLE"
    assert harness.contract.freshness("sub-1", "2026-04-25T09:30Z") == "STALE"
    assert harness.contract.is_claim_supported("sub-1",
                                               "2026-04-25T09:30Z") is False


def test_a_verdict_as_of_before_it_was_made_is_unknown(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    assert harness.contract.freshness("sub-1", "2026-03-01T09:30Z") == \
        "UNKNOWN"
    assert harness.contract.freshness("sub-1", "not a timestamp") == "UNKNOWN"


def test_revoking_the_requirement_blocks_reliance(harness, cold_chain):
    harness, policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is True
    harness.vm.sender = harness.buyer
    harness.contract.revoke_policy_version(policy_id, 1)
    assert harness.contract.freshness("sub-1", AS_OF) == "BLOCKED"
    assert harness.contract.is_claim_supported("sub-1", AS_OF) is False
    assert harness.contract.is_consumable("sub-1", AS_OF) is False
    # The verdict itself is still readable; only reliance is blocked.
    assert json.loads(harness.contract.get_verdict("sub-1"))["verdict"] == \
        "CLAIM_SUPPORTED"


def test_claim_outcome_is_one_call_for_a_consumer(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    harness.resolve("sub-1")
    outcome = json.loads(harness.contract.claim_outcome("sub-1", AS_OF))
    assert outcome["verdict"] == "CLAIM_SUPPORTED"
    assert outcome["claim_supported"] is True
    assert outcome["consumable"] is True
    assert outcome["freshness"] == "RELIABLE"
    assert outcome["shipment_or_lot_id"] == "LOT-4471-B"
    assert outcome["condition_state"] == "HELD"
    assert len(outcome["definition_hash"]) == 64
