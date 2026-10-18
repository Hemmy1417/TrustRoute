"""Shared harness for the Direct Mode suite.

Only the nondeterministic edges are mocked: each record fetch and the single
reading call. Everything between them - admission, deadlines, required kinds,
hashing, issuer-host authenticity, grounding, timestamp normalisation,
checkpoint ordering, the condition arithmetic, identity reconciliation,
precedence, storage and the counters - is the contract's own code.
"""

import hashlib
import json
import os
import pathlib
import sys

import pytest

from eth_utils import to_checksum_address

from gltest.direct import VMContext, deploy_contract, create_test_addresses


def hexaddr(account) -> str:
    """The checksummed spelling a contract stores for a test account."""
    return to_checksum_address(bytes(account))


def _tolerate_windows_tempfile_unlink():
    """Work around a Windows-only failure in the Direct Mode loader.

    `gltest` 0.29.2 writes the transaction message to a temp file, binds that
    file to fd 0 with `dup2`, closes its own descriptor and then unlinks the
    path. POSIX allows unlinking a file another descriptor still references;
    Windows does not, so contract loading dies with

        PermissionError: [WinError 32] The process cannot access the file
        because it is being used by another process

    before any contract code runs. This wraps the loader's own helper so one
    failed cleanup is tolerated - the file is released when the process exits
    - and restores `os.unlink` immediately afterwards.

    It is a host workaround, not a contract fix. The contract is not involved
    and not modified, nothing outside the loader's own call is affected, and
    on anything other than Windows it does nothing at all. docs/TESTING.md
    says so plainly rather than claiming the suite runs natively everywhere.
    """
    if sys.platform != "win32":
        return
    from gltest.direct import loader

    original = getattr(loader, "_inject_message_to_fd0", None)
    if original is None or getattr(original, "_unlink_tolerated", False):
        return

    def wrapped(vm):
        real_unlink = os.unlink

        def tolerant(path, *args, **kwargs):
            try:
                real_unlink(path, *args, **kwargs)
            except OSError:
                pass

        os.unlink = tolerant
        try:
            return original(vm)
        finally:
            os.unlink = real_unlink

    wrapped._unlink_tolerated = True
    loader._inject_message_to_fd0 = wrapped


_tolerate_windows_tempfile_unlink()


ROOT = pathlib.Path(__file__).resolve().parents[2]

# The suite runs against the committed contract unless a mutation sweep
# points it at a patched copy (scripts/mutate.py).
CONTRACT = pathlib.Path(
    os.environ.get("TRUSTROUTE_CONTRACT",
                   str(ROOT / "contracts" / "trustroute.py")))
FIXTURES = ROOT / "fixtures"

# Any https host works against a mocked fetch; this is the host the live
# suite uses, so both suites meet the same admission and authenticity rules.
RAW_HOST = "raw.githubusercontent.com"
BASE = "https://" + RAW_HOST + "/Hemmy1417/TrustRoute/main/fixtures/"

SCAN_ORIGIN = "custody-scan-origin.txt"
SCAN_TRANSIT = "custody-scan-transit.txt"
SCAN_DESTINATION = "custody-scan-destination.txt"
SCAN_OUT_OF_ORDER = "custody-scan-destination-out-of-order.txt"
SCAN_DIRECTED = "custody-scan-directed.txt"
LOG_COMPLIANT = "condition-log-compliant.txt"
LOG_EXCURSION = "condition-log-excursion.txt"
DELIVERY_NOTE = "delivery-confirmation.txt"
DELIVERY_LATE = "delivery-confirmation-late.txt"
CUSTOMS_ENTRY = "customs-entry.txt"
BILL_OF_LADING = "bill-of-lading.txt"
INSPECTION = "inspection-certificate.txt"
ORIGIN_CERTIFICATE = "origin-certificate.txt"
WAREHOUSE_RECEIPT = "warehouse-receipt.txt"
WAREHOUSE_CONFLICTING = "warehouse-receipt-conflicting-lot.txt"

# A transaction clock after the shipment and well before any deadline.
NOW = "2026-03-20T09:30:00.000+00:00"
NOW_STAMP = "2026-03-20T09:30Z"
AS_OF = "2026-03-21T09:30Z"

PORT = "Tema Port Authority (synthetic)"
CARRIER = "Meridian Cold Logistics (synthetic)"
CUSTOMS = "Accra Customs Service (synthetic)"
UNION = "Ashanti Growers Union (synthetic)"

# The union publishes from a host of its own. Every union record in these
# tests is served from the raw host instead, which is exactly how an
# unverifiable source is demonstrated: the bytes did not come from where the
# requirement says that issuer publishes.
UNION_HOST = "records.ashanti-growers.org"

ISSUERS = [
    {"issuer": PORT, "host": RAW_HOST},
    {"issuer": CARRIER, "host": RAW_HOST},
    {"issuer": CUSTOMS, "host": RAW_HOST},
    {"issuer": UNION, "host": UNION_HOST},
]


def record_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def record_text(name: str) -> str:
    return record_bytes(name).decode("utf-8")


def record_sha(name: str) -> str:
    return hashlib.sha256(record_bytes(name)).hexdigest()


def url_for(name: str) -> str:
    return BASE + name


def quote_from(name: str, needle: str) -> str:
    """A verbatim line from a record, for grounding a finding. Returns the
    whole line containing `needle`, which is what a reviewer would quote."""
    for line in record_text(name).splitlines():
        if needle in line:
            quote = line.strip()
            assert len(quote) >= 12, quote
            return quote[:240]
    raise AssertionError("no line in " + name + " contains " + needle)


# == the requirements the tests use ========================================


def definition(claim_type, kinds, identity=None, custody=None, origin=None,
               condition=None, delivery=None, compliance=None,
               requirement="synthetic verification requirement",
               issuers=None):
    """Build a policy definition with only the parts a claim type needs."""
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
        "issuers": issuers if issuers is not None else ISSUERS,
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
    "CONDITION",
    ["CONDITION_LOG", "BILL_OF_LADING"],
    identity=[LOT_KEY, CONTAINER_KEY],
    condition={
        "metric": "return air temperature",
        "unit": "degrees Celsius",
        "series_format": "TIMESTAMP_VALUE_LINES",
        "min_tenths": 20,
        "max_tenths": 80,
        "window_start": "2026-03-14T06:00Z",
        "window_end": "2026-03-16T18:00Z",
        "max_excursion_minutes": 30,
    },
    requirement="the reefer held 2.0 to 8.0 C across the carriage window",
)

CUSTODY_CHAIN = definition(
    "CUSTODY",
    ["CUSTODY_SCAN"],
    identity=[LOT_KEY],
    custody=CUSTODY_EVENTS,
    requirement="the lot passed every declared checkpoint in order",
)

ORIGIN_CLAIM = definition(
    "ORIGIN",
    ["ORIGIN_CERTIFICATE", "CUSTOMS_ENTRY"],
    identity=[LOT_KEY],
    origin={"requirement": "a record identifies the lot's growing region"},
    requirement="the lot came from the origin claimed for it",
)

DELIVERY_CLAIM = definition(
    "DELIVERY",
    ["DELIVERY_CONFIRMATION", "BILL_OF_LADING"],
    identity=[LOT_KEY],
    delivery={"not_before": "2026-03-15T00:00Z",
              "not_after": "2026-03-18T00:00Z"},
    requirement="the consignment was delivered inside the agreed window",
)

COMPLIANCE_CLAIM = definition(
    "COMPLIANCE",
    ["INSPECTION_CERTIFICATE", "CUSTOMS_ENTRY"],
    identity=[LOT_KEY],
    compliance=[{"ref": "K1",
                 "requirement": "the consignment was inspected before "
                                "stuffing and found fit for export",
                 "record_kind": "INSPECTION_CERTIFICATE"}],
    requirement="the consignment satisfies the declared inspection rule",
)


def synthetic_log(rows):
    """A condition log carrying exactly the given rows.

    The contract reads a log by taking the first token of a line as a
    timestamp and the last as the measurement, so a test that needs
    particular readings writes them here rather than mocking an answer.
    The lot and container lines are kept because the identity questions are
    grounded in them.
    """
    lines = ["REEFER TEMPERATURE LOG",
             "Issued by: " + CARRIER,
             "Container: MSKU-774120-3",
             "Lot number: LOT-4471/B",
             "Unit: degrees Celsius",
             "",
             "timestamp            reading"]
    for stamp, value in rows:
        lines.append(str(stamp) + "    " + str(value))
    return NL_JOIN.join(lines) + NL_JOIN


NL_JOIN = chr(10)


def record(record_id, name, kind, issuer, location=None, sha=None):
    return {"record_id": record_id, "kind": kind,
            "location": location if location is not None else url_for(name),
            "sha256": sha if sha is not None else record_sha(name),
            "declared_issuer": issuer}


COLD_CHAIN_RECORDS = [
    record("R1", LOG_COMPLIANT, "CONDITION_LOG", CARRIER),
    record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER),
]

CUSTODY_RECORDS = [
    record("R1", SCAN_ORIGIN, "CUSTODY_SCAN", PORT),
    record("R2", SCAN_TRANSIT, "CUSTODY_SCAN", CARRIER),
    record("R3", SCAN_DESTINATION, "CUSTODY_SCAN", CARRIER),
]


class Harness:
    """One deployed contract plus the mocking a round needs."""

    def __init__(self, vm, contract, accounts):
        self.vm = vm
        self.contract = contract
        self.buyer = accounts[0]
        self.submitter = accounts[1]
        self.stranger = accounts[2]
        self.vm.warp(NOW)

    # -- mocking ----------------------------------------------------------

    def _pattern(self, url: str) -> str:
        return url

    def mock_record(self, name, status=200, body=None, url=None):
        self.vm.mock_web(
            url_pattern=self._pattern(url or url_for(name)),
            response={"method": "GET", "status": status,
                      "body": record_text(name) if body is None else body},
        )

    def mock_records(self, *names):
        for name in names:
            self.mock_record(name)

    def mock_panel(self, raw):
        self.vm.mock_llm(prompt_pattern="independent reviewers reading",
                         response=raw)

    # -- building a reading-stage answer ----------------------------------

    def panel(self, checkpoints=None, identity=None, origin=None,
              delivery=None, compliance=None, contradiction=None,
              basis="synthetic test basis"):
        """Build an answer in the one shape the contract accepts.

        `checkpoints`: list of (ref, finding, record_id, quote, stated_time)
        `identity`:    list of (ref, [(record_id, value, quote), ...])
        `compliance`:  list of (ref, finding, record_id, quote)
        """
        answer = {
            "checkpoints": [
                {"ref": row[0], "finding": row[1], "record_id": row[2],
                 "quote": row[3], "stated_time": row[4]}
                for row in (checkpoints or [])],
            "identity": [
                {"ref": row[0],
                 "values": [{"record_id": value[0], "value": value[1],
                             "quote": value[2]} for value in row[1]]}
                for row in (identity or [])],
            "origin": origin or {"finding": "NOT_ASSESSED", "record_id": "",
                                 "quote": ""},
            "delivery": delivery or {"state": "NOT_ASSESSED",
                                     "record_id": "", "stated_time": "",
                                     "quote": ""},
            "compliance": [
                {"ref": row[0], "finding": row[1], "record_id": row[2],
                 "quote": row[3]}
                for row in (compliance or [])],
            "contradiction": contradiction or {"found": False,
                                               "record_ids": [], "quote": ""},
            "basis": basis,
        }
        return json.dumps(answer)

    # -- writes -----------------------------------------------------------

    def register(self, policy_id="pol-1", sender=None):
        self.vm.sender = sender or self.buyer
        return self.contract.register_policy(policy_id)

    def publish(self, policy_id="pol-1", body=None, sender=None):
        self.vm.sender = sender or self.buyer
        return self.contract.publish_policy_version(
            policy_id, json.dumps(body if body is not None else COLD_CHAIN))

    def open_challenge(self, policy_id="pol-1", version=1,
                       challenge_id="chal-1", lot="LOT-4471-B",
                       origin="Ashanti region, Ghana", days=30, sender=None):
        self.vm.sender = sender or self.buyer
        return self.contract.open_verification_challenge(
            challenge_id, policy_id, version, lot, origin, days)

    def submit(self, challenge_id="chal-1", submission_id="sub-1",
               records=None, reference="PO-2026-0412",
               summary="cold chain held across the carriage window",
               sender=None):
        self.vm.sender = sender or self.submitter
        return self.contract.submit_records(
            submission_id, challenge_id, reference, summary,
            json.dumps(records if records is not None
                       else COLD_CHAIN_RECORDS))

    def submit_cold_log(self, body, challenge_id="chal-1",
                        submission_id="sub-1"):
        """Submit a cold-chain claim whose log is exactly `body`.

        The bytes are bound by their own sha256, as any record is, so the
        contract fetches and hash-verifies this log the same way it would a
        published one.
        """
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        records = [record("R1", LOG_COMPLIANT, "CONDITION_LOG", CARRIER,
                          sha=digest),
                   record("R2", BILL_OF_LADING, "BILL_OF_LADING", CARRIER)]
        self.clear()
        self.mock_record(LOG_COMPLIANT, body=body)
        self.mock_record(BILL_OF_LADING)
        return self.submit(challenge_id, submission_id, records)

    def resolve(self, submission_id="sub-1", sender=None):
        self.vm.sender = sender or self.stranger
        return self.contract.resolve_submission(submission_id)

    def set_clock(self, timestamp):
        """Move the transaction clock the contract reads.

        On a real network every transaction carries its own datetime. Direct
        Mode injects one when the contract is loaded and `vm.warp` after that
        does not reach it, so a test that needs a later transaction moves the
        injected value as well. Nothing in the contract is patched.
        """
        self.vm.warp(timestamp)
        module = sys.modules[type(self.contract).__module__]
        module.gl.message_raw["datetime"] = timestamp

    def clear(self):
        self.vm.clear_mocks()


@pytest.fixture
def harness():
    vm = VMContext()
    vm.check_pickling = True
    with vm.activate():
        accounts = create_test_addresses(4)
        vm.sender = accounts[0]
        vm.warp(NOW)
        contract = deploy_contract(CONTRACT, vm)
        yield Harness(vm, contract, accounts)


@pytest.fixture
def cold_chain(harness):
    """A cold-chain requirement published, a challenge open, and both
    records reachable: the state most verification tests start from."""
    policy_id = harness.register()
    harness.publish(policy_id, COLD_CHAIN)
    challenge_id = harness.open_challenge(policy_id)
    harness.mock_records(LOG_COMPLIANT, BILL_OF_LADING)
    return harness, policy_id, challenge_id


@pytest.fixture
def custody(harness):
    """A custody requirement published, a challenge open, and all three
    scans reachable."""
    policy_id = harness.register("pol-c")
    harness.publish("pol-c", CUSTODY_CHAIN)
    challenge_id = harness.open_challenge("pol-c", 1, "chal-c")
    harness.mock_records(SCAN_ORIGIN, SCAN_TRANSIT, SCAN_DESTINATION)
    return harness, "pol-c", "chal-c"
