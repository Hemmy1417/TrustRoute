"""Mutation sweep: would the tests fail if the contract were wrong?

A green suite says the contract passes its tests. It does not say the tests
would notice if a guard were removed. This removes one guard at a time in a
scratch copy of the contract and runs the whole Direct Mode suite against it.
A mutation that still passes is a hole in the tests and is reported as
SURVIVED.

    python -u scripts/mutate.py > sweep.log     # all of them
    python scripts/mutate.py condition          # only labels matching a word

The committed contract is never modified: each mutant is written to a
temporary file and the suite is pointed at it through TRUSTROUTE_CONTRACT.
Send the output straight to a file - piping it through another process
buffers the progress away.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "trustroute.py"


MUTATIONS = [
    # -- grounding a finding in the bytes -----------------------------
    ("grounding: any quote is accepted",
     '''    if type(quote) is not str or not (MIN_QUOTE_LEN <= len(quote)
                                      <= MAX_QUOTE_LEN):
        return False''',
     '''    if type(quote) is not str:
        return False'''),
    ("grounding: a one-word quote counts",
     "    if type(quote) is not str or not (MIN_QUOTE_LEN <= len(quote)",
     "    if type(quote) is not str or not (1 <= len(quote)"),
    ("grounding: the quote need not be in the record",
     "    return _flatten(quote) in _flatten(text)",
     "    return True"),
    ("grounding: an ungrounded checkpoint keeps its force",
     "                finding, stated = CHECK_UNCLEAR, None",
     "                pass"),
    ("grounding: an ungrounded accusation stands",
     "        if not anchored:",
     "        if False:"),
    ("grounding: an ungrounded compliance finding keeps its force",
     '''        if finding in (CRIT_MET, CRIT_NOT_MET) and not _grounded_in(
                row["record_id"], row["quote"], texts):
            finding = CRIT_UNCLEAR''',
     "        pass"),
    ("grounding: an ungrounded origin finding keeps its force",
     '''    if origin["finding"] in (ORIGIN_SUPPORTED, ORIGIN_NOT_SUPPORTED) and \\
            not _grounded_in(origin["record_id"], origin["quote"], texts):
        origin = {"finding": ORIGIN_UNCLEAR, "record_id": "", "quote": ""}''',
     "    pass"),

    # -- types --------------------------------------------------------
    ("types: a bool passes for an integer",
     "    return type(value) is int",
     "    return isinstance(value, int)"),
    ("types: a float reading is accepted",
     '''        if not _is_int(entry["value_tenths"]):
            return None''',
     '''        if not isinstance(entry["value_tenths"], (int, float)):
            return None'''),
    ("types: an unknown enum value is kept",
     "    return candidate if candidate in allowed else None",
     "    return candidate"),
    ("types: a reading outside the sane range is accepted",
     '''        if not (-10_000 <= int(entry["value_tenths"]) <= 10_000):
            return None''',
     "        pass"),

    # -- the custody chain --------------------------------------------
    ("custody: the declared order is not checked",
     '''        if minutes[index] < minutes[index - 1]:
            return CUSTODY_OUT_OF_ORDER''',
     "        pass"),
    ("custody: a missing checkpoint is tolerated",
     "            return CUSTODY_INCOMPLETE",
     "            pass"),
    ("custody: an untimed checkpoint is tolerated",
     '''        if stamp == "" or _normalise_time(stamp) is None:
            return CUSTODY_UNREADABLE''',
     "        pass"),
    ("custody: an unevidenced checkpoint is tolerated",
     '''        if rows[event["ref"]]["finding"] != CHECK_EVIDENCED:
            return CUSTODY_UNREADABLE''',
     "        pass"),

    # -- the condition series -----------------------------------------
    ("condition: the range is not compared",
     "        if value < low or value > high:",
     "        if False:"),
    ("condition: a zero allowance tolerates an excursion",
     "    if any_out and allowed == 0:",
     "    if False:"),
    ("condition: the excursion allowance is not enforced",
     '''    if worst > allowed:
        return (CONDITION_BREACHED, worst, len(inside))''',
     "    pass"),
    ("condition: a log need not span the window",
     "    if points[0][0] > start or points[-1][0] < end:",
     "    if False:"),
    ("condition: a log with no readings is accepted",
     '''    if series["state"] != SERIES_READ or len(series["readings"]) == 0:
        return (CONDITION_UNREADABLE, 0, 0)''',
     "    pass"),
    ("condition: readings are not sorted before the arithmetic",
     "    points = sorted(points)",
     "    points = list(points)"),

    # -- reconciliation across records --------------------------------
    ("identity: one record counts as corroboration",
     "        elif len(distinct) == 1 and len(contributors) >= 2:",
     "        elif len(distinct) == 1 and len(contributors) >= 1:"),
    ("identity: a conflict is not detected",
     "        if len(distinct) > 1:",
     "        if False:"),
    ("identity: identifiers are compared as written",
     '''    out = []
    for ch in value.upper():
        if ch.isalnum():
            out.append(ch)
    return "".join(out)''',
     "    return value"),

    # -- source authenticity ------------------------------------------
    ("authenticity: the host is not compared",
     '        if str(entry["issuer"]) == declared and str(entry["host"]) == host:',
     '        if str(entry["issuer"]) == declared:'),
    ("authenticity: an unverified record is treated as verified",
     '''        if row["authenticity"] != AUTH_VERIFIED:
            return AUTH_UNVERIFIED''',
     "        pass"),
    ("authenticity: an unreadable record is treated as verified",
     '''        if row["status"] != RECORD_READABLE:
            return AUTH_UNVERIFIED''',
     "        pass"),

    # -- the records themselves ---------------------------------------
    ("documents: the committed hash is not checked",
     "    if hashlib.sha256(body).hexdigest() != expected_sha:",
     "    if False:"),
    ("documents: the size cap is removed",
     "    if len(body) > FETCH_BYTES_CAP:",
     "    if False:"),
    ("documents: any location is admitted",
     '''    host = _host_of(url)
    if host == "":
        return False''',
     "    host = _host_of(url)"),
    ("documents: a numeric host is admitted",
     '''    if labels[-1].isdigit():
        return False''',
     "    pass"),

    # -- the gate -----------------------------------------------------
    ("gate: the derived fields are taken on trust",
     '''        if restated[key] != obj[key]:
            return None''',
     "        pass"),
    ("gate: the missing kinds are taken on trust",
     "    if list(missing) != derived_missing:",
     "    if False:"),
    ("gate: grounding against this node's bytes is skipped",
     '''            if _apply_grounding(findings, ctx, texts) != findings:
                return None''',
     "            pass"),
    ("gate: an unassessed round may carry findings",
     '''        if findings != _unassessed(ctx):
            return None''',
     "        pass"),
    ("gate: a skipped round with nothing missing is accepted",
     '''        if len(derived_missing) == 0 and obj["panel_state"] == PANEL_SKIPPED:
            return None''',
     "        pass"),
    ("gate: an assessed round with a missing record is accepted",
     '''        if len(derived_missing) > 0:
            return None''',
     "        pass"),
    ("gate: an unnormalised payload is accepted",
     '''        if not _findings_normalised(findings):
            return None''',
     "        pass"),
    ("gate: an unreadable row may be authenticated",
     '''        if row["status"] == RECORD_UNAVAILABLE and \\
                row["authenticity"] != AUTH_UNVERIFIED:
            return None''',
     "        pass"),
    ("gate: a criterion need not be a boolean",
     '''        if not _is_bool(obj["criteria"][field]):
            return None''',
     "        pass"),
    ("gate: the payload need not be bound to this submission",
     '''    for field in ("submission_id", "challenge_id", "policy_id",
                  "shipment_or_lot_id"):
        if obj[field] != ctx[field]:
            return None''',
     "    pass"),
    ("gate: the findings need not be the declared shape",
     "        if _read_answer(findings, ctx) is None:\n            return None",
     "        pass"),

    # -- verdict precedence -------------------------------------------
    ("verdict: unreadable records are a reading",
     '''    if not criteria["required_records_present"]:
        return VERDICT_UNAVAILABLE''',
     "    pass"),
    ("verdict: an unusable reading is a reading",
     '''    if payload["panel_state"] != PANEL_ASSESSED:
        return VERDICT_UNAVAILABLE''',
     "    pass"),
    ("verdict: a contradiction is outranked",
     '''    if payload["findings"]["contradiction"]["found"]:
        return INCONSISTENT_EVIDENCE''',
     "    pass"),
    ("verdict: conflicting identifiers are tolerated",
     '''    if payload["identity_state"] == IDENTITY_CONFLICTING:
        return INCONSISTENT_EVIDENCE''',
     "    pass"),
    ("verdict: a record that instructs its reader may win",
     '''    if int(payload["directed_text_hits"]) > 0:
        return CLAIM_NOT_ESTABLISHED''',
     "    pass"),
    ("verdict: an unverified source may win",
     '''    if not criteria["source_authenticity_verified"]:
        return CLAIM_NOT_ESTABLISHED''',
     "    pass"),
    ("verdict: insufficient evidence may win",
     '''    if not payload["findings"]["sufficient"]:
        return CLAIM_NOT_ESTABLISHED''',
     "    pass"),
    ("verdict: an uncorroborated identifier may win",
     '''    if payload["identity_state"] == IDENTITY_UNKNOWN:
        return CLAIM_NOT_ESTABLISHED''',
     "    pass"),
    ("verdict: the required event need not be supported",
     '''    if not criteria["required_event_supported"]:
        return CLAIM_NOT_ESTABLISHED''',
     "    pass"),

    # -- the comparison between validators ----------------------------
    ("validator: everything the leader says is agreed with",
     '''        difference = _first_difference(own, theirs)
        if difference != "":''',
     '''        difference = _first_difference(own, theirs)
        if False:'''),
    ("validator: the verdict is not compared",
     '''                   "authenticity_state", "evidence_status", "verdict"]''',
     '''                   "authenticity_state", "evidence_status"]'''),
    # One field at a time. A mutation that drops four states at once is
    # killed by whichever of them a fixture happens to exercise, which
    # proves nothing about the other three.
    ("validator: the origin state is not compared",
     '''                   "delivery_time", "origin_state", "compliance_state",''',
     '''                   "delivery_time", "compliance_state",'''),
    ("validator: the compliance state is not compared",
     '''                   "delivery_time", "origin_state", "compliance_state",''',
     '''                   "delivery_time", "origin_state",'''),
    ("validator: the delivery state is not compared",
     '''                   "condition_worst_excursion_minutes", "delivery_state",''',
     '''                   "condition_worst_excursion_minutes",'''),
    ("validator: the excursion is not compared",
     '''                   "condition_worst_excursion_minutes", "delivery_state",''',
     '''                   "delivery_state",'''),
    ("validator: the delivery time is not compared",
     '''                   "delivery_time", "origin_state", "compliance_state",''',
     '''                   "origin_state", "compliance_state",'''),
    ("validator: the record rows are not compared",
     '''    for index in range(len(own["rows"])):
        for field in ("record_id", "kind", "status", "reason", "byte_count",
                      "authenticity"):
            if own["rows"][index][field] != theirs["rows"][index][field]:
                return "rows[" + str(index) + "]." + field''',
     "    pass"),
    ("validator: the criteria are not compared",
     '''    for field in CRITERIA_FIELDS:
        if own["criteria"][field] != theirs["criteria"][field]:
            return "criteria." + field + ": " \\
                + str(own["criteria"][field]) + " != " \\
                + str(theirs["criteria"][field])''',
     "    pass"),
    ("validator: the checkpoint findings are not compared",
     '''    for index in range(len(mine["checkpoints"])):
        for field in ("ref", "finding", "stated_time"):
            if mine["checkpoints"][index][field] != \\
                    yours["checkpoints"][index][field]:
                return "checkpoints[" + str(index) + "]." + field''',
     "    pass"),
    ("validator: the reconciliation is not compared",
     '''    for index in range(len(own["identity_summary"])):
        for field in ("ref", "state", "value"):
            if own["identity_summary"][index][field] != \\
                    theirs["identity_summary"][index][field]:
                return "identity_summary[" + str(index) + "]." + field''',
     "    pass"),
    ("validator: a leader failure is believed without reproducing it",
     '''    if not isinstance(leader_res, gl.vm.UserError):
        return False
    leader_text = _error_text(leader_res)
    if leader_text.startswith(ERROR_PANEL):
        return False''',
     '''    if not isinstance(leader_res, gl.vm.UserError):
        return False
    return True
    leader_text = _error_text(leader_res)'''),

    # -- the deterministic lifecycle ----------------------------------
    ("lifecycle: anyone may publish a policy version",
     '''        if owner != gl.message.sender_address:
            self._reject("only the policy owner may publish a version")''',
     "        pass"),
    ("lifecycle: anyone may revoke a policy version",
     '''        if owner != gl.message.sender_address:
            self._reject("only the policy owner may revoke a version")''',
     "        pass"),
    ("lifecycle: anyone may cancel another party's challenge",
     '''        if challenge.opener != gl.message.sender_address:
            self._reject("only the account that opened it may cancel it")''',
     "        pass"),
    ("lifecycle: the deadline is not enforced",
     '''        if _minutes_of(now) > _minutes_of(str(challenge.deadline)):
            self._reject("that challenge closed on "
                         + str(challenge.deadline))''',
     "        pass"),
    ("lifecycle: the required kinds need not be offered",
     '''        for kind in definition["required_record_kinds"]:
            if kind not in offered:
                self._reject("this requirement needs a record of kind "
                             + kind)''',
     "        pass"),
    ("lifecycle: bytes may be replayed across challenges",
     '''            elif str(self.record_challenge.get(item["sha256"])) \\
                    != str(challenge_id):''',
     "            elif False:"),
    ("lifecycle: rounds never run out",
     '''        if int(submission.rounds_used) >= MAX_ROUNDS:
            self._reject("that submission has used all " + str(MAX_ROUNDS)
                         + " rounds")
        ctx = self._context(submission)''',
     "        ctx = self._context(submission)"),
    ("lifecycle: a settled submission can be adjudicated again",
     '''        if str(submission.status) != STATUS_PENDING:
            self._reject("that submission is "
                         + str(submission.status).lower())''',
     "        pass"),
    ("lifecycle: an issuer the requirement does not name is accepted",
     '''            if item["declared_issuer"] not in issuers:
                self._reject("this requirement does not name the issuer "
                             + str(item["declared_issuer"])[:40])''',
     "            pass"),
    ("lifecycle: a revoked version still takes submissions",
     '''        if bool(version.revoked):
            self._reject("that policy version is revoked")
        now = self._now()''',
     "        now = self._now()"),

    # -- the record -----------------------------------------------------
    ("record: a retried claim counts twice",
     "        if verdict in TERMINAL_VERDICTS and not bool(submission.counted):",
     "        if verdict in TERMINAL_VERDICTS:"),
    ("record: an unsettled round is counted",
     "        if verdict in TERMINAL_VERDICTS and not bool(submission.counted):",
     "        if not bool(submission.counted):"),

    # -- reliance -------------------------------------------------------
    ("reliance: an unsettled claim is consumable",
     '''        if str(submission.verdict) not in TERMINAL_VERDICTS:
            return FRESH_UNKNOWN''',
     "        pass"),
    ("reliance: a verdict never goes stale",
     '''        if age > FRESHNESS_WINDOW_SECONDS:
            return FRESH_STALE''',
     "        pass"),
    ("reliance: a revoked requirement blocks nothing",
     '''        if bool(version.revoked):
            return FRESH_BLOCKED''',
     "        pass"),
    ("reliance: an unresolved submission is consumable",
     '''        if str(submission.status) != STATUS_RESOLVED:
            return FRESH_UNKNOWN''',
     "        pass"),
]


# Two mutations cannot change behaviour, so a sweep cannot kill them and a
# test that claimed to would be lying. They are kept in the list because
# removing them would hide the reasoning, and reported separately.
EQUIVALENT = {
    "documents: any location is admitted":
        "the early return for an unreadable host is subsumed by the label "
        "loop below it: a URL whose host cannot be read yields a single "
        "empty label, which `len(labels) < 2` and the empty-label check "
        "both reject. Removing it changes no result.",
    "validator: the verdict is not compared":
        "the verdict is a pure function of fields that are themselves "
        "compared - the four criteria, the panel state, the identity "
        "state, the directed-text count, and the contradiction and "
        "sufficiency findings. Two nodes agreeing on all of those cannot "
        "differ on the verdict, so comparing it is redundancy that makes a "
        "disagreement message clearer, not a rule doing work.",
}


def run_suite(contract_path: pathlib.Path) -> bool:
    """True when the suite passes against this contract."""
    env = dict(os.environ)
    env["TRUSTROUTE_CONTRACT"] = str(contract_path)
    env["PYTHONUTF8"] = "1"
    # The whole suite runs, but in this order: the files that discriminate
    # most come first, so a mutant that is going to die usually dies in the
    # first few seconds. With `-x` that turns a sweep of seventy-nine
    # mutations from hours into minutes without weakening it - a survivor
    # still had to pass every one of the 345 tests.
    order = ["tests/direct/test_survivors.py",
             "tests/direct/test_gate_units.py",
             "tests/direct/test_validators.py",
             "tests/direct/test_verdicts.py",
             "tests/direct/test_hardening.py",
             "tests/direct/test_lifecycle.py",
             "tests/direct/test_smoke.py"]
    result = subprocess.run(
        [sys.executable, "-m", "pytest"] + order
        + ["-x", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(ROOT), env=env, capture_output=True, text=True)
    return result.returncode == 0


def main() -> int:
    needle = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    source = CONTRACT.read_text(encoding="utf-8")
    killed = []
    survived = []
    expected = []
    broken = []
    work = tempfile.mkdtemp(prefix="trustroute-mutants-")

    print("baseline: running the suite against the committed contract",
          flush=True)
    if not run_suite(CONTRACT):
        print("the suite does not pass unmutated; fix that first")
        return 1
    print("baseline PASS\n", flush=True)

    for index in range(len(MUTATIONS)):
        label, find, replace = MUTATIONS[index]
        if needle and needle not in label.lower():
            continue
        if source.count(find) != 1:
            broken.append(label)
            print("SKIP     %s (pattern occurs %d times)"
                  % (label, source.count(find)), flush=True)
            continue
        mutant = pathlib.Path(work) / ("mutant_%02d.py" % index)
        mutant.write_text(source.replace(find, replace), encoding="utf-8",
                          newline="")
        if run_suite(mutant):
            if label in EQUIVALENT:
                expected.append(label)
                print("EQUIVALENT %s" % label, flush=True)
            else:
                survived.append(label)
                print("SURVIVED %s" % label, flush=True)
        else:
            killed.append(label)
            if label in EQUIVALENT:
                print("killed   %s  (expected equivalent - the argument for "
                      "it is wrong)" % label, flush=True)
            else:
                print("killed   %s" % label, flush=True)

    total = len(killed) + len(survived) + len(expected)
    print("\n%d/%d mutants killed, %d equivalent by construction, "
          "%d survived" % (len(killed), total, len(expected),
                           len(survived)))
    for label in expected:
        print("EQUIVALENT: " + label)
        print("    " + EQUIVALENT[label])
    for label in survived:
        print("SURVIVED: " + label)
    for label in broken:
        print("SKIPPED (pattern did not match once): " + label)
    return 1 if survived or broken else 0


sys.exit(main())
