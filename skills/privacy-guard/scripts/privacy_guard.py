#!/usr/bin/env python3
"""Local privacy checks. Never print input content or subprocess diagnostics."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

SECRET = {"secret", "credential_url", "sensitive_url_parameter"}
ACTIONS = {"review", "block", "replace"}
KINDS = {"file", "filename", "stdin", "git_blob", "git_metadata", "git_filename", "json_field"}
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip",
          ".gz", ".ico", ".mp3", ".mp4", ".woff", ".woff2", ".docx", ".xlsx",
          ".onnx", ".exe", ".so", ".sqlite", ".db"}


class GuardError(Exception):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes invalid arguments, which may themselves be PII.
        raise GuardError("invalid_arguments")


def strict_json(text):
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("invalid JSON constant")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def keys(obj, allowed):
    if not isinstance(obj, dict) or set(obj) - set(allowed):
        raise GuardError("invalid_configuration")


def load_config(policy=None, private=None):
    config = {"version": 1, "max_bytes": 2097152, "actions": {}, "rules": [], "allow": []}
    for path in (policy, private):
        if not path:
            continue
        try:
            obj = strict_json(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise GuardError("invalid_configuration") from None
        keys(obj, {"version", "max_bytes", "actions", "rules", "allow", "ner"})
        if type(obj.get("version")) is not int or obj["version"] != 1:
            raise GuardError("invalid_configuration")
        for key in ("rules", "allow"):
            if key in obj:
                if not isinstance(obj[key], list):
                    raise GuardError("invalid_configuration")
                config[key].extend(obj[key])
        if "actions" in obj:
            if not isinstance(obj["actions"], dict):
                raise GuardError("invalid_configuration")
            config["actions"].update(obj["actions"])
        for key in ("max_bytes", "ner"):
            if key in obj:
                config[key] = obj[key]
    if type(config["max_bytes"]) is not int or not 1 <= config["max_bytes"] <= 67108864:
        raise GuardError("invalid_configuration")
    if any(not isinstance(k, str) or v not in ACTIONS for k, v in config["actions"].items()):
        raise GuardError("invalid_configuration")
    seen = set()
    for rule in config["rules"]:
        keys(rule, {"id", "category", "literal", "pattern", "action", "replacement", "ignore_case"})
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", str(rule.get("id", ""))):
            raise GuardError("invalid_configuration")
        if rule["id"] in seen or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", str(rule.get("category", ""))):
            raise GuardError("invalid_configuration")
        seen.add(rule["id"])
        if ("literal" in rule) == ("pattern" in rule):
            raise GuardError("invalid_configuration")
        matcher = rule.get("literal", rule.get("pattern"))
        if not isinstance(matcher, str) or not matcher:
            raise GuardError("invalid_configuration")
        if "ignore_case" in rule and type(rule["ignore_case"]) is not bool:
            raise GuardError("invalid_configuration")
        action = rule.get("action", config["actions"].get(rule["category"], "review"))
        if action not in ACTIONS or (action == "replace" and not isinstance(rule.get("replacement"), str)):
            raise GuardError("invalid_configuration")
        if "replacement" in rule and not isinstance(rule["replacement"], str):
            raise GuardError("invalid_configuration")
        try:
            re.compile(re.escape(matcher) if "literal" in rule else matcher)
        except re.error:
            raise GuardError("invalid_configuration") from None
    for entry in config["allow"]:
        keys(entry, {"category", "literal", "reason", "kind"})
        if any(not isinstance(entry.get(k), str) or not entry[k] for k in ("category", "literal", "reason")):
            raise GuardError("invalid_configuration")
        if entry["category"] in SECRET or ("kind" in entry and entry["kind"] not in KINDS):
            raise GuardError("invalid_configuration")
    if "ner" in config:
        ner = config["ner"]
        keys(ner, {"command", "artifacts", "timeout_seconds", "categories"})
        if (not isinstance(ner.get("command"), list) or not ner["command"]
                or any(not isinstance(x, str) or not x for x in ner["command"])
                or not isinstance(ner.get("artifacts"), dict) or not ner["artifacts"]):
            raise GuardError("invalid_configuration")
        if type(ner.get("timeout_seconds", 120)) is not int or not 1 <= ner.get("timeout_seconds", 120) <= 600:
            raise GuardError("invalid_configuration")
        for path, sha in ner["artifacts"].items():
            if not Path(path).is_absolute() or not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
                raise GuardError("invalid_configuration")
        if "categories" in ner and (not isinstance(ner["categories"], list) or
                any(not isinstance(x, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", x) for x in ner["categories"])):
            raise GuardError("invalid_configuration")
    return config


def git(repo, *args):
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=60,
                                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1"})
    except (OSError, subprocess.TimeoutExpired):
        raise GuardError("git_error") from None
    if result.returncode:
        raise GuardError("git_error")
    return result.stdout


def check_private_location(private, paths, repo=None):
    if not private:
        return
    location = Path(private).resolve()
    for raw in paths:
        path = Path(raw).resolve()
        if location == path or (path.is_dir() and path in location.parents):
            raise GuardError("private_profile_inside_content")
    # Walk ancestors too: nested repositories must not hide an outer publish root.
    for parent in location.parents:
        if (parent / ".git").exists():
            raise GuardError("private_profile_inside_repository")
    if repo:
        root = Path(os.fsdecode(git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
        if root in location.parents:
            raise GuardError("private_profile_inside_repository")


def luhn(value):
    digits = re.sub(r"\D", "", value)
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n = n * 2 - (9 if n >= 5 else 0)
        total += n
    return total % 10 == 0


def literal_secret_assignment(value):
    # Recognize a few unquoted references, not arbitrary expressions. Quoted
    # strings resembling a reference still block. Unknown syntax needs review.
    return not re.search(r"[:=]\s*(?:os\.getenv\(|os\.environ\[|process\.env\.|\$\{?[A-Z_][A-Z0-9_]*\}?(?:\s|$))", value)


BUILTINS = [
    ("secret", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", None),
    ("secret", r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b", None),
    ("secret", r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\b[\"']?\s*[:=]\s*[\"']?[^\s\"'<>;,}]{4,}", literal_secret_assignment),
    ("secret", r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/-]{8,}={0,2}|Basic\s+[A-Za-z0-9+/]{8,}={0,2})", None),
    ("credential_url", r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/<>\"']+:[^\s/<>\"']+@", None),
    ("sensitive_url_parameter", r"(?i)[?&#](?:token|access_token|api_key|key|password|secret|signature|sig|x-amz-signature|x-amz-credential)=[^\s&#<>\"']+", None),
    ("email", r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", None),
    ("phone", r"(?<!\w)\+\d[\d ()-]{6,}\d(?!\w)|(?<!\d)\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)", None),
    ("ip_address", r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", lambda s: valid_ip(s)),
    ("government_id", r"(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)", lambda s: valid_ssn(s)),
    ("payment_card", r"(?<!\d)\d(?:[ -]?\d){12,18}(?![ -]?\d)", luhn),
    ("local_path", r"(?:/home/|/Users/)[^/\s<>\"']+|[A-Za-z]:\\Users\\[^\\\s<>\"']+", None),
    ("account_details", r"(?i)\b(?:my|our|account|remaining|paid)\s+(?:account\s+)?(?:balance|credits?|subscription|allowance)\b[^\n.!?]{0,100}|\b(?:balance|credits?)\s*[:=]\s*[$€£]?\d[\d,.]*|(?:我的|账户|账号|剩余|付费)(?:余额|额度|积分|订阅)[^\n。！？]{0,100}", None),
]


def valid_ip(value):
    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


def valid_ssn(value):
    digits = re.sub(r"\D", "", value)
    return digits[:3] not in {"000", "666"} and digits[0] != "9" and digits[3:5] != "00" and digits[5:] != "0000"


def verify_artifacts(config):
    for path, sha in config.get("ner", {}).get("artifacts", {}).items():
        try:
            with open(path, "rb") as stream:
                h = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1048576), b""):
                    h.update(chunk)
            if h.hexdigest() != sha:
                raise GuardError("detector_artifact_mismatch")
        except OSError:
            raise GuardError("detector_artifact_unavailable") from None


def ner_spans(text, config):
    ner = config["ner"]
    try:
        result = subprocess.run(ner["command"], input=canonical({"text": text}), capture_output=True,
                                timeout=ner.get("timeout_seconds", 120))
        if result.returncode or len(result.stdout) > 16777216:
            raise GuardError("detector_error")
        spans = strict_json(result.stdout)
        if not isinstance(spans, list):
            raise GuardError("detector_invalid_output")
        for span in spans:
            keys(span, {"start", "end", "label", "score"})
            if (type(span.get("start")) is not int or type(span.get("end")) is not int
                    or not 0 <= span["start"] < span["end"] <= len(text)
                    or not isinstance(span.get("label"), str)
                    or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", span["label"])
                    or ("score" in span and (type(span["score"]) not in (int, float) or not 0 <= span["score"] <= 1))):
                raise GuardError("detector_invalid_output")
        return [s for s in spans if "categories" not in ner or s["label"] in ner["categories"]]
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise GuardError("detector_error") from None


def detect(text, config, kind):
    found = []

    def add(start, end, category, rule_id, action=None, replacement=None):
        if end <= start:
            raise GuardError("zero_width_rule")
        action = "block" if category in SECRET else action or config["actions"].get(category, "review")
        if any(a["category"] == category and a["literal"] == text[start:end]
               and a.get("kind", kind) == kind for a in config["allow"]):
            return
        found.append({"start": start, "end": end, "category": category,
                      "action": action, "rule": rule_id, "replacement": replacement})

    for category, pattern, validator in BUILTINS:
        for match in re.finditer(pattern, text):
            if validator is None or validator(match.group()):
                add(match.start(), match.end(), category, "builtin_" + category)
    for i, rule in enumerate(config["rules"]):
        pattern = re.escape(rule["literal"]) if "literal" in rule else rule["pattern"]
        for match in re.finditer(pattern, text, re.I if rule.get("ignore_case") else 0):
            add(match.start(), match.end(), rule["category"], "custom_" + str(i),
                rule.get("action"), rule.get("replacement"))
    if "ner" in config:
        for span in ner_spans(text, config):
            label = span["label"].lower()
            add(span["start"], span["end"], label if label in SECRET else "ner_" + label, "ner")
    # A user-configured replacement that covers an entire non-secret built-in/NER
    # finding resolves it; partial overlaps and other custom rules remain reviewable.
    replacements = [f for f in found if f["rule"].startswith("custom_") and f["action"] == "replace"]
    found = [f for f in found if f["category"] in SECRET or f["rule"].startswith("custom_") or
             not any(r["start"] <= f["start"] and r["end"] >= f["end"] for r in replacements)]
    return sorted(found, key=lambda f: (f["start"], f["end"], f["category"], f["rule"]))


class Scanner:
    def __init__(self, config, profile="document", show_paths=False, json_payload=False):
        self.config = config
        self.show_paths = show_paths
        self.json_payload = json_payload
        self.report = {"version": 1, "profile": profile, "policy_sha256": digest(canonical(config)),
                       "engine_sha256": digest(Path(__file__).read_bytes()),
                       "coverage": {"rules": True, "ner": "ner" in config, "complete": True},
                       "sources": [], "findings": [], "issues": []}

    def source_id(self, kind, name):
        return digest(canonical([kind, name]))[:24]

    def issue(self, kind, name, code):
        issue = {"source": self.source_id(kind, name), "kind": kind, "code": code}
        if self.show_paths:
            issue["location"] = name
        self.report["issues"].append(issue)
        self.report["coverage"]["complete"] = False

    def scan_bytes(self, data, kind, name):
        if len(data) > self.config["max_bytes"]:
            self.issue(kind, name, "oversize_input")
            return []
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            self.issue(kind, name, "non_utf8_input")
            return []
        if "\x00" in text:
            self.issue(kind, name, "binary_input")
            return []
        if text.startswith("version https://git-lfs.github.com/spec/v1\n"):
            self.issue(kind, name, "external_lfs_object")
            return []
        source = {"id": self.source_id(kind, name), "kind": kind, "content_sha256": digest(data)}
        if self.show_paths:
            source["location"] = name
        self.report["sources"].append(source)
        findings = detect(text, self.config, kind)
        for finding in findings:
            public = {k: v for k, v in finding.items() if k not in {"replacement", "rule"}}
            public.update(source=source["id"], line=text.count("\n", 0, finding["start"]) + 1)
            public["id"] = digest(canonical([source["id"], source["content_sha256"], self.report["policy_sha256"],
                                             self.report["engine_sha256"], self.report["profile"], finding]))[:24]
            public["replaceable"] = finding["action"] == "replace" and finding["replacement"] is not None
            self.report["findings"].append(public)
            finding["id"] = public["id"]
        if self.json_payload and kind in {"file", "stdin"}:
            try:
                payload = strict_json(text)
            except ValueError:
                self.issue(kind, name, "invalid_json_payload")
                return findings
            self.json_fields(payload, name)
        return findings

    def json_fields(self, payload, name):
        # Decode JSON escapes before checking strings. Structural indexes rather
        # than key names keep source locations from disclosing private field names.
        queue = [(payload, "root")]
        while queue:
            value, position = queue.pop()
            if isinstance(value, dict):
                for i, (key, item) in reversed(list(enumerate(value.items()))):
                    location = name + "#" + position + "." + str(i)
                    self.scan_bytes(key.encode("utf-8"), "json_field", location + ".key")
                    # A field-name/value projection catches contextual facts such
                    # as {"balance": 123}; string values are also scanned alone.
                    if isinstance(item, (str, int, float)) and not isinstance(item, bool):
                        self.scan_bytes((key + ": " + str(item)).encode("utf-8"), "json_field", location + ".pair")
                    queue.append((item, position + "." + str(i)))
            elif isinstance(value, list):
                for i in range(len(value) - 1, -1, -1):
                    queue.append((value[i], position + "." + str(i)))
            elif isinstance(value, str):
                self.scan_bytes(value.encode("utf-8"), "json_field", name + "#" + position + ".value")

    def file(self, path, published_name=None):
        name = str(path)
        self.scan_bytes((published_name or path.name).encode("utf-8"), "filename", name)
        try:
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                self.issue("file", name, "unsupported_file_type")
                return
            if path.suffix.lower() in BINARY:
                self.issue("file", name, "unsupported_binary_format")
                return
            # NOFOLLOW closes the lstat/open symlink race on platforms supporting it.
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    self.issue("file", name, "unsupported_file_type")
                    return
                data = stream.read(self.config["max_bytes"] + 1)
            self.scan_bytes(data, "file", name)
        except OSError:
            self.issue("file", name, "unreadable_input")

    def paths(self, paths):
        seen = set()
        for raw in sorted(paths):
            path = Path(raw)
            if path.is_dir() and not path.is_symlink():
                def walk_error(_):
                    self.issue("file", raw, "unreadable_directory")
                for root, dirs, files in os.walk(path, followlinks=False, onerror=walk_error):
                    dirs[:] = sorted(d for d in dirs if d != ".git")
                    for directory in list(dirs):
                        child = Path(root) / directory
                        if child.is_symlink():
                            self.file(child, str(Path(path.name) / child.relative_to(path)))
                            dirs.remove(directory)
                    for filename in sorted(files):
                        if filename == ".git":
                            continue
                        child = Path(root) / filename
                        key = os.path.abspath(child)
                        if key not in seen:
                            seen.add(key)
                            self.file(child, str(Path(path.name) / child.relative_to(path)))
            else:
                key = os.path.abspath(path)
                if key not in seen:
                    seen.add(key)
                    self.file(path)

    def git_scan(self, repo, staged=False, refs=None, base=None):
        repo = os.fsdecode(git(repo, "rev-parse", "--show-toplevel")).strip()
        if staged:
            trees = [("index", git(repo, "ls-files", "--stage", "-z"))]
        else:
            resolved = []
            for ref in refs or ["HEAD"]:
                oid = git(repo, "rev-parse", "--verify", "--end-of-options", ref).strip().decode("ascii")
                if git(repo, "cat-file", "-t", oid).strip() == b"tag":
                    self.issue("git_metadata", oid, "annotated_tag_uninspected")
                resolved.append(git(repo, "rev-parse", "--verify", oid + "^{commit}").strip().decode("ascii"))
            exclusion = []
            if base:
                exclusion = ["^" + git(repo, "rev-parse", "--verify", "--end-of-options", base + "^{commit}").strip().decode("ascii")]
            if git(repo, "rev-parse", "--is-shallow-repository").strip() == b"true":
                self.issue("git_metadata", "history", "shallow_history")
            commits = sorted(set(git(repo, "rev-list", *resolved, *exclusion, "--").decode("ascii").split()))
            trees = []
            for commit in commits:
                self.scan_bytes(git(repo, "show", "-s", "--format=%an <%ae>%n%cn <%ce>%n%B", commit), "git_metadata", commit)
                trees.append((commit, git(repo, "ls-tree", "-r", "-z", commit)))
        seen_blobs, seen_names = set(), set()
        for tree, entries in trees:
            for entry in entries.split(b"\x00"):
                if not entry:
                    continue
                header, filename = entry.split(b"\t", 1)
                mode, middle, last = header.split()
                oid = middle if staged else last
                name = os.fsdecode(filename)
                if name not in seen_names:
                    self.scan_bytes(filename, "git_filename", name)
                    seen_names.add(name)
                if staged and last != b"0":
                    self.issue("git_blob", name, "unmerged_index")
                    continue
                if mode not in {b"100644", b"100755"}:
                    self.issue("git_blob", name, "symlink_or_submodule")
                    continue
                if Path(name).suffix.lower() in BINARY:
                    self.issue("git_blob", name, "unsupported_binary_format")
                    continue
                if oid in seen_blobs:
                    continue
                seen_blobs.add(oid)
                size = int(git(repo, "cat-file", "-s", oid.decode("ascii")))
                if size > self.config["max_bytes"]:
                    self.issue("git_blob", name, "oversize_input")
                    continue
                self.scan_bytes(git(repo, "cat-file", "blob", oid.decode("ascii")), "git_blob", name + "@" + oid.decode("ascii"))

    def result(self):
        self.report["sources"].sort(key=lambda s: (s["kind"], s["id"]))
        self.report["findings"].sort(key=lambda f: (f["source"], f["start"], f["end"], f["id"]))
        self.report["issues"].sort(key=lambda i: (i["source"], i["code"]))
        self.report["status"] = "incomplete" if self.report["issues"] else "findings" if self.report["findings"] else "checked"
        return self.report, 2 if self.report["issues"] else 1 if self.report["findings"] else 0


def apply_file(args, config):
    if len(args.path or []) != 1 or not re.fullmatch(r"[a-f0-9]{64}", args.expect_sha256 or ""):
        raise GuardError("apply_requires_one_file_and_digest")
    path = Path(args.path[0])
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.suffix.lower() in BINARY:
        raise GuardError("unsupported_apply_input")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        before_stat = os.fstat(stream.fileno())
        if not stat.S_ISREG(before_stat.st_mode):
            raise GuardError("unsupported_apply_input")
        before = stream.read(config["max_bytes"] + 1)
    if digest(before) != args.expect_sha256:
        raise GuardError("stale_content")
    scanner = Scanner(config, args.profile, args.show_paths)
    filename_findings = scanner.scan_bytes(path.name.encode(), "filename", str(path))
    findings = scanner.scan_bytes(before, "file", str(path))
    if scanner.report["issues"] or filename_findings:
        raise GuardError("unsupported_apply_input")
    if not findings or set(args.approve or []) != {f["id"] for f in findings}:
        raise GuardError("approval_required_for_all_findings")
    if any(f["action"] != "replace" or f["replacement"] is None for f in findings):
        raise GuardError("manual_review_required")
    if any(a["end"] > b["start"] for a, b in zip(findings, findings[1:])):
        raise GuardError("overlapping_replacements")
    text = before.decode("utf-8")
    if path.suffix.lower() == ".json":
        strict_json(text)
    for f in reversed(findings):
        text = text[:f["start"]] + f["replacement"] + text[f["end"]:]
    if path.suffix.lower() == ".json":
        strict_json(text)
    after = text.encode("utf-8")
    candidate = Scanner(config, args.profile, args.show_paths)
    candidate.scan_bytes(after, "file", str(path))
    if candidate.result()[1]:
        raise GuardError("candidate_not_clean")
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".privacy-guard-", dir=path.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), stat.S_IMODE(before_stat.st_mode))
        now = path.lstat()
        if (now.st_dev, now.st_ino, now.st_mtime_ns, now.st_size) != (before_stat.st_dev, before_stat.st_ino, before_stat.st_mtime_ns, before_stat.st_size):
            raise GuardError("stale_content")
        if path.read_bytes() != before:
            raise GuardError("stale_content")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            os.unlink(temporary)
    report, code = candidate.result()
    report["applied"] = len(findings)
    report["previous_sha256"] = digest(before)
    return report, code


def parser():
    p = SafeParser(description=__doc__)
    p.add_argument("command", choices=["scan", "apply"])
    p.add_argument("--profile", choices=["code", "blog", "forum", "document"], default="document")
    p.add_argument("--path", action="append")
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--json", action="store_true", help="Also scan decoded JSON fields (scan paths/stdin only)")
    p.add_argument("--repo", default=".")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--outgoing", action="store_true")
    p.add_argument("--ref", action="append")
    p.add_argument("--base")
    p.add_argument("--policy")
    p.add_argument("--private")
    p.add_argument("--show-paths", action="store_true")
    p.add_argument("--expect-sha256")
    p.add_argument("--approve", action="append")
    return p


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if sum([bool(args.path), args.stdin, args.staged, args.outgoing]) != 1:
            raise GuardError("select_exactly_one_input_mode")
        if (args.ref or args.base) and not args.outgoing:
            raise GuardError("refs_require_outgoing")
        if args.command == "scan" and (args.approve or args.expect_sha256):
            raise GuardError("approval_options_require_apply")
        if args.json and (args.command != "scan" or args.staged or args.outgoing):
            raise GuardError("json_requires_scan_paths_or_stdin")
        check_private_location(args.private, args.path or [], args.repo if args.staged or args.outgoing else None)
        config = load_config(args.policy, args.private)
        verify_artifacts(config)
        if args.command == "apply":
            report, code = apply_file(args, config)
        else:
            scanner = Scanner(config, args.profile, args.show_paths, args.json)
            if args.path:
                scanner.paths(args.path)
            elif args.stdin:
                scanner.scan_bytes(sys.stdin.buffer.read(config["max_bytes"] + 1), "stdin", "stdin")
            else:
                scanner.git_scan(args.repo, args.staged, args.ref, args.base)
            report, code = scanner.result()
    except GuardError as exc:
        report, code = {"version": 1, "status": "error", "code": str(exc)}, 2
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, re.error, RecursionError):
        report, code = {"version": 1, "status": "error", "code": "input_or_configuration_error"}, 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
