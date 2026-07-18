# KubePilot: Your Kubernetes Helmsman on Discord

KubePilot is a powerful and interactive Discord bot designed to bring Kubernetes cluster management directly into your Discord server. It provides a secure, role-based, and user-friendly interface to monitor, diagnose, and manage your cloud-native applications.

## ✨ Features

-   **Interactive Dashboards**: View detailed information for Pods, Deployments, Services, Nodes, and more, all within Discord embeds.
-   **Rich Component UI**: Utilize buttons, dropdown menus, and modals for intuitive actions like scaling, restarting, and editing resources.
-   **Granular RBAC**: Secure your operations with a Role-Based Access Control system that maps Discord roles (`Admin`, `Dev`, `Viewer`) to specific permissions.
-   **Comprehensive Diagnostics**: Quickly access Pod logs, `describe` outputs, and real-time cluster events to troubleshoot issues efficiently.
-   **Node Maintenance**: Safely perform critical node operations like `cordon`, `uncordon`, and `drain` with confirmation steps.
-   **Configuration Management**: View and edit ConfigMaps and Secrets directly from the bot interface.
-   **Complete Audit Trail**: Every write-action (delete, patch, scale) is logged to a dedicated, private audit channel for full traceability.

## 🚀 Available Commands

KubePilot offers a suite of slash commands to interact with your cluster:

-   `/pods`: View status, get logs, describe, and manage individual Pods.
-   `/deployments`: Manage Deployments, including scaling, rollouts, and image updates.
-   `/services`: Inspect and manage Service resources.
-   `/nodes`: View the status of all cluster nodes and perform maintenance.
-   `/events`: See the latest events within a namespace.
-   `/configmaps`: View and edit ConfigMaps.
-   `/secrets`: Manage sensitive data with masked values.
-   `/help`: A comprehensive, navigable help menu.

## 🛠️ Setup & Installation

1.  **Prerequisites**:
    *   Python 3.8+
    *   A running Kubernetes cluster (like k3s, Minikube, or a cloud provider's).
    *   A Discord Bot application.

2.  **Clone the Repository**:
    ```bash
    git clone (https://github.com/NycolazSec/KubePilot.git)
    cd k8s
    ```

3.  **Install Dependencies**:
    *(You may need to create a `requirements.txt` file first)*
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the Bot**:
    Open `config.py` and fill in the required values:
    *   `APP_ID`, `BOT_TOKEN`: From your Discord Developer Portal.
    *   `DISCORD_ROLES`: The IDs of your `@K8s-Admin`, `@K8s-Dev`, and `@K8s-Viewer` roles.
    *   `AUDIT_LOG_CHANNEL_ID`: The ID of the channel where audit logs will be sent.
    *   Ensure your `kubeconfig` file is correctly set up (e.g., at `/etc/rancher/k3s/k3s.yaml` as per `bot/commands/utils.py` or at the default location `~/.kube/config`).

5.  **Run the Bot**:
    ```bash
    python main.py
    ```

---
*This bot was built to streamline DevOps workflows and improve observability for teams using Kubernetes and Discord.*
