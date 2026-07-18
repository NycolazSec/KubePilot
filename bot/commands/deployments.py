from kubernetes import client, config
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
from . import utils
from ..auth import AccessLevel

definition = {
    "name": "deployments",
    "description": "Manage Kubernetes deployments.",
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
        api = client.AppsV1Api()
        deployments = api.list_namespaced_deployment(namespace)

        if not deployments.items:
            return {"embeds": [{"title": "Deployment Management", "description": f"No deployments found in `{namespace}`.", "color": 16705372}]}

        options = []
        for dep in deployments.items[:25]:
            options.append({
                "label": dep.metadata.name,
                "value": dep.metadata.name,
                "description": f"Image: {dep.spec.template.spec.containers[0].image}"
            })

        return {
            "embeds": [{"title": f"Deployment Management ({namespace})", "description": "Please select a deployment to manage from the list below.", "color": 5814783}],
            "components": [{
                "type": 1,
                "components": [{
                    "type": 3,  # Select Menu
                    "custom_id": f"deploy_select_menu:{namespace}",
                    "placeholder": "Choose a deployment...",
                    "options": options
                }]
            }]
        }
    except Exception as e:
        return {"embeds": [{"title": "❌ K8s Error", "description": str(e), "color": 15158332}]}

def get_deployment_details(deployment_name, namespace="default", access_level=AccessLevel.VIEWER):
    try:
        utils._load_k8s_config()
        api = client.AppsV1Api()
        dep = api.read_namespaced_deployment(name=deployment_name, namespace=namespace)

        spec, status = dep.spec, dep.status
        replicas_info = f"{status.ready_replicas or 0}/{spec.replicas} ready"
        if status.unavailable_replicas: replicas_info += f", {status.unavailable_replicas} unavailable"

        strategy = spec.strategy.type
        if strategy == "RollingUpdate" and spec.strategy.rolling_update:
            strategy += f" (Max Surge: {spec.strategy.rolling_update.max_surge}, Max Unavailable: {spec.strategy.rolling_update.max_unavailable})"

        conditions = "\n".join([f"`{c.type}`: {c.status} ({c.reason})" for c in status.conditions]) if status.conditions else "None"
        image = spec.template.spec.containers[0].image

        embed = {
            "title": f"Deployment Dashboard: {dep.metadata.name}",
            "color": 3447003,
            "fields": [
                {"name": "Namespace", "value": f"`{dep.metadata.namespace}`", "inline": True},
                {"name": "Age", "value": utils.format_age(dep.metadata.creation_timestamp), "inline": True},
                {"name": "Replicas", "value": replicas_info, "inline": True},
                {"name": "Main Image", "value": f"`{image}`", "inline": False},
                {"name": "Strategy", "value": strategy, "inline": False},
                {"name": "Conditions", "value": conditions, "inline": False},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        admin_buttons = []
        if access_level >= AccessLevel.ADMIN:
            admin_buttons.extend([
                {"type": 2, "style": 3, "label": "Scale", "custom_id": f"deploy_scale:{deployment_name}:{namespace}", "emoji": {"name": "📈"}},
                {"type": 2, "style": 2, "label": "Rollback", "custom_id": f"deploy_rollback:{deployment_name}:{namespace}", "emoji": {"name": "⏪"}},
                {"type": 2, "style": 2, "label": "Update Image", "custom_id": f"deploy_update_image:{deployment_name}:{namespace}", "emoji": {"name": "📦"}},
                {"type": 2, "style": 4, "label": "Delete", "custom_id": f"deploy_delete:{deployment_name}:{namespace}", "emoji": {"name": "🗑️"}},
            ])

        dev_buttons = []
        if access_level >= AccessLevel.DEV:
            dev_buttons.append(
                {"type": 2, "style": 1, "label": "Rollout Restart", "custom_id": f"deploy_rollout_restart:{deployment_name}:{namespace}", "emoji": {"name": "🔄"}},
            )

        components = []
        all_action_buttons = dev_buttons + admin_buttons
        if all_action_buttons:
            components.extend([{"type": 1, "components": all_action_buttons[i:i + 5]} for i in range(0, len(all_action_buttons), 5)])

        components.append(
            {"type": 1, "components": [
                 {"type": 2, "style": 2, "label": "Back to list", "custom_id": f"deploy_list_refresh:{namespace}"}
            ]}
        )
        return {"embeds": [embed], "components": components}
    except ApiException as e:
        return {"content": f"❌ Kubernetes API Error: `{e.reason}`"}

def scale_deployment(deployment_name, replicas, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.AppsV1Api()
        api.patch_namespaced_deployment_scale(name=deployment_name, namespace=namespace, body={"spec": {"replicas": replicas}})
        return f"✅ Scaling for `{deployment_name}` to **{replicas}** replicas has been requested."
    except ApiException as e:
        return f"❌ Error while scaling `{deployment_name}`: `{e.reason}`"

def rollout_restart_deployment(deployment_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.AppsV1Api()
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {"kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat() + "Z"}
                    }
                }
            }
        }
        api.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch)
        return f"✅ Rollout restart for `{deployment_name}` has been triggered."
    except ApiException as e:
        return f"❌ Error during rollout restart of `{deployment_name}`: `{e.reason}`"

def rollback_deployment(deployment_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.AppsV1Api()
        return f"ℹ️ The rollback feature requires advanced ReplicaSet management logic not implemented in this simple version. The action has been noted."
    except ApiException as e:
        return f"❌ Error during rollback of `{deployment_name}`: `{e.reason}`"

def update_deployment_image(deployment_name, new_image, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.AppsV1Api()
        patch = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{"name": deployment_name, "image": new_image}]
                    }
                }
            }
        }
        deployment = api.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        deployment.spec.template.spec.containers[0].image = new_image
        api.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=deployment)
        return f"✅ Image for `{deployment_name}` has been updated to `{new_image}`."
    except ApiException as e:
        return f"❌ Error while updating image for `{deployment_name}`: `{e.reason}`"
    except (IndexError, AttributeError):
        return f"❌ Could not find the container to update for `{deployment_name}`."

def delete_deployment(deployment_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.AppsV1Api()
        api.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
        return f"✅ Deletion request for deployment `{deployment_name}` has been sent."
    except ApiException as e:
        return f"❌ Error while deleting `{deployment_name}`: `{e.reason}`"