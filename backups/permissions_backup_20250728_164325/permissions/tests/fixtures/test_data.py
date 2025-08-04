"""
Test Fixtures and Data for Permission System
===========================================

Provides test data and fixtures for all permission tests.
"""

import json
from datetime import datetime, timedelta
from app import db
from app.auth.models import Usuario
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao,
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate
)


class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    @staticmethod
    def create_test_users(count=10):
        """Create test users with various profiles"""
        users = []
        profiles = ['vendedor', 'gerente_comercial', 'financeiro', 'logistica', 'portaria']
        
        for i in range(count):
            user = Usuario(
                nome=f'Test User {i}',
                email=f'testuser{i}@example.com',
                perfil=profiles[i % len(profiles)],
                status='ativo',
                senha_hash='$2b$12$dummy_hash_for_testing'
            )
            users.append(user)
            db.session.add(user)
            
        db.session.flush()
        return users
        
    @staticmethod
    def create_complete_hierarchy():
        """Create a complete permission hierarchy for testing"""
        hierarchy = {
            'sales': {
                'name': 'sales',
                'display_name': 'Sales Management',
                'modules': {
                    'customers': {
                        'name': 'customers',
                        'display_name': 'Customer Management',
                        'submodules': [
                            ('list', 'List Customers', 'LOW'),
                            ('view', 'View Customer', 'NORMAL'),
                            ('create', 'Create Customer', 'HIGH'),
                            ('edit', 'Edit Customer', 'HIGH'),
                            ('delete', 'Delete Customer', 'CRITICAL')
                        ]
                    },
                    'orders': {
                        'name': 'orders',
                        'display_name': 'Order Management',
                        'submodules': [
                            ('list', 'List Orders', 'LOW'),
                            ('view', 'View Order', 'NORMAL'),
                            ('create', 'Create Order', 'HIGH'),
                            ('approve', 'Approve Order', 'CRITICAL'),
                            ('cancel', 'Cancel Order', 'HIGH')
                        ]
                    }
                }
            },
            'finance': {
                'name': 'finance',
                'display_name': 'Financial Management',
                'modules': {
                    'invoicing': {
                        'name': 'invoicing',
                        'display_name': 'Invoicing',
                        'submodules': [
                            ('list', 'List Invoices', 'LOW'),
                            ('view', 'View Invoice', 'NORMAL'),
                            ('create', 'Create Invoice', 'HIGH'),
                            ('approve', 'Approve Invoice', 'CRITICAL'),
                            ('void', 'Void Invoice', 'CRITICAL')
                        ]
                    },
                    'payments': {
                        'name': 'payments',
                        'display_name': 'Payment Processing',
                        'submodules': [
                            ('list', 'List Payments', 'LOW'),
                            ('process', 'Process Payment', 'CRITICAL'),
                            ('refund', 'Issue Refund', 'CRITICAL')
                        ]
                    }
                }
            }
        }
        
        created_hierarchy = {}
        
        for cat_key, cat_data in hierarchy.items():
            # Create category
            category = PermissionCategory(
                name=cat_data['name'],
                display_name=cat_data['display_name'],
                created_by=1  # Admin user
            )
            db.session.add(category)
            db.session.flush()
            
            created_hierarchy[cat_key] = {
                'category': category,
                'modules': {}
            }
            
            # Create modules
            for mod_key, mod_data in cat_data['modules'].items():
                module = PermissionModule(
                    category_id=category.id,
                    name=mod_data['name'],
                    display_name=mod_data['display_name'],
                    created_by=1
                )
                db.session.add(module)
                db.session.flush()
                
                created_hierarchy[cat_key]['modules'][mod_key] = {
                    'module': module,
                    'submodules': []
                }
                
                # Create submodules
                for sub_name, sub_display, sub_critical in mod_data['submodules']:
                    submodule = PermissionSubModule(
                        module_id=module.id,
                        name=sub_name,
                        display_name=sub_display,
                        critical_level=sub_critical,
                        created_by=1
                    )
                    db.session.add(submodule)
                    db.session.flush()
                    
                    created_hierarchy[cat_key]['modules'][mod_key]['submodules'].append(submodule)
                    
        db.session.commit()
        return created_hierarchy
        
    @staticmethod
    def create_vendor_team_associations(users, vendors_per_user=3, teams_per_user=2):
        """Create vendor and team associations for users"""
        associations = {'vendors': [], 'teams': []}
        
        for i, user in enumerate(users):
            # Add vendors
            for j in range(vendors_per_user):
                vendor = UsuarioVendedor(
                    usuario_id=user.id,
                    vendedor=f'VENDOR_{i:03d}_{j:02d}',
                    adicionado_por=1,  # Admin
                    observacoes=f'Test vendor for user {user.nome}'
                )
                db.session.add(vendor)
                associations['vendors'].append(vendor)
                
            # Add teams
            for k in range(teams_per_user):
                team = UsuarioEquipeVendas(
                    usuario_id=user.id,
                    equipe_vendas=f'TEAM_{i:02d}_{k}',
                    adicionado_por=1,
                    observacoes=f'Test team for user {user.nome}'
                )
                db.session.add(team)
                associations['teams'].append(team)
                
        db.session.flush()
        return associations
        
    @staticmethod
    def create_permission_templates():
        """Create permission templates for testing"""
        templates = []
        
        # Vendor template
        vendor_template = PermissionTemplate(
            name='Vendor Default Permissions',
            code='vendor_default',
            description='Default permissions for vendor profile',
            category='roles',
            template_data=json.dumps({
                'permissions': [
                    {
                        'category': 'sales',
                        'modules': {
                            'customers': {
                                'list': {'view': True, 'edit': False},
                                'view': {'view': True, 'edit': False}
                            },
                            'orders': {
                                'list': {'view': True, 'edit': False},
                                'view': {'view': True, 'edit': False},
                                'create': {'view': True, 'edit': True}
                            }
                        }
                    }
                ],
                'vendors': ['auto_assign'],
                'teams': []
            }),
            is_system=True,
            created_by=1
        )
        templates.append(vendor_template)
        
        # Manager template
        manager_template = PermissionTemplate(
            name='Manager Full Access',
            code='manager_full',
            description='Full access for managers',
            category='roles',
            template_data=json.dumps({
                'permissions': [
                    {
                        'category': 'sales',
                        'full_access': True
                    },
                    {
                        'category': 'finance',
                        'modules': {
                            'invoicing': {
                                'all': {'view': True, 'edit': True, 'delete': False}
                            }
                        }
                    }
                ],
                'inherit_subordinates': True
            }),
            is_system=True,
            created_by=1
        )
        templates.append(manager_template)
        
        # Custom template
        custom_template = PermissionTemplate(
            name='Custom Department Access',
            code='custom_dept',
            description='Custom permissions for specific department',
            category='custom',
            template_data=json.dumps({
                'permissions': [],
                'dynamic': True
            }),
            created_by=1
        )
        templates.append(custom_template)
        
        for template in templates:
            db.session.add(template)
            
        db.session.flush()
        return templates
        
    @staticmethod
    def create_audit_logs(users, days=7, logs_per_day=50):
        """Create audit log entries for testing"""
        logs = []
        actions = [
            'LOGIN', 'LOGOUT', 'PERMISSION_GRANTED', 'PERMISSION_DENIED',
            'PERMISSION_USED', 'VENDOR_ADDED', 'VENDOR_REMOVED',
            'TEAM_ADDED', 'TEAM_REMOVED', 'PROFILE_UPDATED'
        ]
        
        results = ['SUCESSO', 'SUCESSO', 'SUCESSO', 'NEGADO']  # 75% success rate
        
        for day in range(days):
            for _ in range(logs_per_day):
                user = users[_ % len(users)]
                action = actions[_ % len(actions)]
                
                log = LogPermissao(
                    usuario_id=user.id,
                    acao=action,
                    detalhes=json.dumps({
                        'test_data': True,
                        'day': day,
                        'user': user.email
                    }),
                    resultado=results[_ % len(results)],
                    ip_origem=f'192.168.1.{(_ % 254) + 1}',
                    user_agent='Test Browser',
                    timestamp=datetime.utcnow() - timedelta(days=day, hours=_ % 24)
                )
                logs.append(log)
                db.session.add(log)
                
        db.session.flush()
        return logs
        
    @staticmethod
    def create_complex_permissions(users, hierarchy):
        """Create complex permission scenarios for testing"""
        permissions = []
        
        # Scenario 1: Inherited permissions
        sales_cat = hierarchy['sales']['category']
        finance_cat = hierarchy['finance']['category']
        
        # User 0: Category-level access to sales
        if users:
            perm1 = UserPermission(
                user_id=users[0].id,
                entity_type='CATEGORY',
                entity_id=sales_cat.id,
                can_view=True,
                can_edit=False,
                granted_by=1
            )
            permissions.append(perm1)
            db.session.add(perm1)
            
        # User 1: Module-level override
        if len(users) > 1:
            customers_mod = hierarchy['sales']['modules']['customers']['module']
            perm2 = UserPermission(
                user_id=users[1].id,
                entity_type='MODULE',
                entity_id=customers_mod.id,
                can_view=True,
                can_edit=True,
                can_delete=True,
                custom_override=True,
                granted_by=1
            )
            permissions.append(perm2)
            db.session.add(perm2)
            
        # User 2: Mixed permissions
        if len(users) > 2:
            # View-only on finance category
            perm3 = UserPermission(
                user_id=users[2].id,
                entity_type='CATEGORY',
                entity_id=finance_cat.id,
                can_view=True,
                can_edit=False,
                granted_by=1
            )
            permissions.append(perm3)
            db.session.add(perm3)
            
            # But critical access to specific submodule
            payments_mod = hierarchy['finance']['modules']['payments']['module']
            process_sub = [s for s in hierarchy['finance']['modules']['payments']['submodules'] 
                          if s.name == 'process'][0]
            perm4 = UserPermission(
                user_id=users[2].id,
                entity_type='SUBMODULE',
                entity_id=process_sub.id,
                can_view=True,
                can_edit=True,
                custom_override=True,
                reason='Special approval for payment processing',
                granted_by=1
            )
            permissions.append(perm4)
            db.session.add(perm4)
            
        # User 3: Temporary permissions
        if len(users) > 3:
            orders_mod = hierarchy['sales']['modules']['orders']['module']
            perm5 = UserPermission(
                user_id=users[3].id,
                entity_type='MODULE',
                entity_id=orders_mod.id,
                can_view=True,
                can_edit=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                reason='Temporary access for project',
                granted_by=1
            )
            permissions.append(perm5)
            db.session.add(perm5)
            
        db.session.flush()
        return permissions


class TestScenarios:
    """Pre-built test scenarios"""
    
    @staticmethod
    def setup_basic_scenario():
        """Setup basic testing scenario"""
        # Create users
        users = TestDataGenerator.create_test_users(5)
        
        # Create hierarchy
        hierarchy = TestDataGenerator.create_complete_hierarchy()
        
        # Create associations
        associations = TestDataGenerator.create_vendor_team_associations(users[:3])
        
        # Create some permissions
        permissions = TestDataGenerator.create_complex_permissions(users, hierarchy)
        
        # Create audit logs
        logs = TestDataGenerator.create_audit_logs(users, days=3, logs_per_day=10)
        
        db.session.commit()
        
        return {
            'users': users,
            'hierarchy': hierarchy,
            'associations': associations,
            'permissions': permissions,
            'logs': logs
        }
        
    @staticmethod
    def setup_performance_scenario():
        """Setup scenario for performance testing"""
        # Create many users
        users = TestDataGenerator.create_test_users(100)
        
        # Create large hierarchy
        hierarchy = TestDataGenerator.create_complete_hierarchy()
        
        # Create many associations
        associations = TestDataGenerator.create_vendor_team_associations(
            users, vendors_per_user=10, teams_per_user=5
        )
        
        # Create many permissions
        permissions = []
        for user in users[:50]:
            for cat_data in hierarchy.values():
                # Random permissions
                if hash(user.email + cat_data['category'].name) % 3 == 0:
                    perm = UserPermission(
                        user_id=user.id,
                        entity_type='CATEGORY',
                        entity_id=cat_data['category'].id,
                        can_view=True,
                        can_edit=hash(user.email) % 2 == 0,
                        granted_by=1
                    )
                    permissions.append(perm)
                    db.session.add(perm)
                    
        # Create many logs
        logs = TestDataGenerator.create_audit_logs(users, days=30, logs_per_day=100)
        
        db.session.commit()
        
        return {
            'users': users,
            'hierarchy': hierarchy,
            'associations': associations,
            'permissions': permissions,
            'logs': logs
        }
        
    @staticmethod
    def setup_edge_case_scenario():
        """Setup scenario for edge case testing"""
        users = TestDataGenerator.create_test_users(10)
        hierarchy = TestDataGenerator.create_complete_hierarchy()
        
        # Edge cases
        edge_cases = []
        
        # 1. User with permissions to non-existent entities
        if users:
            perm = UserPermission(
                user_id=users[0].id,
                entity_type='MODULE',
                entity_id=99999,  # Non-existent
                can_view=True,
                granted_by=1
            )
            edge_cases.append(('non_existent_entity', perm))
            db.session.add(perm)
            
        # 2. Circular inheritance attempt
        if len(users) > 1:
            cat = hierarchy['sales']['category']
            mod = hierarchy['sales']['modules']['customers']['module']
            
            # Category permission
            perm1 = UserPermission(
                user_id=users[1].id,
                entity_type='CATEGORY',
                entity_id=cat.id,
                can_view=False,
                can_edit=True,  # Conflicting
                granted_by=1
            )
            db.session.add(perm1)
            
            # Module permission
            perm2 = UserPermission(
                user_id=users[1].id,
                entity_type='MODULE', 
                entity_id=mod.id,
                can_view=True,  # Conflicting
                can_edit=False,
                granted_by=1
            )
            db.session.add(perm2)
            edge_cases.extend([
                ('conflicting_inheritance_cat', perm1),
                ('conflicting_inheritance_mod', perm2)
            ])
            
        # 3. Expired permissions
        if len(users) > 2:
            perm = UserPermission(
                user_id=users[2].id,
                entity_type='CATEGORY',
                entity_id=hierarchy['finance']['category'].id,
                can_view=True,
                can_edit=True,
                expires_at=datetime.utcnow() - timedelta(days=1),  # Already expired
                granted_by=1
            )
            edge_cases.append(('expired_permission', perm))
            db.session.add(perm)
            
        # 4. User with maximum vendors/teams
        if len(users) > 3:
            for i in range(100):  # Many vendors
                vendor = UsuarioVendedor(
                    usuario_id=users[3].id,
                    vendedor=f'MAX_VENDOR_{i:04d}',
                    adicionado_por=1
                )
                db.session.add(vendor)
                
        db.session.commit()
        
        return {
            'users': users,
            'hierarchy': hierarchy,
            'edge_cases': edge_cases
        }


# Fixture data for import
FIXTURE_PROFILES = [
    {'nome': 'test_viewer', 'descricao': 'Test View Only', 'nivel_hierarquico': 1},
    {'nome': 'test_editor', 'descricao': 'Test Editor', 'nivel_hierarquico': 5},
    {'nome': 'test_admin', 'descricao': 'Test Admin', 'nivel_hierarquico': 10}
]

FIXTURE_VENDORS = [
    'TEST_VENDOR_ALPHA',
    'TEST_VENDOR_BETA', 
    'TEST_VENDOR_GAMMA',
    'TEST_VENDOR_DELTA',
    'TEST_VENDOR_EPSILON'
]

FIXTURE_TEAMS = [
    'TEST_TEAM_NORTH',
    'TEST_TEAM_SOUTH',
    'TEST_TEAM_EAST',
    'TEST_TEAM_WEST',
    'TEST_TEAM_CENTRAL'
]