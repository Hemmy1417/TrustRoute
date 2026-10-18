"""Tests for things the live network did that the mocks did not.

Five live rounds on Studionet shaped this file. In order: a model answered
with readings as positional pairs; a model invented its own field names
because the prompt never showed it the answer shape; an explanation one
sentence too long threw away a correct reading; a round reached
NO_MAJORITY because two models had been asked to copy the same eleven-line
log and copied different amounts of it; and four scenarios in one run were
thrown away because models volunteered an answer to a question their
policy never asked.

The last of those is why no model reads a measurement log any more - code
does, and `test_hardening.py` tests that parser. The notation tests that
used to live here for readings went with it; what remains is the notation
tolerance that still applies, to identity values, and the two lessons about
the prompt and the explanation.

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


def test_a_volunteered_answer_to_an_unasked_question_is_dropped(harness,
                                                                cold_chain):
    """The fifth live lesson, and the one with the widest reach.

    A whole seven-scenario run lost four of its scenarios to this. The
    cold-chain and custody policies declare no origin requirement, and
    models kept answering `origin: SUPPORTED` anyway - reasonably, since
    the records really do name a growing region. The contract refused the
    entire answer for it, so a complete and correct reading of the records
    became EVIDENCE_UNAVAILABLE.

    It was also a consensus hazard, which is the worse half. Whether a
    round was usable depended on an irrelevant model whim, so one
    scenario split 1 agree / 3 disagree purely on which nodes happened to
    volunteer. The fix removes that split source: `origin_requirement is
    None` is a deterministic fact from the frozen definition, so every
    node normalises the field to NOT_ASSESSED identically.

    The general rule, worth keeping for any primitive of this family: a
    field code never reads must not be able to fail a round.
    `test_hardening.py` holds the narrow behavioural tests for both
    directions of it."""
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    answer = json.loads(cold_answer(harness))
    answer["origin"] = {"finding": "SUPPORTED", "record_id": "R1",
                        "quote": LOG_LOT}
    answer["delivery"] = {"state": "READ", "record_id": "R1",
                          "stated_time": "2026-03-16T18:00Z",
                          "quote": LOG_LOT}
    harness.mock_panel(json.dumps(answer))

    # Both volunteered at once, as a model actually does it.
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"
    stored = resolved(harness)
    assert stored["origin_state"] == "NOT_ASSESSED"
    assert stored["delivery_state"] == "NOT_DECLARED"
    assert stored["panel_state"] == "ASSESSED"
