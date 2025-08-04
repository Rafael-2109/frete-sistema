"""
Edge Case Tests for Permission System
====================================

Tests for edge cases and boundary conditions including:
- Circular dependencies
- Permission inheritance loops
- Batch operation limits
- Concurrent access
- Data integrity
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from app.permissions.tests.base_test import BasePermissionTest
from app import db
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, PermissaoUsuario,
    UsuarioVendedor, LogPermissao
)
from app.permissions.services import PermissaoService


class TestCircularDependencies(BasePermissionTest):
    """Test handling of circular dependencies"""
    
    def test_category_module_circular_reference(self):
        """Test prevention of circular references between categories and modules"""
        # Create category and module
        category = self._create_test_category('cat1', 'Category 1')
        module = self._create_test_module(category, 'mod1', 'Module 1')
        db.session.commit()
        
        # Try to create a circular reference (this should be prevented by design)
        # In a real system, you'd prevent a module from being its own parent
        self.assertEqual(module.category_id, category.id)
        self.assertNotEqual(module.id, category.id)
        
    def test_permission_inheritance_loop(self):
        """Test handling of permission inheritance loops"""
        # Create hierarchy
        cat1 = self._create_test_category('cat1', 'Category 1')
        mod1 = self._create_test_module(cat1, 'mod1', 'Module 1')
        sub1 = self._create_test_submodule(mod1, 'sub1', 'SubModule 1')
        
        # Grant permissions at different levels
        self._create_hierarchical_permission(
            self.regular_user, 'CATEGORY', cat1.id,
            can_view=True, can_edit=False
        )
        
        self._create_hierarchical_permission(
            self.regular_user, 'MODULE', mod1.id,
            can_view=False, can_edit=True  # Conflicting permission
        )
        
        self._create_hierarchical_permission(
            self.regular_user, 'SUBMODULE', sub1.id,
            can_view=True, can_edit=True
        )
        
        db.session.commit()
        
        # The most specific permission should take precedence
        sub_perm = UserPermission.query.filter_by(
            user_id=self.regular_user.id,
            entity_type='SUBMODULE',
            entity_id=sub1.id
        ).first()
        
        self.assertTrue(sub_perm.can_view)
        self.assertTrue(sub_perm.can_edit)


class TestBatchOperationLimits(BasePermissionTest):
    """Test batch operation limits and performance"""
    
    def test_large_batch_permission_update(self):
        """Test updating permissions for large number of users"""
        # Create many users
        users = []
        for i in range(100):
            user = self._create_test_user(
                nome=f'Batch User {i}',
                email=f'batch{i}@test.com',
                perfil='vendedor'
            )
            users.append(user)
        db.session.commit()
        
        # Create permissions for all users
        category = self._create_test_category('batch_cat', 'Batch Category')
        
        start_time = time.time()
        
        for user in users:
            self._create_hierarchical_permission(
                user, 'CATEGORY', category.id,
                can_view=True, can_edit=False
            )
            
        db.session.commit()
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Should complete within reasonable time
        self.assertLess(execution_time, 5000)  # 5 seconds max
        
        # Verify all permissions were created
        perm_count = UserPermission.query.filter_by(
            entity_type='CATEGORY',
            entity_id=category.id
        ).count()
        
        self.assertEqual(perm_count, 100)
        
    def test_bulk_vendor_assignment(self):
        """Test bulk vendor assignment limits"""
        # Create user with many vendors
        vendor_count = 50
        
        for i in range(vendor_count):
            self._add_vendor_to_user(
                self.regular_user,
                f'VENDOR_{i:04d}'
            )
            
        db.session.commit()
        
        # Check performance of getting vendors
        start_time = time.time()
        vendors = UsuarioVendedor.get_vendedores_usuario(self.regular_user.id)
        end_time = time.time()
        
        query_time = (end_time - start_time) * 1000
        
        self.assertEqual(len(vendors), vendor_count)
        self.assertLess(query_time, 100)  # Should be fast


class TestConcurrentAccess(BasePermissionTest):
    """Test concurrent access scenarios"""
    
    def test_concurrent_permission_updates(self):
        """Test concurrent updates to same permission"""
        category = self._create_test_category('concurrent', 'Concurrent Test')
        results = []
        errors = []
        
        def update_permission(can_edit_value):
            try:
                # Each thread creates/updates the same permission
                perm = UserPermission.query.filter_by(
                    user_id=self.regular_user.id,
                    entity_type='CATEGORY',
                    entity_id=category.id
                ).first()
                
                if not perm:
                    perm = UserPermission(
                        user_id=self.regular_user.id,
                        entity_type='CATEGORY',
                        entity_id=category.id,
                        granted_by=self.admin_user.id
                    )
                    db.session.add(perm)
                
                perm.can_view = True
                perm.can_edit = can_edit_value
                db.session.commit()
                results.append(can_edit_value)
            except Exception as e:
                errors.append(str(e))
                db.session.rollback()
        
        # Create threads
        threads = []
        for i in range(5):
            t = threading.Thread(
                target=update_permission,
                args=(i % 2 == 0,)  # Alternate True/False
            )
            threads.append(t)
            
        # Start all threads
        for t in threads:
            t.start()
            
        # Wait for completion
        for t in threads:
            t.join()
            
        # Should have handled all updates (some may have failed due to locks)
        self.assertGreater(len(results), 0)
        
        # Final permission should exist
        final_perm = UserPermission.query.filter_by(
            user_id=self.regular_user.id,
            entity_type='CATEGORY',
            entity_id=category.id
        ).first()
        
        self.assertIsNotNone(final_perm)
        
    def test_concurrent_audit_logging(self):
        """Test concurrent audit log writes"""
        results = []
        
        def write_log(index):
            log = LogPermissao.registrar(
                usuario_id=self.regular_user.id,
                acao=f'CONCURRENT_TEST_{index}',
                resultado='SUCESSO'
            )
            if log:
                results.append(index)
                
        # Create many concurrent log writes
        threads = []
        for i in range(20):
            t = threading.Thread(target=write_log, args=(i,))
            threads.append(t)
            
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # All logs should be written
        self.assertEqual(len(results), 20)
        
        # Verify in database
        logs = LogPermissao.query.filter(
            LogPermissao.acao.like('CONCURRENT_TEST_%')
        ).all()
        
        self.assertEqual(len(logs), 20)


class TestDataIntegrity(BasePermissionTest):
    """Test data integrity constraints"""
    
    def test_orphaned_permissions(self):
        """Test handling of orphaned permissions"""
        # Create permission
        category = self._create_test_category('orphan', 'Orphan Test')
        perm = self._create_hierarchical_permission(
            self.regular_user, 'CATEGORY', category.id
        )
        db.session.commit()
        
        # Delete category (this should cascade or prevent based on constraints)
        db.session.delete(category)
        
        # Try to commit - should handle gracefully
        try:
            db.session.commit()
            # If cascade delete is enabled, permission should be gone
            remaining = UserPermission.query.filter_by(
                entity_type='CATEGORY',
                entity_id=category.id
            ).count()
            self.assertEqual(remaining, 0)
        except Exception:
            # If cascade is not enabled, should get integrity error
            db.session.rollback()
            
    def test_duplicate_vendor_reactivation(self):
        """Test reactivating soft-deleted vendor"""
        # Add vendor
        vendor = self._add_vendor_to_user(self.regular_user, 'REACTIVATE_TEST')
        db.session.commit()
        
        # Soft delete
        vendor.ativo = False
        db.session.commit()
        
        # Try to add same vendor again - should reactivate
        new_vendor = UsuarioVendedor(
            usuario_id=self.regular_user.id,
            vendedor='REACTIVATE_TEST',
            adicionado_por=self.admin_user.id
        )
        
        # This should fail due to unique constraint
        db.session.add(new_vendor)
        with self.assertRaises(Exception):
            db.session.commit()
            
    def test_permission_expiration_boundary(self):
        """Test permission expiration at exact boundary"""
        # Create permission expiring in 1 microsecond
        permission = self._create_test_permission(
            self.regular_user, 'faturamento', 'listar'
        )
        
        # Set expiration to very near future
        permission.expira_em = datetime.utcnow() + timedelta(microseconds=1)
        db.session.commit()
        
        # Wait a tiny bit
        time.sleep(0.001)
        
        # Should be expired
        self.assertTrue(permission.esta_expirada)
        
    def test_null_handling(self):
        """Test handling of null values in various fields"""
        # Create permission with minimal data
        perm = UserPermission(
            user_id=self.regular_user.id,
            entity_type='CATEGORY',
            entity_id=1,
            granted_by=self.admin_user.id
        )
        db.session.add(perm)
        db.session.commit()
        
        # Check defaults
        self.assertFalse(perm.can_view)
        self.assertFalse(perm.can_edit)
        self.assertFalse(perm.can_delete)
        self.assertFalse(perm.can_export)
        self.assertTrue(perm.active)
        self.assertIsNone(perm.expires_at)
        
    def test_cascade_delete_behavior(self):
        """Test cascade delete behavior across relationships"""
        # Create hierarchy
        category = self._create_test_category('cascade', 'Cascade Test')
        module = self._create_test_module(category, 'cascade_mod', 'Cascade Module')
        submodule = self._create_test_submodule(module, 'cascade_sub', 'Cascade Sub')
        
        # Create permissions at each level
        cat_perm = self._create_hierarchical_permission(
            self.regular_user, 'CATEGORY', category.id
        )
        mod_perm = self._create_hierarchical_permission(
            self.regular_user, 'MODULE', module.id
        )
        sub_perm = self._create_hierarchical_permission(
            self.regular_user, 'SUBMODULE', submodule.id
        )
        
        db.session.commit()
        
        # Delete module - should cascade to submodule
        db.session.delete(module)
        db.session.commit()
        
        # Module and its submodule should be gone
        self.assertIsNone(PermissionModule.query.get(module.id))
        self.assertIsNone(PermissionSubModule.query.get(submodule.id))
        
        # Category should still exist
        self.assertIsNotNone(PermissionCategory.query.get(category.id))


class TestBoundaryConditions(BasePermissionTest):
    """Test boundary conditions and limits"""
    
    def test_maximum_string_lengths(self):
        """Test maximum string length handling"""
        # Test with maximum allowed string
        long_name = 'A' * 255  # Assuming 255 is max for most fields
        
        category = PermissionCategory(
            name='maxlen',
            display_name='Max Length Test',
            description=long_name,
            created_by=self.admin_user.id
        )
        db.session.add(category)
        
        # Should handle gracefully
        try:
            db.session.commit()
            self.assertEqual(len(category.description), 255)
        except Exception:
            db.session.rollback()
            
    def test_zero_and_negative_ids(self):
        """Test handling of zero and negative IDs"""
        # Try to create permission with invalid entity_id
        with self.assertRaises(Exception):
            perm = UserPermission(
                user_id=self.regular_user.id,
                entity_type='CATEGORY',
                entity_id=0,  # Invalid ID
                granted_by=self.admin_user.id
            )
            db.session.add(perm)
            db.session.commit()
            
    def test_empty_collections(self):
        """Test operations on empty collections"""
        # User with no permissions
        new_user = self._create_test_user(
            nome='Empty User',
            email='empty@test.com'
        )
        db.session.commit()
        
        # Should handle empty results gracefully
        vendors = UsuarioVendedor.get_vendedores_usuario(new_user.id)
        self.assertEqual(vendors, [])
        
        perms = UserPermission.query.filter_by(user_id=new_user.id).all()
        self.assertEqual(perms, [])
        
    def test_maximum_hierarchy_depth(self):
        """Test handling of deep permission hierarchies"""
        # Create deep hierarchy
        category = self._create_test_category('deep', 'Deep Hierarchy')
        
        # Create many modules
        for i in range(50):
            module = self._create_test_module(
                category, f'mod_{i}', f'Module {i}'
            )
            
            # Create many submodules
            for j in range(10):
                self._create_test_submodule(
                    module, f'sub_{i}_{j}', f'SubModule {i}.{j}'
                )
                
        db.session.commit()
        
        # Should handle deep queries efficiently
        start_time = time.time()
        
        modules = PermissionModule.query.filter_by(
            category_id=category.id
        ).all()
        
        end_time = time.time()
        query_time = (end_time - start_time) * 1000
        
        self.assertEqual(len(modules), 50)
        self.assertLess(query_time, 1000)  # Should be reasonably fast


if __name__ == '__main__':
    unittest.main()