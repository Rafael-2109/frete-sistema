"""
Base Test Class for Permission System
====================================

Provides common setup and utilities for all permission tests.
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user

from app import create_app, db
from app.auth.models import Usuario
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao,
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, inicializar_dados_padrao
)


class BasePermissionTest(unittest.TestCase):
    """Base test class with common setup for permission tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class - runs once for all tests"""
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()
        
    @classmethod
    def tearDownClass(cls):
        """Tear down test class"""
        cls.app_context.pop()
        
    def setUp(self):
        """Set up each test"""
        # Create all tables
        db.create_all()
        
        # Initialize default data
        inicializar_dados_padrao()
        
        # Create test users
        self.admin_user = self._create_test_user(
            nome='Admin User',
            email='admin@test.com',
            perfil='administrador',
            is_admin=True
        )
        
        self.regular_user = self._create_test_user(
            nome='Regular User',
            email='user@test.com',
            perfil='vendedor'
        )
        
        self.manager_user = self._create_test_user(
            nome='Manager User',
            email='manager@test.com',
            perfil='gerente_comercial'
        )
        
        db.session.commit()
        
    def tearDown(self):
        """Tear down each test"""
        db.session.remove()
        db.drop_all()
        
    def _create_test_user(self, nome, email, perfil='vendedor', is_admin=False):
        """Create a test user"""
        user = Usuario(
            nome=nome,
            email=email,
            perfil=perfil,
            status='ativo',
            senha_hash='$2b$12$test_hash'  # Mock password hash
        )
        if is_admin:
            user.is_admin = True
        db.session.add(user)
        db.session.flush()
        return user
        
    def _login_user(self, user):
        """Login a user for tests"""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
                
    def _create_test_permission(self, user, module_name, function_name, 
                              can_view=True, can_edit=False):
        """Create a test permission"""
        module = ModuloSistema.query.filter_by(nome=module_name).first()
        if not module:
            return None
            
        function = FuncaoModulo.query.filter_by(
            modulo_id=module.id,
            nome=function_name
        ).first()
        if not function:
            return None
            
        permission = PermissaoUsuario(
            usuario_id=user.id,
            funcao_id=function.id,
            pode_visualizar=can_view,
            pode_editar=can_edit,
            concedida_por=self.admin_user.id
        )
        db.session.add(permission)
        db.session.flush()
        return permission
        
    def _create_hierarchical_permission(self, user, entity_type, entity_id,
                                      can_view=True, can_edit=False, 
                                      can_delete=False, can_export=False):
        """Create a hierarchical permission"""
        permission = UserPermission(
            user_id=user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            can_view=can_view,
            can_edit=can_edit,
            can_delete=can_delete,
            can_export=can_export,
            granted_by=self.admin_user.id
        )
        db.session.add(permission)
        db.session.flush()
        return permission
        
    def _create_test_category(self, name, display_name):
        """Create a test permission category"""
        category = PermissionCategory(
            name=name,
            display_name=display_name,
            created_by=self.admin_user.id
        )
        db.session.add(category)
        db.session.flush()
        return category
        
    def _create_test_module(self, category, name, display_name):
        """Create a test permission module"""
        module = PermissionModule(
            category_id=category.id,
            name=name,
            display_name=display_name,
            created_by=self.admin_user.id
        )
        db.session.add(module)
        db.session.flush()
        return module
        
    def _create_test_submodule(self, module, name, display_name, critical_level='NORMAL'):
        """Create a test permission submodule"""
        submodule = PermissionSubModule(
            module_id=module.id,
            name=name,
            display_name=display_name,
            critical_level=critical_level,
            created_by=self.admin_user.id
        )
        db.session.add(submodule)
        db.session.flush()
        return submodule
        
    def _add_vendor_to_user(self, user, vendor_name):
        """Add vendor to user"""
        vendor = UsuarioVendedor(
            usuario_id=user.id,
            vendedor=vendor_name,
            adicionado_por=self.admin_user.id
        )
        db.session.add(vendor)
        db.session.flush()
        return vendor
        
    def _add_team_to_user(self, user, team_name):
        """Add team to user"""
        team = UsuarioEquipeVendas(
            usuario_id=user.id,
            equipe_vendas=team_name,
            adicionado_por=self.admin_user.id
        )
        db.session.add(team)
        db.session.flush()
        return team
        
    @contextmanager
    def assert_max_queries(self, num):
        """Context manager to assert maximum number of queries"""
        # This would integrate with SQLAlchemy query counter
        # For now, just a placeholder
        yield
        
    def assert_permission_granted(self, user, module, function):
        """Assert that user has permission"""
        from app.permissions.services import PermissaoService
        has_permission = PermissaoService.usuario_tem_permissao(
            user.id, module, function
        )
        self.assertTrue(has_permission, 
                       f"User {user.nome} should have permission for {module}.{function}")
        
    def assert_permission_denied(self, user, module, function):
        """Assert that user doesn't have permission"""
        from app.permissions.services import PermissaoService
        has_permission = PermissaoService.usuario_tem_permissao(
            user.id, module, function
        )
        self.assertFalse(has_permission,
                        f"User {user.nome} should NOT have permission for {module}.{function}")
        
    def assert_audit_logged(self, action, user_id=None, result='SUCESSO'):
        """Assert that an audit log entry exists"""
        query = LogPermissao.query.filter_by(acao=action, resultado=result)
        if user_id:
            query = query.filter_by(usuario_id=user_id)
        log = query.first()
        self.assertIsNotNone(log, f"Audit log for action {action} not found")
        return log