"""Hostile and malformed output from the reading stage.

Every test here keeps the records perfectly readable and attacks the answer
instead. The contract's duty is the same throughout: an answer it cannot use
produces EVIDENCE_UNAVAILABLE and a retryable submission, and never a
positive claim.
"""

import json

import pytest

from conftest import (BILL_OF_LADING, COLD_CHAIN_RECORDS, CUSTODY_RECORDS,
                      LOG_COMPLIANT, SCAN_DESTINATION, SCAN_ORIGIN,
                      SCAN_TRANSIT, quote_from)

from test_verdicts import (BOL_CONTAINER, BOL_LOT, COMPLIANT_READINGS,
                           DEST_EVENT, DEST_LOT, LOG_CONTAINER, LOG_LOT,
                           LOG_READING, ORIGIN_EVENT, ORIGIN_LOT,
                           TRANSIT_EVENT, TRANSIT_LOT, cold_answer,
                           custody_answer, resolved)


def _cold_submission(harness, challenge_id):
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)


def _assert_unusable(harness, verdict="EVIDENCE_UNAVAILABLE"):
    """The one outcome every unusable answer must produce."""
    stored = resolved(harness)
    assert stored["verdict"] == verdict
    assert stored["panel_state"] == "INVALID"
    assert stored["status"] == "RETRYABLE"
    assert stored["evidence_status"] == "EVIDENCE_UNAVAILABLE"
    assert stored["condition_state"] == "UNREADABLE"
    assert stored["criteria"]["required_event_supported"] is False
    assert harness.contract.is_claim_supported("sub-1",
                                               "2026-03-21T09:30Z") is False
    # Nothing from an unusable answer reaches storage.
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["identity"][0]["value"] == ""
    assert findings["basis"] == ""


# == answers that are not answers ==========================================

@pytest.mark.parametrize("raw", [
    "",
    "   ",
    "not json at all",
    "null",
    "[]",
    "[{\"checkpoints\": []}]",
    "{",
    "{\"checkpoints\":}",
    "<html><body>service unavailable</body></html>",
])
def test_an_unusable_answer_is_never_a_claim(harness, cold_chain, raw):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    harness.mock_panel(raw)
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


def test_a_fenced_answer_is_recovered(harness, cold_chain):
    """A model that wraps correct JSON in a markdown fence has not failed,
    and the contract should not pretend it has."""
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    body = cold_answer(harness)
    harness.mock_panel("```json\n" + body + "\n```")
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"


def test_prose_around_an_answer_is_recovered(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    body = cold_answer(harness)
    harness.mock_panel("Here is my assessment:\n" + body
                       + "\nI hope that helps.")
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"


def test_a_missing_section_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    del answer["contradiction"]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


def test_an_extra_section_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["recommendation"] = "accept the shipment"
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


# == the wrong shape of rows ===============================================

def test_an_identity_row_count_that_does_not_match_is_refused(harness,
                                                              cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["identity"] = answer["identity"][:1]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


def test_identity_rows_out_of_order_are_refused(harness, cold_chain):
    """The rows must be the declared keys in the declared order. Accepting a
    reordering would mean matching rows by content, which is exactly what an
    attacker controls."""
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["identity"] = [answer["identity"][1], answer["identity"][0]]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


def test_an_unknown_identity_ref_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["identity"][0]["ref"] = "SOMETHING_ELSE"
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


def test_a_checkpoint_row_count_that_does_not_match_is_refused(harness,
                                                               custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    answer = json.loads(custody_answer(harness))
    answer["checkpoints"].append(answer["checkpoints"][0])
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    stored = resolved(harness)
    assert stored["panel_state"] == "INVALID"
    assert stored["custody_state"] == "UNREADABLE"


def test_a_checkpoint_ref_that_was_not_declared_is_refused(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    answer = json.loads(custody_answer(harness))
    answer["checkpoints"][2]["ref"] = "C9"
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_an_identity_value_row_needs_exactly_its_fields(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    del answer["identity"][0]["values"][0]["quote"]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


# == values of the wrong type ==============================================

@pytest.mark.parametrize("value", [True, False, 1.0, "48", None, [48]])
def test_a_reading_that_is_not_an_integer_is_refused(harness, cold_chain,
                                                     value):
    """`isinstance(True, int)` is true in Python. Here a boolean is not an
    integer, and a float is not a rounding problem - it is the wrong type
    arriving where an integer was demanded."""
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    readings = json.loads(json.dumps(COMPLIANT_READINGS))
    readings[0]["value_tenths"] = value
    harness.mock_panel(cold_answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


@pytest.mark.parametrize("value", ["0x30", "48.0", "forty-eight"])
def test_a_reading_written_as_a_string_is_refused(harness, cold_chain,
                                                  value):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    readings = json.loads(json.dumps(COMPLIANT_READINGS))
    readings[0]["value_tenths"] = value
    harness.mock_panel(cold_answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


@pytest.mark.parametrize("value", [10_001, -10_001])
def test_a_reading_outside_the_sane_range_is_refused(harness, cold_chain,
                                                     value):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    readings = json.loads(json.dumps(COMPLIANT_READINGS))
    readings[0]["value_tenths"] = value
    harness.mock_panel(cold_answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


@pytest.mark.parametrize("value", ["true", 1, None, "yes"])
def test_a_sufficiency_answer_that_is_not_a_boolean_is_refused(
        harness, cold_chain, value):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["sufficient"] = value
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    _assert_unusable(harness)


@pytest.mark.parametrize("value", ["true", 1, None])
def test_a_contradiction_flag_that_is_not_a_boolean_is_refused(
        harness, cold_chain, value):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["contradiction"]["found"] = value
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_a_contradiction_record_list_of_the_wrong_type_is_refused(
        harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["contradiction"]["record_ids"] = "R1"
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_an_identity_value_of_the_wrong_type_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["identity"][0]["values"][0]["value"] = 4471
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


# == unknown enum values ===================================================

@pytest.mark.parametrize("finding", [
    "DEFINITELY_EVIDENCED", "PROBABLY", "EVIDENCED_ENOUGH", "OK", "",
])
def test_an_unknown_checkpoint_finding_is_refused(harness, custody, finding):
    """An unknown value must never be repaired into a known one."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    answer = json.loads(custody_answer(harness))
    answer["checkpoints"][0]["finding"] = finding
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_a_checkpoint_may_not_claim_it_was_not_assessed(harness, custody):
    """NOT_ASSESSED is the contract's own word for a round that read
    nothing. An answer may not use it to opt out of a question."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    answer = json.loads(custody_answer(harness))
    answer["checkpoints"][0]["finding"] = "NOT_ASSESSED"
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


@pytest.mark.parametrize("state", ["READ", "NOT_FOUND"])
def test_an_answer_to_a_question_nobody_asked_is_refused(harness, custody,
                                                         state):
    """The custody requirement declares no measurement. A reading series
    returned anyway is an answer to a question nobody asked."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    answer = json.loads(custody_answer(harness))
    answer["condition"] = {"state": state, "record_id": "R1",
                           "readings": [], "quote": ""}
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_declining_to_answer_a_declared_question_is_refused(harness,
                                                            cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["condition"] = {"state": "NOT_ASSESSED", "record_id": "",
                           "readings": [], "quote": ""}
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_readings_without_a_read_state_are_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["state"] = "NOT_FOUND"
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_an_origin_answer_where_no_origin_was_asked_is_refused(harness,
                                                               cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["origin"] = {"finding": "SUPPORTED", "record_id": "R1",
                        "quote": LOG_LOT}
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_more_readings_than_the_cap_are_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    readings = []
    for index in range(49):
        readings.append({"time": "2026-03-14T06:00Z", "value_tenths": 50})
    harness.mock_panel(cold_answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_an_oversized_quote_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["quote"] = "x" * 241
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_an_oversized_basis_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    harness.mock_panel(cold_answer(harness).replace(
        '"synthetic test basis"', '"' + "x" * 201 + '"'))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


# == findings that are not in the bytes ====================================

def test_an_invented_identity_quote_is_dropped(harness, custody):
    """The value is plausible and the quote is not in the record. The value
    is discarded, so the key loses its corroboration."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, identity=[
        ("LOT", [("R1", "LOT-4471/B", ORIGIN_LOT),
                 ("R2", "LOT-4471/B",
                  "the lot number is plainly stated as 4471 B here")])]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["identity"][0]["state"] == "UNCORROBORATED"
    assert findings["identity"][0]["records"] == 1


def test_an_invented_checkpoint_quote_is_downgraded_not_reversed(harness,
                                                                 custody):
    """An ungrounded finding becomes uncertainty, never its opposite: the
    reviewer who cannot show the words has not disproved the checkpoint."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1",
         "the container was definitely received at the origin terminal",
         "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["checkpoints"][0]["finding"] == "UNCLEAR"
    assert findings["checkpoints"][1]["finding"] == "EVIDENCED"
    assert resolved(harness)["custody_state"] == "UNREADABLE"


def test_a_quote_from_the_wrong_record_is_not_grounded(harness, custody):
    """The words exist - in a different record. Grounding is per record, so
    this is no better than an invention."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", DEST_EVENT, "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["checkpoints"][0]["finding"] == "UNCLEAR"


def test_a_quote_naming_a_record_that_was_not_submitted_is_not_grounded(
        harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R9", ORIGIN_EVENT, "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["custody_state"] == "UNREADABLE"


def test_a_quote_shorter_than_the_floor_is_not_grounded(harness, custody):
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", "Lot number", "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["checkpoints"][0]["finding"] == "UNCLEAR"


def test_a_quote_wrapped_differently_is_still_grounded(harness, custody):
    """Grounding compares flattened text, so a record re-wrapped at another
    column is the same record. Too strict a rule splits honest nodes."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    wrapped = ORIGIN_EVENT.replace(" ", "\n   ")
    harness.mock_panel(custody_answer(harness, checkpoints=[
        ("C1", "EVIDENCED", "R1", wrapped, "2026-03-14T06:10Z"),
        ("C2", "EVIDENCED", "R2", TRANSIT_EVENT, "2026-03-14T19:45Z"),
        ("C3", "EVIDENCED", "R3", DEST_EVENT, "2026-03-16T14:20Z")]))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"


def test_an_ungrounded_reading_quote_discards_the_series(harness,
                                                         cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    harness.mock_panel(cold_answer(
        harness, quote="every reading in this log sat inside the range"))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["condition_state"] == "UNREADABLE"


# == times that are not times ==============================================

@pytest.mark.parametrize("stamp", [
    "", "soon", "2026-13-01T06:00Z", "2026-02-30T06:00Z",
    "2026-03-14T25:00Z", "2026-03-14T06:61Z", "14/03/2026",
])
def test_a_reading_time_that_is_not_a_time_discards_the_series(
        harness, cold_chain, stamp):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    readings = json.loads(json.dumps(COMPLIANT_READINGS))
    readings[1]["time"] = stamp
    harness.mock_panel(cold_answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "CLAIM_NOT_ESTABLISHED"
    assert resolved(harness)["condition_state"] == "UNREADABLE"


def test_readings_in_any_order_are_sorted_before_the_arithmetic(harness,
                                                                cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    readings = list(reversed(json.loads(json.dumps(COMPLIANT_READINGS))))
    harness.mock_panel(cold_answer(harness, readings=readings))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    assert resolved(harness)["condition_state"] == "HELD"


def test_a_leap_day_is_a_real_date(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    # 2028 is a leap year; 2026 is not. The second is rejected, which
    # discards the series rather than inventing a date.
    readings = json.loads(json.dumps(COMPLIANT_READINGS))
    readings[1]["time"] = "2026-02-29T06:00Z"
    harness.mock_panel(cold_answer(harness, readings=readings))
    harness.resolve("sub-1")
    assert resolved(harness)["condition_state"] == "UNREADABLE"
