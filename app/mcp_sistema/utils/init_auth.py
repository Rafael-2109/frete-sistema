"""
Initialize authentication system with default roles and permissions
"""
import logging
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..models.database import SessionLocal
from ..models.user import User, Role, Permission
from ..core.security import get_password_hash

logger = logging.getLogger(__name__)


# Default permissions for the system
DEFAULT_PERMISSIONS = [
    # User management
    {"resource": "user", "action": "create", "description": "Create new users"},
    {"resource": "user", "action": "read", "description": "View user information"},
    {"resource": "user", "action": "update", "description": "Update user information"},
    {"resource": "user", "action": "delete", "description": "Delete users"},
    
    # Role management
    {"resource": "role", "action": "create", "description": "Create new roles"},
    {"resource": "role", "action": "read", "description": "View roles"},
    {"resource": "role", "action": "update", "description": "Update roles"},
    {"resource": "role", "action": "delete", "description": "Delete roles"},
    
    # Permission management
    {"resource": "permission", "action": "read", "description": "View permissions"},
    
    # Freight management
    {"resource": "freight", "action": "create", "description": "Create freight orders"},
    {"resource": "freight", "action": "read", "description": "View freight orders"},
    {"resource": "freight", "action": "update", "description": "Update freight orders"},
    {"resource": "freight", "action": "delete", "description": "Delete freight orders"},
    {"resource": "freight", "action": "approve", "description": "Approve freight orders"},
    
    # Shipment management
    {"resource": "shipment", "action": "create", "description": "Create shipments"},
    {"resource": "shipment", "action": "read", "description": "View shipments"},
    {"resource": "shipment", "action": "update", "description": "Update shipments"},
    {"resource": "shipment", "action": "delete", "description": "Delete shipments"},
    {"resource": "shipment", "action": "track", "description": "Track shipments"},
    
    # Invoice management
    {"resource": "invoice", "action": "create", "description": "Create invoices"},
    {"resource": "invoice", "action": "read", "description": "View invoices"},
    {"resource": "invoice", "action": "update", "description": "Update invoices"},
    {"resource": "invoice", "action": "delete", "description": "Delete invoices"},
    {"resource": "invoice", "action": "approve", "description": "Approve invoices"},
    
    # Report management
    {"resource": "report", "action": "create", "description": "Create reports"},
    {"resource": "report", "action": "read", "description": "View reports"},
    {"resource": "report", "action": "export", "description": "Export reports"},
    
    # MCP management
    {"resource": "mcp", "action": "read", "description": "View MCP information"},
    {"resource": "mcp", "action": "execute", "description": "Execute MCP tools"},
    {"resource": "mcp", "action": "manage", "description": "Manage MCP configuration"},
    
    # API management
    {"resource": "api", "action": "manage", "description": "Manage API keys and access"},
]


# Default roles
DEFAULT_ROLES = [
    {
        "name": "superadmin",
        "description": "Super Administrator with full access",
        "permissions": ["*"],  # All permissions
        "is_system": True
    },
    {
        "name": "admin",
        "description": "Administrator with management access",
        "permissions": [
            "user:*", "role:*", "permission:read",
            "freight:*", "shipment:*", "invoice:*",
            "report:*", "mcp:*", "api:manage"
        ],
        "is_system": True
    },
    {
        "name": "manager",
        "description": "Manager with operational access",
        "permissions": [
            "user:read", "user:update",
            "freight:*", "shipment:*", "invoice:*",
            "report:*", "mcp:read", "mcp:execute"
        ],
        "is_system": True
    },
    {
        "name": "operator",
        "description": "Operator with basic access",
        "permissions": [
            "freight:create", "freight:read", "freight:update",
            "shipment:create", "shipment:read", "shipment:update", "shipment:track",
            "invoice:read", "report:read"
        ],
        "is_system": True
    },
    {
        "name": "viewer",
        "description": "Viewer with read-only access",
        "permissions": [
            "freight:read", "shipment:read", "shipment:track",
            "invoice:read", "report:read"
        ],
        "is_system": True
    },
    {
        "name": "mcp_client",
        "description": "MCP Client with API access",
        "permissions": [
            "mcp:read", "mcp:execute",
            "freight:read", "shipment:read"
        ],
        "is_system": True
    }
]


def create_permissions(db: Session) -> Dict[str, Permission]:
    """
    Create default permissions
    """
    permissions = {}
    
    for perm_data in DEFAULT_PERMISSIONS:
        name = Permission.create_name(perm_data["resource"], perm_data["action"])
        
        # Check if permission already exists
        permission = db.query(Permission).filter(Permission.name == name).first()
        
        if not permission:
            permission = Permission(
                name=name,
                resource=perm_data["resource"],
                action=perm_data["action"],
                description=perm_data["description"],
                is_system=True
            )
            db.add(permission)
            logger.info(f"Created permission: {name}")
        
        permissions[name] = permission
    
    db.commit()
    return permissions


def create_roles(db: Session, permissions: Dict[str, Permission]) -> Dict[str, Role]:
    """
    Create default roles
    """
    roles = {}
    
    for role_data in DEFAULT_ROLES:
        # Check if role already exists
        role = db.query(Role).filter(Role.name == role_data["name"]).first()
        
        if not role:
            role = Role(
                name=role_data["name"],
                description=role_data["description"],
                is_system=role_data["is_system"]
            )
            db.add(role)
            
            # Add permissions
            for perm_pattern in role_data["permissions"]:
                if perm_pattern == "*":
                    # Add all permissions
                    for perm in permissions.values():
                        role.permissions.append(perm)
                elif perm_pattern.endswith(":*"):
                    # Add all permissions for a resource
                    resource = perm_pattern.split(":")[0]
                    for perm_name, perm in permissions.items():
                        if perm.resource == resource:
                            role.permissions.append(perm)
                else:
                    # Add specific permission
                    if perm_pattern in permissions:
                        role.permissions.append(permissions[perm_pattern])
            
            logger.info(f"Created role: {role_data['name']} with {len(role.permissions)} permissions")
        
        roles[role_data["name"]] = role
    
    db.commit()
    return roles


def create_superuser(db: Session, roles: Dict[str, Role]) -> User:
    """
    Create default superuser
    """
    # Check if superuser already exists
    superuser = db.query(User).filter(User.username == "admin").first()
    
    if not superuser:
        superuser = User(
            username="admin",
            email="admin@mcp-sistema.com",
            full_name="System Administrator",
            is_active=True,
            is_verified=True,
            is_superuser=True
        )
        superuser.set_password("admin123")  # Change this in production!
        
        # Add superadmin role
        if "superadmin" in roles:
            superuser.roles.append(roles["superadmin"])
        
        db.add(superuser)
        db.commit()
        
        logger.info("Created superuser: admin")
        logger.warning("DEFAULT SUPERUSER PASSWORD IS 'admin123' - CHANGE IT IMMEDIATELY!")
    
    return superuser


def init_auth_system():
    """
    Initialize the authentication system with default data
    """
    db = SessionLocal()
    
    try:
        logger.info("Initializing authentication system...")
        
        # Create permissions
        permissions = create_permissions(db)
        logger.info(f"Initialized {len(permissions)} permissions")
        
        # Create roles
        roles = create_roles(db, permissions)
        logger.info(f"Initialized {len(roles)} roles")
        
        # Create superuser
        superuser = create_superuser(db, roles)
        logger.info("Initialized superuser")
        
        # Create sample users for testing
        if db.query(User).count() == 1:  # Only superuser exists
            # Create manager user
            manager_user = User(
                username="manager",
                email="manager@mcp-sistema.com",
                full_name="Test Manager",
                is_active=True,
                is_verified=True
            )
            manager_user.set_password("manager123")
            manager_user.roles.append(roles["manager"])
            db.add(manager_user)
            
            # Create operator user
            operator_user = User(
                username="operator",
                email="operator@mcp-sistema.com",
                full_name="Test Operator",
                is_active=True,
                is_verified=True
            )
            operator_user.set_password("operator123")
            operator_user.roles.append(roles["operator"])
            db.add(operator_user)
            
            # Create MCP client user
            mcp_user = User(
                username="mcp_client",
                email="mcp@mcp-sistema.com",
                full_name="MCP Client",
                is_active=True,
                is_verified=True,
                mcp_client_id="mcp_client_001"
            )
            mcp_user.set_password("mcp123")
            mcp_user.roles.append(roles["mcp_client"])
            db.add(mcp_user)
            
            db.commit()
            logger.info("Created sample users for testing")
        
        logger.info("Authentication system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing auth system: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_auth_system()