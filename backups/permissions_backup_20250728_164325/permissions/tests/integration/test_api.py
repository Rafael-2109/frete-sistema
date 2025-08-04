"""
Integration Tests for Permission API
===================================

Tests all API endpoints with various scenarios including:
- Authentication and authorization
- CRUD operations
- Batch operations
- Error handling
- Edge cases
"""

import json
import unittest
from datetime import datetime, timedelta
from app.permissions.tests.base_test import BasePermissionTest
from app import db
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate
)


class TestPermissionAPI(BasePermissionTest):
    """Test Permission API endpoints"""
    
    def setUp(self):
        """Set up for API tests"""
        super().setUp()
        self.api_base = '/api/v1/permissions'
        
    def _get_auth_headers(self, user):
        """Get authentication headers for user"""
        # In real app, this would generate JWT token
        return {
            'Authorization': f'Bearer test_token_{user.id}',
            'Content-Type': 'application/json'
        }
        
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get(f'{self.api_base}/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['status'], 'healthy')
        
    def test_list_categories_unauthorized(self):
        """Test listing categories without authentication"""
        response = self.client.get(f'{self.api_base}/categories')
        
        # Should require authentication
        self.assertEqual(response.status_code, 401)
        
    def test_list_categories_authorized(self):
        """Test listing categories with authentication"""
        self._login_user(self.admin_user)
        
        response = self.client.get(
            f'{self.api_base}/categories',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('categories', data['data'])
        
    def test_create_category(self):
        """Test creating a new category"""
        self._login_user(self.admin_user)
        
        category_data = {
            'name': 'test_category',
            'display_name': 'Test Category',
            'description': 'Test category for integration tests',
            'icon': 'test',
            'color': '#FF0000',
            'order_index': 99
        }
        
        response = self.client.post(
            f'{self.api_base}/categories',
            data=json.dumps(category_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['category']['name'], 'test_category')
        
    def test_create_duplicate_category(self):
        """Test creating duplicate category"""
        self._login_user(self.admin_user)
        
        # Create first category
        category = self._create_test_category('duplicate', 'Duplicate')
        db.session.commit()
        
        # Try to create duplicate
        category_data = {
            'name': 'duplicate',
            'display_name': 'Duplicate 2'
        }
        
        response = self.client.post(
            f'{self.api_base}/categories',
            data=json.dumps(category_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'CONFLICT')
        
    def test_list_modules_with_filters(self):
        """Test listing modules with filters"""
        self._login_user(self.admin_user)
        
        # Create test data
        category = self._create_test_category('test_cat', 'Test Category')
        module1 = self._create_test_module(category, 'active_mod', 'Active Module')
        module2 = self._create_test_module(category, 'inactive_mod', 'Inactive Module')
        module2.active = False
        db.session.commit()
        
        # Test with active filter
        response = self.client.get(
            f'{self.api_base}/modules?category_id={category.id}&active=true',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        modules = data['data']['modules']
        
        # Should only return active module
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]['name'], 'active_mod')
        
    def test_get_user_permissions(self):
        """Test getting user permissions"""
        self._login_user(self.admin_user)
        
        # Create test permissions
        category = self._create_test_category('test_cat', 'Test Category')
        module = self._create_test_module(category, 'test_mod', 'Test Module')
        
        perm = self._create_hierarchical_permission(
            self.regular_user, 'MODULE', module.id,
            can_view=True, can_edit=False
        )
        db.session.commit()
        
        response = self.client.get(
            f'{self.api_base}/users/{self.regular_user.id}/permissions?effective=true',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('permissions', data['data'])
        
    def test_update_user_permissions(self):
        """Test updating user permissions"""
        self._login_user(self.admin_user)
        
        # Create test entities
        category = self._create_test_category('test_cat', 'Test Category')
        module = self._create_test_module(category, 'test_mod', 'Test Module')
        db.session.commit()
        
        # Update permissions
        update_data = {
            'permissions': [
                {
                    'type': 'module',
                    'id': module.id,
                    'can_view': True,
                    'can_edit': True,
                    'can_delete': False,
                    'can_export': True,
                    'reason': 'Test permission update'
                }
            ],
            'notify_user': False
        }
        
        response = self.client.post(
            f'{self.api_base}/users/{self.regular_user.id}/permissions',
            data=json.dumps(update_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['count'], 1)
        
        # Verify permission was created
        perm = UserPermission.query.filter_by(
            user_id=self.regular_user.id,
            entity_type='MODULE',
            entity_id=module.id
        ).first()
        
        self.assertIsNotNone(perm)
        self.assertTrue(perm.can_view)
        self.assertTrue(perm.can_edit)
        
    def test_add_vendor_to_user(self):
        """Test adding vendor to user"""
        self._login_user(self.admin_user)
        
        vendor_data = {
            'vendor': 'VENDOR_TEST_001',
            'notes': 'Test vendor assignment'
        }
        
        response = self.client.post(
            f'{self.api_base}/users/{self.regular_user.id}/vendors',
            data=json.dumps(vendor_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['vendor']['vendor'], 'VENDOR_TEST_001')
        
    def test_remove_vendor_from_user(self):
        """Test removing vendor from user"""
        self._login_user(self.admin_user)
        
        # Add vendor first
        vendor = self._add_vendor_to_user(self.regular_user, 'VENDOR_TO_REMOVE')
        db.session.commit()
        
        response = self.client.delete(
            f'{self.api_base}/users/{self.regular_user.id}/vendors/{vendor.id}',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify vendor is soft deleted
        db.session.refresh(vendor)
        self.assertFalse(vendor.ativo)
        
    def test_batch_apply_template(self):
        """Test batch applying permission template"""
        self._login_user(self.admin_user)
        
        # Create template
        template = PermissionTemplate(
            name='Test Batch Template',
            code='test_batch',
            template_data=json.dumps({
                'permissions': {
                    'faturamento': {'listar': 'view'}
                }
            }),
            created_by=self.admin_user.id
        )
        db.session.add(template)
        db.session.commit()
        
        # Apply to multiple users
        batch_data = {
            'template_id': template.id,
            'user_ids': [self.regular_user.id, self.manager_user.id],
            'options': {
                'override_existing': False,
                'apply_vendors': True,
                'apply_teams': True
            },
            'reason': 'Batch template test'
        }
        
        response = self.client.post(
            f'{self.api_base}/batch/apply-template',
            data=json.dumps(batch_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
    def test_audit_logs(self):
        """Test retrieving audit logs"""
        self._login_user(self.admin_user)
        
        # Create some actions to generate logs
        self._create_test_permission(
            self.regular_user, 'faturamento', 'listar'
        )
        db.session.commit()
        
        response = self.client.get(
            f'{self.api_base}/audit?page=1&limit=10',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('logs', data['data'])
        
    def test_permission_templates_list(self):
        """Test listing permission templates"""
        self._login_user(self.admin_user)
        
        # Create test template
        template = PermissionTemplate(
            name='Test Template',
            code='test_list',
            category='custom',
            template_data='{}',
            created_by=self.admin_user.id
        )
        db.session.add(template)
        db.session.commit()
        
        response = self.client.get(
            f'{self.api_base}/templates?active=true',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertGreater(len(data['data']['templates']), 0)
        
    def test_pagination(self):
        """Test API pagination"""
        self._login_user(self.admin_user)
        
        # Create many modules
        category = self._create_test_category('pagination', 'Pagination Test')
        for i in range(15):
            self._create_test_module(category, f'mod_{i}', f'Module {i}')
        db.session.commit()
        
        # Request first page
        response = self.client.get(
            f'{self.api_base}/modules?category_id={category.id}&page=1&per_page=10',
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        pagination = data['data']['pagination']
        
        self.assertEqual(pagination['page'], 1)
        self.assertEqual(pagination['per_page'], 10)
        self.assertEqual(pagination['total'], 15)
        self.assertTrue(pagination['has_next'])
        self.assertFalse(pagination['has_prev'])
        
    def test_error_handling_invalid_json(self):
        """Test error handling for invalid JSON"""
        self._login_user(self.admin_user)
        
        response = self.client.post(
            f'{self.api_base}/categories',
            data='{"invalid json',
            headers=self._get_auth_headers(self.admin_user),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
    def test_concurrent_permission_updates(self):
        """Test handling concurrent permission updates"""
        self._login_user(self.admin_user)
        
        # Create initial permission
        category = self._create_test_category('concurrent', 'Concurrent Test')
        module = self._create_test_module(category, 'concurrent_mod', 'Concurrent Module')
        
        perm = self._create_hierarchical_permission(
            self.regular_user, 'MODULE', module.id,
            can_view=True, can_edit=False
        )
        db.session.commit()
        
        # Simulate concurrent updates
        update_data = {
            'permissions': [{
                'type': 'module',
                'id': module.id,
                'can_view': True,
                'can_edit': True
            }]
        }
        
        # Both updates should succeed (last write wins)
        response1 = self.client.post(
            f'{self.api_base}/users/{self.regular_user.id}/permissions',
            data=json.dumps(update_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        response2 = self.client.post(
            f'{self.api_base}/users/{self.regular_user.id}/permissions',
            data=json.dumps(update_data),
            headers=self._get_auth_headers(self.admin_user)
        )
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)


if __name__ == '__main__':
    unittest.main()