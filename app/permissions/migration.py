"""
Permission System Migration Utilities
====================================

Tools for migrating from the legacy permission system to the new hierarchical system.
"""

from app import db
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, ModuloSistema, FuncaoModulo,
    PermissaoUsuario, PerfilUsuario, BatchPermissionOperation
)
from app.auth.models import Usuario
from app.utils.timezone import agora_brasil
import json
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class PermissionMigrator:
    """Handles migration from legacy to new permission system"""
    
    def __init__(self):
        self.stats = {
            'categories_created': 0,
            'modules_created': 0,
            'submodules_created': 0,
            'permissions_migrated': 0,
            'templates_created': 0,
            'errors': []
        }
    
    def migrate_all(self) -> Dict:
        """Run complete migration"""
        logger.info("Starting permission system migration...")
        
        try:
            # Phase 1: Create hierarchical structure
            self._create_permission_categories()
            self._migrate_modules_to_hierarchy()
            
            # Phase 2: Migrate user permissions
            self._migrate_user_permissions()
            
            # Phase 3: Create templates
            self._create_permission_templates()
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Migration completed successfully: {self.stats}")
            return {
                'success': True,
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.session.rollback()
            self.stats['errors'].append(str(e))
            return {
                'success': False,
                'stats': self.stats,
                'error': str(e)
            }
    
    def _create_permission_categories(self):
        """Create default permission categories"""
        categories = [
            {
                'name': 'commercial',
                'display_name': 'Comercial',
                'description': 'Módulos relacionados a vendas e faturamento',
                'icon': '💼',
                'color': '#28a745',
                'order_index': 1
            },
            {
                'name': 'operations',
                'display_name': 'Operações',
                'description': 'Módulos de logística e operações',
                'icon': '🚛',
                'color': '#17a2b8',
                'order_index': 2
            },
            {
                'name': 'financial',
                'display_name': 'Financeiro',
                'description': 'Módulos financeiros e contábeis',
                'icon': '💰',
                'color': '#ffc107',
                'order_index': 3
            },
            {
                'name': 'management',
                'display_name': 'Gestão',
                'description': 'Módulos de gestão e administração',
                'icon': '👥',
                'color': '#6f42c1',
                'order_index': 4
            },
            {
                'name': 'system',
                'display_name': 'Sistema',
                'description': 'Configurações e administração do sistema',
                'icon': '⚙️',
                'color': '#6c757d',
                'order_index': 5
            }
        ]
        
        for cat_data in categories:
            if not PermissionCategory.query.filter_by(name=cat_data['name']).first():
                category = PermissionCategory(**cat_data)
                db.session.add(category)
                self.stats['categories_created'] += 1
                logger.info(f"Created category: {cat_data['name']}")
    
    def _migrate_modules_to_hierarchy(self):
        """Migrate legacy modules to new hierarchical structure"""
        # Module to category mapping
        module_mapping = {
            'faturamento': 'commercial',
            'carteira': 'commercial',
            'monitoramento': 'operations',
            'embarques': 'operations',
            'portaria': 'operations',
            'financeiro': 'financial',
            'usuarios': 'management',
            'admin': 'system'
        }
        
        # Get legacy modules
        legacy_modules = ModuloSistema.query.filter_by(ativo=True).all()
        
        for legacy_module in legacy_modules:
            try:
                # Determine category
                category_name = module_mapping.get(legacy_module.nome, 'system')
                category = PermissionCategory.query.filter_by(name=category_name).first()
                
                if not category:
                    logger.warning(f"Category {category_name} not found for module {legacy_module.nome}")
                    continue
                
                # Check if already migrated
                if PermissionModule.query.filter_by(name=legacy_module.nome).first():
                    logger.info(f"Module {legacy_module.nome} already migrated")
                    continue
                
                # Create new module
                new_module = PermissionModule(
                    category_id=category.id,
                    name=legacy_module.nome,
                    display_name=legacy_module.nome_exibicao,
                    description=legacy_module.descricao,
                    icon=legacy_module.icone,
                    color=legacy_module.cor,
                    order_index=legacy_module.ordem,
                    active=legacy_module.ativo
                )
                db.session.add(new_module)
                db.session.flush()  # Get the ID
                self.stats['modules_created'] += 1
                
                # Migrate functions to submodules
                self._migrate_functions_to_submodules(legacy_module, new_module)
                
                # Update the legacy module to link to new system
                legacy_module.category_id = category.id
                
            except Exception as e:
                logger.error(f"Error migrating module {legacy_module.nome}: {e}")
                self.stats['errors'].append(f"Module {legacy_module.nome}: {str(e)}")
    
    def _migrate_functions_to_submodules(self, legacy_module, new_module):
        """Migrate legacy functions to submodules"""
        # Group functions by logical categories
        function_groups = {
            'listar': {'group': 'view', 'display': 'Visualização'},
            'visualizar': {'group': 'view', 'display': 'Visualização'},
            'criar': {'group': 'manage', 'display': 'Gerenciamento'},
            'editar': {'group': 'manage', 'display': 'Gerenciamento'},
            'deletar': {'group': 'manage', 'display': 'Gerenciamento'},
            'aprovar': {'group': 'approval', 'display': 'Aprovações'},
            'importar': {'group': 'data', 'display': 'Dados'},
            'exportar': {'group': 'data', 'display': 'Dados'},
            'relatorios': {'group': 'reports', 'display': 'Relatórios'},
            'configurar': {'group': 'config', 'display': 'Configurações'}
        }
        
        # Get functions
        functions = FuncaoModulo.query.filter_by(
            modulo_id=legacy_module.id,
            ativo=True
        ).all()
        
        # Group functions
        grouped = {}
        for func in functions:
            # Determine group
            group_info = None
            for prefix, info in function_groups.items():
                if func.nome.startswith(prefix):
                    group_info = info
                    break
            
            if not group_info:
                group_info = {'group': 'general', 'display': 'Geral'}
            
            group_name = group_info['group']
            if group_name not in grouped:
                grouped[group_name] = {
                    'display': group_info['display'],
                    'functions': []
                }
            
            grouped[group_name]['functions'].append(func)
        
        # Create submodules for each group
        for group_name, group_data in grouped.items():
            try:
                # Create submodule
                submodule = PermissionSubModule(
                    module_id=new_module.id,
                    name=group_name,
                    display_name=group_data['display'],
                    description=f"{group_data['display']} - {new_module.display_name}",
                    order_index=len(grouped) - len(group_data['functions']),  # Order by function count
                    active=True
                )
                db.session.add(submodule)
                db.session.flush()
                self.stats['submodules_created'] += 1
                
                # Link functions to submodule
                for func in group_data['functions']:
                    func.submodulo_id = submodule.id
                
            except Exception as e:
                logger.error(f"Error creating submodule {group_name}: {e}")
                self.stats['errors'].append(f"Submodule {group_name}: {str(e)}")
    
    def _migrate_user_permissions(self):
        """Migrate existing user permissions to new system"""
        # Get all active legacy permissions
        legacy_permissions = PermissaoUsuario.query.filter_by(ativo=True).all()
        
        batch_op = BatchPermissionOperation(
            operation_type='MIGRATION',
            description='Migrate legacy permissions to new system',
            executed_by=1,  # System user
            status='IN_PROGRESS'
        )
        db.session.add(batch_op)
        db.session.flush()
        
        migrated = 0
        errors = 0
        
        for legacy_perm in legacy_permissions:
            try:
                # Get the function's new submodule
                func = legacy_perm.funcao
                if not func.submodulo_id:
                    logger.warning(f"Function {func.nome} has no submodule")
                    continue
                
                # Check if already migrated
                existing = UserPermission.query.filter_by(
                    user_id=legacy_perm.usuario_id,
                    entity_type='SUBMODULE',
                    entity_id=func.submodulo_id
                ).first()
                
                if existing:
                    # Update permissions
                    existing.can_view = existing.can_view or legacy_perm.pode_visualizar
                    existing.can_edit = existing.can_edit or legacy_perm.pode_editar
                else:
                    # Create new permission
                    new_perm = UserPermission(
                        user_id=legacy_perm.usuario_id,
                        entity_type='SUBMODULE',
                        entity_id=func.submodulo_id,
                        can_view=legacy_perm.pode_visualizar,
                        can_edit=legacy_perm.pode_editar,
                        can_delete=legacy_perm.pode_editar,  # Assume edit = delete
                        can_export=legacy_perm.pode_visualizar,  # Assume view = export
                        granted_by=legacy_perm.concedida_por,
                        granted_at=legacy_perm.concedida_em,
                        expires_at=legacy_perm.expira_em,
                        reason=legacy_perm.observacoes,
                        active=True
                    )
                    db.session.add(new_perm)
                
                migrated += 1
                
            except Exception as e:
                logger.error(f"Error migrating permission {legacy_perm.id}: {e}")
                errors += 1
        
        # Update batch operation
        batch_op.affected_permissions = migrated
        batch_op.status = 'COMPLETED' if errors == 0 else 'COMPLETED_WITH_ERRORS'
        batch_op.completed_at = agora_brasil()
        batch_op.details = {
            'migrated': migrated,
            'errors': errors,
            'total': len(legacy_permissions)
        }
        
        self.stats['permissions_migrated'] = migrated
        logger.info(f"Migrated {migrated} permissions with {errors} errors")
    
    def _create_permission_templates(self):
        """Create permission templates based on existing profiles"""
        # Get profiles
        profiles = PerfilUsuario.query.filter_by(ativo=True).all()
        
        for profile in profiles:
            try:
                # Skip if template already exists
                if PermissionTemplate.query.filter_by(code=f'profile_{profile.nome}').first():
                    continue
                
                # Build template based on profile
                template_data = self._build_template_for_profile(profile)
                
                template = PermissionTemplate(
                    name=f'Template {profile.descricao}',
                    code=f'profile_{profile.nome}',
                    description=f'Template baseado no perfil {profile.descricao}',
                    category='profiles',
                    template_data=json.dumps(template_data),
                    is_system=True,
                    active=True
                )
                db.session.add(template)
                self.stats['templates_created'] += 1
                
            except Exception as e:
                logger.error(f"Error creating template for profile {profile.nome}: {e}")
                self.stats['errors'].append(f"Template {profile.nome}: {str(e)}")
    
    def _build_template_for_profile(self, profile) -> Dict:
        """Build template permissions based on profile"""
        # Define profile permissions mapping
        profile_permissions = {
            'administrador': {
                'all_categories': ['view', 'edit', 'delete', 'export']
            },
            'gerente_comercial': {
                'commercial': ['view', 'edit', 'export'],
                'operations': ['view', 'edit'],
                'management': ['view', 'edit']
            },
            'financeiro': {
                'commercial': ['view', 'edit', 'export'],
                'financial': ['view', 'edit', 'delete', 'export'],
                'operations': ['view']
            },
            'logistica': {
                'operations': ['view', 'edit', 'delete', 'export'],
                'commercial': ['view']
            },
            'portaria': {
                'operations': {
                    'portaria': ['view', 'edit'],
                    'embarques': ['view']
                }
            },
            'vendedor': {
                'commercial': {
                    'carteira': ['view'],
                    'monitoramento': ['view']
                }
            }
        }
        
        template_perms = []
        perms = profile_permissions.get(profile.nome, {})
        
        for category_name, actions in perms.items():
            if category_name == 'all_categories':
                # Grant permissions to all categories
                categories = PermissionCategory.query.filter_by(active=True).all()
                for cat in categories:
                    template_perms.append({
                        'entity_type': 'CATEGORY',
                        'entity_id': cat.id,
                        'can_view': 'view' in actions,
                        'can_edit': 'edit' in actions,
                        'can_delete': 'delete' in actions,
                        'can_export': 'export' in actions
                    })
            else:
                # Specific category/module permissions
                category = PermissionCategory.query.filter_by(name=category_name).first()
                if not category:
                    continue
                
                if isinstance(actions, list):
                    # Category-level permissions
                    template_perms.append({
                        'entity_type': 'CATEGORY',
                        'entity_id': category.id,
                        'can_view': 'view' in actions,
                        'can_edit': 'edit' in actions,
                        'can_delete': 'delete' in actions,
                        'can_export': 'export' in actions
                    })
                elif isinstance(actions, dict):
                    # Module-specific permissions
                    for module_name, module_actions in actions.items():
                        module = PermissionModule.query.filter_by(
                            category_id=category.id,
                            name=module_name
                        ).first()
                        if module:
                            template_perms.append({
                                'entity_type': 'MODULE',
                                'entity_id': module.id,
                                'can_view': 'view' in module_actions,
                                'can_edit': 'edit' in module_actions,
                                'can_delete': 'delete' in module_actions,
                                'can_export': 'export' in module_actions
                            })
        
        return {
            'permissions': template_perms,
            'profile_id': profile.id
        }


def run_migration():
    """Run the permission system migration"""
    migrator = PermissionMigrator()
    return migrator.migrate_all()


def validate_migration():
    """Validate the migration was successful"""
    checks = {
        'categories_exist': PermissionCategory.query.count() > 0,
        'modules_exist': PermissionModule.query.count() > 0,
        'submodules_exist': PermissionSubModule.query.count() > 0,
        'templates_exist': PermissionTemplate.query.count() > 0,
        'permissions_migrated': UserPermission.query.count() > 0
    }
    
    all_valid = all(checks.values())
    
    return {
        'valid': all_valid,
        'checks': checks
    }


def rollback_migration():
    """Rollback the migration (use with caution)"""
    try:
        # Delete in reverse order due to foreign keys
        UserPermission.query.delete()
        PermissionTemplate.query.delete()
        PermissionSubModule.query.delete()
        PermissionModule.query.delete()
        PermissionCategory.query.delete()
        
        # Clear new fields in legacy tables
        ModuloSistema.query.update({'category_id': None})
        FuncaoModulo.query.update({'submodulo_id': None})
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Migration rolled back successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }