"""
Unit Tests for Permission Models
================================

Tests for all permission system models including:
- Profile models
- Module and function models
- Permission models
- Vendor and team associations
- Audit logging
"""

import unittest
from datetime import datetime, timedelta
from app.permissions.tests.base_test import BasePermissionTest
from app import db
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao,
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate
)


class TestPerfilUsuario(BasePermissionTest):
    """Test PerfilUsuario model"""
    
    def test_create_profile(self):
        """Test creating a user profile"""
        profile = PerfilUsuario(
            nome='test_profile',
            descricao='Test Profile',
            nivel_hierarquico=5,
            criado_por=self.admin_user.id
        )
        db.session.add(profile)
        db.session.commit()
        
        self.assertIsNotNone(profile.id)
        self.assertEqual(profile.nome, 'test_profile')
        self.assertEqual(profile.nivel_hierarquico, 5)
        self.assertTrue(profile.ativo)
        
    def test_default_profiles_created(self):
        """Test that default profiles are created"""
        profiles = PerfilUsuario.query.all()
        profile_names = [p.nome for p in profiles]
        
        expected_profiles = [
            'administrador', 'gerente_comercial', 'financeiro',
            'logistica', 'portaria', 'vendedor'
        ]
        
        for expected in expected_profiles:
            self.assertIn(expected, profile_names)
            
    def test_profile_hierarchy(self):
        """Test profile hierarchy levels"""
        admin = PerfilUsuario.query.filter_by(nome='administrador').first()
        vendor = PerfilUsuario.query.filter_by(nome='vendedor').first()
        
        self.assertGreater(admin.nivel_hierarquico, vendor.nivel_hierarquico)


class TestModuloSistema(BasePermissionTest):
    """Test ModuloSistema model"""
    
    def test_create_module(self):
        """Test creating a system module"""
        module = ModuloSistema(
            nome='test_module',
            nome_exibicao='Test Module',
            descricao='Test module description',
            icone='🧪',
            cor='#123456',
            ordem=99
        )
        db.session.add(module)
        db.session.commit()
        
        self.assertIsNotNone(module.id)
        self.assertEqual(module.nome, 'test_module')
        self.assertTrue(module.ativo)
        
    def test_default_modules_created(self):
        """Test that default modules are created"""
        modules = ModuloSistema.query.all()
        module_names = [m.nome for m in modules]
        
        expected_modules = [
            'faturamento', 'carteira', 'monitoramento', 'embarques',
            'portaria', 'financeiro', 'usuarios', 'admin'
        ]
        
        for expected in expected_modules:
            self.assertIn(expected, module_names)
            
    def test_module_ordering(self):
        """Test module ordering"""
        modules = ModuloSistema.query.order_by(ModuloSistema.ordem).all()
        
        # Check that modules are ordered correctly
        for i in range(1, len(modules)):
            self.assertGreaterEqual(modules[i].ordem, modules[i-1].ordem)


class TestFuncaoModulo(BasePermissionTest):
    """Test FuncaoModulo model"""
    
    def test_create_function(self):
        """Test creating a module function"""
        module = ModuloSistema.query.filter_by(nome='faturamento').first()
        
        function = FuncaoModulo(
            modulo_id=module.id,
            nome='test_function',
            nome_exibicao='Test Function',
            descricao='Test function description',
            nivel_critico='ALTO'
        )
        db.session.add(function)
        db.session.commit()
        
        self.assertIsNotNone(function.id)
        self.assertEqual(function.nome, 'test_function')
        self.assertEqual(function.nome_completo, 'faturamento.test_function')
        
    def test_function_unique_constraint(self):
        """Test that function names are unique within module"""
        module = ModuloSistema.query.filter_by(nome='faturamento').first()
        
        # Try to create duplicate function
        func1 = FuncaoModulo(modulo_id=module.id, nome='duplicate', nome_exibicao='Dup 1')
        db.session.add(func1)
        db.session.commit()
        
        func2 = FuncaoModulo(modulo_id=module.id, nome='duplicate', nome_exibicao='Dup 2')
        db.session.add(func2)
        
        with self.assertRaises(Exception):
            db.session.commit()
            
    def test_critical_levels(self):
        """Test function critical levels"""
        critical_functions = FuncaoModulo.query.filter_by(nivel_critico='CRITICO').all()
        
        # Check that critical functions exist
        self.assertGreater(len(critical_functions), 0)
        
        # Check specific critical functions
        for func in critical_functions:
            self.assertIn(func.nome, ['importar', 'acesso_total', 'configuracoes'])


class TestPermissaoUsuario(BasePermissionTest):
    """Test PermissaoUsuario model"""
    
    def test_create_permission(self):
        """Test creating a user permission"""
        permission = self._create_test_permission(
            self.regular_user, 'faturamento', 'listar',
            can_view=True, can_edit=False
        )
        
        self.assertIsNotNone(permission.id)
        self.assertTrue(permission.pode_visualizar)
        self.assertFalse(permission.pode_editar)
        self.assertEqual(permission.nivel_acesso, 'Visualizar')
        
    def test_permission_expiration(self):
        """Test permission expiration"""
        permission = self._create_test_permission(
            self.regular_user, 'faturamento', 'listar'
        )
        
        # Set expiration to past
        permission.expira_em = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
        
        self.assertTrue(permission.esta_expirada)
        
    def test_permission_unique_constraint(self):
        """Test that user can't have duplicate permissions"""
        # Create first permission
        self._create_test_permission(
            self.regular_user, 'faturamento', 'listar'
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            self._create_test_permission(
                self.regular_user, 'faturamento', 'listar'
            )
            db.session.commit()


class TestUsuarioVendedor(BasePermissionTest):
    """Test UsuarioVendedor model"""
    
    def test_add_vendor_to_user(self):
        """Test adding vendor to user"""
        vendor = self._add_vendor_to_user(self.regular_user, 'VENDOR001')
        
        self.assertIsNotNone(vendor.id)
        self.assertEqual(vendor.vendedor, 'VENDOR001')
        self.assertTrue(vendor.ativo)
        
    def test_get_user_vendors(self):
        """Test getting user vendors"""
        self._add_vendor_to_user(self.regular_user, 'VENDOR001')
        self._add_vendor_to_user(self.regular_user, 'VENDOR002')
        
        vendors = UsuarioVendedor.get_vendedores_usuario(self.regular_user.id)
        
        self.assertEqual(len(vendors), 2)
        self.assertIn('VENDOR001', vendors)
        self.assertIn('VENDOR002', vendors)
        
    def test_vendor_unique_constraint(self):
        """Test that user can't have duplicate vendors"""
        self._add_vendor_to_user(self.regular_user, 'VENDOR001')
        
        with self.assertRaises(Exception):
            self._add_vendor_to_user(self.regular_user, 'VENDOR001')
            db.session.commit()
            
    def test_vendor_soft_delete(self):
        """Test soft deleting vendor"""
        vendor = self._add_vendor_to_user(self.regular_user, 'VENDOR001')
        
        # Soft delete
        vendor.ativo = False
        db.session.commit()
        
        # Check it's not in active list
        vendors = UsuarioVendedor.get_vendedores_usuario(self.regular_user.id)
        self.assertEqual(len(vendors), 0)


class TestUsuarioEquipeVendas(BasePermissionTest):
    """Test UsuarioEquipeVendas model"""
    
    def test_add_team_to_user(self):
        """Test adding team to user"""
        team = self._add_team_to_user(self.regular_user, 'TEAM001')
        
        self.assertIsNotNone(team.id)
        self.assertEqual(team.equipe_vendas, 'TEAM001')
        self.assertTrue(team.ativo)
        
    def test_get_user_teams(self):
        """Test getting user teams"""
        self._add_team_to_user(self.regular_user, 'TEAM001')
        self._add_team_to_user(self.regular_user, 'TEAM002')
        
        teams = UsuarioEquipeVendas.get_equipes_usuario(self.regular_user.id)
        
        self.assertEqual(len(teams), 2)
        self.assertIn('TEAM001', teams)
        self.assertIn('TEAM002', teams)


class TestLogPermissao(BasePermissionTest):
    """Test LogPermissao model"""
    
    def test_log_action(self):
        """Test logging an action"""
        log = LogPermissao.registrar(
            usuario_id=self.regular_user.id,
            acao='LOGIN',
            detalhes='{"method": "password"}',
            resultado='SUCESSO',
            ip_origem='127.0.0.1',
            user_agent='Test Browser'
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.acao, 'LOGIN')
        self.assertEqual(log.resultado, 'SUCESSO')
        
    def test_search_user_activity(self):
        """Test searching user activity"""
        # Create some logs
        for i in range(5):
            LogPermissao.registrar(
                usuario_id=self.regular_user.id,
                acao=f'ACTION_{i}',
                resultado='SUCESSO'
            )
            
        activities = LogPermissao.buscar_atividade_usuario(
            self.regular_user.id, limite=3
        )
        
        self.assertEqual(len(activities), 3)
        
    def test_search_denied_attempts(self):
        """Test searching denied attempts"""
        # Create denied logs
        for i in range(3):
            LogPermissao.registrar(
                usuario_id=self.regular_user.id,
                acao='PERMISSION_DENIED',
                resultado='NEGADO'
            )
            
        denied = LogPermissao.buscar_tentativas_negadas(dias=1)
        
        self.assertGreaterEqual(len(denied), 3)


class TestHierarchicalPermissions(BasePermissionTest):
    """Test hierarchical permission models"""
    
    def test_create_category(self):
        """Test creating permission category"""
        category = self._create_test_category('test_cat', 'Test Category')
        
        self.assertIsNotNone(category.id)
        self.assertEqual(category.name, 'test_cat')
        self.assertTrue(category.active)
        
    def test_create_module_in_category(self):
        """Test creating module in category"""
        category = self._create_test_category('test_cat', 'Test Category')
        module = self._create_test_module(category, 'test_mod', 'Test Module')
        
        self.assertEqual(module.category_id, category.id)
        self.assertEqual(module.category.name, 'test_cat')
        
    def test_create_submodule_in_module(self):
        """Test creating submodule in module"""
        category = self._create_test_category('test_cat', 'Test Category')
        module = self._create_test_module(category, 'test_mod', 'Test Module')
        submodule = self._create_test_submodule(
            module, 'test_sub', 'Test SubModule', 'HIGH'
        )
        
        self.assertEqual(submodule.module_id, module.id)
        self.assertEqual(submodule.critical_level, 'HIGH')
        
    def test_hierarchical_permission_inheritance(self):
        """Test permission inheritance in hierarchy"""
        category = self._create_test_category('test_cat', 'Test Category')
        module = self._create_test_module(category, 'test_mod', 'Test Module')
        submodule = self._create_test_submodule(module, 'test_sub', 'Test SubModule')
        
        # Grant category-level permission
        cat_perm = self._create_hierarchical_permission(
            self.regular_user, 'CATEGORY', category.id,
            can_view=True, can_edit=True
        )
        
        # Check that permission exists at category level
        self.assertTrue(cat_perm.can_view)
        self.assertTrue(cat_perm.can_edit)
        
        # In real implementation, this would be inherited to modules/submodules
        # through the service layer


class TestPermissionTemplate(BasePermissionTest):
    """Test PermissionTemplate model"""
    
    def test_create_template(self):
        """Test creating permission template"""
        template_data = {
            'permissions': {
                'faturamento': {
                    'listar': 'view',
                    'editar': 'edit'
                }
            }
        }
        
        template = PermissionTemplate(
            name='Test Template',
            code='test_template',
            description='Test template description',
            template_data=str(template_data),
            created_by=self.admin_user.id
        )
        db.session.add(template)
        db.session.commit()
        
        self.assertIsNotNone(template.id)
        self.assertEqual(template.code, 'test_template')
        self.assertTrue(template.active)
        
    def test_template_unique_code(self):
        """Test that template codes are unique"""
        template1 = PermissionTemplate(
            name='Template 1',
            code='unique_code',
            template_data='{}',
            created_by=self.admin_user.id
        )
        db.session.add(template1)
        db.session.commit()
        
        template2 = PermissionTemplate(
            name='Template 2',
            code='unique_code',
            template_data='{}',
            created_by=self.admin_user.id
        )
        db.session.add(template2)
        
        with self.assertRaises(Exception):
            db.session.commit()


if __name__ == '__main__':
    unittest.main()