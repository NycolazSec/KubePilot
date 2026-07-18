import requests
import json
from config import BOT_TOKEN, APP_ID, AUDIT_LOG_CHANNEL_ID
from datetime import datetime, timezone


def send_response(interaction_id, token, response_data, interaction_type=4):
    url = f"https://discord.com/api/v10/interactions/{interaction_id}/{token}/callback"
    if isinstance(response_data, str):
        response_data = {"content": response_data}
    
    payload = {"type": interaction_type, "data": response_data}
    requests.post(url, json=payload)

def edit_response(token, response_data):
    url = f"https://discord.com/api/v10/webhooks/{APP_ID}/{token}/messages/@original"
    if isinstance(response_data, str):
        response_data = {"content": response_data}
    requests.patch(url, json=response_data)

def send_followup(token, response_data, is_ephemeral=False):
    url = f"https://discord.com/api/v10/webhooks/{APP_ID}/{token}"
    if isinstance(response_data, str):
        response_data = {"content": response_data}
    if is_ephemeral:
        response_data["flags"] = 64
    requests.post(url, json=response_data)

def send_followup_with_file(token, file_content, filename, initial_message):
    url = f"https://discord.com/api/v10/webhooks/{APP_ID}/{token}"
    
    payload_json = json.dumps({"content": initial_message, "flags": 64})
    files = {
        'file[0]': (filename, file_content.encode('utf-8'), 'text/plain')
    }
    data = {'payload_json': payload_json}
    
    rep = requests.post(url, files=files, data=data)
    if rep.status_code >= 400:
        print(f"❌ Error sending followup with file: {rep.text}")

def send_audit_log(user, action, resource_name, details=""):
    if not AUDIT_LOG_CHANNEL_ID or AUDIT_LOG_CHANNEL_ID == "YOUR_AUDIT_CHANNEL_ID_HERE":
        return

    user_id = user['id']
    username = user['username']

    embed = {
        "title": f"📝 Audit Log: {action}",
        "color": 15105570, # Orange
        "fields": [
            {"name": "User", "value": f"<@{user_id}> (`{username}`)", "inline": True},
            {"name": "Action", "value": f"`{action}`", "inline": True},
            {"name": "Resource", "value": f"`{resource_name}`", "inline": False},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if details:
        embed["fields"].append({"name": "Details", "value": details, "inline": False})

    url = f"https://discord.com/api/v10/channels/{AUDIT_LOG_CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    payload = {"embeds": [embed]}
    
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"❌ Error sending audit log: {e}")