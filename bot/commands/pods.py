from kubernetes import client, config
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
import yaml
from . import utils
import re
from bot.auth import AccessLevel

definition = {
    "name": "pods",
    "description": "Displays the status of Kubernetes pods.",
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

def _get_pod_metrics(pod_name, namespace="default"):
    try:
        custom_api = client.CustomObjectsApi()
        metrics = custom_api.get_namespaced_custom_object(
            group="metrics.k8s.io", version="v1beta1", name=pod_name,
            namespace=namespace, plural="pods"
        )
        usage = metrics.get('containers', [{}])[0].get('usage', {})
        cpu_n = int(usage.get('cpu', '0n')[:-1])
        mem_ki = int(usage.get('memory', '0Ki')[:-2])

        cpu_str = f"{cpu_n / 1_000_000:.2f}m"
        mem_str = f"{mem_ki / 1024:.1f} MiB" if mem_ki > 1024 else f"{mem_ki} KiB"
        return cpu_str, mem_str
    except ApiException as e:
        if e.status == 404:
            return "N/A", "N/A (metrics-server?)"
        return "N/A", f"N/A (API Err)"
    except (ValueError, TypeError, IndexError, client.ApiException):
        return "N/A", "N/A"

def _get_latest_pod_event(api, pod_name, namespace="default"):
    try:
        field_selector = f'involvedObject.name={pod_name},involvedObject.kind=Pod,involvedObject.namespace={namespace}'
        events = api.list_namespaced_event(namespace, field_selector=field_selector, limit=10)
        if not events.items:
            return None

        events.items.sort(key=lambda e: e.last_timestamp, reverse=True)
        warning_event = next((e for e in events.items if e.type == 'Warning'), None)
        
        latest_event = warning_event or events.items[0]
        
        age = utils.format_age(latest_event.last_timestamp)
        message = (latest_event.message[:150] + '...') if len(latest_event.message) > 150 else latest_event.message
        return f"**{latest_event.type}** ({age} ago): {latest_event.reason} - *{message}*"
    except Exception:
        return None

def execute(d):
    try:
        utils._load_k8s_config()
        
        namespace = "default"
        if d.get('type') == 2:
            namespace = next((opt['value'] for opt in d.get('data', {}).get('options', []) if opt['name'] == 'namespace'), 'default')
        elif d.get('type') == 3:
            custom_id = d.get('data', {}).get('custom_id', '')
            parts = custom_id.split(':')
            if len(parts) > 1: # e.g., k8s_refresh_pods:kube-system
                namespace = parts[1]

        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace=namespace)
        
        if not pods.items:
            description = f"No pods found in `{namespace}`."
        else:
            pod_lines = []
            status_emoji = {"Running": "🟢", "Succeeded": "✅", "Pending": "🟡", "Failed": "🔴", "Unknown": "❓", "Terminating": "⏳"}
            for pod in pods.items:
                status = "Terminating" if pod.metadata.deletion_timestamp else pod.status.phase
                emoji = status_emoji.get(status, "❓")
                restarts = sum(c.restart_count for c in (pod.status.container_statuses or []))
                age = utils.format_age(pod.metadata.creation_timestamp)
                pod_lines.append(f"{emoji} `{pod.metadata.name}` - **{status}** (R: {restarts}, A: {age})")
            description = "\n".join(pod_lines)

        return {
            "embeds": [{
                "title": f"Kubernetes Pod Status ({namespace})",
                "description": description,
                "color": 3066993,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }],
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 1,
                            "label": "Refresh",
                            "custom_id": f"k8s_refresh_pods:{namespace}"
                        },
                        {
                            "type": 2,
                            "style": 2,
                            "label": "Manage pods...",
                            "custom_id": f"k8s_manage_pods:{namespace}"
                        }
                    ]
                }
            ]
        }
    except Exception as e:
        return {"embeds": [{"title": "❌ K8s Error", "description": str(e), "color": 15158332}]}

def show_pod_management(d):
    original_embeds = d.get('message', {}).get('embeds', [])
    if not original_embeds:
        return {"content": "Error: Original embed not found.", "flags": 64}

    description = original_embeds[0].get('description', '')
    pod_names = re.findall(r'`([^`]+)`', description)

    if not pod_names:
        return {"content": "No pods to manage in the list.", "flags": 64}

    custom_id = d.get('data', {}).get('custom_id', '')
    namespace = custom_id.split(':')[1] if ':' in custom_id else 'default'

    options = [{"label": name, "value": name, "description": f"Manage pod {name}"} for name in pod_names[:25]]
    return {
        "embeds": original_embeds,
        "components": [
            {
                "type": 1,
                "components": [{
                    "type": 3, "custom_id": f"k8s_select_pod_action:{namespace}",
                    "placeholder": "Choose a pod for an action", "options": options
                }]
            },
            {
                "type": 1,
                "components": [{ "type": 2, "style": 2, "label": "Cancel", "custom_id": f"k8s_refresh_pods:{namespace}" }]
            }
        ]
    }

def get_pod_details(pod_name, namespace="default", access_level=AccessLevel.VIEWER):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)

        cpu_usage, mem_usage = _get_pod_metrics(pod_name, namespace)
        latest_event = _get_latest_pod_event(api, pod_name, namespace)

        status = "Terminating" if pod.metadata.deletion_timestamp else pod.status.phase
        status_emoji = {"Running": "🟢", "Succeeded": "✅", "Pending": "🟡", "Failed": "🔴", "Unknown": "❓", "Terminating": "⏳"}
        status_colors = {"Running": 3066993, "Succeeded": 3066993, "Pending": 16705372, "Failed": 15158332, "Unknown": 8421504, "Terminating": 8421504}
        emoji = status_emoji.get(status, "❓")
        color = status_colors.get(status, 8421504)

        fields = [
            {"name": "Status", "value": f"{emoji} {status}", "inline": True},
            {"name": "Pod IP", "value": f"`{pod.status.pod_ip or 'N/A'}`", "inline": True},
            {"name": "Age", "value": utils.format_age(pod.metadata.creation_timestamp), "inline": True},
            {"name": "Node", "value": f"`{pod.spec.node_name or 'N/A'}`", "inline": True},
            {"name": "CPU Usage", "value": f"`{cpu_usage}`", "inline": True},
            {"name": "Memory Usage", "value": f"`{mem_usage}`", "inline": True},
        ]

        if pod.metadata.labels:
            labels_str = "\n".join([f"`{k}: {v}`" for k, v in list(pod.metadata.labels.items())[:4]])
            if len(pod.metadata.labels) > 4:
                labels_str += f"\n...and {len(pod.metadata.labels) - 4} more"
            fields.append({"name": "Main Labels", "value": labels_str, "inline": False})

        for container in pod.spec.containers:
            container_status = next((cs for cs in (pod.status.container_statuses or []) if cs.name == container.name), None)
            restarts = container_status.restart_count if container_status else 0
            
            res_info = []
            res = container.resources
            req = f"CPU: {res.requests.get('cpu', '-')} / Mem: {res.requests.get('memory', '-')}" if res and res.requests else "Not defined"
            lim = f"CPU: {res.limits.get('cpu', '-')} / Mem: {res.limits.get('memory', '-')}" if res and res.limits else "Not defined"
            res_info.append(f"**Requests**: {req}")
            res_info.append(f"**Limits**: {lim}")

            if container.ports:
                ports_str = ", ".join([f"{p.container_port}/{p.protocol}" for p in container.ports])
                res_info.append(f"**Ports**: {ports_str}")

            if container.liveness_probe: res_info.append(f"**Liveness Probe**: Oui")
            if container.readiness_probe: res_info.append(f"**Readiness Probe**: Oui")

            fields.append({
                "name": f"📦 Container: {container.name} (Restarts: {restarts})",
                "value": "\n".join(f"> {line}" for line in res_info),
                "inline": False
            })

        if latest_event:
            fields.append({"name": "Last Event", "value": latest_event, "inline": False})

        action_buttons = []
        if access_level >= AccessLevel.DEV:
            action_buttons.extend([
                {"type": 2, "style": 1, "label": "Logs", "custom_id": f"k8s_logs:{pod_name}:{namespace}", "emoji": {"name": "📄"}},
                {"type": 2, "style": 2, "label": "Describe", "custom_id": f"k8s_describe:{pod_name}:{namespace}", "emoji": {"name": "📝"}},
                {"type": 2, "style": 2, "label": "Exec Cmd", "custom_id": f"k8s_exec_cmd:{pod_name}:{namespace}", "emoji": {"name": "💻"}},
            ])
        
        if access_level >= AccessLevel.ADMIN:
            action_buttons.append(
                {"type": 2, "style": 4, "label": "Supprimer", "custom_id": f"k8s_del:{pod_name}:{namespace}", "emoji": {"name": "🗑️"}}
            )

        components = []
        if action_buttons:
            components.append({"type": 1, "components": action_buttons})
        
        components.append(
            {"type": 1, "components": [
                {"type": 2, "style": 1, "label": "Refresh", "custom_id": f"k8s_refresh_details:{pod_name}:{namespace}", "emoji": {"name": "🔄"}},
                {"type": 2, "style": 2, "label": "Back to list", "custom_id": f"k8s_refresh_pods:{namespace}"}
            ]}
        )

        return {
            "embeds": [{
                "title": f"Pod Details: {pod.metadata.name}",
                "fields": fields,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": f"Namespace: {pod.metadata.namespace}"}
            }],
            "components": components
        }

    except client.ApiException as e:
        return {"content": f"❌ Kubernetes API error while fetching details for `{pod_name}`: `{e.reason}`"}
    except Exception as e:
        return {"content": f"❌ Unexpected error while fetching details for `{pod_name}`: `{str(e)}`"}

def get_pod_describe(pod_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        
        pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)
        pod_dict = client.ApiClient().sanitize_for_serialization(pod)
        pod_yaml = yaml.dump(pod_dict, sort_keys=False, indent=2, allow_unicode=True)

        field_selector = f'involvedObject.name={pod_name},involvedObject.kind=Pod,involvedObject.namespace={namespace}'
        events = api.list_namespaced_event(namespace, field_selector=field_selector, limit=20)
        events.items.sort(key=lambda e: e.first_timestamp if e.first_timestamp else datetime.min.replace(tzinfo=timezone.utc))

        events_str = "Events:\n  Type\tReason\tAge\tFrom\tMessage\n  ----\t------\t---\t----\t-------\n"
        if events.items:
            for e in events.items:
                age = utils.format_age(e.last_timestamp)
                message = (e.message or "").split('\n')[0]
                events_str += f"  {e.type or 'N/A'}\t{e.reason or 'N/A'}\t{age}\t{(e.source.component if e.source else 'N/A')}\t{message}\n"
        else:
            events_str += "  <none>\n"

        return f"--- Pod Description (YAML) ---\n{pod_yaml}\n\n--- Recent Events ---\n{events_str}"

    except ApiException as e:
        return f"❌ Kubernetes API error while describing `{pod_name}`: `{e.reason}`"
    except Exception as e:
        return f"❌ Unexpected error while describing `{pod_name}`: `{str(e)}`"

def get_pod_exec_command(pod_name, namespace="default"):
    command = f"kubectl exec -it {pod_name} -n {namespace} -- /bin/sh"
    return {
        "content": f"To connect to the pod, use the following command in your terminal:\n```bash\n{command}\n```",
        "flags": 64
    }

def get_pod_logs(pod_name, namespace="default", tail_lines=50):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        logs = api.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines
        )

        if not logs:
            return {"content": f"📄 Logs for `{pod_name}` (No recent output)."}

        if len(logs) > 4000:
            logs = f"...\n{logs[-4000:]}"

        return {
            "embeds": [{
                "title": f"📄 Logs for pod `{pod_name}`",
                "description": f"```\n{logs}\n```",
                "color": 5814783,
                "footer": {"text": f"Displaying the last {tail_lines} lines."}
            }]
        }

    except client.ApiException as e:
        return {"content": f"❌ Kubernetes API error while fetching logs for `{pod_name}`: `{e.reason}`"}
    except Exception as e:
        return {"content": f"❌ Unexpected error while fetching logs for `{pod_name}`: `{str(e)}`"}

def get_delete_confirmation_modal(pod_name, message_id, namespace):
    title = f"Delete {pod_name}?"
    if len(title) > 45: title = title[:42] + "..."
    
    safe_custom_id = f"k8s_confirm:{message_id}:{pod_name}:{namespace}"[:100]

    return {
        "title": title,
        "custom_id": safe_custom_id,
        "components": [{
            "type": 1,
            "components": [{
                "type": 4, "custom_id": "pod_name_confirm",
                "label": "Confirm by typing the pod name",
                "style": 1, "placeholder": pod_name, "required": True
            }]
        }]
    }

def delete_pod(pod_name, namespace="default"):
    try:
        utils._load_k8s_config()
        api = client.CoreV1Api()
        api.delete_namespaced_pod(name=pod_name, namespace=namespace)
        
        return {"content": f"✅ La demande de suppression pour le pod `{pod_name}` a été envoyée avec succès."}

    except client.ApiException as e:
        return {"content": f"❌ Kubernetes API error while deleting `{pod_name}`: `{e.reason}`"}
    except Exception as e:
        return {"content": f"❌ Unexpected error while trying to delete `{pod_name}`: `{str(e)}`"}