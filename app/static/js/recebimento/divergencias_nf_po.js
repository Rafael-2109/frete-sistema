/**
 * Divergencias NF x PO - JavaScript (especifico da tela)
 *
 * Funcoes compartilhadas (formatacao, modais, download) estao em divergencias_shared.js
 *
 * Contem:
 * - Executar Validacao Manual (com periodo)
 * - Autocomplete de Produtos (filtro)
 * - Inicializacao
 */

// =============================================================================
// EXECUTAR VALIDACAO COM MODAL DE PERIODO
// =============================================================================

function confirmarValidacao() {
    const dataDe = document.getElementById('validacaoDataDe').value;
    const dataAte = document.getElementById('validacaoDataAte').value;

    if (!dataDe || !dataAte) {
        alert('Selecione o período (De e Até)');
        return;
    }

    const de = new Date(dataDe);
    const ate = new Date(dataAte);
    const diffDias = (ate - de) / (1000 * 60 * 60 * 24);
    if (diffDias < 0) {
        alert('Data "De" deve ser anterior à data "Até"');
        return;
    }
    if (diffDias > 90) {
        alert('Período máximo: 90 dias');
        return;
    }

    const btn = document.getElementById('btnConfirmarValidacao');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Executando...';
    btn.disabled = true;

    fetch('/api/recebimento/executar-validacao', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ data_de: dataDe, data_ate: dataAte })
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            const res = data.resultado || {};
            const syncPo = res.sync_pos_vinculados || {};
            const msg = [
                'Validação executada com sucesso!',
                '',
                `POs vinculados (sync): ${syncPo.dfes_atualizados || 0} atualizados`,
                `DFEs processados: ${res.dfes_processados || 0}`,
                `Fase 1 - Aprovados: ${res.fase1_fiscal?.dfes_aprovados || 0}`,
                `Fase 1 - Bloqueados: ${res.fase1_fiscal?.dfes_bloqueados || 0}`,
                `Fase 2 - Aprovados: ${res.fase2_nf_po?.dfes_aprovados || 0}`,
                `Fase 2 - Bloqueados: ${res.fase2_nf_po?.dfes_bloqueados || 0}`
            ].join('\n');
            alert(msg);
            location.reload();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    })
    .catch(err => {
        alert('Erro de conexão: ' + err.message);
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}

// Inicializar datas padrao (ultimos 7 dias)
function initValidacaoDatas() {
    const hoje = new Date();
    const seteDiasAtras = new Date();
    seteDiasAtras.setDate(hoje.getDate() - 7);

    const inputDe = document.getElementById('validacaoDataDe');
    const inputAte = document.getElementById('validacaoDataAte');

    if (inputDe && inputAte) {
        inputAte.value = hoje.toISOString().split('T')[0];
        inputDe.value = seteDiasAtras.toISOString().split('T')[0];
    }
}

// =============================================================================
// AUTOCOMPLETE DE PRODUTOS (FILTRO)
// =============================================================================

let autocompleteTimeout = null;

function initAutocompleteProduto() {
    const inputProduto = document.getElementById('filtro_produto');
    const listaProdutos = document.getElementById('autocomplete_produtos');

    if (!inputProduto || !listaProdutos) return;

    inputProduto.addEventListener('input', function() {
        const termo = this.value.trim();

        if (autocompleteTimeout) {
            clearTimeout(autocompleteTimeout);
        }

        if (termo.length < 2) {
            listaProdutos.style.display = 'none';
            return;
        }

        autocompleteTimeout = setTimeout(() => {
            buscarProdutosAutocomplete(termo);
        }, 300);
    });

    document.addEventListener('click', function(e) {
        if (!inputProduto.contains(e.target) && !listaProdutos.contains(e.target)) {
            listaProdutos.style.display = 'none';
        }
    });

    inputProduto.addEventListener('keydown', function(e) {
        const items = listaProdutos.querySelectorAll('.list-group-item');
        const ativo = listaProdutos.querySelector('.list-group-item.active');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (!ativo && items.length > 0) {
                items[0].classList.add('active');
            } else if (ativo && ativo.nextElementSibling) {
                ativo.classList.remove('active');
                ativo.nextElementSibling.classList.add('active');
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (ativo && ativo.previousElementSibling) {
                ativo.classList.remove('active');
                ativo.previousElementSibling.classList.add('active');
            }
        } else if (e.key === 'Enter') {
            if (ativo) {
                e.preventDefault();
                ativo.click();
            }
        } else if (e.key === 'Escape') {
            listaProdutos.style.display = 'none';
        }
    });
}

function buscarProdutosAutocomplete(termo) {
    const listaProdutos = document.getElementById('autocomplete_produtos');

    fetch(`/api/recebimento/autocomplete-produtos?termo=${encodeURIComponent(termo)}&limit=15`)
        .then(r => r.json())
        .then(data => {
            if (data.erro) {
                console.error('Erro autocomplete:', data.erro);
                return;
            }

            if (data.length === 0) {
                listaProdutos.innerHTML = `
                    <div class="list-group-item text-muted small py-2">
                        <i class="fas fa-search me-2"></i>Nenhum produto encontrado
                    </div>
                `;
                listaProdutos.style.display = 'block';
                return;
            }

            listaProdutos.innerHTML = data.map(p => `
                <a href="#" class="list-group-item list-group-item-action py-2"
                   data-cod="${p.cod_produto}" data-nome="${p.nome_produto || ''}">
                    <strong class="text-primary">${p.cod_produto}</strong>
                    <br><small class="text-muted">${p.nome_produto || '-'}</small>
                </a>
            `).join('');

            listaProdutos.querySelectorAll('.list-group-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    const cod = this.dataset.cod;
                    document.getElementById('filtro_produto').value = cod;
                    listaProdutos.style.display = 'none';
                });
            });

            listaProdutos.style.display = 'block';
        })
        .catch(err => {
            console.error('Erro ao buscar produtos:', err);
        });
}

// =============================================================================
// INICIALIZACAO
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initModaisCompartilhados();
    initValidacaoDatas();
    initAutocompleteProduto();
});
