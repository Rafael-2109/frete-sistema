/**
 * Hierarchical Permission Manager
 * Manages cascading permissions with view/edit checkboxes
 */

class HierarchicalPermissionManager {
    constructor() {
        this.currentUserId = null;
        this.permissionData = null;
        this.vendorData = null;
        this.teamData = null;
        this.templates = null;
        this.changes = new Map();
        
        this.init();
    }

    init() {
        // Initialize event listeners
        this.bindEvents();
        
        // Load initial data
        this.loadUsers();
        this.loadTemplates();
    }

    bindEvents() {
        // User selection
        $('#userSelect').on('change', (e) => {
            this.onUserSelected(e.target.value);
        });

        // Action buttons
        $('#btnScanModules').on('click', () => this.scanModules());
        $('#btnSavePermissions').on('click', () => this.savePermissions());
        $('#btnApplyTemplate').on('click', () => this.showTemplateModal());
        $('#btnExpandAll').on('click', () => this.expandAll());
        $('#btnCollapseAll').on('click', () => this.collapseAll());

        // Batch actions
        $('#selectAllPermissions').on('change', (e) => this.selectAll(e.target.checked));
        $('#btnApplyBatch').on('click', () => this.applyBatchAction());

        // Vendor/Team management
        $('#btnAddVendor').on('click', () => this.showAddModal('vendor'));
        $('#btnAddTeam').on('click', () => this.showAddModal('team'));

        // Modal events
        $('#btnConfirmTemplate').on('click', () => this.applyTemplate());
        $('#btnConfirmAdd').on('click', () => this.confirmAdd());
        $('#templateSelect').on('change', (e) => this.onTemplateSelected(e.target.value));
    }

    // Load users for selection
    async loadUsers() {
        try {
            const response = await fetch('/permissions/api/hierarchical/users');
            const data = await response.json();
            
            if (data.success) {
                const select = $('#userSelect');
                select.empty().append('<option value="">-- Selecione um usuário --</option>');
                
                data.users.forEach(user => {
                    select.append(`
                        <option value="${user.id}">
                            ${user.nome} (${user.email}) - ${user.perfil || 'Sem perfil'}
                        </option>
                    `);
                });
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showError('Erro ao carregar usuários');
        }
    }

    // Load permission templates
    async loadTemplates() {
        try {
            const response = await fetch('/permissions/api/templates');
            const data = await response.json();
            
            if (data.success) {
                this.templates = data.templates;
                const select = $('#templateSelect');
                select.empty().append('<option value="">-- Selecione --</option>');
                
                data.templates.forEach(template => {
                    select.append(`
                        <option value="${template.id}">${template.name}</option>
                    `);
                });
            }
        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }

    // Handle user selection
    async onUserSelected(userId) {
        if (!userId) {
            this.hideAllSections();
            return;
        }

        this.currentUserId = parseInt(userId);
        this.showLoading(true);

        try {
            // Load user permissions and hierarchy
            const [permResponse, vendorResponse, teamResponse] = await Promise.all([
                fetch(`/permissions/api/hierarchy/${userId}`),
                fetch(`/permissions/api/users/${userId}/vendors`),
                fetch(`/permissions/api/users/${userId}/teams`)
            ]);

            const [permData, vendorData, teamData] = await Promise.all([
                permResponse.json(),
                vendorResponse.json(),
                teamResponse.json()
            ]);

            if (permData.success) {
                this.permissionData = permData.hierarchy;
                this.updateUserInfo(permData.user);
                this.renderPermissionTree();
                $('#permissionTreeSection').show();
            }

            if (vendorData.success) {
                this.vendorData = vendorData;
                this.renderVendors(vendorData.vendors);
            }

            if (teamData.success) {
                this.teamData = teamData;
                this.renderTeams(teamData.teams);
            }

            $('#userInfoSection').show();
            $('#vendorTeamSection').show();
            
        } catch (error) {
            console.error('Error loading user data:', error);
            this.showError('Erro ao carregar dados do usuário');
        } finally {
            this.showLoading(false);
        }
    }

    // Update user info cards
    updateUserInfo(user) {
        $('#userProfile').text(user.profile || 'Sem perfil');
        $('#userVendorCount').text(user.vendor_count || 0);
        $('#userTeamCount').text(user.team_count || 0);
        $('#userPermissionCount').text(user.permission_count || 0);
    }

    // Render permission tree with cascading checkboxes
    renderPermissionTree() {
        const container = $('#permissionTree');
        container.empty();

        if (!this.permissionData || this.permissionData.length === 0) {
            container.html('<p class="text-muted">Nenhuma permissão disponível</p>');
            return;
        }

        this.permissionData.forEach(category => {
            const categoryHtml = this.renderCategory(category);
            container.append(categoryHtml);
        });

        // Bind checkbox events
        this.bindTreeEvents();
        this.updateSelectedCount();
    }

    // Render a category node
    renderCategory(category) {
        const categoryId = `category-${category.id}`;
        const hasPermissions = category.permissions && 
            (category.permissions.can_view || category.permissions.can_edit);
        
        return `
            <div class="permission-node category-node" data-id="${category.id}" data-type="category">
                <div class="permission-header">
                    <i class="fas fa-chevron-right toggle-icon"></i>
                    <div class="permission-checkboxes">
                        <div class="form-check form-check-inline">
                            <input class="form-check-input view-check" type="checkbox" 
                                id="${categoryId}-view" data-level="category" 
                                data-id="${category.id}" ${hasPermissions && category.permissions.can_view ? 'checked' : ''}>
                            <label class="form-check-label" for="${categoryId}-view">
                                <i class="fas fa-eye"></i> Ver
                            </label>
                        </div>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input edit-check" type="checkbox" 
                                id="${categoryId}-edit" data-level="category" 
                                data-id="${category.id}" ${hasPermissions && category.permissions.can_edit ? 'checked' : ''}>
                            <label class="form-check-label" for="${categoryId}-edit">
                                <i class="fas fa-edit"></i> Editar
                            </label>
                        </div>
                    </div>
                    <span class="permission-name">
                        <i class="fas ${category.icon || 'fa-folder'}" style="color: ${category.color || '#007bff'}"></i>
                        ${category.display_name}
                    </span>
                    <span class="badge bg-secondary ms-2">${category.modules ? category.modules.length : 0} módulos</span>
                </div>
                <div class="permission-children" style="display: none;">
                    ${category.modules ? category.modules.map(module => this.renderModule(module, category.id)).join('') : ''}
                </div>
            </div>
        `;
    }

    // Render a module node
    renderModule(module, categoryId) {
        const moduleId = `module-${module.id}`;
        const hasPermissions = module.permissions && 
            (module.permissions.can_view || module.permissions.can_edit);
        
        return `
            <div class="permission-node module-node" data-id="${module.id}" data-type="module" data-parent="${categoryId}">
                <div class="permission-header">
                    <i class="fas fa-chevron-right toggle-icon"></i>
                    <div class="permission-checkboxes">
                        <div class="form-check form-check-inline">
                            <input class="form-check-input view-check" type="checkbox" 
                                id="${moduleId}-view" data-level="module" 
                                data-id="${module.id}" ${hasPermissions && module.permissions.can_view ? 'checked' : ''}>
                            <label class="form-check-label" for="${moduleId}-view">
                                <i class="fas fa-eye"></i> Ver
                            </label>
                        </div>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input edit-check" type="checkbox" 
                                id="${moduleId}-edit" data-level="module" 
                                data-id="${module.id}" ${hasPermissions && module.permissions.can_edit ? 'checked' : ''}>
                            <label class="form-check-label" for="${moduleId}-edit">
                                <i class="fas fa-edit"></i> Editar
                            </label>
                        </div>
                    </div>
                    <span class="permission-name">
                        <i class="fas ${module.icon || 'fa-file'}" style="color: ${module.color || '#6c757d'}"></i>
                        ${module.display_name}
                    </span>
                    <span class="badge bg-info ms-2">${module.submodules ? module.submodules.length : 0} submódulos</span>
                </div>
                <div class="permission-children" style="display: none;">
                    ${module.submodules ? module.submodules.map(submodule => this.renderSubmodule(submodule, module.id)).join('') : ''}
                </div>
            </div>
        `;
    }

    // Render a submodule node
    renderSubmodule(submodule, moduleId) {
        const submoduleId = `submodule-${submodule.id}`;
        const hasPermissions = submodule.permissions && 
            (submodule.permissions.can_view || submodule.permissions.can_edit);
        const criticalClass = submodule.critical_level === 'CRITICAL' ? 'critical' : 
                             submodule.critical_level === 'HIGH' ? 'high' : '';
        
        return `
            <div class="permission-node submodule-node ${criticalClass}" data-id="${submodule.id}" data-type="submodule" data-parent="${moduleId}">
                <div class="permission-header">
                    <div class="permission-checkboxes">
                        <div class="form-check form-check-inline">
                            <input class="form-check-input view-check" type="checkbox" 
                                id="${submoduleId}-view" data-level="submodule" 
                                data-id="${submodule.id}" ${hasPermissions && submodule.permissions.can_view ? 'checked' : ''}>
                            <label class="form-check-label" for="${submoduleId}-view">
                                <i class="fas fa-eye"></i> Ver
                            </label>
                        </div>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input edit-check" type="checkbox" 
                                id="${submoduleId}-edit" data-level="submodule" 
                                data-id="${submodule.id}" ${hasPermissions && submodule.permissions.can_edit ? 'checked' : ''}>
                            <label class="form-check-label" for="${submoduleId}-edit">
                                <i class="fas fa-edit"></i> Editar
                            </label>
                        </div>
                    </div>
                    <span class="permission-name">
                        <i class="fas fa-check-circle"></i>
                        ${submodule.display_name}
                        ${submodule.critical_level === 'CRITICAL' ? '<span class="badge bg-danger ms-1">Crítico</span>' : ''}
                        ${submodule.critical_level === 'HIGH' ? '<span class="badge bg-warning ms-1">Alto</span>' : ''}
                    </span>
                </div>
            </div>
        `;
    }

    // Bind tree interaction events
    bindTreeEvents() {
        // Toggle expand/collapse
        $('.toggle-icon').on('click', function() {
            const $node = $(this).closest('.permission-node');
            const $children = $node.find('> .permission-children');
            
            $(this).toggleClass('fa-chevron-right fa-chevron-down');
            $children.slideToggle(200);
        });

        // Checkbox cascade logic
        $('.view-check, .edit-check').on('change', (e) => {
            this.handleCheckboxChange(e.target);
        });
    }

    // Handle checkbox change with cascading logic
    handleCheckboxChange(checkbox) {
        const $checkbox = $(checkbox);
        const isViewCheck = $checkbox.hasClass('view-check');
        const isEditCheck = $checkbox.hasClass('edit-check');
        const isChecked = $checkbox.prop('checked');
        const level = $checkbox.data('level');
        const id = $checkbox.data('id');
        const $node = $checkbox.closest('.permission-node');

        // Track change
        this.trackChange(level, id);

        // Edit requires view
        if (isEditCheck && isChecked) {
            const $viewCheck = $node.find(`> .permission-header .view-check`);
            $viewCheck.prop('checked', true);
            this.trackChange(level, id);
        }

        // Unchecking view unchecks edit
        if (isViewCheck && !isChecked) {
            const $editCheck = $node.find(`> .permission-header .edit-check`);
            $editCheck.prop('checked', false);
            this.trackChange(level, id);
        }

        // Cascade to children
        if (level !== 'submodule') {
            this.cascadeToChildren($node, isViewCheck, isEditCheck, isChecked);
        }

        // Update parent state
        this.updateParentState($node);
        
        // Update count
        this.updateSelectedCount();
    }

    // Cascade checkbox state to children
    cascadeToChildren($parentNode, isViewCheck, isEditCheck, isChecked) {
        const $children = $parentNode.find('.permission-children .permission-node');
        
        $children.each((index, child) => {
            const $child = $(child);
            
            if (isViewCheck) {
                const $childViewCheck = $child.find('> .permission-header .view-check');
                $childViewCheck.prop('checked', isChecked);
                
                // If unchecking view, also uncheck edit
                if (!isChecked) {
                    const $childEditCheck = $child.find('> .permission-header .edit-check');
                    $childEditCheck.prop('checked', false);
                }
            }
            
            if (isEditCheck) {
                const $childEditCheck = $child.find('> .permission-header .edit-check');
                $childEditCheck.prop('checked', isChecked);
                
                // If checking edit, also check view
                if (isChecked) {
                    const $childViewCheck = $child.find('> .permission-header .view-check');
                    $childViewCheck.prop('checked', true);
                }
            }

            // Track changes for all affected children
            const childLevel = $child.data('type');
            const childId = $child.data('id');
            this.trackChange(childLevel, childId);
        });
    }

    // Update parent checkbox state based on children
    updateParentState($node) {
        const parentId = $node.data('parent');
        if (!parentId) return;

        const $parent = $(`.permission-node[data-id="${parentId}"]`).first();
        if ($parent.length === 0) return;

        const $siblings = $(`.permission-node[data-parent="${parentId}"]`);
        
        // Check view state
        const viewCheckedCount = $siblings.find('> .permission-header .view-check:checked').length;
        const $parentViewCheck = $parent.find('> .permission-header .view-check');
        
        if (viewCheckedCount === 0) {
            $parentViewCheck.prop('checked', false).prop('indeterminate', false);
        } else if (viewCheckedCount === $siblings.length) {
            $parentViewCheck.prop('checked', true).prop('indeterminate', false);
        } else {
            $parentViewCheck.prop('checked', false).prop('indeterminate', true);
        }

        // Check edit state
        const editCheckedCount = $siblings.find('> .permission-header .edit-check:checked').length;
        const $parentEditCheck = $parent.find('> .permission-header .edit-check');
        
        if (editCheckedCount === 0) {
            $parentEditCheck.prop('checked', false).prop('indeterminate', false);
        } else if (editCheckedCount === $siblings.length) {
            $parentEditCheck.prop('checked', true).prop('indeterminate', false);
        } else {
            $parentEditCheck.prop('checked', false).prop('indeterminate', true);
        }

        // Track parent change
        const parentLevel = $parent.data('type');
        this.trackChange(parentLevel, parentId);

        // Recursively update grandparent
        this.updateParentState($parent);
    }

    // Track permission changes
    trackChange(level, id) {
        const key = `${level}-${id}`;
        this.changes.set(key, {
            level: level,
            id: id,
            timestamp: Date.now()
        });
    }

    // Update selected count badge
    updateSelectedCount() {
        const viewCount = $('.view-check:checked').length;
        const editCount = $('.edit-check:checked').length;
        $('#selectedCountBadge').text(`${viewCount} visualizar, ${editCount} editar`);
    }

    // Expand all nodes
    expandAll() {
        $('.permission-children').slideDown(200);
        $('.toggle-icon').removeClass('fa-chevron-right').addClass('fa-chevron-down');
    }

    // Collapse all nodes
    collapseAll() {
        $('.permission-children').slideUp(200);
        $('.toggle-icon').removeClass('fa-chevron-down').addClass('fa-chevron-right');
    }

    // Select/deselect all permissions
    selectAll(checked) {
        if (checked) {
            const batchAction = $('input[name="batchAction"]:checked').val();
            if (batchAction === 'view') {
                $('.view-check').prop('checked', true);
            } else if (batchAction === 'edit') {
                $('.view-check, .edit-check').prop('checked', true);
            }
        } else {
            $('.view-check, .edit-check').prop('checked', false);
        }

        // Track all changes
        $('.permission-node').each((index, node) => {
            const $node = $(node);
            const level = $node.data('type');
            const id = $node.data('id');
            this.trackChange(level, id);
        });

        this.updateSelectedCount();
    }

    // Apply batch action to selected permissions
    applyBatchAction() {
        const action = $('input[name="batchAction"]:checked').val();
        if (action === 'none') {
            this.showError('Selecione uma ação para aplicar');
            return;
        }

        // Get all checked category/module checkboxes
        const $checkedNodes = $('.category-node .view-check:checked, .module-node .view-check:checked')
            .closest('.permission-node');

        if ($checkedNodes.length === 0) {
            this.showError('Selecione ao menos uma categoria ou módulo');
            return;
        }

        $checkedNodes.each((index, node) => {
            const $node = $(node);
            
            if (action === 'view') {
                // Apply view only
                $node.find('.view-check').prop('checked', true);
                $node.find('.edit-check').prop('checked', false);
            } else if (action === 'edit') {
                // Apply both view and edit
                $node.find('.view-check, .edit-check').prop('checked', true);
            }

            // Track changes for node and children
            $node.find('.permission-node').addBack().each((i, n) => {
                const $n = $(n);
                this.trackChange($n.data('type'), $n.data('id'));
            });
        });

        this.updateSelectedCount();
        this.showSuccess('Ação em lote aplicada com sucesso');
    }

    // Save permissions
    async savePermissions() {
        if (!this.currentUserId) {
            this.showError('Nenhum usuário selecionado');
            return;
        }

        if (this.changes.size === 0) {
            this.showInfo('Nenhuma alteração para salvar');
            return;
        }

        // Collect permission data
        const permissions = {
            categories: [],
            modules: [],
            submodules: []
        };

        $('.permission-node').each((index, node) => {
            const $node = $(node);
            const type = $node.data('type');
            const id = $node.data('id');
            const viewChecked = $node.find('> .permission-header .view-check').prop('checked');
            const editChecked = $node.find('> .permission-header .edit-check').prop('checked');

            const permData = {
                id: id,
                can_view: viewChecked,
                can_edit: editChecked,
                can_delete: editChecked, // For now, edit includes delete
                can_export: viewChecked  // For now, view includes export
            };

            if (type === 'category') {
                permissions.categories.push(permData);
            } else if (type === 'module') {
                permissions.modules.push(permData);
            } else if (type === 'submodule') {
                permissions.submodules.push(permData);
            }
        });

        try {
            const response = await fetch(`/permissions/api/users/${this.currentUserId}/permissions/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    permissions: permissions,
                    reason: 'Atualização hierárquica de permissões'
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Permissões salvas com sucesso');
                this.changes.clear();
                
                // Reload permissions to ensure consistency
                await this.onUserSelected(this.currentUserId);
            } else {
                this.showError(data.message || 'Erro ao salvar permissões');
            }
        } catch (error) {
            console.error('Error saving permissions:', error);
            this.showError('Erro ao salvar permissões');
        }
    }

    // Scan modules from application
    async scanModules() {
        if (!confirm('Isso irá escanear o sistema e criar módulos/funções automaticamente. Deseja continuar?')) {
            return;
        }

        try {
            // First scan modules
            const scanResponse = await fetch('/permissions/api/hierarchical/scan-modules');
            const scanData = await scanResponse.json();
            
            if (scanData.success) {
                const moduleCount = scanData.count;
                const message = `Encontrados ${moduleCount} módulos. Deseja inicializar a estrutura de permissões?`;
                
                if (confirm(message)) {
                    // Initialize from scan
                    const initResponse = await fetch('/permissions/api/hierarchical/initialize-from-scan', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    const initData = await initResponse.json();
                    
                    if (initData.success) {
                        this.showSuccess('Módulos escaneados e estrutura inicializada com sucesso!');
                        // Reload permissions if user is selected
                        if (this.currentUserId) {
                            this.loadPermissions(this.currentUserId);
                        }
                    } else {
                        this.showError(initData.error || 'Erro ao inicializar estrutura');
                    }
                }
            } else {
                this.showError(scanData.error || 'Erro ao escanear módulos');
            }
        } catch (error) {
            console.error('Error scanning modules:', error);
            this.showError('Erro ao escanear módulos do sistema');
        }
    }

    // Show template modal
    showTemplateModal() {
        $('#templateModal').modal('show');
    }

    // Handle template selection
    onTemplateSelected(templateId) {
        if (!templateId) {
            $('#templateDescription').hide();
            return;
        }

        const template = this.templates.find(t => t.id == templateId);
        if (template) {
            $('#templateDescription')
                .text(template.description || 'Sem descrição')
                .show();
        }
    }

    // Apply selected template
    async applyTemplate() {
        const templateId = $('#templateSelect').val();
        if (!templateId) {
            this.showError('Selecione um template');
            return;
        }

        if (!this.currentUserId) {
            this.showError('Nenhum usuário selecionado');
            return;
        }

        try {
            const response = await fetch(`/permissions/api/users/${this.currentUserId}/permissions/template`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    template_id: templateId
                })
            });

            const data = await response.json();

            if (data.success) {
                $('#templateModal').modal('hide');
                this.showSuccess('Template aplicado com sucesso');
                
                // Reload permissions
                await this.onUserSelected(this.currentUserId);
            } else {
                this.showError(data.message || 'Erro ao aplicar template');
            }
        } catch (error) {
            console.error('Error applying template:', error);
            this.showError('Erro ao aplicar template');
        }
    }

    // Render vendors list
    renderVendors(vendors) {
        const container = $('#vendorsList');
        container.empty();

        if (!vendors || vendors.length === 0) {
            container.html('<p class="text-muted">Nenhum vendedor associado</p>');
            return;
        }

        vendors.forEach(vendor => {
            container.append(`
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <span>${vendor.name}</span>
                    <button class="btn btn-sm btn-danger" onclick="permissionManager.removeVendor(${vendor.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `);
        });
    }

    // Render teams list
    renderTeams(teams) {
        const container = $('#teamsList');
        container.empty();

        if (!teams || teams.length === 0) {
            container.html('<p class="text-muted">Nenhuma equipe associada</p>');
            return;
        }

        teams.forEach(team => {
            container.append(`
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <span>${team.name}</span>
                    <button class="btn btn-sm btn-danger" onclick="permissionManager.removeTeam(${team.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `);
        });
    }

    // Show add vendor/team modal
    async showAddModal(type) {
        const isVendor = type === 'vendor';
        
        $('#addModalTitle').text(isVendor ? 'Adicionar Vendedor' : 'Adicionar Equipe');
        $('#addSelectLabel').text(isVendor ? 'Selecione o Vendedor' : 'Selecione a Equipe');
        $('#addModal').data('type', type);

        // Load available options
        try {
            const endpoint = isVendor ? 
                `/permissions/api/users/${this.currentUserId}/vendors/available` :
                `/permissions/api/users/${this.currentUserId}/teams/available`;
                
            const response = await fetch(endpoint);
            const data = await response.json();

            if (data.success) {
                const select = $('#addSelect');
                select.empty().append('<option value="">-- Selecione --</option>');
                
                const options = isVendor ? data.available_vendors : data.available_teams;
                options.forEach(option => {
                    select.append(`<option value="${option}">${option}</option>`);
                });
            }
        } catch (error) {
            console.error('Error loading options:', error);
            this.showError('Erro ao carregar opções');
            return;
        }

        $('#addModal').modal('show');
    }

    // Confirm add vendor/team
    async confirmAdd() {
        const type = $('#addModal').data('type');
        const value = $('#addSelect').val();
        const observations = $('#addObservations').val();

        if (!value) {
            this.showError('Selecione uma opção');
            return;
        }

        const isVendor = type === 'vendor';
        const endpoint = isVendor ?
            `/permissions/api/users/${this.currentUserId}/vendors` :
            `/permissions/api/users/${this.currentUserId}/teams`;

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    [isVendor ? 'vendor' : 'team']: value,
                    observations: observations
                })
            });

            const data = await response.json();

            if (data.success) {
                $('#addModal').modal('hide');
                $('#addForm')[0].reset();
                this.showSuccess(isVendor ? 'Vendedor adicionado' : 'Equipe adicionada');
                
                // Reload data
                if (isVendor) {
                    const vendorResponse = await fetch(`/permissions/api/users/${this.currentUserId}/vendors`);
                    const vendorData = await vendorResponse.json();
                    if (vendorData.success) {
                        this.renderVendors(vendorData.vendors);
                    }
                } else {
                    const teamResponse = await fetch(`/permissions/api/users/${this.currentUserId}/teams`);
                    const teamData = await teamResponse.json();
                    if (teamData.success) {
                        this.renderTeams(teamData.teams);
                    }
                }
            } else {
                this.showError(data.message || 'Erro ao adicionar');
            }
        } catch (error) {
            console.error('Error adding:', error);
            this.showError('Erro ao adicionar');
        }
    }

    // Remove vendor
    async removeVendor(vendorId) {
        if (!confirm('Confirma a remoção deste vendedor?')) {
            return;
        }

        try {
            const response = await fetch(`/permissions/api/users/${this.currentUserId}/vendors/${vendorId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Vendedor removido');
                
                // Reload vendors
                const vendorResponse = await fetch(`/permissions/api/users/${this.currentUserId}/vendors`);
                const vendorData = await vendorResponse.json();
                if (vendorData.success) {
                    this.renderVendors(vendorData.vendors);
                }
            } else {
                this.showError(data.message || 'Erro ao remover vendedor');
            }
        } catch (error) {
            console.error('Error removing vendor:', error);
            this.showError('Erro ao remover vendedor');
        }
    }

    // Remove team
    async removeTeam(teamId) {
        if (!confirm('Confirma a remoção desta equipe?')) {
            return;
        }

        try {
            const response = await fetch(`/permissions/api/users/${this.currentUserId}/teams/${teamId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Equipe removida');
                
                // Reload teams
                const teamResponse = await fetch(`/permissions/api/users/${this.currentUserId}/teams`);
                const teamData = await teamResponse.json();
                if (teamData.success) {
                    this.renderTeams(teamData.teams);
                }
            } else {
                this.showError(data.message || 'Erro ao remover equipe');
            }
        } catch (error) {
            console.error('Error removing team:', error);
            this.showError('Erro ao remover equipe');
        }
    }

    // UI Helper methods
    showLoading(show) {
        if (show) {
            $('#loadingSpinner').show();
            $('#permissionTreeSection, #userInfoSection, #vendorTeamSection').hide();
        } else {
            $('#loadingSpinner').hide();
        }
    }

    hideAllSections() {
        $('#userInfoSection, #vendorTeamSection, #permissionTreeSection').hide();
    }

    showSuccess(message) {
        $('#successMessage').text(message);
        const toast = new bootstrap.Toast($('#successToast')[0]);
        toast.show();
    }

    showError(message) {
        $('#errorMessage').text(message);
        const toast = new bootstrap.Toast($('#errorToast')[0]);
        toast.show();
    }

    showInfo(message) {
        // Use success toast for info messages
        this.showSuccess(message);
    }
}

// Initialize when document is ready
let permissionManager;
$(document).ready(() => {
    permissionManager = new HierarchicalPermissionManager();
});