/**
 * cadastros-modal.js - CRUD Modal para Cadastros de Ocorrencias
 *
 * Funcoes:
 * - abrirCadastrosCom(tab) - abre modal focando na aba correta
 * - carregarCadastros(tipo) - GET API, renderiza tabela
 * - salvarCadastro(tipo) - POST API, recarrega tabela + selects
 * - editarCadastro(tipo, id) - PUT API inline
 * - toggleCadastro(tipo, id) - PATCH toggle ativo
 * - atualizarSelectsNaPagina(tipo) - atualiza selects sem reload
 */

const BASE_URL_CADASTROS = '/devolucao/cadastros/api';

// Cache de dados carregados (para nao recarregar ao trocar aba)
const _cadastrosCache = {};

// =========================================================================
// Abrir modal focando em aba especifica
// =========================================================================
function abrirCadastrosCom(tab) {
    const modal = new bootstrap.Modal(document.getElementById('modal-cadastros-ocorrencia'));
    modal.show();

    // Ativar aba correta
    const tabBtn = document.getElementById('tab-' + tab);
    if (tabBtn) {
        const bsTab = new bootstrap.Tab(tabBtn);
        bsTab.show();
    }

    // Carregar dados da aba
    carregarCadastros(tab);
}

// =========================================================================
// Event listener para carregar ao trocar aba
// =========================================================================
document.addEventListener('DOMContentLoaded', function() {
    const tabList = document.getElementById('cadastrosTabList');
    if (tabList) {
        tabList.querySelectorAll('button[data-tipo]').forEach(btn => {
            btn.addEventListener('shown.bs.tab', function() {
                carregarCadastros(this.dataset.tipo);
            });
        });
    }
});

// =========================================================================
// Carregar dados de um tipo
// =========================================================================
async function carregarCadastros(tipo) {
    const tbody = document.getElementById('tbody-' + tipo);
    if (!tbody) return;

    try {
        const response = await fetch(`${BASE_URL_CADASTROS}/${tipo}/todos`);
        const result = await response.json();

        if (!result.sucesso) {
            tbody.innerHTML = '<tr><td colspan="2" class="text-danger">Erro ao carregar</td></tr>';
            return;
        }

        _cadastrosCache[tipo] = result.itens;

        if (result.itens.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">Nenhum item cadastrado</td></tr>';
            return;
        }

        tbody.innerHTML = result.itens.map(item => renderizarLinhaCadastro(tipo, item)).join('');

    } catch (error) {
        console.error('Erro ao carregar cadastros:', error);
        tbody.innerHTML = '<tr><td colspan="2" class="text-danger">Erro de conexao</td></tr>';
    }
}

// =========================================================================
// Renderizar linha da tabela
// =========================================================================
function renderizarLinhaCadastro(tipo, item) {
    const classeInativo = item.ativo ? '' : 'cadastro-item-inativo';
    const btnToggleText = item.ativo ? 'Desativar' : 'Ativar';
    const btnToggleClass = item.ativo ? 'btn-outline-warning' : 'btn-outline-success';

    return `
        <tr class="cadastro-item-row ${classeInativo}" data-id="${item.id}">
            <td>
                <span class="cadastro-descricao" id="desc-${tipo}-${item.id}">${item.descricao}</span>
                <input type="text" class="form-control form-control-sm d-none"
                       id="input-edit-${tipo}-${item.id}" value="${item.descricao}"
                       onkeydown="if(event.key==='Enter') confirmarEdicao('${tipo}', ${item.id})">
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary btn-sm" onclick="iniciarEdicao('${tipo}', ${item.id})" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn ${btnToggleClass} btn-sm" onclick="toggleCadastro('${tipo}', ${item.id})" title="${btnToggleText}">
                        <i class="bi bi-${item.ativo ? 'eye-slash' : 'eye'}"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

// =========================================================================
// Iniciar edicao inline
// =========================================================================
function iniciarEdicao(tipo, id) {
    // Mostrar input, esconder span
    document.getElementById(`desc-${tipo}-${id}`).classList.add('d-none');
    const inputDesc = document.getElementById(`input-edit-${tipo}-${id}`);
    inputDesc.classList.remove('d-none');
    inputDesc.focus();

    // Trocar botao editar por confirmar
    const row = inputDesc.closest('tr');
    const btnEditar = row.querySelector('.btn-outline-primary');
    btnEditar.innerHTML = '<i class="bi bi-check-lg"></i>';
    btnEditar.className = 'btn btn-success btn-sm';
    btnEditar.setAttribute('onclick', `confirmarEdicao('${tipo}', ${id})`);
}

// =========================================================================
// Confirmar edicao inline
// =========================================================================
async function confirmarEdicao(tipo, id) {
    const descricao = document.getElementById(`input-edit-${tipo}-${id}`).value.trim();

    if (!descricao) return;

    try {
        const response = await fetch(`${BASE_URL_CADASTROS}/${tipo}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify({ descricao })
        });
        const result = await response.json();

        if (result.sucesso) {
            carregarCadastros(tipo);
            atualizarSelectsNaPagina(tipo);
        } else {
            alert(result.erro || 'Erro ao editar');
        }
    } catch (error) {
        console.error('Erro ao editar:', error);
        alert('Erro de conexao');
    }
}

// =========================================================================
// Salvar novo item
// =========================================================================
async function salvarCadastro(tipo) {
    const input = document.getElementById('input-novo-' + tipo);
    const descricao = input.value.trim();

    if (!descricao) {
        input.focus();
        return;
    }

    try {
        const response = await fetch(`${BASE_URL_CADASTROS}/${tipo}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify({ descricao })
        });
        const result = await response.json();

        if (result.sucesso) {
            input.value = '';
            carregarCadastros(tipo);
            atualizarSelectsNaPagina(tipo);
        } else {
            alert(result.erro || 'Erro ao salvar');
        }
    } catch (error) {
        console.error('Erro ao salvar:', error);
        alert('Erro de conexao');
    }
}

// =========================================================================
// Toggle ativo/inativo
// =========================================================================
async function toggleCadastro(tipo, id) {
    try {
        const response = await fetch(`${BASE_URL_CADASTROS}/${tipo}/${id}/toggle`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
            }
        });
        const result = await response.json();

        if (result.sucesso) {
            carregarCadastros(tipo);
            atualizarSelectsNaPagina(tipo);
        } else {
            alert(result.erro || 'Erro ao alterar status');
        }
    } catch (error) {
        console.error('Erro ao toggle:', error);
        alert('Erro de conexao');
    }
}

// =========================================================================
// Atualizar SELECTs na pagina sem reload
// =========================================================================
async function atualizarSelectsNaPagina(tipo) {
    try {
        const response = await fetch(`${BASE_URL_CADASTROS}/${tipo}`);
        const result = await response.json();

        if (!result.sucesso) return;

        // Mapear tipo para seletores de select na pagina
        const seletores = {
            'categorias': 'select.categoria-select',
            'subcategorias': 'select.subcategoria-select',
            'responsaveis': 'select[name="responsavel_id"]',
            'origens': 'select[name="origem_id"]',
            'autorizados': 'select[name="autorizado_por_id"]',
        };

        const seletor = seletores[tipo];
        if (!seletor) return;

        const selects = document.querySelectorAll(seletor);
        selects.forEach(select => {
            const valorAtual = select.value;

            // Manter primeira opcao (Selecione...)
            const primeiraOpcao = select.querySelector('option:first-child');
            select.innerHTML = '';
            if (primeiraOpcao && primeiraOpcao.value === '') {
                select.appendChild(primeiraOpcao);
            } else {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Selecione...';
                select.appendChild(opt);
            }

            // Popular com novos dados
            result.itens.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = item.descricao;
                if (String(item.id) === String(valorAtual)) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });
        });

    } catch (error) {
        console.error('Erro ao atualizar selects:', error);
    }
}
