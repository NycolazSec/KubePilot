from kubernetes import client, config
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
from . import utils
from ..auth import AccessLevel

definition = {
    "name": "services",
    "description": "Manage Kubernetes services.",
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
        services = api.list_namespaced_service(namespace)

        if not services.items:
            return {"embeds": [{"title": "Service Management", "description": f"No services found in `{namespace}`.", "color": 16705372}]}

        options = []
        for svc in services.items[:25]:
            options.append({
                "label": svc.metadata.name,
                "value": svc.metadata.name,
                "description": f"Type: {svc.spec.type}, IP: {svc.spec.cluster_ip}"
            })

        return {
            "embeds": [{"title": f"Service Management ({namespace})", "description": "Please select a service to inspect from the list below.", "color": 5814783}],
            "components": [{
                "type": 1,
                "components": [{
                    "type": 3,  # Select Menu
                    "custom_id": f"svc_select_menu:{namespace}",
                    "placeholder": "Choose a service...",
                    "options": options
                }]
            }]
        }
    except Exception as e:
        return {"embeds": [{"title": "❌ K8s Error", "description": str(e), "color": 15158332}]}

def get_service_details(service_name, namespace="default", access_level=AccessLevel.VIEWER):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        svc = api.read_namespaced_service(name=service_name, namespace=namespace)

        spec = svc.spec

        type_explanations = {
            "ClusterIP": " (internal)",
            "NodePort": " (node)",
            "LoadBalancer": " (external)",
            "ExternalName": " (alias)"
        }
        type_str = f"`{spec.type}`{type_explanations.get(spec.type, '')}"

        endpoints_str = "None"
        try:
            if spec.type == 'ExternalName':
                endpoints_str = "N/A"
            else:
                endpoints = api.read_namespaced_endpoints(name=service_name, namespace=namespace)
                ready_count = 0
                if endpoints.subsets:
                    for subset in endpoints.subsets:
                        if subset.addresses:
                            ready_count += len(subset.addresses)
                
                if ready_count > 0:
                    endpoints_str = f"✅ {ready_count} ready"
                else:
                    if spec.selector:
                        endpoints_str = "❌ No ready pods"
                    else:
                        endpoints_str = "N/A (no selector)"
        except ApiException as e:
            if e.status == 404:
                endpoints_str = "❌ No ready pods"
            else:
                endpoints_str = "API Error"
        
        ports_str = "\n".join([f"`{p.port}/{p.protocol}` -> `{p.target_port}`" + (f" (NodePort: `{p.node_port}`)" if p.node_port else "") for p in (spec.ports or [])])
        if not ports_str: ports_str = "None"

        external_ips = spec.external_ips or []
        if spec.type == "LoadBalancer" and svc.status.load_balancer and svc.status.load_balancer.ingress:
            external_ips.extend([ing.ip or ing.hostname for ing in svc.status.load_balancer.ingress])
        external_ips_str = ", ".join(f"`{ip}`" for ip in external_ips) or "Aucune"

        selector_str = "\n".join([f"`{k}: {v}`" for k, v in (spec.selector or {}).items()]) or "None"

        embed = {
            "title": f"Service Dashboard: {svc.metadata.name}",
            "color": 3447003,
            "fields": [
                {"name": "Namespace", "value": f"`{svc.metadata.namespace}`", "inline": True},
                {"name": "Age", "value": utils.format_age(svc.metadata.creation_timestamp), "inline": True},
                {"name": "Type", "value": type_str, "inline": True},
                {"name": "Cluster IP", "value": f"`{spec.cluster_ip}`", "inline": True},
                {"name": "Endpoints", "value": endpoints_str, "inline": True},
                {"name": "Session Affinity", "value": f"`{spec.session_affinity}`", "inline": True},
                {"name": "External IP(s)", "value": external_ips_str, "inline": False},
                {"name": "Ports", "value": ports_str, "inline": False},
                {"name": "Selector", "value": selector_str, "inline": False},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        action_buttons = []
        if access_level >= AccessLevel.ADMIN:
            action_buttons.append(
                {"type": 2, "style": 4, "label": "Delete", "custom_id": f"svc_delete:{service_name}:{namespace}", "emoji": {"name": "🗑️"}}
            )

        components = []
        if action_buttons:
            components.append({"type": 1, "components": action_buttons})

        components.append(
            {"type": 1, "components": [
                 {"type": 2, "style": 2, "label": "Back to list", "custom_id": f"svc_list_refresh:{namespace}"}
            ]}
        )
        return (7, {"embeds": [embed], "components": components})
    except ApiException as e:
        return (4, {"content": f"❌ Kubernetes API Error: `{e.reason}`", "flags": 64})

def delete_service(service_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        api.delete_namespaced_service(name=service_name, namespace=namespace)
        return f"✅ Deletion request for service `{service_name}` has been sent."
    except ApiException as e:
        return f"❌ Error while deleting `{service_name}`: `{e.reason}`"