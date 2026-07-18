import asyncio
from bot import discord_api
from config import DISCORD_ROLES
from bot.auth import AccessLevel, get_user_access_level

async def handle_interaction(event, command_registry):
    loop = asyncio.get_running_loop()
    d = event['d']
    int_id = d['id']
    int_token = d['token']

    member_payload = d.get('member')
    user_obj = member_payload.get('user') if member_payload else d.get('user')
    
    access_level = get_user_access_level(member_payload, DISCORD_ROLES)

    if access_level == AccessLevel.NONE:
        error_message = {
            "content": "🚫 Access denied. You do not have the required roles (`@K8s-Admin`, `@K8s-Dev`, or `@K8s-Viewer`) to use this bot.",
            "flags": 64  # Ephemeral message, only visible to the user.
        }
        discord_api.send_response(int_id, int_token, error_message)
        return
    
    interaction_type = d.get('type')
    data = d.get('data', {})

    if interaction_type == 2:
        cmd_name = data.get('name')
        if access_level < AccessLevel.VIEWER:
            discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. Minimum role `@K8s-Viewer` required.", "flags": 64})
            return

        if cmd_name in command_registry:
            module = command_registry[cmd_name]
            response_data = await loop.run_in_executor(None, module.execute, d)
            if response_data:
                discord_api.send_response(int_id, int_token, response_data)

    elif interaction_type == 3:
        custom_id = data.get('custom_id')
        module_name, _, action = custom_id.partition('_')
        
        if access_level < AccessLevel.VIEWER:
            discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. Minimum role `@K8s-Viewer` required.", "flags": 64})
            return
        
        if module_name == 'deploy': module_name = 'deployments'
        if module_name == 'svc': module_name = 'services'
        if module_name == 'cm': module_name = 'configmaps'
        if module_name == 'secret': module_name = 'secrets'

        if module_name in ['pods', 'k8s']: module_name = 'pods' # Alias
        
        module = command_registry.get(module_name)
        if not module: return

        # --- Routage Help ---
        if module_name == 'help':
            if custom_id == 'help_navigation':
                selected_page = data['values'][0]
                response_data = await loop.run_in_executor(None, module.get_help_page, selected_page)
                discord_api.send_response(int_id, int_token, response_data, 7)

        elif module_name == 'pods':
            if custom_id.startswith('k8s_refresh_pods'):
                response = await loop.run_in_executor(None, module.execute, d)
                discord_api.send_response(int_id, int_token, response, 7)
            elif custom_id.startswith('k8s_manage_pods'):
                response = await loop.run_in_executor(None, module.show_pod_management, d)
                discord_api.send_response(int_id, int_token, response, 7)
            elif custom_id.startswith('k8s_select_pod_action'):
                parts = custom_id.split(':')
                namespace = parts[1] if len(parts) > 1 else 'default'
                pod_name = data['values'][0]
                response = await loop.run_in_executor(None, module.get_pod_details, pod_name, namespace, access_level)
                discord_api.send_response(int_id, int_token, response, 7)
            elif custom_id.startswith("k8s_refresh_details:"):
                parts = custom_id.split(':')
                pod_name = parts[1]
                namespace = parts[2] if len(parts) > 2 else 'default'
                response = await loop.run_in_executor(None, module.get_pod_details, pod_name, namespace, access_level)
                discord_api.send_response(int_id, int_token, response, 7)
            elif custom_id.startswith("k8s_logs:"):
                if access_level < AccessLevel.DEV:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Dev` role required to read logs.", "flags": 64})
                    return
                parts = custom_id.split(':')
                pod_name = parts[1]
                namespace = parts[2] if len(parts) > 2 else 'default'
                response = await loop.run_in_executor(None, module.get_pod_logs, pod_name, namespace)
                discord_api.send_response(int_id, int_token, response)
            elif custom_id.startswith("k8s_describe:"):
                if access_level < AccessLevel.DEV:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Dev` role required for `describe`.", "flags": 64})
                    return
                parts = custom_id.split(':')
                pod_name = parts[1]
                namespace = parts[2] if len(parts) > 2 else 'default'
                discord_api.send_response(int_id, int_token, None, 5) # Defer
                describe_content = await loop.run_in_executor(None, module.get_pod_describe, pod_name, namespace)
                discord_api.send_followup_with_file(int_token, describe_content, f"describe-{pod_name}.txt", f"Here is the `describe` for `{pod_name}`:")
            elif custom_id.startswith("k8s_exec_cmd:"):
                if access_level < AccessLevel.DEV:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Dev` role required for `exec`.", "flags": 64})
                    return
                parts = custom_id.split(':')
                pod_name = parts[1]
                namespace = parts[2] if len(parts) > 2 else 'default'
                response = await loop.run_in_executor(None, module.get_pod_exec_command, pod_name, namespace)
                discord_api.send_response(int_id, int_token, response)
            elif custom_id.startswith("k8s_del:"):
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete.", "flags": 64})
                    return
                parts = custom_id.split(':')
                pod_name = parts[1]
                namespace = parts[2] if len(parts) > 2 else 'default'
                response = module.get_delete_confirmation_modal(pod_name, d.get('message', {}).get('id'), namespace)
                discord_api.send_response(int_id, int_token, response, 9)

        elif module_name == 'deployments':
            parts = custom_id.split(':')
            action = parts[0] # e.g., deploy_select_menu

            if action == 'deploy_select_menu':
                namespace = parts[1]
                selected_deployment = data['values'][0]
                response = await loop.run_in_executor(None, module.get_deployment_details, selected_deployment, namespace, access_level)
                discord_api.send_response(int_id, int_token, response, 7)
            elif action == 'deploy_list_refresh':
                namespace = parts[1]
                d_refresh = {'data': {'options': [{'name': 'namespace', 'value': namespace}]}}
                response = await loop.run_in_executor(None, module.execute, d_refresh)
                discord_api.send_response(int_id, int_token, response, 7)
            elif action in ['deploy_scale', 'deploy_update_image', 'deploy_delete', 'deploy_rollout_restart', 'deploy_rollback']:
                if action == 'deploy_rollout_restart' and access_level < AccessLevel.DEV:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Dev` role required to restart.", "flags": 64})
                    return
                if action != 'deploy_rollout_restart' and access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": f"🚫 Access denied. `@K8s-Admin` role required for `{action}`.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                if action == 'deploy_scale':
                    modal = { "title": f"Scale {name}", "custom_id": f"deploy_confirm_scale:{name}:{namespace}", "components": [{"type": 1, "components": [{"type": 4, "custom_id": "replica_count", "label": "Desired number of replicas", "style": 1, "placeholder": "e.g., 3", "required": True}]}]}
                    discord_api.send_response(int_id, int_token, modal, 9)
                elif action == 'deploy_update_image':
                    modal = { "title": f"Update image for {name}", "custom_id": f"deploy_confirm_update_image:{name}:{namespace}", "components": [{"type": 1, "components": [{"type": 4, "custom_id": "image_name", "label": "New image (e.g., nginx:1.23)", "style": 1, "placeholder": "nginx:latest", "required": True}]}]}
                    discord_api.send_response(int_id, int_token, modal, 9)
                elif action == 'deploy_delete':
                    modal = { "title": f"Delete {name}?", "custom_id": f"deploy_confirm_delete:{name}:{namespace}", "components": [{"type": 1, "components": [{"type": 4, "custom_id": "confirm_name", "label": "Confirm by typing the name", "style": 1, "placeholder": name, "required": True}]}]}
                    discord_api.send_response(int_id, int_token, modal, 9)
                elif action in ['deploy_rollout_restart', 'deploy_rollback']:
                    func = module.rollout_restart_deployment if action == 'deploy_rollout_restart' else module.rollback_deployment
                    result = await loop.run_in_executor(None, func, name, namespace)
                    discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                    if "✅" in result:
                        log_action = "ROLLOUT RESTART DEPLOYMENT" if action == 'deploy_rollout_restart' else "ROLLBACK DEPLOYMENT"
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, log_action, f"deployment/{name}", f"Namespace: `{namespace}`")

        elif module_name == 'services':
            parts = custom_id.split(':')
            action = parts[0]

            if action == 'svc_select_menu':
                namespace = parts[1]
                selected_service = data['values'][0]
                response_type, response_data = await loop.run_in_executor(None, module.get_service_details, selected_service, namespace, access_level)
                discord_api.send_response(int_id, int_token, response_data, response_type)
            elif action == 'svc_list_refresh':
                namespace = parts[1]
                d_refresh = {'data': {'options': [{'name': 'namespace', 'value': namespace}]}}
                response = await loop.run_in_executor(None, module.execute, d_refresh)
                discord_api.send_response(int_id, int_token, response, 7)
            elif action == 'svc_delete':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                modal = { "title": f"Delete service {name}?", "custom_id": f"svc_confirm_delete:{name}:{namespace}", "components": [{"type": 1, "components": [{"type": 4, "custom_id": "confirm_name", "label": "Confirm by typing the name", "style": 1, "placeholder": name, "required": True}]}]}
                discord_api.send_response(int_id, int_token, modal, 9)

        elif module_name == 'configmaps':
            parts = custom_id.split(':')
            action = parts[0]

            if action == 'cm_select_menu':
                namespace = parts[1]
                selected_cm = data['values'][0]
                response_type, response_data = await loop.run_in_executor(None, module.get_configmap_details, selected_cm, namespace, access_level)
                discord_api.send_response(int_id, int_token, response_data, response_type)
            elif action == 'cm_list_refresh':
                namespace = parts[1]
                d_refresh = {'data': {'options': [{'name': 'namespace', 'value': namespace}]}}
                response = await loop.run_in_executor(None, module.execute, d_refresh)
                discord_api.send_response(int_id, int_token, response, 7)
            elif action == 'cm_delete':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                modal = { "title": f"Delete ConfigMap {name}?", "custom_id": f"cm_confirm_delete:{name}:{namespace}", "components": [{"type": 1, "components": [{"type": 4, "custom_id": "confirm_name", "label": "Confirm by typing the name", "style": 1, "placeholder": name, "required": True}]}]}
                discord_api.send_response(int_id, int_token, modal, 9)

            elif action == 'cm_edit':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to edit.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                modal = {
                    "title": f"Edit a key in {name}",
                    "custom_id": f"cm_confirm_edit:{name}:{namespace}",
                    "components": [
                        {
                            "type": 1,
                            "components": [{"type": 4, "custom_id": "key_to_edit", "label": "Key name to edit/add", "style": 1, "placeholder": "e.g., DATABASE_URL", "required": True}]
                        },
                        {
                            "type": 1,
                            "components": [{"type": 4, "custom_id": "new_value", "label": "New value", "style": 2, "placeholder": "e.g., postgres://...", "required": True}]
                        }
                    ]
                }
                discord_api.send_response(int_id, int_token, modal, 9)

        elif module_name == 'secrets':
            parts = custom_id.split(':')
            action = parts[0]

            if action == 'secret_select_menu':
                namespace = parts[1]
                selected_secret = data['values'][0]
                response_type, response_data = await loop.run_in_executor(None, module.get_secret_details, selected_secret, namespace, access_level)
                discord_api.send_response(int_id, int_token, response_data, response_type)
            elif action == 'secret_list_refresh':
                namespace = parts[1]
                d_refresh = {'data': {'options': [{'name': 'namespace', 'value': namespace}]}}
                response = await loop.run_in_executor(None, module.execute, d_refresh)
                discord_api.send_response(int_id, int_token, response, 7)
            elif action == 'secret_delete':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                modal = { "title": f"Delete Secret {name}?", "custom_id": f"secret_confirm_delete:{name}:{namespace}", "components": [{"type": 1, "components": [{"type": 4, "custom_id": "confirm_name", "label": "Confirm by typing the name", "style": 1, "placeholder": name, "required": True}]}]}
                discord_api.send_response(int_id, int_token, modal, 9)
            elif action == 'secret_edit':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to edit.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                modal = {
                    "title": f"Edit a key in {name}",
                    "custom_id": f"secret_confirm_edit:{name}:{namespace}",
                    "components": [
                        {
                            "type": 1,
                            "components": [{"type": 4, "custom_id": "key_to_edit", "label": "Key name to edit/add", "style": 1, "placeholder": "e.g., DATABASE_PASSWORD", "required": True}]
                        },
                        {
                            "type": 1,
                            "components": [{"type": 4, "custom_id": "new_value", "label": "New value (will be masked)", "style": 2, "placeholder": "Enter the secret value here", "required": True}]
                        }
                    ]
                }
                discord_api.send_response(int_id, int_token, modal, 9)
            elif action == 'secret_delete_key':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete a key.", "flags": 64})
                    return
                name, namespace = parts[1], parts[2]
                modal = {
                    "title": f"Delete a key from {name}",
                    "custom_id": f"secret_confirm_delete_key:{name}:{namespace}",
                    "components": [{
                        "type": 1,
                        "components": [{"type": 4, "custom_id": "key_to_delete", "label": "Name of the key to delete", "style": 1, "placeholder": "e.g., OLD_API_KEY", "required": True}]
                    }]
                }
                discord_api.send_response(int_id, int_token, modal, 9)

        elif module_name == 'events':
            parts = custom_id.split(':')
            action = parts[0]

            if action == 'events_refresh':
                namespace = parts[1] if len(parts) > 1 else 'default'
                d_refresh = {'data': {'options': [{'name': 'namespace', 'value': namespace}]}}
                response = await loop.run_in_executor(None, module.execute, d_refresh)
                discord_api.send_response(int_id, int_token, response, 7)

        elif module_name == 'nodes':
            parts = custom_id.split(':')
            action = parts[0]

            if action == 'nodes_manage':
                response_type, response_data = await loop.run_in_executor(None, module.show_node_management, d)
                discord_api.send_response(int_id, int_token, response_data, response_type)
            elif action == 'nodes_select_node':
                selected_node = data['values'][0]
                response_type, response_data = await loop.run_in_executor(None, module.get_node_details, selected_node, access_level)
                discord_api.send_response(int_id, int_token, response_data, response_type)
            elif action == 'nodes_list_refresh':
                response_data = await loop.run_in_executor(None, module.execute, d)
                discord_api.send_response(int_id, int_token, response_data, 7)
            elif action in ['nodes_cordon', 'nodes_uncordon']:
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required for this action.", "flags": 64})
                    return
                node_name = parts[1]
                schedulable = (action == 'nodes_uncordon')
                response_type, response_data = await loop.run_in_executor(None, module.toggle_node_scheduling, node_name, schedulable, access_level)
                if response_type == 7: # Success updates the message
                    log_action = "UNCORDON NODE" if schedulable else "CORDON NODE"
                    await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, log_action, f"node/{node_name}")
                discord_api.send_response(int_id, int_token, response_data, response_type)
            elif action == 'nodes_drain':
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to drain a node.", "flags": 64})
                    return
                node_name = parts[1]
                modal = {
                    "title": f"Drain node {node_name}?",
                    "custom_id": f"nodes_confirm_drain:{node_name}",
                    "components": [{"type": 1, "components": [{"type": 4, "custom_id": "confirm_name", "label": "Confirm by typing the node name", "style": 1, "placeholder": node_name, "required": True}]}]
                }
                discord_api.send_response(int_id, int_token, modal, 9)

    elif interaction_type == 5:
        custom_id = data.get('custom_id')
        module_name, _, action = custom_id.partition('_')
        
        if module_name == 'deploy': module_name = 'deployments'
        if module_name == 'svc': module_name = 'services'
        if module_name == 'cm': module_name = 'configmaps'
        if module_name == 'secret': module_name = 'secrets'
        if module_name in ['pods', 'k8s']: module_name = 'pods' # Alias
        
        module = command_registry.get(module_name)
        if not module: return

        if module_name == 'pods' and custom_id.startswith("k8s_confirm:"):
            try:
                if access_level < AccessLevel.ADMIN:
                    discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete.", "flags": 64})
                    return

                parts = custom_id.split(':')
                message_id, pod_to_delete, namespace = parts[1], parts[2], (parts[3] if len(parts) > 3 else 'default')
                submitted_input = data['components'][0]['components'][0]['value']
                channel_id = d.get('channel_id')

                if submitted_input == pod_to_delete:
                    discord_api.send_response(int_id, int_token, None, 5) # Defer
                    
                    delete_result = await loop.run_in_executor(None, module.delete_pod, pod_to_delete, namespace)
                    discord_api.send_followup(int_token, delete_result, is_ephemeral=True)
                    if "✅" in delete_result.get("content", ""):
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "DELETE POD", f"pod/{pod_to_delete}", f"Namespace: `{namespace}`")
                    
                    if "✅" in delete_result.get("content", ""):
                        await asyncio.sleep(2)
                else:
                    discord_api.send_response(int_id, int_token, {"content": f"❌ Failure: The name does not match.", "flags": 64})
            except Exception as e:
                discord_api.send_response(int_id, int_token, {"content": f"❌ Internal error: {e}", "flags": 64})

        elif module_name == 'deployments':
            parts = custom_id.split(':')
            action = parts[0] # e.g., deploy_confirm_scale
            name, namespace = parts[1], parts[2]

            if access_level < AccessLevel.ADMIN:
                discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required for this action.", "flags": 64})
                return

            if action == 'deploy_confirm_scale':
                try:
                    replicas = int(data['components'][0]['components'][0]['value'])
                    result = await loop.run_in_executor(None, module.scale_deployment, name, replicas, namespace)
                    discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                    if "✅" in result:
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "SCALE DEPLOYMENT", f"deployment/{name}", f"Namespace: `{namespace}`\nReplicas: `{replicas}`")
                except ValueError:
                    discord_api.send_response(int_id, int_token, {"content": "❌ The number of replicas must be an integer.", "flags": 64})
            elif action == 'deploy_confirm_update_image':
                image = data['components'][0]['components'][0]['value']
                result = await loop.run_in_executor(None, module.update_deployment_image, name, image, namespace)
                discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                if "✅" in result:
                    await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "UPDATE DEPLOYMENT IMAGE", f"deployment/{name}", f"Namespace: `{namespace}`\nImage: `{image}`")
            elif action == 'deploy_confirm_delete':
                confirm_name = data['components'][0]['components'][0]['value']
                if name == confirm_name:
                    result = await loop.run_in_executor(None, module.delete_deployment, name, namespace)
                    discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                    if "✅" in result:
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "DELETE DEPLOYMENT", f"deployment/{name}", f"Namespace: `{namespace}`")
                else:
                    discord_api.send_response(int_id, int_token, {"content": "❌ The name does not match. Aborting.", "flags": 64})
        
        elif module_name == 'services':
            parts = custom_id.split(':')
            name, namespace = parts[1], parts[2]
            
            if access_level < AccessLevel.ADMIN:
                discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required to delete.", "flags": 64})
                return

            confirm_name = data['components'][0]['components'][0]['value']
            if name == confirm_name:
                result = await loop.run_in_executor(None, module.delete_service, name, namespace)
                discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                if "✅" in result:
                    await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "DELETE SERVICE", f"service/{name}", f"Namespace: `{namespace}`")
            else:
                discord_api.send_response(int_id, int_token, {"content": "❌ The name does not match. Aborting.", "flags": 64})

        elif module_name == 'configmaps':
            parts = custom_id.split(':')
            action = parts[0]
            name, namespace = parts[1], parts[2]

            if access_level < AccessLevel.ADMIN:
                discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required for this action.", "flags": 64})
                return

            if action == 'cm_confirm_delete':
                confirm_name = data['components'][0]['components'][0]['value']
                if name == confirm_name:
                    result = await loop.run_in_executor(None, module.delete_configmap, name, namespace)
                    discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                    if "✅" in result:
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "DELETE CONFIGMAP", f"configmap/{name}", f"Namespace: `{namespace}`")
                else:
                    discord_api.send_response(int_id, int_token, {"content": "❌ The name does not match. Aborting.", "flags": 64})
            
            elif action == 'cm_confirm_edit':
                key = data['components'][0]['components'][0]['value']
                value = data['components'][1]['components'][0]['value']
                response_type, response_data = await loop.run_in_executor(None, module.patch_configmap_data, name, key, value, namespace)
                discord_api.send_response(int_id, int_token, response_data, response_type)
                if response_type == 7: # Success
                    await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "PATCH CONFIGMAP", f"configmap/{name}", f"Namespace: `{namespace}`\nKey: `{key}`")

        elif module_name == 'secrets':
            parts = custom_id.split(':')
            action = parts[0]
            name, namespace = parts[1], parts[2]

            if access_level < AccessLevel.ADMIN:
                discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required for this action.", "flags": 64})
                return

            if action == 'secret_confirm_delete':
                confirm_name = data['components'][0]['components'][0]['value']
                if name == confirm_name:
                    result = await loop.run_in_executor(None, module.delete_secret, name, namespace)
                    discord_api.send_response(int_id, int_token, {"content": result, "flags": 64})
                    if "✅" in result:
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "DELETE SECRET", f"secret/{name}", f"Namespace: `{namespace}`")
                else:
                    discord_api.send_response(int_id, int_token, {"content": "❌ The name does not match. Aborting.", "flags": 64})
            
            elif action == 'secret_confirm_edit':
                key = data['components'][0]['components'][0]['value']
                value = data['components'][1]['components'][0]['value']
                response_type, response_data = await loop.run_in_executor(None, module.patch_secret_data, name, key, value, namespace)
                discord_api.send_response(int_id, int_token, response_data, response_type)
                if response_type == 7: # Success
                    await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "PATCH SECRET", f"secret/{name}", f"Namespace: `{namespace}`\nKey: `{key}`")
            
            elif action == 'secret_confirm_delete_key':
                key_to_delete = data['components'][0]['components'][0]['value']
                response_type, response_data = await loop.run_in_executor(None, module.delete_secret_key, name, key_to_delete, namespace)
                discord_api.send_response(int_id, int_token, response_data, response_type)
                if response_type == 7: # Success
                    await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "PATCH SECRET (REMOVE KEY)", f"secret/{name}", f"Namespace: `{namespace}`\nKey: `{key_to_delete}`")

        elif module_name == 'nodes':
            parts = custom_id.split(':')
            action = parts[0]
            node_name = parts[1]

            if access_level < AccessLevel.ADMIN:
                discord_api.send_response(int_id, int_token, {"content": "🚫 Access denied. `@K8s-Admin` role required for this action.", "flags": 64})
                return

            if action == 'nodes_confirm_drain':
                confirm_name = data['components'][0]['components'][0]['value']
                if node_name == confirm_name:
                    discord_api.send_response(int_id, int_token, None, 5)
                    result_message = await loop.run_in_executor(None, module.drain_node, node_name)
                    discord_api.send_followup(int_token, {"content": result_message})
                    if "Drainage" in result_message:
                        await loop.run_in_executor(None, discord_api.send_audit_log, user_obj, "DRAIN NODE", f"node/{node_name}")
                else:
                    discord_api.send_response(int_id, int_token, {"content": "❌ The name does not match. Aborting.", "flags": 64})