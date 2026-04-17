from enum import StrEnum
from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException, status


class Permission(StrEnum):
    # Contacts
    CONTACTS_READ = "contacts:read"
    CONTACTS_WRITE = "contacts:write"
    CONTACTS_DELETE = "contacts:delete"
    CONTACTS_EXPORT = "contacts:export"
    CONTACTS_IMPORT = "contacts:import"

    # Conversations
    CONVERSATIONS_READ = "conversations:read"
    CONVERSATIONS_WRITE = "conversations:write"
    CONVERSATIONS_ASSIGN = "conversations:assign"

    # Messages
    MESSAGES_READ = "messages:read"
    MESSAGES_SEND = "messages:send"
    MESSAGES_SEND_TEMPLATE = "messages:send_template"

    # Templates
    TEMPLATES_READ = "templates:read"
    TEMPLATES_WRITE = "templates:write"

    # Pipeline
    PIPELINE_READ = "pipeline:read"
    PIPELINE_WRITE = "pipeline:write"
    DEALS_READ = "deals:read"
    DEALS_WRITE = "deals:write"

    # Automations
    AUTOMATIONS_READ = "automations:read"
    AUTOMATIONS_WRITE = "automations:write"

    # Landing Pages
    LANDING_PAGES_READ = "landing_pages:read"
    LANDING_PAGES_WRITE = "landing_pages:write"

    # Analytics
    ANALYTICS_READ = "analytics:read"

    # Billing
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # Admin
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"

    # Webhooks
    WEBHOOKS_READ = "webhooks:read"
    WEBHOOKS_WRITE = "webhooks:write"

    # Shipping
    SHIPPING_READ = "shipping:read"
    SHIPPING_WRITE = "shipping:write"


# Default role permissions mapping
ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "platform_admin": list(Permission),  # All permissions
    "owner": [p for p in Permission if p != Permission.ADMIN_WRITE],
    "admin": [
        p for p in Permission
        if not p.value.startswith("admin:")
    ],
    "manager": [
        Permission.CONTACTS_READ, Permission.CONTACTS_WRITE, Permission.CONTACTS_EXPORT,
        Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_WRITE, Permission.CONVERSATIONS_ASSIGN,
        Permission.MESSAGES_READ, Permission.MESSAGES_SEND, Permission.MESSAGES_SEND_TEMPLATE,
        Permission.TEMPLATES_READ, Permission.TEMPLATES_WRITE,
        Permission.PIPELINE_READ, Permission.PIPELINE_WRITE,
        Permission.DEALS_READ, Permission.DEALS_WRITE,
        Permission.AUTOMATIONS_READ, Permission.AUTOMATIONS_WRITE,
        Permission.LANDING_PAGES_READ, Permission.LANDING_PAGES_WRITE,
        Permission.ANALYTICS_READ,
        Permission.SHIPPING_READ, Permission.SHIPPING_WRITE,
    ],
    "agent": [
        Permission.CONTACTS_READ, Permission.CONTACTS_WRITE,
        Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_WRITE,
        Permission.MESSAGES_READ, Permission.MESSAGES_SEND,
        Permission.TEMPLATES_READ,
        Permission.PIPELINE_READ,
        Permission.DEALS_READ, Permission.DEALS_WRITE,
        Permission.SHIPPING_READ,
    ],
}


def check_permission(user_permissions: list[str], required: Permission) -> bool:
    """Check if user has the required permission."""
    return required.value in user_permissions


def require_permission(permission: Permission) -> Callable:
    """Decorator/dependency factory to require a specific permission."""
    def dependency(current_user: Any) -> Any:
        if not hasattr(current_user, "permissions"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if not check_permission(current_user.permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission.value}",
            )
        return current_user
    return dependency
