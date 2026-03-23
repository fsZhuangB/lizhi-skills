#!/usr/bin/env python3
"""
Monitor X/Twitter users' latest tweets via RSSHub RSS feeds.

Usage:
    python3 fetch_tweets.py              # Check all monitored users for new tweets
    python3 fetch_tweets.py --add <id>   # Add a user to monitor
    python3 fetch_tweets.py --remove <id># Remove a user
    python3 fetch_tweets.py --list       # List all monitored users
    python3 fetch_tweets.py --reset      # Clear state, treat all as new next check
"""

import argparse
import json
import os
import sys
import html
import re
import tempfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request
from xml.etree import ElementTree

CONFIG_DIR = Path.home() / ".lizhi-skills" / "tweet-monitor"
USERS_FILE = CONFIG_DIR / "users.json"
STATE_FILE = CONFIG_DIR / "state.json"
DEFAULT_RSSHUB_BASE = "https://rsshub.app"
DEFAULT_USERS = ["dotey"]
REQUEST_TIMEOUT = 30


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_users():
    ensure_config_dir()
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
            if isinstance(users, list):
                return users
        except (json.JSONDecodeError, IOError):
            pass
    # Initialize with defaults
    save_users(DEFAULT_USERS)
    return list(DEFAULT_USERS)


def _atomic_write(filepath, data):
    """Write JSON data to a file atomically using a temp file + os.replace."""
    ensure_config_dir()
    tmp_fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def save_users(users):
    _atomic_write(USERS_FILE, users)


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_state(state):
    _atomic_write(STATE_FILE, state)


def strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return text.strip()


def extract_links(text):
    """Extract URLs from text."""
    return re.findall(r"https?://[^\s<>\"']+", text)


def fetch_rss(twitter_id):
    """Fetch and parse RSS feed for a Twitter user from RSSHub."""
    base_url = os.environ.get("RSSHUB_BASE_URL", DEFAULT_RSSHUB_BASE).rstrip("/")
    url = f"{base_url}/twitter/user/{twitter_id}"

    req = Request(url, headers={"User-Agent": "lizhi-tweet-monitor/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()
    except URLError as e:
        print(f"  [错误] 无法获取 @{twitter_id} 的推文: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [错误] 请求 @{twitter_id} 时发生异常: {e}", file=sys.stderr)
        return None

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as e:
        print(f"  [错误] 解析 @{twitter_id} 的 RSS 数据失败: {e}", file=sys.stderr)
        return None

    items = []
    for item in root.iter("item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")
        guid_el = item.find("guid")

        title = title_el.text if title_el is not None and title_el.text else ""
        raw_desc = desc_el.text if desc_el is not None and desc_el.text else ""
        link = link_el.text if link_el is not None and link_el.text else ""
        pub_date = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""
        guid = guid_el.text if guid_el is not None and guid_el.text else link

        content = strip_html(raw_desc) if raw_desc else title
        links = extract_links(raw_desc) if raw_desc else []
        # Ensure the tweet link itself is included
        if link and link not in links:
            links.insert(0, link)

        parsed_date = None
        if pub_date:
            try:
                parsed_date = parsedate_to_datetime(pub_date)
            except (ValueError, TypeError):
                pass

        items.append({
            "guid": guid,
            "title": title,
            "content": content,
            "link": link,
            "links": links,
            "pub_date": pub_date,
            "parsed_date": parsed_date,
        })

    return items


def check_tweets():
    """Check all monitored users for new tweets."""
    users = load_users()
    if not users:
        print("没有监控的用户。使用 --add <twitter_id> 添加用户。")
        return

    state = load_state()
    any_new = False

    for twitter_id in users:
        print(f"正在检查 @{twitter_id} ...")
        items = fetch_rss(twitter_id)
        if items is None:
            continue
        if not items:
            print(f"  @{twitter_id}: 未获取到任何推文。")
            continue

        is_first_check = twitter_id not in state or not state.get(twitter_id, {}).get("seen_guids")

        if is_first_check:
            # First run: show all existing tweets so user can see what they look like
            new_items = items
            print(f"\n  @{twitter_id}: 首次监控，展示最近 {len(items)} 条推文：")
        else:
            seen_guids = set(state[twitter_id].get("seen_guids", []))
            new_items = [item for item in items if item["guid"] not in seen_guids]

        if not new_items:
            print(f"  @{twitter_id}: 没有新推文。")
            continue

        any_new = True
        print(f"\n{'='*60}")
        print(f"  @{twitter_id} 有 {len(new_items)} 条新推文:")
        print(f"{'='*60}")

        for item in new_items:
            print(f"\n--- 推文 ---")
            print(f"作者: @{twitter_id}")
            if item["pub_date"]:
                if item["parsed_date"]:
                    display_time = item["parsed_date"].strftime("%Y-%m-%d %H:%M:%S %Z")
                else:
                    display_time = item["pub_date"]
                print(f"时间: {display_time}")
            print(f"内容:\n{item['content']}")
            if item["links"]:
                print("链接:")
                for link in item["links"]:
                    print(f"  - {link}")
            print()

        # Update state: store all current guids
        all_guids = [item["guid"] for item in items]
        if twitter_id not in state:
            state[twitter_id] = {}
        state[twitter_id]["seen_guids"] = all_guids
        state[twitter_id]["last_check"] = datetime.now(timezone.utc).isoformat()

    if not any_new:
        print("\n所有监控用户均无新推文。")

    save_state(state)


TWITTER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,15}$")


def validate_twitter_id(twitter_id):
    """Validate that a twitter_id looks like a real Twitter handle."""
    if not TWITTER_ID_PATTERN.match(twitter_id):
        print(f"无效的 Twitter ID: {twitter_id} (只允许字母、数字、下划线，最长15位)", file=sys.stderr)
        return False
    return True


def add_user(twitter_id):
    """Add a user to the monitoring list."""
    if not validate_twitter_id(twitter_id):
        return
    users = load_users()
    if twitter_id in users:
        print(f"@{twitter_id} 已在监控列表中。")
        return
    users.append(twitter_id)
    save_users(users)
    print(f"已添加 @{twitter_id} 到监控列表。")


def remove_user(twitter_id):
    """Remove a user from the monitoring list."""
    if not validate_twitter_id(twitter_id):
        return
    users = load_users()
    if twitter_id not in users:
        print(f"@{twitter_id} 不在监控列表中。")
        return
    users.remove(twitter_id)
    save_users(users)
    # Also remove from state
    state = load_state()
    if twitter_id in state:
        del state[twitter_id]
        save_state(state)
    print(f"已从监控列表中移除 @{twitter_id}。")


def list_users():
    """List all monitored users."""
    users = load_users()
    if not users:
        print("监控列表为空。使用 --add <twitter_id> 添加用户。")
        return
    print(f"当前监控 {len(users)} 个用户:")
    state = load_state()
    for uid in users:
        last_check = state.get(uid, {}).get("last_check", "从未检查")
        seen_count = len(state.get(uid, {}).get("seen_guids", []))
        print(f"  - @{uid} (已记录 {seen_count} 条推文, 上次检查: {last_check})")


def reset_state():
    """Clear all state, so next check treats all tweets as new."""
    save_state({})
    print("已清除所有状态。下次检查时所有推文将被视为新推文。")


def main():
    parser = argparse.ArgumentParser(
        description="监控 X/Twitter 用户的最新推文 (通过 RSSHub)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--add", metavar="TWITTER_ID", help="添加要监控的用户")
    group.add_argument("--remove", metavar="TWITTER_ID", help="移除监控的用户")
    group.add_argument("--list", action="store_true", help="列出所有监控的用户")
    group.add_argument("--reset", action="store_true", help="清除状态，下次检查时所有推文视为新推文")

    args = parser.parse_args()

    if args.add:
        add_user(args.add)
    elif args.remove:
        remove_user(args.remove)
    elif args.list:
        list_users()
    elif args.reset:
        reset_state()
    else:
        check_tweets()


if __name__ == "__main__":
    main()
