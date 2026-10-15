import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "privacy_guard.py"
spec = importlib.util.spec_from_file_location("privacy_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class FixtureMixin:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="privacy-guard-test-")
        self.root = Path(self.temp.name)
        self.content = self.root / "content"
        self.content.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def config(self, **kwargs):
        path = self.root / "policy.json"
        path.write_text(json.dumps({"version": 1, **kwargs}))
        return guard.load_config(path)

    def scan(self, text, config=None, kind="stdin"):
        s = guard.Scanner(config or guard.load_config())
        s.scan_bytes(text.encode(), kind, "source")
        return s.result()

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.main(list(args))
        return json.loads(out.getvalue()), code

    def file(self, text, name="article.md"):
        path = self.content / name
        path.write_bytes(text.encode())
        return path


class PrivacyTests(FixtureMixin, unittest.TestCase):
    def test_clean_public_links_and_code(self):
        report, code = self.scan("Read https://example.org/docs?lang=en\n```python\nprint(42)\n```")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "checked")
        self.assertFalse(report["coverage"]["ner"])

    def test_masked_report_and_determinism(self):
        text = "Contact private.person@example.net; /home/secret-person/notes"
        a, code = self.scan(text)
        b, _ = self.scan(text)
        self.assertEqual(code, 1)
        self.assertEqual(a, b)
        encoded = json.dumps(a)
        for value in ("private.person", "example.net", "secret-person", "source"):
            if value != "source":
                self.assertNotIn(value, encoded)
        self.assertEqual({f["category"] for f in a["findings"]}, {"email", "local_path"})

    def test_secrets_not_exempted_by_public_url(self):
        text = "https://public.example/docs?token=privatevalue and https://u:password@example.org/x"
        report, code = self.scan(text)
        self.assertEqual(code, 1)
        self.assertTrue({"sensitive_url_parameter", "credential_url"}.issubset({f["category"] for f in report["findings"]}))
        self.assertTrue(all(f["action"] == "block" for f in report["findings"] if f["category"] in guard.SECRET))

    def test_secret_assignment_and_pem(self):
        report, _ = self.scan('api_key = "abcdefghijklmnopqrstuvwxyz"\n-----BEGIN OPENSSH PRIVATE KEY-----')
        self.assertEqual(len(report["findings"]), 2)

    def test_environment_references_are_not_literal_secrets(self):
        text = 'api_key = os.getenv("APP_KEY")\npassword = process.env.APP_PASSWORD\naccess_token = os.environ["APP_TOKEN"]'
        self.assertEqual(self.scan(text)[1], 0)
        self.assertEqual(self.scan('password = "process.env.NOT_A_REFERENCE"')[1], 1)

    def test_contextual_account_details(self):
        report, _ = self.scan("My remaining credits: 125. 我的余额是123元。 Account balance is $200.")
        self.assertGreaterEqual(sum(f["category"] == "account_details" for f in report["findings"]), 2)

    def test_chinese_identity_dictionary_and_unicode_offsets(self):
        config = self.config(rules=[{"id": "identity", "category": "private_identity", "literal": "张三"}])
        report, _ = self.scan("😀 名字张三", config)
        finding = report["findings"][0]
        self.assertEqual((finding["start"], finding["end"]), (4, 6))

    def test_allow_is_exact_category_and_kind_scoped(self):
        config = self.config(allow=[{"category": "email", "literal": "public@example.org", "reason": "public", "kind": "git_metadata"}])
        self.assertEqual(self.scan("public@example.org", config, "git_metadata")[1], 0)
        self.assertEqual(self.scan("public@example.org", config)[1], 1)
        self.assertEqual(self.scan("notpublic@example.org", config, "git_metadata")[1], 1)

    def test_allow_secret_rejected(self):
        with self.assertRaises(guard.GuardError):
            self.config(allow=[{"category": "secret", "literal": "x", "reason": "test"}])

    def test_secret_action_cannot_be_downgraded(self):
        config = self.config(actions={"secret": "review"})
        report, _ = self.scan("password=abcdefghijk", config)
        self.assertEqual(report["findings"][0]["action"], "block")

    def test_invalid_configs(self):
        for obj in ({"unknown": True}, {"rules": [{"id": "a", "category": "x", "pattern": "["}]},
                    {"actions": {"email": "allow"}}, {"max_bytes": True},
                    {"rules": [{"id": "a", "category": "x", "literal": "x", "action": "replace"}]}):
            with self.subTest(obj=obj), self.assertRaises(guard.GuardError):
                self.config(**obj)

    def test_zero_width_rule_fails(self):
        config = self.config(rules=[{"id": "zero", "category": "x", "pattern": "^"}])
        with self.assertRaises(guard.GuardError):
            self.scan("x", config)

    def test_checksum_validation(self):
        self.assertTrue(guard.luhn("4111 1111 1111 1111"))
        self.assertFalse(guard.luhn("4111 1111 1111 1112"))
        self.assertFalse(guard.valid_ssn("000-12-3456"))
        self.assertFalse(guard.valid_ip("999.1.2.3"))

    def test_frontmatter_code_blocks_and_filename_scanned(self):
        path = self.file('---\ncontact: person@example.net\n---\n```text\npassword=actualpassword\n```', "private@example.net.md")
        report, code = self.cli("scan", "--path", str(path))
        self.assertEqual(code, 1)
        self.assertEqual({f["category"] for f in report["findings"]}, {"email", "secret"})
        self.assertTrue(any(s["kind"] == "filename" for s in report["sources"]))
        self.assertNotIn(str(path), json.dumps(report))

    def test_show_paths_opt_in(self):
        path = self.file("hello")
        report, _ = self.cli("scan", "--path", str(path), "--show-paths")
        self.assertIn(str(path), json.dumps(report))

    def test_show_paths_does_not_change_finding_ids(self):
        path = self.file("private@example.net")
        a, _ = self.cli("scan", "--path", str(path))
        b, _ = self.cli("scan", "--path", str(path), "--show-paths")
        self.assertEqual(a["findings"][0]["id"], b["findings"][0]["id"])

    def test_only_publishable_filename_not_host_prefix_scanned(self):
        scanner = guard.Scanner(guard.load_config())
        scanner.file(self.content / "missing.md", "article.md")
        self.assertFalse(scanner.report["findings"])

    def test_binary_symlink_and_lfs_incomplete(self):
        (self.content / "image.png").write_bytes(b"text")
        (self.content / "link").symlink_to(self.content / "image.png")
        self.file("version https://git-lfs.github.com/spec/v1\noid sha256:abc\n", "pointer")
        report, code = self.cli("scan", "--path", str(self.content))
        self.assertEqual(code, 2)
        self.assertFalse(report["coverage"]["complete"])
        self.assertEqual({i["code"] for i in report["issues"]},
                         {"unsupported_binary_format", "unsupported_file_type", "external_lfs_object"})

    def test_non_utf8_nul_and_limit(self):
        for data, config, issue in [(b"\xff", guard.load_config(), "non_utf8_input"),
                                    (b"a\0b", guard.load_config(), "binary_input"),
                                    (b"abc", self.config(max_bytes=2), "oversize_input")]:
            s = guard.Scanner(config)
            s.scan_bytes(data, "stdin", "stdin")
            self.assertEqual(s.result()[1], 2)
            self.assertEqual(s.report["issues"][0]["code"], issue)

    def test_private_config_not_in_content(self):
        private = self.content / "identity.json"
        private.write_text('{"version":1}')
        report, code = self.cli("scan", "--path", str(self.content), "--private", str(private))
        self.assertEqual(code, 2)
        self.assertEqual(report["code"], "private_profile_inside_content")

    def test_invalid_modes(self):
        for args in [("scan",), ("scan", "--stdin", "--staged"), ("apply", "--stdin"),
                     ("scan", "--stdin", "--base", "HEAD"), ("scan", "--stdin", "--approve", "abc"),
                     ("scan", "--staged", "--json")]:
            self.assertEqual(self.cli(*args)[1], 2)

    def test_invalid_arguments_do_not_echo_sensitive_values(self):
        report, code = self.cli("scan", "--stdin", "private@example.net")
        self.assertEqual(code, 2)
        self.assertEqual(report["code"], "invalid_arguments")
        self.assertNotIn("private@example.net", json.dumps(report))

    def test_duplicate_json_keys_and_nonfinite_numbers_rejected(self):
        for text in ['{"body":"private","body":"clean"}', '{"value":NaN}']:
            scanner = guard.Scanner(guard.load_config(), json_payload=True)
            scanner.scan_bytes(text.encode(), "stdin", "stdin")
            self.assertEqual(scanner.result()[1], 2)

    def test_json_payload_decodes_escapes_and_contextual_fields(self):
        config = self.config(rules=[{"id": "identity", "category": "private_identity", "literal": "张三"}])
        scanner = guard.Scanner(config, "forum", json_payload=True)
        payload = json.dumps({"title": "张三", "body": "text", "balance": 123})
        scanner.scan_bytes(payload.encode(), "stdin", "stdin")
        report, code = scanner.result()
        self.assertEqual(code, 1)
        self.assertTrue({"private_identity", "account_details"}.issubset({f["category"] for f in report["findings"]}))
        self.assertNotIn("张三", json.dumps(report))
        self.assertTrue(any(s["kind"] == "json_field" for s in report["sources"]))

    def test_invalid_json_payload_not_clean(self):
        scanner = guard.Scanner(guard.load_config(), json_payload=True)
        scanner.scan_bytes(b"not json", "stdin", "stdin")
        self.assertEqual(scanner.result()[1], 2)

    def replacement_setup(self, text="Private Person\r\n", replacement="Public Author"):
        config = self.config(rules=[{"id": "name", "category": "private_identity", "literal": "Private Person",
                                     "action": "replace", "replacement": replacement}])
        path = self.file(text)
        report, _ = self.cli("scan", "--path", str(path), "--policy", str(self.root / "policy.json"))
        ids = [f["id"] for f in report["findings"]]
        args = ["apply", "--path", str(path), "--policy", str(self.root / "policy.json"),
                "--expect-sha256", hashlib.sha256(path.read_bytes()).hexdigest()]
        return path, config, args, ids

    def test_approved_application_preserves_crlf_and_mode(self):
        path, config, args, ids = self.replacement_setup()
        path.chmod(0o640)
        for ident in ids:
            args += ["--approve", ident]
        report, code = self.cli(*args)
        self.assertEqual(code, 0)
        self.assertEqual(report["applied"], 1)
        self.assertEqual(path.read_bytes(), b"Public Author\r\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.scan(path.read_text(), config)[1], 0)
        self.assertFalse(list(self.content.glob(".privacy-guard-*")))

    def test_missing_approval_stale_content_and_stale_policy(self):
        path, _, args, ids = self.replacement_setup()
        self.assertEqual(self.cli(*args)[1], 2)
        self.config(rules=[{"id": "name", "category": "private_identity", "literal": "Private Person", "action": "replace", "replacement": "Other Author"}])
        self.assertEqual(self.cli(*args, "--approve", ids[0])[1], 2)
        path.write_text("changed")
        self.assertEqual(self.cli(*args, "--approve", ids[0])[0]["code"], "stale_content")

    def test_replacement_must_rescan_clean(self):
        path, _, args, ids = self.replacement_setup(replacement="private@example.net")
        report, code = self.cli(*args, "--approve", ids[0])
        self.assertEqual(code, 2)
        self.assertEqual(report["code"], "candidate_not_clean")
        self.assertIn("Private Person", path.read_text())

    def test_overlapping_replacements_need_manual_edit(self):
        self.config(rules=[{"id": "whole", "category": "x", "literal": "Private Person", "action": "replace", "replacement": "Public"},
                           {"id": "part", "category": "x", "literal": "Person", "action": "replace", "replacement": "Author"}])
        path = self.file("Private Person")
        policy = str(self.root / "policy.json")
        report, _ = self.cli("scan", "--path", str(path), "--policy", policy)
        args = ["apply", "--path", str(path), "--policy", policy, "--expect-sha256", guard.digest(path.read_bytes())]
        for f in report["findings"]:
            args += ["--approve", f["id"]]
        result, code = self.cli(*args)
        self.assertEqual(code, 2)
        self.assertEqual(result["code"], "overlapping_replacements")
        self.assertEqual(path.read_text(), "Private Person")

    def test_private_path_rule_resolves_contained_builtin(self):
        config = self.config(rules=[{"id": "home", "category": "private_identity", "literal": "/home/EXAMPLE_USER/", "action": "replace", "replacement": "/path/to/"}])
        report, _ = self.scan("/home/EXAMPLE_USER/project", config)
        self.assertEqual(len(report["findings"]), 1)
        self.assertTrue(report["findings"][0]["replaceable"])

    def test_replacement_never_suppresses_secret(self):
        config = self.config(rules=[{"id": "whole", "category": "private_identity", "literal": "password=supersecret", "action": "replace", "replacement": "omitted"}])
        report, _ = self.scan("password=supersecret", config)
        self.assertIn("block", {f["action"] for f in report["findings"]})

    def test_json_replacement_syntax_failure_is_non_destructive(self):
        path, _, args, ids = self.replacement_setup(text='{"name":"Private Person"}', replacement='"')
        jsonpath = path.with_suffix(".json")
        path.rename(jsonpath)
        args[2] = str(jsonpath)
        report, _ = self.cli("scan", "--path", str(jsonpath), "--policy", str(self.root / "policy.json"))
        self.assertEqual(self.cli(*args, "--approve", report["findings"][0]["id"])[1], 2)
        self.assertEqual(json.loads(jsonpath.read_text())["name"], "Private Person")

    def detector_config(self, output, status=0):
        script = self.root / "detector.py"
        script.write_text("import sys\nsys.stdin.read()\nprint(" + repr(json.dumps(output)) + ")\nsys.exit(" + str(status) + ")\n")
        return self.config(ner={"command": [sys.executable, str(script)],
                               "artifacts": {str(script): hashlib.sha256(script.read_bytes()).hexdigest()}})

    def test_detector_protocol_and_pinned_assets(self):
        config = self.detector_config([{"start": 2, "end": 4, "label": "GIVEN_NAME", "score": 0.9}])
        guard.verify_artifacts(config)
        report, _ = self.scan("😀 张三", config)
        self.assertTrue(report["coverage"]["ner"])
        self.assertEqual(report["findings"][0]["category"], "ner_given_name")
        (self.root / "detector.py").write_text("changed")
        with self.assertRaises(guard.GuardError):
            guard.verify_artifacts(config)

    def test_detector_failure_and_bad_spans_fail_closed(self):
        for output, status in [([], 1), ([{"start": 0, "end": 500, "label": "NAME"}], 0),
                               ([{"start": False, "end": 1, "label": "NAME"}], 0),
                               ([{"start": 0, "end": 1, "label": "NAME", "score": float("nan")}], 0)]:
            with self.subTest(output=output), self.assertRaises(guard.GuardError):
                self.scan("x", self.detector_config(output, status))

    def test_external_secret_detector_still_blocks(self):
        config = self.detector_config([{"start": 0, "end": 3, "label": "SECRET"}])
        report, _ = self.scan("xyz", config)
        self.assertEqual(report["findings"][0]["action"], "block")

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_bridge_utf16_offsets(self):
        bridge = SCRIPT.with_name("rampart_bridge.mjs")
        code = f"import {{ codePointOffset }} from {json.dumps(bridge.as_uri())}; console.log(codePointOffset('😀张三', 2)); try {{ codePointOffset('😀', 1); process.exit(1); }} catch {{}}"
        result = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), b"1")

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_bridge_protocol_with_mock_modules(self):
        # This tests integration, not actual model inference.
        transformers = self.root / "transformers.mjs"
        transformers.write_text("export const env = {};")
        rampart = self.root / "rampart.mjs"
        rampart.write_text(f"""import {{ env }} from {json.dumps(transformers.as_uri())};
export function detectHeuristics() {{ return []; }}
export function premask(text) {{ return {{ masked: text }}; }}
export function projectMaskedSpan(span) {{ return span; }}
export async function loadNerClassifier(options) {{
  if (env.allowRemoteModels !== false || options.device !== 'cpu') throw Error('offline required');
  return null;
}}
export async function detectNer() {{ return [{{ start: 2, end: 4, label: 'SURNAME', score: 0.9 }}]; }}
""")
        result = subprocess.run(["node", str(SCRIPT.with_name("rampart_bridge.mjs")), str(rampart),
                                 str(transformers), str(self.root)], input=json.dumps({"text": "😀张三"}).encode(), capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), [{"start": 1, "end": 3, "label": "SURNAME", "score": 0.9}])


@unittest.skipUnless(shutil.which("git"), "Git unavailable")
class GitTests(FixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.content
        self.run_git("init", "-q")
        self.run_git("config", "user.name", "Synthetic Author")
        self.run_git("config", "user.email", "public@example.org")
        self.policy = self.config(allow=[{"category": "email", "literal": "public@example.org", "reason": "public author", "kind": "git_metadata"}])

    def run_git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True).stdout

    def git_scan(self, **kwargs):
        scanner = guard.Scanner(self.policy)
        scanner.git_scan(self.repo, **kwargs)
        return scanner.result()

    def test_staged_not_worktree(self):
        path = self.file("private@example.net")
        self.run_git("add", "article.md")
        path.write_text("clean now")
        self.assertEqual(self.git_scan(staged=True)[1], 1)
        self.assertEqual(self.cli("scan", "--path", str(path))[1], 0)

    def test_staged_from_subdirectory_includes_root_files(self):
        self.file("private@example.net")
        subdir = self.repo / "nested"
        subdir.mkdir()
        (subdir / "clean.md").write_text("clean")
        self.run_git("add", ".")
        scanner = guard.Scanner(self.policy)
        scanner.git_scan(subdir, staged=True)
        self.assertEqual(scanner.result()[1], 1)

    def test_old_deleted_blob_and_commit_message_checked(self):
        path = self.file("private@example.net")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "first")
        path.unlink()
        self.file("clean", "clean.md")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "contact another@example.net")
        report, code = self.git_scan()
        self.assertEqual(code, 1)
        kinds = {s["kind"] for s in report["sources"]}
        self.assertIn("git_metadata", kinds)
        self.assertIn("git_blob", kinds)
        self.assertEqual(sum(f["category"] == "email" for f in report["findings"]), 2)

    def test_explicit_base_and_multiple_refs(self):
        self.file("old@example.net")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "old")
        base = self.run_git("rev-parse", "HEAD").decode().strip()
        self.run_git("branch", "other")
        self.file("clean")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "new")
        self.assertEqual(self.git_scan(base=base)[1], 0)
        self.assertEqual(self.git_scan(refs=["HEAD", "other"])[1], 1)

    def test_symlink_not_silently_clean(self):
        self.file("clean")
        (self.repo / "link").symlink_to("article.md")
        self.run_git("add", ".")
        report, code = self.git_scan(staged=True)
        self.assertEqual(code, 2)
        self.assertIn("symlink_or_submodule", {i["code"] for i in report["issues"]})

    def test_unmerged_index_not_silently_clean(self):
        self.file("clean")
        self.run_git("add", ".")
        oid = self.run_git("rev-parse", ":article.md").decode().strip()
        subprocess.run(["git", "-C", str(self.repo), "update-index", "--index-info"],
                       input=f"100644 {oid} 1\tconflict.md\n100644 {oid} 2\tconflict.md\n".encode(),
                       check=True, capture_output=True)
        report, code = self.git_scan(staged=True)
        self.assertEqual(code, 2)
        self.assertIn("unmerged_index", {i["code"] for i in report["issues"]})

    def test_shallow_history_not_silently_clean(self):
        self.file("clean")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "first")
        (self.repo / ".git" / "shallow").write_bytes(self.run_git("rev-parse", "HEAD"))
        report, code = self.git_scan()
        self.assertEqual(code, 2)
        self.assertIn("shallow_history", {i["code"] for i in report["issues"]})

    def test_annotated_tag_incomplete(self):
        self.file("clean")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "clean")
        self.run_git("tag", "-am", "private@example.net", "release")
        report, code = self.git_scan(refs=["release"])
        self.assertEqual(code, 2)
        self.assertIn("annotated_tag_uninspected", {i["code"] for i in report["issues"]})


if __name__ == "__main__":
    unittest.main()
