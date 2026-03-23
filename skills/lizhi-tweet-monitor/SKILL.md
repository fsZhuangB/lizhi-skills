# lizhi-tweet-monitor

Monitor specified X/Twitter users' latest tweets via RSSHub.

## Trigger

When the user asks to check tweets, monitor a Twitter/X user, or uses `/lizhi-tweet-monitor`.

## Instructions

1. Run the fetch script to check for new tweets:
   ```bash
   python3 skills/lizhi-tweet-monitor/scripts/fetch_tweets.py
   ```

2. If new tweets are found, present them clearly to the user:
   - Show the author (@handle), time, and tweet content
   - Include any links contained in the tweet
   - Summarize long threads briefly

3. If no new tweets are found, report "没有新推文" (no new tweets since last check).

## Managing Monitored Users

- Add a user: `python3 skills/lizhi-tweet-monitor/scripts/fetch_tweets.py --add <twitter_id>`
- Remove a user: `python3 skills/lizhi-tweet-monitor/scripts/fetch_tweets.py --remove <twitter_id>`
- List monitored users: `python3 skills/lizhi-tweet-monitor/scripts/fetch_tweets.py --list`
- Reset state (treat all tweets as new on next check): `python3 skills/lizhi-tweet-monitor/scripts/fetch_tweets.py --reset`

## Scheduled Monitoring

Use with `/loop` for periodic checks:
```
/loop 10m /lizhi-tweet-monitor
```

## Configuration

- **User list**: `~/.lizhi-skills/tweet-monitor/users.json` (default: `["dotey"]`)
- **State file**: `~/.lizhi-skills/tweet-monitor/state.json`
- **RSSHub instance**: defaults to `https://rsshub.app`; set env var `RSSHUB_BASE_URL` to override with a self-hosted instance

## Dependencies

- Python 3.8+
- No third-party packages required (stdlib only: `urllib`, `xml.etree.ElementTree`, `json`, `argparse`)
