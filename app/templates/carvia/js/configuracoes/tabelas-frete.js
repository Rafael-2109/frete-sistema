/* ===== Utils ===== */
function parseBR(value) {
    if (!value) return null;
    return parseFloat(String(value).replace(/\./g, '').replace(',', '.'));
}

function formatBR(val) {
    if (val == null) return '';
    return Number(val).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 4});
}

function csrfHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
    };
}

function apiCall(url, opts) {
    return fetch(url, opts)
        .then(function(r) { return r.json().then(function(d) { return {ok: r.ok, data: d}; }); });
}

/* ===== Estado do modal ===== */
var _modoEditar = false;
var _combo = {};     // {nome_tabela, uf_origem, uf_destino, tipo_carga}
var _veiculosCache = null;
var _categoriasCache = null;

/* ===== Abrir Nova Tabela ===== */
function abrirNovaTabela() {
    _modoEditar = false;
    _combo = {};

    document.getElementById('modalTituloTexto').textContent = 'Nova Tabela de Frete';
    document.getElementById('secaoIdentificacao').classList.remove('d-none');
    document.getElementById('secaoInfoReadonly').classList.add('d-none');

    // Reset campos identificacao
    document.getElementById('mdUfOrigem').value = '';
    document.getElementById('mdUfDestino').value = '';
    document.getElementById('mdNomeTabela').innerHTML = '<option value="">Selecione UFs primeiro</option>';
    document.getElementById('mdTipoCarga').value = 'FRACIONADA';
    document.getElementById('mdGrupoCliente').value = '';

    // Habilitar selects
    ['mdUfOrigem', 'mdUfDestino', 'mdTipoCarga'].forEach(function(id) {
        document.getElementById(id).disabled = false;
    });

    limparFormPrecos();
    toggleTipoCarga();
    carregarDadosFixos();

    new bootstrap.Modal(document.getElementById('modalTabela')).show();
}

/* ===== Abrir Editar ===== */
function abrirEditarTabela(nome, origem, destino, tipo) {
    _modoEditar = true;
    _combo = {nome_tabela: nome, uf_origem: origem, uf_destino: destino, tipo_carga: tipo};

    document.getElementById('modalTituloTexto').textContent = 'Editar Tabela de Frete';
    document.getElementById('secaoIdentificacao').classList.add('d-none');
    document.getElementById('secaoInfoReadonly').classList.remove('d-none');

    // Preencher info readonly
    document.getElementById('infoNome').textContent = nome;
    document.getElementById('infoRota').textContent = origem + ' \u2192 ' + destino;
    document.getElementById('infoTipo').innerHTML = '<span class="badge ' +
        (tipo === 'DIRETA' ? 'bg-primary' : 'bg-info') + '">' + tipo + '</span>';
    document.getElementById('mdGrupoClienteEdit').value = '';

    // Configurar tipo_carga (fixa)
    if (tipo === 'DIRETA') {
        document.getElementById('secaoFracionada').classList.add('d-none');
        document.getElementById('secaoDireta').classList.remove('d-none');
    } else {
        document.getElementById('secaoFracionada').classList.remove('d-none');
        document.getElementById('secaoDireta').classList.add('d-none');
    }

    limparFormPrecos();
    carregarDadosFixos(function() { carregarCombinacao(); });

    new bootstrap.Modal(document.getElementById('modalTabela')).show();
}

/* ===== Toggle tipo carga (Nova Tabela) ===== */
function toggleTipoCarga() {
    var tipo = document.getElementById('mdTipoCarga').value;
    document.getElementById('secaoFracionada').classList.toggle('d-none', tipo === 'DIRETA');
    document.getElementById('secaoDireta').classList.toggle('d-none', tipo !== 'DIRETA');
}

/* ===== Toggle nome tabela manual ===== */
var _nomeManual = false;
function toggleNomeTabelaManual() {
    _nomeManual = !_nomeManual;
    document.getElementById('mdNomeTabela').classList.toggle('d-none', _nomeManual);
    document.getElementById('mdNomeTabelaManual').classList.toggle('d-none', !_nomeManual);
    if (_nomeManual) document.getElementById('mdNomeTabelaManual').focus();
}

/* ===== Carregar nomes tabela de CarviaCidadeAtendida ===== */
function carregarNomesTabela() {
    var origem = document.getElementById('mdUfOrigem').value;
    var destino = document.getElementById('mdUfDestino').value;
    var sel = document.getElementById('mdNomeTabela');

    if (!origem || !destino) {
        sel.innerHTML = '<option value="">Selecione ambas UFs</option>';
        return;
    }

    fetch(CARVIA_URLS.nomesTabela + '?uf_origem=' + origem + '&uf_destino=' + destino)
    .then(function(r) { return r.json(); })
    .then(function(data) {
        var nomes = data.nomes || [];
        if (nomes.length === 0) {
            sel.innerHTML = '<option value="">Nenhuma tabela encontrada</option>';
        } else {
            var html = '<option value="">Selecione...</option>';
            nomes.forEach(function(n) { html += '<option value="' + n + '">' + n + '</option>'; });
            sel.innerHTML = html;
        }
    });
}

/* ===== Carregar dados fixos (veiculos + categorias) ===== */
function carregarDadosFixos(callback) {
    var pending = 2;
    function done() { if (--pending === 0 && callback) callback(); }

    if (_veiculosCache) { renderizarVeiculos(); done(); }
    else {
        fetch(CARVIA_URLS.veiculosLista).then(function(r) { return r.json(); })
        .then(function(data) {
            _veiculosCache = data.veiculos || [];
            renderizarVeiculos();
            done();
        }).catch(done);
    }

    if (_categoriasCache) { renderizarCategoriasMoto(); done(); }
    else {
        fetch(CARVIA_URLS.categoriasMotoLista).then(function(r) { return r.json(); })
        .then(function(data) {
            _categoriasCache = data.categorias || [];
            renderizarCategoriasMoto();
            done();
        }).catch(done);
    }
}

function renderizarVeiculos(dados) {
    var tbody = document.getElementById('tbodyVeiculos');
    if (!_veiculosCache || _veiculosCache.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-muted small text-center">Nenhum veiculo cadastrado.</td></tr>';
        return;
    }
    var html = '';
    _veiculosCache.forEach(function(v) {
        var d = (dados || []).find(function(x) { return x.nome === v.nome; });
        var val = d && d.frete_minimo_valor != null ? formatBR(d.frete_minimo_valor) : '';
        var checked = d && d.icms_incluso ? 'checked' : '';
        html += '<tr>' +
            '<td>' + v.nome + '</td>' +
            '<td><input type="text" class="form-control form-control-sm" data-veiculo="' + v.nome + '"' +
            ' inputmode="decimal" placeholder="0,00" value="' + val + '"></td>' +
            '<td class="text-center"><input type="checkbox" class="form-check-input" data-veiculo-icms="' + v.nome + '" ' + checked + '></td>' +
            '</tr>';
    });
    tbody.innerHTML = html;
}

function renderizarCategoriasMoto(dados) {
    var tbody = document.getElementById('tbodyMotoPrecos');
    if (!_categoriasCache || _categoriasCache.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-muted small text-center">Nenhuma categoria cadastrada.</td></tr>';
        return;
    }
    var html = '';
    _categoriasCache.forEach(function(c) {
        var p = (dados || []).find(function(x) { return x.categoria_id === c.id; });
        var val = p && p.valor_unitario != null ? formatBR(p.valor_unitario) : '';
        html += '<tr>' +
            '<td>' + c.nome + '</td>' +
            '<td><input type="text" class="form-control form-control-sm" data-cat-id="' + c.id + '"' +
            ' inputmode="decimal" placeholder="0,00" value="' + val + '"></td>' +
            '</tr>';
    });
    tbody.innerHTML = html;
}

/* ===== Limpar form de precos ===== */
function limparFormPrecos() {
    var fpIds = ['fpValorKg','fpMinPeso','fpPercentualValor','fpMinValor',
                 'fpGris','fpGrisMin','fpAdv','fpAdvMin','fpRca','fpPedagio',
                 'fpDespacho','fpCte','fpTas','fpIcmsProprio'];
    fpIds.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.value = '';
    });
    document.getElementById('fpIcmsIncluso').checked = false;
    renderizarVeiculos();
    renderizarCategoriasMoto();
}

/* ===== Carregar combinacao existente ===== */
function carregarCombinacao() {
    var grupoSel = _modoEditar
        ? document.getElementById('mdGrupoClienteEdit')
        : document.getElementById('mdGrupoCliente');
    var grupoId = grupoSel.value;

    var nome, origem, destino, tipo;
    if (_modoEditar) {
        nome = _combo.nome_tabela;
        origem = _combo.uf_origem;
        destino = _combo.uf_destino;
        tipo = _combo.tipo_carga;
    } else {
        origem = document.getElementById('mdUfOrigem').value;
        destino = document.getElementById('mdUfDestino').value;
        var selNome = document.getElementById('mdNomeTabela');
        var manualNome = document.getElementById('mdNomeTabelaManual');
        nome = _nomeManual ? manualNome.value.trim().toUpperCase() : selNome.value;
        tipo = document.getElementById('mdTipoCarga').value;
    }

    if (!nome || !origem || !destino || !tipo) return;

    document.getElementById('secaoPrecoLoading').classList.remove('d-none');

    var url = CARVIA_URLS.combinacao + '?nome_tabela=' +
        encodeURIComponent(nome) + '&uf_origem=' + origem + '&uf_destino=' + destino +
        '&tipo_carga=' + tipo;
    if (grupoId) url += '&grupo_cliente_id=' + grupoId;

    fetch(url)
    .then(function(r) { return r.json(); })
    .then(function(data) {
        document.getElementById('secaoPrecoLoading').classList.add('d-none');

        if (tipo === 'FRACIONADA') {
            preencherFretePeso(data.frete_peso);
            renderizarCategoriasMoto(data.frete_moto || []);
        } else {
            renderizarVeiculos(data.veiculos || []);
        }
    })
    .catch(function(err) {
        document.getElementById('secaoPrecoLoading').classList.add('d-none');
        console.error(err);
    });
}

/* ===== Preencher campos Frete Peso ===== */
var _fpMap = {
    valor_kg: 'fpValorKg', frete_minimo_peso: 'fpMinPeso',
    percentual_valor: 'fpPercentualValor', frete_minimo_valor: 'fpMinValor',
    percentual_gris: 'fpGris', gris_minimo: 'fpGrisMin',
    percentual_adv: 'fpAdv', adv_minimo: 'fpAdvMin',
    percentual_rca: 'fpRca', pedagio_por_100kg: 'fpPedagio',
    valor_despacho: 'fpDespacho', valor_cte: 'fpCte',
    valor_tas: 'fpTas', icms_proprio: 'fpIcmsProprio',
};

function preencherFretePeso(fp) {
    Object.keys(_fpMap).forEach(function(key) {
        var el = document.getElementById(_fpMap[key]);
        if (el) el.value = fp && fp[key] != null ? formatBR(fp[key]) : '';
    });
    document.getElementById('fpIcmsIncluso').checked = fp && fp.icms_incluso || false;
}

/* ===== Salvar ===== */
function salvarCombinacao() {
    var grupoSel = _modoEditar
        ? document.getElementById('mdGrupoClienteEdit')
        : document.getElementById('mdGrupoCliente');
    var grupoId = grupoSel.value ? parseInt(grupoSel.value) : null;

    var nome, origem, destino, tipo;
    if (_modoEditar) {
        nome = _combo.nome_tabela;
        origem = _combo.uf_origem;
        destino = _combo.uf_destino;
        tipo = _combo.tipo_carga;
    } else {
        origem = document.getElementById('mdUfOrigem').value;
        destino = document.getElementById('mdUfDestino').value;
        var selNome = document.getElementById('mdNomeTabela');
        var manualNome = document.getElementById('mdNomeTabelaManual');
        nome = _nomeManual ? manualNome.value.trim().toUpperCase() : selNome.value;
        tipo = document.getElementById('mdTipoCarga').value;
    }

    if (!nome || !origem || !destino || !tipo) {
        alert('Preencha todos os campos obrigatorios.');
        return;
    }

    var payload = {
        nome_tabela: nome, uf_origem: origem, uf_destino: destino,
        tipo_carga: tipo, grupo_cliente_id: grupoId,
    };

    if (tipo === 'FRACIONADA') {
        var fp = {};
        var temAlgumValor = false;
        Object.keys(_fpMap).forEach(function(key) {
            var v = parseBR(document.getElementById(_fpMap[key]).value);
            fp[key] = v;
            if (v != null && v !== 0) temAlgumValor = true;
        });
        fp.icms_incluso = document.getElementById('fpIcmsIncluso').checked;
        payload.frete_peso = fp;

        var moto = [];
        document.querySelectorAll('#tbodyMotoPrecos input[data-cat-id]').forEach(function(inp) {
            var val = parseBR(inp.value);
            if (val !== null && val !== undefined) {
                moto.push({categoria_moto_id: parseInt(inp.dataset.catId), valor_unitario: val});
                temAlgumValor = true;
            }
        });
        payload.frete_moto = moto;

        if (!temAlgumValor) {
            alert('Preencha pelo menos um campo de preco (Frete Peso ou Frete por Moto).');
            return;
        }
    } else {
        var veiculos = [];
        var temAlgumVeiculo = false;
        document.querySelectorAll('#tbodyVeiculos input[data-veiculo]').forEach(function(inp) {
            var nome_v = inp.dataset.veiculo;
            var icmsEl = document.querySelector('input[data-veiculo-icms="' + nome_v + '"]');
            var val = parseBR(inp.value);
            veiculos.push({
                nome: nome_v,
                frete_minimo_valor: val,
                icms_incluso: icmsEl ? icmsEl.checked : false,
            });
            if (val) temAlgumVeiculo = true;
        });
        payload.veiculos = veiculos;

        if (!temAlgumVeiculo) {
            alert('Preencha o frete minimo de pelo menos um veiculo.');
            return;
        }
    }

    document.getElementById('btnSalvar').disabled = true;

    apiCall(CARVIA_URLS.salvarCombinacao, {
        method: 'POST', headers: csrfHeaders(), body: JSON.stringify(payload)
    })
    .then(function(res) {
        document.getElementById('btnSalvar').disabled = false;
        if (!res.ok) { alert(res.data.erro || 'Erro ao salvar.'); return; }
        bootstrap.Modal.getInstance(document.getElementById('modalTabela')).hide();
        location.reload();
    })
    .catch(function(err) {
        document.getElementById('btnSalvar').disabled = false;
        alert(err.message);
    });
}

/* ===== Desativar combinacao ===== */
function desativarCombinacao(nome, origem, destino, tipo) {
    if (!confirm('Desativar TODOS os registros de "' + nome + '" (' + origem + '\u2192' + destino + ' ' + tipo + ')?')) return;

    apiCall(CARVIA_URLS.desativarCombinacao, {
        method: 'POST', headers: csrfHeaders(),
        body: JSON.stringify({nome_tabela: nome, uf_origem: origem, uf_destino: destino, tipo_carga: tipo})
    })
    .then(function(res) {
        if (!res.ok) { alert(res.data.erro || 'Erro'); return; }
        location.reload();
    })
    .catch(function(err) { alert(err.message); });
}
