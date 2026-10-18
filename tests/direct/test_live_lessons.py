"""Tests for things the live network did that the mocks did not.

Every test here exists because a real Studionet round behaved in a way no
local test had produced. They are kept separate so it stays obvious which
parts of the contract are shaped by what actually happened rather than by
what I imagined would.
"""

import json

import pytest

from conftest import COLD_CHAIN_RECORDS, CUSTODY_RECORDS
from test_verdicts import (BOL_LOT, COMPLIANT_READINGS, LOG_CONTAINER,
                           LOG_LOT, LOG_READING, ORIGIN_LOT, TRANSIT_LOT,
                           BOL_CONTAINER, cold_answer, custody_answer,
                           resolved)


def test_readings_given_as_positional_pairs_are_read(harness, cold_chain):
    """The first live round on Studionet returned every reading as
    `["2026-03-14T06:00Z", 48]` rather than as an object, and the contract
    discarded a perfectly good reading of the log as unusable - the stored
    verdict was EVIDENCE_UNAVAILABLE for a compliant cold chain.

    A positional pair carries the same two values in the same order, so it
    is read. Nothing semantic is normalised: see the tests below.
    """
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["readings"] = [
        [entry["time"], entry["value_tenths"]]
        for entry in COMPLIANT_READINGS]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    stored = resolved(harness)
    assert stored["condition_state"] == "HELD"
    assert stored["condition_readings_used"] == len(COMPLIANT_READINGS)
    # Whichever spelling arrived, the receipt stores the one canonical form.
    receipt = json.loads(harness.contract.get_receipt("sub-1", 1))
    assert receipt["findings"]["condition"]["readings"][0] == {
        "time": "2026-03-14T06:00Z", "value_tenths": 48}


def test_identity_values_given_as_positional_triples_are_read(harness,
                                                              custody):
    """The same notation, one structure along: a value, the record it came
    from and the quote, in the order the contract asks for them."""
    harness, _policy_id, challenge_id = custody
    harness.submit(challenge_id, "sub-1", CUSTODY_RECORDS)
    answer = json.loads(custody_answer(harness))
    answer["identity"][0]["values"] = [["R1", "LOT-4471/B", ORIGIN_LOT],
                                       ["R2", "LOT-4471/B", TRANSIT_LOT]]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert findings["identity"][0]["state"] == "RECONCILED"


@pytest.mark.parametrize("pair", [
    ["2026-03-14T06:00Z"],                       # too short
    ["2026-03-14T06:00Z", 48, "extra"],          # too long
    ["2026-03-14T06:00Z", 48.0],                 # a float is still refused
    ["2026-03-14T06:00Z", True],                 # a bool is still not an int
    [48, "2026-03-14T06:00Z"],                   # the wrong way round
    ["not a time", 48],
])
def test_a_positional_pair_is_still_type_checked(harness, cold_chain, pair):
    """Reading the other notation must not become a way in. Length, order
    and every type are checked exactly as they are for the object form."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["readings"] = [
        pair] + [[entry["time"], entry["value_tenths"]]
                 for entry in COMPLIANT_READINGS]
    harness.mock_panel(json.dumps(answer))
    harness.resolve("sub-1")
    stored = resolved(harness)
    # Either the answer was refused outright, or the series was discarded.
    # Neither can produce a supported claim.
    assert stored["verdict"] != "CLAIM_SUPPORTED"
    assert stored["condition_state"] == "UNREADABLE"


def test_a_mapping_with_the_wrong_keys_is_still_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["readings"] = [{"timestamp": "2026-03-14T06:00Z",
                                        "value_tenths": 48}]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    assert resolved(harness)["panel_state"] == "INVALID"


def test_a_mapping_with_an_extra_key_is_still_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["readings"] = [{"time": "2026-03-14T06:00Z",
                                        "value_tenths": 48,
                                        "note": "looked fine"}]
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"


def test_the_two_notations_produce_the_same_payload(harness, cold_chain):
    """The decisive property for consensus: a node whose model answered in
    one notation and a node whose model answered in the other must produce
    byte-identical payloads, or the round would split over a spelling."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.mock_panel(cold_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    objects = harness.contract.get_receipt("sub-1", 1)

    harness.submit(challenge_id, "sub-2", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["condition"]["readings"] = [
        [entry["time"], entry["value_tenths"]]
        for entry in COMPLIANT_READINGS]
    harness.clear()
    from conftest import BILL_OF_LADING, LOG_COMPLIANT
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-2") == "CLAIM_SUPPORTED"
    pairs = harness.contract.get_receipt("sub-2", 1)

    one = json.loads(objects)
    two = json.loads(pairs)
    for key in one:
        if key in ("submission_id",):
            continue
        assert one[key] == two[key], key


def test_an_overlong_basis_is_bounded_not_refused(harness, cold_chain):
    """A live round answered every question correctly and explained itself
    in a sentence longer than the 200-character bound, and the contract
    threw the whole reading away. The basis is prose: it is not compared
    between validators, nothing is derived from it, and no consumer gates
    on it. It is bounded now, not refused."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["basis"] = ("The records identify the lot and the container and "
                       "provide a return-air temperature log with eleven "
                       "timestamped readings across the requested window, "
                       "and the bill of lading states the same lot and "
                       "container as the log does throughout.")
    assert len(answer["basis"]) > 200
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    findings = json.loads(harness.contract.get_findings("sub-1"))
    assert len(findings["basis"]) == 200
    assert findings["basis"] == answer["basis"][:200]


def test_a_basis_that_is_not_a_string_is_still_refused(harness, cold_chain):
    """Bounding prose is not the same as accepting anything in its place."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["basis"] = {"text": "the records are fine"}
    harness.mock_panel(json.dumps(answer))
    assert harness.resolve("sub-1") == "EVIDENCE_UNAVAILABLE"
    assert resolved(harness)["panel_state"] == "INVALID"
