"""
integrations/slack_bot.py
─────────────────────────────────────────────────────────────────────────────
Slack Integration
Formats the weekly digest report into a beautiful Slack Block Kit payload.
Saves to `slack_payload.json` for live UI previews and prints to console.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import requests

DIGEST_PATH = "weekly_digest.json"
SLACK_PAYLOAD_PATH = "slack_payload.json"

def format_slack_blocks(digest_data: dict) -> dict:
    """Format weekly digest report into a structured Slack Block Kit message."""
    date_range = digest_data.get("report_date_range", "Weekly Report")
    total_reviews = digest_data.get("total_reviews_analyzed", 0)
    avg_urgency = digest_data.get("average_urgency", 0.0)
    rising = digest_data.get("top_rising_theme", {})
    urgency_issue = digest_data.get("top_urgency_issue", {})
    unmet = digest_data.get("new_unmet_need", "None detected")
    competitors = digest_data.get("competitive_signals", {})
    
    comp_list = [f"{comp.replace('_', ' ').title()}: {count} mention(s)" for comp, count in competitors.items()]
    comp_str = ", ".join(comp_list) if comp_list else "None detected"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Spotify Review Intelligence Weekly Summary",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 *{date_range}*  |  👥 *{total_reviews} reviews analyzed*  |  ⚠️ *Avg Urgency: {avg_urgency}/5.0*"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📈 *Top Rising Theme:*\n`{rising.get('theme')}` ▲ *{rising.get('wow_increase_percent')}% WoW*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔥 *Top Urgency Issue:*\n`{urgency_issue.get('theme')}` — Urgency *{urgency_issue.get('urgency')}/5.0*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *New Unmet Need / Feature Request:*\n\"{unmet}\""
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚔️ *Competitive Mentions:*\n{comp_str}"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Full Dashboard ➔",
                        "emoji": True
                    },
                    "url": "http://localhost:8000",
                    "action_id": "view_dashboard"
                }
            ]
        }
    ]

    return {"blocks": blocks}

def generate_slack_digest():
    if not os.path.exists(DIGEST_PATH):
        print(f"[-] Weekly digest {DIGEST_PATH} not found. Run weekly_digest.py first.")
        return None

    with open(DIGEST_PATH, "r", encoding="utf-8") as f:
        digest_data = json.load(f)

    payload = format_slack_blocks(digest_data)

    with open(SLACK_PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if webhook_url:
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                print("[+] Successfully posted weekly digest to Slack webhook.")
            else:
                print(f"[-] Failed to post to Slack: status {resp.status_code}")
        except Exception as exc:
            print(f"[-] Error dispatching Slack webhook: {exc}")
    else:
        print("[*] No SLACK_WEBHOOK_URL configured. Payload saved to slack_payload.json for preview.")

    # Ensure stdout uses UTF-8 or replace unprintable chars
    import sys
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("\n======================================================")
    print("           SLACK BLOCK KIT PREVIEW GENERATED")
    print("======================================================")
    for block in payload["blocks"]:
        if block["type"] == "header":
            print(f"HEADER: {block['text']['text']}")
        elif block["type"] == "context":
            print(f"CONTEXT: {block['elements'][0]['text']}")
        elif block["type"] == "section":
            print(f"SECTION: {block['text']['text']}")
    print("======================================================")

    return payload

if __name__ == "__main__":
    generate_slack_digest()
