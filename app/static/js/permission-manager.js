/**
 * Permission Manager - Hierarchical Permission Management System
 * Handles all UI interactions for the permission management interface
 */

const PermissionManager = (function() {
    'use strict';

    // State management
    let state = {
        selectedUser: null,
        users: [],
        categories: [],
        permissions: {},
        pendingChanges: new Map(),
        vendors: [],
        teams: [],
        templates: [],
        searchTerm: '',
        expandedNodes: new Set(),
        loading: false
    };

    // API endpoints
    const API = {
        base: '/api/v1/permissions',
        categories: () => `${API.base}/categories`,
        modules: () => `${API.base}/modules`,
        submodules: () => `${API.base}/submodules`,
        userPermissions: (userId) => `${API.base}/users/${userId}/permissions`,
        userVendors: (userId) => `${API.base}/users/${userId}/vendors`,
        userTeams: (userId) => `${API.base}/users/${userId}/teams`,
        templates: () => `${API.base}/templates`,
        batchApplyTemplate: () => `${API.base}/batch/apply-template`,
        batchUpdate: () => `${API.base}/batch/bulk-update`,
        audit: () => `${API.base}/audit`,
        users: () => '/api/users' // Assuming this exists
    };

    // Initialize the permission manager
    function init() {
        loadUsers();
        loadCategories();
        loadStatistics();
        setupEventListeners();
        
        // Set up auto-save
        setInterval(checkPendingChanges, 30000); // Auto-save every 30 seconds
    }

    // Setup event listeners
    function setupEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                savePermissions();
            }
        });

        // Window unload warning
        window.addEventListener('beforeunload', (e) => {
            if (state.pendingChanges.size > 0) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }

    // Load users
    async function loadUsers() {
        try {
            const response = await fetch(API.users());
            const data = await response.json();
            
            if (data.success) {
                state.users = data.users;
                renderUserList();
            }
        } catch (error) {
            console.error('Error loading users:', error);
            showToast('Erro ao carregar usuários', 'error');
        }
    }

    // Load categories and build hierarchy
    async function loadCategories() {
        try {
            const response = await fetch(`${API.categories()}?include_modules=true&include_counts=true`);
            const data = await response.json();
            
            if (data.success) {
                state.categories = data.data.categories;
                updateStatistics();
            }
        } catch (error) {
            console.error('Error loading categories:', error);
            showToast('Erro ao carregar categorias', 'error');
        }
    }

    // Load statistics
    async function loadStatistics() {
        // This would typically come from a dedicated endpoint
        const stats = {
            users: state.users.length,
            permissions: 0,
            categories: state.categories.length,
            modules: state.categories.reduce((sum, cat) => sum + (cat.modules?.length || 0), 0)
        };
        
        document.getElementById('stat-users').textContent = stats.users;
        document.getElementById('stat-permissions').textContent = stats.permissions;
        document.getElementById('stat-categories').textContent = stats.categories;
        document.getElementById('stat-modules').textContent = stats.modules;
    }

    // Render user list
    function renderUserList() {
        const container = document.getElementById('user-list');
        const searchTerm = document.getElementById('user-search').value.toLowerCase();
        const profileFilter = document.getElementById('profile-filter').value;
        
        const filteredUsers = state.users.filter(user => {
            const matchesSearch = user.nome.toLowerCase().includes(searchTerm) || 
                                  user.email.toLowerCase().includes(searchTerm);
            const matchesProfile = !profileFilter || user.perfil === profileFilter;
            return matchesSearch && matchesProfile;
        });

        container.innerHTML = filteredUsers.map(user => `
            <div class="user-card ${state.selectedUser?.id === user.id ? 'selected' : ''}" 
                 onclick="PermissionManager.selectUser(${user.id})">
                <div class="d-flex align-items-center">
                    <div class="flex-grow-1">
                        <div class="fw-bold">${highlightText(user.nome, searchTerm)}</div>
                        <small class="text-muted">${highlightText(user.email, searchTerm)}</small>
                    </div>
                    <span class="badge bg-secondary">${user.perfil}</span>
                </div>
            </div>
        `).join('');
    }

    // Select a user
    async function selectUser(userId) {
        if (state.pendingChanges.size > 0) {
            if (!confirm('Você tem alterações não salvas. Deseja continuar?')) {
                return;
            }
            state.pendingChanges.clear();
        }

        const user = state.users.find(u => u.id === userId);
        if (!user) return;

        state.selectedUser = user;
        showLoading(true);

        try {
            // Load user permissions
            const permResponse = await fetch(`${API.userPermissions(userId)}?effective=true&include_inherited=true`);
            const permData = await permResponse.json();
            
            if (permData.success) {
                state.permissions = permData.data;
                renderPermissionTree();
                
                // Show additional UI elements
                document.getElementById('permission-tree-title').textContent = 
                    `Permissões de ${user.nome}`;
                document.getElementById('permission-actions').style.display = 'block';
                document.getElementById('permission-search-box').style.display = 'block';
                document.getElementById('vendor-team-card').style.display = 'block';
                document.getElementById('audit-card').style.display = 'block';
                
                // Load vendors and teams
                loadUserVendors(userId);
                loadUserTeams(userId);
                loadAuditLog(userId);
            }
        } catch (error) {
            console.error('Error loading user permissions:', error);
            showToast('Erro ao carregar permissões', 'error');
        } finally {
            showLoading(false);
            renderUserList(); // Update selection
        }
    }

    // Render permission tree
    function renderPermissionTree() {
        const container = document.getElementById('permission-tree');
        const categories = state.permissions.permissions.categories;
        
        container.innerHTML = categories.map(category => 
            renderCategory(category)
        ).join('');
        
        // Restore expanded state
        state.expandedNodes.forEach(nodeId => {
            const element = document.getElementById(nodeId);
            if (element) {
                element.style.display = 'block';
            }
        });
    }

    // Render category
    function renderCategory(category) {
        const isExpanded = state.expandedNodes.has(`cat-${category.id}`);
        const hasCustomPermissions = category.permissions.granted_at !== null;
        
        return `
            <div class="permission-category" data-category-id="${category.id}">
                <div class="permission-header ${hasCustomPermissions ? 'custom-override' : ''}">
                    <span class="permission-toggle" onclick="PermissionManager.toggleNode('cat-${category.id}')">
                        <i class="fas fa-chevron-${isExpanded ? 'down' : 'right'}"></i>
                    </span>
                    <span class="permission-icon" style="color: ${category.color || '#007bff'}">
                        <i class="fas fa-folder"></i>
                    </span>
                    <span class="flex-grow-1">${category.display_name}</span>
                    <div class="permission-actions">
                        ${renderPermissionCheckboxes(category, 'CATEGORY', category.id)}
                    </div>
                </div>
                <div id="cat-${category.id}" style="display: ${isExpanded ? 'block' : 'none'}">
                    ${category.modules.map(module => renderModule(module, category)).join('')}
                </div>
            </div>
        `;
    }

    // Render module
    function renderModule(module, category) {
        const isExpanded = state.expandedNodes.has(`mod-${module.id}`);
        const hasCustomPermissions = module.permissions.custom_override;
        const isInherited = module.permissions.inherited && !hasCustomPermissions;
        
        return `
            <div class="permission-module" data-module-id="${module.id}">
                <div class="permission-header ${hasCustomPermissions ? 'custom-override' : ''} ${isInherited ? 'inherited-permission' : ''}">
                    <span class="permission-toggle" onclick="PermissionManager.toggleNode('mod-${module.id}')">
                        <i class="fas fa-chevron-${isExpanded ? 'down' : 'right'}"></i>
                    </span>
                    <span class="permission-icon" style="color: ${module.color || '#6c757d'}">
                        <i class="fas fa-cube"></i>
                    </span>
                    <span class="flex-grow-1">
                        ${module.display_name}
                        ${isInherited ? '<small class="text-muted">(herdado)</small>' : ''}
                    </span>
                    <div class="permission-actions">
                        ${renderPermissionCheckboxes(module, 'MODULE', module.id)}
                    </div>
                </div>
                <div id="mod-${module.id}" style="display: ${isExpanded ? 'block' : 'none'}">
                    ${module.submodules.map(submodule => renderSubModule(submodule, module)).join('')}
                </div>
            </div>
        `;
    }

    // Render submodule
    function renderSubModule(submodule, module) {
        const hasCustomPermissions = !submodule.permissions.inherited;
        const criticalClass = submodule.critical_level === 'CRITICAL' ? 'text-danger' :
                            submodule.critical_level === 'HIGH' ? 'text-warning' : '';
        
        return `
            <div class="permission-submodule ${hasCustomPermissions ? 'custom-override' : ''}" 
                 data-submodule-id="${submodule.id}">
                <div class="permission-header">
                    <span class="permission-icon ${criticalClass}">
                        <i class="fas fa-file"></i>
                    </span>
                    <span class="flex-grow-1">
                        ${submodule.display_name}
                        ${submodule.permissions.inherited ? 
                            `<small class="text-muted">(herdado de ${submodule.permissions.inherited_from})</small>` : ''}
                    </span>
                    <div class="permission-actions">
                        ${renderPermissionCheckboxes(submodule, 'SUBMODULE', submodule.id)}
                    </div>
                </div>
            </div>
        `;
    }

    // Render permission checkboxes
    function renderPermissionCheckboxes(entity, type, id) {
        const permissions = entity.permissions;
        const key = `${type}-${id}`;
        
        return `
            <div class="form-check form-check-inline">
                <input class="form-check-input permission-checkbox" type="checkbox" 
                       id="view-${key}" ${permissions.can_view ? 'checked' : ''}
                       onchange="PermissionManager.updatePermission('${type}', ${id}, 'can_view', this.checked)">
                <label class="form-check-label" for="view-${key}">
                    <i class="fas fa-eye"></i> Ver
                </label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input permission-checkbox" type="checkbox" 
                       id="edit-${key}" ${permissions.can_edit ? 'checked' : ''}
                       ${!permissions.can_view ? 'disabled' : ''}
                       onchange="PermissionManager.updatePermission('${type}', ${id}, 'can_edit', this.checked)">
                <label class="form-check-label" for="edit-${key}">
                    <i class="fas fa-edit"></i> Editar
                </label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input permission-checkbox" type="checkbox" 
                       id="delete-${key}" ${permissions.can_delete ? 'checked' : ''}
                       ${!permissions.can_edit ? 'disabled' : ''}
                       onchange="PermissionManager.updatePermission('${type}', ${id}, 'can_delete', this.checked)">
                <label class="form-check-label" for="delete-${key}">
                    <i class="fas fa-trash"></i> Deletar
                </label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input permission-checkbox" type="checkbox" 
                       id="export-${key}" ${permissions.can_export ? 'checked' : ''}
                       ${!permissions.can_view ? 'disabled' : ''}
                       onchange="PermissionManager.updatePermission('${type}', ${id}, 'can_export', this.checked)">
                <label class="form-check-label" for="export-${key}">
                    <i class="fas fa-download"></i> Exportar
                </label>
            </div>
        `;
    }

    // Update permission
    function updatePermission(type, id, permission, value) {
        const key = `${type}-${id}`;
        
        // Get current state
        if (!state.pendingChanges.has(key)) {
            state.pendingChanges.set(key, {
                type: type,
                id: id,
                permissions: {}
            });
        }
        
        const change = state.pendingChanges.get(key);
        change.permissions[permission] = value;
        
        // Handle cascading logic
        if (permission === 'can_view' && !value) {
            // If removing view, remove all other permissions
            ['can_edit', 'can_delete', 'can_export'].forEach(perm => {
                change.permissions[perm] = false;
                const checkbox = document.getElementById(`${perm.replace('can_', '')}-${key}`);
                if (checkbox) {
                    checkbox.checked = false;
                    checkbox.disabled = true;
                }
            });
        } else if (permission === 'can_view' && value) {
            // Enable other checkboxes
            ['can_edit', 'can_export'].forEach(perm => {
                const checkbox = document.getElementById(`${perm.replace('can_', '')}-${key}`);
                if (checkbox) checkbox.disabled = false;
            });
        } else if (permission === 'can_edit' && value) {
            // Enable delete
            const deleteCheckbox = document.getElementById(`delete-${key}`);
            if (deleteCheckbox) deleteCheckbox.disabled = false;
        } else if (permission === 'can_edit' && !value) {
            // Disable and uncheck delete
            change.permissions.can_delete = false;
            const deleteCheckbox = document.getElementById(`delete-${key}`);
            if (deleteCheckbox) {
                deleteCheckbox.checked = false;
                deleteCheckbox.disabled = true;
            }
        }
        
        // Show unsaved indicator
        updateUnsavedIndicator();
        
        // Handle inheritance cascade if needed
        if (document.getElementById('cascade-permissions')?.checked) {
            cascadePermissions(type, id, change.permissions);
        }
    }

    // Cascade permissions to children
    function cascadePermissions(parentType, parentId, permissions) {
        if (parentType === 'CATEGORY') {
            // Apply to all modules in category
            const category = state.permissions.permissions.categories.find(c => c.id === parentId);
            if (category) {
                category.modules.forEach(module => {
                    updatePermission('MODULE', module.id, 'can_view', permissions.can_view);
                    updatePermission('MODULE', module.id, 'can_edit', permissions.can_edit);
                    updatePermission('MODULE', module.id, 'can_delete', permissions.can_delete);
                    updatePermission('MODULE', module.id, 'can_export', permissions.can_export);
                });
            }
        } else if (parentType === 'MODULE') {
            // Apply to all submodules in module
            state.permissions.permissions.categories.forEach(category => {
                const module = category.modules.find(m => m.id === parentId);
                if (module) {
                    module.submodules.forEach(submodule => {
                        updatePermission('SUBMODULE', submodule.id, 'can_view', permissions.can_view);
                        updatePermission('SUBMODULE', submodule.id, 'can_edit', permissions.can_edit);
                        updatePermission('SUBMODULE', submodule.id, 'can_delete', permissions.can_delete);
                        updatePermission('SUBMODULE', submodule.id, 'can_export', permissions.can_export);
                    });
                }
            });
        }
    }

    // Save permissions
    async function savePermissions() {
        if (state.pendingChanges.size === 0) {
            showToast('Nenhuma alteração para salvar', 'info');
            return;
        }
        
        if (!state.selectedUser) {
            showToast('Nenhum usuário selecionado', 'warning');
            return;
        }
        
        showLoading(true);
        
        try {
            const permissions = Array.from(state.pendingChanges.values()).map(change => ({
                type: change.type,
                id: change.id,
                ...change.permissions,
                custom_override: true,
                reason: 'Atualização manual via interface'
            }));
            
            const response = await fetch(API.userPermissions(state.selectedUser.id), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    permissions: permissions,
                    notify_user: false
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Permissões salvas com sucesso', 'success');
                state.pendingChanges.clear();
                updateUnsavedIndicator();
                
                // Reload permissions to get updated state
                selectUser(state.selectedUser.id);
            } else {
                showToast(data.error.message || 'Erro ao salvar permissões', 'error');
            }
        } catch (error) {
            console.error('Error saving permissions:', error);
            showToast('Erro ao salvar permissões', 'error');
        } finally {
            showLoading(false);
        }
    }

    // Load user vendors
    async function loadUserVendors(userId) {
        try {
            const response = await fetch(API.userVendors(userId));
            const data = await response.json();
            
            if (data.success) {
                state.vendors = data.data.vendors;
                renderVendors();
            }
        } catch (error) {
            console.error('Error loading vendors:', error);
        }
    }

    // Load user teams
    async function loadUserTeams(userId) {
        try {
            const response = await fetch(API.userTeams(userId));
            const data = await response.json();
            
            if (data.success) {
                state.teams = data.data.teams;
                renderTeams();
            }
        } catch (error) {
            console.error('Error loading teams:', error);
        }
    }

    // Render vendors
    function renderVendors() {
        const container = document.getElementById('vendor-list');
        
        if (state.vendors.length === 0) {
            container.innerHTML = '<p class="text-muted mb-2">Nenhum vendedor associado</p>';
            return;
        }
        
        container.innerHTML = state.vendors.map(vendor => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>${vendor.vendor}</span>
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="PermissionManager.removeVendor(${vendor.id})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }

    // Render teams
    function renderTeams() {
        const container = document.getElementById('team-list');
        
        if (state.teams.length === 0) {
            container.innerHTML = '<p class="text-muted mb-2">Nenhuma equipe associada</p>';
            return;
        }
        
        container.innerHTML = state.teams.map(team => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>${team.team}</span>
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="PermissionManager.removeTeam(${team.id})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }

    // Add vendor
    async function addVendor() {
        // Load available vendors
        try {
            const response = await fetch(API.userVendors(state.selectedUser.id));
            const data = await response.json();
            
            if (data.success) {
                const availableVendors = data.data.available_vendors;
                const select = document.getElementById('vendor-select');
                
                select.innerHTML = '<option value="">Selecione...</option>' +
                    availableVendors.map(v => `<option value="${v}">${v}</option>`).join('');
                
                const modal = new bootstrap.Modal(document.getElementById('addVendorModal'));
                modal.show();
            }
        } catch (error) {
            console.error('Error loading available vendors:', error);
            showToast('Erro ao carregar vendedores disponíveis', 'error');
        }
    }

    // Save vendor
    async function saveVendor() {
        const vendor = document.getElementById('vendor-select').value;
        const notes = document.getElementById('vendor-notes').value;
        
        if (!vendor) {
            showToast('Selecione um vendedor', 'warning');
            return;
        }
        
        try {
            const response = await fetch(API.userVendors(state.selectedUser.id), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    vendor: vendor,
                    notes: notes
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Vendedor adicionado com sucesso', 'success');
                bootstrap.Modal.getInstance(document.getElementById('addVendorModal')).hide();
                loadUserVendors(state.selectedUser.id);
            } else {
                showToast(data.error.message || 'Erro ao adicionar vendedor', 'error');
            }
        } catch (error) {
            console.error('Error adding vendor:', error);
            showToast('Erro ao adicionar vendedor', 'error');
        }
    }

    // Remove vendor
    async function removeVendor(vendorId) {
        if (!confirm('Remover este vendedor?')) return;
        
        try {
            const response = await fetch(`${API.userVendors(state.selectedUser.id)}/${vendorId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Vendedor removido', 'success');
                loadUserVendors(state.selectedUser.id);
            }
        } catch (error) {
            console.error('Error removing vendor:', error);
            showToast('Erro ao remover vendedor', 'error');
        }
    }

    // Load audit log
    async function loadAuditLog(userId) {
        try {
            const response = await fetch(`${API.audit()}?user_id=${userId}&limit=20`);
            const data = await response.json();
            
            if (data.success) {
                renderAuditLog(data.data.logs);
            }
        } catch (error) {
            console.error('Error loading audit log:', error);
        }
    }

    // Render audit log
    function renderAuditLog(logs) {
        const container = document.getElementById('audit-log');
        
        if (logs.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">Nenhuma atividade registrada</p>';
            return;
        }
        
        container.innerHTML = logs.map(log => {
            const date = new Date(log.timestamp);
            const riskClass = log.risk_level === 'HIGH' ? 'text-danger' :
                            log.risk_level === 'MEDIUM' ? 'text-warning' : '';
            
            return `
                <div class="audit-entry">
                    <div class="d-flex justify-content-between">
                        <small class="text-muted">${date.toLocaleString('pt-BR')}</small>
                        <small class="${riskClass}">${log.action_category}</small>
                    </div>
                    <div>${log.action}</div>
                    ${log.details ? `<small class="text-muted">${JSON.stringify(log.details)}</small>` : ''}
                </div>
            `;
        }).join('');
    }

    // Toggle node expansion
    function toggleNode(nodeId) {
        const element = document.getElementById(nodeId);
        const isExpanded = element.style.display !== 'none';
        
        element.style.display = isExpanded ? 'none' : 'block';
        
        if (isExpanded) {
            state.expandedNodes.delete(nodeId);
        } else {
            state.expandedNodes.add(nodeId);
        }
        
        // Update chevron
        const chevron = element.previousElementSibling.querySelector('.fa-chevron-right, .fa-chevron-down');
        if (chevron) {
            chevron.className = isExpanded ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
        }
    }

    // Expand all nodes
    function expandAll() {
        document.querySelectorAll('.permission-category, .permission-module').forEach(node => {
            const nodeId = node.querySelector('[id^="cat-"], [id^="mod-"]')?.id;
            if (nodeId) {
                document.getElementById(nodeId).style.display = 'block';
                state.expandedNodes.add(nodeId);
            }
        });
        
        document.querySelectorAll('.fa-chevron-right').forEach(chevron => {
            chevron.className = 'fas fa-chevron-down';
        });
    }

    // Collapse all nodes
    function collapseAll() {
        document.querySelectorAll('[id^="cat-"], [id^="mod-"]').forEach(node => {
            node.style.display = 'none';
        });
        
        state.expandedNodes.clear();
        
        document.querySelectorAll('.fa-chevron-down').forEach(chevron => {
            chevron.className = 'fas fa-chevron-right';
        });
    }

    // Search permissions
    function searchPermissions() {
        const searchTerm = document.getElementById('permission-search').value.toLowerCase();
        state.searchTerm = searchTerm;
        
        if (!searchTerm) {
            // Clear search - show all
            document.querySelectorAll('.permission-category, .permission-module, .permission-submodule').forEach(el => {
                el.style.display = '';
            });
            return;
        }
        
        // Hide all first
        document.querySelectorAll('.permission-category, .permission-module, .permission-submodule').forEach(el => {
            el.style.display = 'none';
        });
        
        // Show matching items and their parents
        document.querySelectorAll('.permission-header').forEach(header => {
            const text = header.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                let element = header.parentElement;
                while (element) {
                    element.style.display = '';
                    // Expand parent nodes
                    const parentContent = element.previousElementSibling?.nextElementSibling;
                    if (parentContent && parentContent.id) {
                        parentContent.style.display = 'block';
                        state.expandedNodes.add(parentContent.id);
                    }
                    element = element.parentElement.closest('.permission-category, .permission-module');
                }
            }
        });
    }

    // Filter users
    function filterUsers() {
        renderUserList();
    }

    // Show templates modal
    async function showTemplates() {
        try {
            const response = await fetch(API.templates());
            const data = await response.json();
            
            if (data.success) {
                state.templates = data.data.templates;
                renderTemplates();
                
                const modal = new bootstrap.Modal(document.getElementById('templateModal'));
                modal.show();
            }
        } catch (error) {
            console.error('Error loading templates:', error);
            showToast('Erro ao carregar templates', 'error');
        }
    }

    // Render templates
    function renderTemplates() {
        const container = document.getElementById('template-list');
        
        container.innerHTML = state.templates.map(template => `
            <div class="card mb-2">
                <div class="card-body">
                    <h6 class="card-title">${template.name}</h6>
                    <p class="card-text text-muted">${template.description || 'Sem descrição'}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <small>${template.permission_count} permissões</small>
                        <button class="btn btn-sm btn-primary" 
                                onclick="PermissionManager.previewTemplate(${template.id})">
                            Visualizar
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Show batch operations modal
    function showBatchOperations() {
        const modal = new bootstrap.Modal(document.getElementById('batchModal'));
        modal.show();
        
        // Load templates for batch apply
        loadBatchTemplates();
        loadBatchUsers();
    }

    // Export configuration
    async function exportConfig() {
        if (!state.selectedUser) {
            showToast('Selecione um usuário primeiro', 'warning');
            return;
        }
        
        try {
            const data = {
                user: state.selectedUser,
                permissions: state.permissions,
                vendors: state.vendors,
                teams: state.teams,
                exported_at: new Date().toISOString()
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `permissions_${state.selectedUser.email}_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            showToast('Configuração exportada com sucesso', 'success');
        } catch (error) {
            console.error('Error exporting config:', error);
            showToast('Erro ao exportar configuração', 'error');
        }
    }

    // Utility functions
    function showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
        state.loading = show;
    }

    function showToast(message, type = 'info') {
        // Using toastr if available, otherwise console
        if (window.toastr) {
            toastr[type](message);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    function getCSRFToken() {
        // Get CSRF token from cookie or meta tag
        const token = document.querySelector('meta[name="csrf-token"]')?.content;
        return token || '';
    }

    function highlightText(text, searchTerm) {
        if (!searchTerm) return text;
        
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<span class="search-highlight">$1</span>');
    }

    function updateUnsavedIndicator() {
        const saveButton = document.querySelector('button[onclick="PermissionManager.savePermissions()"]');
        if (saveButton) {
            if (state.pendingChanges.size > 0) {
                saveButton.classList.add('btn-warning');
                saveButton.innerHTML = '<i class="fas fa-save"></i> Salvar Alterações (' + state.pendingChanges.size + ')';
            } else {
                saveButton.classList.remove('btn-warning');
                saveButton.innerHTML = '<i class="fas fa-save"></i> Salvar Alterações';
            }
        }
    }

    function checkPendingChanges() {
        if (state.pendingChanges.size > 0 && !state.loading) {
            if (confirm('Você tem alterações não salvas. Deseja salvar agora?')) {
                savePermissions();
            }
        }
    }

    function updateStatistics() {
        // Update based on loaded data
        const moduleCount = state.categories.reduce((sum, cat) => sum + (cat.module_count || 0), 0);
        document.getElementById('stat-categories').textContent = state.categories.length;
        document.getElementById('stat-modules').textContent = moduleCount;
    }

    async function loadBatchTemplates() {
        try {
            const response = await fetch(API.templates());
            const data = await response.json();
            
            if (data.success) {
                const select = document.getElementById('batch-template-select');
                select.innerHTML = '<option value="">Escolha um template...</option>' +
                    data.data.templates.map(t => 
                        `<option value="${t.id}">${t.name} (${t.permission_count} permissões)</option>`
                    ).join('');
            }
        } catch (error) {
            console.error('Error loading batch templates:', error);
        }
    }

    async function loadBatchUsers() {
        const container = document.getElementById('batch-user-select');
        container.innerHTML = state.users.map(user => `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${user.id}" id="batch-user-${user.id}">
                <label class="form-check-label" for="batch-user-${user.id}">
                    ${user.nome} (${user.email})
                </label>
            </div>
        `).join('');
    }

    async function applyTemplate() {
        const templateId = document.getElementById('batch-template-select').value;
        if (!templateId) {
            showToast('Selecione um template', 'warning');
            return;
        }
        
        const selectedUsers = Array.from(document.querySelectorAll('#batch-user-select input:checked'))
            .map(input => parseInt(input.value));
        
        if (selectedUsers.length === 0) {
            showToast('Selecione pelo menos um usuário', 'warning');
            return;
        }
        
        if (!confirm(`Aplicar template para ${selectedUsers.length} usuário(s)?`)) {
            return;
        }
        
        showLoading(true);
        
        try {
            const response = await fetch(API.batchApplyTemplate(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    template_id: parseInt(templateId),
                    user_ids: selectedUsers,
                    options: {
                        override_existing: false,
                        apply_vendors: true,
                        apply_teams: true
                    },
                    reason: 'Aplicação em lote via interface'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast(`Template aplicado para ${data.data.affected_users} usuários`, 'success');
                bootstrap.Modal.getInstance(document.getElementById('batchModal')).hide();
                
                // Reload current user if affected
                if (state.selectedUser && selectedUsers.includes(state.selectedUser.id)) {
                    selectUser(state.selectedUser.id);
                }
            } else {
                showToast(data.error.message || 'Erro ao aplicar template', 'error');
            }
        } catch (error) {
            console.error('Error applying template:', error);
            showToast('Erro ao aplicar template', 'error');
        } finally {
            showLoading(false);
        }
    }

    // Public API
    return {
        init,
        selectUser,
        toggleNode,
        expandAll,
        collapseAll,
        searchPermissions,
        filterUsers,
        updatePermission,
        savePermissions,
        addVendor,
        saveVendor,
        removeVendor,
        addTeam: addVendor, // Similar implementation
        saveTeam: saveVendor, // Similar implementation
        removeTeam: removeVendor, // Similar implementation
        showTemplates,
        showBatchOperations,
        exportConfig,
        applyTemplate,
        previewTemplate: (id) => console.log('Preview template:', id) // TODO: Implement
    };
})();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    PermissionManager.init();
});