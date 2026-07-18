import os

APP_ID = os.environ.get("DISCORD_APP_ID", "")
BOT_TOKEN = os.environ.get("DISCORD_TOKEN", "")
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "")

# --- RBAC - DISCORD ROLES ---
# Replace the values with your Discord role IDs.
# Leave a string empty ("") for a role if you are not using it.
DISCORD_ROLES = {
    "admin": "",
    "dev": "",
    "viewer": ""
}

# --- AUDIT LOG ---
# ID of the channel where audit logs will be sent. Leave empty ("") to disable.
# Make sure the bot has "Send Messages" permissions in this channel.
AUDIT_LOG_CHANNEL_ID = "" # Replace with the ID of your #audit-logs channel