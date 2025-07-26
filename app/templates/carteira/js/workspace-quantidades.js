/**
 * 🎯 WORKSPACE QUANTIDADES
 * Módulo responsável por cálculos e atualizações de quantidades
 */

class WorkspaceQuantidades {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Workspace Quantidades inicializado');
    }

    /**
     * 🎯 CALCULAR SALDO DISPONÍVEL DO PRODUTO
     * Fórmula: Qtd Pedido - Qtd em Separações - Qtd em Pré-Separações
     */
    calcularSaldoDisponivel(produto) {
        const qtdPedido = produto.qtd_pedido || 0;
        const qtdSeparacoes = produto.qtd_separacoes || 0; // Vindas da API
        const qtdPreSeparacoes = produto.qtd_pre_separacoes || 0; // Vindas da API
        
        // Calcular também baseado nos lotes locais (workspace atual)
        let qtdPreSeparacoesLocal = 0;
        if (window.workspace && window.workspace.preSeparacoes) {
            window.workspace.preSeparacoes.forEach(loteData => {
                const produtoNoLote = loteData.produtos.find(p => p.codProduto === produto.cod_produto);
                if (produtoNoLote) {
                    qtdPreSeparacoesLocal += produtoNoLote.quantidade || 0;
                }
            });
        }
        
        // Calcular separações confirmadas locais
        let qtdSeparacoesConfirmadas = 0;
        if (window.workspace && window.workspace.separacoesConfirmadas) {
            window.workspace.separacoesConfirmadas.forEach(separacao => {
                const produtoNaSeparacao = separacao.produtos.find(p => p.cod_produto === produto.cod_produto);
                if (produtoNaSeparacao) {
                    qtdSeparacoesConfirmadas += produtoNaSeparacao.qtd_saldo || 0;
                }
            });
        }
        
        // Usar o maior valor entre API e local para pré-separações
        const qtdPreSeparacoesTotal = Math.max(qtdPreSeparacoes, qtdPreSeparacoesLocal);
        
        // Usar o maior valor entre API e local para separações
        const qtdSeparacoesTotal = Math.max(qtdSeparacoes, qtdSeparacoesConfirmadas);
        
        // Saldo disponível = Qtd Pedido - (Separações + Pré-Separações)
        const qtdEditavel = qtdPedido - qtdSeparacoesTotal - qtdPreSeparacoesTotal;
        
        return {
            qtdEditavel: Math.max(0, qtdEditavel), // Nunca negativo
            qtdSeparacoes: qtdSeparacoesTotal,
            qtdPreSeparacoes: qtdPreSeparacoesTotal,
            qtdIndisponivel: Math.max(0, -qtdEditavel), // Se negativo, é indisponível
            temRestricao: qtdSeparacoesTotal > 0 || qtdPreSeparacoesTotal > 0
        };
    }

    /**
     * 🎯 ATUALIZAR SALDO APÓS ADICIONAR AO LOTE
     */
    atualizarSaldoAposAdicao(codProduto, quantidadeAdicionada) {
        const input = document.querySelector(`input[data-produto="${codProduto}"]`);
        if (input) {
            // Buscar dados do produto no workspace
            const dadosProduto = window.workspace?.dadosProdutos?.get(codProduto);
            if (dadosProduto) {
                // Recalcular saldo completo considerando todas as pré-separações
                const saldoCalculado = this.calcularSaldoDisponivel(dadosProduto);
                const novoSaldo = Math.floor(saldoCalculado.qtdEditavel);
                
                // Atualizar dataset
                input.dataset.qtdSaldo = novoSaldo;
                input.max = novoSaldo;
                
                // Atualizar o valor editável para o novo saldo
                input.value = novoSaldo;
                
                // Atualizar o span de saldo
                const spanSaldo = input.nextElementSibling;
                if (spanSaldo && spanSaldo.classList.contains('input-group-text')) {
                    spanSaldo.textContent = `/${novoSaldo}`;
                    
                    // Adicionar feedback visual
                    spanSaldo.classList.add('text-warning');
                    setTimeout(() => {
                        spanSaldo.classList.remove('text-warning');
                    }, 1000);
                }
                
                // Atualizar valores calculados
                this.atualizarQuantidadeProduto(input);
                
                console.log(`✅ Saldo atualizado: ${codProduto} = ${novoSaldo} (removido ${quantidadeAdicionada})`);
            }
        }
    }
    
    /**
     * 🎯 ATUALIZAR SALDO APÓS REMOVER DO LOTE
     */
    atualizarSaldoAposRemocao(codProduto, quantidadeRemovida) {
        const input = document.querySelector(`input[data-produto="${codProduto}"]`);
        if (input) {
            const saldoAtual = parseInt(input.dataset.qtdSaldo) || 0;
            const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
            const novoSaldo = Math.min(qtdOriginal, saldoAtual + quantidadeRemovida);
            
            // Atualizar dataset
            input.dataset.qtdSaldo = novoSaldo;
            input.max = novoSaldo;
            
            // Atualizar o span de saldo
            const spanSaldo = input.nextElementSibling;
            if (spanSaldo && spanSaldo.classList.contains('input-group-text')) {
                spanSaldo.textContent = `/${novoSaldo}`;
                
                // Adicionar feedback visual
                spanSaldo.classList.add('text-success');
                setTimeout(() => {
                    spanSaldo.classList.remove('text-success');
                }, 1000);
            }
            
            console.log(`✅ Saldo restaurado: ${codProduto} = ${novoSaldo} (devolvido ${quantidadeRemovida})`);
        }
    }
    
    /**
     * 🎯 ATUALIZAR QUANTIDADE DE PRODUTO NA TABELA
     */
    atualizarQuantidadeProduto(input) {
        try {
            const codProduto = input.dataset.produto;
            const novaQtd = parseInt(input.value) || 0;
            const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
            const qtdSaldo = parseInt(input.dataset.qtdSaldo) || 0;
            
            // Validar limites
            if (novaQtd < 0) {
                input.value = 0;
                return;
            }
            
            if (novaQtd > qtdSaldo) {
                input.value = qtdSaldo;
                alert(`Quantidade máxima disponível: ${qtdSaldo}`);
                return;
            }
            
            // Buscar dados do produto
            const dadosProduto = window.workspace ? 
                window.workspace.dadosProdutos.get(codProduto) : null;
            
            if (!dadosProduto) {
                console.error('Dados do produto não encontrados:', codProduto);
                return;
            }
            
            // Atualizar colunas calculadas na tabela
            this.atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto);
            
            // Recalcular totais dos lotes que contêm este produto
            this.recalcularTotaisLotesComProduto(codProduto);
            
            console.log(`✅ Quantidade atualizada: ${codProduto} = ${novaQtd}`);
            
        } catch (error) {
            console.error('Erro ao atualizar quantidade:', error);
        }
    }

    /**
     * 🎯 ATUALIZAR COLUNAS CALCULADAS
     */
    atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto) {
        try {
            // Atualizar valor
            const valorElement = document.getElementById(`valor-${codProduto}`);
            if (valorElement) {
                const valorCalculado = novaQtd * (dadosProduto.preco_unitario || 0);
                const valorCalculadoElement = valorElement.querySelector('.valor-calculada');
                if (valorCalculadoElement) {
                    valorCalculadoElement.textContent = this.formatarMoeda(valorCalculado);
                }
            }
            
            // Atualizar peso
            const pesoElement = document.getElementById(`peso-${codProduto}`);
            if (pesoElement) {
                const pesoCalculado = novaQtd * (dadosProduto.peso_unitario || 0);
                const pesoCalculadoElement = pesoElement.querySelector('.peso-calculado');
                if (pesoCalculadoElement) {
                    pesoCalculadoElement.textContent = this.formatarPeso(pesoCalculado);
                }
            }
            
            // Atualizar pallet
            const palletElement = document.getElementById(`pallet-${codProduto}`);
            if (palletElement) {
                const palletCalculado = novaQtd / (dadosProduto.palletizacao || 1);
                const palletCalculadoElement = palletElement.querySelector('.pallet-calculado');
                if (palletCalculadoElement) {
                    palletCalculadoElement.textContent = this.formatarPallet(palletCalculado);
                }
            }
            
        } catch (error) {
            console.error('Erro ao atualizar colunas calculadas:', error);
        }
    }

    /**
     * 🎯 RECALCULAR TOTAIS DOS LOTES
     */
    recalcularTotaisLotesComProduto(codProduto) {
        try {
            if (!window.workspace || !window.workspaceLotes) return;
            
            // Encontrar lotes que contêm este produto
            window.workspace.preSeparacoes.forEach((loteData, loteId) => {
                const produtoNoLote = loteData.produtos.find(p => p.codProduto === codProduto);
                if (produtoNoLote) {
                    // Recalcular totais do lote
                    if (window.workspaceLotes.atualizarTotaisLote) {
                        window.workspaceLotes.atualizarTotaisLote(loteId);
                    }
                }
            });
            
        } catch (error) {
            console.error('Erro ao recalcular totais dos lotes:', error);
        }
    }

    /**
     * 🎯 RESETAR QUANTIDADE DO PRODUTO
     */
    resetarQuantidadeProduto(codProduto) {
        try {
            const input = document.querySelector(`input[data-produto="${codProduto}"]`);
            if (input) {
                const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
                input.value = qtdOriginal;
                
                // Disparar evento de mudança
                const event = new Event('change', { bubbles: true });
                input.dispatchEvent(event);
            }
        } catch (error) {
            console.error('Erro ao resetar quantidade:', error);
        }
    }

    /**
     * 🎯 CALCULAR STATUS DE DISPONIBILIDADE
     */
    calcularStatusDisponibilidade(produto) {
        if (produto.estoque_hoje >= produto.qtd_pedido) {
            return { classe: 'bg-success', texto: 'Hoje' };
        }
        
        if (produto.data_disponibilidade) {
            const diasAte = this.calcularDiasAte(produto.data_disponibilidade);
            if (diasAte <= 7) {
                return { classe: 'bg-warning', texto: `${diasAte}d` };
            }
        }
        
        return { classe: 'bg-danger', texto: 'Sem est.' };
    }

    /**
     * 🎯 CALCULAR DIAS ATÉ DATA
     */
    calcularDiasAte(dataStr) {
        const hoje = new Date();
        const dataTarget = new Date(dataStr);
        const diffTime = dataTarget - hoje;
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }

    /**
     * 🎯 MÉTODOS DE FORMATAÇÃO
     */
    formatarMoeda(valor) {
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
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
window.WorkspaceQuantidades = WorkspaceQuantidades;