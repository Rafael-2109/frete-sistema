/**
 * SimuladorUI — Controlador da interface do Simulador 3D de Carga.
 *
 * Orquestra:
 * - Sidebar: selecao de veiculo, linhas de modelo de moto, botoes +/-
 * - BinPacker: calcula empacotamento
 * - CargaRenderer: renderiza cena Three.js
 * - Stats: atualiza metricas na sidebar
 *
 * Dois modos:
 * - 'livre': carrega catalogo via API, usuario monta livremente
 * - 'embarque': dados vem embutidos no HTML (JSON), read-only
 */
;(function () {
  'use strict';

  var DEBOUNCE_MS = 200;
  var PALETTE_HEX = [
    '#4a90d9', '#e8854c', '#67c26a', '#b06fc4',
    '#e8cc4c', '#4cc4c4', '#e85c6e', '#8a9bb0',
  ];

  var state = {
    modo: 'livre', // 'livre' ou 'embarque'
    veiculos: [],
    modelosMoto: [],
    veiculoSelecionado: null,
    linhasMoto: [], // [{modeloId, qty}]
    renderer: null,
    colorMap: {}, // {modelo_id: '#hex'}
    debounceTimer: null,
  };

  function init() {
    var container = document.getElementById('simulador-canvas');
    if (!container) return;

    // Detectar modo
    var initDataEl = document.getElementById('simulador-init-data');
    if (initDataEl) {
      state.modo = 'embarque';
      initEmbarqueMode(initDataEl, container);
    } else {
      state.modo = 'livre';
      initLivreMode(container);
    }
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

        // Selecionar primeiro veiculo com dimensoes
        var selectEl = document.getElementById('simulador-veiculo');
        if (selectEl && selectEl.value) {
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

    var selectDiv = document.createElement('div');
    selectDiv.className = 'simulador-moto-select-wrap';
    var select = createMotoModelSelect();
    if (modeloId) select.value = modeloId;
    select.addEventListener('change', function () { scheduleRecalc(); });
    selectDiv.appendChild(select);

    var dimsSpan = document.createElement('div');
    dimsSpan.className = 'simulador-moto-dims';
    dimsSpan.textContent = getDimsText(select);

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

    row.appendChild(selectDiv);
    row.appendChild(dimsSpan);
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

  // ========== Modo Embarque ==========

  function initEmbarqueMode(initDataEl, container) {
    var data;
    try {
      data = JSON.parse(initDataEl.textContent);
    } catch (e) {
      console.error('Erro ao parsear dados do embarque:', e);
      return;
    }

    if (data.erro === 'veiculo_sem_dimensoes') {
      var warning = document.getElementById('simulador-warning');
      if (warning) {
        warning.textContent = 'Veículo do embarque não possui dimensões do baú cadastradas. Configure nas Administração de Veículos.';
        warning.style.display = 'block';
      }
      return;
    }

    // Criar renderer
    var isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    state.renderer = new CargaRenderer(container, isDark ? 'dark' : 'light');

    if (!data.veiculo) return;

    state.veiculoSelecionado = {
      w: data.veiculo.comprimento_bau,
      d: data.veiculo.largura_bau,
      h: data.veiculo.altura_bau,
      pesoMax: data.veiculo.peso_maximo,
      nome: data.veiculo.nome,
    };

    // Montar lista de motos e executar pack
    var motoList = [];
    var colorMap = {};
    for (var i = 0; i < data.motos.length; i++) {
      var m = data.motos[i];
      var colorHex = PALETTE_HEX[i % PALETTE_HEX.length];
      colorMap[m.modelo_id] = colorHex;
      motoList.push({
        id: m.modelo_id,
        nome: m.modelo_nome,
        comprimento: m.comprimento,
        largura: m.largura,
        altura: m.altura,
        peso_medio: m.peso_medio || 0,
        qty: m.quantidade,
        color: colorHex,
      });
    }
    state.colorMap = colorMap;

    var result = BinPacker.pack(state.veiculoSelecionado, motoList);
    state.renderer.render(result, state.veiculoSelecionado, colorMap);
    updateStats(result, state.veiculoSelecionado);
    updateLegend(motoList, colorMap);

    // Bind vistas
    document.querySelectorAll('.simulador-view-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var preset = this.dataset.view;
        document.querySelectorAll('.simulador-view-btn').forEach(function (b) {
          b.classList.remove('active');
        });
        this.classList.add('active');
        state.renderer.setView(preset, state.veiculoSelecionado);
      });
    });
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

    var result = BinPacker.pack(bay, motoList);
    state.renderer.render(result, bay, colorMap);
    updateStats(result, bay);
    updateLegend(motoList, colorMap);
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
