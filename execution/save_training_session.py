"""
Google Sheets Logger - Saves training session data to Google Sheets.
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def save_to_google_sheets(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save training session to Google Sheets.

    Args:
        session_data: Dictionary with session results

    Returns:
        Dictionary with save status
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return {
            "success": False,
            "error": "Google API libraries not installed"
        }

    # Get credentials
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "..", "token.json")
    creds_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path)

    if not creds or not creds.valid:
        return {
            "success": False,
            "error": "Google credentials not set up. Run setup to authenticate."
        }

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Spreadsheet ID (you'll need to create this and update)
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_TRAINING_LOG_ID")
        if not spreadsheet_id:
            return {
                "success": False,
                "error": "GOOGLE_SHEETS_TRAINING_LOG_ID not set in .env"
            }

        # Prepare row data
        row = [
            session_data.get("agent_name", "Unknown"),
            datetime.now().isoformat(),
            session_data.get("duration_minutes", 0),
            session_data.get("final_score", 0),
            session_data.get("grade", ""),
            session_data.get("objections_handled", 0),
            session_data.get("objection_handling_score", 0),
            session_data.get("tone_score", 0),
            session_data.get("script_adherence_score", 0),
            session_data.get("active_listening_score", 0),
            session_data.get("professionalism_score", 0),
            ", ".join(session_data.get("improvements", [])),
            session_data.get("transcript_link", ""),
        ]

        # Append to sheet
        range_name = "Training Sessions!A:M"
        body = {"values": [row]}

        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body
        ).execute()

        return {
            "success": True,
            "rows_added": result.get("updates", {}).get("updatedRows", 0),
            "spreadsheet_id": spreadsheet_id
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save to Google Sheets: {str(e)}"
        }

def send_slack_notification(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send Slack notification for low-scoring sessions.

    Args:
        session_data: Session results

    Returns:
        Notification status
    """
    import requests

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return {
            "success": False,
            "error": "SLACK_WEBHOOK_URL not configured"
        }

    score = session_data.get("final_score", 0)
    agent_name = session_data.get("agent_name", "Unknown Agent")

    # Only notify if score is low or needs follow-up
    if score >= 7.0 and not session_data.get("needs_trainer_followup"):
        return {"success": True, "skipped": "Score is good, no notification needed"}

    # Build message
    emoji = "🟡" if score >= 5.0 else "🔴"
    message = {
        "text": f"{emoji} Training Session Alert: {agent_name}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Training Session Needs Review*\n\n*Agent:* {agent_name}\n*Score:* {score}/10 ({session_data.get('grade', 'N/A')})\n*Objections Handled:* {session_data.get('objections_handled', 0)}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Areas for Improvement:*\n" + "\n".join([f"• {item}" for item in session_data.get("improvements", ["No specific feedback"])])
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        return {"success": True, "notified": True}
    except Exception as e:
        return {
            "success": False,
            "error": f"Slack notification failed: {str(e)}"
        }

def save_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete session save: Google Sheets + Slack notification.

    Args:
        session_data: Full session results

    Returns:
        Save status for both systems
    """
    results = {}

    # Save to Google Sheets
    sheets_result = save_to_google_sheets(session_data)
    results["google_sheets"] = sheets_result

    # Send Slack notification if needed
    if session_data.get("needs_trainer_followup") or session_data.get("final_score", 10) < 7.0:
        slack_result = send_slack_notification(session_data)
        results["slack"] = slack_result

    results["success"] = sheets_result.get("success", False)
    return results

# Sample Google Sheets setup helper
def create_training_log_sheet():
    """
    Helper to create the Training Sessions Google Sheet.
    Run this once to set up the sheet structure.
    """
    print("Creating Google Sheets Training Log...")
    print("\nHeaders for your sheet (Row 1):")
    headers = [
        "Agent Name",
        "Date/Time",
        "Duration (minutes)",
        "Final Score",
        "Grade",
        "Objections Handled",
        "Objection Handling Score",
        "Tone & Confidence Score",
        "Script Adherence Score",
        "Active Listening Score",
        "Professionalism Score",
        "Areas for Improvement",
        "Transcript Link"
    ]
    print(", ".join(headers))
    print("\n1. Create a new Google Sheet")
    print("2. Name it 'Insurance Training Sessions'")
    print("3. Add the headers above to Row 1")
    print("4. Share it with your Google service account email")
    print("5. Copy the spreadsheet ID from the URL")
    print("6. Add to .env: GOOGLE_SHEETS_TRAINING_LOG_ID=<your_spreadsheet_id>")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        create_training_log_sheet()
    else:
        # Test save
        test_data = {
            "agent_name": "Test Agent",
            "duration_minutes": 10,
            "final_score": 7.5,
            "grade": "Good",
            "objections_handled": 3,
            "objection_handling_score": 8.0,
            "tone_score": 7.0,
            "script_adherence_score": 8.0,
            "active_listening_score": 7.5,
            "professionalism_score": 9.0,
            "improvements": ["Work on price objection handling", "Reduce filler words"],
            "transcript_link": "https://example.com/transcript",
            "needs_trainer_followup": False
        }

        result = save_session(test_data)
        print(f"Save result: {result}")
