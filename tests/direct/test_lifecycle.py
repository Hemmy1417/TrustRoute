"""Deterministic lifecycle: who may do what, against which frozen
requirement, in what order, with which records, and by when.

Nothing in this file reaches the reading stage. Every assertion here is about
code that runs before any model is convened.
"""

import json

import pytest

from conftest import (BILL_OF_LADING, COLD_CHAIN, COLD_CHAIN_RECORDS,
                      COMPLIANCE_CLAIM, CUSTODY_CHAIN, CUSTODY_EVENTS,
                      CUSTODY_RECORDS, CARRIER, CUSTOMS, DELIVERY_CLAIM,
                      INSPECTION, ISSUERS, LOG_COMPLIANT, ORIGIN_CLAIM,
                      PORT, RAW_HOST, SCAN_ORIGIN, UNION, UNION_HOST,
                      WAREHOUSE_RECEIPT, definition, hexaddr, record,
                      record_sha, url_for)


def _cold(**changes):
    body = json.loads(json.dumps(COLD_CHAIN))
    body.update(changes)
    return body


def _records(*entries):
    return json.loads(json.dumps(list(entries)))


# == the contract describes itself =========================================

def test_config_is_self_describing(harness):
    config = json.loads(harness.contract.get_config())
    assert config["schema"] == "trustroute/1"
    assert config["verdicts"] == ["CLAIM_SUPPORTED", "CLAIM_NOT_ESTABLISHED",
                                  "INCONSISTENT_EVIDENCE",
                                  "EVIDENCE_UNAVAILABLE"]
    assert config["terminal_verdicts"] == ["CLAIM_SUPPORTED",
                                           "CLAIM_NOT_ESTABLISHED"]
    assert "SOURCE_AUTHENTICITY_UNVERIFIED" in config["evidence_statuses"]
    assert config["criteria"] == ["required_records_present",
                                  "records_consistent",
                                  "source_authenticity_verified",
                                  "required_event_supported"]
    assert config["bounds"]["rounds"] == 3
    assert config["bounds"]["records"] == 8
    assert config["moves_value"] is False


def test_stats_start_at_zero(harness):
    stats = json.loads(harness.contract.get_stats())
    assert stats == {"policies": 0, "challenges": 0, "submissions": 0,
                     "resolved": 0}


# == registering a policy ==================================================

@pytest.mark.parametrize("policy_id,reason", [
    ("", "1 to 64 characters"),
    ("a" * 65, "1 to 64 characters"),
    ("has space", "1 to 64 characters"),
    ("has/slash", "1 to 64 characters"),
])
def test_a_bad_policy_id_is_refused(harness, policy_id, reason):
    with harness.vm.expect_revert(reason):
        harness.register(policy_id)


def test_a_policy_id_is_claimed_once(harness):
    harness.register("pol-1")
    with harness.vm.expect_revert("taken"):
        harness.register("pol-1")


def test_the_registrant_owns_the_policy(harness):
    harness.register("pol-1")
    policy = json.loads(harness.contract.get_policy("pol-1"))
    assert policy["owner"] == hexaddr(harness.buyer)
    assert policy["latest_version"] == 0
    stats = json.loads(harness.contract.get_stats())
    assert stats["policies"] == 1


def test_an_unregistered_policy_has_no_views(harness):
    with harness.vm.expect_revert("no such policy"):
        harness.contract.get_policy("nope")


# == publishing a version ==================================================

def test_only_the_owner_publishes_a_version(harness):
    harness.register("pol-1")
    with harness.vm.expect_revert("only the policy owner"):
        harness.publish("pol-1", COLD_CHAIN, sender=harness.stranger)


def test_publishing_needs_a_registered_policy(harness):
    with harness.vm.expect_revert("no such policy"):
        harness.publish("pol-1", COLD_CHAIN)


def test_the_definition_must_be_json(harness):
    harness.register("pol-1")
    harness.vm.sender = harness.buyer
    with harness.vm.expect_revert("not valid json"):
        harness.contract.publish_policy_version("pol-1", "not json at all")
    with harness.vm.expect_revert("must be a JSON object"):
        harness.contract.publish_policy_version("pol-1", "[1, 2, 3]")


@pytest.mark.parametrize("changes,reason", [
    ({"claim_type": "GUESSWORK"}, "claim_type must be one of"),
    ({"requirement": ""}, "requirement must be 1 to 200"),
    ({"required_record_kinds": []}, "must list 1 to 8 kinds"),
    ({"required_record_kinds": ["NOT_A_KIND"]}, "unknown record kind"),
    ({"required_record_kinds": ["CONDITION_LOG", "CONDITION_LOG"]},
     "must not repeat a kind"),
    ({"identity_keys": [{"ref": "A", "label": "a"},
                        {"ref": "A", "label": "b"}]},
     "must not repeat a ref"),
    ({"identity_keys": [{"ref": "A"}]}, "exactly ref and label"),
    ({"issuers": []}, "issuers must list 1 to 6"),
    ({"issuers": [{"issuer": "X", "host": "localhost"}]},
     "not an admissible host"),
    ({"issuers": [{"issuer": "X", "host": "RAW.GITHUBUSERCONTENT.COM"}]},
     "must be lowercase"),
    ({"issuers": [{"issuer": "X", "host": "a.test"},
                  {"issuer": "X", "host": "b.test"}]},
     "must not repeat an issuer"),
    ({"compliance_criteria": [{"ref": "K1", "requirement": "r",
                               "record_kind": "PACKING_LIST"}]},
     "a kind the policy does not require"),
])
def test_a_malformed_definition_is_refused(harness, changes, reason):
    harness.register("pol-1")
    with harness.vm.expect_revert(reason):
        harness.publish("pol-1", _cold(**changes))


def test_an_unknown_definition_field_is_refused(harness):
    harness.register("pol-1")
    body = _cold()
    body["extra_rule"] = "please apply this too"
    with harness.vm.expect_revert("unknown definition field"):
        harness.publish("pol-1", body)


def test_a_missing_definition_field_is_refused(harness):
    harness.register("pol-1")
    body = _cold()
    del body["issuers"]
    with harness.vm.expect_revert("missing issuers"):
        harness.publish("pol-1", body)


# -- the checkpoint order has to be a real order --------------------------

@pytest.mark.parametrize("orders,reason", [
    ([1, 2, 2], "order must be 1..n"),
    ([1, 2, 4], "order must be 1..n"),
    ([0, 1, 2], "order must be 1..n"),
])
def test_checkpoint_orders_must_be_a_permutation(harness, orders, reason):
    harness.register("pol-c")
    events = json.loads(json.dumps(CUSTODY_EVENTS))
    for index in range(len(events)):
        events[index]["order"] = orders[index]
    body = json.loads(json.dumps(CUSTODY_CHAIN))
    body["custody_events"] = events
    with harness.vm.expect_revert(reason):
        harness.publish("pol-c", body)


def test_a_checkpoint_order_must_be_an_integer(harness):
    harness.register("pol-c")
    body = json.loads(json.dumps(CUSTODY_CHAIN))
    body["custody_events"][0]["order"] = True
    with harness.vm.expect_revert("order must be an integer"):
        harness.publish("pol-c", body)


# -- the condition requirement --------------------------------------------

def _condition(**changes):
    body = json.loads(json.dumps(COLD_CHAIN))
    body["condition_requirement"].update(changes)
    return body


@pytest.mark.parametrize("changes,reason", [
    ({"min_tenths": 90}, "range is inverted"),
    ({"min_tenths": 2.5}, "integer tenths"),
    ({"max_tenths": True}, "integer tenths"),
    ({"window_start": "not a time"}, "window_start is not a timestamp"),
    ({"window_end": "2026-03-14T06:00Z"}, "window does not advance"),
    ({"max_excursion_minutes": -1}, "must be 0 to 10080"),
    ({"max_excursion_minutes": 10081}, "must be 0 to 10080"),
    ({"max_excursion_minutes": 1.0}, "must be an integer"),
])
def test_a_malformed_condition_requirement_is_refused(harness, changes,
                                                      reason):
    harness.register("pol-1")
    with harness.vm.expect_revert(reason):
        harness.publish("pol-1", _condition(**changes))


def test_a_condition_policy_needs_a_range_and_a_log(harness):
    harness.register("pol-1")
    with harness.vm.expect_revert("must declare condition_requirement"):
        harness.publish("pol-1", _cold(condition_requirement=None))
    body = _cold(required_record_kinds=["BILL_OF_LADING"])
    with harness.vm.expect_revert("must require a CONDITION_LOG"):
        harness.publish("pol-1", body)


def test_each_claim_type_needs_the_part_that_answers_it(harness):
    harness.register("pol-a")
    body = json.loads(json.dumps(CUSTODY_CHAIN))
    body["custody_events"] = []
    with harness.vm.expect_revert("at least one checkpoint"):
        harness.publish("pol-a", body)

    harness.register("pol-b")
    body = json.loads(json.dumps(ORIGIN_CLAIM))
    body["origin_requirement"] = None
    with harness.vm.expect_revert("must declare origin_requirement"):
        harness.publish("pol-b", body)

    harness.register("pol-d")
    body = json.loads(json.dumps(DELIVERY_CLAIM))
    body["delivery_window"] = None
    with harness.vm.expect_revert("must declare delivery_window"):
        harness.publish("pol-d", body)

    harness.register("pol-e")
    body = json.loads(json.dumps(COMPLIANCE_CLAIM))
    body["compliance_criteria"] = []
    with harness.vm.expect_revert("at least one criterion"):
        harness.publish("pol-e", body)


def test_an_inverted_delivery_window_is_refused(harness):
    harness.register("pol-d")
    body = json.loads(json.dumps(DELIVERY_CLAIM))
    body["delivery_window"] = {"not_before": "2026-03-18T00:00Z",
                               "not_after": "2026-03-15T00:00Z"}
    with harness.vm.expect_revert("delivery window is inverted"):
        harness.publish("pol-d", body)


# -- versions -------------------------------------------------------------

def test_versions_are_numbered_and_hashed(harness):
    harness.register("pol-1")
    assert harness.publish("pol-1", COLD_CHAIN) == 1
    assert harness.publish("pol-1", _cold(requirement="a tighter rule")) == 2
    first = json.loads(harness.contract.get_policy_version("pol-1", 1))
    second = json.loads(harness.contract.get_policy_version("pol-1", 2))
    assert first["definition_hash"] != second["definition_hash"]
    assert json.loads(harness.contract.get_policy("pol-1"))[
        "latest_version"] == 2


def test_the_definition_hash_covers_the_whole_definition(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.register("pol-2")
    harness.publish("pol-2", COLD_CHAIN)
    one = json.loads(harness.contract.get_policy_version("pol-1", 1))
    two = json.loads(harness.contract.get_policy_version("pol-2", 1))
    # The same definition hashes the same, whoever published it.
    assert one["definition_hash"] == two["definition_hash"]

    harness.publish("pol-2", _condition(max_excursion_minutes=31))
    three = json.loads(harness.contract.get_policy_version("pol-2", 2))
    assert three["definition_hash"] != two["definition_hash"]


def test_a_policy_runs_out_of_versions(harness):
    harness.register("pol-1")
    for index in range(16):
        harness.publish("pol-1", _cold(requirement="rule " + str(index)))
    with harness.vm.expect_revert("used all 16 versions"):
        harness.publish("pol-1", _cold(requirement="one more"))


def test_an_unknown_version_has_no_views(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    with harness.vm.expect_revert("no such policy version"):
        harness.contract.get_policy_version("pol-1", 2)


# == revocation ============================================================

def test_only_the_owner_revokes(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the policy owner"):
        harness.contract.revoke_policy_version("pol-1", 1)


def test_a_version_is_revoked_once(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.vm.sender = harness.buyer
    harness.contract.revoke_policy_version("pol-1", 1)
    assert json.loads(harness.contract.get_policy_version(
        "pol-1", 1))["revoked"] is True
    with harness.vm.expect_revert("already revoked"):
        harness.contract.revoke_policy_version("pol-1", 1)


def test_a_revoked_version_takes_no_new_work(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1")
    harness.vm.sender = harness.buyer
    harness.contract.revoke_policy_version("pol-1", 1)

    with harness.vm.expect_revert("revoked"):
        harness.open_challenge("pol-1", 1, "chal-2")
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    with harness.vm.expect_revert("revoked"):
        harness.submit("chal-1", "sub-1", COLD_CHAIN_RECORDS)


# == opening a challenge ===================================================

def test_a_challenge_binds_one_version_and_its_hash(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.publish("pol-1", _cold(requirement="a later rule"))
    harness.open_challenge("pol-1", 1, "chal-1")
    challenge = json.loads(harness.contract.get_challenge("chal-1"))
    version = json.loads(harness.contract.get_policy_version("pol-1", 1))
    assert challenge["policy_version"] == 1
    assert challenge["definition_hash"] == version["definition_hash"]
    assert harness.contract.get_policy_hash("chal-1") == \
        version["definition_hash"]
    assert harness.contract.get_policy_version_of("chal-1") == 1


def test_a_later_version_does_not_touch_an_open_challenge(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1")
    before = harness.contract.get_policy_hash("chal-1")
    harness.publish("pol-1", _cold(requirement="changed after the fact"))
    assert harness.contract.get_policy_hash("chal-1") == before


@pytest.mark.parametrize("kwargs,reason", [
    ({"challenge_id": "has space"}, "a challenge id is 1 to 64"),
    ({"lot": "has space"}, "a shipment or lot id is 1 to 64"),
    ({"origin": ""}, "declared_origin is 1 to 200"),
    ({"origin": "x" * 201}, "declared_origin is 1 to 200"),
    ({"days": 0}, "deadline_days is 1 to 365"),
    ({"days": 366}, "deadline_days is 1 to 365"),
    ({"days": True}, "deadline_days is 1 to 365"),
])
def test_a_bad_challenge_is_refused(harness, kwargs, reason):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    with harness.vm.expect_revert(reason):
        harness.open_challenge("pol-1", 1, **kwargs)


def test_a_challenge_id_is_claimed_once(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1")
    with harness.vm.expect_revert("taken"):
        harness.open_challenge("pol-1", 1, "chal-1")


def test_the_deadline_is_computed_from_the_transaction_clock(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1", days=10)
    challenge = json.loads(harness.contract.get_challenge("chal-1"))
    assert challenge["opened_at"] == "2026-03-20T09:30Z"
    assert challenge["deadline"] == "2026-03-30T09:30Z"


def test_only_the_opener_cancels_a_challenge(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1")
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the account that opened it"):
        harness.contract.cancel_challenge("chal-1")
    harness.vm.sender = harness.buyer
    harness.contract.cancel_challenge("chal-1")
    assert harness.contract.get_challenge_status("chal-1") == "CANCELLED"
    with harness.vm.expect_revert("already cancelled"):
        harness.contract.cancel_challenge("chal-1")


def test_a_cancelled_challenge_takes_no_submissions(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.vm.sender = harness.buyer
    harness.contract.cancel_challenge(challenge_id)
    with harness.vm.expect_revert("cancelled"):
        harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)


# == submitting records ====================================================

@pytest.mark.parametrize("kwargs,reason", [
    ({"submission_id": "has space"}, "a submission id is 1 to 64"),
    ({"reference": ""}, "submitter_reference is 1 to 200"),
    ({"summary": "x" * 201}, "claim_summary is 1 to 200"),
])
def test_a_bad_submission_is_refused(harness, cold_chain, kwargs, reason):
    harness, _policy_id, challenge_id = cold_chain
    with harness.vm.expect_revert(reason):
        harness.submit(challenge_id, **kwargs)


def test_a_submission_id_is_claimed_once(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    with harness.vm.expect_revert("taken"):
        harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)


def test_the_records_must_be_a_bounded_json_list(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.vm.sender = harness.submitter
    with harness.vm.expect_revert("not valid json"):
        harness.contract.submit_records("sub-1", challenge_id, "ref", "sum",
                                        "{nope")
    with harness.vm.expect_revert("submit 1 to 8 records"):
        harness.contract.submit_records("sub-1", challenge_id, "ref", "sum",
                                        "[]")


def test_each_record_needs_exactly_the_declared_fields(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    entry = dict(COLD_CHAIN_RECORDS[0])
    del entry["declared_issuer"]
    with harness.vm.expect_revert("exactly record_id, kind"):
        harness.submit(challenge_id, "sub-1", [entry])
    entry = dict(COLD_CHAIN_RECORDS[0])
    entry["note"] = "extra"
    with harness.vm.expect_revert("exactly record_id, kind"):
        harness.submit(challenge_id, "sub-2", [entry])


@pytest.mark.parametrize("location", [
    "http://raw.githubusercontent.com/x",      # not https
    "https://localhost/x",
    "https://records.localhost/x",
    "https://service.internal/x",
    "https://127.0.0.1/x",
    "https://10.0.0.5/x",
    "https://192.168.0.1/x",
    "https://0177.0.0.1/x",                    # legacy spelling
    "https://user:pass@example.org/x",         # embedded credentials
    "https://example.org:8443/x",              # unexpected port
    "https://single/x",                        # no dot
    "https://bad_label.example.org/x",
])
def test_an_inadmissible_location_is_refused(harness, cold_chain, location):
    harness, _policy_id, challenge_id = cold_chain
    entry = dict(COLD_CHAIN_RECORDS[0])
    entry["location"] = location
    with harness.vm.expect_revert("public https url"):
        harness.submit(challenge_id, "sub-1", [entry,
                                               COLD_CHAIN_RECORDS[1]])


def test_every_record_needs_the_hash_of_its_bytes(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    entry = dict(COLD_CHAIN_RECORDS[0])
    entry["sha256"] = "not a hash"
    with harness.vm.expect_revert("64 lowercase hex characters"):
        harness.submit(challenge_id, "sub-1", [entry,
                                               COLD_CHAIN_RECORDS[1]])


def test_the_same_bytes_cannot_be_submitted_twice_in_one_submission(
        harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    twin = dict(COLD_CHAIN_RECORDS[0])
    twin["record_id"] = "R9"
    with harness.vm.expect_revert("the same bytes are submitted twice"):
        harness.submit(challenge_id, "sub-1",
                       [COLD_CHAIN_RECORDS[0], COLD_CHAIN_RECORDS[1], twin])


def test_a_duplicate_record_id_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    twin = dict(COLD_CHAIN_RECORDS[1])
    twin["record_id"] = "R1"
    with harness.vm.expect_revert("duplicate record id"):
        harness.submit(challenge_id, "sub-1", [COLD_CHAIN_RECORDS[0], twin])


def test_an_unknown_record_kind_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    entry = dict(COLD_CHAIN_RECORDS[0])
    entry["kind"] = "VIBES"
    with harness.vm.expect_revert("unknown record kind"):
        harness.submit(challenge_id, "sub-1", [entry,
                                               COLD_CHAIN_RECORDS[1]])


def test_an_issuer_the_requirement_does_not_name_is_refused(harness,
                                                            cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    entry = dict(COLD_CHAIN_RECORDS[0])
    entry["declared_issuer"] = "Someone Else Entirely"
    with harness.vm.expect_revert("does not name the issuer"):
        harness.submit(challenge_id, "sub-1", [entry,
                                               COLD_CHAIN_RECORDS[1]])


def test_every_required_kind_must_be_offered(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    with harness.vm.expect_revert("needs a record of kind BILL_OF_LADING"):
        harness.submit(challenge_id, "sub-1", [COLD_CHAIN_RECORDS[0]])


def test_a_challenge_stops_taking_submissions_at_the_cap(harness,
                                                         cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    # Eight distinct submissions, each with its own bytes, is the cap. The
    # records differ only in their declared hash, which is enough: the cap
    # is about the challenge, not about the fetches.
    for index in range(8):
        entry = dict(COLD_CHAIN_RECORDS[0])
        entry["sha256"] = ("%064x" % (index + 1))
        harness.submit(challenge_id, "sub-" + str(index + 1),
                       [entry, dict(COLD_CHAIN_RECORDS[1],
                                    sha256="%064x" % (100 + index))])
    with harness.vm.expect_revert("reached 8 submissions"):
        harness.submit(challenge_id, "sub-9", COLD_CHAIN_RECORDS)


def test_the_deadline_closes_the_challenge(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.set_clock("2026-05-20T09:30:00.000+00:00")
    with harness.vm.expect_revert("that challenge closed on"):
        harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)


def test_the_same_bytes_cannot_be_evidence_for_another_lot(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    harness.open_challenge("pol-1", 1, "chal-1", lot="LOT-A")
    harness.open_challenge("pol-1", 1, "chal-2", lot="LOT-B")
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    harness.submit("chal-1", "sub-1", COLD_CHAIN_RECORDS)
    with harness.vm.expect_revert("already evidence for another shipment"):
        harness.submit("chal-2", "sub-2", COLD_CHAIN_RECORDS)


def test_one_shipment_may_be_the_subject_of_several_requirements(harness):
    """A live run caught this. One lot is legitimately judged against more
    than one requirement - a cold-chain rule and a custody rule, opened by a
    buyer and a carrier - and the same bill of lading is evidence in both.
    The replay rule binds bytes to the lot, not to the challenge."""
    harness.register("pol-cold")
    harness.publish("pol-cold", COLD_CHAIN)
    harness.register("pol-cust")
    harness.publish("pol-cust", CUSTODY_CHAIN)
    harness.open_challenge("pol-cold", 1, "chal-cold", lot="LOT-4471-B")
    harness.open_challenge("pol-cust", 1, "chal-cust", lot="LOT-4471-B")
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING, SCAN_ORIGIN)
    harness.submit("chal-cold", "sub-cold", COLD_CHAIN_RECORDS)
    # The bill of lading again, for the same lot, under another requirement.
    shared = [record("R1", SCAN_ORIGIN, "CUSTODY_SCAN", PORT),
              record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER)]
    harness.submit("chal-cust", "sub-cust", shared)
    assert json.loads(harness.contract.get_submission(
        "sub-cust"))["status"] == "PENDING"
    # Still recorded against the submission that first bound it.
    assert harness.contract.record_first_seen(
        record_sha(BILL_OF_LADING)) == "sub-cold"


def test_the_same_bytes_may_be_resubmitted_in_their_own_challenge(harness,
                                                                  cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.submit(challenge_id, "sub-2", COLD_CHAIN_RECORDS)
    assert harness.contract.record_first_seen(
        record_sha(LOG_COMPLIANT)) == "sub-1"


def test_the_record_registry_reports_nothing_for_unseen_bytes(harness):
    assert harness.contract.record_first_seen("%064x" % 7) == ""


def test_a_submission_records_its_submitter_and_digest(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    stored = json.loads(harness.contract.get_submission("sub-1"))
    assert stored["submitter"] == hexaddr(harness.submitter)
    assert len(stored["evidence_digest"]) == 64
    assert stored["submitted_at"] == "2026-03-20T09:30Z"
    assert stored["rounds_used"] == 0
    stats = json.loads(harness.contract.get_stats())
    assert stats["submissions"] == 1


# == resolving: the guards before any round ================================

def test_resolving_an_unknown_submission_is_refused(harness):
    with harness.vm.expect_revert("no such submission"):
        harness.resolve("nope")


def test_a_cancelled_challenge_blocks_resolution(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.vm.sender = harness.buyer
    harness.contract.cancel_challenge(challenge_id)
    with harness.vm.expect_revert("that challenge is cancelled"):
        harness.resolve("sub-1")


def test_a_revoked_version_blocks_resolution(harness, cold_chain):
    harness, policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.vm.sender = harness.buyer
    harness.contract.revoke_policy_version(policy_id, 1)
    with harness.vm.expect_revert("revoked"):
        harness.resolve("sub-1")


# == cancelling a submission ===============================================

def test_a_stranger_cannot_cancel_a_submission(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.vm.sender = harness.stranger
    with harness.vm.expect_revert("only the submitter or the challenge"):
        harness.contract.cancel_submission("sub-1")


def test_the_submitter_cancels_a_submission(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.vm.sender = harness.submitter
    harness.contract.cancel_submission("sub-1")
    stored = json.loads(harness.contract.get_submission("sub-1"))
    assert stored["status"] == "CANCELLED"
    assert stored["verdict"] == ""
    with harness.vm.expect_revert("that submission is cancelled"):
        harness.resolve("sub-1")


def test_the_challenge_opener_cancels_a_submission(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.vm.sender = harness.buyer
    harness.contract.cancel_submission("sub-1")
    assert json.loads(harness.contract.get_submission(
        "sub-1"))["status"] == "CANCELLED"


def test_retry_needs_a_retryable_submission(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    harness.vm.sender = harness.submitter
    with harness.vm.expect_revert("only a retryable submission"):
        harness.contract.retry_submission("sub-1")


# == the bounded views =====================================================

def test_submissions_are_listed_in_bounded_pages(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    for index in range(5):
        entry = dict(COLD_CHAIN_RECORDS[0], sha256="%064x" % (index + 1))
        other = dict(COLD_CHAIN_RECORDS[1], sha256="%064x" % (200 + index))
        harness.submit(challenge_id, "sub-" + str(index + 1),
                       [entry, other])
    page = json.loads(harness.contract.list_submissions(challenge_id, 0, 2))
    assert page["total"] == 5
    assert page["limit"] == 2
    assert [row["submission_id"] for row in page["submissions"]] == ["sub-1",
                                                                     "sub-2"]
    page = json.loads(harness.contract.list_submissions(challenge_id, 4, 50))
    assert [row["submission_id"] for row in page["submissions"]] == ["sub-5"]
    # A limit above the cap is clamped, not honoured.
    page = json.loads(harness.contract.list_submissions(challenge_id, 0, 500))
    assert page["limit"] == 50
    page = json.loads(harness.contract.list_submissions(challenge_id, 0, 0))
    assert page["limit"] == 1


def test_a_missing_receipt_is_refused(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    with harness.vm.expect_revert("no such round"):
        harness.contract.get_receipt("sub-1", 1)


def test_an_unresolved_submission_is_not_consumable(harness, cold_chain):
    harness, _policy_id, challenge_id = cold_chain
    harness.submit(challenge_id, "sub-1", COLD_CHAIN_RECORDS)
    assert harness.contract.is_claim_supported("sub-1", "2026-03-21T09:30Z") \
        is False
    assert harness.contract.is_consumable("sub-1", "2026-03-21T09:30Z") \
        is False
    assert harness.contract.freshness("sub-1", "2026-03-21T09:30Z") == \
        "UNKNOWN"


def test_an_unknown_submission_fails_every_gate_closed(harness):
    assert harness.contract.is_claim_supported("nope", "2026-03-21T09:30Z") \
        is False
    assert harness.contract.is_consumable("nope", "2026-03-21T09:30Z") is False
    assert harness.contract.is_fresh("nope", "2026-03-21T09:30Z") is False
    assert harness.contract.freshness("nope", "2026-03-21T09:30Z") == "UNKNOWN"


def test_the_issuer_registry_is_part_of_the_published_requirement(harness):
    harness.register("pol-1")
    harness.publish("pol-1", COLD_CHAIN)
    version = json.loads(harness.contract.get_policy_version("pol-1", 1))
    hosts = {entry["issuer"]: entry["host"]
             for entry in version["definition"]["issuers"]}
    assert hosts[CARRIER] == RAW_HOST
    assert hosts[UNION] == UNION_HOST
    assert len(ISSUERS) == 4
