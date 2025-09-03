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
            // Garantir que produto tem estrutura mínima necessária
            if (!produto || !produto.cod_produto) {
                console.warn('⚠️ Produto inválido ou sem código:', produto);
                return; // Pular este produto
            }
            
            // Se não há estoque nem produção, mostrar INDISPONÍVEL em vez de CARREGANDO
            let statusDisponibilidade = this.calcularStatusDisponibilidade(produto);
            if (!statusDisponibilidade) {
                // Se estoque é 0 e não há produção, não está carregando, está indisponível
                const temEstoque = (produto.estoque_hoje ?? produto.estoque ?? 0) > 0;
                const temProducao = (produto.producao_hoje ?? 0) > 0;
                const temDisponibilidade = produto.data_disponibilidade && produto.data_disponibilidade !== 'Sem previsão';
                
                if (!temEstoque && !temProducao && !temDisponibilidade) {
                    statusDisponibilidade = {
                        class: 'bg-danger text-white',
                        texto: 'INDISPONÍVEL',
                        detalhes: 'Sem estoque',
                        tooltip: 'Produto indisponível no momento'
                    };
                } else {
                    statusDisponibilidade = {
                        class: 'bg-secondary text-white',
                        texto: 'CARREGANDO...',
                        detalhes: 'Aguardando dados',
                        tooltip: 'Dados de estoque sendo carregados'
                    };
                }
            }
            
            const saldoDisponivel = this.calcularSaldoDisponivel(produto) || {
                qtdEditavel: produto.qtd_pedido || produto.qtd_saldo_produto_pedido || 0,
                qtdSeparacoes: 0,
                qtdPreSeparacoes: 0,
                qtdIndisponivel: 0
            };
            
            const producaoHoje = produto.producao_hoje || 0;
            
            // Garantir que valores numéricos não sejam undefined
            const estoqueHoje = produto.estoque_hoje ?? 0;
            const menorEstoque7d = produto.menor_estoque_7d ?? produto.menor_estoque_produto_d7 ?? 0;
            const precoUnitario = produto.preco_unitario ?? produto.preco_produto_pedido ?? 0;
            const pesoUnitario = produto.peso_unitario ?? 0;
            const palletizacao = produto.palletizacao ?? 1000;

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
                        <strong class="text-success valor-calculada">${this.formatarMoeda(saldoDisponivel.qtdEditavel * precoUnitario)}</strong>
                        <br><small class="text-muted">Unit: ${this.formatarMoeda(precoUnitario)}</small>
                    </td>
                    
                    <td class="text-end" id="peso-${produto.cod_produto}">
                        <strong class="text-info peso-calculado">${this.formatarPeso(saldoDisponivel.qtdEditavel * pesoUnitario)}</strong>
                        <br><small class="text-muted">Unit: ${this.formatarPeso(pesoUnitario)}</small>
                    </td>
                    
                    <td class="text-end" id="pallet-${produto.cod_produto}">
                        <strong class="text-warning pallet-calculado">${this.formatarPallet(saldoDisponivel.qtdEditavel / palletizacao)}</strong>
                        <br><small class="text-muted">PLT: ${this.formatarPallet(palletizacao)}</small>
                    </td>
                    
                    <td class="text-center">
                        <span class="badge ${this.getEstoqueHojeBadgeClass(estoqueHoje)}"
                              title="Estoque disponível hoje">
                            ${this.formatarQuantidade(estoqueHoje)}
                        </span>
                    </td>
                    
                    <td class="text-center">
                        <span class="badge ${this.getEstoqueMinimoBadgeClass(menorEstoque7d)}"
                              title="Menor estoque projetado nos próximos 7 dias">
                            ${this.formatarQuantidade(menorEstoque7d)}
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
     * 🎯 DELEGAR CÁLCULO DE STATUS DE DISPONIBILIDADE
     * Usa workspace-quantidades para cálculo completo
     */
    calcularStatusDisponibilidade(produto) {
        try {
            // Verificar se produto é válido
            if (!produto) {
                console.warn('⚠️ calcularStatusDisponibilidade chamado com produto undefined');
                return null;
            }
            
            // Debug: verificar dados do produto
            console.log('📊 DEBUG calcularStatusDisponibilidade:', {
                cod_produto: produto.cod_produto,
                qtd_pedido: produto.qtd_pedido,
                estoque_hoje: produto.estoque_hoje,
                data_disponibilidade: produto.data_disponibilidade,
                qtd_disponivel: produto.qtd_disponivel,
                workspaceQuantidades_existe: !!window.workspaceQuantidades
            });
            
            // Delegar para workspace-quantidades se disponível
            if (window.workspaceQuantidades) {
                const resultado = window.workspaceQuantidades.calcularStatusDisponibilidade(produto);
                console.log('📊 Resultado de workspaceQuantidades:', resultado);
                return resultado;
            }
            
            // Fallback simplificado se workspace-quantidades não estiver disponível
            const qtdPedido = produto.qtd_pedido || produto.qtd_saldo_produto_pedido || 0;
            const estoqueHoje = produto.estoque_hoje ?? produto.estoque ?? 0;

            if (estoqueHoje >= qtdPedido) {
                return {
                    class: 'bg-success text-white',
                    texto: 'DISPONÍVEL',
                    detalhes: `${this.formatarQuantidade(estoqueHoje)} unidades`,
                    tooltip: `Estoque: ${this.formatarQuantidade(estoqueHoje)}, Pedido: ${this.formatarQuantidade(qtdPedido)}`
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
            console.error('Erro ao calcular disponibilidade:', error, produto);
            return {
                class: 'bg-secondary text-white',
                texto: 'ERRO',
                detalhes: 'Erro no cálculo',
                tooltip: 'Erro ao calcular disponibilidade'
            };
        }
    }

    /**
     * 🎯 DELEGAR CÁLCULO DE SALDO DISPONÍVEL
     * Já está delegando corretamente para WorkspaceQuantidades
     */
    calcularSaldoDisponivel(produto) {
        try {
            // Verificar se produto é válido
            if (!produto) {
                console.warn('⚠️ calcularSaldoDisponivel chamado com produto undefined');
                return {
                    qtdEditavel: 0,
                    qtdSeparacoes: 0,
                    qtdPreSeparacoes: 0,
                    qtdIndisponivel: 0
                };
            }
            
            // Já delega para o WorkspaceQuantidades se disponível
            if (window.workspaceQuantidades) {
                const resultado = window.workspaceQuantidades.calcularSaldoDisponivel(produto);
                if (resultado) return resultado;
            }

            // Fallback caso WorkspaceQuantidades não esteja disponível
            const qtdPedido = produto.qtd_pedido || produto.qtd_produto_pedido || 0;
            const qtdSeparacoes = produto.qtd_separacoes || 0;
            const qtdPreSeparacoes = produto.qtd_pre_separacoes || 0;
            const qtdEditavel = qtdPedido - qtdSeparacoes - qtdPreSeparacoes;

            return {
                qtdEditavel: Math.max(0, qtdEditavel),
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
     * 🎯 DELEGAÇÃO DE FORMATAÇÃO
     * Todas as formatações são delegadas para workspace-quantidades
     */
    formatarMoeda(valor) {
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarMoeda(valor);
        }
        // Fallback se workspace-quantidades não estiver disponível
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarQuantidade(qtd) {
        if (window.workspaceQuantidades) {
            // Usar formatação do workspace-quantidades mas sem decimais
            const formatted = window.workspaceQuantidades.formatarQuantidade(qtd);
            return formatted ? formatted.split(',')[0] : '0';
        }
        // Fallback
        if (qtd === null || qtd === undefined || isNaN(qtd)) return '0';
        const numero = parseFloat(qtd);
        if (isNaN(numero)) return '0';
        return Math.floor(numero).toLocaleString('pt-BR');
    }

    formatarPeso(peso) {
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarPeso(peso);
        }
        // Fallback
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarPallet(pallet);
        }
        // Fallback
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }
    
    formatarData(data) {
        if (!data) return '';
        // Se já está no formato dd/mm/yyyy, retornar como está
        if (data.includes('/')) return data;
        // Converter de yyyy-mm-dd para dd/mm/yyyy
        const [ano, mes, dia] = data.split('-');
        return `${dia}/${mes}/${ano}`;
    }
    
    calcularDiasAteData(dataFutura) {
        try {
            // Garantir formato correto da data (yyyy-mm-dd)
            const hoje = new Date();
            hoje.setHours(0, 0, 0, 0);
            hoje.setMinutes(0);
            hoje.setSeconds(0);
            hoje.setMilliseconds(0);
            
            // Criar data futura garantindo timezone correto
            const [ano, mes, dia] = dataFutura.split('-');
            const futuro = new Date(parseInt(ano), parseInt(mes) - 1, parseInt(dia));
            futuro.setHours(0, 0, 0, 0);
            
            const diffTime = futuro.getTime() - hoje.getTime();
            const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
            
            return Math.max(0, diffDays);
        } catch (error) {
            console.error('Erro ao calcular dias:', error, dataFutura);
            return 0;
        }
    }
}

// Disponibilizar globalmente
window.WorkspaceTabela = WorkspaceTabela;