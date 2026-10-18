"""A first pass through the whole lifecycle, used to shake out the harness.

Kept in the suite because it is the only test that walks register → publish →
open → submit → resolve in one place and asserts each step actually
happened, rather than starting from a fixture.
"""

import json

from conftest import (AS_OF, BILL_OF_LADING, COLD_CHAIN, COLD_CHAIN_RECORDS,
                      LOG_COMPLIANT, quote_from)


LOT_QUOTE = quote_from(LOG_COMPLIANT, "Lot number")
CONTAINER_QUOTE = quote_from(LOG_COMPLIANT, "Container:")
BOL_LOT_QUOTE = quote_from(BILL_OF_LADING, "Lot number")
BOL_CONTAINER_QUOTE = quote_from(BILL_OF_LADING, "Container:")
READING_QUOTE = quote_from(LOG_COMPLIANT, "2026-03-14T06:00Z")

READINGS = [
    {"time": "2026-03-14T06:00Z", "value_tenths": 48},
    {"time": "2026-03-14T12:00Z", "value_tenths": 51},
    {"time": "2026-03-14T18:00Z", "value_tenths": 49},
    {"time": "2026-03-15T00:00Z", "value_tenths": 50},
    {"time": "2026-03-15T06:00Z", "value_tenths": 52},
    {"time": "2026-03-15T12:00Z", "value_tenths": 47},
    {"time": "2026-03-15T18:00Z", "value_tenths": 50},
    {"time": "2026-03-16T00:00Z", "value_tenths": 53},
    {"time": "2026-03-16T06:00Z", "value_tenths": 51},
    {"time": "2026-03-16T12:00Z", "value_tenths": 49},
    {"time": "2026-03-16T18:00Z", "value_tenths": 50},
]


def cold_chain_answer(harness, readings=None):
    return harness.panel(
        identity=[("LOT", [("R1", "LOT-4471/B", LOT_QUOTE),
                           ("R2", "LOT-4471/B", BOL_LOT_QUOTE)]),
                  ("CONTAINER", [("R1", "MSKU-774120-3", CONTAINER_QUOTE),
                                 ("R2", "MSKU-774120-3",
                                  BOL_CONTAINER_QUOTE)])],
        condition={"state": "READ", "record_id": "R1",
                   "readings": readings if readings is not None else READINGS,
                   "quote": READING_QUOTE},
    )


def test_the_whole_lifecycle_of_a_supported_claim(harness):
    assert harness.register("pol-1") == "pol-1"
    assert harness.publish("pol-1", COLD_CHAIN) == 1

    policy = json.loads(harness.contract.get_policy_version("pol-1", 1))
    assert policy["claim_type"] == "CONDITION"
    assert policy["revoked"] is False
    assert len(policy["definition_hash"]) == 64

    assert harness.open_challenge("pol-1", 1, "chal-1") == "chal-1"
    challenge = json.loads(harness.contract.get_challenge("chal-1"))
    assert challenge["status"] == "OPEN"
    assert challenge["definition_hash"] == policy["definition_hash"]

    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    assert harness.submit("chal-1", "sub-1", COLD_CHAIN_RECORDS) == "sub-1"
    submission = json.loads(harness.contract.get_submission("sub-1"))
    assert submission["status"] == "PENDING"
    assert len(submission["records"]) == 2
    assert submission["definition_hash"] == policy["definition_hash"]

    harness.mock_panel(cold_chain_answer(harness))
    assert harness.resolve("sub-1") == "CLAIM_SUPPORTED"

    stored = json.loads(harness.contract.get_submission("sub-1"))
    assert stored["status"] == "RESOLVED"
    assert stored["verdict"] == "CLAIM_SUPPORTED"
    assert stored["evidence_status"] == "EVIDENCE_SUFFICIENT"
    assert stored["condition_state"] == "HELD"
    assert stored["identity_state"] == "CONSISTENT"
    assert stored["authenticity_state"] == "AUTHENTICATED_ORIGIN"
    assert stored["condition_worst_excursion_minutes"] == 0
    assert stored["condition_readings_used"] == 11
    assert stored["directed_text_hits"] == 0
    assert stored["criteria"] == {
        "required_records_present": True,
        "records_consistent": True,
        "source_authenticity_verified": True,
        "required_event_supported": True,
    }
    for row in stored["records"]:
        assert row["status"] == "RECORD_READABLE"
        assert row["authenticity"] == "AUTHENTICATED_ORIGIN"
        assert row["byte_count"] > 0

    assert harness.contract.is_claim_supported("sub-1", AS_OF) is True
    assert harness.contract.is_consumable("sub-1", AS_OF) is True
    assert harness.contract.freshness("sub-1", AS_OF) == "RELIABLE"

    record = json.loads(harness.contract.policy_record("pol-1", 1))
    assert record["CLAIM_SUPPORTED"] == 1
    assert record["TOTAL"] == 1
