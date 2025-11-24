/**
 * MODAL ADICIONAR PROGRAMAÇÃO - Programação por Linhas
 * Gerencia a criação de novas programações de produção
 *
 * ✅ ENCAPSULADO em IIFE para evitar conflitos de variáveis globais
 */

(function() {
    'use strict';

    // ============================================================
    // ESTADO DO MODAL (PRIVADO)
    // ============================================================

    let produtoSelecionado = null;
    let linhasDisponiveis = [];
    let produtosComuns = [];

    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================

    $(document).ready(function() {
    // Limpar modal ao abrir
    $('#modalAdicionarProgramacao').on('show.bs.modal', function() {
        limparFormulario();
        carregarProdutosComuns();
    });

    // Autocomplete do produto
    let timeoutAutocomplete = null;
    $('#add-prog-produto-busca').on('input', function() {
        clearTimeout(timeoutAutocomplete);
        const termo = $(this).val().trim();

        if (termo.length < 2) {
            $('#add-prog-autocomplete-list').html('').hide();
            return;
        }

        timeoutAutocomplete = setTimeout(() => buscarProdutos(termo), 300);
    });

    // Dropdown de produtos comuns
    $('#add-prog-produto-select').on('change', function() {
        const codProduto = $(this).val();
        if (codProduto) {
            const produto = produtosComuns.find(p => p.cod_produto === codProduto);
            if (produto) {
                selecionarProduto(produto);
                $('#add-prog-produto-busca').val(''); // Limpar busca
            }
        }
    });

    // Botão Salvar
    $('#btn-salvar-programacao').on('click', salvarProgramacao);

    // Fechar autocomplete ao clicar fora
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.autocomplete-container').length) {
            $('#add-prog-autocomplete-list').hide();
        }
    });
});

// ============================================================
// FUNÇÕES DE BUSCA E SELEÇÃO DE PRODUTOS
// ============================================================

/**
 * Busca produtos por termo (autocomplete)
 */
async function buscarProdutos(termo) {
    try {
        const response = await fetch(`/manufatura/api/necessidade-producao/autocomplete-produtos?termo=${encodeURIComponent(termo)}`);
        const produtos = await response.json();

        if (produtos.erro) {
            console.error('[AUTOCOMPLETE] Erro:', produtos.erro);
            return;
        }

        renderizarAutocomplete(produtos);
    } catch (error) {
        console.error('[AUTOCOMPLETE] Erro:', error);
    }
}

/**
 * Renderiza lista de autocomplete
 */
function renderizarAutocomplete(produtos) {
    const $list = $('#add-prog-autocomplete-list');

    if (!produtos || produtos.length === 0) {
        $list.html('<div class="autocomplete-item text-muted">Nenhum produto encontrado</div>').show();
        return;
    }

    let html = '';
    produtos.forEach(produto => {
        html += `
            <div class="autocomplete-item" data-cod="${produto.cod_produto}" data-nome="${produto.nome_produto}">
                <strong>${produto.cod_produto}</strong> - ${produto.nome_produto}
                ${produto.linha_producao ? `<br><small class="text-muted">Linha: ${produto.linha_producao}</small>` : ''}
            </div>
        `;
    });

    $list.html(html).show();

    // Listener de clique nos itens
    $('.autocomplete-item').on('click', function() {
        const codProduto = $(this).data('cod');
        const nomeProduto = $(this).data('nome');

        selecionarProduto({
            cod_produto: codProduto,
            nome_produto: nomeProduto
        });

        $list.hide();
    });
}

/**
 * Carrega produtos comuns (mais usados) para dropdown
 */
async function carregarProdutosComuns() {
    try {
        // Buscar produtos com produto_produzido=True
        const response = await fetch('/manufatura/api/lista-materiais/produtos-produzidos');
        const data = await response.json();

        if (data.erro) {
            console.error('[PRODUTOS COMUNS] Erro:', data.erro);
            $('#add-prog-produto-select').html('<option value="">Erro ao carregar</option>');
            return;
        }

        produtosComuns = data.produtos || [];

        // Preencher dropdown (limitar a 50 produtos mais comuns)
        const $select = $('#add-prog-produto-select');
        $select.html('<option value="">Selecione um produto</option>');

        produtosComuns.slice(0, 50).forEach(produto => {
            $select.append(`
                <option value="${produto.cod_produto}">
                    ${produto.cod_produto} - ${produto.nome_produto}
                </option>
            `);
        });

    } catch (error) {
        console.error('[PRODUTOS COMUNS] Erro:', error);
        $('#add-prog-produto-select').html('<option value="">Erro ao carregar</option>');
    }
}

/**
 * Seleciona um produto e busca suas linhas de produção
 */
async function selecionarProduto(produto) {
    produtoSelecionado = produto;

    // Mostrar info do produto
    $('#add-prog-cod-produto').val(produto.cod_produto);
    $('#add-prog-nome-produto').text(`${produto.cod_produto} - ${produto.nome_produto}`);
    $('#add-prog-produto-info').removeClass('d-none');

    // Buscar linhas de produção disponíveis para este produto
    await carregarLinhasProducao(produto.cod_produto);
}

/**
 * Carrega linhas de produção disponíveis para o produto
 */
async function carregarLinhasProducao(codProduto) {
    try {
        const response = await fetch(`/manufatura/recursos/api/listar?search=${encodeURIComponent(codProduto)}`);
        const data = await response.json();

        if (!data.success) {
            mostrarAlerta('Erro ao buscar linhas de produção', 'danger');
            return;
        }

        linhasDisponiveis = data.dados || [];

        const $select = $('#add-prog-linha');
        $select.html('');

        if (linhasDisponiveis.length === 0) {
            $select.html('<option value="">Nenhuma linha disponível</option>');
            $select.prop('disabled', true);
            mostrarAlerta('Este produto não possui linhas de produção cadastradas', 'warning');
            return;
        }

        // Agrupar por linha
        const linhasUnicas = [...new Set(linhasDisponiveis.map(r => r.linha_producao))];

        linhasUnicas.forEach(linha => {
            $select.append(`<option value="${linha}">${linha}</option>`);
        });

        $select.prop('disabled', false);
        ocultarAlerta();

    } catch (error) {
        console.error('[LINHAS PRODUCAO] Erro:', error);
        mostrarAlerta('Erro ao carregar linhas de produção', 'danger');
    }
}

// ============================================================
// SALVAR PROGRAMAÇÃO
// ============================================================

/**
 * Valida e salva a programação
 */
async function salvarProgramacao() {
    try {
        // Validar campos
        const codProduto = $('#add-prog-cod-produto').val();
        const dataProgramacao = $('#add-prog-data').val();
        const linhaProducao = $('#add-prog-linha').val();
        const qtdProgramada = parseFloat($('#add-prog-quantidade').val());
        const clienteProduto = $('#add-prog-cliente').val().trim();
        const observacaoPcp = $('#add-prog-observacao').val().trim();

        if (!codProduto) {
            mostrarAlerta('Selecione um produto', 'warning');
            return;
        }

        if (!dataProgramacao) {
            mostrarAlerta('Informe a data de programação', 'warning');
            return;
        }

        if (!linhaProducao) {
            mostrarAlerta('Selecione a linha de produção', 'warning');
            return;
        }

        if (!qtdProgramada || qtdProgramada <= 0) {
            mostrarAlerta('Informe uma quantidade válida', 'warning');
            return;
        }

        // Desabilitar botão
        const $btn = $('#btn-salvar-programacao');
        const textoOriginal = $btn.html();
        $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-1"></i>Salvando...');

        // Enviar para API
        const response = await fetch('/manufatura/api/necessidade-producao/adicionar-programacao', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cod_produto: codProduto,
                data_programacao: dataProgramacao,
                linha_producao: linhaProducao,
                qtd_programada: qtdProgramada,
                cliente_produto: clienteProduto || null,
                observacao_pcp: observacaoPcp || null
            })
        });

        const resultado = await response.json();

        if (resultado.erro) {
            mostrarAlerta(resultado.erro, 'danger');
            $btn.prop('disabled', false).html(textoOriginal);
            return;
        }

        // Sucesso!
        mostrarAlerta('Programação adicionada com sucesso!', 'success');

        // Aguardar 1 segundo e fechar modal
        setTimeout(() => {
            $('#modalAdicionarProgramacao').modal('hide');

            // Recarregar dados da tela
            if (typeof carregarProgramacaoLinhas === 'function') {
                carregarProgramacaoLinhas();
            }
        }, 1000);

    } catch (error) {
        console.error('[SALVAR PROGRAMACAO] Erro:', error);
        mostrarAlerta('Erro ao salvar programação: ' + error.message, 'danger');
        $('#btn-salvar-programacao').prop('disabled', false).html('<i class="fas fa-save me-1"></i>Salvar Programação');
    }
}

// ============================================================
// UTILITÁRIOS
// ============================================================

/**
 * Limpa o formulário
 */
function limparFormulario() {
    $('#form-adicionar-programacao')[0].reset();
    $('#add-prog-cod-produto').val('');
    $('#add-prog-produto-busca').val('');
    $('#add-prog-produto-select').val('');
    $('#add-prog-produto-info').addClass('d-none');
    $('#add-prog-linha').html('<option value="">Selecione um produto primeiro</option>').prop('disabled', true);
    $('#add-prog-autocomplete-list').html('').hide();
    $('#btn-salvar-programacao').prop('disabled', false).html('<i class="fas fa-save me-1"></i>Salvar Programação');
    ocultarAlerta();
    produtoSelecionado = null;
    linhasDisponiveis = [];

    // Definir data padrão como hoje
    const hoje = new Date().toISOString().split('T')[0];
    $('#add-prog-data').val(hoje);
}

/**
 * Mostra alerta no modal
 */
function mostrarAlerta(mensagem, tipo) {
    const $alert = $('#add-prog-alert');
    $alert.removeClass('d-none alert-success alert-warning alert-danger alert-info')
        .addClass(`alert-${tipo}`)
        .html(`<i class="fas fa-${tipo === 'success' ? 'check-circle' : tipo === 'danger' ? 'exclamation-circle' : 'exclamation-triangle'} me-2"></i>${mensagem}`);
}

/**
 * Oculta alerta
 */
function ocultarAlerta() {
    $('#add-prog-alert').addClass('d-none');
}

})(); // ✅ Fecha IIFE (Immediately Invoked Function Expression)
