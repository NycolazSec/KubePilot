from kubernetes import client
from datetime import datetime, timezone
from . import utils

definition = {
    "name": "events",
    "description": "Displays the latest events in a Kubernetes namespace.",
    "type": 1,
    "options": [
        {
            "name": "namespace",
            "description": "The namespace to inspect (default: default).",
            "type": 3,
            "required": False
        }
    ]
}

def execute(d):
    try:
        utils._load_k8s_config()
        namespace = next((opt['value'] for opt in d.get('data', {}).get('options', []) if opt['name'] == 'namespace'), 'default')
        api = client.CoreV1Api()
        
        events = api.list_namespaced_event(namespace, limit=50)

        if not events.items:
            return {"embeds": [{"title": f"Events in `{namespace}`", "description": "No recent events found.", "color": 16705372}]}

        events.items.sort(key=lambda e: e.last_timestamp, reverse=True)

        description_lines = []
        for event in events.items[:15]:
            event_type_emoji = "⚠️" if event.type == "Warning" else "ℹ️"
            age = utils.format_age(event.last_timestamp)
            obj = event.involved_object
            message = (event.message or "").split('\n')[0]
            
            line = (
                f"{event_type_emoji} **{event.reason}** ({age})\n"
                f"> **Object**: `{obj.kind}/{obj.name}`\n"
                f"> **Message**: *{message}*"
            )
            description_lines.append(line)
        
        description = "\n\n".join(description_lines)
        if len(description) > 4096:
            description = description[:4090] + "\n..."

        embed = {
            "title": f"Latest Events in `{namespace}`",
            "description": description,
            "color": 3447003,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": f"Displaying the {len(description_lines)} most recent events."}
        }
        
        components = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 1,
                        "label": "Refresh",
                        "custom_id": f"events_refresh:{namespace}",
                        "emoji": {"name": "🔄"}
                    }
                ]
            }
        ]

        return {"embeds": [embed], "components": components}

    except Exception as e:
        return {"embeds": [{"title": "❌ K8s Error", "description": str(e), "color": 15158332}]}