/**
 * 🎯 MÓDULO DE AGENDAMENTO NO PORTAL SENDAS
 * 
 * Sistema de fila inteligente:
 * - Adiciona solicitações individuais na fila
 * - Processa em lote automaticamente
 * - Notifica quando concluído
 */

class PortalSendas {
    constructor() {
        console.log('🚀 [DEBUG] Construtor PortalSendas chamado');
        try {
            this.init();
        } catch (error) {
            console.error('❌ [DEBUG] Erro no init() do PortalSendas:', error);
        }
    }

    init() {
        console.log('✅ Módulo Portal Sendas inicializado');
        // DESABILITADO - verificação periódica comentada por bug no toast
        // this.verificarFilaPeriodicamente();
    }

    /**
     * 📅 FUNÇÃO PRINCIPAL - Nova Etapa 2 com Comparação
     * Busca TODOS os itens do lote e compara via rota de SEPARAÇÃO
     */
    async agendarNoPortal(loteId, dataAgendamento) {
        console.log(`📅 [Sendas] Iniciando comparação para separação ${loteId}`);

        try {
            // ✅ CORREÇÃO: Não preencher automaticamente com D+1
            // Data virá da Separacao.agendamento ou ficará vazia para o usuário preencher
            // dataAgendamento pode vir vazia e será tratada no modal

            // Mostrar loading
            Swal.fire({
                title: 'Comparando com Planilha Sendas',
                html: `
                    <div class="text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Comparando...</span>
                        </div>
                        <p>Comparando todos os itens da separação ${loteId}...</p>
                    </div>
                `,
                allowOutsideClick: false,
                showConfirmButton: false
            });

            // Fazer comparação diretamente via rota de SEPARAÇÃO
            const response = await fetch('/portal/sendas/solicitar/separacao/comparar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    separacao_lote_id: loteId,
                    data_agendamento: dataAgendamento
                })
            });

            const resultado = await response.json();

            if (!resultado.sucesso) {
                throw new Error(resultado.erro || 'Erro na comparação');
            }

            // Processar resultados
            this.processarResultadoComparacao(resultado, loteId, dataAgendamento);
            return true;

        } catch (error) {
            console.error('Erro ao comparar separação:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro na Comparação',
                text: error.message || 'Erro ao comparar com planilha Sendas',
                confirmButtonText: 'OK'
            });
            return false;
        }
    }

    /**
     * 🎯 Processa e exibe resultado da comparação
     */
    processarResultadoComparacao(resultado, loteId, dataAgendamento) {
        console.log('Resultado da comparação:', resultado);

        // Verificar estrutura do resultado
        const resultadoPorCnpj = resultado.resultados_por_cnpj || {};
        const cnpjs = Object.keys(resultadoPorCnpj);

        if (cnpjs.length === 0) {
            Swal.fire({
                icon: 'warning',
                title: 'Nenhum resultado',
                text: 'Nenhum item foi encontrado para comparação',
                confirmButtonText: 'OK'
            });
            return;
        }

        // Para simplicidade, pegar o primeiro CNPJ (geralmente separação tem 1 CNPJ)
        const cnpj = cnpjs[0];
        const dadosCnpj = resultadoPorCnpj[cnpj];

        // ✅ CORREÇÃO: Usar data da Separação ou deixar vazia
        const dataAgendamentoFormatada = dataAgendamento || '';

        // Montar HTML do resultado
        let htmlResultado = `
            <div class="text-start">
                <h5>Resultado da Comparação</h5>
                <p><strong>CNPJ:</strong> ${cnpj}</p>
                <p><strong>Filial Sendas:</strong> ${dadosCnpj.unidade_destino_sendas || 'Não identificada'}</p>

                <!-- ✅ CAMPO DE DATA EDITÁVEL -->
                <div class="mb-3">
                    <label for="dataAgendamentoModal" class="form-label">
                        <strong>Data de Agendamento:</strong>
                        <span class="text-danger">* Obrigatório</span>
                    </label>
                    <input type="date" class="form-control" id="dataAgendamentoModal"
                           value="${dataAgendamentoFormatada}" required>
                    <div class="invalid-feedback">
                        Data de agendamento é obrigatória
                    </div>
                    ${!dataAgendamentoFormatada ?
                '<small class="text-warning">Data não definida na Separação. Por favor, informe a data desejada.</small>' :
                ''}
                </div>

                <p><strong>Total de itens:</strong> ${dadosCnpj.total_itens || 0}</p>
                <p><strong>Itens encontrados:</strong> ${dadosCnpj.itens_encontrados || 0}</p>
                <p><strong>Itens não encontrados:</strong> ${dadosCnpj.itens_nao_encontrados || 0}</p>
        `;

        // Listar itens com detalhes completos
        if (dadosCnpj.itens && dadosCnpj.itens.length > 0) {
            htmlResultado += '<hr><h6>Detalhes dos Itens:</h6>';
            htmlResultado += '<div class="table-responsive"><table class="table table-sm table-striped">';
            htmlResultado += `
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Código Solicitado</th>
                        <th>Qtd Solicitada</th>
                        <th>Código Planilha</th>
                        <th>Pedido Planilha</th>
                        <th>Saldo Disponível</th>
                        <th width="120">Qtd a Agendar</th>
                    </tr>
                </thead>
                <tbody>
            `;

            dadosCnpj.itens.forEach((item, index) => {
                const icone = item.tipo_match === 'exato' ? '✅' : '⚠️';
                const solicitado = item.solicitado || {};
                const encontrado = item.encontrado || {};
                const saldoDisponivel = encontrado.saldo_disponivel || 0;
                const qtdSolicitada = solicitado.quantidade || 0;
                const qtdPreenchida = item.tipo_match === 'exato' ?
                    Math.min(qtdSolicitada, saldoDisponivel) : 0;

                htmlResultado += `
                    <tr>
                        <td>${icone}</td>
                        <td>${solicitado.cod_produto || '-'}</td>
                        <td>${qtdSolicitada}</td>
                        <td>${encontrado.codigo_produto_sendas || '-'}</td>
                        <td>${encontrado.codigo_pedido_sendas || '-'}</td>
                        <td>
                            <span class="badge bg-${saldoDisponivel > 0 ? 'info' : 'danger'}">
                                ${saldoDisponivel}
                            </span>
                        </td>
                        <td>
                            ${item.tipo_match === 'exato' ? `
                                <input type="number"
                                       class="form-control form-control-sm qtd-principal"
                                       id="qtd_principal_${index}"
                                       data-codigo="${solicitado.cod_produto}"
                                       data-pedido="${solicitado.pedido_cliente || ''}"
                                       data-codigo-sendas="${encontrado.codigo_produto_sendas}"
                                       data-pedido-sendas="${encontrado.codigo_pedido_sendas}"
                                       data-disponivel="${saldoDisponivel}"
                                       data-solicitada="${qtdSolicitada}"
                                       min="0"
                                       max="${saldoDisponivel}"
                                       value="${qtdPreenchida}"
                                       style="width: 100px;">
                                <div class="invalid-feedback">
                                    Máx: ${saldoDisponivel}
                                </div>
                            ` : `
                                <span class="text-muted">N/A</span>
                            `}
                        </td>
                    </tr>
                `;
            });
            htmlResultado += '</tbody></table></div>';
        }

        // Se tem alternativas de filial - mostrar TUDO quando não tem match completo
        if (dadosCnpj.alternativas_filial && dadosCnpj.alternativas_filial.total_pedidos > 0) {
            const mostrarTudo = dadosCnpj.alternativas_filial.mostrar_tudo || false;

            htmlResultado += `
                <div class="alert ${mostrarTudo ? 'alert-warning' : 'alert-info'} mt-3">
                    <strong>${mostrarTudo ? '⚠️ Produtos Disponíveis na Filial:' : 'Alternativas:'}</strong><br>
                    <small>${dadosCnpj.alternativas_filial.sugestao}</small>
                </div>
                <div class="accordion mt-2" id="accordionAlternativas">
            `;

            const pedidosAlternativos = dadosCnpj.alternativas_filial.pedidos || {};
            let indexPedido = 0;

            Object.entries(pedidosAlternativos).forEach(([pedido, produtos]) => {
                // Contar quantos são matches
                const qtdMatches = produtos.filter(p => p.eh_match).length;
                const expandido = qtdMatches > 0 ? '' : 'collapsed';
                const show = qtdMatches > 0 ? 'show' : '';

                htmlResultado += `
                    <div class="accordion-item">
                        <h6 class="accordion-header" id="heading${indexPedido}">
                            <button class="accordion-button ${expandido}" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${indexPedido}">
                                Pedido: ${pedido} (${produtos.length} produtos${qtdMatches > 0 ? ` - ${qtdMatches} match(es)` : ''})
                            </button>
                        </h6>
                        <div id="collapse${indexPedido}" class="accordion-collapse collapse ${show}" data-bs-parent="#accordionAlternativas">
                            <div class="accordion-body">
                                <table class="table table-sm table-hover">
                                    <thead>
                                        <tr>
                                            <th width="30">Usar</th>
                                            <th>Código</th>
                                            <th>Descrição</th>
                                            <th>Disponível</th>
                                            <th width="100">Qtd Agendar</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                `;

                produtos.forEach((produto, indexProduto) => {
                    const produtoId = `alt_${indexPedido}_${indexProduto}`;
                    const ehMatch = produto.eh_match || false;
                    const checked = ehMatch ? 'checked' : '';
                    const qtdPreenchida = ehMatch ?
                        Math.min(produto.quantidade_pre_preenchida || 0, produto.saldo_disponivel) : 0;
                    const rowClass = ehMatch ? 'table-success' : '';

                    htmlResultado += `
                        <tr class="${rowClass}">
                            <td>
                                <input type="checkbox" class="form-check-input alternativa-produto"
                                       id="${produtoId}"
                                       data-pedido="${produto.codigo_pedido_sendas}"
                                       data-codigo="${produto.codigo_produto_sendas}"
                                       data-descricao="${produto.descricao}"
                                       data-disponivel="${produto.saldo_disponivel}"
                                       ${checked}>
                            </td>
                            <td><label for="${produtoId}">${produto.codigo_produto_nosso || produto.codigo_produto_sendas}</label></td>
                            <td>${produto.descricao}</td>
                            <td>${produto.saldo_disponivel} ${produto.unidade_medida}</td>
                            <td>
                                <input type="number" class="form-control form-control-sm qtd-alternativa"
                                       id="qtd_${produtoId}"
                                       max="${produto.saldo_disponivel}"
                                       min="0"
                                       value="${qtdPreenchida}"
                                       ${!checked ? 'disabled' : ''}>
                            </td>
                            <td>
                                ${ehMatch ?
                            `<span class="badge bg-success">MATCH</span>` :
                            `<span class="badge bg-secondary">Disponível</span>`}
                            </td>
                        </tr>
                    `;
                });

                htmlResultado += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `;
                indexPedido++;
            });

            htmlResultado += '</div>';
        }

        htmlResultado += `
            <div class="alert alert-warning mt-3">
                <strong>⚠️ Importante:</strong><br>
                Sendas aceita divergências de quantidade e produto, mas NÃO aceita divergência de filial.
                ${dadosCnpj.pode_agendar_todos ?
                'Todos os itens podem ser agendados.' :
                'Verifique os itens antes de confirmar.'}
            </div>
        </div>`;

        // Mostrar resultado e opção de confirmar
        Swal.fire({
            title: 'Comparação Concluída',
            html: htmlResultado,
            icon: 'info',
            width: '800px',
            showCancelButton: true,
            confirmButtonText: 'Confirmar Agendamento',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#28a745',
            didOpen: () => {
                // ========== VALIDAÇÃO DE QUANTIDADE PRINCIPAL ==========
                // Adicionar validação em tempo real para quantidades principais
                document.querySelectorAll('.qtd-principal').forEach(input => {
                    input.addEventListener('input', function () {
                        const disponivel = parseFloat(this.dataset.disponivel) || 0;
                        const valor = parseFloat(this.value) || 0;
                        const solicitada = parseFloat(this.dataset.solicitada) || 0;

                        // Validar se está dentro do limite
                        if (valor > disponivel) {
                            this.value = disponivel;
                            this.classList.add('is-invalid');

                            // Mostrar alerta temporário
                            const feedback = this.nextElementSibling;
                            if (feedback) {
                                feedback.style.display = 'block';
                                setTimeout(() => {
                                    feedback.style.display = 'none';
                                    this.classList.remove('is-invalid');
                                }, 3000);
                            }
                        } else if (valor < 0) {
                            this.value = 0;
                        } else {
                            this.classList.remove('is-invalid');
                        }

                        // Adicionar indicador visual
                        if (valor === solicitada && valor <= disponivel) {
                            this.classList.add('border-success');
                            this.classList.remove('border-warning');
                        } else if (valor < solicitada && valor <= disponivel) {
                            this.classList.add('border-warning');
                            this.classList.remove('border-success');
                        } else {
                            this.classList.remove('border-success', 'border-warning');
                        }
                    });
                });

                // ========== VALIDAÇÃO DE ALTERNATIVAS ==========
                // Adicionar validação para quantidades alternativas
                document.querySelectorAll('.qtd-alternativa').forEach(input => {
                    input.addEventListener('input', function () {
                        const disponivel = parseFloat(this.getAttribute('max')) || 0;
                        const valor = parseFloat(this.value) || 0;

                        // Validar se está dentro do limite
                        if (valor > disponivel) {
                            this.value = disponivel;
                            this.classList.add('is-invalid');

                            // Mostrar feedback temporário
                            setTimeout(() => {
                                this.classList.remove('is-invalid');
                            }, 2000);
                        } else if (valor < 0) {
                            this.value = 0;
                        } else {
                            this.classList.remove('is-invalid');
                        }
                    });
                });

                // ========== CHECKBOX DE ALTERNATIVAS ==========
                // Adicionar eventos aos checkboxes de alternativas
                document.querySelectorAll('.alternativa-produto').forEach(checkbox => {
                    checkbox.addEventListener('change', function () {
                        const qtdInput = document.getElementById('qtd_' + this.id);
                        if (qtdInput) {
                            if (this.checked) {
                                qtdInput.disabled = false;
                                // Pré-preencher com a quantidade mínima entre 10 e disponível
                                qtdInput.value = Math.min(10, parseFloat(this.dataset.disponivel) || 0);
                                qtdInput.focus(); // Focar no input para facilitar edição
                            } else {
                                qtdInput.disabled = true;
                                qtdInput.value = 0;
                                qtdInput.classList.remove('is-invalid');
                            }
                        }
                    });
                });
            }
        }).then(async (result) => {
            if (result.isConfirmed) {
                // ✅ CORREÇÃO: Pegar data atualizada do modal
                const dataModalElement = document.getElementById('dataAgendamentoModal');
                let dataAgendamentoFinal = dataAgendamento;

                if (dataModalElement) {
                    const dataModal = dataModalElement.value;
                    if (!dataModal) {
                        // Validar que data foi preenchida
                        Swal.fire({
                            icon: 'error',
                            title: 'Data Obrigatória',
                            text: 'Por favor, preencha a data de agendamento',
                            confirmButtonText: 'OK'
                        });
                        return;
                    }
                    dataAgendamentoFinal = dataModal;
                }

                await this.confirmarAgendamentoSeparacao(resultado, loteId, dataAgendamentoFinal);
            }
        });
    }

    /**
     * ✅ Confirma o agendamento após comparação
     */
    async confirmarAgendamentoSeparacao(resultadoComparacao, loteId, dataAgendamento) {
        try {
            console.log('Confirmando agendamento da separação:', loteId);

            // Montar itens para confirmação COM DADOS DA PLANILHA
            const itensConfirmados = [];
            const resultadoPorCnpj = resultadoComparacao.resultados_por_cnpj || {};

            // ========== COLETAR QUANTIDADES EDITADAS PELO USUÁRIO ==========
            // Primeiro, pegar as quantidades dos inputs principais
            const quantidadesPrincipais = {};
            document.querySelectorAll('.qtd-principal').forEach(input => {
                const codigo = input.dataset.codigo;
                const quantidade = parseFloat(input.value) || 0;
                if (quantidade > 0) {
                    quantidadesPrincipais[codigo] = {
                        quantidade: quantidade,
                        codigoSendas: input.dataset.codigoSendas,
                        pedidoSendas: input.dataset.pedidoSendas
                    };
                }
            });

            Object.entries(resultadoPorCnpj).forEach(([cnpj, dadosCnpj]) => {
                if (dadosCnpj.itens) {
                    dadosCnpj.itens.forEach(item => {
                        const solicitado = item.solicitado || {};
                        const encontrado = item.encontrado || {};

                        // 🔴 CORREÇÃO CRÍTICA: SEMPRE gravar dados DA PLANILHA MODELO em FilaAgendamentoSendas
                        // Conforme documento linhas 68-109: FilaAgendamentoSendas = ESPELHO da planilha
                        if (item.tipo_match === 'exato' && encontrado.codigo_pedido_sendas) {
                            // Pegar quantidade editada pelo usuário
                            const qtdEditada = quantidadesPrincipais[solicitado.cod_produto];
                            const quantidadeAgendar = qtdEditada ?
                                qtdEditada.quantidade :
                                Math.min(solicitado.quantidade, encontrado.saldo_disponivel);

                            // Só adicionar se quantidade > 0
                            if (quantidadeAgendar > 0) {
                                // ✅ GRAVAR DADOS EXATOS DA PLANILHA MODELO
                                itensConfirmados.push({
                                    // Referência ao documento origem
                                    separacao_lote_id: loteId,
                                    tipo_origem: 'separacao',
                                    documento_origem: loteId,

                                    // 🔴 DADOS DA PLANILHA MODELO (preservar EXATAMENTE como está)
                                    cnpj: cnpj,
                                    pedido_cliente: encontrado.codigo_pedido_sendas,  // ✅ VALOR COMPLETO da planilha (ex: PC123-001)
                                    cod_produto: encontrado.codigo_produto_sendas,    // ✅ Código da planilha
                                    nome_produto: encontrado.descricao,               // ✅ Descrição da planilha
                                    quantidade: quantidadeAgendar,                    // ✅ Quantidade editada pelo usuário
                                    data_agendamento: dataAgendamento,
                                    num_pedido: solicitado.num_pedido,               // num_pedido original para rastreabilidade

                                    // Dados originais da Separação para rastreabilidade interna
                                    pedido_original_separacao: solicitado.pedido_cliente,
                                    codigo_original_separacao: solicitado.cod_produto,
                                    observacao: 'Match exato com planilha'
                                });
                            }
                        } else if (item.tipo_match === 'nao_encontrado') {
                            // Item não encontrado - NÃO deve registrar pois não tem correspondência na planilha
                            // Sendas aceita divergências mas precisa de ALGUM item da filial para agendar
                            console.warn(`Item ${solicitado.cod_produto} não encontrado na planilha - será ignorado`);
                        }
                    });
                }
            });

            // Adicionar alternativas selecionadas pelo usuário
            const alternativasSelecionadas = this.obterAlternativasSelecionadas();

            // Obter num_pedido do primeiro item para usar como fallback
            let numPedidoFallback = null;
            const primeiroCnpj = Object.keys(resultadoPorCnpj)[0];
            const dadosPrimeiroCnpj = resultadoPorCnpj[primeiroCnpj];
            if (dadosPrimeiroCnpj && dadosPrimeiroCnpj.itens && dadosPrimeiroCnpj.itens.length > 0) {
                numPedidoFallback = dadosPrimeiroCnpj.itens[0].solicitado?.num_pedido;
            }

            alternativasSelecionadas.forEach(alt => {
                itensConfirmados.push({
                    // Referência ao documento origem
                    separacao_lote_id: loteId,
                    tipo_origem: 'separacao',
                    documento_origem: loteId,

                    // Dados DA PLANILHA selecionados pelo usuário
                    cnpj: Object.keys(resultadoPorCnpj)[0], // Pegar o CNPJ do resultado
                    pedido_cliente: alt.pedido,
                    cod_produto: alt.codigo,
                    nome_produto: alt.descricao,
                    quantidade: alt.quantidade,
                    data_agendamento: dataAgendamento,
                    num_pedido: numPedidoFallback,  // ✅ ADICIONADO: num_pedido (usando fallback)

                    // Marcar como alternativa
                    eh_alternativa: true,
                    observacao: 'Produto alternativo selecionado pelo usuário'
                });
            });

            if (itensConfirmados.length === 0) {
                throw new Error('Nenhum item para confirmar');
            }

            // Mostrar loading
            Swal.fire({
                title: 'Confirmando Agendamento',
                text: 'Gravando na fila de agendamento...',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // Confirmar agendamento
            const response = await fetch('/portal/sendas/solicitar/separacao/confirmar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    itens_confirmados: itensConfirmados,
                    separacao_lote_id: loteId
                })
            });

            const resultado = await response.json();

            if (resultado.sucesso) {
                Swal.fire({
                    icon: 'success',
                    title: 'Agendamento Confirmado!',
                    html: `
                        <div class="text-center">
                            <h4>Protocolo: ${resultado.protocolo}</h4>
                            <p>${resultado.mensagem || 'Agendamento realizado com sucesso'}</p>
                            <p class="mt-3"><small>Total de itens: ${resultado.total_itens || itensConfirmados.length}</small></p>
                        </div>
                    `,
                    confirmButtonText: 'OK',
                    confirmButtonColor: '#28a745'
                });

                // Atualizar interface se necessário
                // Pode recarregar a página ou atualizar elementos específicos
            } else {
                throw new Error(resultado.erro || 'Erro ao confirmar agendamento');
            }

        } catch (error) {
            console.error('Erro ao confirmar agendamento:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro ao Confirmar',
                text: error.message,
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * 📊 Mostra status da fila - COMPLETAMENTE DESABILITADA
     */
    async mostrarStatusFila(dados) {
        // FUNÇÃO COMPLETAMENTE DESABILITADA POR ERRO DE RENDERIZAÇÃO
        console.error('❌ mostrarStatusFila FOI CHAMADA MAS ESTÁ DESABILITADA!');
        console.trace('Stack trace para debug:');
        return;
    }

    /**
     * 🚀 Processa a fila em lote
     */
    async processarFila() {
        console.log('🚀 [Sendas] Processando fila em lote');

        Swal.fire({
            title: 'Processando Fila Sendas',
            html: `
                <div class="text-center">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Processando...</span>
                    </div>
                    <p>Preparando lote para envio ao portal...</p>
                </div>
            `,
            allowOutsideClick: false,
            showConfirmButton: false
        });

        try {
            // USAR O MESMO ENDPOINT DO SCHEDULER PARA GARANTIR CONSISTÊNCIA
            // Este endpoint já processa corretamente com todos os itens
            const response = await fetch('/portal/sendas/fila/processar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();

            if (result.success) {
                // O endpoint /processar já marca os itens como processados internamente

                Swal.fire({
                    icon: 'success',
                    title: 'Fila Processada!',
                    html: `
                        <div class="text-center">
                            <p><strong>${result.total_processado || 0}</strong> grupos enviados para processamento</p>
                            ${result.job_id ? `
                                <p class="text-muted mt-2">
                                    <i class="fas fa-info-circle"></i>
                                    O processamento está sendo feito em background
                                </p>
                                <small>Job ID: ${result.job_id}</small>
                            ` : ''}
                        </div>
                    `,
                    confirmButtonText: 'OK'
                });
            } else {
                throw new Error(result.error || 'Erro no processamento');
            }

        } catch (error) {
            console.error('Erro ao processar fila:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao processar fila: ' + error.message,
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * 🔍 Verifica status de agendamento
     */
    async verificarPortal(loteId) {
        // Por enquanto, apenas mostrar status da fila
        const response = await fetch('/portal/sendas/fila/status');
        const data = await response.json();

        Swal.fire({
            icon: 'info',
            title: 'Status da Fila Sendas',
            html: `
                <div class="text-center">
                    <p><strong>${data.pendentes_total}</strong> itens pendentes</p>
                    ${Object.entries(data.pendentes_por_cnpj).map(([cnpj, total]) =>
                `<p><small>${cnpj}: ${total} itens</small></p>`
            ).join('')}
                </div>
            `,
            confirmButtonText: 'OK'
        });
    }

    /**
     * 🔄 Verifica fila periodicamente - COMPLETAMENTE DESABILITADA
     */
    verificarFilaPeriodicamente() {
        // FUNÇÃO COMPLETAMENTE DESABILITADA
        console.warn('⚠️ verificarFilaPeriodicamente está DESABILITADO');
        return;
    }

    /**
     * Obtém CSRF Token
     */
    getCSRFToken() {
        return window.Security.getCSRFToken();
    }

    /**
     * 🔍 Obtém alternativas selecionadas pelo usuário
     */
    obterAlternativasSelecionadas() {
        const alternativas = [];

        // Buscar todos os checkboxes de alternativas marcados
        document.querySelectorAll('.alternativa-produto:checked').forEach(checkbox => {
            const qtdInput = document.getElementById('qtd_' + checkbox.id);
            const quantidade = parseFloat(qtdInput.value) || 0;

            if (quantidade > 0) {
                alternativas.push({
                    pedido: checkbox.dataset.pedido,
                    codigo: checkbox.dataset.codigo,
                    descricao: checkbox.dataset.descricao,
                    disponivel: parseFloat(checkbox.dataset.disponivel),
                    quantidade: Math.min(quantidade, parseFloat(checkbox.dataset.disponivel))
                });
            }
        });

        return alternativas;
    }
}

// Exportar globalmente
window.PortalSendas = new PortalSendas();

console.log('✅ Portal Sendas carregado - Sistema de fila ativo');