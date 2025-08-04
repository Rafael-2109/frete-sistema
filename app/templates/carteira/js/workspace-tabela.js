/**
 * 🎯 WORKSPACE TABELA DE PRODUTOS
 * Módulo responsável pela renderização e interação da tabela de produtos
 */

class WorkspaceTabela {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Workspace Tabela inicializado');
    }

    /**
     * 🎯 RENDERIZAR TABELA DE PRODUTOS
     * Remove Est.Exp, adiciona Prod.Hoje, alinha colunas
     */
    renderizarTabelaProdutos(produtos) {
        let html = `
            <div class="table-responsive">
                <table class="table table-sm table-hover workspace-produtos-table">
                    <thead class="table-dark">
                        <tr>
                            <th width="30px">
                                <input type="checkbox" class="form-check-input" id="select-all-produtos" 
                                       title="Selecionar todos os produtos">
                            </th>
                            <th>Produto</th>
                            <th>Qtd/Saldo</th>
                            <th>Valor</th>
                            <th>Peso</th>
                            <th>Pallet</th>
                            <th class="text-center">Est.Hoje</th>
                            <th class="text-center">Est.Min.D+7</th>
                            <th class="text-center">Prod.Hoje</th>
                            <th>Disponível</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        produtos.forEach(produto => {
            const statusDisponibilidade = this.calcularStatusDisponibilidade(produto);
            const saldoDisponivel = this.calcularSaldoDisponivel(produto);
            const producaoHoje = produto.producao_hoje || 0;

            html += `
                <tr class="produto-origem" 
                    data-produto="${produto.cod_produto}"
                    data-qtd-pedido="${produto.qtd_pedido}">
                    
                    <td class="text-center">
                        <input type="checkbox" class="form-check-input produto-checkbox" 
                               data-produto="${produto.cod_produto}"
                               title="Selecionar este produto">
                    </td>
                    
                    <td>
                        <div class="produto-info">
                            <strong class="text-primary">${produto.cod_produto}</strong>
                            <br><small class="text-muted">${produto.nome_produto || ''}</small>
                        </div>
                    </td>
                    
                    <td class="text-end">
                        <div class="input-group input-group-sm" style="max-width: 140px;">
                            <input type="number" 
                                   class="form-control form-control-sm text-end qtd-editavel" 
                                   value="${Math.floor(saldoDisponivel.qtdEditavel)}"
                                   min="0"
                                   max="${Math.floor(saldoDisponivel.qtdEditavel)}"
                                   step="1"
                                   data-produto="${produto.cod_produto}"
                                   data-qtd-original="${Math.floor(produto.qtd_pedido)}"
                                   data-qtd-saldo="${Math.floor(saldoDisponivel.qtdEditavel)}"
                                   oninput="workspace.atualizarQuantidadeProduto(this)"
                                   title="Quantidade editável para separação parcial (apenas números inteiros)">
                            <span class="input-group-text text-xs" 
                                  title="Saldo disponível: ${this.formatarQuantidade(saldoDisponivel.qtdEditavel)} de ${this.formatarQuantidade(produto.qtd_pedido)} do pedido"
                                  style="font-size: 0.7rem;">
                                /${Math.floor(saldoDisponivel.qtdEditavel)}
                            </span>
                        </div>
                    </td>
                    
                    <td class="text-end" id="valor-${produto.cod_produto}">
                        <strong class="text-success valor-calculada">${this.formatarMoeda(saldoDisponivel.qtdEditavel * (produto.preco_unitario || 0))}</strong>
                        <br><small class="text-muted">Unit: ${this.formatarMoeda(produto.preco_unitario || 0)}</small>
                    </td>
                    
                    <td class="text-end" id="peso-${produto.cod_produto}">
                        <strong class="text-info peso-calculado">${this.formatarPeso(saldoDisponivel.qtdEditavel * (produto.peso_unitario || 0))}</strong>
                        <br><small class="text-muted">Unit: ${this.formatarPeso(produto.peso_unitario || 0)}</small>
                    </td>
                    
                    <td class="text-end" id="pallet-${produto.cod_produto}">
                        <strong class="text-warning pallet-calculado">${this.formatarPallet(saldoDisponivel.qtdEditavel / (produto.palletizacao || 1))}</strong>
                        <br><small class="text-muted">PLT: ${this.formatarPallet(produto.palletizacao || 1)}</small>
                    </td>
                    
                    <td class="text-center">
                        <span class="badge ${this.getEstoqueHojeBadgeClass(produto.estoque_hoje)}"
                              title="Estoque disponível hoje">
                            ${this.formatarQuantidade(produto.estoque_hoje || 0)}
                        </span>
                    </td>
                    
                    <td class="text-center">
                        <span class="badge ${this.getEstoqueMinimoBadgeClass(produto.menor_estoque_7d)}"
                              title="Menor estoque projetado nos próximos 7 dias">
                            ${this.formatarQuantidade(produto.menor_estoque_7d || 0)}
                        </span>
                    </td>
                    
                    <td class="text-center">
                        <span class="badge ${this.getProducaoHojeBadgeClass(producaoHoje)}"
                              title="Quantidade programada para produzir hoje">
                            ${this.formatarQuantidade(producaoHoje)}
                        </span>
                    </td>
                    
                    <td>
                        <span class="badge ${statusDisponibilidade.class}" title="${statusDisponibilidade.tooltip}">
                            ${statusDisponibilidade.texto}
                        </span>
                        <br><small class="text-muted">${statusDisponibilidade.detalhes}</small>
                    </td>
                    
                    <td>
                        <div class="btn-group-vertical btn-group-sm">
                            <button class="btn btn-outline-info btn-xs mb-1" 
                                    onclick="workspace.abrirCardex('${produto.cod_produto}')"
                                    title="Ver projeção de estoque D+0 a D+28">
                                <i class="fas fa-chart-line me-1"></i>Cardex
                            </button>
                            <button class="btn btn-outline-secondary btn-xs" 
                                    onclick="workspace.resetarQuantidadeProduto('${produto.cod_produto}')"
                                    title="Restaurar quantidade original do pedido">
                                <i class="fas fa-undo me-1"></i>Reset
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        return html;
    }

    /**
     * 🎯 OBTER PRODUÇÃO HOJE
     * Busca quantidade programada para produzir hoje na classe SaldoEstoque
     */
    obterProducaoHoje(produto) {
        try {
            // Se o produto tem resumo de estoque, usar a projeção D0
            if (produto.resumo_estoque && produto.resumo_estoque.projecao_29_dias) {
                const hoje = produto.resumo_estoque.projecao_29_dias[0]; // D0
                return hoje ? hoje.producao_programada || 0 : 0;
            }

            // Fallback: retornar 0 se não houver dados
            return 0;

        } catch (error) {
            console.error('Erro ao obter produção hoje:', error);
            return 0;
        }
    }

    /**
     * 🎯 CLASSES CSS PARA BADGES
     */
    getEstoqueHojeBadgeClass(estoque) {
        if (estoque <= 0) return 'bg-danger text-white';
        if (estoque < 10) return 'bg-warning text-dark';
        if (estoque < 50) return 'bg-info text-white';
        return 'bg-success text-white';
    }

    getEstoqueMinimoBadgeClass(estoqueMinimo) {
        if (estoqueMinimo <= 0) return 'bg-danger text-white';
        if (estoqueMinimo < 5) return 'bg-warning text-dark';
        return 'bg-secondary text-white';
    }

    getProducaoHojeBadgeClass(producao) {
        if (producao <= 0) return 'bg-light text-dark';
        if (producao < 10) return 'bg-primary text-white';
        return 'bg-success text-white';
    }

    /**
     * 🎯 CÁLCULOS DE STATUS E DISPONIBILIDADE
     */
    calcularStatusDisponibilidade(produto) {
        try {
            const qtdPedido = produto.qtd_pedido || 0;
            const estoqueHoje = produto.estoque_hoje || 0;

            if (estoqueHoje >= qtdPedido) {
                return {
                    class: 'bg-success text-white',
                    texto: 'DISPONÍVEL',
                    detalhes: 'Estoque suficiente',
                    tooltip: `Estoque: ${this.formatarQuantidade(estoqueHoje)}, Pedido: ${this.formatarQuantidade(qtdPedido)}`
                };
            } else if (estoqueHoje > 0) {
                return {
                    class: 'bg-warning text-dark',
                    texto: 'PARCIAL',
                    detalhes: `Falta: ${this.formatarQuantidade(qtdPedido - estoqueHoje)}`,
                    tooltip: `Disponível parcialmente. Estoque: ${this.formatarQuantidade(estoqueHoje)}`
                };
            } else {
                return {
                    class: 'bg-danger text-white',
                    texto: 'INDISPONÍVEL',
                    detalhes: 'Sem estoque',
                    tooltip: 'Produto indisponível no momento'
                };
            }
        } catch (error) {
            return {
                class: 'bg-secondary text-white',
                texto: 'ERRO',
                detalhes: 'Erro no cálculo',
                tooltip: 'Erro ao calcular disponibilidade'
            };
        }
    }

    calcularSaldoDisponivel(produto) {
        // Delegar para o WorkspaceQuantidades se disponível
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.calcularSaldoDisponivel(produto);
        }

        // Fallback caso WorkspaceQuantidades não esteja disponível
        try {
            const qtdPedido = produto.qtd_pedido || produto.qtd_produto_pedido || 0;
            const qtdSeparacoes = produto.qtd_separacoes || 0;
            const qtdPreSeparacoes = produto.qtd_pre_separacoes || 0;

            // Saldo disponível = Qtd Pedido - (Separações + Pré-Separações)
            const qtdEditavel = qtdPedido - qtdSeparacoes - qtdPreSeparacoes;

            return {
                qtdEditavel: Math.max(0, qtdEditavel), // Nunca negativo
                qtdSeparacoes: qtdSeparacoes,
                qtdPreSeparacoes: qtdPreSeparacoes,
                qtdIndisponivel: Math.max(0, -qtdEditavel)
            };
        } catch (error) {
            console.error('Erro ao calcular saldo disponível:', error);
            return {
                qtdEditavel: produto.qtd_pedido || produto.qtd_produto_pedido || 0,
                qtdSeparacoes: 0,
                qtdPreSeparacoes: 0,
                qtdIndisponivel: 0
            };
        }
    }

    /**
     * 🎯 MÉTODOS DE FORMATAÇÃO (compatíveis com workspace-core.js)
     */
    formatarMoeda(valor) {
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarQuantidade(qtd) {
        if (!qtd) return '0';
        return Math.floor(qtd).toLocaleString('pt-BR');
    }

    formatarPeso(peso) {
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }
}

// Disponibilizar globalmente
window.WorkspaceTabela = WorkspaceTabela;