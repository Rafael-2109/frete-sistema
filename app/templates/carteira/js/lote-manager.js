/**
 * 📦 GERENCIADOR DE LOTES
 * Responsável pela criação, atualização e remoção dos lotes de pré-separação
 */

class LoteManager {
    constructor(workspace) {
        this.workspace = workspace;
        this.init();
    }

    init() {
        console.log('✅ Lote Manager inicializado');
    }

    gerarNovoLoteId() {
        const hoje = new Date();
        const data = hoje.toISOString().slice(0, 10).replace(/-/g, '');
        const hora = hoje.toTimeString().slice(0, 8).replace(/:/g, '');
        const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');

        return `LOTE-${data}-${random}-${hora}`;
    }

    criarNovoLote(numPedido) {
        const loteId = this.gerarNovoLoteId();
        this.criarLote(numPedido, loteId);
    }

    criarLote(numPedido, loteId) {
        const container = document.getElementById(`lotes-container-${numPedido}`);
        if (!container) return;

        // Inicializar dados do lote
        this.workspace.preSeparacoes.set(loteId, {
            produtos: [],
            totais: { valor: 0, peso: 0, pallet: 0 }
        });

        // Remover placeholder se existir
        const placeholder = container.querySelector('.lote-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Criar card do lote
        const loteCard = document.createElement('div');
        loteCard.className = 'col-md-4 mb-3';
        loteCard.innerHTML = this.renderizarCardLote(loteId);

        container.appendChild(loteCard);

        // Drag & drop removido - usando checkboxes
        const newCard = loteCard.querySelector('.lote-card');

        console.log(`✅ Lote criado: ${loteId}`);
    }

    renderizarCardLote(loteId) {
        const loteData = this.workspace.preSeparacoes.get(loteId);
        const temProdutos = loteData.produtos.length > 0;

        // Obter status do pedido atual
        const numPedido = this.workspace.obterNumeroPedido();
        const statusPedido = this.workspace.statusPedido || 'ABERTO';
        const mostrarBotaoAdicionar = ['ABERTO', 'COTADO'].includes(statusPedido);

        return `
            <div class="card lote-card h-100" data-lote-id="${loteId}">
                <div class="card-header bg-gradient-primary text-black">
                    <h6 class="mb-0">
                        <i class="fas fa-box me-2"></i>
                        PRÉ-SEPARAÇÃO
                        <small class="text-muted ms-2" title="Alterações são salvas automaticamente">
                            <i class="fas fa-save"></i> Auto-save
                        </small>
                    </h6>
                    <small>${loteId}</small>
                </div>
                
                <div class="card-body">
                    <div class="produtos-lote mb-3">
                        ${temProdutos ? this.renderizarProdutosDoLote(loteData.produtos, loteId) :
                '<p class="text-muted text-center"><i class="fas fa-hand-pointer me-2"></i>Selecione produtos e clique em "Adicionar Selecionados"</p>'}
                    </div>
                    
                    ${temProdutos ? `
                        <div class="totais-lote border-top pt-2">
                            <div class="row text-center">
                                <div class="col-3">
                                    <strong class="text-success">${this.formatarMoeda(loteData.totais.valor)}</strong>
                                    <br><small class="text-muted">Valor</small>
                                </div>
                                <div class="col-3">
                                    <strong class="text-primary">${this.formatarPeso(loteData.totais.peso)}</strong>
                                    <br><small class="text-muted">Peso</small>
                                </div>
                                <div class="col-3">
                                    <strong class="text-info">${this.formatarPallet(loteData.totais.pallet)}</strong>
                                    <br><small class="text-muted">Pallets</small>
                                </div>
                                <div class="col-3">
                                    <strong class="text-dark">${loteData.produtos.length}</strong>
                                    <br><small class="text-muted">Itens</small>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                <div class="card-footer">
                    <div class="btn-group-vertical w-100">
                        ${mostrarBotaoAdicionar ? `
                            <button class="btn btn-success btn-sm mb-1" 
                                    onclick="workspace.adicionarProdutosSelecionados('${loteId}')">
                                <i class="fas fa-plus-circle me-1"></i> Adicionar Selecionados
                            </button>
                        ` : ''}
                        <div class="btn-group w-100">
                            <button class="btn btn-primary btn-sm" 
                                    onclick="workspace.gerarSeparacao('${loteId}')"
                                    ${!temProdutos ? 'disabled' : ''}>
                                <i class="fas fa-play me-1"></i> Gerar Separação
                            </button>
                            <button class="btn btn-secondary btn-sm" 
                                    onclick="workspace.editarDatasPreSeparacao('${loteId}')"
                                    ${!temProdutos ? 'disabled' : ''}>
                                <i class="fas fa-calendar-alt me-1"></i> Datas
                            </button>
                            <button class="btn btn-info btn-sm" 
                                    onclick="workspace.abrirDetalhesLote('${loteId}')">
                                <i class="fas fa-search me-1"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-sm" 
                                    onclick="workspace.removerLote('${loteId}')">
                                <i class="fas fa-trash me-1"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderizarCardPreSeparacao(loteData) {
        const temProdutos = loteData.produtos.length > 0;
        const isPre = loteData.status === 'pre_separacao';

        // Obter status do pedido atual
        const numPedido = this.workspace.obterNumeroPedido();
        const statusPedido = this.workspace.statusPedido || 'ABERTO';
        const mostrarBotaoAdicionar = ['ABERTO', 'COTADO'].includes(statusPedido) && isPre;

        return `
            <div class="card lote-card h-100" data-lote-id="${loteData.lote_id}">
                <div class="card-header ${isPre ? 'bg-warning' : 'bg-success'} text-black">
                    <h6 class="mb-0">
                        <i class="fas fa-${isPre ? 'clock' : 'check'} me-2"></i>
                        ${isPre ? 'PRÉ-SEPARAÇÃO' : 'SEPARAÇÃO'}
                    </h6>
                    <div class="d-flex justify-content-between align-items-center">
                        <small>${loteData.lote_id}</small>
                        <span class="badge ${isPre ? 'bg-light text-dark' : 'bg-dark text-white'}">
                            ${isPre ? 'PLANEJADA' : 'CONFIRMADA'}
                        </span>
                    </div>
                </div>
                
                <div class="card-body">
                    <div class="produtos-lote mb-3">
                        ${temProdutos ? this.renderizarProdutosDaPreSeparacao(loteData.produtos, loteData.lote_id) :
                '<p class="text-muted text-center"><i class="fas fa-inbox me-2"></i>Nenhum produto</p>'}
                    </div>
                    
                    ${temProdutos ? `
                        <div class="totais-lote border-top pt-2">
                            <div class="row text-center">
                                <div class="col-3">
                                    <strong class="text-success">${this.formatarMoeda(loteData.totais.valor)}</strong>
                                    <br><small class="text-muted">Valor</small>
                                </div>
                                <div class="col-3">
                                    <strong class="text-primary">${this.formatarPeso(loteData.totais.peso)}</strong>
                                    <br><small class="text-muted">Peso</small>
                                </div>
                                <div class="col-3">
                                    <strong class="text-info">${this.formatarPallet(loteData.totais.pallet)}</strong>
                                    <br><small class="text-muted">Pallets</small>
                                </div>
                                <div class="col-3">
                                    <strong class="text-dark">${loteData.produtos.length}</strong>
                                    <br><small class="text-muted">Itens</small>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${loteData.data_expedicao ? `
                        <div class="mt-2 text-center">
                            <small class="text-muted">
                                <i class="fas fa-calendar me-1"></i>
                                Expedição: ${new Date(loteData.data_expedicao).toLocaleDateString('pt-BR')}
                            </small>
                        </div>
                    ` : ''}
                </div>
                
                <div class="card-footer">
                    ${isPre ? `
                        <div class="btn-group-vertical w-100">
                            ${mostrarBotaoAdicionar ? `
                                <button class="btn btn-success btn-sm mb-1" 
                                        onclick="workspace.adicionarProdutosSelecionados('${loteData.lote_id}')">
                                    <i class="fas fa-plus-circle me-1"></i> Adicionar Selecionados
                                </button>
                            ` : ''}
                            <div class="btn-group w-100">
                                <button class="btn btn-primary btn-sm" 
                                        onclick="workspace.confirmarSeparacao('${loteData.lote_id}')"
                                        ${!temProdutos ? 'disabled' : ''}>
                                    <i class="fas fa-check me-1"></i> Confirmar
                                </button>
                                <button class="btn btn-info btn-sm" 
                                        onclick="workspace.abrirDetalhesLote('${loteData.lote_id}')">
                                    <i class="fas fa-search me-1"></i>
                                </button>
                                <button class="btn btn-outline-danger btn-sm" 
                                        onclick="workspace.removerLote('${loteData.lote_id}')">
                                    <i class="fas fa-trash me-1"></i>
                                </button>
                            </div>
                        </div>
                    ` : `</div>
                        <div class="btn-group w-100">
                            <button class="btn btn-outline-primary btn-sm" 
                                    onclick="workspace.editarSeparacao('${loteData.lote_id}')">
                                <i class="fas fa-edit me-1"></i> Editar
                            </button>
                            <button class="btn btn-outline-info btn-sm" 
                                    onclick="workspace.abrirDetalhesLote('${loteData.lote_id}')">
                                <i class="fas fa-search me-1"></i> Detalhes
                            </button>
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    renderizarProdutosDaPreSeparacao(produtos, loteId) {
        return produtos.map(produto => {
            return `
                <div class="produto-lote d-flex justify-content-between align-items-center mb-1">
                    <div class="produto-info">
                        <small><strong>${produto.cod_produto}</strong></small>
                        <br><small class="text-muted">${produto.quantidade}un</small>
                    </div>
                    <div class="produto-acoes">
                        <span class="badge bg-info text-white">${this.formatarMoeda(produto.valor)}</span>
                        <button class="btn btn-sm btn-outline-danger ms-1" 
                                onclick="workspace.removerProdutoDoLote('${produto.loteId || produto.lote_id || loteId}', '${produto.cod_produto || produto.codProduto}')"
                                title="Remover produto da pré-separação (salva automaticamente)">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderizarProdutosDoLote(produtos, loteId) {
        return produtos.map(produto => {
            const dadosProduto = this.workspace.dadosProdutos.get(produto.codProduto);
            const estoqueData = dadosProduto ? dadosProduto.estoque_data_expedicao : 0;

            return `
                <div class="produto-lote d-flex justify-content-between align-items-center mb-1">
                    <div class="produto-info">
                        <small><strong>${produto.codProduto}</strong></small>
                        <br><small class="text-muted">${produto.quantidade}un (${estoqueData})</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="workspace.removerProdutoDoLote('${produto.loteId || loteId}', '${produto.codProduto}')"
                            title="Remover produto (salva automaticamente)">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');
    }

    async adicionarProdutoNoLote(loteId, dadosProduto) {
        try {
            // Obter data de expedição (usar amanhã como padrão)
            const dataExpedicao = dadosProduto.dataExpedicao || this.obterDataExpedicaoDefault();

            // 🎯 USAR PreSeparacaoManager para manter consistência
            const resultado = await this.workspace.preSeparacaoManager.salvarPreSeparacao(
                this.workspace.obterNumeroPedido(),
                dadosProduto.codProduto,
                loteId,
                dadosProduto.qtdPedido,
                dataExpedicao  // ✅ Passando data de expedição
            );

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao salvar pré-separação');
            }

            // Atualizar dados locais com resposta da API
            const loteData = this.workspace.preSeparacoes.get(loteId) || {
                produtos: [],
                totais: { valor: 0, peso: 0, pallet: 0 }
            };

            // Verificar se produto já existe no lote
            const produtoExistente = loteData.produtos.find(p => p.codProduto === dadosProduto.codProduto);

            if (produtoExistente) {
                // Somar quantidade ao produto existente
                produtoExistente.quantidade = resultado.dados.quantidade; // Já vem somado da API
                produtoExistente.valor = resultado.dados.valor;
                produtoExistente.peso = resultado.dados.peso;
                produtoExistente.pallet = resultado.dados.pallet;
                produtoExistente.preSeparacaoId = resultado.pre_separacao_id;

                // Mostrar feedback específico
                this.workspace.mostrarFeedback(
                    `Quantidade do produto ${dadosProduto.codProduto} atualizada para ${resultado.dados.quantidade}`,
                    'success'
                );
            } else {
                // Adicionar novo produto com dados da API
                loteData.produtos.push({
                    codProduto: dadosProduto.codProduto,
                    quantidade: resultado.dados.quantidade,
                    valor: resultado.dados.valor,
                    peso: resultado.dados.peso,
                    pallet: resultado.dados.pallet,
                    preSeparacaoId: resultado.pre_separacao_id,
                    loteId: loteId,
                    status: 'pre_separacao'
                });
            }

            // Atualizar Map local
            this.workspace.preSeparacoes.set(loteId, loteData);

            // Recalcular totais
            this.recalcularTotaisLote(loteId);

            // Re-renderizar o lote
            this.atualizarCardLote(loteId);

            console.log(`✅ Produto ${dadosProduto.codProduto} persistido no lote ${loteId} (ID: ${resultado.pre_separacao_id})`);

            // DEBUG: Verificar estado antes de atualizar saldo
            console.log(`🔍 DEBUG antes de atualizarSaldoAposAdicao:`);
            console.log(`   - codProduto: ${dadosProduto.codProduto}`);
            console.log(`   - quantidade adicionada ao lote: ${dadosProduto.qtdPedido}`);
            console.log(`   - pré-separações no lote:`, loteData.produtos);

            // IMPORTANTE: Atualizar saldo na tabela de origem
            if (window.workspaceQuantidades) {
                window.workspaceQuantidades.atualizarSaldoAposAdicao(dadosProduto.codProduto, dadosProduto.qtdPedido);
            }

            // FORÇAR atualização visual do campo para garantir que mostre o saldo correto
            setTimeout(() => {
                const inputProduto = document.querySelector(`input.qtd-editavel[data-produto="${dadosProduto.codProduto}"]`);
                if (inputProduto && window.workspace) {
                    const dadosProdutoAtualizado = window.workspace.dadosProdutos.get(dadosProduto.codProduto);
                    if (dadosProdutoAtualizado) {
                        const saldoAtualizado = window.workspaceQuantidades.calcularSaldoDisponivel(dadosProdutoAtualizado);
                        const novoValor = Math.floor(saldoAtualizado.qtdEditavel);

                        console.log(`🔧 FORÇANDO atualização do campo ${dadosProduto.codProduto}:`);
                        console.log(`   - Valor atual: ${inputProduto.value}`);
                        console.log(`   - Novo valor: ${novoValor}`);

                        inputProduto.value = novoValor;
                        inputProduto.setAttribute('value', novoValor);
                        inputProduto.dataset.qtdSaldo = novoValor;
                        inputProduto.max = novoValor;

                        // Atualizar span
                        const span = inputProduto.nextElementSibling;
                        if (span && span.classList.contains('input-group-text')) {
                            span.textContent = `/${novoValor}`;
                        }
                    }
                }
            }, 200);

            // DEBUG: Verificar valor do campo após atualização
            setTimeout(() => {
                const input = document.querySelector(`input[data-produto="${dadosProduto.codProduto}"]`);
                if (input) {
                    console.log(`🔍 DEBUG 100ms após atualização:`);
                    console.log(`   - input.value: ${input.value}`);
                    console.log(`   - input.dataset.qtdSaldo: ${input.dataset.qtdSaldo}`);
                }
            }, 100);

        } catch (error) {
            console.error('❌ Erro ao adicionar produto ao lote:', error);
            alert(`❌ Erro ao salvar: ${error.message}`);
        }
    }

    obterDataExpedicaoDefault() {
        // Data padrão: amanhã
        const amanha = new Date();
        amanha.setDate(amanha.getDate() + 1);
        return amanha.toISOString().split('T')[0];
    }

    recalcularTotaisLote(loteId) {
        const loteData = this.workspace.preSeparacoes.get(loteId);
        if (!loteData) return;

        let valor = 0;
        let peso = 0;
        let pallet = 0;

        loteData.produtos.forEach(produto => {
            // Usar valores já calculados pela API
            valor += produto.valor || 0;
            peso += produto.peso || 0;
            pallet += produto.pallet || 0;
        });

        loteData.totais = { valor, peso, pallet };
    }

    atualizarCardLote(loteId) {
        const cardElement = document.querySelector(`[data-lote-id="${loteId}"]`);
        if (cardElement) {
            cardElement.outerHTML = this.renderizarCardLote(loteId);

            // Reconfigurar eventos no novo elemento
            const newCard = document.querySelector(`[data-lote-id="${loteId}"]`);
            // Drag & drop removido - usando checkboxes
        }
    }

    async removerLote(loteId) {
        if (confirm(`Tem certeza que deseja remover o lote ${loteId}?`)) {
            try {
                const loteData = this.workspace.preSeparacoes.get(loteId);

                if (loteData && loteData.produtos && loteData.produtos.length > 0) {
                    // Guardar informações dos produtos antes de remover
                    const produtosParaAtualizar = [...loteData.produtos];

                    // Remover cada produto da pré-separação via API
                    for (const produto of loteData.produtos) {
                        if (produto.preSeparacaoId) {
                            console.log(`🗑️ Removendo produto ${produto.codProduto} (ID: ${produto.preSeparacaoId})`);

                            const response = await fetch(`/carteira/api/pre-separacao/${produto.preSeparacaoId}/remover`, {
                                method: 'DELETE',
                                headers: {
                                    'X-CSRFToken': this.getCSRFToken()
                                }
                            });

                            const result = await response.json();

                            if (!result.success) {
                                throw new Error(result.error || 'Erro ao remover pré-separação');
                            }
                        }
                    }

                    // Atualizar saldos de todos os produtos removidos
                    for (const produto of produtosParaAtualizar) {
                        if (window.workspaceQuantidades) {
                            console.log(`🔄 Atualizando saldo após remover lote: ${produto.codProduto} (qtd: ${produto.quantidade})`);
                            window.workspaceQuantidades.atualizarSaldoAposRemocao(produto.codProduto, produto.quantidade);
                        }
                    }

                    // FORÇAR atualização visual após remover lote completo
                    setTimeout(() => {
                        console.log(`🔧 Forçando atualização de ${produtosParaAtualizar.length} produtos após remover lote`);

                        for (const produto of produtosParaAtualizar) {
                            const inputProduto = document.querySelector(`input.qtd-editavel[data-produto="${produto.codProduto}"]`);
                            if (inputProduto && window.workspace) {
                                const dadosProdutoAtualizado = window.workspace.dadosProdutos.get(produto.codProduto);
                                if (dadosProdutoAtualizado) {
                                    const saldoAtualizado = window.workspaceQuantidades.calcularSaldoDisponivel(dadosProdutoAtualizado);
                                    const novoValor = Math.floor(saldoAtualizado.qtdEditavel);

                                    console.log(`   - Atualizando ${produto.codProduto}: ${inputProduto.value} → ${novoValor}`);

                                    inputProduto.value = novoValor;
                                    inputProduto.setAttribute('value', novoValor);
                                    inputProduto.dataset.qtdSaldo = novoValor;
                                    inputProduto.max = novoValor;

                                    // Atualizar span
                                    const span = inputProduto.nextElementSibling;
                                    if (span && span.classList.contains('input-group-text')) {
                                        span.textContent = `/${novoValor}`;
                                    }

                                    // Atualizar valores calculados
                                    window.workspaceQuantidades.atualizarColunasCalculadas(produto.codProduto, novoValor, dadosProdutoAtualizado);
                                }
                            }
                        }
                    }, 300);
                }

                // Remover do Map local
                this.workspace.preSeparacoes.delete(loteId);

                // Remover o card visual
                const cardElement = document.querySelector(`[data-lote-id="${loteId}"]`).closest('.col-md-4');
                if (cardElement) {
                    cardElement.remove();
                }

                console.log(`✅ Lote ${loteId} removido completamente`);
                this.workspace.mostrarToast('Lote removido com sucesso!', 'success');

            } catch (error) {
                console.error('❌ Erro ao remover lote:', error);
                this.workspace.mostrarToast(`Erro ao remover lote: ${error.message}`, 'error');
            }
        }
    }

    async removerProdutoDoLote(loteId, codProduto) {
        try {
            const loteData = this.workspace.preSeparacoes.get(loteId);
            if (!loteData) return;

            // Encontrar produto para obter o ID da pré-separação
            const produto = loteData.produtos.find(p => p.codProduto === codProduto);
            if (!produto || !produto.preSeparacaoId) {
                console.warn(`⚠️ Produto ${codProduto} não tem ID de pré-separação`);
                return;
            }

            // 🎯 REMOVER do backend via API
            const response = await fetch(`/carteira/api/pre-separacao/${produto.preSeparacaoId}/remover`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            // Verificar se a resposta é JSON válida
            let result;
            try {
                const text = await response.text();
                result = text ? JSON.parse(text) : { success: response.ok };
            } catch (e) {
                console.error('❌ Erro ao processar resposta:', e);
                result = { success: false, error: 'Resposta inválida do servidor' };
            }

            if (!result.success) {
                throw new Error(result.error || 'Erro ao remover pré-separação');
            }

            // Remover do Map local
            loteData.produtos = loteData.produtos.filter(p => p.codProduto !== codProduto);
            this.recalcularTotaisLote(loteId);
            this.atualizarCardLote(loteId);

            console.log(`🗑️ Produto ${codProduto} removido do lote ${loteId} (ID: ${produto.preSeparacaoId})`);

            // IMPORTANTE: Atualizar saldo na tabela de origem após remover
            if (window.workspaceQuantidades) {
                window.workspaceQuantidades.atualizarSaldoAposRemocao(codProduto, produto.quantidade);
            }

            // FORÇAR atualização visual do campo após remoção
            setTimeout(() => {
                const inputProduto = document.querySelector(`input.qtd-editavel[data-produto="${codProduto}"]`);
                if (inputProduto && window.workspace) {
                    const dadosProdutoAtualizado = window.workspace.dadosProdutos.get(codProduto);
                    if (dadosProdutoAtualizado) {
                        const saldoAtualizado = window.workspaceQuantidades.calcularSaldoDisponivel(dadosProdutoAtualizado);
                        const novoValor = Math.floor(saldoAtualizado.qtdEditavel);

                        console.log(`🔧 FORÇANDO atualização do campo após remoção ${codProduto}:`);
                        console.log(`   - Valor atual: ${inputProduto.value}`);
                        console.log(`   - Novo valor: ${novoValor}`);

                        inputProduto.value = novoValor;
                        inputProduto.setAttribute('value', novoValor);
                        inputProduto.dataset.qtdSaldo = novoValor;
                        inputProduto.max = novoValor;

                        // Atualizar span
                        const span = inputProduto.nextElementSibling;
                        if (span && span.classList.contains('input-group-text')) {
                            span.textContent = `/${novoValor}`;
                        }

                        // Atualizar valores calculados
                        window.workspaceQuantidades.atualizarColunasCalculadas(codProduto, novoValor, dadosProdutoAtualizado);
                    }
                }
            }, 200);

        } catch (error) {
            console.error('❌ Erro ao remover produto do lote:', error);
            alert(`❌ Erro ao remover: ${error.message}`);
        }
    }

    // Utilitários
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

    /**
     * Obter CSRF Token de forma consistente
     */
    getCSRFToken() {
        // Usar o mesmo método do PreSeparacaoManager
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        if (cookieValue) return cookieValue;

        const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (metaToken) return metaToken;

        const inputToken = document.querySelector('input[name="csrf_token"]')?.value;
        if (inputToken) return inputToken;

        if (window.csrfToken) return window.csrfToken;

        console.warn('⚠️ CSRF Token não encontrado');
        return '';
    }
}

// Disponibilizar globalmente
window.LoteManager = LoteManager;