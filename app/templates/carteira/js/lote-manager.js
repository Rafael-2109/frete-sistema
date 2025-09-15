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

    // Função removida - usar app.utils.lote_utils.gerar_lote_id() no backend
    // Mantida temporariamente apenas como fallback até migração completa
    gerarNovoLoteId() {
        // TODO: Migrar para chamada do backend
        const hoje = new Date();
        const data = hoje.toISOString().slice(0, 10).replace(/-/g, '');
        const hora = hoje.toTimeString().slice(0, 8).replace(/:/g, '');
        const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
        return `LOTE_${data}_${hora}_${random}`; // Formato alinhado com backend
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
        // Obter dados do lote ou criar estrutura padrão
        const loteData = this.workspace.preSeparacoes.get(loteId) || {
            produtos: [],
            totais: { valor: 0, peso: 0, pallet: 0 },
            status: 'ABERTO',
            lote_id: loteId,
            separacao_lote_id: loteId,
            data_expedicao: null,
            data_agendamento: null,
            expedicao: null,
            agendamento: null,
            protocolo: null,
            agendamento_confirmado: false
        };
        
        // Garantir defaults
        loteData.status = loteData.status || 'ABERTO';
        loteData.lote_id = loteData.lote_id || loteId;
        
        // USAR O CARD UNIVERSAL
        return this.renderizarCardUniversal(loteData);
    }

    /**
     * 🔐 OBTER PERMISSÕES BASEADAS NO STATUS
     * Centraliza toda lógica de permissões
     */
    obterPermissoes(status) {
        return {
            podeEditarDatas: ['PREVISAO', 'ABERTO'].includes(status),
            podeAdicionarProdutos: ['PREVISAO', 'ABERTO'].includes(status),
            podeRemoverProdutos: ['PREVISAO', 'ABERTO'].includes(status),
            podeConfirmar: status === 'PREVISAO',
            podeReverter: status === 'ABERTO',
            podeExcluir: ['PREVISAO', 'ABERTO'].includes(status),
            podeImprimir: true,
            podeAgendarPortal: ['ABERTO', 'COTADO'].includes(status),
            podeVerificarPortal: ['ABERTO', 'COTADO'].includes(status),
            podeVerDetalhes: ['COTADO', 'EMBARCADO', 'FATURADO'].includes(status)
        };
    }

    /**
     * 🎨 RENDERIZAR CARD UNIVERSAL
     * Card único para todos os status de separação
     * Diferenciado apenas por cores e permissões
     */
    renderizarCardUniversal(loteData) {
        // Configuração de cores por status
        const configStatus = {
            'PREVISAO': {
                cor: 'secondary',     // Cinza claro
                texto: 'SEPARAÇÃO',   // Sempre "SEPARAÇÃO", não "PRÉ-SEPARAÇÃO"
                icone: 'clock',
                badge: 'PREVISÃO'     // Badge indica o status real
            },
            'ABERTO': {
                cor: 'warning',       // Amarelo
                texto: 'SEPARAÇÃO',
                icone: 'box-open',
                badge: 'ABERTO'
            },
            'COTADO': {
                cor: 'primary',       // Azul
                texto: 'SEPARAÇÃO',
                icone: 'truck',
                badge: 'COTADO'
            },
            'EMBARCADO': {
                cor: 'success',       // Verde
                texto: 'SEPARAÇÃO',
                icone: 'shipping-fast',
                badge: 'EMBARCADO'
            },
            'FATURADO': {
                cor: 'success',       // Verde
                texto: 'SEPARAÇÃO',
                icone: 'file-invoice-dollar',
                badge: 'FATURADO'
            },
            'NF_CD': {
                cor: 'danger',        // Vermelho
                texto: 'SEPARAÇÃO',
                icone: 'exclamation-triangle',
                badge: 'NF NO CD'
            }
        };

        // Compatibilidade com status antigo 'pre_separacao'
        const status = loteData.status === 'pre_separacao' ? 'PREVISAO' : loteData.status;
        const config = configStatus[status] || configStatus['PREVISAO'];
        
        // Usar método centralizado de permissões
        const permissoes = this.obterPermissoes(status);
        
        const temProdutos = loteData.produtos && loteData.produtos.length > 0;
        
        console.log('🎨 Renderizando card universal:', {
            loteId: loteData.lote_id,
            status: status,
            config: config,
            permissoes: permissoes
        });

        return `
            <div class="card lote-card h-100 border-${config.cor}" data-lote-id="${loteData.lote_id}" data-status="${status}">
                <div class="card-header bg-${config.cor} ${config.cor === 'warning' ? 'text-dark' : 'text-white'}">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-${config.icone} me-2"></i>
                            ${config.texto}
                            ${status === 'ABERTO' ? `
                                <small class="text-muted ms-2" title="Alterações são salvas automaticamente">
                                    <i class="fas fa-save"></i> Auto-save
                                </small>
                            ` : ''}
                        </h6>
                        <span class="badge ${config.cor === 'warning' ? 'bg-dark text-white' : 'bg-white text-dark'}">
                            ${config.badge}
                        </span>
                    </div>
                    <small class="d-block mt-1">${loteData.lote_id || loteData.separacao_lote_id}</small>
                </div>
                
                <div class="card-body">
                    <!-- Lista de produtos -->
                    <div class="produtos-lote mb-3">
                        ${temProdutos ? this.renderizarProdutosUniversal(loteData.produtos, loteData.lote_id, permissoes.podeRemoverProdutos) :
                            '<p class="text-muted text-center"><i class="fas fa-box-open me-2"></i>Nenhum produto neste lote</p>'}
                    </div>
                    
                    <!-- Totais -->
                    ${temProdutos ? `
                        <div class="totais-lote border-top pt-3">
                            <div class="row text-center">
                                <div class="col-4">
                                    <small class="text-muted d-block">Valor</small>
                                    <strong class="text-success total-valor-card">${this.formatarMoeda(loteData.totais?.valor || loteData.valor_total || loteData.valor_saldo || 0)}</strong>
                                </div>
                                <div class="col-4">
                                    <small class="text-muted d-block">Peso</small>
                                    <strong class="text-primary total-peso-card">${this.formatarPeso(loteData.totais?.peso || loteData.peso_total || loteData.peso || 0)}</strong>
                                </div>
                                <div class="col-4">
                                    <small class="text-muted d-block">Pallets</small>
                                    <strong class="text-info total-pallet-card">${this.formatarPallet(loteData.totais?.pallet || loteData.pallet_total || loteData.pallet || 0)}</strong>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    <!-- Datas -->
                    <div class="datas-lote border-top pt-3 mt-3">
                        <div class="row">
                            <div class="col-6">
                                <small class="text-muted d-block">Expedição</small>
                                <div class="fw-bold data-expedicao-card">${this.formatarDataDisplay(loteData.expedicao || loteData.data_expedicao) || 'Não definida'}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted d-block">Agendamento</small>
                                <div class="fw-bold data-agendamento-card">
                                    <span class="data-agendamento-texto">${this.formatarDataDisplay(loteData.agendamento || loteData.data_agendamento) || 'Não definido'}</span>
                                    ${loteData.agendamento_confirmado ? '<i class="fas fa-check-circle text-success ms-1 agendamento-confirmado-icon" title="Confirmado"></i>' : ''}
                                </div>
                            </div>
                        </div>
                        ${loteData.protocolo ? `
                            <div class="row mt-2">
                                <div class="col-12">
                                    <small class="text-muted d-block">Protocolo</small>
                                    <div class="fw-bold protocolo-card">${loteData.protocolo}</div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <!-- Footer com ações baseadas no status -->
                <div class="card-footer">
                    <!-- Primeira linha: Botões principais -->
                    <div class="btn-group mb-2" role="group">
                        ${permissoes.podeEditarDatas ? `
                            <button class="btn btn-outline-primary btn-sm" 
                                    onclick="workspace.editarDatas('${loteData.lote_id}', '${status}')">
                                <i class="fas fa-calendar-alt"></i> Datas
                            </button>
                        ` : ''}

                        ${permissoes.podeAdicionarProdutos ? `
                            <button class="btn btn-outline-success btn-sm" 
                                    onclick="workspace.adicionarProdutosSelecionados('${loteData.lote_id}')">
                                <i class="fas fa-plus"></i> Adicionar
                            </button>
                        ` : ''}

                        ${permissoes.podeConfirmar ? `
                            <button class="btn btn-warning btn-sm" 
                                    onclick="workspace.alterarStatusSeparacao('${loteData.lote_id}', 'ABERTO')"
                                    title="Transformar em separação confirmada (ABERTO)">
                                <i class="fas fa-check"></i> Confirmar
                            </button>
                        ` : ''}

                        ${permissoes.podeReverter ? `
                            <button class="btn btn-secondary btn-sm" 
                                    onclick="workspace.alterarStatusSeparacao('${loteData.lote_id}', 'PREVISAO')"
                                    title="Voltar para previsão">
                                <i class="fas fa-undo"></i> Previsão
                            </button>
                        ` : ''}

                        ${permissoes.podeExcluir ? `
                            <button class="btn btn-outline-danger btn-sm" 
                                    onclick="workspace.excluirLote('${loteData.lote_id}')"
                                    title="Excluir separação">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>

                    <!-- Segunda linha: Botões do Portal -->
                    ${(loteData.agendamento || loteData.data_agendamento) ? `
                        <div class="btn-group mb-2" role="group">
                            <button class="btn btn-outline-success btn-sm"
                                    onclick="carteiraAgrupada.agendarNoPortal('${loteData.lote_id || loteData.separacao_lote_id}', '${loteData.agendamento || loteData.data_agendamento}')"
                                    title="Agendar no portal do cliente">
                                <i class="fas fa-calendar-plus"></i> Agendar
                            </button>
                        
                            ${loteData.protocolo ? `
                                <button class="btn btn-outline-info btn-sm"
                                        	onclick="window.PortalAgendamento.verificarProtocoloNoPortal('${loteData.lote_id || loteData.separacao_lote_id}', '${loteData.protocolo}')"
                                        title="Verificar protocolo: ${loteData.protocolo}">
                                    <i class="fas fa-check-circle"></i> Ver. Protocolo
                                </button>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
            </div> 
        `;
    }

    


    /**
     * 📅 FORMATAR DATA PARA DISPLAY
     * Converte data em qualquer formato para dd/mm/yyyy
     */
    formatarDataDisplay(data) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.data) {
            return window.Formatters.data(data);
        }
        
        // Fallback para implementação original
        if (!data) return null;
        
        // Se já está no formato dd/mm/yyyy, retornar como está
        if (typeof data === 'string' && data.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
            return data;
        }
        
        // Se está no formato yyyy-mm-dd
        if (typeof data === 'string' && data.match(/^\d{4}-\d{2}-\d{2}$/)) {
            const [ano, mes, dia] = data.split('-');
            return `${dia}/${mes}/${ano}`;
        }
        
        // Se é um objeto Date ou string de data
        try {
            const dateObj = new Date(data);
            if (!isNaN(dateObj.getTime())) {
                const dia = String(dateObj.getDate()).padStart(2, '0');
                const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
                const ano = dateObj.getFullYear();
                return `${dia}/${mes}/${ano}`;
            }
        } catch (e) {
            console.warn('Erro ao formatar data:', e);
        }
        
        return null;
    }

    /**
     * 🎨 RENDERIZAR PRODUTOS UNIVERSAL
     * Renderiza lista de produtos com permissão condicional de remoção
     * Layout compacto: 1 linha por produto
     */
    renderizarProdutosUniversal(produtos, loteId, podeRemover = false) {
        if (!produtos || produtos.length === 0) {
            return '<p class="text-muted text-center"><i class="fas fa-box-open me-2"></i>Nenhum produto</p>';
        }

        return `<div class="produtos-lista">` + produtos.map(produto => {
            // Compatibilidade com diferentes estruturas de dados - PRIORIZAR campos do backend
            const codProduto = produto.cod_produto || produto.codProduto;
            const nomeProduto = produto.nome_produto || produto.nomeProduto || '';
            const quantidade = parseFloat(produto.qtd_saldo || produto.quantidade || 0);
            const valor = parseFloat(produto.valor_saldo || produto.valor || 0);
            const peso = parseFloat(produto.peso || 0);
            const pallet = parseFloat(produto.pallet || 0);
            
            // Formatar valores
            const qtdFormatada = Math.floor(quantidade).toLocaleString('pt-BR');
            const valorFormatado = valor > 0 ? valor.toLocaleString('pt-BR', { 
                minimumFractionDigits: 2, 
                maximumFractionDigits: 2 
            }) : '0,00';
            const pesoFormatado = peso > 0 ? peso.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }) : '0,00';
            const palletFormatado = pallet > 0 ? pallet.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }) : '0,00';

            return `
                <div class="produto-lote d-flex align-items-center justify-content-between py-1 border-bottom">
                    <div class="produto-info d-flex align-items-center flex-grow-1" style="min-width: 0;">
                        <strong class="me-2 text-nowrap">${codProduto}</strong>
                        <span class="text-truncate small text-muted me-2" style="max-width: 200px;" title="${nomeProduto}">
                            ${nomeProduto}
                        </span>
                    </div>
                    <div class="produto-valores d-flex align-items-center text-nowrap">
                        <span class="small me-2">
                            <strong>${qtdFormatada}</strong>un
                        </span>
                        ${valor > 0 ? `
                            <span class="small text-success me-2">
                                R$ <strong>${valorFormatado}</strong>
                            </span>
                        ` : ''}
                        ${peso > 0 ? `
                            <span class="small text-primary me-2">
                                <strong>${pesoFormatado}</strong>kg
                            </span>
                        ` : ''}
                        ${pallet > 0 ? `
                            <span class="small text-info me-2">
                                <strong>${palletFormatado}</strong>plt
                            </span>
                        ` : ''}
                        ${podeRemover ? `
                            <button class="btn btn-sm btn-link text-danger p-0 ms-2" 
                                    onclick="workspace.loteManager.removerProdutoDoLote('${loteId}', '${codProduto}')"
                                    title="Remover produto">
                                <i class="fas fa-times"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('') + `</div>`;
    }

    async adicionarProdutoNoLote(loteId, dadosProduto) {
        try {
            // Obter data de expedição (usar amanhã como padrão)
            const dataExpedicao = dadosProduto.dataExpedicao || this.obterDataExpedicaoDefault();

            // 🔍 DEBUG: Verificar qual pedido está sendo usado
            const numPedido = this.workspace.obterNumeroPedido();
            console.log(`🔍 DEBUG adicionarProdutoNoLote:
                - Pedido atual: ${numPedido}
                - Produto: ${dadosProduto.codProduto}
                - Lote: ${loteId}`);

            // 🎯 USAR API diretamente para salvar separação
            const resultado = await this.salvarSeparacaoAPI(
                numPedido,
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
            const produtoExistente = loteData.produtos.find(p => 
                (p.cod_produto === dadosProduto.codProduto) || (p.codProduto === dadosProduto.codProduto)
            );

            if (produtoExistente) {
                // Somar quantidade ao produto existente - USAR NOMES DO BACKEND
                produtoExistente.qtd_saldo = resultado.dados.quantidade; // Já vem somado da API
                produtoExistente.valor_saldo = resultado.dados.valor;
                produtoExistente.peso = resultado.dados.peso;
                produtoExistente.pallet = resultado.dados.pallet;
                produtoExistente.separacaoId = resultado.separacao_id;
                produtoExistente.nome_produto = dadosProduto.nomeProduto || dadosProduto.nome_produto || '';

                // Mostrar feedback específico
                this.workspace.mostrarFeedback(
                    `Quantidade do produto ${dadosProduto.codProduto} atualizada para ${resultado.dados.quantidade}`,
                    'success'
                );
            } else {
                // Adicionar novo produto com dados da API - USAR NOMES DO BACKEND
                loteData.produtos.push({
                    cod_produto: dadosProduto.codProduto,
                    nome_produto: dadosProduto.nomeProduto || dadosProduto.nome_produto || '',
                    qtd_saldo: resultado.dados.quantidade,
                    valor_saldo: resultado.dados.valor,
                    peso: resultado.dados.peso,
                    pallet: resultado.dados.pallet,
                    separacaoId: resultado.separacao_id,
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

            console.log(`✅ Produto ${dadosProduto.codProduto} persistido no lote ${loteId} (ID: ${resultado.separacao_id})`);

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
            // Usar valores já calculados pela API - compatível com ambas estruturas
            valor += produto.valor_saldo || produto.valor || 0;
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

    // Método removerLote removido - usar workspace.excluirLote() que é o método correto

    async removerProdutoDoLote(loteId, codProduto) {
        try {
            const loteData = this.workspace.preSeparacoes.get(loteId);
            if (!loteData) return;

            // Encontrar produto para obter o ID da separação - compatível com ambas estruturas
            const produto = loteData.produtos.find(p => 
                p.codProduto === codProduto || p.cod_produto === codProduto
            );
            const separacaoId = produto?.separacaoId || produto?.preSeparacaoId;
            if (!produto || !separacaoId) {
                console.warn(`⚠️ Produto ${codProduto} não tem ID de separação`);
                return;
            }

            // 🎯 REMOVER do backend via API
            const response = await fetch(`/carteira/api/separacao/${separacaoId}/remover`, {
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

            // Remover do Map local - compatível com ambas estruturas
            loteData.produtos = loteData.produtos.filter(p => 
                p.codProduto !== codProduto && p.cod_produto !== codProduto
            );
            this.recalcularTotaisLote(loteId);
            this.atualizarCardLote(loteId);

            console.log(`🗑️ Produto ${codProduto} removido do lote ${loteId} (ID: ${separacaoId})`);

            // IMPORTANTE: Atualizar saldo na tabela de origem após remover
            if (window.workspaceQuantidades) {
                const quantidade = produto.quantidade || produto.qtd_saldo || 0;
                window.workspaceQuantidades.atualizarSaldoAposRemocao(codProduto, quantidade);
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

    // Utilitários - Usando módulo centralizado com fallback
    formatarMoeda(valor) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.moeda) {
            return window.Formatters.moeda(valor);
        }
        // Fallback para implementação original
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarPeso(peso) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.peso) {
            return window.Formatters.peso(peso);
        }
        // Fallback para workspaceQuantidades
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarPeso(peso);
        }
        // Fallback final
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.pallet) {
            return window.Formatters.pallet(pallet);
        }
        // Fallback para workspaceQuantidades
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.formatarPallet(pallet);
        }
        // Fallback final
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }

    /**
     * 🔄 SALVAR SEPARAÇÃO VIA API
     * Substitui a chamada ao PreSeparacaoManager obsoleto
     */
    async salvarSeparacaoAPI(numPedido, codProduto, loteId, quantidade, dataExpedicao) {
        try {
            const response = await fetch('/carteira/api/separacao/salvar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    cod_produto: codProduto,
                    separacao_lote_id: loteId,
                    qtd_saldo: quantidade,
                    expedicao: dataExpedicao,
                    status: 'ABERTO'  // Status inicial sempre ABERTO
                })
            });

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Erro ao salvar separação');
            }

            // Calcular valores localmente usando dados do produto
            const dadosProduto = this.workspace.dadosProdutos.get(codProduto);
            let valorCalculado = 0;
            let pesoCalculado = 0;
            let palletCalculado = 0;
            
            if (dadosProduto) {
                // CORRIGIDO: Usar os campos corretos que existem em dadosProduto
                const preco = parseFloat(dadosProduto.preco_produto_pedido) || parseFloat(dadosProduto.preco_unitario) || 0;
                const peso = parseFloat(dadosProduto.peso_unitario) || 0;  // Campo correto: peso_unitario
                const palletizacao = parseFloat(dadosProduto.palletizacao) || 1000;  // Default: 1000 (não 1)
                
                valorCalculado = quantidade * preco;
                pesoCalculado = quantidade * peso;
                palletCalculado = palletizacao > 0 ? quantidade / palletizacao : 0;
            }

            // Adaptar resposta para formato esperado
            return {
                success: true,
                separacao_id: result.separacao_id,
                dados: {
                    quantidade: quantidade,
                    valor: valorCalculado,
                    peso: pesoCalculado,
                    pallet: palletCalculado
                }
            };
        } catch (error) {
            console.error('❌ Erro ao salvar separação:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Obter CSRF Token de forma consistente
     */
    getCSRFToken() {
        // Usar módulo centralizado se disponível
        if (window.Security && window.Security.getCSRFToken) {
            return window.Security.getCSRFToken();
        }
        
        // Fallback para implementação original
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