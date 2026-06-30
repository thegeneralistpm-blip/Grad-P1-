"""
integrations/email_sender.py
─────────────────────────────────────────────────────────────────────────────
Email Integration Formatter
Compiles the weekly summary metrics into a beautifully styled HTML email.
Saves to `weekly_email_preview.html` for live UI previews.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json

DIGEST_PATH = "weekly_digest.json"
EMAIL_PREVIEW_PATH = "weekly_email_preview.html"

def generate_email_html(digest_data: dict) -> str:
    """Format weekly digest report into standard inline-styled HTML for email client."""
    date_range = digest_data.get("report_date_range", "Weekly Report")
    total_reviews = digest_data.get("total_reviews_analyzed", 0)
    avg_urgency = digest_data.get("average_urgency", 0.0)
    rising = digest_data.get("top_rising_theme", {})
    urgency_issue = digest_data.get("top_urgency_issue", {})
    unmet = digest_data.get("new_unmet_need", "None detected")
    competitors = digest_data.get("competitive_signals", {})
    
    comp_list = [f"<li><strong>{comp.replace('_', ' ').title()}:</strong> {count} mention(s)</li>" for comp, count in competitors.items()]
    comp_html = "\n".join(comp_list) if comp_list else "<li>No competitor mentions.</li>"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Spotify Review Intelligence Weekly Report</title>
</head>
<body style="margin: 0; padding: 0; background-color: #121212; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #E0E0E0;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #121212; padding: 40px 10px;">
        <tr>
            <td align="center">
                <!-- Outer Container -->
                <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #1E1E1E; border-radius: 8px; border: 1px solid #292929; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1DB954, #1aa34a); padding: 30px; text-align: center;">
                            <h1 style="margin: 0; color: #FFFFFF; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">📊 Spotify Review Discovery Engine</h1>
                            <p style="margin: 5px 0 0 0; color: #E2FFE9; font-size: 14px; font-weight: 500;">Weekly Insights Summary Report</p>
                        </td>
                    </tr>
                    <!-- Meta Content -->
                    <tr>
                        <td style="padding: 20px 30px 10px 30px; border-bottom: 1px solid #292929;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="color: #B3B3B3; font-size: 12px;">REPORT PERIOD</td>
                                    <td align="right" style="color: #1DB954; font-size: 13px; font-weight: 600;">{date_range}</td>
                                </tr>
                                <tr>
                                    <td style="color: #B3B3B3; font-size: 12px; padding-top: 5px;">REVIEWS INGESTED</td>
                                    <td align="right" style="color: #FFFFFF; font-size: 13px; font-weight: 600; padding-top: 5px;">{total_reviews} raw signals</td>
                                </tr>
                                <tr>
                                    <td style="color: #B3B3B3; font-size: 12px; padding-top: 5px;">AVG URGENCY SCORE</td>
                                    <td align="right" style="color: #FF5555; font-size: 13px; font-weight: 600; padding-top: 5px;">{avg_urgency} / 5.0 (Elevated)</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Main Body Card Details -->
                    <tr>
                        <td style="padding: 30px;">
                            <!-- Metric 1 -->
                            <div style="margin-bottom: 25px;">
                                <h3 style="margin: 0 0 5px 0; color: #FFFFFF; font-size: 16px; font-weight: 600;">📈 Top Rising Theme</h3>
                                <div style="background-color: #252525; padding: 15px; border-radius: 6px; border-left: 4px solid #1DB954;">
                                    <span style="color: #FFFFFF; font-size: 15px; font-weight: 500;">{rising.get("theme")}</span>
                                    <span style="color: #1DB954; font-size: 14px; font-weight: 700; margin-left: 8px;">▲ {rising.get("wow_increase_percent")}% WoW</span>
                                </div>
                            </div>

                            <!-- Metric 2 -->
                            <div style="margin-bottom: 25px;">
                                <h3 style="margin: 0 0 5px 0; color: #FFFFFF; font-size: 16px; font-weight: 600;">🔥 Top Urgency Issue</h3>
                                <div style="background-color: #252525; padding: 15px; border-radius: 6px; border-left: 4px solid #FF5555;">
                                    <span style="color: #FFFFFF; font-size: 15px; font-weight: 500;">{urgency_issue.get("theme")}</span>
                                    <span style="color: #FF5555; font-size: 14px; font-weight: 700; margin-left: 8px;">Urgency: {urgency_issue.get("urgency")} / 5.0</span>
                                </div>
                            </div>

                            <!-- Metric 3 -->
                            <div style="margin-bottom: 25px;">
                                <h3 style="margin: 0 0 5px 0; color: #FFFFFF; font-size: 16px; font-weight: 600;">💡 New Unmet Need / Feature Request</h3>
                                <div style="background-color: #252525; padding: 15px; border-radius: 6px; color: #B3B3B3; font-size: 14px; font-style: italic;">
                                    "{unmet}"
                                </div>
                            </div>

                            <!-- Metric 4 -->
                            <div style="margin-bottom: 30px;">
                                <h3 style="margin: 0 0 5px 0; color: #FFFFFF; font-size: 16px; font-weight: 600;">⚔️ Competitive Mentions</h3>
                                <ul style="margin: 0; padding-left: 20px; color: #B3B3B3; font-size: 14px; line-height: 1.6;">
                                    {comp_html}
                                </ul>
                            </div>

                            <!-- CTA Button -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <a href="http://localhost:8000" style="display: inline-block; background-color: #1DB954; color: #FFFFFF; font-size: 14px; font-weight: 600; text-decoration: none; padding: 14px 30px; border-radius: 30px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 4px 6px rgba(29, 185, 84, 0.2);">Open RAG Query Engine Dashboard</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #161616; padding: 20px; text-align: center; border-top: 1px solid #252525;">
                            <p style="margin: 0; color: #7F7F7F; font-size: 11px; line-height: 1.4;">
                                You are receiving this automated report because you are in the Spotify Growth PM distribution list.<br>
                                Designed and maintained by Spotify Growth Engineering Team.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return html

def generate_email_preview():
    if not os.path.exists(DIGEST_PATH):
        print(f"[-] Weekly digest {DIGEST_PATH} not found. Run weekly_digest.py first.")
        return None

    with open(DIGEST_PATH, "r", encoding="utf-8") as f:
        digest_data = json.load(f)

    html_content = generate_email_html(digest_data)

    with open(EMAIL_PREVIEW_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("======================================================")
    print(f"[*] HTML Email Preview Generated Successfully!")
    print(f"[*] Preview Saved to: {EMAIL_PREVIEW_PATH}")
    print("======================================================")
    return html_content

if __name__ == "__main__":
    generate_email_preview()
