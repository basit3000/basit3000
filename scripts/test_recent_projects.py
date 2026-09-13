import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import update_recent_projects as updater


def repo(name="project", date="2026-09-01T12:00:00Z", **changes):
    return dict(name=name, pushed_at=date, private=False, fork=False,
                archived=False, language="Python", owner={"login": "basit3000"}) | changes


class RecentProjectsTests(unittest.TestCase):
    def test_filters_private_archived_forks_self_and_other_owners(self):
        candidates = [repo("public"), repo("secret", private=True),
                      repo("archived", archived=True), repo("fork", fork=True),
                      repo("basit3000"), repo("foreign", owner={"login": "other"}),
                      repo("unknown", private=None)]
        result = updater.render_projects(candidates)
        self.assertIn("[public]", result)
        self.assertEqual(len(result.splitlines()), 1)

    def test_three_most_recent_sorted_by_push_time(self):
        result = updater.render_projects([
            repo("old", "2025-01-01T00:00:00Z"), repo("second"),
            repo("newest", "2026-09-12T00:00:00Z"),
            repo("third", "2026-08-01T00:00:00Z")])
        self.assertEqual(len(result.splitlines()), 3)
        self.assertIn("[newest]", result.splitlines()[0])
        self.assertIn("[second]", result.splitlines()[1])
        self.assertNotIn("[old]", result)

    def test_text_is_escaped_and_links_use_trusted_origin(self):
        result = updater.render_projects([repo("safe_name", language="<b>[Click](bad)\n*",
                                               html_url="https://evil.example")])
        self.assertNotIn("<b>", result)
        self.assertNotIn("evil.example", result)
        self.assertIn("https://github.com/basit3000/safe_name", result)
        self.assertIn(r"\[Click\]", result)
        self.assertEqual(len(result.splitlines()), 1)

    def test_empty_and_missing_language_or_push(self):
        self.assertIn("Browse", updater.render_projects([]))
        self.assertIn("Browse", updater.render_projects([repo(pushed_at=None)]))
        self.assertNotIn("None", updater.render_projects([repo(language=None)]))

    def test_markers_preserve_surrounding_content(self):
        before, after = "Personal intro\n\n", "\n\nPersonal footer\n"
        original = before + updater.START + "\nold\n" + updater.END + after
        updated = updater.replace_section(original, "new")
        self.assertEqual(updated, before + updater.START + "\nnew\n" + updater.END + after)

    def test_missing_duplicate_and_reversed_markers_rejected(self):
        for original in ["none", updater.START, updater.START * 2 + updater.END,
                         updater.END + updater.START]:
            with self.subTest(original=original), self.assertRaises(ValueError):
                updater.replace_section(original, "new")

    def test_paginates_public_api(self):
        responses = [io.BytesIO(json.dumps([repo()] * 100).encode()),
                     io.BytesIO(json.dumps([repo("last")]).encode())]
        with patch.object(updater.urllib.request, "urlopen", side_effect=responses) as fetch:
            self.assertEqual(len(updater.fetch_repositories()), 101)
            self.assertIn("page=2", fetch.call_args.args[0].full_url)

    def test_failure_preserves_file_and_success_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            original = f"intro\r\n{updater.START}\r\nold\r\n{updater.END}\r\nfooter\r\n".encode()
            path.write_bytes(original)
            with patch.object(updater, "fetch_repositories", side_effect=URLError("offline")):
                with self.assertRaises(URLError):
                    updater.update_readme(path)
            self.assertEqual(path.read_bytes(), original)
            with patch.object(updater, "fetch_repositories", return_value=[repo()]):
                self.assertTrue(updater.update_readme(path))
                self.assertFalse(updater.update_readme(path))
            self.assertTrue(path.read_bytes().endswith(b"\r\nfooter\r\n"))

    def test_bad_date_preserves_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            original = f"{updater.START}\nold\n{updater.END}"
            path.write_text(original, encoding="utf-8")
            with patch.object(updater, "fetch_repositories", return_value=[repo(date="bad")]):
                with self.assertRaises(ValueError):
                    updater.update_readme(path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
