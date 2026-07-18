definition = {
    "name": "help",
    "description": "Displays a complete and visual presentation of KubePilot and its commands.",
    "type": 1
}

HELP_EMBEDS = {
    "home": {
        "title": "🏠 KubePilot: Your Kubernetes Helmsman",
        "description": (
            "Welcome aboard! I am KubePilot, your automated infrastructure assistant. "
            "My role is to simplify the management, monitoring, and security of your Kubernetes clusters "
            "directly from your Discord server. Use the menu below to navigate through the help sections."
        ),
        "color": 3447003,
        "footer": {"text": "Use slash commands (/) to interact."}
    },
    "resources": {
        "title": "🏗️ Resource Management",
        "description": "These commands allow you to manipulate the fundamental building blocks of your applications.",
        "color": 15105570,
        "fields": [
            {"name": "`/deployments`", "value": "Manage Deployment objects (creation, update, scaling).", "inline": False},
            {"name": "`/services`", "value": "Manage the network exposure of your applications (Services).", "inline": False}
        ]
    },
    "health": {
        "title": "🩺 Health & Diagnostics",
        "description": "Monitor the vital status of your cluster and containers.",
        "color": 3066993,
        "fields": [
            {"name": "`/pods`", "value": "Check the status, logs, and manage individual Pods.", "inline": False},
            {"name": "`/nodes`", "value": "Display detailed information about the status of cluster nodes.", "inline": False},
            {"name": "`/events`", "value": "Display the latest events in a namespace.", "inline": False}
        ]
    },
    "security": {
        "title": "🔒 Configuration & Security",
        "description": "Manage the settings and sensitive data of your applications.",
        "color": 15158332,
        "fields": [
            {"name": "`/configmaps`", "value": "Manage non-sensitive configuration dictionaries.", "inline": False},
            {"name": "`/secrets`", "value": "Manage sensitive data (passwords, keys, tokens).", "inline": False}
        ]
    },
    "organization": {
        "title": "🗺️ Organization & Help",
        "description": "Navigate the structure of your cluster.",
        "color": 10181046,
        "fields": [
            {"name": "`namespace` Option", "value": "All resource commands accept a `namespace` option to target a specific workspace.", "inline": False},
            {"name": "`/help` (this command)", "value": "Displays this visual presentation.", "inline": False}
        ]
    }
}

def _get_help_components(selected_page="home"):
    return [{
        "type": 1,
        "components": [{
            "type": 3,
            "custom_id": "help_navigation",
            "placeholder": "Navigate sections...",
            "options": [
                {"label": "Home", "value": "home", "emoji": {"name": "🏠"}, "default": selected_page == "home"},
                {"label": "Resource Management", "value": "resources", "emoji": {"name": "🏗️"}, "default": selected_page == "resources"},
                {"label": "Health & Diagnostics", "value": "health", "emoji": {"name": "🩺"}, "default": selected_page == "health"},
                {"label": "Configuration & Security", "value": "security", "emoji": {"name": "🔒"}, "default": selected_page == "security"},
                {"label": "Organization & Help", "value": "organization", "emoji": {"name": "🗺️"}, "default": selected_page == "organization"},
            ]
        }]
    }]

def execute(d):
    return {
        "embeds": [HELP_EMBEDS["home"]],
        "components": _get_help_components("home")
    }

def get_help_page(page_name):
    embed = HELP_EMBEDS.get(page_name)
    if not embed:
        embed = HELP_EMBEDS["home"]
        page_name = "home"
    
    return {
        "embeds": [embed],
        "components": _get_help_components(page_name)
    }