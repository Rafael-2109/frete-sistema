"""
UI Interaction Tests for Permission System
=========================================

Tests for UI components and user interactions including:
- Permission management interface
- User vendor/team assignment
- Batch operations UI
- Real-time updates
- Form validations
"""

import unittest
import json
from app.permissions.tests.base_test import BasePermissionTest
from app import db
from flask import url_for
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, UsuarioVendedor, UsuarioEquipeVendas
)


class TestPermissionManagementUI(BasePermissionTest):
    """Test permission management UI interactions"""
    
    def setUp(self):
        """Set up UI tests"""
        super().setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
    def test_permission_tree_view(self):
        """Test rendering permission tree view"""
        self._login_user(self.admin_user)
        
        # Create test hierarchy
        category = self._create_test_category('ui_cat', 'UI Category')
        module = self._create_test_module(category, 'ui_mod', 'UI Module')
        submodule = self._create_test_submodule(module, 'ui_sub', 'UI SubModule')
        db.session.commit()
        
        # Request permission tree
        response = self.client.get('/permissions/manage')
        
        self.assertEqual(response.status_code, 200)
        # Check that hierarchy is rendered
        self.assertIn(b'UI Category', response.data)
        self.assertIn(b'UI Module', response.data)
        self.assertIn(b'UI SubModule', response.data)
        
    def test_user_permission_edit_form(self):
        """Test user permission edit form"""
        self._login_user(self.admin_user)
        
        # Get edit form
        response = self.client.get(f'/permissions/users/{self.regular_user.id}/edit')
        
        self.assertEqual(response.status_code, 200)
        # Check form elements
        self.assertIn(b'can_view', response.data)
        self.assertIn(b'can_edit', response.data)
        self.assertIn(b'can_delete', response.data)
        self.assertIn(b'can_export', response.data)
        
    def test_permission_toggle_ajax(self):
        """Test AJAX permission toggle"""
        self._login_user(self.admin_user)
        
        # Create test permission
        category = self._create_test_category('toggle_cat', 'Toggle Category')
        db.session.commit()
        
        # Toggle permission via AJAX
        toggle_data = {
            'user_id': self.regular_user.id,
            'entity_type': 'CATEGORY',
            'entity_id': category.id,
            'permission': 'can_view',
            'value': True
        }
        
        response = self.client.post(
            '/permissions/toggle',
            data=json.dumps(toggle_data),
            content_type='application/json',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        
        # Verify permission was created
        perm = UserPermission.query.filter_by(
            user_id=self.regular_user.id,
            entity_type='CATEGORY',
            entity_id=category.id
        ).first()
        
        self.assertIsNotNone(perm)
        self.assertTrue(perm.can_view)
        
    def test_bulk_permission_form(self):
        """Test bulk permission assignment form"""
        self._login_user(self.admin_user)
        
        # Get bulk assignment form
        response = self.client.get('/permissions/bulk-assign')
        
        self.assertEqual(response.status_code, 200)
        # Check form elements
        self.assertIn(b'user_selection', response.data)
        self.assertIn(b'permission_template', response.data)
        self.assertIn(b'custom_permissions', response.data)
        
    def test_permission_template_builder(self):
        """Test permission template builder UI"""
        self._login_user(self.admin_user)
        
        # Get template builder
        response = self.client.get('/permissions/templates/new')
        
        self.assertEqual(response.status_code, 200)
        # Check builder components
        self.assertIn(b'template_name', response.data)
        self.assertIn(b'permission_selector', response.data)
        self.assertIn(b'save_template', response.data)


class TestVendorTeamAssignmentUI(BasePermissionTest):
    """Test vendor and team assignment UI"""
    
    def test_vendor_assignment_autocomplete(self):
        """Test vendor autocomplete search"""
        self._login_user(self.admin_user)
        
        # Search for vendors
        response = self.client.get(
            '/permissions/vendors/search?q=VEND',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('vendors', data)
        
    def test_add_vendor_form_submission(self):
        """Test adding vendor through form"""
        self._login_user(self.admin_user)
        
        # Submit vendor assignment form
        form_data = {
            'vendor': 'UI_TEST_VENDOR',
            'notes': 'Added through UI test'
        }
        
        response = self.client.post(
            f'/permissions/users/{self.regular_user.id}/vendors/add',
            data=form_data,
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify vendor was added
        vendor = UsuarioVendedor.query.filter_by(
            usuario_id=self.regular_user.id,
            vendedor='UI_TEST_VENDOR'
        ).first()
        
        self.assertIsNotNone(vendor)
        self.assertEqual(vendor.observacoes, 'Added through UI test')
        
    def test_remove_vendor_ajax(self):
        """Test removing vendor via AJAX"""
        self._login_user(self.admin_user)
        
        # Add vendor first
        vendor = self._add_vendor_to_user(self.regular_user, 'VENDOR_TO_REMOVE_UI')
        db.session.commit()
        
        # Remove via AJAX
        response = self.client.delete(
            f'/permissions/users/{self.regular_user.id}/vendors/{vendor.id}',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify soft delete
        db.session.refresh(vendor)
        self.assertFalse(vendor.ativo)
        
    def test_team_multiselect_widget(self):
        """Test team multiselect widget"""
        self._login_user(self.admin_user)
        
        # Get user edit page with team widget
        response = self.client.get(f'/permissions/users/{self.regular_user.id}/teams')
        
        self.assertEqual(response.status_code, 200)
        # Check multiselect elements
        self.assertIn(b'team_multiselect', response.data)
        self.assertIn(b'available_teams', response.data)
        self.assertIn(b'selected_teams', response.data)


class TestRealTimeUpdates(BasePermissionTest):
    """Test real-time UI updates"""
    
    def test_permission_change_notification(self):
        """Test real-time permission change notifications"""
        self._login_user(self.admin_user)
        
        # Simulate WebSocket connection (in real app)
        # For testing, we'll check notification endpoint
        response = self.client.get(
            f'/permissions/notifications/user/{self.regular_user.id}',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('notifications', data)
        
    def test_concurrent_edit_warning(self):
        """Test warning when multiple users edit same permissions"""
        self._login_user(self.admin_user)
        
        # Simulate checking for concurrent edits
        response = self.client.get(
            f'/permissions/users/{self.regular_user.id}/edit-lock',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('locked', data)
        
    def test_auto_save_draft(self):
        """Test auto-saving permission draft changes"""
        self._login_user(self.admin_user)
        
        # Save draft
        draft_data = {
            'user_id': self.regular_user.id,
            'permissions': {
                'MODULE_1': {'can_view': True, 'can_edit': False}
            }
        }
        
        response = self.client.post(
            '/permissions/drafts/save',
            data=json.dumps(draft_data),
            content_type='application/json',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('saved'))


class TestFormValidations(BasePermissionTest):
    """Test form validations and error handling"""
    
    def test_invalid_permission_submission(self):
        """Test handling of invalid permission data"""
        self._login_user(self.admin_user)
        
        # Submit invalid data
        invalid_data = {
            'permissions': [
                {
                    'type': 'INVALID_TYPE',  # Invalid entity type
                    'id': 999999,  # Non-existent ID
                    'can_view': 'not_boolean'  # Invalid boolean
                }
            ]
        }
        
        response = self.client.post(
            f'/permissions/users/{self.regular_user.id}/update',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        # Should return validation error
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)
        
    def test_duplicate_vendor_validation(self):
        """Test duplicate vendor validation"""
        self._login_user(self.admin_user)
        
        # Add vendor
        self._add_vendor_to_user(self.regular_user, 'DUPLICATE_VENDOR')
        db.session.commit()
        
        # Try to add same vendor again
        form_data = {
            'vendor': 'DUPLICATE_VENDOR',
            'notes': 'Duplicate attempt'
        }
        
        response = self.client.post(
            f'/permissions/users/{self.regular_user.id}/vendors/add',
            data=form_data
        )
        
        # Should show error
        self.assertIn(b'already assigned', response.data)
        
    def test_permission_conflict_resolution(self):
        """Test UI for resolving permission conflicts"""
        self._login_user(self.admin_user)
        
        # Create conflicting permissions
        category = self._create_test_category('conflict', 'Conflict Test')
        module = self._create_test_module(category, 'conflict_mod', 'Conflict Module')
        
        # Category says can't edit, module says can edit
        self._create_hierarchical_permission(
            self.regular_user, 'CATEGORY', category.id,
            can_view=True, can_edit=False
        )
        self._create_hierarchical_permission(
            self.regular_user, 'MODULE', module.id,
            can_view=True, can_edit=True
        )
        db.session.commit()
        
        # Get conflict resolution UI
        response = self.client.get(
            f'/permissions/users/{self.regular_user.id}/conflicts'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Permission Conflicts', response.data)
        self.assertIn(b'conflict_mod', response.data)


class TestAccessibilityAndUsability(BasePermissionTest):
    """Test UI accessibility and usability features"""
    
    def test_keyboard_navigation(self):
        """Test keyboard navigation support"""
        self._login_user(self.admin_user)
        
        response = self.client.get('/permissions/manage')
        
        # Check for keyboard navigation attributes
        self.assertIn(b'tabindex', response.data)
        self.assertIn(b'role="tree"', response.data)
        self.assertIn(b'aria-expanded', response.data)
        
    def test_screen_reader_support(self):
        """Test screen reader accessibility"""
        self._login_user(self.admin_user)
        
        response = self.client.get('/permissions/manage')
        
        # Check ARIA labels
        self.assertIn(b'aria-label', response.data)
        self.assertIn(b'aria-describedby', response.data)
        self.assertIn(b'role="button"', response.data)
        
    def test_responsive_design(self):
        """Test responsive design elements"""
        self._login_user(self.admin_user)
        
        # Test with mobile user agent
        response = self.client.get(
            '/permissions/manage',
            headers={'User-Agent': 'Mobile Safari'}
        )
        
        self.assertEqual(response.status_code, 200)
        # Check for responsive classes
        self.assertIn(b'table-responsive', response.data)
        self.assertIn(b'col-sm-', response.data)
        
    def test_loading_states(self):
        """Test loading state indicators"""
        self._login_user(self.admin_user)
        
        response = self.client.get('/permissions/manage')
        
        # Check for loading indicators
        self.assertIn(b'spinner', response.data)
        self.assertIn(b'loading-overlay', response.data)
        
    def test_error_recovery_ui(self):
        """Test error recovery UI elements"""
        self._login_user(self.admin_user)
        
        # Trigger an error condition
        response = self.client.get('/permissions/error-test')
        
        # Check for user-friendly error UI
        if response.status_code >= 400:
            self.assertIn(b'retry', response.data)
            self.assertIn(b'contact support', response.data)


class TestSearchAndFiltering(BasePermissionTest):
    """Test search and filtering UI"""
    
    def test_permission_search(self):
        """Test permission search functionality"""
        self._login_user(self.admin_user)
        
        # Create searchable permissions
        for i in range(5):
            cat = self._create_test_category(f'search_cat_{i}', f'Search Category {i}')
            self._create_test_module(cat, f'search_mod_{i}', f'Search Module {i}')
        db.session.commit()
        
        # Search for permissions
        response = self.client.get(
            '/permissions/search?q=search_mod_2',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(len(data.get('results', [])), 0)
        
    def test_filter_by_permission_level(self):
        """Test filtering by permission level"""
        self._login_user(self.admin_user)
        
        # Apply filters
        response = self.client.get(
            '/permissions/manage?filter=can_edit',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should only show users with edit permissions
        self.assertIn('filtered_users', data)
        
    def test_advanced_filters(self):
        """Test advanced filtering options"""
        self._login_user(self.admin_user)
        
        # Test combined filters
        filter_params = {
            'profile': 'vendedor',
            'has_vendors': 'true',
            'permission_level': 'view_only',
            'module': 'faturamento'
        }
        
        response = self.client.get(
            '/permissions/users',
            query_string=filter_params,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('users', data)
        self.assertIn('filter_summary', data)


if __name__ == '__main__':
    unittest.main()