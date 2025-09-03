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
            console.log(`   🔍 DEBUG calcularSaldoDisponivel - Verificando pré-separações locais:`);
            console.log(`      - Total de lotes: ${window.workspace.preSeparacoes.size}`);
            console.log(`      - Procurando produto: ${produto.cod_produto}`);

            window.workspace.preSeparacoes.forEach((loteData, loteId) => {
                console.log(`      - Lote ${loteId}:`, loteData.produtos);
                const produtoNoLote = loteData.produtos.find(p =>
                    p.codProduto === produto.cod_produto || p.cod_produto === produto.cod_produto
                );
                if (produtoNoLote) {
                    console.log(`         ✓ Produto encontrado no lote:`, produtoNoLote);
                    qtdPreSeparacoesLocal += produtoNoLote.quantidade || 0;
                }
            });
            console.log(`      - Total pré-separações locais: ${qtdPreSeparacoesLocal}`);
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
        console.log(`🔍 DEBUG atualizarSaldoAposAdicao - Início`);
        console.log(`   - codProduto: ${codProduto}`);
        console.log(`   - quantidadeAdicionada: ${quantidadeAdicionada}`);

        // Seletor mais específico para garantir que pegue o input correto
        const input = document.querySelector(`input.qtd-editavel[data-produto="${codProduto}"]`);
        if (input) {
            console.log(`   - Valor atual do input: ${input.value}`);
            console.log(`   - qtdOriginal: ${input.dataset.qtdOriginal}`);
            console.log(`   - qtdSaldo atual: ${input.dataset.qtdSaldo}`);
            console.log(`   - Input encontrado:`, input);

            // Buscar dados do produto no workspace
            const dadosProduto = window.workspace?.dadosProdutos?.get(codProduto);
            if (dadosProduto) {
                console.log(`   - Dados do produto encontrados`);
                console.log(`   - qtd_pedido: ${dadosProduto.qtd_pedido}`);

                // Recalcular saldo completo considerando todas as pré-separações
                const saldoCalculado = this.calcularSaldoDisponivel(dadosProduto);
                const novoSaldo = Math.floor(saldoCalculado.qtdEditavel);

                console.log(`   - Saldo calculado:`);
                console.log(`     - qtdEditavel: ${saldoCalculado.qtdEditavel}`);
                console.log(`     - qtdPreSeparacoes: ${saldoCalculado.qtdPreSeparacoes}`);
                console.log(`     - qtdSeparacoes: ${saldoCalculado.qtdSeparacoes}`);
                console.log(`   - Novo saldo (novoSaldo): ${novoSaldo}`);

                // Atualizar dataset
                input.dataset.qtdSaldo = novoSaldo;
                input.max = novoSaldo;

                console.log(`   - Atualizando input.value de ${input.value} para ${novoSaldo}`);

                // FORÇAR atualização do valor - usar setAttribute também
                input.value = novoSaldo;
                input.setAttribute('value', novoSaldo);

                // Disparar evento change para garantir que outros listeners sejam notificados
                input.dispatchEvent(new Event('input', { bubbles: true }));

                console.log(`   - Input.value após atualização: ${input.value}`);

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

                // NÃO chamar atualizarQuantidadeProduto aqui para evitar loop
                // A atualização dos valores calculados já será feita pelo evento 'input'
                console.log(`   - Valores calculados serão atualizados pelo evento input`);

                console.log(`✅ Saldo atualizado: ${codProduto} = ${novoSaldo} (removido ${quantidadeAdicionada})`);

                // DEBUG: Verificar se algo sobrescreve o valor depois
                const valorEsperado = novoSaldo;
                setTimeout(() => {
                    const inputDepois = document.querySelector(`input.qtd-editavel[data-produto="${codProduto}"]`);
                    if (inputDepois && inputDepois.value != valorEsperado) {
                        console.error(`❌ VALOR FOI SOBRESCRITO!`);
                        console.error(`   - Esperado: ${valorEsperado}`);
                        console.error(`   - Atual: ${inputDepois.value}`);
                        console.error(`   - Stack trace:`, new Error().stack);

                        // FORÇAR correção novamente
                        inputDepois.value = valorEsperado;
                        inputDepois.setAttribute('value', valorEsperado);
                    }
                }, 50);
            } else {
                console.log(`   ❌ Dados do produto NÃO encontrados`);
            }
        } else {
            console.log(`   ❌ Input NÃO encontrado para o produto ${codProduto}`);
        }
        console.log(`🔍 DEBUG atualizarSaldoAposAdicao - Fim`);
    }

    /**
     * 🎯 ATUALIZAR SALDO APÓS REMOVER DO LOTE
     */
    atualizarSaldoAposRemocao(codProduto, quantidadeRemovida) {
        console.log(`🔍 DEBUG atualizarSaldoAposRemocao - Início`);
        console.log(`   - codProduto: ${codProduto}`);
        console.log(`   - quantidadeRemovida: ${quantidadeRemovida}`);

        // Usar o mesmo seletor específico
        const input = document.querySelector(`input.qtd-editavel[data-produto="${codProduto}"]`);
        if (input) {
            console.log(`   - Valor atual do input: ${input.value}`);
            console.log(`   - qtdSaldo atual: ${input.dataset.qtdSaldo}`);

            // Buscar dados do produto no workspace para recalcular corretamente
            const dadosProduto = window.workspace?.dadosProdutos?.get(codProduto);
            if (dadosProduto) {
                // Recalcular saldo completo considerando todas as pré-separações
                const saldoCalculado = this.calcularSaldoDisponivel(dadosProduto);
                const novoSaldo = Math.floor(saldoCalculado.qtdEditavel);

                console.log(`   - Saldo recalculado após remoção:`);
                console.log(`     - qtdEditavel: ${saldoCalculado.qtdEditavel}`);
                console.log(`     - qtdPreSeparacoes: ${saldoCalculado.qtdPreSeparacoes}`);
                console.log(`   - Novo saldo: ${novoSaldo}`);

                // Atualizar dataset
                input.dataset.qtdSaldo = novoSaldo;
                input.max = novoSaldo;

                // ATUALIZAR O VALOR DO CAMPO
                input.value = novoSaldo;
                input.setAttribute('value', novoSaldo);

                // Disparar evento para atualizar valores calculados
                input.dispatchEvent(new Event('input', { bubbles: true }));

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

                // Verificar se algo sobrescreve depois
                const valorEsperado = novoSaldo;
                setTimeout(() => {
                    const inputDepois = document.querySelector(`input.qtd-editavel[data-produto="${codProduto}"]`);
                    if (inputDepois && inputDepois.value != valorEsperado) {
                        console.error(`❌ VALOR FOI SOBRESCRITO após remoção!`);
                        console.error(`   - Esperado: ${valorEsperado}`);
                        console.error(`   - Atual: ${inputDepois.value}`);

                        // FORÇAR correção
                        inputDepois.value = valorEsperado;
                        inputDepois.setAttribute('value', valorEsperado);
                    }
                }, 50);
            } else {
                // Fallback se não encontrar dados do produto
                const saldoAtual = parseInt(input.dataset.qtdSaldo) || 0;
                const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
                const novoSaldo = Math.min(qtdOriginal, saldoAtual + quantidadeRemovida);

                input.dataset.qtdSaldo = novoSaldo;
                input.max = novoSaldo;
                input.value = novoSaldo;
                input.setAttribute('value', novoSaldo);

                console.log(`✅ Saldo restaurado (fallback): ${codProduto} = ${novoSaldo}`);
            }
        } else {
            console.log(`   ❌ Input NÃO encontrado para o produto ${codProduto}`);
        }
        console.log(`🔍 DEBUG atualizarSaldoAposRemocao - Fim`);
    }

    /**
     * 🎯 ATUALIZAR QUANTIDADE DE PRODUTO NA TABELA
     */
    atualizarQuantidadeProduto(input) {
        try {
            console.log(`🔍 DEBUG atualizarQuantidadeProduto - Início`);
            const codProduto = input.dataset.produto;
            const novaQtd = parseInt(input.value) || 0;
            const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
            const qtdSaldo = parseInt(input.dataset.qtdSaldo) || 0;

            console.log(`   - codProduto: ${codProduto}`);
            console.log(`   - novaQtd (input.value): ${novaQtd}`);
            console.log(`   - qtdOriginal: ${qtdOriginal}`);
            console.log(`   - qtdSaldo: ${qtdSaldo}`);

            // Validar limites
            if (novaQtd < 0) {
                console.log(`   ⚠️ Quantidade negativa, ajustando para 0`);
                input.value = 0;
                return;
            }

            if (novaQtd > qtdSaldo) {
                console.log(`   ⚠️ Quantidade ${novaQtd} excede saldo ${qtdSaldo}, ajustando`);
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
        // Debug: verificar dados recebidos
        console.log('🔍 calcularStatusDisponibilidade - Dados do produto:', {
            cod_produto: produto.cod_produto,
            qtd_pedido: produto.qtd_pedido,
            qtd_saldo_produto_pedido: produto.qtd_saldo_produto_pedido,
            estoque_hoje: produto.estoque_hoje,
            estoque: produto.estoque,
            qtd_disponivel: produto.qtd_disponivel,
            data_disponibilidade: produto.data_disponibilidade
        });
        
        const qtdPedido = produto.qtd_pedido || produto.qtd_saldo_produto_pedido || 0;
        const estoqueHoje = produto.estoque_hoje ?? produto.estoque ?? 0;
        const qtdDisponivel = produto.qtd_disponivel || 0;
        
        // Se tem estoque suficiente hoje
        if (estoqueHoje >= qtdPedido) {
            console.log('✅ Estoque suficiente hoje:', estoqueHoje, '>=', qtdPedido);
            
            // Formatar data de hoje
            const hoje = new Date();
            const dia = String(hoje.getDate()).padStart(2, '0');
            const mes = String(hoje.getMonth() + 1).padStart(2, '0');
            const dataHoje = `${dia}/${mes}`;
            
            return {
                class: 'bg-success text-white',
                texto: 'HOJE',
                detalhes: `${dataHoje} (${this.formatarQuantidade(estoqueHoje)} un)`,
                tooltip: `Disponível hoje (${dataHoje}): ${this.formatarQuantidade(estoqueHoje)} unidades`
            };
        }

        // Se tem data de disponibilidade futura
        if (produto.data_disponibilidade && produto.data_disponibilidade !== 'Sem previsão') {
            console.log('📅 Data disponibilidade encontrada:', produto.data_disponibilidade);
            const diasAte = this.calcularDiasAte(produto.data_disponibilidade);
            
            // Calcular a data somando dias a hoje
            const hoje = new Date();
            const dataFutura = new Date(hoje);
            dataFutura.setDate(hoje.getDate() + diasAte);
            
            // Formatar a data para exibição (dd/mm)
            const dia = String(dataFutura.getDate()).padStart(2, '0');
            const mes = String(dataFutura.getMonth() + 1).padStart(2, '0');
            const dataFormatada = `${dia}/${mes}`;
            
            console.log(`📅 Data calculada: Hoje + ${diasAte} dias = ${dataFormatada}`);
            
            // Determinar a classe baseada nos dias
            let colorClass = 'bg-warning';
            if (diasAte <= 3) {
                colorClass = 'bg-success';
            } else if (diasAte > 7) {
                colorClass = 'bg-danger';
            }
            
            const resultado = {
                class: `${colorClass} text-white`,
                texto: `D+${diasAte}`,
                detalhes: `${dataFormatada} (${this.formatarQuantidade(qtdDisponivel)} un)`,
                tooltip: `Disponível em ${diasAte} dias (${dataFormatada}) - Quantidade: ${this.formatarQuantidade(qtdDisponivel)} unidades`
            };
            
            console.log('📊 Resultado calculado:', resultado);
            return resultado;
        }

        // Sem disponibilidade
        console.log('❌ Sem disponibilidade - data:', produto.data_disponibilidade, 'qtd:', qtdDisponivel);
        return {
            class: 'bg-danger text-white',
            texto: 'INDISPONÍVEL',
            detalhes: 'Sem previsão',
            tooltip: 'Produto sem previsão de disponibilidade'
        };
    }

    /**
     * 🎯 CALCULAR DIAS ATÉ DATA
     */
    calcularDiasAte(dataStr) {
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0); // Zerar horas para comparação de dias
        
        const dataTarget = new Date(dataStr);
        dataTarget.setHours(0, 0, 0, 0); // Zerar horas para comparação de dias
        
        const diffTime = dataTarget - hoje;
        const dias = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        // Não retornar dias negativos - mínimo é 0 (hoje)
        return Math.max(0, dias);
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

    formatarQuantidade(qtd) {
        // Verificar se é null, undefined ou NaN
        if (qtd === null || qtd === undefined || isNaN(qtd)) return '0';
        // Garantir que é um número válido
        const numero = parseFloat(qtd);
        if (isNaN(numero)) return '0';
        // Retornar com 3 decimais para quantidades precisas
        return numero.toFixed(3).replace('.', ',');
    }

    formatarPeso(valor) {
        if (!valor || isNaN(valor)) return '0';
        // Formatar com separador de milhar "." sem casa decimal
        return Math.round(valor).toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }) +' kg';
    }

    formatarPallet(valor) {
        if (!valor || isNaN(valor)) return '0,0';
        // Formatar com separador de milhar "." e 1 casa decimal ","
        return valor.toLocaleString('pt-BR', {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }) +' plt';
    }
}

// Disponibilizar globalmente
window.WorkspaceQuantidades = WorkspaceQuantidades;