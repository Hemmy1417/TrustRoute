#!/usr/bin/env python3
"""Live evidence driver for hosted Studionet.

Deploys `contracts/trustroute.py` as it stands, then puts synthetic
shipments to real validators reading real records:

    A  a cold chain whose log holds the range across the window
    B  a cold chain with an eighteen-hour excursion
    C  a custody chain whose checkpoints are out of order
    D  records that disagree about which lot they describe
    E  a record that instructs whoever reads it
    F  a certificate not served from the host its issuer publishes from
    G  a required record that cannot be fetched, then a retry

Every transaction hash, every stored result and every assertion is printed.

    python scripts/live.py --commit <sha>                  deploy and run all
    python scripts/live.py --commit <sha> --address 0x...  reuse a deployment
    python scripts/live.py --commit <sha> --scenarios a,b

The fixtures must already be pushed: the records are read from
raw.githubusercontent.com at the commit given, so the bytes the validators
fetch are pinned and cannot change under a round.

A signer comes from TRUSTROUTE_SIGNER_KEY when it is set; otherwise a
throwaway account is generated and funded from the Studionet faucet. No key
is ever printed.
"""

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.request

from genlayer_py import (chains, create_account, create_client,
                         generate_private_key)
from genlayer_py.types import TransactionStatus


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "trustroute.py"
FIXTURES = ROOT / "fixtures"
PROOFS = ROOT / "docs" / "proofs"

RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"
RAW_HOST = "raw.githubusercontent.com"
RAW = "https://" + RAW_HOST + "/Hemmy1417/TrustRoute/%s/fixtures/%s"

SCAN_ORIGIN = "custody-scan-origin.txt"
SCAN_TRANSIT = "custody-scan-transit.txt"
SCAN_DESTINATION = "custody-scan-destination.txt"
SCAN_OUT_OF_ORDER = "custody-scan-destination-out-of-order.txt"
SCAN_DIRECTED = "custody-scan-directed.txt"
LOG_COMPLIANT = "condition-log-compliant.txt"
LOG_EXCURSION = "condition-log-excursion.txt"
DELIVERY_NOTE = "delivery-confirmation.txt"
CUSTOMS_ENTRY = "customs-entry.txt"
BILL_OF_LADING = "bill-of-lading.txt"
INSPECTION = "inspection-certificate.txt"
ORIGIN_CERTIFICATE = "origin-certificate.txt"
WAREHOUSE_RECEIPT = "warehouse-receipt.txt"
WAREHOUSE_CONFLICTING = "warehouse-receipt-conflicting-lot.txt"

RECORDS = [SCAN_ORIGIN, SCAN_TRANSIT, SCAN_DESTINATION, SCAN_OUT_OF_ORDER,
           SCAN_DIRECTED, LOG_COMPLIANT, LOG_EXCURSION, DELIVERY_NOTE,
           CUSTOMS_ENTRY, BILL_OF_LADING, INSPECTION, ORIGIN_CERTIFICATE,
           WAREHOUSE_RECEIPT, WAREHOUSE_CONFLICTING]

PORT = "Tema Port Authority (synthetic)"
CARRIER = "Meridian Cold Logistics (synthetic)"
CUSTOMS = "Accra Customs Service (synthetic)"
UNION = "Ashanti Growers Union (synthetic)"
UNION_HOST = "records.ashanti-growers.org"

ISSUERS = [
    {"issuer": PORT, "host": RAW_HOST},
    {"issuer": CARRIER, "host": RAW_HOST},
    {"issuer": CUSTOMS, "host": RAW_HOST},
    {"issuer": UNION, "host": UNION_HOST},
]

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

AS_OF = "2026-10-20T12:00Z"

# Ids carry a per-run tag. A policy id is claimed once for the life of a
# contract, so without this a second run against the same deployment would
# be refused - and re-running against the canonical deployment is exactly
# what a reviewer should be able to do.
TAG = [""]


def tagged(base: str) -> str:
    return base + TAG[0]

log_lines = []


def say(text=""):
    print(text, flush=True)
    log_lines.append(text)


# -- the requirements --------------------------------------------------------

def definition(claim_type, kinds, identity=None, custody=None, origin=None,
               condition=None, delivery=None, compliance=None,
               requirement="synthetic verification requirement"):
    return {
        "claim_type": claim_type,
        "requirement": requirement,
        "required_record_kinds": kinds,
        "identity_keys": identity if identity is not None else [],
        "custody_events": custody if custody is not None else [],
        "origin_requirement": origin,
        "condition_requirement": condition,
        "delivery_window": delivery,
        "compliance_criteria": compliance if compliance is not None else [],
        "issuers": ISSUERS,
    }


LOT_KEY = {"ref": "LOT", "label": "lot number"}
CONTAINER_KEY = {"ref": "CONTAINER", "label": "container number"}

CUSTODY_EVENTS = [
    {"ref": "C1", "description": "received into origin terminal custody",
     "order": 1},
    {"ref": "C2", "description": "custody accepted by the carrier",
     "order": 2},
    {"ref": "C3", "description": "received into destination terminal custody",
     "order": 3},
]

COLD_CHAIN = definition(
    "CONDITION", ["CONDITION_LOG", "BILL_OF_LADING"],
    identity=[LOT_KEY, CONTAINER_KEY],
    condition={"metric": "return air temperature",
               "unit": "degrees Celsius",
               "series_format": "TIMESTAMP_VALUE_LINES",
               "min_tenths": 20, "max_tenths": 80,
               "window_start": "2026-03-14T06:00Z",
               "window_end": "2026-03-16T18:00Z",
               "max_excursion_minutes": 30},
    requirement="the reefer held 2.0 to 8.0 C across the carriage window")

CUSTODY_CHAIN = definition(
    "CUSTODY", ["CUSTODY_SCAN"], identity=[LOT_KEY],
    custody=CUSTODY_EVENTS,
    requirement="the lot passed every declared checkpoint in order")

ORIGIN_CLAIM = definition(
    "ORIGIN", ["ORIGIN_CERTIFICATE", "CUSTOMS_ENTRY"], identity=[LOT_KEY],
    origin={"requirement": "a record identifies the lot's growing region"},
    requirement="the lot came from the origin claimed for it")


# -- published bytes ---------------------------------------------------------

def published(commit, name):
    """(url, sha256, size) for the bytes a validator will actually fetch."""
    url = RAW % (commit, name)
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    digest = hashlib.sha256(body).hexdigest()
    local = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
    if digest != local:
        raise SystemExit("published %s does not match the local file "
                         "(%s vs %s)" % (name, digest, local))
    return url, digest, len(body)


def record_entry(record_id, kind, issuer, name, published_map, location=None):
    url, digest, _size = published_map[name]
    return {"record_id": record_id, "kind": kind,
            "location": location if location is not None else url,
            "sha256": digest, "declared_issuer": issuer}


# -- chain -------------------------------------------------------------------

def rpc(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                          "params": params}).encode("utf-8")
    request = urllib.request.Request(
        RPC, data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def signer():
    key = os.environ.get("TRUSTROUTE_SIGNER_KEY")
    if key:
        account = create_account(account_private_key=key)
        say("signer: provided through the environment, %s" % account.address)
        return account, False
    account = create_account(account_private_key=generate_private_key())
    say("signer: generated for this run, %s" % account.address)
    return account, True


def fund(address):
    result = rpc("sim_fundAccount", [address, 500000000000000000000])
    if "error" in result:
        raise SystemExit("faucet refused: %s" % result["error"])
    say("faucet: funded %s" % address)
    time.sleep(3)


def consensus_summary(receipt):
    """Agreement as the receipt records it. An idle validator is not a
    disagreeing one, and collapsing the two would overstate dissent as
    easily as it would hide it."""
    data = receipt.get("consensus_data") or {}
    votes = data.get("votes") or {}
    if not votes:
        return "no votes recorded"
    agree = sum(1 for v in votes.values() if str(v).lower() == "agree")
    disagree = sum(1 for v in votes.values()
                   if str(v).lower().startswith("disagree"))
    other = len(votes) - agree - disagree
    return "%d agree, %d disagree, %d idle of %d" % (
        agree, disagree, other, len(votes))


def execution_result(receipt):
    """On this network the top-level execution_result is empty; the real
    value is on the leader receipt."""
    named = receipt.get("execution_result_name") or receipt.get("result_name")
    leader = (receipt.get("consensus_data") or {}).get("leader_receipt")
    if isinstance(leader, list) and leader:
        return str(leader[0].get("execution_result") or named or "unknown")
    return str(named or "unknown")


def lifecycle(receipt):
    return str(receipt.get("status_name") or receipt.get("status"))


def revert_reason(receipt):
    try:
        leader = receipt.get("consensus_data", {}).get("leader_receipt")
        if isinstance(leader, list) and leader:
            return str(leader[0].get("result", {}).get("payload", ""))[:300]
    except Exception:
        pass
    return ""


def _hex(value):
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


class Chain:
    def __init__(self, account):
        self.client = create_client(chain=chains.studionet, account=account)
        self.account = account
        self.transactions = []
        self.address = ""

    def deploy(self):
        code = CONTRACT.read_bytes()
        say("deploying %d bytes, sha256 %s"
            % (len(code), hashlib.sha256(code).hexdigest()))
        tx_hash = self.client.deploy_contract(code=code.decode("utf-8"),
                                              args=[],
                                              consensus_max_rotations=3)
        receipt = self.client.wait_for_transaction_receipt(
            transaction_hash=tx_hash, status=TransactionStatus.ACCEPTED,
            interval=5000, retries=80)
        address = ((receipt.get("data") or {}).get("contract_address")
                   or ((receipt.get("tx_data_decoded") or {})
                       .get("contract_address")))
        if not address:
            raise SystemExit("no contract address in the receipt: %s"
                             % json.dumps(receipt)[:400])
        result = execution_result(receipt)
        say("deploy tx %s" % _hex(tx_hash))
        say("deploy lifecycle %s, execution %s, %s"
            % (lifecycle(receipt), result, consensus_summary(receipt)))
        if result.upper().endswith("ERROR"):
            raise SystemExit("deployment executed with an error: %s"
                             % revert_reason(receipt))
        self.address = address
        self.transactions.append(("deploy", _hex(tx_hash)))
        say("contract %s" % address)
        say("explorer %s/address/%s" % (EXPLORER, address))
        return address, _hex(tx_hash)

    def bind(self, address):
        self.address = address
        say("reusing deployment %s" % address)

    def write(self, method, args, label, allow_error=False):
        tx_hash = self.client.write_contract(
            address=self.address, function_name=method, args=args,
            consensus_max_rotations=3)
        receipt = self.client.wait_for_transaction_receipt(
            transaction_hash=tx_hash, status=TransactionStatus.ACCEPTED,
            interval=5000, retries=100)
        result = execution_result(receipt)
        say("  %-28s tx %s  %s  %s"
            % (label, _hex(tx_hash), result, consensus_summary(receipt)))
        if result.upper().endswith("ERROR") and not allow_error:
            say("  revert: %s" % revert_reason(receipt))
            raise SystemExit("%s failed on chain" % label)
        self.transactions.append((label, _hex(tx_hash)))
        return _hex(tx_hash), receipt

    def read(self, method, args=None):
        return self.client.read_contract(address=self.address,
                                         function_name=method,
                                         args=args or [])

    def finality(self, tx_hash):
        tx = self.client.get_transaction(transaction_hash=tx_hash)
        return lifecycle(tx), execution_result(tx), consensus_summary(tx)


# -- assertions --------------------------------------------------------------

FAILURES = []


def expect(label, actual, wanted):
    ok = actual == wanted
    say("    %-44s %s" % (label, "OK" if ok else
                          ("FAIL got %r wanted %r" % (actual, wanted))))
    if not ok:
        FAILURES.append(label)
    return ok


def expect_in(label, actual, wanted):
    ok = actual in wanted
    say("    %-44s %s" % (label, ("OK (%s)" % actual) if ok else
                          ("FAIL got %r wanted one of %r" % (actual,
                                                             wanted))))
    if not ok:
        FAILURES.append(label)
    return ok


def resolve_and_read(chain, submission_id, label):
    """Resolve, then read the stored state. The receipt is never the proof:
    a round whose validators do not reach a majority commits nothing and
    still reports success."""
    chain.write("resolve_submission", [submission_id], label)
    stored = json.loads(chain.read("get_submission", [submission_id]))
    say("    stored verdict %s, status %s, evidence %s"
        % (stored["verdict"] or "(none)", stored["status"],
           stored["evidence_status"] or "(none)"))
    return stored


def setup(chain, policy_id, body, challenge_id, lot, origin, days=200):
    policy_id = tagged(policy_id)
    challenge_id = tagged(challenge_id)
    chain.write("register_policy", [policy_id], "register " + policy_id)
    chain.write("publish_policy_version", [policy_id, json.dumps(body)],
                "publish " + policy_id)
    chain.write("open_verification_challenge",
                [challenge_id, policy_id, 1, lot, origin, days],
                "open " + challenge_id)
    return policy_id, challenge_id


# -- the scenarios -----------------------------------------------------------

def scenario_a(chain, pub):
    say("\nA  a cold chain whose log holds the range across the window")
    setup(chain, "pol-cold-ok", COLD_CHAIN, "chal-cold-ok", "LOT-4471-B",
          "Ashanti region, Ghana")
    records = [record_entry("R1", "CONDITION_LOG", CARRIER, LOG_COMPLIANT,
                            pub),
               record_entry("R2", "BILL_OF_LADING", CARRIER, BILL_OF_LADING,
                            pub)]
    chain.write("submit_records",
                [tagged("sub-cold-ok"), tagged("chal-cold-ok"), "PO-2026-0412",
                 "the reefer held its range across the carriage window",
                 json.dumps(records)], "submit sub-cold-ok")
    stored = resolve_and_read(chain, tagged("sub-cold-ok"), "resolve sub-cold-ok")

    # Facts about the records, decided by code, which must hold whatever the
    # panel made of the log.
    expect("both records readable",
           [row["status"] for row in stored["records"]],
           ["RECORD_READABLE", "RECORD_READABLE"])
    expect("both records authenticated",
           [row["authenticity"] for row in stored["records"]],
           ["AUTHENTICATED_ORIGIN", "AUTHENTICATED_ORIGIN"])
    expect("no reader-directed text", stored["directed_text_hits"], 0)
    # A log this clean should hold its range; a reading that cannot settle it
    # is the other honest outcome. Nothing else is.
    expect_in("condition state", stored["condition_state"],
              ("HELD", "UNREADABLE"))
    expect_in("verdict", stored["verdict"],
              ("CLAIM_SUPPORTED", "CLAIM_NOT_ESTABLISHED"))
    if stored["verdict"] == "CLAIM_SUPPORTED":
        expect("condition held", stored["condition_state"], "HELD")
        expect("excursion", stored["condition_worst_excursion_minutes"], 0)
        expect("identifiers reconciled", stored["identity_state"],
               "CONSISTENT")
        expect("gate true", chain.read("is_claim_supported",
                                       [tagged("sub-cold-ok"), AS_OF]), True)
    return stored


def scenario_b(chain, pub):
    say("\nB  a cold chain with an eighteen-hour excursion")
    setup(chain, "pol-cold-exc", COLD_CHAIN, "chal-cold-exc", "LOT-4471-B",
          "Ashanti region, Ghana")
    records = [record_entry("R1", "CONDITION_LOG", CARRIER, LOG_EXCURSION,
                            pub),
               record_entry("R2", "BILL_OF_LADING", CARRIER, BILL_OF_LADING,
                            pub)]
    chain.write("submit_records",
                [tagged("sub-cold-exc"), tagged("chal-cold-exc"), "PO-2026-0418",
                 "the reefer log is submitted for the carriage window",
                 json.dumps(records)], "submit sub-cold-exc")
    stored = resolve_and_read(chain, tagged("sub-cold-exc"), "resolve sub-cold-exc")
    # The allowance is thirty minutes and the log shows hours out of range.
    # Code decides that, so the claim cannot be supported.
    expect("claim not supported",
           stored["verdict"] != "CLAIM_SUPPORTED", True)
    expect("gate false", chain.read("is_claim_supported",
                                    [tagged("sub-cold-exc"), AS_OF]), False)
    if stored["condition_state"] == "BREACHED":
        say("    worst excursion %d minutes"
            % stored["condition_worst_excursion_minutes"])
    return stored


def scenario_c(chain, pub):
    say("\nC  a custody chain whose checkpoints are out of order")
    setup(chain, "pol-cust-ooo", CUSTODY_CHAIN, "chal-cust-ooo",
          "LOT-4471-B", "Ashanti region, Ghana")
    records = [record_entry("R1", "CUSTODY_SCAN", PORT, SCAN_ORIGIN, pub),
               record_entry("R2", "CUSTODY_SCAN", CARRIER, SCAN_TRANSIT,
                            pub),
               record_entry("R3", "CUSTODY_SCAN", CARRIER,
                            SCAN_OUT_OF_ORDER, pub)]
    chain.write("submit_records",
                [tagged("sub-cust-ooo"), tagged("chal-cust-ooo"), "PO-2026-0421",
                 "every declared checkpoint is evidenced for this lot",
                 json.dumps(records)], "submit sub-cust-ooo")
    stored = resolve_and_read(chain, tagged("sub-cust-ooo"), "resolve sub-cust-ooo")
    expect("claim not supported",
           stored["verdict"] != "CLAIM_SUPPORTED", True)
    say("    custody state %s" % stored["custody_state"])
    chain_view = json.loads(chain.read("get_custody_chain",
                                       [tagged("sub-cust-ooo")]))
    for row in chain_view["checkpoints"]:
        say("      %s order %d  %-14s %s"
            % (row["ref"], row["order"], row["finding"],
               row["stated_time"] or "-"))
    return stored


def scenario_d(chain, pub):
    say("\nD  records that disagree about which lot they describe")
    setup(chain, "pol-cust-conf", CUSTODY_CHAIN, "chal-cust-conf",
          "LOT-4471-B", "Ashanti region, Ghana")
    records = [record_entry("R1", "CUSTODY_SCAN", PORT, SCAN_ORIGIN, pub),
               record_entry("R2", "CUSTODY_SCAN", CARRIER, SCAN_TRANSIT,
                            pub),
               record_entry("R3", "CUSTODY_SCAN", CARRIER,
                            SCAN_DESTINATION, pub),
               record_entry("R4", "WAREHOUSE_RECEIPT", CUSTOMS,
                            WAREHOUSE_CONFLICTING, pub)]
    chain.write("submit_records",
                [tagged("sub-cust-conf"), tagged("chal-cust-conf"), "PO-2026-0425",
                 "the custody record for this lot, with the warehouse "
                 "receipt",
                 json.dumps(records)], "submit sub-cust-conf")
    stored = resolve_and_read(chain, tagged("sub-cust-conf"),
                              "resolve sub-cust-conf")
    expect("claim not supported",
           stored["verdict"] != "CLAIM_SUPPORTED", True)
    say("    identity state %s" % stored["identity_state"])
    findings = json.loads(chain.read("get_findings", [tagged("sub-cust-conf")]))
    for row in findings["identity"]:
        say("      %s %-15s %-12s from %d record(s)"
            % (row["ref"], row["state"], row["value"] or "-",
               row["records"]))
    return stored


def scenario_e(chain, pub):
    say("\nE  a record that instructs whoever reads it")
    setup(chain, "pol-cust-dir", CUSTODY_CHAIN, "chal-cust-dir",
          "LOT-4471-B", "Ashanti region, Ghana")
    records = [record_entry("R1", "CUSTODY_SCAN", PORT, SCAN_DIRECTED, pub),
               record_entry("R2", "CUSTODY_SCAN", CARRIER, SCAN_TRANSIT,
                            pub),
               record_entry("R3", "CUSTODY_SCAN", CARRIER,
                            SCAN_DESTINATION, pub)]
    chain.write("submit_records",
                [tagged("sub-cust-dir"), tagged("chal-cust-dir"), "PO-2026-0428",
                 "every declared checkpoint is evidenced for this lot",
                 json.dumps(records)], "submit sub-cust-dir")
    stored = resolve_and_read(chain, tagged("sub-cust-dir"), "resolve sub-cust-dir")
    # Code counted the markers, so this holds however the round read the
    # checkpoints.
    expect("markers counted in code",
           stored["directed_text_hits"] >= 4, True)
    expect("claim not supported",
           stored["verdict"] != "CLAIM_SUPPORTED", True)
    expect("gate false", chain.read("is_claim_supported",
                                    [tagged("sub-cust-dir"), AS_OF]), False)
    say("    directed text hits %d, custody state %s"
        % (stored["directed_text_hits"], stored["custody_state"]))
    return stored


def scenario_f(chain, pub):
    say("\nF  a certificate not served from the host its issuer publishes "
        "from")
    setup(chain, "pol-origin", ORIGIN_CLAIM, "chal-origin", "LOT-4471-B",
          "Ashanti region, Ghana")
    records = [record_entry("R1", "ORIGIN_CERTIFICATE", UNION,
                            ORIGIN_CERTIFICATE, pub),
               record_entry("R2", "CUSTOMS_ENTRY", CUSTOMS, CUSTOMS_ENTRY,
                            pub)]
    chain.write("submit_records",
                [tagged("sub-origin"), tagged("chal-origin"), "PO-2026-0430",
                 "the lot came from the region the certificate names",
                 json.dumps(records)], "submit sub-origin")
    stored = resolve_and_read(chain, tagged("sub-origin"), "resolve sub-origin")
    # Entirely deterministic: the requirement says the union publishes from
    # its own host, and these bytes came from the raw host.
    expect("source not authenticated", stored["authenticity_state"],
           "SOURCE_UNVERIFIED")
    expect("authenticity criterion false",
           stored["criteria"]["source_authenticity_verified"], False)
    expect("claim not supported",
           stored["verdict"] != "CLAIM_SUPPORTED", True)
    expect("gate false", chain.read("is_claim_supported",
                                    [tagged("sub-origin"), AS_OF]), False)
    return stored


def scenario_g(chain, pub):
    say("\nG  a required record that cannot be fetched, then a retry")
    setup(chain, "pol-cold-gone", COLD_CHAIN, "chal-cold-gone",
          "LOT-4471-B", "Ashanti region, Ghana")
    # A location that is admissible and will not resolve to a record.
    missing = RAW % ("0" * 40, LOG_COMPLIANT)
    records = [record_entry("R1", "CONDITION_LOG", CARRIER, LOG_COMPLIANT,
                            pub, location=missing),
               record_entry("R2", "BILL_OF_LADING", CARRIER, BILL_OF_LADING,
                            pub)]
    chain.write("submit_records",
                [tagged("sub-cold-gone"), tagged("chal-cold-gone"), "PO-2026-0502",
                 "the reefer log is submitted for the carriage window",
                 json.dumps(records)], "submit sub-cold-gone")
    stored = resolve_and_read(chain, tagged("sub-cold-gone"),
                              "resolve sub-cold-gone")
    # Deterministic: an unfetchable required record is never a finding.
    expect("verdict", stored["verdict"], "EVIDENCE_UNAVAILABLE")
    expect("retryable", stored["status"], "RETRYABLE")
    expect("panel skipped", stored["panel_state"], "SKIPPED")
    expect("not consumable", chain.read("is_consumable",
                                        [tagged("sub-cold-gone"), AS_OF]), False)
    chain.write("retry_submission", [tagged("sub-cold-gone")], "retry sub-cold-gone")
    after = json.loads(chain.read("get_submission", [tagged("sub-cold-gone")]))
    expect("pending again after retry", after["status"], "PENDING")

    # What is recorded is the state the chain is left in, not the state
    # mid-run: this is the only scenario that changes its submission after
    # reading it, and `scripts/verify.py` re-reads the contract later. The
    # first round's outcome is not lost - it is what `first_round` holds,
    # and the resolve transaction evidences it independently.
    stored["first_round"] = {"verdict": stored["verdict"],
                             "status": stored["status"],
                             "panel_state": stored["panel_state"]}
    stored["status"] = after["status"]
    stored["rounds_used"] = after["rounds_used"]
    return stored


SCENARIOS = {"a": scenario_a, "b": scenario_b, "c": scenario_c,
             "d": scenario_d, "e": scenario_e, "f": scenario_f,
             "g": scenario_g}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True,
                        help="a pushed commit the fixtures are read from")
    parser.add_argument("--address", default="",
                        help="reuse an existing deployment")
    parser.add_argument("--scenarios", default="a,b,c,d,e,f,g")
    args = parser.parse_args()

    PROOFS.mkdir(parents=True, exist_ok=True)
    TAG[0] = "-" + args.commit[:6]
    say("TrustRoute live run")
    say("commit %s" % args.commit)
    say("id tag %s" % TAG[0])
    say("rpc %s" % RPC)

    say("\nchecking the published bytes")
    pub = {}
    for name in RECORDS:
        url, digest, size = published(args.commit, name)
        pub[name] = (url, digest, size)
        say("  %-44s %6d bytes  %s" % (name, size, digest[:16] + "..."))

    account, generated = signer()
    if generated:
        fund(account.address)
    chain = Chain(account)

    if args.address:
        chain.bind(args.address)
        deploy_tx = ""
    else:
        _address, deploy_tx = chain.deploy()

    results = {}
    for key in args.scenarios.split(","):
        key = key.strip().lower()
        if key not in SCENARIOS:
            raise SystemExit("unknown scenario: " + key)
        results[key] = SCENARIOS[key](chain, pub)

    say("\nfinality")
    finals = {}
    for label, tx_hash in chain.transactions:
        status, result, votes = chain.finality(tx_hash)
        finals[tx_hash] = {"label": label, "lifecycle": status,
                           "execution": result, "consensus": votes}
        say("  %-28s %-10s %-8s %s" % (label, status, result, votes))

    stats = json.loads(chain.read("get_stats"))
    say("\nstats %s" % json.dumps(stats))

    ledger = {
        "commit": args.commit,
        "chain_id": 61999,
        "rpc": RPC,
        "contract": chain.address,
        "explorer": EXPLORER + "/address/" + chain.address,
        "deploy_tx": deploy_tx,
        "deployer": account.address,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        "records": {name: {"url": pub[name][0], "sha256": pub[name][1],
                           "bytes": pub[name][2]} for name in pub},
        "transactions": [{"label": label, "tx": tx_hash}
                         for label, tx_hash in chain.transactions],
        "finality": finals,
        "scenarios": {key: results[key] for key in results},
        "stats": stats,
        "as_of": AS_OF,
    }
    path = PROOFS / "live.json"
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    if existing.get("contract") == chain.address:
        merged = dict(existing)
        merged.update(ledger)
        merged["transactions"] = (existing.get("transactions", [])
                                  + ledger["transactions"])
        merged["finality"] = dict(existing.get("finality", {}),
                                  **ledger["finality"])
        merged["scenarios"] = dict(existing.get("scenarios", {}),
                                   **ledger["scenarios"])
        ledger = merged
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="")
    (PROOFS / "live-run.log").write_text("\n".join(log_lines) + "\n",
                                         encoding="utf-8", newline="")
    say("\nwrote %s and %s" % (path, PROOFS / "live-run.log"))

    if FAILURES:
        say("\n%d assertion(s) failed:" % len(FAILURES))
        for label in FAILURES:
            say("  " + label)
        return 1
    say("\nevery assertion held")
    return 0


sys.exit(main())
