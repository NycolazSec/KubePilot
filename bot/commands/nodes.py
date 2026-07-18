from kubernetes import client
from datetime import datetime, timezone
from . import utils
import re

definition = {
    "name": "nodes",
    "description": "Displays information about the Kubernetes cluster nodes.",
    "type": 1
}

def _get_node_roles(node):
    roles = [
        key.split('/')[-1]
        for key in node.metadata.labels
        if key.startswith('node-role.kubernetes.io/')
    ]
    if not roles:
        if 'node.kubernetes.io/master' in node.metadata.labels:
            return "master"
        return "<none>"
    return ", ".join(roles)

def execute(d):
    """Executes the command to list cluster nodes."""
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        nodes = api.list_node()

        if not nodes.items:
            return {
                "embeds": [{
                    "title": "Kubernetes Node Status",
                    "description": "No nodes found in the cluster.",
                    "color": 16705372  # Orange
                }]
            }

        embed = {
            "title": "Kubernetes Node Status",
            "color": 3447003,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": []
        }

        for node in nodes.items:
            ready_condition = next((c for c in node.status.conditions if c.type == 'Ready'), None)
            status = "Ready" if ready_condition and ready_condition.status == "True" else "NotReady"
            
            if node.spec.unschedulable:
                status_emoji = "🚧"
                status += ", SchedulingDisabled"
            else:
                status_emoji = "🟢" if status == "Ready" else "🔴"
            
            roles = _get_node_roles(node)
            age = utils.format_age(node.metadata.creation_timestamp)
            version = node.status.node_info.kubelet_version

            cpu_alloc = node.status.allocatable.get('cpu', 'N/A')
            mem_alloc = node.status.allocatable.get('memory', 'N/A')

            field_value = (
                f"**Status**: {status_emoji} {status}\n"
                f"**Roles**: `{roles}`\n"
                f"**Age**: {age}\n"
                f"**Version**: `{version}`\n"
                f"**CPU (alloc.)**: `{cpu_alloc}`\n"
                f"**Memory (alloc.)**: `{mem_alloc}`"
            )

            embed["fields"].append({
                "name": f"🔹 {node.metadata.name}",
                "value": field_value,
                "inline": True
            })
        
        embed["fields"] = embed["fields"][:25]

        components = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 1,
                        "label": "Refresh",
                        "custom_id": "nodes_list_refresh",
                        "emoji": {"name": "🔄"}
                    },
                    {
                        "type": 2,
                        "style": 2,
                        "label": "Manage...",
                        "custom_id": "nodes_manage",
                        "emoji": {"name": "🔧"}
                    }
                ]
            }
        ]

        return {"embeds": [embed], "components": components}

    except Exception as e:
        return {"embeds": [{"title": "❌ K8s Error", "description": str(e), "color": 15158332}]}

def show_node_management(d):
    original_embeds = d.get('message', {}).get('embeds', [])
    if not original_embeds:
        return (7, {"content": "Error: Original embed not found.", "flags": 64})

    fields = original_embeds[0].get('fields', [])
    node_names = [field['name'].replace('🔹 ', '') for field in fields]

    if not node_names:
        return (7, {"content": "No nodes to manage in the list.", "flags": 64})

    options = [{"label": name, "value": name, "description": f"View details for {name}"} for name in node_names[:25]]
    
    response_data = {
        "embeds": original_embeds,
        "components": [
            {
                "type": 1,
                "components": [{
                    "type": 3, "custom_id": "nodes_select_node",
                    "placeholder": "Choose a node to inspect...", "options": options
                }]
            },
            {
                "type": 1,
                "components": [{ "type": 2, "style": 2, "label": "Cancel", "custom_id": "nodes_list_refresh" }]
            }
        ]
    }
    return (7, response_data)

def get_node_details(node_name):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        node = api.read_node(name=node_name)

        schedulable_status = "No (cordoned)" if node.spec.unschedulable else "Yes"

        taints_str = "\n".join([f"`{t.key}={t.value}:{t.effect}`" for t in (node.spec.taints or [])]) or "None"

        conditions_str = ""
        for c in node.status.conditions:
            positive_conditions = ['Ready']
            
            is_good_state = False
            if c.type in positive_conditions:
                is_good_state = (c.status == 'True')
            else: # For pressure conditions, 'False' is the desired state.
                is_good_state = (c.status == 'False')

            if c.status == 'Unknown':
                emoji = "❔"
            else:
                emoji = "✅" if is_good_state else "❌"

            conditions_str += f"{emoji} `{c.type}`: {c.status} - *{c.reason or 'N/A'}*\n"
        if not conditions_str: conditions_str = "None"

        info = node.status.node_info
        info_value = f"**OS**: `{info.operating_system}`\n**Arch**: `{info.architecture}`\n**Kernel**: `{info.kernel_version}`\n**Runtime**: `{info.container_runtime_version}`"

        embed = {
            "title": f"🔎 Node Details: {node.metadata.name}",
            "color": 3447003,
            "fields": [
                {"name": "Schedulable", "value": schedulable_status, "inline": True},
                {"name": "Informations Système", "value": info_value, "inline": False},
                {"name": "Taints", "value": taints_str, "inline": False},
                {"name": "Conditions", "value": conditions_str, "inline": False},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if node.spec.unschedulable:
            toggle_button = {
                "type": 2, "style": 3, "label": "Uncordon", 
                "custom_id": f"nodes_uncordon:{node_name}", "emoji": {"name": "✅"}
            }
        else:
            toggle_button = {
                "type": 2, "style": 4, "label": "Cordon", 
                "custom_id": f"nodes_cordon:{node_name}", "emoji": {"name": "🚧"}
            }

        components = [
            {"type": 1, "components": [
                 toggle_button,
                 {"type": 2, "style": 4, "label": "Drain", "custom_id": f"nodes_drain:{node_name}", "emoji": {"name": "💧"}},
                 {"type": 2, "style": 2, "label": "Back to list", "custom_id": "nodes_list_refresh"}
            ]}
        ]
        return (7, {"embeds": [embed], "components": components})

    except client.ApiException as e:
        return (7, {"content": f"❌ Kubernetes API Error: `{e.reason}`"})

def toggle_node_scheduling(node_name, schedulable):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        
        body = {"spec": {"unschedulable": not schedulable}}
        api.patch_node(name=node_name, body=body)
        
        return get_node_details(node_name)
        
    except client.ApiException as e:
        action = "uncordon" if schedulable else "cordon"
        return (4, {"content": f"❌ API error during '{action}' on node `{node_name}`: `{e.reason}`", "flags": 64})

def drain_node(node_name):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()

        api.patch_node(name=node_name, body={"spec": {"unschedulable": True}})

        field_selector = f'spec.nodeName={node_name}'
        pods = api.list_pod_for_all_namespaces(field_selector=field_selector)

        eviction_results = {"success": [], "failed": [], "skipped": []}
        
        for pod in pods.items:
            if any(owner.kind == 'DaemonSet' for owner in (pod.metadata.owner_references or [])):
                eviction_results["skipped"].append(pod.metadata.name)
                continue

            eviction_body = client.V1Eviction(
                metadata=client.V1ObjectMeta(name=pod.metadata.name, namespace=pod.metadata.namespace),
                delete_options=client.V1DeleteOptions(grace_period_seconds=30)
            )
            try:
                api.create_namespaced_pod_eviction(name=pod.metadata.name, namespace=pod.metadata.namespace, body=eviction_body)
                eviction_results["success"].append(pod.metadata.name)
            except ApiException as e:
                eviction_results["failed"].append(f"{pod.metadata.name} ({e.status})")

        summary = [f"Draining of node `{node_name}` initiated."]
        if eviction_results["success"]: summary.append(f"✅ {len(eviction_results['success'])} pod(s) being evicted.")
        if eviction_results["failed"]: summary.append(f"❌ Eviction failed for {len(eviction_results['failed'])} pod(s): {', '.join(eviction_results['failed'])}")
        if eviction_results["skipped"]: summary.append(f"ℹ️ {len(eviction_results['skipped'])} pod(s) (DaemonSet) ignored.")
        return "\n".join(summary)

    except ApiException as e:
        return f"❌ API error while draining node `{node_name}`: `{e.reason}`"