from enum import IntEnum

class AccessLevel(IntEnum):
    NONE = 0
    VIEWER = 1
    DEV = 2
    ADMIN = 3

def get_user_access_level(user_payload, configured_roles):
    if not user_payload:
        return AccessLevel.NONE

    user_roles = set(user_payload.get('roles', []))

    if configured_roles.get('admin') and configured_roles['admin'] in user_roles:
        return AccessLevel.ADMIN
    if configured_roles.get('dev') and configured_roles['dev'] in user_roles:
        return AccessLevel.DEV
    if configured_roles.get('viewer') and configured_roles['viewer'] in user_roles:
        return AccessLevel.VIEWER
        
    return AccessLevel.NONE