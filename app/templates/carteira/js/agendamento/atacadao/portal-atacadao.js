/**
 * 🎯 MÓDULO DE AGENDAMENTO NO PORTAL ATACADÃO
 * 
 * Este módulo contém a implementação específica para o portal do Atacadão.
 * É chamado pelo roteador principal (destinacao-portais.js) quando 
 * identificado que o cliente é do grupo Atacadão.
 * 
 * @author Sistema de Frete
 * @since 2025-01-09
 */

class PortalAtacadao {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Módulo de Agendamento do Portal Atacadão inicializado');
    }

    /**
     * 📅 FUNÇÃO PRINCIPAL DE AGENDAMENTO
     * Realiza o agendamento completo no portal do cliente
     * 
     * @param {string} loteId - ID do lote de separação
     * @param {string} dataAgendamento - Data de agendamento (opcional)
     * @returns {Promise<boolean>} - Sucesso do agendamento
     */
    async agendarNoPortal(loteId, dataAgendamento) {
        console.log(`📅 Agendando lote ${loteId} no portal`);

        // Primeiro verificar se todos os produtos têm De-Para cadastrado
        Swal.fire({
            title: 'Verificando De-Para...',
            text: 'Validando mapeamento de produtos',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            // Verificar De-Para
            const verificacaoResponse = await fetch(`/portal/atacadao/agendamento/verificar_depara/${loteId}`);
            const verificacao = await verificacaoResponse.json();

            if (!verificacao.success) {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: verificacao.message || 'Erro ao verificar De-Para',
                    confirmButtonText: 'OK'
                });
                return false;
            }

            // Se tem produtos sem De-Para, avisar o usuário
            if (verificacao.sem_depara > 0) {
                const produtosSemDePara = verificacao.produtos_sem_depara.map(p =>
                    `<li><strong>${p.codigo}</strong> - ${p.descricao}</li>`
                ).join('');

                const result = await Swal.fire({
                    icon: 'warning',
                    title: 'Produtos sem De-Para',
                    html: `
                        <p>${verificacao.sem_depara} produto(s) não têm mapeamento De-Para cadastrado:</p>
                        <ul style="text-align: left; max-height: 200px; overflow-y: auto;">
                            ${produtosSemDePara}
                        </ul>
                        <p>Deseja continuar mesmo assim?</p>
                    `,
                    showCancelButton: true,
                    confirmButtonText: 'Continuar',
                    cancelButtonText: 'Cadastrar De-Para',
                    confirmButtonColor: window.Notifications?.colors?.warning || '#ffc107',
                    cancelButtonColor: window.Notifications?.colors?.neutral || '#6c757d'
                });

                if (result.dismiss === Swal.DismissReason.cancel) {
                    // Abrir modal de De-Para
                    this.abrirModalDePara(verificacao.produtos_sem_depara);
                    return false;
                }

                if (!result.isConfirmed) {
                    return false;
                }
            }

            // Preparar dados de agendamento
            const preparacaoResponse = await fetch(`/portal/atacadao/agendamento/preparar/${loteId}`);
            const preparacao = await preparacaoResponse.json();

            if (!preparacao.success) {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: preparacao.message || 'Erro ao preparar dados',
                    confirmButtonText: 'OK'
                });
                return false;
            }

            // Se não tem data de agendamento, usar a da preparação ou solicitar
            if (!dataAgendamento || dataAgendamento === '') {
                dataAgendamento = preparacao.data_agendamento;

                if (!dataAgendamento) {
                    const { value: data } = await Swal.fire({
                        title: 'Data de Agendamento',
                        input: 'date',
                        inputLabel: 'Selecione a data para agendamento',
                        inputPlaceholder: 'dd/mm/aaaa',
                        inputAttributes: {
                            min: new Date().toISOString().split('T')[0]
                        },
                        showCancelButton: true,
                        confirmButtonText: 'Continuar',
                        cancelButtonText: 'Cancelar'
                    });

                    if (!data) {
                        return false;
                    }
                    dataAgendamento = data;
                }
            }

            // Mostrar resumo dos produtos convertidos
            const produtosHtml = preparacao.produtos.map(p =>
                `<tr>
                    <td>${p.codigo_atacadao}</td>
                    <td>${p.descricao_atacadao}</td>
                    <td>${p.quantidade.toFixed(2)}</td>
                    <td>${p.pallets.toFixed(2)}</td>
                </tr>`
            ).join('');

            // Formatar data para exibição
            const dataFormatada = this.formatarData(dataAgendamento);

            // 🆕 Se TODOS os produtos tem De-Para: confirmacao rapida (sem tabela).
            //    Se houver produto sem De-Para: mantem o modal completo com a tabela.
            let confirmou;
            if (verificacao.sem_depara === 0) {
                const confirmResult = await Swal.fire({
                    title: 'Solicitar agendamento?',
                    icon: 'question',
                    html: `
                        <p>Portal <strong>Atacadão</strong></p>
                        <p><strong>Data:</strong> ${dataFormatada}</p>
                        <p>${preparacao.total_convertidos} de ${preparacao.total_itens} itens com De-Para.</p>
                    `,
                    showCancelButton: true,
                    confirmButtonText: 'Confirmar e Agendar',
                    cancelButtonText: 'Cancelar'
                });
                confirmou = confirmResult.isConfirmed;
            } else {
                const confirmResult = await Swal.fire({
                    title: 'Confirmar Agendamento',
                    html: `
                        <p><strong>Data:</strong> ${dataFormatada}</p>
                        <p><strong>Produtos convertidos:</strong> ${preparacao.total_convertidos} de ${preparacao.total_itens}</p>
                        <table class="table table-sm" style="font-size: 0.85em;">
                            <thead>
                                <tr>
                                    <th>Cód. Atacadão</th>
                                    <th>Descrição</th>
                                    <th>Qtd</th>
                                    <th>Pallets</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${produtosHtml}
                            </tbody>
                        </table>
                    `,
                    showCancelButton: true,
                    confirmButtonText: 'Confirmar e Agendar',
                    cancelButtonText: 'Cancelar',
                    width: '600px'
                });
                confirmou = confirmResult.isConfirmed;
            }

            if (!confirmou) {
                return false;
            }

            // Mostrar loading
            Swal.fire({
                title: 'Processando...',
                text: 'Realizando agendamento no portal do cliente',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // Fazer o agendamento ASSÍNCRONO com Redis Queue
            const response = await fetch('/portal/api/solicitar-agendamento-async', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    tipo: 'separacao',
                    portal: 'atacadao',
                    data_agendamento: dataAgendamento,
                    produtos_convertidos: preparacao.produtos
                })
            });

            const data = await response.json();

            if (data.success) {
                // Se tem protocolo, gravar na Separacao
                if (data.protocolo) {
                    await this.gravarProtocolo(loteId, data.protocolo);
                }

                // 🆕 Todos com De-Para: toast no canto superior (tela livre).
                //    Caso contrario: mantem o modal de sucesso.
                if (verificacao.sem_depara === 0) {
                    this._toastSucesso(`Atacadão: agendamento solicitado. Protocolo: ${data.protocolo || 'aguardando confirmação'}`);
                } else {
                    await Swal.fire({
                        icon: 'success',
                        title: 'Agendamento Realizado!',
                        html: `
                            <p><strong>Protocolo:</strong> ${data.protocolo || 'Aguardando confirmação'}</p>
                            <p>${data.message}</p>
                        `,
                        confirmButtonText: 'OK'
                    });
                }

                // Recarregar modal de separações se estiver aberto
                if (window.modalSeparacoes && document.getElementById('modal-pedido-numero')) {
                    const numPedido = document.getElementById('modal-pedido-numero').textContent;
                    if (numPedido && window.modalSeparacoes.carregarSeparacoes) {
                        window.modalSeparacoes.carregarSeparacoes(numPedido);
                    }
                }

                // Disparar evento para atualizar outras interfaces
                this.dispararEventoAtualizacao('agendamento-realizado', { loteId, protocolo: data.protocolo });

                return true;
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro no Agendamento',
                    text: data.message || 'Erro ao processar agendamento',
                    confirmButtonText: 'OK'
                });
                return false;
            }
        } catch (error) {
            console.error('Erro ao agendar:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao comunicar com o servidor',
                confirmButtonText: 'OK'
            });
            return false;
        }
    }

    /**
     * 🔍 VERIFICAR STATUS DO AGENDAMENTO
     * Verifica o status de um lote no portal
     * 
     * @param {string} loteId - ID do lote
     */
    async verificarPortal(loteId) {
        console.log(`🔍 Verificando lote ${loteId} no portal`);

        // Mostrar loading
        Swal.fire({
            title: 'Verificando Status...',
            text: 'Consultando informações do agendamento',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            // Verificar De-Para e status
            const [verificacaoResponse, preparacaoResponse] = await Promise.all([
                fetch(`/portal/atacadao/agendamento/verificar_depara/${loteId}`),
                fetch(`/portal/atacadao/agendamento/preparar/${loteId}`)
            ]);

            const verificacao = await verificacaoResponse.json();
            const preparacao = await preparacaoResponse.json();

            if (!verificacao.success || !preparacao.success) {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: 'Erro ao buscar informações do agendamento',
                    confirmButtonText: 'OK'
                });
                return;
            }

            // Buscar separação - primeiro tenta local (se modal estiver aberto), senão busca do servidor
            let separacao = null;
            if (window.modalSeparacoes && window.modalSeparacoes.separacoes) {
                separacao = window.modalSeparacoes.separacoes.find(s => s.separacao_lote_id === loteId);
            }

            if (!separacao) {
                const separacaoResponse = await fetch(`/carteira/api/separacao/${loteId}`);
                separacao = await separacaoResponse.json();
            }

            // Montar HTML do status
            let statusHtml = `
                <div class="text-start">
                    <h5>📦 Informações do Lote</h5>
                    <p><strong>Lote ID:</strong> ${loteId}</p>
                    <p><strong>Data Expedição:</strong> ${this.formatarData(preparacao.data_expedicao)}</p>
                    <p><strong>Data Agendamento:</strong> ${this.formatarData(preparacao.data_agendamento)}</p>
                    
                    <hr>
                    
                    <h5>📋 Status De-Para</h5>
                    <p><strong>Total de Produtos:</strong> ${verificacao.total_produtos}</p>
                    <p><strong>Com De-Para:</strong> ${verificacao.com_depara} ✅</p>
                    <p><strong>Sem De-Para:</strong> ${verificacao.sem_depara} ${verificacao.sem_depara > 0 ? '❌' : '✅'}</p>
            `;

            if (verificacao.produtos_sem_depara && verificacao.produtos_sem_depara.length > 0) {
                statusHtml += `
                    <div class="alert alert-warning mt-3">
                        <strong>Produtos sem De-Para:</strong>
                        <ul class="mb-0">
                            ${verificacao.produtos_sem_depara.map(p =>
                    `<li>${p.codigo} - ${p.descricao}</li>`
                ).join('')}
                        </ul>
                    </div>
                `;
            }

            if (separacao && separacao.protocolo) {
                statusHtml += `
                    <hr>
                    <h5>✅ Agendamento Confirmado</h5>
                    <p><strong>Protocolo:</strong> ${separacao.protocolo}</p>
                `;
            }

            statusHtml += '</div>';

            // Mostrar resultado
            const result = await Swal.fire({
                title: 'Status do Agendamento',
                html: statusHtml,
                icon: 'info',
                showCancelButton: separacao && separacao.protocolo,
                showConfirmButton: !separacao || !separacao.protocolo,
                confirmButtonText: 'Agendar Agora',
                cancelButtonText: verificacao.sem_depara > 0 ? 'Cadastrar De-Para' : 'Fechar',
                confirmButtonColor: window.Notifications?.colors?.success || '#28a745',
                cancelButtonColor: window.Notifications?.colors?.neutral || '#6c757d'
            });

            if (result.isConfirmed && (!separacao || !separacao.protocolo)) {
                // Se não tem protocolo e clicou em "Agendar Agora"
                this.agendarNoPortal(loteId, preparacao.data_agendamento);
            } else if (result.dismiss === Swal.DismissReason.cancel && verificacao.sem_depara > 0) {
                // Abrir modal de De-Para
                this.abrirModalDePara(verificacao.produtos_sem_depara);
            }

        } catch (error) {
            console.error('Erro ao verificar status:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao verificar status do agendamento',
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * 🔍 VERIFICAR PROTOCOLO NO PORTAL
     * Verifica um protocolo específico no portal
     * 
     * @param {string} loteId - ID do lote
     * @param {string} protocolo - Protocolo a verificar
     */
    async verificarProtocoloNoPortal(loteId, protocolo) {
        console.log(`🔍 Verificando protocolo ${protocolo} no portal`);

        // Mostrar loading
        Swal.fire({
            title: 'Verificando Protocolo...',
            text: `Consultando protocolo ${protocolo} no Portal Atacadão`,
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            // Fazer chamada para verificar protocolo
            const response = await fetch('/carteira/api/verificar-protocolo-portal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    protocolo: protocolo
                })
            });

            const data = await response.json();

            if (data.success) {
                // Montar HTML de comparação com tabela unificada
                let htmlComparacao = `
                    <style>
                        .table-comparacao {
                            font-size: 0.85rem;
                        }
                        .table-comparacao th {
                            font-size: 0.9rem;
                            font-weight: 600;
                        }
                        .linha-divergencia {
                            background-color: var(--semantic-danger-subtle, #ffebee) !important;
                        }
                        .texto-divergencia {
                            color: var(--semantic-danger, #c62828);
                            font-weight: 600;
                        }
                        .badge-diferenca {
                            font-size: 0.75rem;
                        }
                    </style>
                    
                    <div class="container-fluid">
                        <!-- Status do Agendamento -->
                        <div class="row mb-3">
                            <div class="col-12">
                                <div class="alert ${data.agendamento_confirmado ? 'alert-success' : 'alert-warning'}">
                                    <h6 class="mb-2">
                                        <i class="fas ${data.agendamento_confirmado ? 'fa-check-circle' : 'fa-clock'}"></i>
                                        Status: ${data.agendamento_confirmado ? 'Aguardando check-in' : 'Aguardando aprovação'}
                                    </h6>
                                    ${data.data_aprovada ? `
                                        <p class="mb-1 small"><strong>Entrega aprovada para:</strong> ${this.formatarData(data.data_aprovada)}</p>
                                    ` : ''}
                                    <p class="mb-0 small"><strong>Protocolo:</strong> ${protocolo}</p>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Tabela Unificada -->
                        <div class="row">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header py-2">
                                        <h6 class="mb-0">
                                            <i class="fas fa-exchange-alt"></i> Comparação de Produtos
                                        </h6>
                                    </div>
                                    <div class="card-body p-2">
                                        ${data.produtos_unificados && data.produtos_unificados.length > 0 ? `
                                            <div class="table-responsive">
                                                <table class="table table-sm table-hover table-comparacao mb-0">
                                                    <thead class="table-light">
                                                        <tr>
                                                            <th width="15%">Código</th>
                                                            <th width="40%">Descrição</th>
                                                            <th width="12%" class="text-center">Qtd Separação</th>
                                                            <th width="12%" class="text-center">Qtd Agendamento</th>
                                                            <th width="12%" class="text-center">Diferença</th>
                                                            <th width="9%" class="text-center">Status</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        ${data.produtos_unificados.map(p => `
                                                            <tr class="${p.tem_divergencia ? 'linha-divergencia' : ''}">
                                                                <td><small>${p.codigo_nosso}</small></td>
                                                                <td><small>${p.descricao_nossa}</small></td>
                                                                <td class="text-center">
                                                                    <span class="${p.tem_divergencia && p.qtd_separacao !== p.qtd_agendamento ? 'texto-divergencia' : ''}">
                                                                        ${p.qtd_separacao.toFixed(2)}
                                                                    </span>
                                                                </td>
                                                                <td class="text-center">
                                                                    <span class="${p.tem_divergencia && p.qtd_separacao !== p.qtd_agendamento ? 'texto-divergencia' : ''}">
                                                                        ${p.qtd_agendamento.toFixed(2)}
                                                                    </span>
                                                                </td>
                                                                <td class="text-center">
                                                                    ${p.diferenca !== 0 ? `
                                                                        <span class="badge ${p.diferenca > 0 ? 'bg-warning' : 'bg-danger'} badge-diferenca">
                                                                            ${p.diferenca > 0 ? '+' : ''}${p.diferenca.toFixed(2)}
                                                                        </span>
                                                                    ` : `
                                                                        <span class="text-muted">0.00</span>
                                                                    `}
                                                                </td>
                                                                <td class="text-center">
                                                                    ${p.tem_divergencia ?
                        '<i class="fas fa-exclamation-triangle text-danger"></i>' :
                        '<i class="fas fa-check-circle text-success"></i>'
                    }
                                                                </td>
                                                            </tr>
                                                        `).join('')}
                                                    </tbody>
                                                    <tfoot class="table-secondary">
                                                        <tr>
                                                            <th colspan="2">Total</th>
                                                            <th class="text-center">
                                                                ${data.produtos_unificados.reduce((sum, p) => sum + p.qtd_separacao, 0).toFixed(2)}
                                                            </th>
                                                            <th class="text-center">
                                                                ${data.produtos_unificados.reduce((sum, p) => sum + p.qtd_agendamento, 0).toFixed(2)}
                                                            </th>
                                                            <th class="text-center">
                                                                ${data.produtos_unificados.reduce((sum, p) => sum + p.diferenca, 0).toFixed(2)}
                                                            </th>
                                                            <th></th>
                                                        </tr>
                                                    </tfoot>
                                                </table>
                                            </div>
                                        ` : `
                                            <p class="text-muted text-center py-3">Nenhum produto encontrado</p>
                                        `}
                                        
                                        <!-- Produtos não mapeados (se houver) -->
                                        ${data.produtos_nao_mapeados && data.produtos_nao_mapeados.length > 0 ? `
                                            <div class="alert alert-warning mt-3 mb-0">
                                                <h6 class="alert-heading">
                                                    <i class="fas fa-exclamation-triangle"></i> 
                                                    Produtos sem DE-PARA configurado:
                                                </h6>
                                                <small>
                                                    <ul class="mb-0">
                                                        ${data.produtos_nao_mapeados.map(p => `
                                                            <li>Código Atacadão: ${p.codigo_atacadao} - ${p.descricao} (Qtd: ${p.quantidade})</li>
                                                        `).join('')}
                                                    </ul>
                                                </small>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Resumo de divergências -->
                        ${data.divergencias && data.divergencias.length > 0 ? `
                            <div class="row mt-2">
                                <div class="col-12">
                                    <div class="alert alert-info py-2 mb-0">
                                        <small>
                                            <strong>Resumo:</strong> ${data.divergencias.join(' | ')}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;

                // Mostrar resultado
                Swal.fire({
                    title: `Protocolo ${protocolo}`,
                    html: htmlComparacao,
                    width: '1100px',
                    showCancelButton: false,
                    confirmButtonText: data.agendamento_confirmado ? 'OK' : 'Atualizar Status',
                    confirmButtonColor: data.agendamento_confirmado
                        ? (window.Notifications?.colors?.success || '#28a745')
                        : (window.Notifications?.colors?.warning || '#ffc107')
                }).then((result) => {
                    if (result.isConfirmed && !data.agendamento_confirmado) {
                        // Atualizar status da separação
                        this.atualizarStatusSeparacao(loteId, data.data_aprovada, data.agendamento_confirmado);
                    }
                });

            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: data.message || 'Erro ao verificar protocolo',
                    confirmButtonText: 'OK'
                });
            }
        } catch (error) {
            console.error('Erro ao verificar protocolo:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao comunicar com o servidor',
                confirmButtonText: 'OK'
            });
        }
    }

    async atualizarStatusSeparacao(loteId, dataAprovada, confirmado) {
        try {
            const response = await fetch('/carteira/api/atualizar-status-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    agendamento: dataAprovada,
                    agendamento_confirmado: confirmado
                })
            });

            const data = await response.json();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Status Atualizado',
                    text: 'Dados da separação atualizados com sucesso',
                    confirmButtonText: 'OK'
                }).then(() => {
                    // Recarregar separações se modal estiver aberto
                    if (window.modalSeparacoes && document.getElementById('modal-pedido-numero')) {
                        const numPedido = document.getElementById('modal-pedido-numero').textContent;
                        if (numPedido && window.modalSeparacoes.carregarSeparacoes) {
                            window.modalSeparacoes.carregarSeparacoes(numPedido);
                        }
                    }
                });
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Erro ao atualizar status:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao atualizar status da separação',
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * 📝 ABRIR MODAL DE CADASTRO DE-PARA
     * Abre modal para cadastrar mapeamento de produtos
     * 
     * @param {Array} produtosSemDePara - Lista de produtos sem mapeamento
     */
    abrirModalDePara(produtosSemDePara) {
        if (!produtosSemDePara || produtosSemDePara.length === 0) {
            return;
        }

        const produto = produtosSemDePara[0];

        Swal.fire({
            title: 'Cadastrar De-Para',
            html: `
                <form id="formDePara">
                    <div class="mb-3">
                        <label class="form-label">Nosso Código:</label>
                        <input type="text" class="form-control" value="${produto.codigo}" readonly>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Nossa Descrição:</label>
                        <input type="text" class="form-control" value="${produto.descricao}" readonly>
                    </div>
                    <hr>
                    <div class="mb-3">
                        <label class="form-label">Código Atacadão:</label>
                        <input type="text" id="codigo_atacadao" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Descrição Atacadão:</label>
                        <input type="text" id="descricao_atacadao" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Fator de Conversão:</label>
                        <input type="number" id="fator_conversao" class="form-control" value="1.0" step="0.0001" min="0.0001">
                    </div>
                </form>
            `,
            showCancelButton: true,
            confirmButtonText: 'Salvar',
            cancelButtonText: 'Cancelar',
            preConfirm: () => {
                const codigo_atacadao = document.getElementById('codigo_atacadao').value;
                const descricao_atacadao = document.getElementById('descricao_atacadao').value;
                const fator_conversao = document.getElementById('fator_conversao').value;

                if (!codigo_atacadao || !descricao_atacadao) {
                    Swal.showValidationMessage('Preencha todos os campos obrigatórios');
                    return false;
                }

                return {
                    codigo_nosso: produto.codigo,
                    codigo_atacadao: codigo_atacadao,
                    descricao_atacadao: descricao_atacadao,
                    fator_conversao: parseFloat(fator_conversao)
                };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.salvarDePara(result.value);
            }
        });
    }

    /**
     * 💾 SALVAR DE-PARA
     * Salva o mapeamento de produtos no banco
     */
    async salvarDePara(dados) {
        try {
            const response = await fetch('/portal/atacadao/cadastrar_depara', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(dados)
            });

            const data = await response.json();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'De-Para Cadastrado!',
                    text: 'Mapeamento salvo com sucesso',
                    timer: 2000,
                    showConfirmButton: false
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: data.message || 'Erro ao salvar De-Para'
                });
            }
        } catch (error) {
            console.error('Erro ao salvar De-Para:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao comunicar com o servidor'
            });
        }
    }

    /**
     * 💾 GRAVAR PROTOCOLO
     * Grava o protocolo retornado pelo portal
     */
    async gravarProtocolo(loteId, protocolo) {
        try {
            await fetch('/portal/atacadao/agendamento/gravar_protocolo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    lote_id: loteId,
                    protocolo: protocolo
                })
            });
        } catch (error) {
            console.error('Erro ao gravar protocolo:', error);
        }
    }

    /**
     * 📅 FORMATAR DATA
     * Formata data para exibição BR
     */
    formatarData(data) {
        return window.Formatters.data(data) || '-';
    }

    /**
     * 🔑 OBTER CSRF TOKEN
     * Obtém o token CSRF para requisições
     */
    getCSRFToken() {
        return window.Security.getCSRFToken();
    }

    /**
     * 🆕 Toast de sucesso no canto superior direito (tela livre).
     */
    _toastSucesso(titulo) {
        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: titulo,
            timer: 4000,
            showConfirmButton: false,
            timerProgressBar: true
        });
    }

    /**
     * 📡 DISPARAR EVENTO DE ATUALIZAÇÃO
     * Dispara evento customizado para atualizar interfaces
     */
    dispararEventoAtualizacao(tipo, dados) {
        const evento = new CustomEvent(tipo, { detail: dados });
        window.dispatchEvent(evento);
    }

    /**
     * 🔄 ALIASES PARA COMPATIBILIDADE
     * Mantém compatibilidade com código existente
     */

    verificarAgendamento(loteId, protocolo) {
        if (protocolo) {
            return this.verificarProtocoloNoPortal(loteId, protocolo);
        } else {
            return this.verificarPortal(loteId);
        }
    }
}

// Inicializar e exportar globalmente
window.PortalAtacadao = new PortalAtacadao();

console.log('✅ Portal Atacadão carregado com sucesso');