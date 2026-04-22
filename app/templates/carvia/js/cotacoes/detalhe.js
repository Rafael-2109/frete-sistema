const cotacaoId = CARVIA_DATA.cotacaoId;
const modelosMoto = CARVIA_DATA.modelosMoto;
const _criacaoTardia = CARVIA_DATA.criacaoTardia || false;
const _cotacaoStatus = CARVIA_DATA.cotacaoStatus || '';

// Endereco de entrega da cotacao (override, pode ser null)
const _entregaCotacao = CARVIA_DATA.entregaCotacao;

/* ===== Readonly: desabilitar campos por status ===== */
const _readonly = (!_criacaoTardia && ['APROVADO', 'CANCELADO'].includes(_cotacaoStatus));
const _podeEditar = ['RASCUNHO', 'RECUSADO', 'PENDENTE_ADMIN'].includes(_cotacaoStatus);

document.addEventListener('DOMContentLoaded', () => {
    // Criacao tardia: bloquear subset especifico
    if (_criacaoTardia) {
        ['selCliente', 'selTipoMaterial',
         'inpPeso', 'inpValorMerc', 'inpVolumes',
         'inpDimC', 'inpDimL', 'inpDimA',
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });
    }

    // Readonly (APROVADO/CANCELADO sem tardia): desabilitar inputs de moto dinamicos
    if (_readonly) {
        document.querySelectorAll('#tbodyMotos input, #tbodyMotos select, #tbodyMotos button').forEach(el => {
            el.disabled = true;
        });
    }

    // Auto-save em RASCUNHO: salvar ao alterar campos
    if (_podeEditar) {
        _setupAutoSave();
    }
});

/* ===== Auto-save com debounce ===== */
let _autoSaveTimer = null;
function autoSave(campo, valor) {
    clearTimeout(_autoSaveTimer);
    _autoSaveTimer = setTimeout(() => {
        const payload = {};
        // Converter strings vazias para null em IDs
        if (campo.endsWith('_id')) {
            payload[campo] = valor ? parseInt(valor) : null;
        } else if (['peso', 'valor_mercadoria', 'dimensao_c', 'dimensao_l', 'dimensao_a',
                     'percentual_remetente', 'percentual_destinatario'].includes(campo)) {
            payload[campo] = valor ? parseFloat(valor) : null;
        } else if (['volumes', 'prazo_dias'].includes(campo)) {
            payload[campo] = valor ? parseInt(valor) : null;
        } else {
            payload[campo] = valor || null;
        }
        apiCall(`/carvia/api/cotacoes/${cotacaoId}`, 'PUT', payload).then(d => {
            if (d.sucesso) {
                _showAutoSaveFeedback(campo);
            } else {
                console.warn('Auto-save falhou:', campo, d.erro);
            }
        });
    }, 500);
}

function _showAutoSaveFeedback(campo) {
    // Mapa campo backend -> ID do element
    const mapa = {
        'cliente_id': 'selCliente', 'tipo_material': 'selTipoMaterial',
        'tipo_carga': 'selTipoCarga', 'endereco_origem_id': 'selOrigem',
        'endereco_destino_id': 'selDestino', 'peso': 'inpPeso',
        'valor_mercadoria': 'inpValorMerc', 'volumes': 'inpVolumes',
        'dimensao_c': 'inpDimC', 'dimensao_l': 'inpDimL', 'dimensao_a': 'inpDimA',
        'condicao_pagamento': 'selCondicaoPgto', 'prazo_dias': 'inpPrazoDias',
        'responsavel_frete': 'selResponsavelFrete',
        'percentual_remetente': 'inpPctRem', 'percentual_destinatario': 'inpPctDest',
        'observacoes': 'inpObs',
    };
    const elId = mapa[campo];
    const el = elId ? document.getElementById(elId) : null;
    if (!el) return;
    // Inserir check temporario
    const check = document.createElement('span');
    check.className = 'text-success ms-1 small';
    check.innerHTML = '<i class="fas fa-check"></i>';
    check.style.transition = 'opacity 0.5s';
    el.parentElement.appendChild(check);
    setTimeout(() => { check.style.opacity = '0'; }, 1500);
    setTimeout(() => { check.remove(); }, 2000);
}

function _setupAutoSave() {
    // Selects: salvar ao mudar
    const selectMap = {
        'selCliente': 'cliente_id',
        'selTipoMaterial': 'tipo_material',
        'selTipoCarga': 'tipo_carga',
        'selOrigem': 'endereco_origem_id',
        'selDestino': 'endereco_destino_id',
        'selCondicaoPgto': 'condicao_pagamento',
        'selResponsavelFrete': 'responsavel_frete',
    };
    Object.entries(selectMap).forEach(([elId, campo]) => {
        const el = document.getElementById(elId);
        if (!el || el.disabled) return;
        el.addEventListener('change', () => autoSave(campo, el.value));
    });

    // Inputs numericos e texto: salvar ao blur
    const inputMap = {
        'inpPeso': 'peso',
        'inpValorMerc': 'valor_mercadoria',
        'inpVolumes': 'volumes',
        'inpDimC': 'dimensao_c',
        'inpDimL': 'dimensao_l',
        'inpDimA': 'dimensao_a',
        'inpPrazoDias': 'prazo_dias',
        'inpPctRem': 'percentual_remetente',
        'inpPctDest': 'percentual_destinatario',
        'inpObs': 'observacoes',
    };
    Object.entries(inputMap).forEach(([elId, campo]) => {
        const el = document.getElementById(elId);
        if (!el || el.disabled) return;
        el.addEventListener('blur', () => autoSave(campo, el.value));
    });
}

/* ===== API helper ===== */
function apiCall(url, method, body) {
    return fetch(url, {
        method: method || 'POST',
        headers: {'Content-Type': 'application/json'},
        body: body ? JSON.stringify(body) : undefined
    }).then(r => r.json());
}

/* ===== Enderecos por cliente ===== */
const _origemAtual = CARVIA_DATA.origemAtual;
const _destinoAtual = CARVIA_DATA.destinoAtual;

let _enderecosCacheados = [];
function carregarEnderecos() {
    const clienteId = document.getElementById('selCliente').value;
    if (!clienteId) return;

    fetch(`/carvia/api/cotacoes/enderecos-cliente/${clienteId}`)
    .then(r => r.json())
    .then(data => {
        _enderecosCacheados = data.enderecos || [];
        const origens = _enderecosCacheados.filter(e => e.tipo === 'ORIGEM');
        const destinos = _enderecosCacheados.filter(e => e.tipo === 'DESTINO');

        const selO = document.getElementById('selOrigem');
        const selD = document.getElementById('selDestino');
        selO.innerHTML = '<option value="">Selecione...</option>';
        selD.innerHTML = '<option value="">Selecione...</option>';

        origens.forEach(e => {
            const sel = e.id === _origemAtual ? 'selected' : '';
            selO.innerHTML += `<option value="${e.id}" ${sel}>${e.label}</option>`;
        });
        destinos.forEach(e => {
            const sel = e.id === _destinoAtual ? 'selected' : '';
            selD.innerHTML += `<option value="${e.id}" ${sel}>${e.label}</option>`;
        });

        // Preencher endereco de entrega inline (Ajuste 8)
        const destId = parseInt(selD.value);
        if (destId) {
            const destEnd = _enderecosCacheados.find(e => e.id === destId);
            if (destEnd && typeof preencherEnderecoInline === 'function') preencherEnderecoInline(destEnd);
        }
    });
}
// Atualizar endereco inline ao trocar destino
document.getElementById('selDestino').addEventListener('change', function() {
    const destId = parseInt(this.value);
    const destEnd = _enderecosCacheados.find(e => e.id === destId);
    if (typeof preencherEnderecoInline === 'function') preencherEnderecoInline(destEnd || null);
});

/* ===== Show/hide por tipo material ===== */
document.getElementById('selTipoMaterial').addEventListener('change', function() {
    const isMoto = this.value === 'MOTO';
    document.getElementById('secaoCargaGeral').classList.toggle('d-none', isMoto);
    document.getElementById('secaoMoto').classList.toggle('d-none', !isMoto);
    if (isMoto && document.querySelectorAll('#tbodyMotos tr').length === 0) {
        adicionarLinhaMotos();
    }
});

/* ===== Tabela dinamica de motos (mesma logica do criar.html) ===== */
let motoRowIdx = 0;

function buildOpcoesModelo(selectedId) {
    let html = '<option value="">Selecione...</option>';
    modelosMoto.forEach(m => {
        const sel = m.id === selectedId ? 'selected' : '';
        html += `<option value="${m.id}" ${sel}>${m.nome}</option>`;
    });
    return html;
}

function adicionarLinhaMotos(dados) {
    const tbody = document.getElementById('tbodyMotos');
    const idx = motoRowIdx++;
    const d = dados || {};

    const modeloId = d.modelo_moto_id || '';
    const qtd = d.quantidade || 1;
    const valorUnit = d.valor_unitario != null ? d.valor_unitario : '';
    const pesoUnit = d.peso_cubado_unitario != null ? Number(d.peso_cubado_unitario).toFixed(3) : '';
    const valorTotal = d.valor_total != null ? Number(d.valor_total).toFixed(2) : '';
    const pesoTotal = d.peso_cubado_total != null ? Number(d.peso_cubado_total).toFixed(3) : '';

    const tr = document.createElement('tr');
    tr.id = `motoRow${idx}`;
    tr.innerHTML = `
        <td><select class="form-select form-select-sm" id="motoModelo${idx}" onchange="onModeloChange(${idx})">${buildOpcoesModelo(modeloId)}</select></td>
        <td><input type="number" class="form-control form-control-sm" id="motoQtd${idx}" value="${qtd}" min="1" oninput="recalcularMoto(${idx})"></td>
        <td><input type="number" class="form-control form-control-sm" id="motoValorUnit${idx}" step="0.01" min="0" value="${valorUnit}" oninput="recalcularMoto(${idx})"></td>
        <td><input type="text" class="form-control form-control-sm bg-light" id="motoPesoUnit${idx}" readonly tabindex="-1" value="${pesoUnit}"></td>
        <td><input type="text" class="form-control form-control-sm bg-light" id="motoValorTotal${idx}" readonly tabindex="-1" value="${valorTotal}"></td>
        <td><input type="text" class="form-control form-control-sm bg-light" id="motoPesoTotal${idx}" readonly tabindex="-1" value="${pesoTotal}"></td>
        <td><button type="button" class="btn btn-outline-danger btn-sm" onclick="removerLinhaMotos(${idx})" title="Remover"><i class="fas fa-trash"></i></button></td>
    `;
    tbody.appendChild(tr);
}

function onModeloChange(idx) {
    const modeloId = parseInt(document.getElementById(`motoModelo${idx}`).value);
    const modelo = modelosMoto.find(m => m.id === modeloId);
    document.getElementById(`motoPesoUnit${idx}`).value =
        modelo && modelo.peso_cubado ? modelo.peso_cubado.toFixed(3) : '';
    recalcularMoto(idx);
}

function recalcularMoto(idx) {
    const pesoUnit = parseFloat(document.getElementById(`motoPesoUnit${idx}`).value) || 0;
    const qtd = parseInt(document.getElementById(`motoQtd${idx}`).value) || 0;
    const valorUnit = parseFloat(document.getElementById(`motoValorUnit${idx}`).value) || 0;

    document.getElementById(`motoValorTotal${idx}`).value =
        valorUnit && qtd ? (valorUnit * qtd).toFixed(2) : '';
    document.getElementById(`motoPesoTotal${idx}`).value =
        pesoUnit && qtd ? (pesoUnit * qtd).toFixed(3) : '';

    recalcularTotaisMotos();
}

function recalcularTotaisMotos() {
    let totalValor = 0, totalPeso = 0;
    document.querySelectorAll('#tbodyMotos tr').forEach(tr => {
        totalValor += parseFloat(tr.querySelector('[id^="motoValorTotal"]')?.value) || 0;
        totalPeso += parseFloat(tr.querySelector('[id^="motoPesoTotal"]')?.value) || 0;
    });
    document.getElementById('totalValorMotos').textContent =
        `R$ ${totalValor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('totalPesoMotos').textContent =
        totalPeso.toLocaleString('pt-BR', {minimumFractionDigits: 3, maximumFractionDigits: 3});
}

function removerLinhaMotos(idx) {
    const row = document.getElementById(`motoRow${idx}`);
    if (row) row.remove();
    recalcularTotaisMotos();
    if (document.querySelectorAll('#tbodyMotos tr').length === 0) {
        adicionarLinhaMotos();
    }
}

/* ===== Inicializar motos existentes do servidor ===== */
const motosExistentes = CARVIA_DATA.motosExistentes;

function initMotos() {
    if (motosExistentes.length > 0) {
        motosExistentes.forEach(m => adicionarLinhaMotos(m));
    } else if (document.getElementById('selTipoMaterial').value === 'MOTO') {
        adicionarLinhaMotos();
    }
    recalcularTotaisMotos();
}

/* ===== Toggle Destino Manual ===== */
let _modoDestinoManual = false;

function toggleModoDestinoManual() {
    _modoDestinoManual = !_modoDestinoManual;
    const dropdown = document.getElementById('blocoDestinoDropdown');
    const manual = document.getElementById('blocoDestinoManual');
    const btn = document.getElementById('btnToggleDestinoManual');
    const endInline = document.getElementById('enderecoEntregaInline');

    if (_modoDestinoManual) {
        if (dropdown) dropdown.classList.add('d-none');
        if (manual) manual.classList.remove('d-none');
        if (endInline) endInline.classList.add('d-none');
        if (btn) btn.textContent = '\u2190 Selecionar da lista';
    } else {
        if (dropdown) dropdown.classList.remove('d-none');
        if (manual) manual.classList.add('d-none');
        if (btn) btn.textContent = 'Inserir manualmente';
        // Limpar campos manuais
        ['manDestUf','manDestCidade','manDestCep','manDestLogradouro','manDestNumero','manDestBairro','manDestRazao'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const fb = document.getElementById('manDestFeedback');
        if (fb) fb.style.display = 'none';
        // Re-mostrar endereco inline se ha destino selecionado no dropdown
        const destId = parseInt(document.getElementById('selDestino').value);
        if (destId && endInline) {
            const destEnd = _enderecosCacheados.find(e => e.id === destId);
            if (destEnd) preencherEnderecoInline(destEnd);
        }
    }
}

/* ===== SALVAR TUDO (dados + motos) ===== */
async function salvarTudo() {
    let destinoId = parseInt(document.getElementById('selDestino').value) || null;

    // Se modo manual: criar destino provisorio via API primeiro
    if (_modoDestinoManual) {
        const cidade = (document.getElementById('manDestCidade')?.value || '').trim();
        const uf = (document.getElementById('manDestUf')?.value || '').trim().toUpperCase();
        const clienteId = parseInt(document.getElementById('selCliente').value) || 0;

        if (!cidade || !uf) {
            alert('Cidade e UF do destino sao obrigatorios.');
            return;
        }
        if (!clienteId) {
            alert('Selecione o cliente.');
            return;
        }

        const fb = document.getElementById('manDestFeedback');
        if (fb) {
            fb.innerHTML = '<small class="text-muted"><i class="fas fa-spinner fa-spin"></i> Criando destino provisorio...</small>';
            fb.style.display = 'block';
        }

        try {
            const resp = await fetch('/carvia/api/cotacoes/destino-provisorio', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cliente_id: clienteId,
                    razao_social: document.getElementById('manDestRazao')?.value.trim() || null,
                    fisico: {
                        uf: uf,
                        cidade: cidade,
                        cep: document.getElementById('manDestCep')?.value.trim() || null,
                        logradouro: document.getElementById('manDestLogradouro')?.value.trim() || null,
                        numero: document.getElementById('manDestNumero')?.value.trim() || null,
                        bairro: document.getElementById('manDestBairro')?.value.trim() || null,
                    }
                })
            });
            const data = await resp.json();
            if (!data.sucesso) {
                if (fb) fb.innerHTML = '<small class="text-danger"><i class="fas fa-times"></i> ' + (data.erro || 'Erro') + '</small>';
                alert(data.erro || 'Erro ao criar destino provisorio.');
                return;
            }
            destinoId = data.endereco_id;
            if (fb) fb.innerHTML = '<small class="text-success"><i class="fas fa-check"></i> Destino provisorio criado.</small>';
        } catch (err) {
            alert('Erro de rede: ' + err.message);
            return;
        }
    }

    const tipoMat = document.getElementById('selTipoMaterial').value;

    const payload = {
        cliente_id: parseInt(document.getElementById('selCliente').value) || null,
        endereco_origem_id: parseInt(document.getElementById('selOrigem').value) || null,
        endereco_destino_id: destinoId,
        tipo_material: tipoMat,
        tipo_carga: document.getElementById('selTipoCarga').value,
        veiculo_id: parseInt(document.getElementById('selVeiculo')?.value) || null,
        peso: parseFloat(document.getElementById('inpPeso').value) || null,
        valor_mercadoria: parseFloat(document.getElementById('inpValorMerc').value) || null,
        volumes: parseInt(document.getElementById('inpVolumes').value) || null,
        dimensao_c: parseFloat(document.getElementById('inpDimC').value) || null,
        dimensao_l: parseFloat(document.getElementById('inpDimL').value) || null,
        dimensao_a: parseFloat(document.getElementById('inpDimA').value) || null,
        data_expedicao: document.getElementById('inpDataExp').value || null,
        data_agenda: document.getElementById('inpDataAg').value || null,
        observacoes: document.getElementById('inpObs').value || null,
        // Condicoes comerciais
        condicao_pagamento: document.getElementById('selCondicaoPgto').value || null,
        prazo_dias: parseInt(document.getElementById('inpPrazoDias').value) || null,
        responsavel_frete: document.getElementById('selResponsavelFrete').value || null,
        percentual_remetente: document.getElementById('inpPctRem').value !== '' ? parseFloat(document.getElementById('inpPctRem').value) : null,
        percentual_destinatario: document.getElementById('inpPctDest').value !== '' ? parseFloat(document.getElementById('inpPctDest').value) : null,
    };

    // Incluir endereco de entrega (override cotacao) se inline visivel
    const _endInline = document.getElementById('enderecoEntregaInline');
    if (_endInline && !_endInline.classList.contains('d-none')) {
        payload.entrega_uf = (document.getElementById('endUf').value || '').trim().toUpperCase();
        payload.entrega_cidade = (document.getElementById('endCidade').value || '').trim();
        payload.entrega_logradouro = (document.getElementById('endLogradouro').value || '').trim();
        payload.entrega_numero = (document.getElementById('endNumero').value || '').trim();
        payload.entrega_bairro = (document.getElementById('endBairro').value || '').trim();
        payload.entrega_cep = (document.getElementById('endCep').value || '').trim();
        payload.entrega_complemento = (document.getElementById('endComplemento').value || '').trim();
    }

    // Coletar motos da tabela
    if (tipoMat === 'MOTO') {
        const motos = [];
        document.querySelectorAll('#tbodyMotos tr').forEach(tr => {
            const modeloId = parseInt(tr.querySelector('[id^="motoModelo"]')?.value);
            const qtd = parseInt(tr.querySelector('[id^="motoQtd"]')?.value);
            const valorUnit = parseFloat(tr.querySelector('[id^="motoValorUnit"]')?.value) || null;
            if (modeloId && qtd > 0) {
                motos.push({modelo_moto_id: modeloId, quantidade: qtd, valor_unitario: valorUnit});
            }
        });
        if (motos.length === 0) {
            alert('Adicione pelo menos uma moto.');
            return;
        }
        payload.motos = motos;
    }

    // Criacao tardia APROVADO: enviar apenas campos permitidos
    let payloadFinal = payload;
    if (_criacaoTardia && _cotacaoStatus === 'APROVADO') {
        const permitidos = [
            'endereco_origem_id', 'endereco_destino_id', 'tipo_carga',
            'entrega_uf', 'entrega_cidade', 'entrega_logradouro',
            'entrega_numero', 'entrega_bairro', 'entrega_cep', 'entrega_complemento',
        ];
        payloadFinal = {};
        permitidos.forEach(k => { if (payload[k] !== undefined) payloadFinal[k] = payload[k]; });
    }

    apiCall(`/carvia/api/cotacoes/${cotacaoId}/salvar-completo`, 'PUT', payloadFinal).then(d => {
        if (d.sucesso) location.reload();
        else alert(d.erro || 'Erro ao salvar.');
    });
}

/* ===== Auto-save datas ===== */
function salvarData(campo, valor) {
    const payload = {};
    payload[campo] = valor || null;
    apiCall(`/carvia/api/cotacoes/${cotacaoId}`, 'PUT', payload).then(d => {
        if (!d.sucesso) alert(d.erro || 'Erro ao salvar data.');
    });
}

/* ===== Pricing ===== */
async function calcularPreco() {
    // Auto-salvar endereco de entrega na COTACAO antes de calcular
    const endInline = document.getElementById('enderecoEntregaInline');
    if (endInline && !endInline.classList.contains('d-none')) {
        const entrega = {
            entrega_uf: (document.getElementById('endUf').value || '').trim().toUpperCase(),
            entrega_cidade: (document.getElementById('endCidade').value || '').trim(),
            entrega_logradouro: (document.getElementById('endLogradouro').value || '').trim(),
            entrega_numero: (document.getElementById('endNumero').value || '').trim(),
            entrega_bairro: (document.getElementById('endBairro').value || '').trim(),
            entrega_cep: (document.getElementById('endCep').value || '').trim(),
            entrega_complemento: (document.getElementById('endComplemento').value || '').trim(),
        };
        const resp = await apiCall(`/carvia/api/cotacoes/${cotacaoId}`, 'PUT', entrega);
        if (!resp.sucesso) {
            alert(resp.erro || 'Erro ao salvar endereco de entrega.');
            return;
        }
    }
    apiCall(`/carvia/api/cotacoes/${cotacaoId}/calcular-preco`).then(d => {
        if (d.sucesso) location.reload(); else alert(d.erro);
    });
}

function aplicarDesconto() {
    const pct = parseFloat(document.getElementById('inpDescontoPct').value || 0);
    apiCall(`/carvia/api/cotacoes/${cotacaoId}/desconto`, 'POST', {percentual_desconto: pct}).then(d => {
        if (d.sucesso) location.reload(); else alert(d.erro);
    });
}

/* ===== Cotacao Manual ===== */
function abrirCotacaoManual() {
    const bloco = document.getElementById('blocoCotacaoManual');
    bloco.classList.toggle('d-none');
    if (!bloco.classList.contains('d-none')) {
        document.getElementById('inpValorManual').focus();
    }
}

function aplicarValorManual() {
    const valor = parseFloat(document.getElementById('inpValorManual').value || 0);
    if (valor <= 0) { alert('Informe um valor positivo.'); return; }
    if (!confirm('Definir R$ ' + valor.toFixed(2) + ' como valor manual?\nA cotacao ira para aprovacao do admin.')) return;
    apiCall(`/carvia/api/cotacoes/${cotacaoId}/valor-manual`, 'POST', {valor: valor}).then(d => {
        if (d.sucesso) location.reload(); else alert(d.erro);
    });
}

/* ===== Veiculo DIRETA ===== */
function toggleVeiculoBlock() {
    const tc = document.getElementById('selTipoCarga').value;
    const bloco = document.getElementById('blocoVeiculoDireta');
    if (bloco) {
        bloco.classList.toggle('d-none', tc !== 'DIRETA');
    }
}

async function sugerirVeiculo() {
    const tc = document.getElementById('selTipoCarga').value;
    if (tc !== 'DIRETA') return;

    const peso = parseFloat(document.getElementById('inpPeso')?.value) || 0;
    if (peso <= 0) return;

    const data = await apiCall('/carvia/api/cotacoes/sugerir-veiculo', 'POST', {peso: peso});
    if (data.veiculo_id) {
        const sel = document.getElementById('selVeiculo');
        if (sel) {
            sel.value = data.veiculo_id;
            const hint = document.getElementById('veiculoHint');
            if (hint) hint.textContent = 'Sugerido pelo peso';
            salvarVeiculo();
        }
    }
}

function salvarVeiculo() {
    const veiculoId = parseInt(document.getElementById('selVeiculo').value) || null;
    apiCall(`/carvia/api/cotacoes/${cotacaoId}`, 'PUT', {veiculo_id: veiculoId}).then(d => {
        if (!d.sucesso) alert(d.erro || 'Erro ao salvar veiculo.');
        const hint = document.getElementById('veiculoHint');
        if (hint) hint.textContent = '';
    });
}

/* ===== Status ===== */
function enviarCotacao() { if (!confirm('Gravar cotacao?')) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/enviar`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function aprovarCliente() { if (!confirm('Cliente aprovou?')) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/aprovar-cliente`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function recusarCliente() { if (!confirm('Cliente recusou?')) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/recusar-cliente`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function contraProposta() { const v = prompt('Valor da contra-proposta (R$):'); if (!v) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/contra-proposta`, 'POST', {novo_valor: parseFloat(v)}).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function cancelarCotacao() {
    const pedidosAtivos = CARVIA_DATA.pedidosAtivos;
    let msg = 'Cancelar cotacao?';
    if (pedidosAtivos > 0) msg += '\n\n' + pedidosAtivos + ' pedido(s) vinculado(s) tambem serao cancelados.';
    if (!confirm(msg)) return;
    apiCall(`/carvia/api/cotacoes/${cotacaoId}/cancelar`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); });
}
function reabrirCotacao() { if (!confirm('Reabrir cotacao? O status voltara para RASCUNHO.')) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/reabrir`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function adminAprovar() { if (!confirm('Aprovar desconto?')) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/admin-aprovar`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function adminRejeitar() { if (!confirm('Rejeitar desconto?')) return; apiCall(`/carvia/api/cotacoes/${cotacaoId}/admin-rejeitar`).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); }); }
function alterarExigirAprovacaoAdmin(val) {
    apiCall('/carvia/api/config/exigir-aprovacao-admin', 'PUT', { valor: val })
        .then(d => { if (!d.sucesso) { alert(d.erro || 'Erro.'); document.getElementById('toggleExigirAprovacao').checked = !val; } });
}

/* ===== Pedidos ===== */
function criarPedido() {
    apiCall(`/carvia/api/cotacoes/${cotacaoId}/pedidos`, 'POST', {
        filial: document.getElementById('selFilial').value,
        observacoes: document.getElementById('pedObs').value
    }).then(d => { if (d.sucesso) location.reload(); else alert(d.erro); });
}

function excluirPedido(pedidoId, num) {
    if (!confirm('Excluir pedido ' + num + '? Isso remove o pedido, seus itens e o EmbarqueItem vinculado.')) return;
    apiCall('/carvia/api/pedidos-carvia/' + pedidoId, 'DELETE').then(d => {
        if (d.sucesso) {
            if (d.aviso) alert('ATENCAO: ' + d.aviso);
            location.reload();
        } else {
            alert(d.erro || 'Erro ao excluir.');
        }
    });
}

let _pedidoIdNF = null;
function abrirModalAnexarNF(pedidoId, num) {
    _pedidoIdNF = pedidoId;
    document.getElementById('atalhoNFDesc').textContent = 'Pedido: ' + num;
    document.getElementById('inpNFAtalho').value = '';
    new bootstrap.Modal(document.getElementById('modalAnexarNFAtalho')).show();
}

function atalhoAnexarNF() {
    const nf = (document.getElementById('inpNFAtalho').value || '').trim();
    if (!nf || !_pedidoIdNF) return;
    apiCall('/carvia/api/pedidos-carvia/' + _pedidoIdNF + '/nf', 'PUT', {numero_nf: nf}).then(d => {
        if (d.sucesso) { setTimeout(() => location.reload(), 1000); }
        else alert(d.erro);
    });
}

/* ===== Importar NF — Modal 2 Etapas ===== */
let _nfArquivo = null;
function abrirModalImportarNF() {
    _nfArquivo = null;
    document.getElementById('nfStep1').classList.remove('d-none');
    document.getElementById('nfStep2').classList.add('d-none');
    document.getElementById('nfStepLabel').textContent = 'Etapa 1/2';
    document.getElementById('btnNFVoltar').style.display = 'none';
    document.getElementById('btnNFAvancar').textContent = 'Proximo';
    document.getElementById('btnNFAvancar').disabled = false;
    document.getElementById('inpArquivoNF').value = '';
    const fb1 = document.getElementById('nfStep1Feedback');
    if (fb1) fb1.style.display = 'none';
    const fb2 = document.getElementById('nfStep2Feedback');
    if (fb2) fb2.style.display = 'none';
    new bootstrap.Modal(document.getElementById('modalImportarNF')).show();
}
function nfStepAvancar() {
    const step1Visivel = !document.getElementById('nfStep1').classList.contains('d-none');
    if (step1Visivel) {
        const fileInput = document.getElementById('inpArquivoNF');
        if (!fileInput.files || !fileInput.files[0]) { alert('Selecione o arquivo da NF.'); return; }
        _nfArquivo = fileInput.files[0];
        // Carregar origens globais
        fetch('/carvia/api/cotacoes/origens-globais')
        .then(r => r.json()).then(data => {
            const sel = document.getElementById('selOrigemNF');
            sel.innerHTML = '<option value="">Selecione a origem...</option>';
            (data.origens || []).forEach(o => {
                sel.innerHTML += '<option value="' + o.id + '">' + o.label + '</option>';
            });
        });
        document.getElementById('nfStep1').classList.add('d-none');
        document.getElementById('nfStep2').classList.remove('d-none');
        document.getElementById('nfStepLabel').textContent = 'Etapa 2/2';
        document.getElementById('btnNFVoltar').style.display = '';
        document.getElementById('btnNFAvancar').textContent = 'Importar';
    } else {
        const origemId = document.getElementById('selOrigemNF').value;
        if (!origemId) { alert('Selecione a origem.'); return; }
        confirmarImportarNF(origemId);
    }
}
function nfStepVoltar() {
    document.getElementById('nfStep1').classList.remove('d-none');
    document.getElementById('nfStep2').classList.add('d-none');
    document.getElementById('nfStepLabel').textContent = 'Etapa 1/2';
    document.getElementById('btnNFVoltar').style.display = 'none';
    document.getElementById('btnNFAvancar').textContent = 'Proximo';
}
function confirmarImportarNF(origemId) {
    const formData = new FormData();
    formData.append('arquivo', _nfArquivo);
    formData.append('origem_id', origemId);
    document.getElementById('btnNFAvancar').disabled = true;
    fetch(`/carvia/api/cotacoes/${cotacaoId}/nf`, { method: 'POST', body: formData })
    .then(r => r.json())
    .then(d => {
        document.getElementById('btnNFAvancar').disabled = false;
        if (d.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalImportarNF')).hide();
            location.reload();
        } else {
            const fb = document.getElementById('nfStep2Feedback');
            fb.innerHTML = '<div class="alert alert-danger py-1 small">' + (d.erro || 'Erro') + '</div>';
            fb.style.display = 'block';
        }
    })
    .catch(err => {
        document.getElementById('btnNFAvancar').disabled = false;
        alert('Erro de rede: ' + err.message);
    });
}

/* ===== Filial Editavel ===== */
function editarFilial(pedidoId, filialAtual) {
    const nova = filialAtual === 'SP' ? 'RJ' : 'SP';
    if (!confirm('Trocar filial de ' + filialAtual + ' para ' + nova + '?')) return;
    apiCall('/carvia/api/pedidos-carvia/' + pedidoId + '/filial', 'PATCH', {filial: nova})
    .then(d => { if (d.sucesso) location.reload(); else alert(d.erro || 'Erro ao trocar filial.'); });
}

/* ===== Desanexar NF ===== */
function desanexarNFPedido(pedidoId, numPedido) {
    if (!confirm('Desanexar NF do pedido ' + numPedido + '? O pedido voltara para ABERTO.')) return;
    apiCall('/carvia/api/pedidos-carvia/' + pedidoId + '/desanexar-nf')
    .then(d => {
        if (d.sucesso) {
            if (d.aviso) alert('ATENCAO: ' + d.aviso);
            location.reload();
        } else {
            alert(d.erro || 'Erro ao desanexar.');
        }
    });
}

/* ===== Desconto Sincronizado ===== */
const _valorTabela = CARVIA_DATA.valorTabela;
function syncDescontoPct() {
    const pct = parseFloat(document.getElementById('inpDescontoPct').value) || 0;
    const valor = _valorTabela * (1 - pct / 100);
    document.getElementById('inpDescontoValor').value = valor.toFixed(2);
}
function syncDescontoValor() {
    const valor = parseFloat(document.getElementById('inpDescontoValor').value) || 0;
    if (_valorTabela > 0) {
        const pct = (1 - valor / _valorTabela) * 100;
        document.getElementById('inpDescontoPct').value = pct.toFixed(2);
    }
}

/* ===== Endereco Entrega Inline ===== */
let _enderecoDestinoId = null;
function preencherEnderecoInline(endereco) {
    if (!endereco) {
        const bloco = document.getElementById('enderecoEntregaInline');
        if (bloco) bloco.classList.add('d-none');
        return;
    }
    _enderecoDestinoId = endereco.id;

    // Prioridade: entrega da cotacao (override) > destino cadastrado
    const e = _entregaCotacao;
    const temOverride = e.uf || e.cidade;
    document.getElementById('endLogradouro').value = (temOverride ? e.logradouro : endereco.fisico_logradouro) || '';
    document.getElementById('endNumero').value = (temOverride ? e.numero : endereco.fisico_numero) || '';
    document.getElementById('endBairro').value = (temOverride ? e.bairro : endereco.fisico_bairro) || '';
    document.getElementById('endComplemento').value = (temOverride ? e.complemento : endereco.fisico_complemento) || '';
    document.getElementById('endCidade').value = (temOverride ? e.cidade : endereco.fisico_cidade) || '';
    document.getElementById('endUf').value = (temOverride ? e.uf : endereco.fisico_uf) || '';
    document.getElementById('endCep').value = (temOverride ? e.cep : endereco.fisico_cep) || '';

    const bloco = document.getElementById('enderecoEntregaInline');
    if (bloco) bloco.classList.remove('d-none');
}
function salvarEnderecoInline(silencioso) {
    if (!_enderecoDestinoId) return Promise.resolve(true);
    const data = {
        fisico_logradouro: document.getElementById('endLogradouro').value,
        fisico_numero: document.getElementById('endNumero').value,
        fisico_bairro: document.getElementById('endBairro').value,
        fisico_complemento: document.getElementById('endComplemento').value,
        fisico_cidade: document.getElementById('endCidade').value,
        fisico_uf: document.getElementById('endUf').value,
        fisico_cep: document.getElementById('endCep').value,
    };
    return apiCall('/carvia/api/cotacoes/enderecos/' + _enderecoDestinoId, 'PATCH', data)
    .then(d => {
        const fb = document.getElementById('enderecoFeedback');
        if (d.sucesso) {
            if (!silencioso) {
                fb.innerHTML = '<small class="text-success"><i class="fas fa-check"></i> Endereco salvo.</small>';
                fb.style.display = 'block';
                setTimeout(() => fb.style.display = 'none', 3000);
            }
            return true;
        } else {
            fb.innerHTML = '<small class="text-danger">' + (d.erro || 'Erro') + '</small>';
            fb.style.display = 'block';
            return false;
        }
    });
}

/* ===== Auto-save endereco cotacao com debounce 500ms ===== */
let _enderecoDebounce = null;
const _camposPricing = ['endUf', 'endCidade', 'endCep'];

function _zerarPricingUI() {
    // Zerar exibicao de pricing no card (sem reload)
    document.querySelectorAll('.card-header').forEach(h => {
        if (h.textContent.trim() === 'Pricing') {
            const body = h.nextElementSibling;
            if (body) {
                body.querySelectorAll('.fs-5, .fs-4').forEach(el => el.textContent = '-');
            }
        }
    });
}

function _salvarEnderecoCotacaoDebounce(campoAlterado) {
    clearTimeout(_enderecoDebounce);
    _enderecoDebounce = setTimeout(async () => {
        const entrega = {
            entrega_uf: (document.getElementById('endUf').value || '').trim().toUpperCase(),
            entrega_cidade: (document.getElementById('endCidade').value || '').trim(),
            entrega_logradouro: (document.getElementById('endLogradouro').value || '').trim(),
            entrega_numero: (document.getElementById('endNumero').value || '').trim(),
            entrega_bairro: (document.getElementById('endBairro').value || '').trim(),
            entrega_cep: (document.getElementById('endCep').value || '').trim(),
            entrega_complemento: (document.getElementById('endComplemento').value || '').trim(),
        };
        const resp = await apiCall(`/carvia/api/cotacoes/${cotacaoId}`, 'PUT', entrega);
        const fb = document.getElementById('enderecoFeedback');
        if (resp.sucesso) {
            fb.innerHTML = '<small class="text-success"><i class="fas fa-check"></i> Endereco salvo na cotacao.</small>';
            fb.style.display = 'block';
            setTimeout(() => fb.style.display = 'none', 3000);
        }
    }, 500);

    // Zerar pricing imediatamente se campo critico mudou
    if (_camposPricing.includes(campoAlterado)) {
        _zerarPricingUI();
    }
}

// Attach listeners em todos os campos inline
document.addEventListener('DOMContentLoaded', function() {
    ['endLogradouro','endNumero','endBairro','endComplemento','endCidade','endUf','endCep'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('input', () => _salvarEnderecoCotacaoDebounce(id));
        // Tambem capturar 'change' para auto-preenchimento do ViaCEP
        el.addEventListener('change', () => _salvarEnderecoCotacaoDebounce(id));
    });
});

/* ===== Condicoes Comerciais: toggle campos ===== */
function togglePrazoDias() {
    const v = document.getElementById('selCondicaoPgto').value;
    document.getElementById('blocoPrazoDias').style.display = v === 'PRAZO' ? '' : 'none';
    if (v !== 'PRAZO') document.getElementById('inpPrazoDias').value = '';
}

function togglePercentuais() {
    const v = document.getElementById('selResponsavelFrete').value;
    const remEl = document.getElementById('inpPctRem');
    const destEl = document.getElementById('inpPctDest');
    const showCustom = v === 'PERSONALIZADO';
    document.getElementById('blocoPercentualRem').style.display = showCustom ? '' : 'none';
    document.getElementById('blocoPercentualDest').style.display = showCustom ? '' : 'none';

    if (v === '100_REMETENTE') { remEl.value = '100'; destEl.value = '0'; }
    else if (v === '100_DESTINATARIO') { remEl.value = '0'; destEl.value = '100'; }
    else if (v === '50_50') { remEl.value = '50'; destEl.value = '50'; }
    else if (!v) { remEl.value = ''; destEl.value = ''; }
}

/* ===== Emissao CTe SSW ===== */
var _emissaoCaptcha = '';
var _emissaoComFatura = false;

function iniciarEmissaoCte(comFatura) {
    _emissaoComFatura = comFatura;
    const statusDiv = document.getElementById('emissaoCteStatus');
    const erroDiv = document.getElementById('emissaoCteErro');
    const resumoDiv = document.getElementById('emissaoCteResumo');
    const captchaDiv = document.getElementById('emissaoCteCaptcha');
    const captchaInput = document.getElementById('inpCaptchaCte');
    const successDiv = document.getElementById('emissaoCteSuccess');
    const btnConfirmar = document.getElementById('btnConfirmarEmissao');
    const vencBlock = document.getElementById('emissaoVencimentoBlock');

    // Reset
    erroDiv.classList.add('d-none');
    successDiv.classList.add('d-none');
    resumoDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm"></div> Validando premissas...</div>';
    captchaDiv.classList.add('d-none');
    captchaInput.value = '';
    btnConfirmar.disabled = true;
    vencBlock.style.display = comFatura ? '' : 'none';

    // Titulo
    document.getElementById('emissaoCteModalTitle').textContent =
        comFatura ? 'Emitir CTe + Fatura SSW' : 'Emitir CTe SSW';

    new bootstrap.Modal(document.getElementById('modalEmitirCteCotacao')).show();

    // Buscar preview
    fetch(`/carvia/api/cotacoes/${cotacaoId}/preview-emissao-cte`)
        .then(r => r.json().then(d => ({status: r.status, data: d})))
        .then(({status, data}) => {
            if (status !== 200 || !data.sucesso) {
                erroDiv.classList.remove('d-none');
                erroDiv.textContent = data.erro || 'Erro na validacao';
                if (data.itens_sem_nf) {
                    erroDiv.innerHTML += '<br><small>Itens: ' +
                        data.itens_sem_nf.map(i => `${i.pedido}: ${i.descricao} (${i.quantidade}x)`).join(', ') +
                        '</small>';
                }
                resumoDiv.innerHTML = '';
                return;
            }

            _emissaoCaptcha = data.captcha;

            // Montar resumo
            let html = '<table class="table table-sm small mb-2">';
            html += `<tr><td class="text-muted">Cotacao</td><td><strong>${data.cotacao.numero}</strong></td></tr>`;
            html += `<tr><td class="text-muted">Cliente</td><td>${data.cotacao.cliente}</td></tr>`;
            html += `<tr><td class="text-muted">Destino</td><td>${data.cotacao.destino}</td></tr>`;
            html += `<tr><td class="text-muted">Valor Frete</td><td><strong>R$ ${(data.cotacao.valor_frete||0).toFixed(2).replace('.', ',')}</strong></td></tr>`;
            html += `<tr><td class="text-muted">Placa</td><td>${data.placa || 'ARMAZEM'}</td></tr>`;
            if (data.cnpj_tomador) html += `<tr><td class="text-muted">CNPJ Tomador</td><td>${data.cnpj_tomador}</td></tr>`;
            html += '</table>';

            // NFs
            html += `<p class="fw-bold small mb-1">NFs para emissao (${data.nfs.length})</p><ul class="small mb-2">`;
            data.nfs.forEach(nf => {
                let badge = '';
                if (nf.em_andamento) badge = ' <span class="badge bg-warning">Em andamento</span>';
                html += `<li>NF ${nf.numero_nf} — Chave: <code>${nf.chave_acesso.substring(0,12)}...${nf.chave_acesso.substring(36)}</code>${badge}</li>`;
            });
            html += '</ul>';

            // Medidas moto
            if (data.medidas && data.medidas.length > 0) {
                html += '<p class="fw-bold small mb-1">Medidas Moto</p><ul class="small mb-2">';
                data.medidas.forEach(m => {
                    html += `<li>${m.modelo_nome}: ${m.comp_cm}x${m.larg_cm}x${m.alt_cm} cm, ${m.qtd}x</li>`;
                });
                html += '</ul>';
            }

            resumoDiv.innerHTML = html;

            // Mostrar captcha
            captchaDiv.classList.remove('d-none');
            document.getElementById('captchaNumero').textContent = _emissaoCaptcha;
        })
        .catch(err => {
            erroDiv.classList.remove('d-none');
            erroDiv.textContent = 'Erro de conexao: ' + err.message;
            resumoDiv.innerHTML = '';
        });
}

// Validar captcha no input.
// NOTA: o modal #modalEmitirCteCotacao e incluido no template APOS este script
// (bloco {% if cotacao.status == 'APROVADO' %}), entao #inpCaptchaCte ainda nao
// esta no DOM quando este arquivo executa. Anexamos o listener dentro do
// DOMContentLoaded ou via delegacao para garantir que roda quando o elemento
// realmente existe.
function _bindCaptchaListener() {
    const input = document.getElementById('inpCaptchaCte');
    const btn = document.getElementById('btnConfirmarEmissao');
    if (!input || !btn || input.dataset.captchaBound === '1') return;
    input.addEventListener('input', function() {
        btn.disabled = this.value.trim() !== _emissaoCaptcha;
    });
    input.dataset.captchaBound = '1';
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _bindCaptchaListener);
} else {
    _bindCaptchaListener();
}

function confirmarEmissaoCte() {
    const btn = document.getElementById('btnConfirmarEmissao');
    const erroDiv = document.getElementById('emissaoCteErro');
    const successDiv = document.getElementById('emissaoCteSuccess');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Emitindo...';

    const payload = {
        captcha_resposta: document.getElementById('inpCaptchaCte').value.trim(),
        captcha_esperado: _emissaoCaptcha,
        incluir_fatura: _emissaoComFatura,
        placa: 'ARMAZEM',
    };

    if (_emissaoComFatura) {
        payload.data_vencimento = document.getElementById('inpVencimentoCte')?.value || '';
    }

    fetch(`/carvia/api/cotacoes/${cotacaoId}/emitir-cte`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    })
    .then(r => r.json().then(d => ({status: r.status, data: d})))
    .then(({status, data}) => {
        if (status === 202 && data.sucesso) {
            const okEmissoes = (data.emissoes || []).filter(e => e.status !== 'ERRO' && e.emissao_id);
            const erros = (data.emissoes || []).filter(e => e.status === 'ERRO');

            // Fecha o modal e entrega tracking ao SswProgress — uma entrada
            // por NF/emissao. Cada toast mostra progresso independente
            // (LOGIN/PREENCHIMENTO/SEFAZ/...) e persiste entre reloads.
            const modalEl = document.getElementById('modalEmitirCteCotacao');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            const descBase = _emissaoComFatura
                ? 'SSW: login → preenchimento → SEFAZ → consulta 101 → importacao XML/DACTE → fatura 437.'
                : 'SSW: login → preenchimento → SEFAZ → consulta 101 → importacao XML/DACTE.';

            okEmissoes.forEach(function(em) {
                window.SswProgress && window.SswProgress.start({
                    label: 'Emitindo CTe SSW — NF ' + (em.numero_nf || em.nf_id),
                    descricao: descBase,
                    statusUrl: '/carvia/api/emissao-cte/' + em.emissao_id + '/status',
                    statusType: 'emissao_cte',
                    // Nao recarrega automaticamente na cotacao para nao
                    // interromper as outras NFs em progresso. Usuario
                    // recarrega manualmente quando todas terminarem.
                    reloadOnDone: false,
                });
            });

            if (erros.length > 0) {
                alert(erros.length + ' NF(s) nao puderam ser enfileiradas:\n'
                    + erros.map(e => '• NF ' + (e.numero_nf || e.nf_id) + ': ' + e.erro).join('\n'));
            }

            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-bolt"></i> Confirmar Emissao';
        } else {
            erroDiv.classList.remove('d-none');
            erroDiv.textContent = data.erro || 'Erro ao emitir';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-bolt"></i> Confirmar Emissao';
        }
    })
    .catch(err => {
        erroDiv.classList.remove('d-none');
        erroDiv.textContent = 'Erro: ' + err.message;
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-bolt"></i> Confirmar Emissao';
    });
}

/* ===== Init ===== */
document.addEventListener('DOMContentLoaded', function() {
    carregarEnderecos();
    initMotos();
});
