from kubernetes import client, config
from datetime import datetime, timezone

def _load_k8s_config():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

def format_age(creation_timestamp):
    if not creation_timestamp: return "N/A"
    now = datetime.now(timezone.utc)
    delta = now - creation_timestamp
    if delta.days > 0: return f"{delta.days}d"
    hours = delta.seconds // 3600
    if hours > 0: return f"{hours}h"
    minutes = (delta.seconds % 3600) // 60
    if minutes > 0: return f"{minutes}m"
    return f"{delta.seconds}s"