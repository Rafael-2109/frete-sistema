/* ============================================================================
 * Análise de Produção — Modal de Componentes (compartilhado)
 *
 * Usado em:
 *   - app/templates/manufatura/analise_producao/index.html
 *   - app/templates/estoque/listar_movimentacoes.html (modal inline)
 *
 * Depende de: Bootstrap 5 (modal), SweetAlert2 (Swal global),
 *             <meta name="csrf-token"> (presente no base.html) e do partial
 *             _modal_componentes.html (estrutura DOM do modal).
 * ==========================================================================*/

// Estado do modal
let producaoAtualId = null;
let producaoAtualGrupo = null; // {ordem_producao, cod_produto} quando é grupo
let componentesOriginais = {};
let _buscaComponenteTimer = null;

function _csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function formatarNumero(valor) {
    if (valor === null || valor === undefined) return '-';
    return parseFloat(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3
    });
}

// ============================================================
// ABERTURA DO MODAL (individual e grupo)
// ============================================================

function abrirModalComponentes(producaoId) {
    producaoAtualId = producaoId;
    producaoAtualGrupo = null;
    componentesOriginais = {};

    document.getElementById('corpoComponentes').innerHTML = `
        <tr><td colspan="6" class="text-center py-4">
            <i class="fas fa-spinner fa-spin me-2"></i> Carregando componentes...
        </td></tr>`;
    _resetBuscaComponente();

    const modal = new bootstrap.Modal(document.getElementById('modalComponentes'));
    modal.show();

    fetch(`/manufatura/analise-producao/${producaoId}/componentes`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                preencherModalComponentes(data);
            } else {
                Swal.fire('Erro', data.message || 'Erro ao carregar componentes', 'error');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            Swal.fire('Erro', 'Erro de comunicação com o servidor', 'error');
        });
}

function abrirModalComponentesGrupo(ordemProducao, codProduto) {
    producaoAtualId = null;
    producaoAtualGrupo = { ordem_producao: ordemProducao, cod_produto: codProduto };
    componentesOriginais = {};

    document.getElementById('corpoComponentes').innerHTML = `
        <tr><td colspan="6" class="text-center py-4">
            <i class="fas fa-spinner fa-spin me-2"></i> Carregando componentes do grupo...
        </td></tr>`;
    _resetBuscaComponente();

    const modal = new bootstrap.Modal(document.getElementById('modalComponentes'));
    modal.show();

    fetch(`/manufatura/analise-producao/componentes-grupo?ordem_producao=${encodeURIComponent(ordemProducao)}&cod_produto=${encodeURIComponent(codProduto)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                preencherModalComponentes(data);
            } else {
                Swal.fire('Erro', data.message || 'Erro ao carregar componentes do grupo', 'error');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            Swal.fire('Erro', 'Erro de comunicação com o servidor', 'error');
        });
}

// ============================================================
// RENDER DE LINHA + PREENCHIMENTO
// ============================================================

function _escAttr(valor) {
    return String(valor).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function htmlLinhaComponente(comp) {
    // Valor inicial do Ajuste = -(consumo_real - consumo_previsto)  (mesma base do save)
    const ajusteAtual = -((comp.consumo_real || 0) - (comp.consumo_previsto || 0));
    const nivelClass = `nivel-${Math.min(comp.nivel || 1, 4)}`;
    const treeIcon = comp.tem_estrutura
        ? '<i class="fas fa-folder-open tree-icon"></i>'
        : '<i class="fas fa-cube tree-icon"></i>';
    const tipoBadgeClass = `tipo-badge-${comp.tipo}`;
    const foraBomBadge = comp.fora_bom
        ? ' <span class="badge bg-warning text-dark" title="Componente apontado fora do BOM atual">Fora do BOM</span>'
        : '';
    const codAttr = _escAttr(comp.cod_produto);

    return `
        <tr class="componente-row" data-cod="${comp.cod_produto}">
            <td>
                <div class="nivel-indent ${nivelClass}">
                    ${treeIcon}
                    <strong>${comp.cod_produto}</strong>${foraBomBadge}
                    <br>
                    <small class="text-muted">${comp.nome_produto}</small>
                </div>
            </td>
            <td class="text-center">
                <span class="badge ${tipoBadgeClass}">${comp.tipo}</span>
            </td>
            <td class="text-end">
                <span class="${comp.estoque_atual < 0 ? 'text-danger' : ''}">${formatarNumero(comp.estoque_atual)}</span>
            </td>
            <td class="text-end fw-bold">${formatarNumero(-comp.consumo_previsto)}</td>
            <td class="text-end">
                <input type="number"
                       class="form-control form-control-sm input-ajuste"
                       id="ajuste-${comp.cod_produto}"
                       value="${ajusteAtual.toFixed(3)}"
                       step="0.001"
                       onchange="calcularConsumoReal('${codAttr}')"
                       onfocus="this.select()">
            </td>
            <td class="text-end">
                <input type="number"
                       class="form-control form-control-sm input-ajuste"
                       id="consumo-real-${comp.cod_produto}"
                       value="${(-comp.consumo_real).toFixed(3)}"
                       step="0.001"
                       onchange="calcularAjuste('${codAttr}')"
                       onfocus="this.select()">
            </td>
        </tr>`;
}

function preencherModalComponentes(data) {
    const prod = data.producao;

    document.getElementById('modal-prod-id').textContent = prod.id;
    document.getElementById('modal-prod-codigo').textContent = prod.cod_produto;
    document.getElementById('modal-prod-nome').textContent = prod.nome_produto;
    document.getElementById('modal-prod-qtd').textContent = formatarNumero(prod.qtd_produzida);
    document.getElementById('modal-prod-data').textContent = prod.data_movimentacao;

    const opElement = document.getElementById('modal-prod-op');
    if (prod.ordem_producao) {
        opElement.innerHTML = `<span class="badge bg-primary">${prod.ordem_producao}</span>`;
        if (prod.qtd_producoes && prod.qtd_producoes > 1) {
            opElement.innerHTML += ` <span class="badge bg-secondary">${prod.qtd_producoes} produções</span>`;
        }
    } else {
        opElement.textContent = '-';
    }

    const tbody = document.getElementById('corpoComponentes');
    componentesOriginais = {};

    if (!data.componentes || data.componentes.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6" class="text-center py-4 text-muted">
                <i class="fas fa-info-circle me-2"></i>
                Este produto não possui estrutura de materiais (BOM)
            </td></tr>`;
        return;
    }

    let html = '';
    data.componentes.forEach(comp => {
        componentesOriginais[comp.cod_produto] = {
            consumo_previsto: comp.consumo_previsto,
            consumo_real: comp.consumo_real,
            ajuste_registrado: comp.ajuste_registrado,
            fora_bom: comp.fora_bom || false
        };
        html += htmlLinhaComponente(comp);
    });
    tbody.innerHTML = html;
}

// ============================================================
// CÁLCULOS DE AJUSTE
// ============================================================

function calcularConsumoReal(codProduto) {
    const original = componentesOriginais[codProduto];
    const inputAjuste = document.getElementById(`ajuste-${codProduto}`);
    const inputConsumoReal = document.getElementById(`consumo-real-${codProduto}`);

    const ajuste = parseFloat(inputAjuste.value) || 0;
    // Consumo real = -previsto + ajuste (ambos negativos quando consumiu)
    const consumoReal = -original.consumo_previsto + ajuste;

    inputConsumoReal.value = consumoReal.toFixed(3);
    marcarLinha(codProduto, ajuste);
}

function calcularAjuste(codProduto) {
    const original = componentesOriginais[codProduto];
    const inputAjuste = document.getElementById(`ajuste-${codProduto}`);
    const inputConsumoReal = document.getElementById(`consumo-real-${codProduto}`);

    const consumoReal = parseFloat(inputConsumoReal.value) || 0;
    // Ajuste = consumoReal - (-previsto) = consumoReal + previsto
    const ajuste = consumoReal + original.consumo_previsto;

    inputAjuste.value = ajuste.toFixed(3);
    marcarLinha(codProduto, ajuste);
}

function marcarLinha(codProduto, ajuste) {
    const original = componentesOriginais[codProduto];
    // Baseline: -(consumo_real - consumo_previsto) — idêntico ao usado em salvarAjustes()
    const ajusteOriginal = -(original.consumo_real - original.consumo_previsto);
    const row = document.querySelector(`tr[data-cod="${codProduto}"]`);
    const inputAjuste = document.getElementById(`ajuste-${codProduto}`);

    const diferenca = Math.abs(ajuste - ajusteOriginal);

    if (diferenca > 0.001) {
        row.classList.add('modificado');
    } else {
        row.classList.remove('modificado');
    }

    if (ajuste > 0.001) {
        inputAjuste.classList.add('ajuste-positivo');
        inputAjuste.classList.remove('ajuste-negativo');
    } else if (ajuste < -0.001) {
        inputAjuste.classList.add('ajuste-negativo');
        inputAjuste.classList.remove('ajuste-positivo');
    } else {
        inputAjuste.classList.remove('ajuste-positivo', 'ajuste-negativo');
    }
}

// ============================================================
// ADICIONAR COMPONENTE (autocomplete)
// ============================================================

function _resetBuscaComponente() {
    const wrap = document.getElementById('buscaComponenteWrap');
    const input = document.getElementById('inputBuscaComponente');
    const dd = document.getElementById('dropdownBuscaComponente');
    if (wrap) wrap.style.display = 'none';
    if (input) input.value = '';
    if (dd) { dd.style.display = 'none'; dd.innerHTML = ''; }
}

function mostrarBuscaComponente() {
    const wrap = document.getElementById('buscaComponenteWrap');
    const input = document.getElementById('inputBuscaComponente');
    if (!wrap) return;
    wrap.style.display = '';
    if (input) input.focus();
}

function buscarComponentes() {
    const input = document.getElementById('inputBuscaComponente');
    const dd = document.getElementById('dropdownBuscaComponente');
    if (!input || !dd) return;

    const termo = input.value.trim();
    if (termo.length < 3) {
        dd.style.display = 'none';
        dd.innerHTML = '';
        return;
    }

    clearTimeout(_buscaComponenteTimer);
    _buscaComponenteTimer = setTimeout(() => {
        fetch(`/manufatura/analise-producao/buscar-produtos?q=${encodeURIComponent(termo)}`)
            .then(response => response.json())
            .then(data => {
                const produtos = (data && data.produtos) || [];
                if (produtos.length === 0) {
                    dd.innerHTML = '<div class="list-group-item text-muted small">Nenhum produto encontrado</div>';
                    dd.style.display = '';
                    return;
                }
                dd.innerHTML = produtos.map(p => `
                    <button type="button" class="list-group-item list-group-item-action py-1"
                            onclick="selecionarComponente('${_escAttr(p.cod_produto)}', '${_escAttr(p.nome_produto)}')">
                        <strong>${p.cod_produto}</strong>
                        <small class="text-muted">${p.nome_produto}</small>
                    </button>`).join('');
                dd.style.display = '';
            })
            .catch(error => {
                console.error('Erro na busca de componentes:', error);
                dd.style.display = 'none';
            });
    }, 250);
}

function selecionarComponente(codProduto, nomeProduto) {
    const dd = document.getElementById('dropdownBuscaComponente');
    const input = document.getElementById('inputBuscaComponente');

    // Já está na lista? avisa e foca a linha existente
    if (Object.prototype.hasOwnProperty.call(componentesOriginais, codProduto)) {
        Swal.fire('Atenção', `O componente ${codProduto} já está na lista.`, 'warning');
        const linha = document.querySelector(`tr[data-cod="${codProduto}"]`);
        if (linha) linha.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (dd) { dd.style.display = 'none'; dd.innerHTML = ''; }
        if (input) input.value = '';
        return;
    }

    const comp = {
        cod_produto: codProduto,
        nome_produto: nomeProduto,
        tipo: 'COMPONENTE',
        nivel: 1,
        consumo_previsto: 0,
        consumo_registrado: 0,
        ajuste_registrado: 0,
        consumo_real: 0,
        estoque_atual: 0,
        tem_estrutura: false,
        fora_bom: true
    };
    componentesOriginais[codProduto] = {
        consumo_previsto: 0,
        consumo_real: 0,
        ajuste_registrado: 0,
        fora_bom: true
    };

    const tbody = document.getElementById('corpoComponentes');
    // Se só havia o placeholder "sem BOM", limpa antes de inserir
    if (tbody.querySelector('td[colspan]')) {
        tbody.innerHTML = '';
    }
    tbody.insertAdjacentHTML('beforeend', htmlLinhaComponente(comp));

    if (dd) { dd.style.display = 'none'; dd.innerHTML = ''; }
    if (input) input.value = '';

    const novoInput = document.getElementById(`consumo-real-${codProduto}`);
    if (novoInput) novoInput.focus();
}

// Fecha o dropdown ao clicar fora da área de busca
document.addEventListener('click', function (e) {
    const wrap = document.getElementById('buscaComponenteWrap');
    const dd = document.getElementById('dropdownBuscaComponente');
    if (!wrap || !dd) return;
    if (!wrap.contains(e.target)) {
        dd.style.display = 'none';
    }
});

// ============================================================
// SALVAR
// ============================================================

function salvarAjustes() {
    const ajustesParaSalvar = [];

    Object.keys(componentesOriginais).forEach(codProduto => {
        const original = componentesOriginais[codProduto];
        const inputAjuste = document.getElementById(`ajuste-${codProduto}`);

        if (!inputAjuste) return;

        const ajusteNovo = parseFloat(inputAjuste.value) || 0;
        // Baseline idêntico ao init do input e a marcarLinha(): -(consumo_real - consumo_previsto)
        const ajusteOriginal = -(original.consumo_real - original.consumo_previsto);

        const diferenca = ajusteNovo - ajusteOriginal;

        if (Math.abs(diferenca) > 0.001) {
            ajustesParaSalvar.push({
                cod_produto: codProduto,
                qtd_ajuste: -diferenca  // Inverter para o backend (visão de consumo)
            });
        }
    });

    if (ajustesParaSalvar.length === 0) {
        Swal.fire('Aviso', 'Nenhum ajuste para salvar', 'info');
        return;
    }

    Swal.fire({
        title: 'Confirmar Ajustes',
        html: `Serão salvos <strong>${ajustesParaSalvar.length}</strong> ajuste(s).<br><br>
               <small class="text-muted">Ajustes negativos aumentam o consumo, positivos reduzem.</small>`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Salvar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            executarSalvarAjustes(ajustesParaSalvar);
        }
    });
}

function executarSalvarAjustes(ajustes) {
    let url, body;

    if (producaoAtualGrupo) {
        url = '/manufatura/analise-producao/grupo/ajustar';
        body = JSON.stringify({
            ordem_producao: producaoAtualGrupo.ordem_producao,
            cod_produto: producaoAtualGrupo.cod_produto,
            ajustes: ajustes
        });
    } else {
        url = `/manufatura/analise-producao/${producaoAtualId}/ajustar`;
        body = JSON.stringify({ ajustes: ajustes });
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': _csrfToken()
        },
        body: body
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Sucesso!',
                text: data.message,
                timer: 2000,
                showConfirmButton: false
            });

            // Recarregar componentes (reflete os novos AJUSTE e a dedup BOM ∪ apontados)
            if (producaoAtualGrupo) {
                abrirModalComponentesGrupo(producaoAtualGrupo.ordem_producao, producaoAtualGrupo.cod_produto);
            } else {
                abrirModalComponentes(producaoAtualId);
            }
        } else {
            Swal.fire('Erro', data.message || 'Erro ao salvar ajustes', 'error');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        Swal.fire('Erro', 'Erro de comunicação com o servidor', 'error');
    });
}
