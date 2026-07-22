from kubernetes import client
from datetime import datetime, timezone
from . import utils
from bot.auth import AccessLevel

definition = {
    "name": "configmaps",
    "description": "Manage Kubernetes ConfigMaps.",
    "type": 1,
    "options": [
        {
            "name": "namespace",
            "description": "The Kubernetes namespace to inspect (default: default).",
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
        config_maps = api.list_namespaced_config_map(namespace)

        if not config_maps.items:
            return {"embeds": [{"title": f"ConfigMap Management ({namespace})", "description": f"No ConfigMaps found in `{namespace}`.", "color": 16705372}]}

        options = []
        for cm in config_maps.items[:25]:
            data_count = len(cm.data) if cm.data else 0
            options.append({
                "label": cm.metadata.name,
                "value": cm.metadata.name,
                "description": f"{data_count} data key(s)"
            })

        return {
            "embeds": [{"title": f"ConfigMap Management ({namespace})", "description": "Please select a ConfigMap to inspect.", "color": 5814783}],
            "components": [{
                "type": 1,
                "components": [{
                    "type": 3,
                    "custom_id": f"cm_select_menu:{namespace}",
                    "placeholder": "Choose a ConfigMap...",
                    "options": options
                }]
            }]
        }
    except Exception as e:
        return {"embeds": [{"title": "❌ Erreur K8s", "description": str(e), "color": 15158332}]}

def get_configmap_details(configmap_name, namespace="default", access_level=AccessLevel.VIEWER):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        cm = api.read_namespaced_config_map(name=configmap_name, namespace=namespace)

        embed = {
            "title": f"ConfigMap Details: {cm.metadata.name}",
            "color": 3447003,
            "fields": [
                {"name": "Namespace", "value": f"`{cm.metadata.namespace}`", "inline": True},
                {"name": "Age", "value": utils.format_age(cm.metadata.creation_timestamp), "inline": True},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if cm.data:
            data_str = ""
            for key, value in cm.data.items():
                value_snippet = (value[:70] + '...') if len(value) > 70 else value
                data_str += f"**`{key}`**:\n```\n{value_snippet}\n```\n"
            
            if len(data_str) > 1024:
                data_str = data_str[:1020] + "\n..."
            embed["fields"].append({"name": "Data", "value": data_str, "inline": False})
        else:
            embed["fields"].append({"name": "Data", "value": "None", "inline": False})

        action_buttons = []
        if access_level >= AccessLevel.ADMIN:
            action_buttons.extend([
                {"type": 2, "style": 2, "label": "Edit", "custom_id": f"cm_edit:{configmap_name}:{namespace}", "emoji": {"name": "✏️"}},
                {"type": 2, "style": 4, "label": "Delete", "custom_id": f"cm_delete:{configmap_name}:{namespace}", "emoji": {"name": "🗑️"}},
            ])

        components = []
        if action_buttons:
            components.append({"type": 1, "components": action_buttons})
        
        components.append(
            {"type": 1, "components": [
                 {"type": 2, "style": 2, "label": "Back to list", "custom_id": f"cm_list_refresh:{namespace}"}
            ]}
        )
        return (7, {"embeds": [embed], "components": components})
    except client.ApiException as e:
        return (4, {"content": f"❌ Kubernetes API Error: `{e.reason}`", "flags": 64})

def patch_configmap_data(configmap_name, key, value, namespace="default", access_level=AccessLevel.ADMIN):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()

        body = {"data": {key: value}}
        api.patch_namespaced_config_map(name=configmap_name, namespace=namespace, body=body)

        return get_configmap_details(configmap_name, namespace, access_level)
    except client.ApiException as e:
        return (4, {"content": f"❌ Error while updating `{configmap_name}`: `{e.reason}`", "flags": 64})

def delete_configmap(configmap_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        api.delete_namespaced_config_map(name=configmap_name, namespace=namespace)
        return f"✅ Deletion request for ConfigMap `{configmap_name}` has been sent."
    except client.ApiException as e:
        return f"❌ Error while deleting `{configmap_name}`: `{e.reason}`"