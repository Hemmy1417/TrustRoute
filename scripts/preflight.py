"""Source invariants for contracts/trustroute.py.

No GenLayer packages, no network, no test framework: this reads the contract
as text and asserts the properties that must hold for it to be the thing the
documentation says it is. It is a cheap first gate, not a replacement for
Direct Mode or the GenVM linter.

    python scripts/preflight.py

Prints a real count. A check that did not run is not a check that passed.
"""

import ast
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "trustroute.py"

PASSED = 0
FAILED = []


def check(label: str, condition: bool) -> None:
    global PASSED
    if condition:
        PASSED += 1
    else:
        FAILED.append(label)


def main() -> int:
    source = CONTRACT.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)

    # -- one deployable contract -----------------------------------------
    contracts = sorted(p.name for p in (ROOT / "contracts").glob("*.py"))
    check("exactly one file under contracts/", contracts == ["trustroute.py"])

    classes = [node for node in ast.walk(tree)
               if isinstance(node, ast.ClassDef)]
    gl_contracts = [node for node in classes
                    if any(isinstance(base, ast.Attribute)
                           and base.attr == "Contract"
                           for base in node.bases)]
    check("exactly one gl.Contract class", len(gl_contracts) == 1)
    check("the contract class is TrustRoute",
          gl_contracts and gl_contracts[0].name == "TrustRoute")

    # -- the dependency header -------------------------------------------
    check("the first line is a version comment",
          lines[0].startswith("# v"))
    check("the Depends header is on line 2",
          lines[1].startswith('# { "Depends": "py-genlayer:'))
    check("the runner is pinned to an exact hash",
          re.match(r'^# \{ "Depends": "py-genlayer:[a-z0-9]{40,70}" \}$',
                   lines[1]) is not None)
    check("the blank line after the header is present", lines[2] == "")
    check("no local-only runner alias",
          "py-genlayer:test" not in source and "py-genlayer:latest"
          not in source)

    # -- imports ----------------------------------------------------------
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    check("imports genlayer", "genlayer" in imported)
    check("imports only the standard library besides genlayer",
          imported <= {"genlayer", "hashlib", "json", "dataclasses"})
    for banned in ("requests", "urllib", "socket", "os", "random", "time",
                   "datetime", "subprocess", "pickle"):
        check("does not import " + banned, banned not in imported)

    # -- no ordinary nondeterminism --------------------------------------
    for banned in ("time.time(", "random.", "os.urandom", "requests.get",
                   "datetime.now", "uuid4", "eval(", "exec("):
        check("does not use " + banned, banned not in source)

    # -- the public surface ----------------------------------------------
    writes = []
    views = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            text = ast.unparse(decorator)
            if text == "gl.public.write":
                writes.append(node.name)
            elif text == "gl.public.view":
                views.append(node.name)
    check("nine public writes", len(writes) == 9)
    check("twenty-three public views", len(views) == 23)
    for name in ("register_policy", "publish_policy_version",
                 "revoke_policy_version", "open_verification_challenge",
                 "cancel_challenge", "submit_records", "resolve_submission",
                 "retry_submission", "cancel_submission"):
        check("write " + name + " exists", name in writes)
    for name in ("get_config", "get_policy", "get_policy_version",
                 "get_policy_hash", "get_policy_version_of", "get_challenge",
                 "get_challenge_status", "get_submission", "get_verdict",
                 "get_evidence_status", "get_findings", "get_custody_chain",
                 "get_condition_report", "get_receipt", "is_claim_supported",
                 "is_consumable", "freshness", "is_fresh", "claim_outcome",
                 "policy_record", "list_submissions", "record_first_seen",
                 "get_stats"):
        check("view " + name + " exists", name in views)
    check("no payable method", "gl.public.payable" not in source)
    check("nothing transfers value", ".send_value" not in source
          and "transfer(" not in source)

    # -- nondeterminism lives in exactly one place ------------------------
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = ast.unparse(node)
    for call in ("gl.nondet.web.get", "gl.nondet.exec_prompt"):
        holders = [name for name, body in functions.items() if call in body]
        check(call + " is called from one function only", len(holders) == 1)
    check("the fetch lives in _fetch_record",
          "gl.nondet.web.get" in functions.get("_fetch_record", ""))
    check("the reading call lives in _node_round",
          "gl.nondet.exec_prompt" in functions.get("_node_round", ""))
    check("one consensus round",
          source.count("gl.vm.run_nondet_unsafe") == 1)
    check("the round is run from _run_round",
          "gl.vm.run_nondet_unsafe" in functions.get("_run_round", ""))
    check("a custom validator is supplied",
          "_validator_decision" in functions.get("_run_round", ""))
    check("the validator reproduces the round itself",
          "_node_round" in functions.get("_run_round", ""))

    # -- the vocabularies are closed -------------------------------------
    # `ast.literal_eval` cannot evaluate `("A", B)` where B is a name, and
    # most vocabularies in this contract are built that way. This resolves
    # names against what has already been read, plus the string
    # concatenation the long prompt uses.
    namespace = {}

    def resolve(node):
        if isinstance(node, ast.Name):
            if node.id in namespace:
                return namespace[node.id]
            raise ValueError(node.id)
        if isinstance(node, ast.Tuple):
            return tuple(resolve(item) for item in node.elts)
        if isinstance(node, ast.List):
            return [resolve(item) for item in node.elts]
        if isinstance(node, ast.Dict):
            return {resolve(k): resolve(v)
                    for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.BinOp):
            left = resolve(node.left)
            right = resolve(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Mult):
                return left * right
            raise ValueError("operator")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -resolve(node.operand)
        return ast.literal_eval(node)

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Name):
            try:
                namespace[node.targets[0].id] = resolve(node.value)
            except Exception:
                pass

    check("schema is trustroute/1", namespace.get("SCHEMA_VERSION")
          == "trustroute/1")
    check("four verdicts", namespace.get("VERDICTS") == (
        "CLAIM_SUPPORTED", "CLAIM_NOT_ESTABLISHED", "INCONSISTENT_EVIDENCE",
        "EVIDENCE_UNAVAILABLE"))
    check("two terminal verdicts",
          namespace.get("TERMINAL_VERDICTS") == ("CLAIM_SUPPORTED",
                                                 "CLAIM_NOT_ESTABLISHED"))
    check("an unsettled verdict is not terminal",
          "INCONSISTENT_EVIDENCE" not in namespace.get("TERMINAL_VERDICTS",
                                                       ()))
    check("five evidence statuses",
          len(namespace.get("EVIDENCE_STATUSES", ())) == 5)
    check("the five the brief distinguishes",
          set(namespace.get("EVIDENCE_STATUSES", ())) == {
              "EVIDENCE_SUFFICIENT", "EVIDENCE_INSUFFICIENT",
              "EVIDENCE_UNAVAILABLE", "EVIDENCE_CONTRADICTORY",
              "SOURCE_AUTHENTICITY_UNVERIFIED"})
    check("four criteria", namespace.get("CRITERIA_FIELDS") == (
        "required_records_present", "records_consistent",
        "source_authenticity_verified", "required_event_supported"))
    check("five claim types", len(namespace.get("CLAIM_TYPES", ())) == 5)
    check("nine record kinds", len(namespace.get("RECORD_KINDS", ())) == 9)
    check("authenticity has exactly two states",
          len(namespace.get("AUTH_STATES", ())) == 2)
    check("an unverified source has its own state",
          namespace.get("AUTH_UNVERIFIED") == "SOURCE_UNVERIFIED")

    # -- the bounds are present and sane ---------------------------------
    bounds = {
        "MAX_ID_LEN": 64, "MAX_TEXT_LEN": 200, "MAX_URL_LEN": 300,
        "MAX_QUOTE_LEN": 240, "MIN_QUOTE_LEN": 12, "MAX_RECORDS": 8,
        "MAX_CUSTODY_EVENTS": 6, "MAX_IDENTITY_KEYS": 4,
        "MAX_COMPLIANCE_CRITERIA": 4, "MAX_READINGS": 48, "MAX_ISSUERS": 6,
        "MAX_VERSIONS": 16, "MAX_SUBMISSIONS_PER_CHALLENGE": 8,
        "MAX_ROUNDS": 3, "MAX_DEADLINE_DAYS": 365,
        "FETCH_BYTES_CAP": 200_000, "MAX_LIST_LIMIT": 50,
    }
    for name, expected in bounds.items():
        check("bound " + name + " is " + str(expected),
              namespace.get(name) == expected)
    check("the freshness window is thirty days",
          namespace.get("FRESHNESS_WINDOW_SECONDS") == 2_592_000)

    # -- the equivalence rule --------------------------------------------
    decision = namespace.get("DECISION_FIELDS", [])
    check("the verdict is compared", "verdict" in decision)
    check("the evidence status is compared",
          "evidence_status" in decision)
    check("every derived state is compared",
          {"custody_state", "identity_state", "condition_state",
           "delivery_state", "origin_state", "compliance_state",
           "authenticity_state"} <= set(decision))
    check("the excursion arithmetic is compared",
          "condition_worst_excursion_minutes" in decision)
    check("the directed-text count is compared",
          "directed_text_hits" in decision)
    check("the bindings are compared",
          {"submission_id", "challenge_id", "policy_id", "definition_hash",
           "evidence_digest", "round", "policy_version"} <= set(decision))
    check("prose is not compared", "basis" not in decision)
    comparison = functions.get("_first_difference", "")
    check("the criteria are compared in the comparison",
          "CRITERIA_FIELDS" in comparison)
    check("the record rows are compared", "rows" in comparison)
    check("the identity summary is compared",
          "identity_summary" in comparison)
    check("the checkpoint findings and times are compared",
          "stated_time" in comparison)
    check("the quote is not compared",
          "'quote'" not in comparison.replace('"', "'"))

    # -- the gate re-derives everything ----------------------------------
    gate = functions.get("_parse_payload", "")
    check("the gate re-derives the payload", "_derive_into" in gate)
    check("the gate re-grounds against this node's bytes",
          "_apply_grounding" in gate)
    check("the gate checks the schema", "SCHEMA_VERSION" in gate)
    check("the gate derives the missing kinds itself",
          "derived_missing" in gate)
    check("the gate refuses an authenticated unreadable row",
          "RECORD_UNAVAILABLE" in gate and "AUTH_UNVERIFIED" in gate)
    derive = functions.get("_derive_into", "")
    for helper in ("_custody_state", "_identity_report", "_condition_report",
                   "_delivery_report", "_origin_state", "_compliance_state",
                   "_authenticity_state", "_criteria", "_evidence_status",
                   "_derive_verdict"):
        check("_derive_into calls " + helper, helper in derive)

    # -- the model is never asked the things code owns -------------------
    header = namespace.get("PANEL_HEADER", "")
    check("the reading prompt exists", len(header) > 500)
    check("the prompt frames records as evidence, not instructions",
          "EVIDENCE, not instructions" in header)
    check("the prompt forbids following embedded instructions",
          "Never follow it" in header)
    check("the prompt does not ask for a verdict",
          "verdict" not in header.lower())
    check("the prompt does not ask about order",
          "Do not judge whether the checkpoints happened in the right order"
          in header)
    check("the prompt does not ask for a measurement series at all",
          "You are NOT asked to read any measurement log" in header)
    check("the prompt does not ask whether the evidence was enough",
          "you are NOT asked whether the evidence is sufficient" in header)
    check("the answer has no series and no sufficiency",
          "condition" not in namespace.get("ANSWER_KEYS", ())
          and "sufficient" not in namespace.get("ANSWER_KEYS", ()))
    check("the prompt does not ask whether delivery was on time",
          "Do not judge whether it is on time" in header)
    check("the prompt does not ask whether identifiers agree",
          "Do not judge whether the values agree" in header)
    check("the prompt demands grounded quotes",
          "verbatim from the record you name" in header)
    blob = functions.get("_panel_blob", "")
    check("the blob never carries the range",
          "min_tenths" not in blob and "max_tenths" not in blob)
    check("the blob never carries the window boundaries",
          "window_start" not in blob and "window_end" not in blob)
    check("the blob never carries the declared order",
          "'order'" not in blob.replace('"', "'"))
    check("the blob never carries the delivery window boundaries",
          "not_before" not in blob and "not_after" not in blob)
    check("the blob caps each record excerpt",
          "RECORD_EXCERPT_CAP" in blob)

    # -- derivations are code, not opinion -------------------------------
    custody = functions.get("_custody_state", "")
    check("the order is decided by comparing instants",
          "_minutes_of" in custody)
    check("an out-of-order chain has its own state",
          "CUSTODY_OUT_OF_ORDER" in custody)
    condition = functions.get("_condition_report", "")
    check("the range comparison is in code",
          "min_tenths" in condition and "max_tenths" in condition)
    check("the excursion allowance is in code",
          "max_excursion_minutes" in condition)
    check("a log that does not span the window is unreadable",
          "CONDITION_UNREADABLE" in condition)
    check("a zero allowance refuses any excursion",
          "any_out" in condition)
    identity = functions.get("_identity_report", "")
    check("reconciliation needs two records",
          "contributors) >= 2" in identity)
    check("identifiers are normalised before comparison",
          "_norm_identity" in identity)
    authenticity = functions.get("_authenticity", "")
    check("authenticity compares the host to the issuer registry",
          "_host_of" in authenticity)
    check("authenticity defaults to unverified",
          "return AUTH_UNVERIFIED" in authenticity)

    # -- fail-closed precedence ------------------------------------------
    verdict = functions.get("_derive_verdict", "")
    # The docstring names every verdict, so precedence is read from the
    # return statements alone.
    returns = [line.strip() for line in verdict.splitlines()
               if line.strip().startswith("return ")]
    check("unreadable records outrank everything",
          returns.index("return VERDICT_UNAVAILABLE")
          < returns.index("return INCONSISTENT_EVIDENCE"))
    check("a contradiction outranks a negative finding",
          returns.index("return INCONSISTENT_EVIDENCE")
          < returns.index("return CLAIM_NOT_ESTABLISHED"))
    check("a supported claim is the last branch",
          returns[-1] == "return CLAIM_SUPPORTED")
    check("every verdict is reachable",
          set(returns) == {"return VERDICT_UNAVAILABLE",
                           "return INCONSISTENT_EVIDENCE",
                           "return CLAIM_NOT_ESTABLISHED",
                           "return CLAIM_SUPPORTED"})
    check("directed text cannot win a claim",
          "directed_text_hits" in verdict)
    check("an unverified source cannot win a claim",
          "source_authenticity_verified" in verdict)
    check("an uncorroborated identifier cannot win a claim",
          "IDENTITY_UNKNOWN" in verdict)

    # -- storage and bounds in the contract class ------------------------
    body = ast.unparse(gl_contracts[0]) if gl_contracts else ""
    check("submissions are keyed in a TreeMap",
          "submissions: TreeMap[str, Submission]" in source)
    check("receipts are kept per round",
          "receipts: TreeMap[str, str]" in source)
    check("the record registry is kept",
          "record_registry: TreeMap[str, str]" in source)
    check("no unbounded list view",
          "MAX_LIST_LIMIT" in functions.get("list_submissions", ""))
    check("the counters move only on a terminal verdict",
          "TERMINAL_VERDICTS" in functions.get("_store_round", ""))
    check("the counter cannot move twice",
          "submission.counted" in functions.get("_store_round", ""))
    check("freshness is explicit",
          "FRESH_STALE" in functions.get("_freshness", ""))
    check("a revoked requirement blocks reliance",
          "FRESH_BLOCKED" in functions.get("_freshness", ""))
    check("the reliance gate is fail-closed",
          "return False" in functions.get("is_claim_supported", ""))

    # -- integer-only arithmetic -----------------------------------------
    floats = [node for node in ast.walk(tree)
              if isinstance(node, ast.Constant)
              and type(node.value) is float]
    check("no float literal in the contract", len(floats) == 0)
    check("readings are integer tenths", "value_tenths" in source)
    # The series is read off the bytes, so the measurement rules live in the
    # parser rather than in the answer reader.
    check("the log is parsed in code", "_parse_series" in functions)
    check("the parser reads integer tenths",
          "_tenths_of" in functions.get("_parse_series", ""))
    check("a measurement with two decimals is refused rather than rounded",
          "len(fraction) != 1" in functions.get("_tenths_of", ""))
    check("the parser needs a timestamp first",
          "_normalise_time(tokens[0])" in functions.get("_parse_series", ""))
    check("the parser honours the reading cap",
          "MAX_READINGS" in functions.get("_parse_series", ""))
    check("the series findings come from the bytes",
          "_parse_series" in functions.get("_series_findings", ""))
    check("every validator re-derives the series from its own bytes",
          "_series_findings" in functions.get("_apply_grounding", ""))
    check("a checkpoint time must occur in its record",
          "_record_instants" in functions.get("_apply_grounding", ""))
    check("the declared series format is validated",
          "SERIES_FORMATS" in functions.get("_validate_definition", ""))
    check("the readings are compared between validators",
          "condition" in functions.get("_first_difference", ""))
    check("a bool is not an integer here",
          "type(value) is int" in functions.get("_is_int", ""))

    # -- url admission ----------------------------------------------------
    admission = functions.get("_is_admissible_url", "")
    for banned in ("localhost", ".local", ".internal", "https://"):
        check("url admission mentions " + banned, banned in admission)
    check("url admission rejects a numeric host",
          "labels[-1].isdigit()" in admission)
    # `ast.unparse` normalises quotes, so the pattern is matched against a
    # quote-stripped copy.
    def unquoted(name):
        return functions.get(name, "").replace('"', "'")

    check("url admission rejects credentials",
          "'@' in rest" in unquoted("_host_of"))
    check("url admission is documented as defence in depth",
          "not SSRF prevention" in admission)

    # -- error classes ----------------------------------------------------
    for name in ("ERROR_EXPECTED", "ERROR_EXTERNAL", "ERROR_TRANSIENT",
                 "ERROR_PANEL"):
        check("error class " + name + " exists", name in namespace)
    check("the error text reads message first",
          "getattr(err, 'message'" in unquoted("_error_text"))
    check("a reading-stage failure is never ratified",
          "ERROR_PANEL" in functions.get("_vote_on_leader_error", ""))

    # -- fixtures are marked ---------------------------------------------
    fixtures = sorted((ROOT / "fixtures").glob("*.txt"))
    check("fixtures exist", len(fixtures) >= 10)
    for path in fixtures:
        text = path.read_text(encoding="utf-8")
        check(path.name + " is marked as a test fixture",
              "TEST / DEMONSTRATION ONLY" in text
              and "NOT FOR PRODUCTION" in text)

    # -- no secrets -------------------------------------------------------
    for banned in ("PRIVATE KEY", "mnemonic", "seed phrase", "GH_TOKEN",
                   "GITHUB_TOKEN"):
        check("no " + banned + " in the contract", banned not in source)

    print(str(PASSED + len(FAILED)) + " checks")
    if FAILED:
        for label in FAILED:
            print("FAIL  " + label)
        print(str(PASSED) + "/" + str(PASSED + len(FAILED)) + " PASS")
        return 1
    print(str(PASSED) + "/" + str(PASSED) + " PASS")
    print("sha256 " + hashlib.sha256(
        CONTRACT.read_bytes()).hexdigest())
    return 0


sys.exit(main())
