"""
Performance Tests for Permission System
======================================

Tests system performance under various loads including:
- Query performance
- Bulk operations
- Concurrent access
- Memory usage
- Cache effectiveness
"""

import unittest
import time
import random
import threading
import psutil
import os
from datetime import datetime, timedelta
from app.permissions.tests.base_test import BasePermissionTest
from app import db
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissaoUsuario, UsuarioVendedor,
    LogPermissao, FuncaoModulo, ModuloSistema
)
from app.permissions.services import PermissaoService


class TestQueryPerformance(BasePermissionTest):
    """Test query performance under various conditions"""
    
    def setUp(self):
        """Set up performance test data"""
        super().setUp()
        self._create_large_dataset()
        
    def _create_large_dataset(self):
        """Create a large dataset for performance testing"""
        # Create 10 categories
        self.categories = []
        for i in range(10):
            cat = self._create_test_category(f'perf_cat_{i}', f'Performance Category {i}')
            self.categories.append(cat)
            
        # Create 50 modules (5 per category)
        self.modules = []
        for cat in self.categories:
            for j in range(5):
                mod = self._create_test_module(cat, f'perf_mod_{cat.id}_{j}', f'Module {j}')
                self.modules.append(mod)
                
        # Create 200 submodules (4 per module)
        self.submodules = []
        for mod in self.modules:
            for k in range(4):
                sub = self._create_test_submodule(mod, f'perf_sub_{mod.id}_{k}', f'SubModule {k}')
                self.submodules.append(sub)
                
        # Create 100 test users
        self.test_users = []
        for i in range(100):
            user = self._create_test_user(
                nome=f'Perf User {i}',
                email=f'perf{i}@test.com',
                perfil='vendedor'
            )
            self.test_users.append(user)
            
        db.session.commit()
        
    def test_permission_check_performance(self):
        """Test performance of permission checks"""
        # Grant various permissions
        for i, user in enumerate(self.test_users[:50]):
            # Grant some permissions
            for j in range(10):
                module_idx = (i + j) % len(self.modules)
                self._create_hierarchical_permission(
                    user, 'MODULE', self.modules[module_idx].id,
                    can_view=True, can_edit=(j % 2 == 0)
                )
        db.session.commit()
        
        # Test permission check performance
        check_times = []
        
        for _ in range(100):
            user = random.choice(self.test_users[:50])
            module = random.choice(self.modules)
            
            start_time = time.time()
            
            # Check permission
            has_perm = UserPermission.query.filter_by(
                user_id=user.id,
                entity_type='MODULE',
                entity_id=module.id,
                active=True
            ).first()
            
            end_time = time.time()
            check_times.append((end_time - start_time) * 1000)
            
        avg_time = sum(check_times) / len(check_times)
        max_time = max(check_times)
        
        # Performance assertions
        self.assertLess(avg_time, 10)  # Average under 10ms
        self.assertLess(max_time, 50)  # Max under 50ms
        
    def test_hierarchical_permission_resolution(self):
        """Test performance of hierarchical permission resolution"""
        # Create complex permission hierarchy
        user = self.test_users[0]
        
        # Grant permissions at different levels
        self._create_hierarchical_permission(
            user, 'CATEGORY', self.categories[0].id,
            can_view=True, can_edit=False
        )
        
        # Override at module level for some modules
        for module in self.modules[:10]:
            if module.category_id == self.categories[0].id:
                self._create_hierarchical_permission(
                    user, 'MODULE', module.id,
                    can_view=True, can_edit=True
                )
                
        db.session.commit()
        
        # Test resolution performance
        resolution_times = []
        
        for submodule in self.submodules[:50]:
            start_time = time.time()
            
            # Resolve effective permissions (would check module, then category)
            sub_perm = UserPermission.query.filter_by(
                user_id=user.id,
                entity_type='SUBMODULE',
                entity_id=submodule.id,
                active=True
            ).first()
            
            if not sub_perm:
                # Check module level
                mod_perm = UserPermission.query.filter_by(
                    user_id=user.id,
                    entity_type='MODULE',
                    entity_id=submodule.module_id,
                    active=True
                ).first()
                
                if not mod_perm:
                    # Check category level
                    module = PermissionModule.query.get(submodule.module_id)
                    if module:
                        cat_perm = UserPermission.query.filter_by(
                            user_id=user.id,
                            entity_type='CATEGORY',
                            entity_id=module.category_id,
                            active=True
                        ).first()
                        
            end_time = time.time()
            resolution_times.append((end_time - start_time) * 1000)
            
        avg_resolution_time = sum(resolution_times) / len(resolution_times)
        self.assertLess(avg_resolution_time, 20)  # Under 20ms average
        
    def test_bulk_permission_query(self):
        """Test performance of bulk permission queries"""
        # Grant many permissions
        for user in self.test_users[:20]:
            for module in self.modules[:20]:
                self._create_hierarchical_permission(
                    user, 'MODULE', module.id,
                    can_view=True, can_edit=random.choice([True, False])
                )
        db.session.commit()
        
        # Test bulk query performance
        start_time = time.time()
        
        # Get all permissions for multiple users
        user_ids = [u.id for u in self.test_users[:20]]
        all_permissions = UserPermission.query.filter(
            UserPermission.user_id.in_(user_ids),
            UserPermission.active == True
        ).all()
        
        end_time = time.time()
        query_time = (end_time - start_time) * 1000
        
        self.assertGreater(len(all_permissions), 0)
        self.assertLess(query_time, 500)  # Under 500ms for bulk query


class TestBulkOperationPerformance(BasePermissionTest):
    """Test performance of bulk operations"""
    
    def test_bulk_permission_assignment(self):
        """Test bulk permission assignment performance"""
        # Create test data
        users = []
        for i in range(50):
            user = self._create_test_user(
                nome=f'Bulk User {i}',
                email=f'bulk{i}@test.com'
            )
            users.append(user)
            
        category = self._create_test_category('bulk_test', 'Bulk Test')
        modules = []
        for i in range(10):
            mod = self._create_test_module(category, f'bulk_mod_{i}', f'Bulk Module {i}')
            modules.append(mod)
            
        db.session.commit()
        
        # Measure bulk assignment time
        start_time = time.time()
        
        # Assign permissions in bulk
        permissions = []
        for user in users:
            for module in modules:
                perm = UserPermission(
                    user_id=user.id,
                    entity_type='MODULE',
                    entity_id=module.id,
                    can_view=True,
                    can_edit=False,
                    granted_by=self.admin_user.id
                )
                permissions.append(perm)
                
        db.session.bulk_save_objects(permissions)
        db.session.commit()
        
        end_time = time.time()
        bulk_time = (end_time - start_time) * 1000
        
        # Should handle 500 permissions efficiently
        self.assertEqual(len(permissions), 500)
        self.assertLess(bulk_time, 2000)  # Under 2 seconds
        
    def test_bulk_vendor_assignment(self):
        """Test bulk vendor assignment performance"""
        # Create vendors for multiple users
        start_time = time.time()
        
        vendor_assignments = []
        for i in range(50):
            user = self._create_test_user(
                nome=f'Vendor User {i}',
                email=f'vendor{i}@test.com'
            )
            
            # Assign 10 vendors to each user
            for j in range(10):
                vendor = UsuarioVendedor(
                    usuario_id=user.id,
                    vendedor=f'VENDOR_{i:03d}_{j:02d}',
                    adicionado_por=self.admin_user.id
                )
                vendor_assignments.append(vendor)
                
        db.session.bulk_save_objects(vendor_assignments)
        db.session.commit()
        
        end_time = time.time()
        bulk_time = (end_time - start_time) * 1000
        
        self.assertEqual(len(vendor_assignments), 500)
        self.assertLess(bulk_time, 2000)  # Under 2 seconds


class TestConcurrentAccessPerformance(BasePermissionTest):
    """Test performance under concurrent access"""
    
    def test_concurrent_permission_checks(self):
        """Test concurrent permission check performance"""
        # Create permissions
        for i in range(10):
            user = self._create_test_user(
                nome=f'Concurrent User {i}',
                email=f'concurrent{i}@test.com'
            )
            
            # Grant some permissions
            self._create_test_permission(user, 'faturamento', 'listar')
            self._create_test_permission(user, 'carteira', 'visualizar')
            
        db.session.commit()
        
        # Test concurrent access
        results = []
        errors = []
        
        def check_permissions(user_id, module, function):
            try:
                start = time.time()
                
                # Simulate permission check
                has_perm = PermissaoService.usuario_tem_permissao(
                    user_id, module, function
                )
                
                end = time.time()
                results.append({
                    'time': (end - start) * 1000,
                    'result': has_perm
                })
            except Exception as e:
                errors.append(str(e))
                
        # Create threads
        threads = []
        for i in range(20):
            user_id = (i % 10) + 1  # Cycle through users
            module = 'faturamento' if i % 2 == 0 else 'carteira'
            function = 'listar' if i % 2 == 0 else 'visualizar'
            
            t = threading.Thread(
                target=check_permissions,
                args=(user_id, module, function)
            )
            threads.append(t)
            
        # Run all threads
        start_time = time.time()
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        # All checks should complete
        self.assertEqual(len(results), 20)
        self.assertEqual(len(errors), 0)
        
        # Should handle concurrent access efficiently
        self.assertLess(total_time, 1000)  # Under 1 second for all
        
        # Average time per check
        avg_check_time = sum(r['time'] for r in results) / len(results)
        self.assertLess(avg_check_time, 50)  # Under 50ms average


class TestMemoryUsage(BasePermissionTest):
    """Test memory usage and efficiency"""
    
    def test_large_dataset_memory_usage(self):
        """Test memory usage with large datasets"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        categories = []
        for i in range(20):
            cat = self._create_test_category(f'mem_cat_{i}', f'Memory Category {i}')
            categories.append(cat)
            
            # Create modules
            for j in range(10):
                mod = self._create_test_module(cat, f'mem_mod_{i}_{j}', f'Module {j}')
                
                # Create submodules
                for k in range(5):
                    self._create_test_submodule(mod, f'mem_sub_{i}_{j}_{k}', f'Sub {k}')
                    
        db.session.commit()
        
        # Load all data
        all_categories = PermissionCategory.query.all()
        all_modules = PermissionModule.query.all()
        all_submodules = PermissionSubModule.query.all()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Check counts
        self.assertEqual(len(all_categories), 20)
        self.assertEqual(len(all_modules), 200)
        self.assertEqual(len(all_submodules), 1000)
        
        # Memory increase should be reasonable
        self.assertLess(memory_increase, 100)  # Less than 100MB increase
        
    def test_query_result_pagination_memory(self):
        """Test memory efficiency of paginated queries"""
        # Create many permissions
        for i in range(100):
            user = self._create_test_user(
                nome=f'Page User {i}',
                email=f'page{i}@test.com'
            )
            
            # Create 50 permissions per user
            for j in range(50):
                module = ModuloSistema.query.first()
                func = FuncaoModulo.query.filter_by(modulo_id=module.id).first()
                if func:
                    PermissaoUsuario(
                        usuario_id=user.id,
                        funcao_id=func.id,
                        pode_visualizar=True,
                        concedida_por=self.admin_user.id
                    )
                    
        db.session.commit()
        
        process = psutil.Process(os.getpid())
        
        # Test paginated query memory usage
        page_memories = []
        
        for page in range(1, 11):
            initial_mem = process.memory_info().rss / 1024 / 1024
            
            # Query one page
            paginated = PermissaoUsuario.query.paginate(
                page=page, per_page=100, error_out=False
            )
            
            # Process results
            for item in paginated.items:
                _ = item.nivel_acesso  # Access property
                
            final_mem = process.memory_info().rss / 1024 / 1024
            page_memories.append(final_mem - initial_mem)
            
        # Memory usage should be consistent across pages
        avg_memory = sum(page_memories) / len(page_memories)
        max_memory = max(page_memories)
        
        self.assertLess(max_memory, avg_memory * 2)  # No major spikes


class TestAuditLogPerformance(BasePermissionTest):
    """Test audit log performance"""
    
    def test_high_volume_logging(self):
        """Test performance with high volume of audit logs"""
        start_time = time.time()
        
        # Generate many log entries
        for i in range(1000):
            LogPermissao.registrar(
                usuario_id=self.regular_user.id,
                acao=f'TEST_ACTION_{i % 10}',
                funcao_id=None,
                detalhes=f'{{"iteration": {i}}}',
                resultado='SUCESSO' if i % 10 != 0 else 'NEGADO',
                ip_origem='127.0.0.1',
                user_agent='Performance Test'
            )
            
        end_time = time.time()
        insert_time = (end_time - start_time) * 1000
        
        # Should handle 1000 logs efficiently
        self.assertLess(insert_time, 5000)  # Under 5 seconds
        
        # Test query performance
        start_time = time.time()
        
        # Query recent logs
        recent_logs = LogPermissao.query.filter_by(
            usuario_id=self.regular_user.id
        ).order_by(LogPermissao.timestamp.desc()).limit(100).all()
        
        end_time = time.time()
        query_time = (end_time - start_time) * 1000
        
        self.assertEqual(len(recent_logs), 100)
        self.assertLess(query_time, 100)  # Under 100ms
        
    def test_log_search_performance(self):
        """Test audit log search performance"""
        # Create varied log entries
        actions = ['LOGIN', 'LOGOUT', 'PERMISSION_GRANTED', 'PERMISSION_DENIED', 'ERROR']
        
        for i in range(500):
            LogPermissao.registrar(
                usuario_id=self.regular_user.id if i % 2 == 0 else self.admin_user.id,
                acao=random.choice(actions),
                resultado='SUCESSO' if i % 3 != 0 else 'NEGADO',
                ip_origem=f'192.168.1.{i % 255}',
                detalhes=f'{{"search_test": {i}}}'
            )
            
        db.session.commit()
        
        # Test various search scenarios
        search_times = []
        
        # Search by action
        start = time.time()
        login_logs = LogPermissao.query.filter_by(acao='LOGIN').all()
        search_times.append((time.time() - start) * 1000)
        
        # Search by result
        start = time.time()
        denied_logs = LogPermissao.query.filter_by(resultado='NEGADO').all()
        search_times.append((time.time() - start) * 1000)
        
        # Search by date range
        start = time.time()
        recent = LogPermissao.query.filter(
            LogPermissao.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).all()
        search_times.append((time.time() - start) * 1000)
        
        # All searches should be fast
        for search_time in search_times:
            self.assertLess(search_time, 200)  # Under 200ms each


if __name__ == '__main__':
    unittest.main()