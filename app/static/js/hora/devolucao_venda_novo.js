/**
 * Wizard de Nova Devolucao de Venda (HORA).
 *
 * Fluxo:
 *   1. Pesquisar NF de venda (FATURADO) por NF/cliente/CPF (AJAX).
 *   2. Selecionar a venda -> carrega motos elegiveis (AJAX).
 *   3. Operador marca chassis devolvidos (checkboxes) + motivo geral.
 *   4. Submit -> backend cria HoraDevolucaoVenda + items + emite eventos DEVOLVIDA.
 *
 * URLs sao lidas dos data-attributes do <body data-dv-novo-...> para nao
 * misturar Jinja e JS (mantem este arquivo cacheavel pelo navegador e
 * evita refazer build por cada renderizacao).
 */
(function () {
  'use strict';

  const root = document.getElementById('dv-novo-root');
  if (!root) return; // pagina nao e a de Nova Devolucao

  const URL_BUSCAR_VENDAS = root.dataset.urlBuscarVendas;
  const URL_MOTOS_VENDA = root.dataset.urlMotosVenda;
  const URL_LISTA = root.dataset.urlLista;

  const $busca = document.getElementById('busca-venda');
  const $btnBuscar = document.getElementById('btn-buscar');
  const $resultadosWrap = document.getElementById('resultados-busca-wrap');
  const $resultados = document.getElementById('resultados-busca');
  const $buscaVazia = document.getElementById('busca-vazia');

  const $cardPesquisa = document.getElementById('card-pesquisa-venda');
  const $form = document.getElementById('form-devolucao');
  const $vendaIdInput = document.getElementById('venda_id_input');
  const $vendaInfo = document.getElementById('venda-info');
  const $motos = document.getElementById('motos-da-venda');
  const $motosVazio = document.getElementById('motos-vazio');
  const $checkTodos = document.getElementById('check-todos');

  function fmtBRL(v) {
    if (v == null) return '—';
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  function buscarVendas() {
    const termo = $busca.value.trim();
    if (termo.length < 2) {
      $resultados.innerHTML = '';
      $resultadosWrap.style.display = 'none';
      $buscaVazia.style.display = 'none';
      return;
    }
    fetch(`${URL_BUSCAR_VENDAS}?q=${encodeURIComponent(termo)}`, {
      headers: { Accept: 'application/json' },
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.ok) {
          alert(data.erro || 'Erro ao buscar vendas');
          return;
        }
        $resultados.innerHTML = '';
        if (!data.vendas || data.vendas.length === 0) {
          $resultadosWrap.style.display = 'none';
          $buscaVazia.style.display = 'block';
          return;
        }
        $buscaVazia.style.display = 'none';
        $resultadosWrap.style.display = '';
        data.vendas.forEach((v) => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>${escapeHtml(v.nf_saida_numero || '—')}</strong></td>
            <td><small>${escapeHtml(v.data_venda || '—')}</small></td>
            <td>${escapeHtml(v.nome_cliente || '—')}</td>
            <td><small class="chassi-mono">${escapeHtml(v.cpf_cliente || '—')}</small></td>
            <td><small>${escapeHtml(v.loja_nome || '—')}</small></td>
            <td>${fmtBRL(v.valor_total)}</td>
            <td>
              <button type="button" class="btn btn-sm btn-success btn-selecionar"
                      data-venda-id="${v.id}"
                      data-venda-nf="${escapeHtml(v.nf_saida_numero || '')}"
                      data-venda-cliente="${escapeHtml(v.nome_cliente || '')}"
                      data-venda-data="${escapeHtml(v.data_venda || '')}"
                      data-venda-loja="${escapeHtml(v.loja_nome || '')}">
                Selecionar
              </button>
            </td>`;
          $resultados.appendChild(tr);
        });
      })
      .catch((err) => alert('Erro de rede: ' + err));
  }

  function selecionarVenda(meta) {
    $vendaIdInput.value = meta.id;
    $vendaInfo.innerHTML = `
      <div class="row g-3">
        <div class="col-md-3"><strong>NF:</strong> ${escapeHtml(meta.nf || '—')}</div>
        <div class="col-md-3"><strong>Data:</strong> ${escapeHtml(meta.data || '—')}</div>
        <div class="col-md-3"><strong>Cliente:</strong> ${escapeHtml(meta.cliente || '—')}</div>
        <div class="col-md-3"><strong>Loja:</strong> ${escapeHtml(meta.loja || '—')}</div>
      </div>`;

    fetch(`${URL_MOTOS_VENDA}?venda_id=${encodeURIComponent(meta.id)}`, {
      headers: { Accept: 'application/json' },
    })
      .then((r) => r.json())
      .then((data) => {
        $motos.innerHTML = '';
        if (!data.ok) {
          alert(data.erro || 'Erro ao carregar motos');
          return;
        }
        if (!data.motos || data.motos.length === 0) {
          $motosVazio.style.display = '';
          return;
        }
        $motosVazio.style.display = 'none';
        data.motos.forEach((m) => {
          const tr = document.createElement('tr');
          const elegivel = m.elegivel === true;
          const inputId = `motivo_chassi_${m.numero_chassi}`;
          const statusBadge = elegivel
            ? `<span class="badge bg-info">${escapeHtml(m.ultimo_evento || '—')}</span>`
            : `<span class="badge bg-warning text-dark" title="${escapeHtml(m.motivo_inelegivel || '')}">${escapeHtml(m.ultimo_evento || '—')}</span>`;
          tr.innerHTML = `
            <td>
              <input type="checkbox" name="chassis_selecionados"
                     value="${escapeHtml(m.numero_chassi)}"
                     class="check-chassi"
                     ${elegivel ? '' : 'disabled'}>
            </td>
            <td><strong class="chassi-mono">${escapeHtml(m.numero_chassi)}</strong></td>
            <td>${escapeHtml(m.modelo_nome || '—')}</td>
            <td>${escapeHtml(m.cor || '—')}</td>
            <td>${fmtBRL(m.preco_final)}</td>
            <td>${statusBadge}</td>
            <td>
              <input type="text" id="${inputId}"
                     name="motivo_especifico__${escapeHtml(m.numero_chassi)}"
                     class="form-control form-control-sm"
                     placeholder="Opcional"
                     ${elegivel ? '' : 'disabled'}>
            </td>`;
          $motos.appendChild(tr);
        });
      })
      .catch((err) => alert('Erro ao carregar motos: ' + err));

    $cardPesquisa.style.display = 'none';
    $form.style.display = '';
    $form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Eventos
  $btnBuscar.addEventListener('click', buscarVendas);
  $busca.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      buscarVendas();
    }
  });

  $resultados.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-selecionar');
    if (!btn) return;
    selecionarVenda({
      id: btn.dataset.vendaId,
      nf: btn.dataset.vendaNf,
      cliente: btn.dataset.vendaCliente,
      data: btn.dataset.vendaData,
      loja: btn.dataset.vendaLoja,
    });
  });

  $checkTodos.addEventListener('change', (e) => {
    document.querySelectorAll('.check-chassi:not(:disabled)').forEach((c) => {
      c.checked = e.target.checked;
    });
  });

  document.getElementById('btn-trocar-venda').addEventListener('click', () => {
    $form.style.display = 'none';
    $cardPesquisa.style.display = '';
    $vendaIdInput.value = '';
    $motos.innerHTML = '';
    $vendaInfo.innerHTML = '';
    $checkTodos.checked = false;
  });

  $form.addEventListener('submit', (e) => {
    const sel = document.querySelectorAll('.check-chassi:checked').length;
    if (sel === 0) {
      e.preventDefault();
      alert('Selecione ao menos 1 chassi para devolução.');
      return;
    }
    const motivo = document.getElementById('motivo-geral').value.trim();
    if (motivo.length < 3) {
      e.preventDefault();
      alert('Informe o motivo da devolução (mínimo 3 caracteres).');
      return;
    }
  });

  // URL_LISTA fica disponivel se algum botao "voltar" precisar (placeholder).
  void URL_LISTA;
})();
