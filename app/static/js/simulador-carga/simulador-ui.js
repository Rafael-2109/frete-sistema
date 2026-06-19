/**
 * SimuladorUI — Controlador da interface do Simulador 3D de Carga.
 *
 * Orquestra:
 * - Sidebar: selecao de veiculo, linhas de modelo de moto, botoes +/-
 * - BinPacker: calcula empacotamento
 * - CargaRenderer: renderiza cena Three.js
 * - Stats: atualiza metricas na sidebar
 *
 * Modo unico: livre — carrega catalogo via API e o usuario monta a carga.
 * Pode abrir PRE-PREENCHIDO via <script id="simulador-prefill-data"> (motos/NFs/
 * pallets de um embarque ou de uma rota do mapa), permanecendo editavel.
 */
;(function () {
  'use strict';

  var DEBOUNCE_MS = 200;
  var PALETTE_HEX = [
    '#4a90d9', '#e8854c', '#67c26a', '#b06fc4',
    '#e8cc4c', '#4cc4c4', '#e85c6e', '#8a9bb0',
  ];

  var state = {
    veiculos: [],
    modelosMoto: [],
    veiculoSelecionado: null,
    linhasMoto: [], // [{modeloId, qty}]
    renderer: null,
    colorMap: {}, // {modelo_id: '#hex'}
    debounceTimer: null,
    packToken: 0, // descarta resultado de otimizacao obsoleto (input mudou)
    nfsPendentes: null, // cache das NFs CarVia nao entregues (lazy)
    nfsAdicionadas: {}, // {chave: [{modelo_id, quantidade}]} — motos puxadas por unidade (NF/pedido/cotacao) p/ remover
    pallets: [], // pallets de conservas Nacom (Camada 1) empacotados junto das motos
    loteSeparacao: null, // separacao_lote_id ativo
  };

  function init() {
    var container = document.getElementById('simulador-canvas');
    if (!container) return;
    // Modo unico: simulador livre. O embarque alimenta o livre via prefill
    // (rota /simulador-carga?embarque_id=<id>), nao ha mais tela dedicada.
    initLivreMode(container);
  }

  // ========== Modo Livre ==========

  function initLivreMode(container) {
    // Criar renderer
    var isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    state.renderer = new CargaRenderer(container, isDark ? 'dark' : 'light');

    // Carregar catalogo
    fetch('/carvia/api/simulador-carga/catalogo')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.veiculos = data.veiculos || [];
        state.modelosMoto = data.modelos_moto || [];
        populateVeiculoSelect();
        populateModeloOptions();
        bindEvents();
        bindPackControls(scheduleRecalc);
        setupNfSelector();
        setupSalvarDimensoes();
        setupPalletControls();

        // Prefill (rota do mapa) tem prioridade na selecao do veiculo + motos
        var aplicouPrefill = applyPrefill();

        // Selecionar primeiro veiculo com dimensoes (se nao veio do prefill)
        var selectEl = document.getElementById('simulador-veiculo');
        if (!aplicouPrefill && selectEl && selectEl.value) {
          onVeiculoChange();
        }
      })
      .catch(function (err) {
        console.error('Erro ao carregar catalogo:', err);
      });
  }

  function populateVeiculoSelect() {
    var select = document.getElementById('simulador-veiculo');
    if (!select) return;

    select.innerHTML = '<option value="">Selecione um veículo...</option>';
    for (var i = 0; i < state.veiculos.length; i++) {
      var v = state.veiculos[i];
      if (!v.tem_dimensoes_bau) continue;

      var opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = v.nome + ' — ' + formatNumber(v.peso_maximo) + 'kg' +
        ' (' + Math.round(v.comprimento_bau) + '×' + Math.round(v.largura_bau) +
        '×' + Math.round(v.altura_bau) + 'cm)';
      opt.dataset.comprimento = v.comprimento_bau;
      opt.dataset.largura = v.largura_bau;
      opt.dataset.altura = v.altura_bau;
      opt.dataset.pesoMax = v.peso_maximo;
      opt.dataset.nome = v.nome;
      select.appendChild(opt);
    }

    // Info de veiculos sem dimensoes
    var semDims = state.veiculos.filter(function (v) { return !v.tem_dimensoes_bau; });
    if (semDims.length > 0) {
      var info = document.getElementById('simulador-veiculos-sem-dims');
      if (info) {
        info.textContent = semDims.length + ' veículo(s) sem dimensões do baú cadastradas.';
        info.style.display = 'block';
      }
    }
  }

  function populateModeloOptions() {
    // Armazena lista para usar nos selects de modelos
    // Os selects sao criados dinamicamente ao clicar "Adicionar Modelo"
  }

  function createMotoModelSelect() {
    var select = document.createElement('select');
    select.className = 'form-select form-select-sm simulador-modelo-select';
    select.innerHTML = '<option value="">Selecione modelo...</option>';
    for (var i = 0; i < state.modelosMoto.length; i++) {
      var m = state.modelosMoto[i];
      var opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.nome;
      opt.dataset.comprimento = m.comprimento;
      opt.dataset.largura = m.largura;
      opt.dataset.altura = m.altura;
      opt.dataset.peso = m.peso_medio || 0;
      select.appendChild(opt);
    }
    return select;
  }

  function addMotoRow(modeloId, qty) {
    var container = document.getElementById('simulador-motos-container');
    if (!container) return;

    var idx = container.children.length;
    var colorHex = PALETTE_HEX[idx % PALETTE_HEX.length];

    var row = document.createElement('div');
    row.className = 'simulador-moto-row';
    row.style.borderLeftColor = colorHex;
    row.dataset.color = colorHex;

    // Coluna com o modelo (select) por cima e as medidas embaixo
    var infoDiv = document.createElement('div');
    infoDiv.className = 'simulador-moto-info';

    var selectDiv = document.createElement('div');
    selectDiv.className = 'simulador-moto-select-wrap';
    var select = createMotoModelSelect();
    if (modeloId) select.value = modeloId;
    select.addEventListener('change', function () { scheduleRecalc(); });
    selectDiv.appendChild(select);

    var dimsSpan = document.createElement('div');
    dimsSpan.className = 'simulador-moto-dims';
    dimsSpan.textContent = getDimsText(select);

    infoDiv.appendChild(selectDiv);
    infoDiv.appendChild(dimsSpan);

    var qtyDiv = document.createElement('div');
    qtyDiv.className = 'simulador-moto-qty';

    var btnMinus = document.createElement('button');
    btnMinus.type = 'button';
    btnMinus.className = 'btn btn-sm btn-outline-secondary simulador-qty-btn';
    btnMinus.textContent = '-';

    var qtyInput = document.createElement('input');
    qtyInput.type = 'number';
    qtyInput.className = 'form-control form-control-sm simulador-qty-input';
    qtyInput.min = '0';
    qtyInput.max = '200';
    qtyInput.value = qty || 1;

    var btnPlus = document.createElement('button');
    btnPlus.type = 'button';
    btnPlus.className = 'btn btn-sm btn-outline-secondary simulador-qty-btn';
    btnPlus.textContent = '+';

    var btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'btn btn-sm btn-outline-danger simulador-remove-btn';
    btnRemove.innerHTML = '<i class="fas fa-times"></i>';

    // Events
    btnMinus.addEventListener('click', function () {
      var val = parseInt(qtyInput.value) || 0;
      if (val > 0) { qtyInput.value = val - 1; scheduleRecalc(); }
    });
    btnPlus.addEventListener('click', function () {
      var val = parseInt(qtyInput.value) || 0;
      if (val < 200) { qtyInput.value = val + 1; scheduleRecalc(); }
    });
    qtyInput.addEventListener('input', function () { scheduleRecalc(); });
    btnRemove.addEventListener('click', function () {
      row.remove();
      updateRowColors();
      scheduleRecalc();
    });
    select.addEventListener('change', function () {
      dimsSpan.textContent = getDimsText(select);
    });

    qtyDiv.appendChild(btnMinus);
    qtyDiv.appendChild(qtyInput);
    qtyDiv.appendChild(btnPlus);

    row.appendChild(infoDiv);
    row.appendChild(qtyDiv);
    row.appendChild(btnRemove);

    container.appendChild(row);

    // Update dims text
    dimsSpan.textContent = getDimsText(select);

    scheduleRecalc();
  }

  function getDimsText(select) {
    var opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) return '';
    return opt.dataset.comprimento + '×' + opt.dataset.largura + '×' + opt.dataset.altura + 'cm' +
      (opt.dataset.peso && parseFloat(opt.dataset.peso) > 0 ? ' | ' + opt.dataset.peso + 'kg' : '');
  }

  function updateRowColors() {
    var rows = document.querySelectorAll('.simulador-moto-row');
    for (var i = 0; i < rows.length; i++) {
      var colorHex = PALETTE_HEX[i % PALETTE_HEX.length];
      rows[i].style.borderLeftColor = colorHex;
      rows[i].dataset.color = colorHex;
    }
  }

  function bindEvents() {
    // Veiculo select
    var veiculoSelect = document.getElementById('simulador-veiculo');
    if (veiculoSelect) {
      veiculoSelect.addEventListener('change', onVeiculoChange);
    }

    // Adicionar modelo
    var addBtn = document.getElementById('simulador-add-moto');
    if (addBtn) {
      addBtn.addEventListener('click', function () {
        addMotoRow(null, 1);
      });
    }

    // Vistas
    document.querySelectorAll('.simulador-view-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var preset = this.dataset.view;
        document.querySelectorAll('.simulador-view-btn').forEach(function (b) {
          b.classList.remove('active');
        });
        this.classList.add('active');
        if (state.renderer && state.veiculoSelecionado) {
          state.renderer.setView(preset, state.veiculoSelecionado);
        }
      });
    });

    // Override de dimensoes
    ['simulador-override-comp', 'simulador-override-larg', 'simulador-override-alt'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('input', function () { scheduleRecalc(); });
    });
  }

  function onVeiculoChange() {
    var select = document.getElementById('simulador-veiculo');
    if (!select || !select.value) {
      state.veiculoSelecionado = null;
      updateDimsDisplay(null);
      return;
    }
    var opt = select.options[select.selectedIndex];
    state.veiculoSelecionado = {
      id: parseInt(select.value, 10),
      w: parseFloat(opt.dataset.comprimento),
      d: parseFloat(opt.dataset.largura),
      h: parseFloat(opt.dataset.altura),
      pesoMax: parseFloat(opt.dataset.pesoMax),
      nome: opt.dataset.nome || opt.textContent.split('—')[0].trim(),
    };

    updateDimsDisplay(state.veiculoSelecionado);
    setOverrideValues(state.veiculoSelecionado);
    scheduleRecalc();
  }

  function updateDimsDisplay(bay) {
    var el = document.getElementById('simulador-dims-display');
    if (!el) return;
    if (!bay) {
      el.style.display = 'none';
      return;
    }
    el.style.display = 'block';
  }

  function setOverrideValues(bay) {
    var compEl = document.getElementById('simulador-override-comp');
    var largEl = document.getElementById('simulador-override-larg');
    var altEl = document.getElementById('simulador-override-alt');
    if (compEl) compEl.value = Math.round(bay.w);
    if (largEl) largEl.value = Math.round(bay.d);
    if (altEl) altEl.value = Math.round(bay.h);
  }

  // ========== NF nao entregue + prefill (modo livre) ==========

  /** Adiciona qty ao modelo se ja houver linha dele; senao cria nova linha. */
  function addOrIncrementMoto(modeloId, qty) {
    if (!modeloId || qty <= 0) return;
    var rows = document.querySelectorAll('.simulador-moto-row');
    for (var i = 0; i < rows.length; i++) {
      var sel = rows[i].querySelector('.simulador-modelo-select');
      if (sel && parseInt(sel.value) === parseInt(modeloId)) {
        var qi = rows[i].querySelector('.simulador-qty-input');
        qi.value = (parseInt(qi.value) || 0) + qty;
        scheduleRecalc();
        return;
      }
    }
    addMotoRow(modeloId, qty);
  }

  /** Pre-preenche veiculo + motos a partir da rota do mapa (modo livre editavel).
      Retorna true se selecionou um veiculo (p/ nao sobrescrever com o 1o do select). */
  function applyPrefill() {
    var el = document.getElementById('simulador-prefill-data');
    if (!el) return false;
    var data;
    try { data = JSON.parse(el.textContent); } catch (e) { return false; }

    var selecionouVeiculo = false;
    if (data.veiculo && data.veiculo.id) {
      var select = document.getElementById('simulador-veiculo');
      if (select) {
        select.value = String(data.veiculo.id);
        if (select.value === String(data.veiculo.id)) {
          onVeiculoChange();
          selecionouVeiculo = true;
        }
      }
    }

    // Pallets de conservas Nacom (carga mista do embarque) -> entram no
    // empacotamento 3D junto das motos. O recalc (debounced) abaixo le state.pallets.
    if (data.pallets && data.pallets.length) {
      state.pallets = data.pallets;
    }

    // TODAS as motos (NF + itens sem NF) -> linhas. `data.motos` ja e o total
    // agregado: as motos SEMPRE aparecem aqui, mesmo se os chips abaixo falharem.
    var motos = data.motos || [];
    for (var i = 0; i < motos.length; i++) {
      addOrIncrementMoto(motos[i].modelo_id, motos[i].quantidade);
    }

    // Unidades de roteirizacao -> chips removiveis (NF real / pedido s/ NF /
    // cotacao solta). As motos JA foram adicionadas via `data.motos`; aqui so
    // registramos quais motos cada unidade injetou (p/ o removeUnidade
    // decrementar) e criamos o chip. Fallback p/ `data.nfs` (formato antigo)
    // caso o backend ainda nao envie `unidades`.
    var unidades = data.unidades;
    if (!unidades && data.nfs) {
      unidades = data.nfs.map(function (nf) {
        return {
          chave: String(nf.numero_nf), tipo: 'nf', rotulo: 'NF ' + nf.numero_nf,
          cliente: nf.cliente, municipio: nf.municipio, uf: nf.uf,
          motos: nf.motos || [],
        };
      });
    }
    unidades = unidades || [];
    if (unidades.length) {
      var nfBox = document.getElementById('simulador-nf-box');
      if (nfBox) nfBox.style.display = 'block'; // chips precisam estar visiveis
      for (var n = 0; n < unidades.length; n++) {
        var u = unidades[n];
        if (state.nfsAdicionadas[u.chave]) continue;
        state.nfsAdicionadas[u.chave] = u.motos || []; // guarda p/ remover depois
        addUnidadeChip(u);
      }
    }
    return selecionouVeiculo;
  }

  function setupNfSelector() {
    var toggle = document.getElementById('simulador-add-nf-toggle');
    var box = document.getElementById('simulador-nf-box');
    var search = document.getElementById('simulador-nf-search');
    if (!toggle || !box || !search) return;

    toggle.addEventListener('click', function () {
      var hidden = box.style.display === 'none' || !box.style.display;
      box.style.display = hidden ? 'block' : 'none';
      if (hidden) {
        if (state.nfsPendentes === null) loadNfsPendentes();
        search.focus();
      }
    });

    search.addEventListener('input', function () {
      renderNfResults(search.value);
    });
  }

  function loadNfsPendentes() {
    state.nfsPendentes = [];
    fetch('/carvia/api/simulador-carga/nfs-pendentes')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.nfsPendentes = data.nfs || [];
        var search = document.getElementById('simulador-nf-search');
        renderNfResults(search ? search.value : '');
      })
      .catch(function (err) { console.error('Erro ao carregar NFs pendentes:', err); });
  }

  function renderNfResults(termo) {
    var container = document.getElementById('simulador-nf-results');
    if (!container) return;
    container.innerHTML = '';
    var lista = state.nfsPendentes || [];
    termo = (termo || '').trim().toLowerCase();

    var matches = [];
    for (var i = 0; i < lista.length && matches.length < 20; i++) {
      var nf = lista[i];
      if (state.nfsAdicionadas[nf.numero_nf]) continue;
      if (termo) {
        var hay = (nf.numero_nf + ' ' + (nf.cliente || '') + ' ' +
                   (nf.municipio || '') + ' ' + (nf.uf || '')).toLowerCase();
        if (hay.indexOf(termo) === -1) continue;
      }
      matches.push(nf);
    }

    for (var j = 0; j < matches.length; j++) {
      (function (nf) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'list-group-item list-group-item-action py-1 px-2';
        btn.style.fontSize = '0.75rem';
        var local = [nf.municipio, nf.uf].filter(Boolean).join('/');
        btn.innerHTML = '<strong>NF ' + nf.numero_nf + '</strong>' +
          (nf.cliente ? ' — ' + escapeHtml(nf.cliente) : '') +
          '<br><span class="text-muted">' + escapeHtml(local) +
          (nf.data ? ' · ' + nf.data : '') + '</span>';
        btn.addEventListener('click', function () { addNf(nf); });
        container.appendChild(btn);
      })(matches[j]);
    }

    if (!matches.length) {
      var empty = document.createElement('div');
      empty.className = 'text-muted px-2 py-1';
      empty.style.fontSize = '0.75rem';
      empty.textContent = (state.nfsPendentes && state.nfsPendentes.length)
        ? 'Nenhuma NF encontrada.' : 'Nenhuma NF não entregue.';
      container.appendChild(empty);
    }
  }

  function addNf(nf) {
    if (state.nfsAdicionadas[nf.numero_nf]) return;
    state.nfsAdicionadas[nf.numero_nf] = []; // placeholder anti duplo-clique

    fetch('/carvia/api/simulador-carga/motos-por-nf?nfs=' + encodeURIComponent(nf.numero_nf))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var motos = data.motos || [];
        state.nfsAdicionadas[nf.numero_nf] = motos; // guarda p/ remover depois
        for (var i = 0; i < motos.length; i++) {
          addOrIncrementMoto(motos[i].modelo_id, motos[i].quantidade);
        }
        // NF manual = unidade com chave = numero_nf (mesma chave do prefill, p/
        // nao duplicar caso a NF tambem tenha vindo da rota).
        addUnidadeChip({
          chave: String(nf.numero_nf), tipo: 'nf', rotulo: 'NF ' + nf.numero_nf,
          cliente: nf.cliente, municipio: nf.municipio, uf: nf.uf, motos: motos,
        });
        // Fecha a listagem ao selecionar: limpa busca + resultados (chips ficam visiveis).
        var search = document.getElementById('simulador-nf-search');
        if (search) search.value = '';
        var results = document.getElementById('simulador-nf-results');
        if (results) results.innerHTML = '';
      })
      .catch(function (err) {
        console.error('Erro ao resolver motos da NF:', err);
        delete state.nfsAdicionadas[nf.numero_nf];
      });
  }

  /** Cria 1 chip removivel para uma unidade de carga (NF / pedido / cotacao). */
  function addUnidadeChip(unidade) {
    var chips = document.getElementById('simulador-nf-chips');
    if (!chips) return;
    var motos = unidade.motos || [];
    var total = 0;
    for (var i = 0; i < motos.length; i++) total += (motos[i].quantidade || 0);

    var chip = document.createElement('span');
    chip.className = 'badge bg-secondary d-inline-flex align-items-center gap-1';
    chip.dataset.chave = unidade.chave;
    var localTxt = [unidade.municipio, unidade.uf].filter(Boolean).join('/');
    chip.title = [unidade.cliente, localTxt].filter(Boolean).join(' · ') || unidade.rotulo;

    var label = document.createElement('span');
    var cli = unidade.cliente
      ? (unidade.cliente.length > 28 ? unidade.cliente.slice(0, 28) + '…' : unidade.cliente)
      : '';
    label.textContent = unidade.rotulo + (cli ? ' · ' + cli : '') +
      ' (' + total + (total === 1 ? ' moto)' : ' motos)');
    chip.appendChild(label);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-close btn-close-white';
    btn.style.fontSize = '0.55rem';
    btn.setAttribute('aria-label', 'Remover ' + unidade.rotulo);
    btn.addEventListener('click', function () { removeUnidade(unidade.chave); });
    chip.appendChild(btn);

    chips.appendChild(chip);
  }

  /** Remove uma unidade adicionada: decrementa as motos que ela injetou e tira o chip. */
  function removeUnidade(chave) {
    var motos = state.nfsAdicionadas[chave];
    if (Array.isArray(motos)) {
      for (var i = 0; i < motos.length; i++) {
        decrementMoto(motos[i].modelo_id, motos[i].quantidade);
      }
    }
    delete state.nfsAdicionadas[chave];

    var chips = document.getElementById('simulador-nf-chips');
    if (chips) {
      var chip = chips.querySelector('[data-chave="' + chave + '"]');
      if (chip) chip.remove();
    }
    // Unidade volta a ficar disponivel na busca (NF manual)
    var search = document.getElementById('simulador-nf-search');
    renderNfResults(search ? search.value : '');
    scheduleRecalc();
  }

  /** Subtrai qty da linha do modelo; remove a linha se zerar. */
  function decrementMoto(modeloId, qty) {
    if (!modeloId || qty <= 0) return;
    var rows = document.querySelectorAll('.simulador-moto-row');
    for (var i = 0; i < rows.length; i++) {
      var sel = rows[i].querySelector('.simulador-modelo-select');
      if (sel && parseInt(sel.value) === parseInt(modeloId)) {
        var qi = rows[i].querySelector('.simulador-qty-input');
        var novo = (parseInt(qi.value) || 0) - qty;
        if (novo > 0) {
          qi.value = novo;
        } else {
          rows[i].remove();
          updateRowColors();
        }
        scheduleRecalc();
        return;
      }
    }
  }

  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // ========== Persistir dimensoes do veiculo (override -> cadastro) ==========

  function setupSalvarDimensoes() {
    var btn = document.getElementById('simulador-salvar-dims');
    if (btn) btn.addEventListener('click', salvarDimensoesVeiculo);
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function notificarDims(msg, tipo) {
    var el = document.getElementById('simulador-dims-status');
    if (!el) return;
    el.textContent = msg;
    el.className = 'd-block mt-1 ' + (tipo === 'erro' ? 'text-danger' : 'text-success');
    el.style.fontSize = '0.7rem';
  }

  function salvarDimensoesVeiculo() {
    var select = document.getElementById('simulador-veiculo');
    var veiculoId = select && select.value ? parseInt(select.value, 10) : null;
    if (!veiculoId) {
      notificarDims('Selecione um veículo primeiro.', 'erro');
      return;
    }
    var comp = parseFloat((document.getElementById('simulador-override-comp') || {}).value);
    var larg = parseFloat((document.getElementById('simulador-override-larg') || {}).value);
    var alt = parseFloat((document.getElementById('simulador-override-alt') || {}).value);
    if (!(comp > 0 && larg > 0 && alt > 0)) {
      notificarDims('Informe comprimento, largura e altura (> 0).', 'erro');
      return;
    }

    var btn = document.getElementById('simulador-salvar-dims');
    if (btn) btn.disabled = true;
    notificarDims('Salvando…', 'ok');

    fetch('/carvia/api/simulador-carga/veiculo/' + veiculoId + '/dimensoes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify({ comprimento_bau: comp, largura_bau: larg, altura_bau: alt }),
    })
      .then(function (r) {
        return r.json().then(function (j) { return { ok: r.ok, body: j }; });
      })
      .then(function (res) {
        if (btn) btn.disabled = false;
        if (!res.ok || !res.body.sucesso) {
          notificarDims((res.body && res.body.erro) || 'Falha ao salvar dimensões.', 'erro');
          return;
        }
        atualizarVeiculoNoCatalogo(res.body.veiculo);
        notificarDims('Dimensões salvas no veículo.', 'ok');
      })
      .catch(function (err) {
        if (btn) btn.disabled = false;
        console.error('Erro ao salvar dimensões:', err);
        notificarDims('Erro de rede ao salvar.', 'erro');
      });
  }

  /** Reflete as dimensoes salvas no cache, no <option> e no veiculo selecionado. */
  function atualizarVeiculoNoCatalogo(v) {
    if (!v) return;
    for (var i = 0; i < state.veiculos.length; i++) {
      if (state.veiculos[i].id === v.id) {
        state.veiculos[i].comprimento_bau = v.comprimento_bau;
        state.veiculos[i].largura_bau = v.largura_bau;
        state.veiculos[i].altura_bau = v.altura_bau;
        state.veiculos[i].tem_dimensoes_bau = v.tem_dimensoes_bau;
        break;
      }
    }
    var select = document.getElementById('simulador-veiculo');
    if (select) {
      var opt = select.querySelector('option[value="' + v.id + '"]');
      if (opt) {
        opt.dataset.comprimento = v.comprimento_bau;
        opt.dataset.largura = v.largura_bau;
        opt.dataset.altura = v.altura_bau;
        opt.textContent = v.nome + ' — ' + formatNumber(v.peso_maximo) + 'kg (' +
          Math.round(v.comprimento_bau) + '×' + Math.round(v.largura_bau) +
          '×' + Math.round(v.altura_bau) + 'cm)';
      }
    }
    if (state.veiculoSelecionado && state.veiculoSelecionado.id === v.id) {
      state.veiculoSelecionado.w = v.comprimento_bau;
      state.veiculoSelecionado.d = v.largura_bau;
      state.veiculoSelecionado.h = v.altura_bau;
    }
  }

  // ========== Conservas Nacom (pallets) ==========

  function setupPalletControls() {
    // "Pallet sobre pallet" e client-side (re-empacota) — vale nos 2 modos.
    var sobre = document.getElementById('pallet-sobre-pallet');
    if (sobre) sobre.addEventListener('change', scheduleRecalc);

    var loteInput = document.getElementById('pallet-lote');
    if (loteInput) {
      loteInput.addEventListener('change', function () {
        state.loteSeparacao = (loteInput.value || '').trim() || null;
        recarregarPallets();
      });
    }
    ['pallet-modo', 'pallet-separado'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', recarregarPallets);
    });
    var ob = document.getElementById('pallet-overbooking');
    if (ob) {
      ob.addEventListener('input', function () {
        var v = document.getElementById('pallet-overbooking-val');
        if (v) v.textContent = ob.value + '%';
      });
      ob.addEventListener('change', recarregarPallets);
    }
  }

  /** Busca os pallets do lote informado no backend (Camada 1) e re-empacota. */
  function recarregarPallets() {
    if (!state.loteSeparacao) {
      state.pallets = [];
      mostrarPendencias([]);
      scheduleRecalc();
      return;
    }
    var modo = (document.getElementById('pallet-modo') || {}).value || 'A';
    var separado = !!(document.getElementById('pallet-separado') || {}).checked;
    var obEl = document.getElementById('pallet-overbooking');
    var ob = obEl ? (parseFloat(obEl.value) || 0) / 100 : 0;
    var q = 'lote=' + encodeURIComponent(state.loteSeparacao) +
            '&modo=' + encodeURIComponent(modo) +
            '&separado=' + (separado ? '1' : '0') +
            '&overbooking=' + ob;
    fetch('/carvia/api/simulador-carga/pallets-por-separacao?' + q)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.pallets = data.pallets || [];
        mostrarPendencias(data.pendencias || []);
        scheduleRecalc();
      })
      .catch(function (err) { console.error('Erro ao carregar pallets:', err); });
  }

  function mostrarPendencias(pend) {
    var el = document.getElementById('pallet-pendencias');
    if (!el) return;
    if (!pend || !pend.length) { el.textContent = ''; return; }
    var cods = pend.map(function (p) { return p.cod_produto; }).join(', ');
    el.textContent = '⚠ ' + pend.length + ' produto(s) sem cadastro de palletização: ' + cods;
  }

  /**
   * Render em 2 fases: pack() instantaneo (feedback imediato) seguido de packOptimized
   * (Simulated Annealing, ~100-350ms) que "sobe" o resultado. A otimizacao roda fora do
   * frame atual (setTimeout) para nao atrasar o render preliminar; o packToken descarta
   * o resultado se o usuario alterou a entrada nesse meio-tempo.
   */
  function packAndRender(bay, motoList, colorMap) {
    var options = getPackingOptions();
    // Conservas Nacom primeiro: o bin-packer assenta os pallets no piso (fase 1)
    // e as motos por cima (fase 2). A ordem na lista nao importa — packItems separa.
    var itens = (state.pallets || []).concat(motoList);

    var quick = BinPacker.pack(bay, itens, options);
    state.renderer.render(quick, bay, colorMap);
    updateStats(quick, bay);
    updateLegend(motoList, colorMap);

    var token = ++state.packToken;
    setTimeout(function () {
      if (token !== state.packToken) return; // entrada mudou; descarta
      var optimized = BinPacker.packOptimized(bay, itens, options);
      if (token !== state.packToken) return;
      if (optimized.stats.posicionadas >= quick.stats.posicionadas) {
        state.renderer.render(optimized, bay, colorMap);
        updateStats(optimized, bay);
      }
    }, 0);
  }

  // ========== Recalc ==========

  function scheduleRecalc() {
    if (state.debounceTimer) clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(recalcular, DEBOUNCE_MS);
  }

  function recalcular() {
    if (!state.renderer) return;

    // Ler bay (com override se disponivel)
    var bay = getEffectiveBay();
    if (!bay) {
      state.renderer.render(null, null, null);
      updateStats(null, null);
      return;
    }

    // Ler motos das linhas
    var motoList = [];
    var colorMap = {};
    var rows = document.querySelectorAll('.simulador-moto-row');
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var select = row.querySelector('.simulador-modelo-select');
      var qtyInput = row.querySelector('.simulador-qty-input');
      if (!select || !select.value || !qtyInput) continue;

      var opt = select.options[select.selectedIndex];
      var modeloId = parseInt(select.value);
      var qty = parseInt(qtyInput.value) || 0;
      if (qty <= 0) continue;

      var colorHex = row.dataset.color || PALETTE_HEX[i % PALETTE_HEX.length];
      colorMap[modeloId] = colorHex;

      motoList.push({
        id: modeloId,
        nome: opt.textContent,
        comprimento: parseFloat(opt.dataset.comprimento),
        largura: parseFloat(opt.dataset.largura),
        altura: parseFloat(opt.dataset.altura),
        peso_medio: parseFloat(opt.dataset.peso) || 0,
        qty: qty,
        color: colorHex,
      });
    }

    state.colorMap = colorMap;
    packAndRender(bay, motoList, colorMap);
  }

  // ========== Opcoes de empacotamento (sliders) ==========

  /** Le as opcoes de APOIO dos sliders (fallback p/ defaults se ausentes).
      Nao ha sobreposicao: caixas nunca se interpenetram. */
  function getPackingOptions() {
    function rd(id, def, div) {
      var el = document.getElementById(id);
      if (!el) return def;
      var v = parseFloat(el.value);
      if (isNaN(v)) return def;
      return div ? v / div : v;
    }
    var sobre = document.getElementById('pallet-sobre-pallet');
    return {
      minSupport: rd('pack-min-support', 50, 100),
      maxOverhang: rd('pack-max-overhang', 15, 1),
      maxGap: rd('pack-max-gap', 50, 1),
      palletSobrePallet: !!(sobre && sobre.checked),
    };
  }

  /** Conecta os sliders: atualiza o valor exibido e dispara recalculo (debounced). */
  function bindPackControls(onChange) {
    var inputs = document.querySelectorAll('.simulador-pack-input');
    for (var i = 0; i < inputs.length; i++) {
      (function (el) {
        function update() {
          var span = document.getElementById('val-' + el.id.replace('pack-', ''));
          if (span) span.textContent = el.value + (el.dataset.suffix || '');
          if (onChange) onChange();
        }
        el.addEventListener('input', update);
        // Sincroniza o valor exibido com o value inicial do HTML
        var span0 = document.getElementById('val-' + el.id.replace('pack-', ''));
        if (span0) span0.textContent = el.value + (el.dataset.suffix || '');
      })(inputs[i]);
    }
  }

  function getEffectiveBay() {
    // Usar override se disponivel
    var compEl = document.getElementById('simulador-override-comp');
    var largEl = document.getElementById('simulador-override-larg');
    var altEl = document.getElementById('simulador-override-alt');

    if (compEl && compEl.value && largEl && largEl.value && altEl && altEl.value) {
      return {
        w: parseFloat(compEl.value),
        d: parseFloat(largEl.value),
        h: parseFloat(altEl.value),
        nome: state.veiculoSelecionado ? state.veiculoSelecionado.nome : '',
        pesoMax: state.veiculoSelecionado ? state.veiculoSelecionado.pesoMax : 0,
      };
    }

    return state.veiculoSelecionado;
  }

  // ========== UI Updates ==========

  function updateStats(result, bay) {
    if (!result) {
      setStatValue('simulador-stat-posicionadas', '—');
      setStatValue('simulador-stat-rejeitadas', '—');
      setStatValue('simulador-stat-ocupacao', '—');
      setStatValue('simulador-stat-peso', '—');
      return;
    }

    setStatValue('simulador-stat-posicionadas', result.stats.posicionadas);
    setStatValue('simulador-stat-rejeitadas', result.stats.rejeitadas);
    setStatValue('simulador-stat-ocupacao', result.stats.percentualOcupacao + '%');
    setStatValue('simulador-stat-peso', formatNumber(result.stats.pesoTotal) + 'kg');

    // Peso maximo
    var pesoMaxEl = document.getElementById('simulador-peso-max');
    if (pesoMaxEl && bay && bay.pesoMax) {
      var folga = bay.pesoMax - result.stats.pesoTotal;
      pesoMaxEl.textContent = 'Peso máx. veículo: ' + formatNumber(bay.pesoMax) +
        'kg | Folga: ' + formatNumber(folga) + 'kg';
    }

    // Destaque se rejeitadas > 0
    var rejEl = document.getElementById('simulador-stat-rejeitadas');
    if (rejEl) {
      rejEl.parentElement.classList.toggle('simulador-stat-alert', result.stats.rejeitadas > 0);
    }
  }

  function setStatValue(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function updateLegend(motoList, colorMap) {
    var container = document.getElementById('simulador-legend');
    if (!container) return;

    container.innerHTML = '';
    for (var i = 0; i < motoList.length; i++) {
      var m = motoList[i];
      if ((m.qty || 0) <= 0) continue;

      var item = document.createElement('div');
      item.className = 'simulador-legend-item';

      var swatch = document.createElement('div');
      swatch.className = 'simulador-legend-swatch';
      swatch.style.backgroundColor = colorMap[m.id] || PALETTE_HEX[i % PALETTE_HEX.length];

      var label = document.createElement('span');
      label.textContent = m.nome + ' (' + m.qty + 'x)';

      item.appendChild(swatch);
      item.appendChild(label);
      container.appendChild(item);
    }

    // Grupos de pallets de conservas (cor + grupo, contagem de pallets)
    var grupos = {};
    var lista = state.pallets || [];
    for (var k = 0; k < lista.length; k++) {
      var pal = lista[k];
      var chave = (pal.grupo || 'Conservas') + '|' + (pal.color || '#c0844a');
      if (!grupos[chave]) grupos[chave] = { grupo: pal.grupo || 'Conservas', color: pal.color || '#c0844a', n: 0 };
      grupos[chave].n += 1;
    }
    Object.keys(grupos).forEach(function (chave) {
      var g = grupos[chave];
      var item2 = document.createElement('div');
      item2.className = 'simulador-legend-item';
      var swatch2 = document.createElement('div');
      swatch2.className = 'simulador-legend-swatch';
      swatch2.style.backgroundColor = g.color;
      var label2 = document.createElement('span');
      label2.textContent = g.grupo + ' (' + g.n + ' pallet' + (g.n === 1 ? '' : 's') + ')';
      item2.appendChild(swatch2);
      item2.appendChild(label2);
      container.appendChild(item2);
    });
  }

  function formatNumber(n) {
    if (n == null) return '0';
    return n.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
  }

  // Init ao carregar DOM
  document.addEventListener('DOMContentLoaded', init);

  // Cleanup ao sair
  window.addEventListener('beforeunload', function () {
    if (state.renderer) state.renderer.dispose();
  });
})();
