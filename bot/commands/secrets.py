import base64
from kubernetes import client
from datetime import datetime, timezone
from . import utils

definition = {
    "name": "secrets",
    "description": "Manage Kubernetes Secrets (values are masked).",
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
        secrets = api.list_namespaced_secret(namespace)

        if not secrets.items:
            return {"embeds": [{"title": f"Secret Management ({namespace})", "description": f"No Secrets found in `{namespace}`.", "color": 16705372}]}

        options = []
        for secret in secrets.items[:25]:
            data_count = len(secret.data) if secret.data else 0
            options.append({
                "label": secret.metadata.name,
                "value": secret.metadata.name,
                "description": f"Type: {secret.type}, {data_count} key(s)"
            })

        return {
            "embeds": [{"title": f"Secret Management ({namespace})", "description": "Please select a Secret to inspect.", "color": 5814783}],
            "components": [{
                "type": 1,
                "components": [{
                    "type": 3,
                    "custom_id": f"secret_select_menu:{namespace}",
                    "placeholder": "Choose a Secret...",
                    "options": options
                }]
            }]
        }
    except Exception as e:
        return {"embeds": [{"title": "❌ Erreur K8s", "description": str(e), "color": 15158332}]}

def get_secret_details(secret_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        secret = api.read_namespaced_secret(name=secret_name, namespace=namespace)

        embed = {
            "title": f"Détails du Secret: {secret.metadata.name}",
            "color": 3447003,
            "fields": [
                {"name": "Namespace", "value": f"`{secret.metadata.namespace}`", "inline": True},
                {"name": "Age", "value": utils.format_age(secret.metadata.creation_timestamp), "inline": True},
                {"name": "Type", "value": f"`{secret.type}`", "inline": True},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if secret.data:
            data_str = ""
            for key, value in secret.data.items():
                try:
                    size = len(base64.b64decode(value))
                    data_str += f"**`{key}`**: `[value masked - {size} bytes]`\n"
                except (TypeError, ValueError):
                    data_str += f"**`{key}`**: `[invalid or non-b64 data]`\n"
            embed["fields"].append({"name": "Data", "value": data_str, "inline": False})
        else:
            embed["fields"].append({"name": "Data", "value": "None", "inline": False})

        components = [
            {"type": 1, "components": [
                {"type": 2, "style": 2, "label": "Edit/Add Key", "custom_id": f"secret_edit:{secret_name}:{namespace}", "emoji": {"name": "✏️"}},
                {"type": 2, "style": 2, "label": "Delete Key", "custom_id": f"secret_delete_key:{secret_name}:{namespace}", "emoji": {"name": "🔑"}},
                {"type": 2, "style": 4, "label": "Delete Secret", "custom_id": f"secret_delete:{secret_name}:{namespace}", "emoji": {"name": "🗑️"}},
            ]},
            {"type": 1, "components": [
                 {"type": 2, "style": 2, "label": "Back to list", "custom_id": f"secret_list_refresh:{namespace}"}
            ]}
        ]
        return (7, {"embeds": [embed], "components": components})
    except client.ApiException as e:
        return (4, {"content": f"❌ Kubernetes API Error: `{e.reason}`", "flags": 64})

def patch_secret_data(secret_name, key, value, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        value_b64 = base64.b64encode(value.encode('utf-8')).decode('utf-8')
        body = {"data": {key: value_b64}}
        api.patch_namespaced_secret(name=secret_name, namespace=namespace, body=body)
        return get_secret_details(secret_name, namespace)
    except client.ApiException as e:
        return (4, {"content": f"❌ Error while updating `{secret_name}`: `{e.reason}`", "flags": 64})

def delete_secret_key(secret_name, key, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()

        escaped_key = key.replace("~", "~0").replace("/", "~1")
        
        patch = [{"op": "remove", "path": f"/data/{escaped_key}"}]
        api.patch_namespaced_secret(name=secret_name, namespace=namespace, body=patch)
        
        return get_secret_details(secret_name, namespace)
    except client.ApiException as e:
        if e.status in [404, 422]:
            return (4, {"content": f"❌ Key `{key}` was not found in Secret `{secret_name}`.", "flags": 64})
        return (4, {"content": f"❌ Error while deleting key `{key}`: `{e.reason}`", "flags": 64})

def delete_secret(secret_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        api.delete_namespaced_secret(name=secret_name, namespace=namespace)
        return f"✅ Deletion request for Secret `{secret_name}` has been sent."
    except client.ApiException as e:
        return f"❌ Error while deleting `{secret_name}`: `{e.reason}`"