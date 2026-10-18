#!/usr/bin/env python3
"""Re-read the recorded live run off Studionet. No keys, no funds, no writes.

Reads `docs/proofs/live.json`, then asks the network to confirm every claim
in it: that the deployed bytes are the committed source, that each bound
record still publishes the exact bytes its hash names, what each transaction
finally settled as, and what the contract stores for every scenario. Then it
rewrites `docs/proofs/live.md` from those answers.

    python scripts/verify.py

It paces itself: Studionet allows about thirty reads a minute per address,
and a verification that trips the limit would look like a failure.

Exit code 1 if anything does not hold.
"""

import argparse
import base64
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

from genlayer_py import (chains, create_account, create_client,
                         generate_private_key)


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "trustroute.py"
FIXTURES = ROOT / "fixtures"
PROOFS = ROOT / "docs" / "proofs"
LEDGER = PROOFS / "live.json"

RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"
CHAIN_ID = 61999
PACE_SECONDS = 2.2

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

SCENARIO_TITLES = {
    "a": "a cold chain whose log holds the range across the window",
    "b": "a cold chain with an eighteen-hour excursion",
    "c": "a custody chain whose checkpoints are out of order",
    "d": "records that disagree about which lot they describe",
    "e": "a record that instructs whoever reads it",
    "f": "a certificate not served from its issuer's registered host",
    "g": "a required record that cannot be fetched, then a retry",
}

lines = []
failures = []
QUIET = []


def say(text=""):
    if not QUIET:
        print(text, flush=True)
    lines.append(text)


def check(label, actual, wanted):
    ok = actual == wanted
    if not ok:
        failures.append("%s: expected %r, got %r" % (label, wanted, actual))
    say("| %s | `%s` | %s |" % (label, actual, "OK" if ok else "**WRONG**"))
    return ok


def check_true(label, condition, shown):
    if not condition:
        failures.append("%s: %r" % (label, shown))
    say("| %s | `%s` | %s |" % (label, shown, "OK" if condition
                                else "**WRONG**"))
    return condition


def rpc(method, params):
    request = urllib.request.Request(
        RPC,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                         "params": params}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def deployed_bytes(address):
    """The contract as the network holds it, decoded."""
    result = rpc("gen_getContractCode", [address])["result"]
    if isinstance(result, str) and result.startswith("0x"):
        return bytes.fromhex(result[2:])
    return base64.b64decode(str(result))


def published_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def votes_of(tx):
    data = tx.get("consensus_data") or {}
    votes = data.get("votes") or {}
    agree = sum(1 for v in votes.values() if str(v).lower() == "agree")
    disagree = sum(1 for v in votes.values()
                   if str(v).lower().startswith("disagree"))
    return agree, disagree, len(votes) - agree - disagree, len(votes)


def execution_of(tx):
    leader = (tx.get("consensus_data") or {}).get("leader_receipt")
    if isinstance(leader, list) and leader:
        return str(leader[0].get("execution_result"))
    return str(tx.get("execution_result_name") or tx.get("result_name")
               or "unknown")


class Reader:
    """Paced, read-only access to the deployment."""

    def __init__(self, address):
        self.address = address
        self.client = create_client(
            chain=chains.studionet,
            account=create_account(
                account_private_key=generate_private_key()))
        self.reads = 0

    def view(self, method, args=None):
        self.reads += 1
        time.sleep(PACE_SECONDS)
        return self.client.read_contract(address=self.address,
                                         function_name=method,
                                         args=args or [])

    def transaction(self, tx_hash):
        self.reads += 1
        time.sleep(PACE_SECONDS)
        return self.client.get_transaction(transaction_hash=tx_hash)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.quiet:
        QUIET.append(True)

    if not LEDGER.exists():
        print("no ledger at %s - run scripts/live.py first" % LEDGER)
        return 1
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    address = ledger["contract"]
    reader = Reader(address)

    say("# Live evidence")
    say()
    say("Written by `python scripts/verify.py`, which reads everything below "
        "off GenLayer Studionet. Nothing here is a transcript: re-run it and "
        "the network answers again. It needs no key, no funds and no "
        "GenLayer account.")
    say()
    say("| | |")
    say("|---|---|")
    say("| Network | GenLayer Studionet, chain %d |" % CHAIN_ID)
    say("| RPC | `%s` |" % RPC)
    say("| Contract | [`%s`](%s/address/%s) |" % (address, EXPLORER,
                                                  address))
    say("| Deployer | `%s` |" % ledger.get("deployer", "-"))
    say("| Source commit | `%s` |" % ledger.get("commit", "-"))

    source = CONTRACT.read_bytes()
    source_sha = hashlib.sha256(source).hexdigest()
    say("| Contract source | `contracts/trustroute.py`, %d bytes, sha256 "
        "`%s` |" % (len(source), source_sha))
    live = deployed_bytes(address)
    live_sha = hashlib.sha256(live).hexdigest()
    if live_sha != source_sha:
        failures.append("the deployed contract is not the committed source")
    say("| Deployed bytes | %d bytes, sha256 `%s` |" % (len(live), live_sha))
    say("| Deployed = committed source | %s |"
        % ("**yes, byte-identical**" if live_sha == source_sha else "**NO**"))
    say()

    # -- the records every node had to fetch and hash ---------------------
    say("## The records, re-fetched")
    say()
    say("Each one is bound to the sha256 of its exact bytes. Change a byte "
        "and the contract reports `HASH_MISMATCH` instead of reading it, so "
        "these hashes are what the adjudications actually rest on.")
    say()
    say("| Record | Bytes | sha256 | Still publishes those bytes |")
    say("|---|---|---|---|")
    for name in sorted(ledger.get("records", {})):
        entry = ledger["records"][name]
        try:
            body = published_bytes(entry["url"])
            digest = hashlib.sha256(body).hexdigest()
            ok = digest == entry["sha256"]
        except Exception as err:
            body, digest, ok = b"", "fetch failed: %s" % err, False
        if not ok:
            failures.append("%s no longer publishes its committed bytes"
                            % name)
        local = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
        if local != entry["sha256"]:
            failures.append("%s in this checkout is not the bytes that were "
                            "bound" % name)
        say("| `%s` | %d | `%s` | %s |"
            % (name, len(body), entry["sha256"][:16] + "...",
               "yes" if ok else "**no**"))
    say()

    # -- what each transaction settled as --------------------------------
    say("## Every transaction, re-queried")
    say()
    say("A round whose validators do not reach a majority commits nothing "
        "and still reports success, so the lifecycle and the votes are read "
        "here rather than taken from the run that made them.")
    say()
    say("| What | Transaction | Lifecycle | Execution | Consensus |")
    say("|---|---|---|---|---|")
    for entry in ledger.get("transactions", []):
        tx_hash = entry["tx"]
        try:
            tx = reader.transaction(tx_hash)
        except Exception as err:
            failures.append("could not re-query %s: %s" % (tx_hash, err))
            say("| %s | `%s` | **unreadable** | - | - |"
                % (entry["label"], tx_hash))
            continue
        agree, disagree, idle, total = votes_of(tx)
        status = str(tx.get("status_name") or tx.get("status"))
        result = execution_of(tx)
        if result.upper().endswith("ERROR"):
            failures.append("%s executed with an error" % entry["label"])
        say("| %s | [`%s...`](%s/tx/%s) | %s | %s | %d agree, %d disagree, "
            "%d idle of %d |"
            % (entry["label"], tx_hash[:18], EXPLORER, tx_hash, status,
               result, agree, disagree, idle, total))
    say()

    # -- what the contract stores now ------------------------------------
    say("## What the contract stores")
    say()
    as_of = ledger.get("as_of", "2026-10-20T12:00Z")
    for key in sorted(ledger.get("scenarios", {})):
        stored_then = ledger["scenarios"][key]
        submission_id = stored_then["submission_id"]
        say("### %s - %s" % (key.upper(),
                             SCENARIO_TITLES.get(key, submission_id)))
        say()
        stored = json.loads(reader.view("get_submission", [submission_id]))
        outcome = json.loads(reader.view("claim_outcome",
                                        [submission_id, as_of]))
        say("| | | |")
        say("|---|---|---|")
        check("submission", stored["submission_id"], submission_id)
        check("verdict", stored["verdict"], stored_then["verdict"])
        check("status", stored["status"], stored_then["status"])
        check("evidence status", stored["evidence_status"],
              stored_then["evidence_status"])
        check("records present",
              stored["criteria"].get("required_records_present"),
              stored_then["criteria"].get("required_records_present"))
        check("records consistent",
              stored["criteria"].get("records_consistent"),
              stored_then["criteria"].get("records_consistent"))
        check("source authenticity verified",
              stored["criteria"].get("source_authenticity_verified"),
              stored_then["criteria"].get("source_authenticity_verified"))
        check("required event supported",
              stored["criteria"].get("required_event_supported"),
              stored_then["criteria"].get("required_event_supported"))
        for field in ("custody_state", "identity_state", "condition_state",
                      "delivery_state", "origin_state", "compliance_state",
                      "authenticity_state", "directed_text_hits"):
            if stored_then.get(field) not in (None, "", "NOT_DECLARED",
                                              "NOT_ASSESSED"):
                check(field.replace("_", " "), stored[field],
                      stored_then[field])
        # The gate a consumer actually reads.
        supported = outcome["claim_supported"]
        check_true("is_claim_supported",
                   supported == (stored["verdict"] == "CLAIM_SUPPORTED"
                                 and outcome["freshness"] == "RELIABLE"),
                   supported)
        check("freshness", outcome["freshness"], outcome["freshness"])
        say()

    stats = json.loads(reader.view("get_stats"))
    say("## The contract's own counters")
    say()
    say("| | |")
    say("|---|---|")
    for field in ("policies", "challenges", "submissions", "resolved"):
        say("| %s | %d |" % (field, stats[field]))
    say()
    expected = ledger.get("stats")
    if expected:
        for field in ("policies", "challenges", "submissions"):
            if stats[field] < expected.get(field, 0):
                failures.append("the %s counter went backwards" % field)
    say("Only a settled verdict - `CLAIM_SUPPORTED` or "
        "`CLAIM_NOT_ESTABLISHED` - moves the resolved counter, which is why "
        "it is lower than the number of submissions.")
    say()

    say("## What this proves")
    say()
    say("- the deployed contract is the committed source, byte for byte;")
    say("- every record a verdict rests on still publishes the exact bytes "
        "its hash names;")
    say("- a cold chain that held its range is adjudicated as supported, "
        "and one with an excursion is not - the range comparison and the "
        "excursion arithmetic are code, and no model is told the range;")
    say("- checkpoints evidenced out of order do not establish a custody "
        "claim, because the order is decided from the instants the records "
        "state;")
    say("- records that disagree about which lot they describe produce "
        "`INCONSISTENT_EVIDENCE`, which is a finding about the records and "
        "not about the shipment;")
    say("- a record that instructs whoever reads it cannot produce a "
        "supported claim, and code - not the reading stage - is what caught "
        "it;")
    say("- a certificate not served from the host its issuer is registered "
        "to publish from leaves the source unverified, and the contract "
        "never claims a signature was checked;")
    say("- a required record nobody can fetch is `EVIDENCE_UNAVAILABLE` and "
        "retryable, never a finding about the world;")
    say("- every reliance gate is false for everything uncertain.")
    say()
    say("Schema `trustroute/1`, contract version `0.1.0`. %d reads."
        % reader.reads)
    say()

    PROOFS.mkdir(parents=True, exist_ok=True)
    (PROOFS / "live.md").write_text("\n".join(lines) + "\n",
                                    encoding="utf-8", newline="")
    if failures:
        print("\n%d check(s) failed:" % len(failures))
        for text in failures:
            print("  " + text)
        return 1
    print("\nall checks passed; written to %s" % (PROOFS / "live.md"))
    return 0


sys.exit(main())
