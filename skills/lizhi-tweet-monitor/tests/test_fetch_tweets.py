#!/usr/bin/env python3
"""
Tests for lizhi-tweet-monitor/scripts/fetch_tweets.py

Uses only Python stdlib (unittest). No third-party packages needed.
All tests use temp directories, no real network requests or user config affected.

Run:
    python3 -m pytest tests/                          # if pytest installed
    python3 -m unittest tests/test_fetch_tweets.py    # stdlib only
    python3 tests/test_fetch_tweets.py                # direct run
"""

import json
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add scripts/ to path so we can import fetch_tweets
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_tweets


# Sample RSS XML for testing (simulates RSSHub response)
SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>dotey's Twitter</title>
    <link>https://x.com/dotey</link>
    <description>Twitter feed for @dotey</description>
    <item>
      <title>First tweet from dotey</title>
      <description>&lt;p&gt;Hello world! Check out &lt;a href="https://example.com"&gt;this link&lt;/a&gt;&lt;/p&gt;</description>
      <link>https://x.com/dotey/status/111</link>
      <guid>https://x.com/dotey/status/111</guid>
      <pubDate>Mon, 23 Mar 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Second tweet from dotey</title>
      <description>&lt;p&gt;This is another tweet &amp;amp; it has entities&lt;/p&gt;</description>
      <link>https://x.com/dotey/status/222</link>
      <guid>https://x.com/dotey/status/222</guid>
      <pubDate>Mon, 23 Mar 2026 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_RSS_NEW_TWEET = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>dotey's Twitter</title>
    <item>
      <title>Brand new tweet!</title>
      <description>&lt;p&gt;This is a brand new tweet&lt;/p&gt;</description>
      <link>https://x.com/dotey/status/333</link>
      <guid>https://x.com/dotey/status/333</guid>
      <pubDate>Mon, 23 Mar 2026 12:00:00 +0000</pubDate>
    </item>
    <item>
      <title>First tweet from dotey</title>
      <description>&lt;p&gt;Hello world!&lt;/p&gt;</description>
      <link>https://x.com/dotey/status/111</link>
      <guid>https://x.com/dotey/status/111</guid>
      <pubDate>Mon, 23 Mar 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

EMPTY_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty feed</title>
  </channel>
</rss>
"""


class TempConfigMixin:
    """Mixin to redirect config/state files to a temp directory for testing."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.orig_config_dir = fetch_tweets.CONFIG_DIR
        self.orig_users_file = fetch_tweets.USERS_FILE
        self.orig_state_file = fetch_tweets.STATE_FILE

        fetch_tweets.CONFIG_DIR = self.tmp_dir
        fetch_tweets.USERS_FILE = self.tmp_dir / "users.json"
        fetch_tweets.STATE_FILE = self.tmp_dir / "state.json"

    def tearDown(self):
        fetch_tweets.CONFIG_DIR = self.orig_config_dir
        fetch_tweets.USERS_FILE = self.orig_users_file
        fetch_tweets.STATE_FILE = self.orig_state_file
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestStripHtml(unittest.TestCase):
    """Test HTML stripping and entity decoding."""

    def test_simple_tags(self):
        self.assertEqual(fetch_tweets.strip_html("<p>hello</p>"), "hello")

    def test_br_tags(self):
        result = fetch_tweets.strip_html("line1<br/>line2<BR>line3")
        self.assertEqual(result, "line1\nline2\nline3")

    def test_entities(self):
        self.assertEqual(fetch_tweets.strip_html("a &amp; b &lt; c"), "a & b < c")

    def test_nested_tags(self):
        self.assertEqual(
            fetch_tweets.strip_html('<a href="url"><b>text</b></a>'),
            "text",
        )

    def test_empty_string(self):
        self.assertEqual(fetch_tweets.strip_html(""), "")


class TestExtractLinks(unittest.TestCase):
    """Test URL extraction from text."""

    def test_single_link(self):
        links = fetch_tweets.extract_links('visit <a href="https://example.com">here</a>')
        self.assertEqual(links, ["https://example.com"])

    def test_multiple_links(self):
        text = "https://a.com and http://b.com/path?q=1"
        links = fetch_tweets.extract_links(text)
        self.assertEqual(len(links), 2)

    def test_no_links(self):
        self.assertEqual(fetch_tweets.extract_links("no links here"), [])


class TestValidateTwitterId(unittest.TestCase):
    """Test Twitter ID validation."""

    def test_valid_ids(self):
        self.assertTrue(fetch_tweets.validate_twitter_id("dotey"))
        self.assertTrue(fetch_tweets.validate_twitter_id("elonmusk"))
        self.assertTrue(fetch_tweets.validate_twitter_id("user_123"))
        self.assertTrue(fetch_tweets.validate_twitter_id("A"))

    def test_invalid_ids(self):
        self.assertFalse(fetch_tweets.validate_twitter_id(""))
        self.assertFalse(fetch_tweets.validate_twitter_id("a" * 16))  # too long
        self.assertFalse(fetch_tweets.validate_twitter_id("user name"))  # space
        self.assertFalse(fetch_tweets.validate_twitter_id("user@name"))  # special char
        self.assertFalse(fetch_tweets.validate_twitter_id("用户"))  # non-ASCII


class TestUserManagement(TempConfigMixin, unittest.TestCase):
    """Test add/remove/list user operations."""

    def test_load_default_users(self):
        users = fetch_tweets.load_users()
        self.assertEqual(users, ["dotey"])
        # Should have created the file
        self.assertTrue(fetch_tweets.USERS_FILE.exists())

    def test_add_user(self):
        fetch_tweets.load_users()  # init defaults
        fetch_tweets.add_user("elonmusk")
        users = fetch_tweets.load_users()
        self.assertIn("elonmusk", users)
        self.assertIn("dotey", users)

    def test_add_duplicate_user(self):
        fetch_tweets.load_users()  # init defaults
        fetch_tweets.add_user("dotey")  # already exists
        users = fetch_tweets.load_users()
        self.assertEqual(users.count("dotey"), 1)

    def test_remove_user(self):
        fetch_tweets.load_users()
        fetch_tweets.add_user("testuser")
        fetch_tweets.remove_user("testuser")
        users = fetch_tweets.load_users()
        self.assertNotIn("testuser", users)

    def test_remove_nonexistent_user(self):
        fetch_tweets.load_users()
        fetch_tweets.remove_user("nobody")  # should not raise
        users = fetch_tweets.load_users()
        self.assertEqual(users, ["dotey"])

    def test_remove_cleans_state(self):
        fetch_tweets.load_users()
        fetch_tweets.add_user("testuser")
        # Write some state for testuser
        state = {"testuser": {"seen_guids": ["123"], "last_check": "2026-01-01"}}
        fetch_tweets.save_state(state)
        fetch_tweets.remove_user("testuser")
        state = fetch_tweets.load_state()
        self.assertNotIn("testuser", state)

    def test_add_invalid_user(self):
        fetch_tweets.load_users()
        fetch_tweets.add_user("invalid user!")
        users = fetch_tweets.load_users()
        self.assertNotIn("invalid user!", users)


class TestStateManagement(TempConfigMixin, unittest.TestCase):
    """Test state load/save with atomic writes."""

    def test_empty_state(self):
        state = fetch_tweets.load_state()
        self.assertEqual(state, {})

    def test_save_and_load_state(self):
        data = {"dotey": {"seen_guids": ["111", "222"], "last_check": "2026-03-23T10:00:00"}}
        fetch_tweets.save_state(data)
        loaded = fetch_tweets.load_state()
        self.assertEqual(loaded, data)

    def test_reset_state(self):
        fetch_tweets.save_state({"dotey": {"seen_guids": ["111"]}})
        fetch_tweets.reset_state()
        state = fetch_tweets.load_state()
        self.assertEqual(state, {})

    def test_atomic_write_no_leftover_tmp(self):
        fetch_tweets.save_state({"test": True})
        tmp_files = list(self.tmp_dir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, "No .tmp files should remain after atomic write")

    def test_corrupted_state_file(self):
        with open(fetch_tweets.STATE_FILE, "w") as f:
            f.write("not valid json{{{")
        state = fetch_tweets.load_state()
        self.assertEqual(state, {})


class TestFetchRss(unittest.TestCase):
    """Test RSS fetching and parsing (mocked network)."""

    def _mock_urlopen(self, data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("fetch_tweets.urlopen")
    def test_parse_valid_rss(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        items = fetch_tweets.fetch_rss("dotey")
        self.assertIsNotNone(items)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["guid"], "https://x.com/dotey/status/111")
        self.assertIn("Hello world", items[0]["content"])
        self.assertIn("https://x.com/dotey/status/111", items[0]["links"])

    @patch("fetch_tweets.urlopen")
    def test_parse_empty_rss(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(EMPTY_RSS)
        items = fetch_tweets.fetch_rss("dotey")
        self.assertIsNotNone(items)
        self.assertEqual(len(items), 0)

    @patch("fetch_tweets.urlopen")
    def test_network_error(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")
        items = fetch_tweets.fetch_rss("dotey")
        self.assertIsNone(items)

    @patch("fetch_tweets.urlopen")
    def test_invalid_xml(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(b"not xml at all")
        items = fetch_tweets.fetch_rss("dotey")
        self.assertIsNone(items)

    @patch("fetch_tweets.urlopen")
    def test_html_entities_decoded(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        items = fetch_tweets.fetch_rss("dotey")
        # Second tweet has &amp; which should decode to &
        self.assertIn("& it has entities", items[1]["content"])

    @patch("fetch_tweets.urlopen")
    def test_custom_rsshub_base(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        with patch.dict(os.environ, {"RSSHUB_BASE_URL": "https://my-rsshub.com"}):
            fetch_tweets.fetch_rss("dotey")
        called_url = mock_urlopen.call_args[0][0].full_url
        self.assertTrue(called_url.startswith("https://my-rsshub.com/"))


class TestCheckTweets(TempConfigMixin, unittest.TestCase):
    """Test the main check_tweets flow (mocked network)."""

    def _mock_urlopen(self, data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("fetch_tweets.urlopen")
    def test_first_run_seeds_state(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        fetch_tweets.check_tweets()
        state = fetch_tweets.load_state()
        self.assertIn("dotey", state)
        self.assertEqual(len(state["dotey"]["seen_guids"]), 2)

    @patch("fetch_tweets.urlopen")
    def test_detects_new_tweets(self, mock_urlopen):
        # First run: seed state
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        fetch_tweets.check_tweets()

        # Second run: new tweet appears
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS_NEW_TWEET)
        fetch_tweets.check_tweets()

        state = fetch_tweets.load_state()
        self.assertIn("https://x.com/dotey/status/333", state["dotey"]["seen_guids"])

    @patch("fetch_tweets.urlopen")
    def test_no_new_tweets(self, mock_urlopen):
        # First run
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        fetch_tweets.check_tweets()
        # Second run with same data
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_RSS)
        fetch_tweets.check_tweets()
        # State unchanged
        state = fetch_tweets.load_state()
        self.assertEqual(len(state["dotey"]["seen_guids"]), 2)

    def test_no_users(self):
        fetch_tweets.save_users([])
        fetch_tweets.check_tweets()  # should not raise


if __name__ == "__main__":
    unittest.main()
