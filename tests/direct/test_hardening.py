"""Hostile and malformed output from the reading stage.

Every test here keeps the records perfectly readable and attacks the answer
instead. The contract's duty is the same throughout: an answer it cannot use
produces EVIDENCE_UNAVAILABLE and a retryable submission, and never a
positive claim.
"""

import json

import pytest

import sys

from conftest import (BILL_OF_LADING, COLD_CHAIN_RECORDS, CUSTODY_RECORDS,
                      LOG_COMPLIANT, SCAN_DESTINATION, SCAN_ORIGIN,
                      SCAN_TRANSIT, quote_from, synthetic_log)

NL = chr(10)

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


def test_an_origin_answer_where_no_origin_was_asked_is_refused(harness,
                                                               cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    answer = json.loads(cold_answer(harness))
    answer["origin"] = {"finding": "SUPPORTED", "record_id": "R1",
                        "quote": LOG_LOT}
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_an_oversized_basis_is_bounded_rather_than_refused(harness,
                                                            cold_chain):
    """The basis is the one field that is prose and nothing else: not
    compared between validators, not derived from, not gated on. A live
    round was discarded because its explanation ran past the bound, so the
    bound is now applied to the text instead of to the answer.
    `test_live_lessons.py` holds the detail, including that a basis which is
    not a string is still refused outright."""
    harness, _policy_id, challenge_id = cold_chain
    _cold_submission(harness, challenge_id)
    harness.mock_panel(cold_answer(harness).replace(
        '"synthetic test basis"', '"' + "x" * 201 + '"'))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["basis"] == "x" * 200


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


# == times that are not times ==============================================

@pytest.mark.parametrize("stamp", [
    "", "soon", "2026-13-01T06:00Z", "2026-02-30T06:00Z",
    "2026-03-14T25:00Z", "2026-03-14T06:61Z", "14/03/2026",
])


# == the log parser ========================================================
#
# These attacks used to be aimed at a model's answer, because the readings
# came from there. Code reads the log now, so they are aimed at the parser.
# Its rule is narrow on purpose: a line is a reading when its first token is
# a timestamp and its last is a measurement, and anything else is not a
# reading.

def _series(harness, body):
    """Parse a log body with the contract's own parser."""
    module = sys.modules[type(harness.contract).__module__]
    return module._parse_series(body)


def test_only_lines_that_start_with_a_timestamp_are_readings(harness):
    body = (synthetic_log([("2026-03-14T06:00Z", "4.8"),
                           ("2026-03-14T12:00Z", "5.1")]))
    readings = _series(harness, body)
    # The banner, the issuer line, the unit line, the heading and the
    # calibration date are all skipped by that one rule.
    assert readings == [{"time": "2026-03-14T06:00Z", "value_tenths": 48},
                        {"time": "2026-03-14T12:00Z", "value_tenths": 51}]


def test_the_parser_skips_a_line_whose_measurement_is_not_a_number(harness):
    body = synthetic_log([("2026-03-14T06:00Z", "4.8"),
                          ("2026-03-14T12:00Z", "probe offline"),
                          ("2026-03-14T18:00Z", "5.0")])
    assert [row["value_tenths"] for row in _series(harness, body)] == [48, 50]


@pytest.mark.parametrize("token", ["4.85", "4.8.1", "", "-", "4,8", "1e3",
                                   "0x30", "forty"])
def test_the_parser_refuses_a_measurement_it_cannot_read_exactly(harness,
                                                                 token):
    """More than one decimal place is refused rather than rounded: rounding
    a measurement is a judgement, and the parser makes none."""
    module = sys.modules[type(harness.contract).__module__]
    assert module._tenths_of(token) is None


@pytest.mark.parametrize("token,tenths", [
    ("4.8", 48), ("11", 110), ("-2.5", -25), ("0", 0), ("0.0", 0),
    ("182", 1820), (" 5.1 ", 51),
])
def test_the_parser_reads_a_measurement_as_integer_tenths(harness, token,
                                                          tenths):
    module = sys.modules[type(harness.contract).__module__]
    assert module._tenths_of(token) == tenths


def test_the_parser_skips_an_impossible_date(harness):
    """2026 is not a leap year, so there is no 29 February in it to read."""
    body = synthetic_log([("2026-02-29T06:00Z", "5.0"),
                          ("2026-03-14T06:00Z", "4.8")])
    assert _series(harness, body) == [{"time": "2026-03-14T06:00Z",
                                       "value_tenths": 48}]


def test_the_parser_sorts_what_it_reads(harness):
    body = synthetic_log([("2026-03-16T18:00Z", "5.0"),
                          ("2026-03-14T06:00Z", "4.8"),
                          ("2026-03-15T00:00Z", "5.2")])
    assert [row["time"] for row in _series(harness, body)] == [
        "2026-03-14T06:00Z", "2026-03-15T00:00Z", "2026-03-16T18:00Z"]


def test_the_parser_stops_at_the_reading_cap(harness):
    rows = []
    for index in range(80):
        rows.append(("2026-03-14T" + str(index % 24).zfill(2) + ":00Z",
                     "5.0"))
    assert len(_series(harness, synthetic_log(rows))) == 48


def test_the_parser_refuses_a_measurement_outside_the_sane_range(harness):
    body = synthetic_log([("2026-03-14T06:00Z", "99999"),
                          ("2026-03-14T12:00Z", "5.0")])
    assert _series(harness, body) == [{"time": "2026-03-14T12:00Z",
                                       "value_tenths": 50}]


def test_a_log_of_prose_carries_no_readings(harness):
    body = ("REEFER TEMPERATURE LOG" + NL
            + "The reefer ran within range for the whole voyage." + NL)
    assert _series(harness, body) == []
