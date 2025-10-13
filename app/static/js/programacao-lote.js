/**
 * JavaScript para Programação em Lote - Versão 3ª Etapa
 * Implementa análise de estoques, sugestão de datas e priorização
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Iniciando script de programação em lote v3...');
    
    // Elementos
    const checkTodos = document.getElementById('checkTodos');
    const btnSelecionarTodos = document.getElementById('btnSelecionarTodos');
    const btnProcessarLote = document.getElementById('btnProcessarLote');
    const btnAnalisarEstoques = document.getElementById('btnAnalisarEstoques');
    const btnSugerirDatas = document.getElementById('btnSugerirDatas');
    // const btnImportarAgendamentos = document.getElementById('btnImportarAgendamentos'); // ⚠️ REMOVIDO

    // Estado
    let cnpjsSelecionados = new Set();
    let dadosRuptura = {};
    
    // Garantir que window.dadosRuptura esteja disponível globalmente
    window.dadosRuptura = dadosRuptura;
    
    // Inicializar
    inicializar();
    
    function inicializar() {
        console.log('Inicializando event listeners...');
        
        // Botões principais
        if (btnAnalisarEstoques) {
            btnAnalisarEstoques.addEventListener('click', handleAnalisarEstoques);
            console.log('Botão analisar estoques configurado');
        }
        
        if (btnSugerirDatas) {
            btnSugerirDatas.addEventListener('click', handleSugerirDatas);
            console.log('Botão sugerir datas configurado');
        }
        
        if (btnSelecionarTodos) {
            btnSelecionarTodos.addEventListener('click', handleSelecionarTodos);
        }
        
        if (btnProcessarLote) {
            btnProcessarLote.addEventListener('click', handleProcessarLote);
        }

        // ⚠️ REMOVIDO: btnImportarAgendamentos não existe mais
        // if (btnImportarAgendamentos) {
        //     btnImportarAgendamentos.addEventListener('click', handleImportarAgendamentos);
        //     console.log('Botão importar agendamentos configurado');
        // }

        // Checkboxes
        if (checkTodos) {
            checkTodos.addEventListener('change', handleCheckTodos);
        }
        
        document.querySelectorAll('.check-cnpj').forEach(checkbox => {
            checkbox.addEventListener('change', handleCheckCnpj);
        });
        
        // Botões das linhas
        document.querySelectorAll('.btn-expandir').forEach(btn => {
            btn.addEventListener('click', handleExpandir);
        });
        
        document.querySelectorAll('.btn-priorizar').forEach(btn => {
            btn.addEventListener('click', handlePriorizar);
        });
        
        document.querySelectorAll('.btn-analisar-ruptura').forEach(btn => {
            btn.addEventListener('click', handleAnalisarRupturaIndividual);
        });
        
        // Campos de data - auto D+1
        document.querySelectorAll('.data-expedicao').forEach(input => {
            input.addEventListener('change', handleDataExpedicaoChange);
        });
        
        // Calcular totais
        calcularTotais();
        
        // Analisar ruptura inicial para todos os CNPJs
        analisarRupturaInicial();
    }
    
    // Analisar ruptura inicial
    async function analisarRupturaInicial() {
        console.log('Analisando ruptura inicial...');
        const botoes = document.querySelectorAll('.btn-analisar-ruptura');
        
        for (const btn of botoes) {
            const cnpj = btn.dataset.cnpj;
            await analisarRupturaSimplificada(cnpj, btn);
        }
    }
    
    // Análise simplificada de ruptura para o botão
    async function analisarRupturaSimplificada(cnpj, btn) {
        try {
            // Usar novo endpoint que analisa TODOS os pedidos do CNPJ
            console.log(`Analisando ruptura para CNPJ ${cnpj} - TODOS os pedidos`);

            // Fazer URL encoding do CNPJ para evitar problemas com caracteres especiais (/, -, .)
            const cnpjEncoded = encodeURIComponent(cnpj);
            console.log(`CNPJ original: ${cnpj} | CNPJ encoded: ${cnpjEncoded}`);

            // Fazer chamada ao endpoint que consolida TODOS os produtos do CNPJ
            console.log(`Fazendo requisição para: /carteira/programacao-lote/api/analisar-ruptura-cnpj/${cnpjEncoded}`);
            const response = await fetch(`/carteira/programacao-lote/api/analisar-ruptura-cnpj/${cnpjEncoded}`);
            
            console.log('Status da resposta:', response.status);
            console.log('Status OK?', response.ok);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Erro na resposta da API:', response.status, errorText);
                throw new Error(`API retornou erro ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('Dados da API de ruptura (CNPJ completo):', data);

            // Novo formato: { success: true, cnpj: "...", data: { resumo: {...}, itens: [...], itens_disponiveis: [...] } }
            if (data.success && data.data && data.data.resumo) {
                const resumo = data.data.resumo;
                const disponibilidade = Math.round(resumo.percentual_disponibilidade || 0);

                // Usar data_disponibilidade_total que vem da API
                let dataCompleta = resumo.data_disponibilidade_total;

                // Tratar diferentes formatos de resposta
                if (!dataCompleta || dataCompleta === 'null' || dataCompleta === 'agora') {
                    dataCompleta = 'Disponível';
                } else if (dataCompleta.includes('-')) {
                    // Formatar data ISO (YYYY-MM-DD) para DD/MM
                    const partes = dataCompleta.split('-');
                    if (partes.length === 3) {
                        const [ano, mes, dia] = partes;
                        dataCompleta = `${dia}/${mes}`;  // Formato DD/MM
                    }
                }

                console.log(`Data completa formatada: ${dataCompleta}`);
                console.log(`Disponibilidade: ${disponibilidade}%`);

                // Atualizar botão
                const span = btn.querySelector('.ruptura-info');
                if (!span) {
                    console.error('Span .ruptura-info não encontrado');
                    return;
                }

                // Formatação consistente: X% | Disp. DD/MM ou X% | Disponível
                if (disponibilidade === 100) {
                    // 100% disponível - sempre mostra "Disponível"
                    span.innerHTML = `100% | Disponível`;
                    btn.classList.remove('btn-primary', 'btn-warning', 'btn-danger');
                    btn.classList.add('btn-success');
                } else {
                    // Tem ruptura - mostrar data se disponível, senão mostrar texto apropriado
                    let textoData;
                    if (dataCompleta && dataCompleta !== 'Disponível') {
                        // Tem data de disponibilidade calculada
                        textoData = `Disp. ${dataCompleta}`;
                    } else {
                        // Sem data (sem produção programada)
                        textoData = disponibilidade >= 80 ? 'Parcial' : 'Sem Produção';
                    }

                    span.innerHTML = `${disponibilidade}% | ${textoData}`;

                    // Cor do botão conforme severidade
                    btn.classList.remove('btn-primary', 'btn-success', 'btn-warning', 'btn-danger');
                    if (disponibilidade >= 80) {
                        btn.classList.add('btn-warning');  // Amarelo: quase pronto
                    } else {
                        btn.classList.add('btn-danger');   // Vermelho: ruptura crítica
                    }
                }

                // Guardar dados completos para uso no modal
                dadosRuptura[cnpj] = {
                    disponibilidade: disponibilidade,
                    dataCompleta: dataCompleta,
                    resumo: resumo,
                    itens: data.data.itens || [],
                    itens_disponiveis: data.data.itens_disponiveis || []
                };

                console.log(`Ruptura analisada para CNPJ ${cnpj}: ${disponibilidade}% disponível (${resumo.qtd_itens_disponiveis}/${resumo.total_itens} itens)`);
            } else {
                // Se falhou, mostrar como disponível
                console.log('Falha na API ou sem dados, mostrando como disponível');
                const span = btn.querySelector('.ruptura-info');
                if (span) {
                    span.innerHTML = `100% | Disponível`;
                    btn.classList.remove('btn-primary', 'btn-warning', 'btn-danger');
                    btn.classList.add('btn-success');
                }
            }
            
        } catch (error) {
            console.error('Erro ao analisar ruptura para CNPJ', cnpj, ':', error);
            console.error('Mensagem:', error.message);
            console.error('Stack:', error.stack);
            
            const span = btn.querySelector('.ruptura-info');
            if (span) {
                // Mostrar erro ao invés de valor padrão
                span.innerHTML = 'Erro ao analisar';
                btn.classList.remove('btn-primary', 'btn-success', 'btn-warning');
                btn.classList.add('btn-danger');
            }
        }
    }
    
    // Analisar Estoques
    async function handleAnalisarEstoques() {
        console.log('Analisar estoques clicado');
        const cardAnalise = document.getElementById('cardAnaliseEstoques');
        
        if (cardAnalise.classList.contains('d-none')) {
            cardAnalise.classList.remove('d-none');
            await carregarAnaliseEstoques();
        } else {
            cardAnalise.classList.add('d-none');
        }
    }
    
    // Carregar análise de estoques
    async function carregarAnaliseEstoques() {
        try {
            const titulo = document.querySelector('h1').textContent;
            const rede = titulo.includes('Atacadão') ? 'atacadao' : 'sendas';
            
            const tbody = document.querySelector('#tabelaAnaliseEstoques tbody');
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">Carregando análise...</td></tr>';
            
            const response = await fetch(`/carteira/programacao-lote/api/analisar-estoques/${rede}`);
            const result = await response.json();
            
            if (result.success) {
                renderizarTabelaEstoques(result.data);
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Erro ao carregar</td></tr>';
            }
        } catch (error) {
            console.error('Erro:', error);
            const tbody = document.querySelector('#tabelaAnaliseEstoques tbody');
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Erro ao carregar</td></tr>';
        }
    }
    
    // Renderizar tabela de estoques
    function renderizarTabelaEstoques(dados) {
        const tbody = document.querySelector('#tabelaAnaliseEstoques tbody');
        tbody.innerHTML = '';
        
        dados.forEach(item => {
            const tr = document.createElement('tr');
            const insuficiente = item.estoque_atual < item.qtd_total;
            
            if (insuficiente) {
                tr.classList.add('table-warning');
            }
            
            tr.innerHTML = `
                <td>${item.cod_produto}</td>
                <td>${item.nome_produto}</td>
                <td class="text-end">${item.qtd_total.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                <td class="text-end">R$ ${item.valor_total.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                <td class="text-end ${insuficiente ? 'text-danger fw-bold' : ''}">${item.estoque_atual.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                <td class="text-center">${item.data_disponivel}</td>
                <td class="text-end">${item.projecao_15_dias.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            `;
            
            tbody.appendChild(tr);
        });
    }
    
    // Sugerir Datas - CONFIRMAÇÃO: Expedição 2ª-5ª, Agendamento D+1
    async function handleSugerirDatas() {
        console.log('Sugerir datas clicado');
        try {
            let cnpjs = [];
            if (cnpjsSelecionados.size > 0) {
                cnpjs = Array.from(cnpjsSelecionados);
            } else {
                document.querySelectorAll('.cnpj-row').forEach(row => {
                    cnpjs.push(row.dataset.cnpj);
                });
            }
            
            if (cnpjs.length === 0) {
                Swal.fire('Atenção', 'Nenhum CNPJ disponível', 'warning');
                return;
            }
            
            const titulo = document.querySelector('h1').textContent;
            const rede = titulo.includes('Atacadão') ? 'atacadao' : 'sendas';
            
            console.log('Enviando para API:', {rede, cnpjs_count: cnpjs.length});
            
            Swal.fire({
                title: 'Sugerindo datas...',
                text: 'Calculando datas otimizadas (2ª-5ª expedição, agendamento D+1)',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Criar objeto com ordem dos CNPJs baseada na posição atual na tela
            const ordem = {};
            const rows = document.querySelectorAll('tbody tr.cnpj-row');
            rows.forEach((row, index) => {
                const cnpj = row.dataset.cnpj;
                if (cnpj) {
                    ordem[cnpj] = index;
                }
            });
            
            const response = await fetch(`/carteira/programacao-lote/api/sugerir-datas/${rede}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cnpjs: cnpjs,
                    ordem: ordem
                })
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Erro na resposta:', errorText);
                Swal.fire('Erro', `Erro ${response.status}: ${errorText.substring(0, 100)}`, 'error');
                return;
            }
            
            const result = await response.json();
            console.log('Resultado da API:', result);
            
            if (result.success) {
                // Aplicar sugestões
                let datasAplicadas = 0;
                let cnpjsComRuptura = 0;
                let cnpjsAjustados = 0;
                
                for (const [cnpj, datas] of Object.entries(result.sugestoes)) {
                    const inputExp = document.querySelector(`.data-expedicao[data-cnpj="${cnpj}"]`);
                    const inputAge = document.querySelector(`.data-agendamento[data-cnpj="${cnpj}"]`);
                    const row = document.querySelector(`tr.cnpj-row[data-cnpj="${cnpj}"]`);
                    
                    if (inputExp) {
                        inputExp.value = datas.expedicao;
                        datasAplicadas++;
                        
                        // Adicionar indicador visual se há ruptura
                        if (datas.tem_ruptura) {
                            cnpjsComRuptura++;
                            inputExp.style.backgroundColor = '#fff3cd';
                            inputExp.title = `Disponibilidade de estoque: ${datas.disponibilidade_estoque}`;
                            
                            // Se a data de expedição foi ajustada devido ao estoque
                            if (datas.expedicao < datas.disponibilidade_estoque) {
                                cnpjsAjustados++;
                                inputExp.style.backgroundColor = '#ffe6e6';
                            }
                        } else {
                            inputExp.style.backgroundColor = '';
                            inputExp.title = '';
                        }
                    }
                    
                    if (inputAge) {
                        inputAge.value = datas.agendamento;
                        
                        // Adicionar indicador visual se há ruptura
                        if (datas.tem_ruptura) {
                            inputAge.style.backgroundColor = '#fff3cd';
                            inputAge.title = `Disponibilidade de estoque: ${datas.disponibilidade_estoque}`;
                        } else {
                            inputAge.style.backgroundColor = '';
                            inputAge.title = '';
                        }
                    }
                    
                    // Badge de ruptura removido - não mais necessário
                    // O indicador de ruptura agora é mostrado apenas no campo de agendamento (amarelo)
                }
                
                // Preparar mensagem detalhada
                let mensagemDetalhes = '';
                if (cnpjsComRuptura > 0) {
                    mensagemDetalhes = `<div class="alert alert-warning mt-3">
                        <strong>⚠️ Atenção:</strong><br>
                        ${cnpjsComRuptura} CNPJ(s) com ruptura de estoque detectada<br>
                        ${cnpjsAjustados > 0 ? `${cnpjsAjustados} data(s) ajustada(s) para disponibilidade de estoque` : ''}
                        <br><small>Campos em amarelo indicam ruptura</small>
                    </div>`;
                }
                
                Swal.fire({
                    icon: 'success',
                    title: 'Datas Sugeridas!',
                    html: `<strong>Regras aplicadas:</strong><br>
                          ✅ Expedições: 2ª a 5ª feira (iniciando D+2 úteis)<br>
                          ✅ Agendamentos: D+1 da expedição<br>
                          ✅ Máximo: 30 CNPJs por dia<br>
                          ✅ Análise de ruptura considerada<br>
                          <br>
                          <strong>${datasAplicadas} CNPJs configurados</strong>
                          ${mensagemDetalhes}`,
                    confirmButtonText: 'OK'
                });
            } else {
                Swal.fire('Erro', result.error || 'Erro ao sugerir datas', 'error');
            }
        } catch (error) {
            console.error('Erro completo:', error);
            Swal.fire('Erro', `Erro ao processar: ${error.message}`, 'error');
        }
    }
    
    // Priorizar CNPJ
    function handlePriorizar(e) {
        const cnpj = e.currentTarget.dataset.cnpj;
        const row = document.querySelector(`tr.cnpj-row[data-cnpj="${cnpj}"]`);
        const detailRow = document.querySelector(`tr[data-cnpj-detail="${cnpj}"]`);
        const tbody = row.parentElement;
        
        tbody.insertBefore(row, tbody.firstChild);
        if (detailRow) {
            tbody.insertBefore(detailRow, row.nextSibling);
        }
        
        Swal.fire({
            icon: 'success',
            title: 'Priorizado!',
            text: 'CNPJ movido para o topo da lista',
            timer: 1500,
            showConfirmButton: false
        });
        
        // Re-analisar ruptura com nova ordem
        analisarRupturaInicial();
    }
    
    // Analisar ruptura individual - mostrar detalhes
    async function handleAnalisarRupturaIndividual(e) {
        e.preventDefault();
        e.stopPropagation();

        const btn = e.currentTarget;
        const cnpj = btn.dataset.cnpj;

        console.log('handleAnalisarRupturaIndividual chamado para CNPJ:', cnpj);

        // Verificar se já temos dados em cache
        if (dadosRuptura[cnpj] && dadosRuptura[cnpj].resumo) {
            console.log('Usando dados em cache para', cnpj);
            console.log('Itens em ruptura:', dadosRuptura[cnpj].itens?.length || 0);
            console.log('Itens disponíveis:', dadosRuptura[cnpj].itens_disponiveis?.length || 0);
            mostrarModalRupturaDetalhado({
                resumo: dadosRuptura[cnpj].resumo,
                itens: dadosRuptura[cnpj].itens || [],
                itens_disponiveis: dadosRuptura[cnpj].itens_disponiveis || []
            }, cnpj);
            return;
        }

        // Guardar texto original antes do try
        const originalText = btn.innerHTML;

        try {
            // Mostrar loading
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando...';

            // Fazer URL encoding do CNPJ para evitar problemas com caracteres especiais (/, -, .)
            const cnpjEncoded = encodeURIComponent(cnpj);
            console.log(`CNPJ original: ${cnpj} | CNPJ encoded: ${cnpjEncoded}`);

            // Fazer requisição para API de ruptura consolidada (TODOS os pedidos do CNPJ)
            console.log(`Fazendo requisição para: /carteira/programacao-lote/api/analisar-ruptura-cnpj/${cnpjEncoded}`);
            const response = await fetch(`/carteira/programacao-lote/api/analisar-ruptura-cnpj/${cnpjEncoded}`);

            console.log('Status da resposta:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Erro na resposta da API:', response.status, errorText);
                throw new Error(`API retornou erro ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('Resposta da API (modal):', data);

            // Restaurar botão
            btn.disabled = false;
            btn.innerHTML = originalText;

            // Novo formato: { success: true, cnpj: "...", data: { resumo: {...}, itens: [...], itens_disponiveis: [...] } }
            if (data.success && data.data && data.data.resumo) {
                // Salvar em cache
                dadosRuptura[cnpj] = {
                    ...(dadosRuptura[cnpj] || {}),
                    resumo: data.data.resumo,
                    itens: data.data.itens || [],
                    itens_disponiveis: data.data.itens_disponiveis || []
                };

                // Mostrar modal com dados completos
                console.log('Chamando mostrarModalRupturaDetalhado');
                console.log('Itens em ruptura:', data.data.itens?.length || 0);
                console.log('Itens disponíveis:', data.data.itens_disponiveis?.length || 0);
                mostrarModalRupturaDetalhado(data.data, cnpj);
            } else {
                console.error('API retornou erro:', data);
                Swal.fire({
                    icon: 'error',
                    title: 'Erro na análise',
                    text: data.error || 'Erro ao analisar ruptura'
                });
            }
        } catch (error) {
            console.error('Erro ao analisar ruptura:', error);
            btn.disabled = false;
            btn.innerHTML = originalText;

            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao analisar ruptura do CNPJ: ' + error.message
            });
        }
    }
    
    // Funções auxiliares de formatação
    function formatarValor(valor) {
        if (valor === null || valor === undefined) return '0,00';
        return valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    
    function formatarNumero(numero) {
        if (numero === null || numero === undefined) return '0';
        // Sem casas decimais para quantidades
        return Math.round(numero).toLocaleString('pt-BR');
    }
    
    function formatarNumeroDecimal(numero) {
        if (numero === null || numero === undefined) return '0,00';
        return numero.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    
    // Função para formatar data de YYYY-MM-DD para DD/MM/YYYY
    function formatarData(data) {
        if (!data) return '-';
        const partes = data.split('-');
        if (partes.length === 3) {
            return `${partes[2]}/${partes[1]}/${partes[0]}`;
        }
        return data;
    }
    
    // Variável global para guardar dados do modal atual
    let dadosModalAtual = null;
    
    // Função para mostrar modal detalhado de ruptura
    function mostrarModalRupturaDetalhado(data, cnpj) {
        console.log('Mostrando modal de ruptura para CNPJ:', cnpj);
        console.log('Dados recebidos:', data);
        
        // Guardar dados para uso nas abas
        dadosModalAtual = data;
        window.dadosModalAtual = data; // Disponibilizar globalmente
        
        try {
            const resumo = data.resumo;
            const cores = {
                'CRITICA': 'danger',
                'ALTA': 'warning', 
                'MEDIA': 'info',
                'BAIXA': 'secondary'
            };
            
            // Criar modal se não existir
            let modal = document.getElementById('modalRupturaLote');
            if (!modal) {
                console.log('Modal não existe, criando...');
                modal = criarModalRupturaLote();
            }
            
            // Verificar se elementos existem antes de atualizar
            const tituloElement = document.getElementById('modalRupturaLoteTitulo');
            if (!tituloElement) {
                console.error('Elemento modalRupturaLoteTitulo não encontrado');
                return;
            }
            
            // Atualizar título com botões de toggle como na carteira agrupada
            tituloElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        Análise de Ruptura - Pedido ${resumo.num_pedido}
                        <span class="badge bg-${cores[resumo.criticidade] || 'info'} ms-2">
                            ${resumo.criticidade || 'MÉDIA'}
                        </span>
                    </div>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-danger active" id="btnMostrarRuptura"
                                onclick="window.mostrarItensRupturaModal()">
                            <i class="fas fa-exclamation-triangle me-1"></i>
                            Ruptura (${resumo.qtd_itens_ruptura || 0})
                        </button>
                        <button type="button" class="btn btn-outline-success" id="btnMostrarDisponiveis"
                                onclick="window.mostrarItensDisponiveisModal()">
                            <i class="fas fa-check-circle me-1"></i>
                            Disponíveis (${resumo.qtd_itens_disponiveis || 0})
                        </button>
                        <button type="button" class="btn btn-outline-primary" id="btnMostrarTodos"
                                onclick="window.mostrarTodosItensModal()">
                            <i class="fas fa-list me-1"></i>
                            Todos (${resumo.total_itens || 0})
                        </button>
                    </div>
                </div>
            `;
            
            // Atualizar resumo igual à carteira agrupada
            const resumoElement = document.getElementById('modalRupturaLoteResumo');
            if (!resumoElement) {
                console.error('Elemento modalRupturaLoteResumo não encontrado');
                return;
            }
            
            resumoElement.innerHTML = `
                <div class="row">
                    <div class="col-md-3">
                        <div class="text-center">
                            <strong>Disponibilidade</strong><br>
                            <span class="h4 text-success">${Math.round(resumo.percentual_disponibilidade || 0)}%</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <strong>Em Ruptura</strong><br>
                            <span class="h4 text-danger">${resumo.percentual_ruptura || 0}%</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <strong>Valor Total</strong><br>
                            <span class="h5">R$ ${formatarValor(resumo.valor_total_pedido)}</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <strong>Valor em Risco</strong><br>
                            <span class="h5 text-danger">R$ ${formatarValor(resumo.valor_com_ruptura)}</span>
                        </div>
                    </div>
                </div>
            `;
            
            // Atualizar tabela de itens com campos corretos da API
            const tbody = document.getElementById('modalRupturaLoteItens');
            tbody.innerHTML = '';
            
            if (data.itens && data.itens.length > 0) {
                data.itens.forEach(item => {
                    const tr = document.createElement('tr');
                    // Usar campos corretos: qtd_saldo, estoque_atual, estoque_min_d7, data_producao, qtd_producao, data_disponivel
                    tr.innerHTML = `
                        <td>${item.cod_produto}</td>
                        <td>${item.nome_produto}</td>
                        <td class="text-end">${formatarNumero(item.qtd_saldo)}</td>
                        <td class="text-end ${item.estoque_atual < 0 ? 'text-danger' : ''}">
                            ${formatarNumero(item.estoque_atual || 0)}
                        </td>
                        <td class="text-end ${item.estoque_min_d7 < 0 ? 'text-danger' : ''}">
                            ${formatarNumero(item.estoque_min_d7)}
                        </td>
                        <td class="text-center">
                            ${item.data_producao ? 
                                `<span class="badge bg-primary">
                                    ${formatarData(item.data_producao)}
                                    <br>
                                    <small>${formatarNumero(item.qtd_producao)} un</small>
                                </span>` : 
                                '<span class="badge bg-danger">Sem Produção</span>'
                            }
                        </td>
                        <td class="text-center">
                            ${item.data_disponivel ? 
                                `<span class="badge bg-success">
                                    ${formatarData(item.data_disponivel)}
                                </span>` : 
                                '<span class="badge bg-secondary">Indisponível</span>'
                            }
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center text-muted">
                            <i class="fas fa-check-circle text-success me-2"></i>
                            Nenhum item com ruptura
                        </td>
                    </tr>
                `;
            }
            
            // Mostrar modal
            console.log('Tentando mostrar modal...');
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
            console.log('Modal mostrado com sucesso');
            
        } catch (error) {
            console.error('Erro ao mostrar modal de ruptura:', error);
            console.error('Stack trace:', error.stack);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao exibir detalhes da ruptura: ' + error.message
            });
        }
    }
    
    // Funções para alternar entre as abas do modal
    window.mostrarItensRupturaModal = function() {
        if (!dadosModalAtual) return;
        
        // Atualizar botões
        document.querySelectorAll('#modalRupturaLote .btn-group button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById('btnMostrarRuptura')?.classList.add('active');
        
        // Atualizar título da seção
        const tituloSecao = document.querySelector('#modalRupturaLote h6');
        if (tituloSecao) {
            tituloSecao.innerHTML = '<i class="fas fa-exclamation-triangle text-danger me-2"></i>Itens com Ruptura de Estoque:';
        }
        
        // Atualizar tabela
        const tbody = document.getElementById('modalRupturaLoteItens');
        const itens = dadosModalAtual.itens || [];
        
        if (itens.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        Nenhum item com ruptura
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        itens.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.cod_produto}</td>
                <td>${item.nome_produto}</td>
                <td class="text-end">${formatarNumero(item.qtd_saldo)}</td>
                <td class="text-end ${item.estoque_atual < 0 ? 'text-danger' : ''}">
                    ${formatarNumero(item.estoque_atual || 0)}
                </td>
                <td class="text-end ${item.estoque_min_d7 < 0 ? 'text-danger' : ''}">
                    ${formatarNumero(item.estoque_min_d7)}
                </td>
                <td class="text-center">
                    ${item.data_producao ? 
                        `<span class="badge bg-primary">
                            ${formatarData(item.data_producao)}
                            <br>
                            <small>${formatarNumero(item.qtd_producao)} un</small>
                        </span>` : 
                        '<span class="badge bg-danger">Sem Produção</span>'
                    }
                </td>
                <td class="text-center">
                    ${item.data_disponivel ? 
                        `<span class="badge bg-success">
                            ${formatarData(item.data_disponivel)}
                        </span>` : 
                        '<span class="badge bg-secondary">Indisponível</span>'
                    }
                </td>
            `;
            tbody.appendChild(tr);
        });
    };
    
    window.mostrarItensDisponiveisModal = function() {
        if (!dadosModalAtual) return;
        
        // Atualizar botões
        document.querySelectorAll('#modalRupturaLote .btn-group button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById('btnMostrarDisponiveis')?.classList.add('active');
        
        // Atualizar título da seção
        const tituloSecao = document.querySelector('#modalRupturaLote h6');
        if (tituloSecao) {
            tituloSecao.innerHTML = '<i class="fas fa-check-circle text-success me-2"></i>Itens com Disponibilidade:';
        }
        
        // Atualizar tabela
        const tbody = document.getElementById('modalRupturaLoteItens');
        const itens = dadosModalAtual.itens_disponiveis || [];
        
        if (itens.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                        Nenhum item disponível
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        itens.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.cod_produto}</td>
                <td>${item.nome_produto}</td>
                <td class="text-end">${formatarNumero(item.qtd_saldo)}</td>
                <td class="text-end text-success">
                    ${formatarNumero(item.estoque_atual || 0)}
                </td>
                <td class="text-end text-success">
                    ${formatarNumero(item.estoque_min_d7)}
                </td>
                <td class="text-center">
                    <span class="badge bg-success">
                        <i class="fas fa-check"></i> Disponível
                    </span>
                </td>
                <td class="text-center">
                    <span class="badge bg-success">Agora</span>
                </td>
            `;
            tbody.appendChild(tr);
        });
    };
    
    window.mostrarTodosItensModal = function() {
        if (!dadosModalAtual) return;
        
        // Atualizar botões
        document.querySelectorAll('#modalRupturaLote .btn-group button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById('btnMostrarTodos')?.classList.add('active');
        
        // Atualizar título da seção
        const tituloSecao = document.querySelector('#modalRupturaLote h6');
        if (tituloSecao) {
            tituloSecao.innerHTML = '<i class="fas fa-list text-primary me-2"></i>Todos os Itens do Pedido:';
        }
        
        // Atualizar tabela
        const tbody = document.getElementById('modalRupturaLoteItens');
        const itensRuptura = dadosModalAtual.itens || [];
        const itensDisponiveis = dadosModalAtual.itens_disponiveis || [];
        
        tbody.innerHTML = '';
        
        // Adicionar itens com ruptura primeiro
        if (itensRuptura.length > 0) {
            const trHeader = document.createElement('tr');
            trHeader.className = 'table-secondary';
            trHeader.innerHTML = `
                <td colspan="7" class="fw-bold">
                    <i class="fas fa-exclamation-triangle text-danger me-2"></i>
                    Itens com Ruptura (${itensRuptura.length})
                </td>
            `;
            tbody.appendChild(trHeader);
            
            itensRuptura.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.cod_produto}</td>
                    <td>${item.nome_produto}</td>
                    <td class="text-end">${formatarNumero(item.qtd_saldo)}</td>
                    <td class="text-end ${item.estoque_atual < 0 ? 'text-danger' : ''}">
                        ${formatarNumero(item.estoque_atual || 0)}
                    </td>
                    <td class="text-end ${item.estoque_min_d7 < 0 ? 'text-danger' : ''}">
                        ${formatarNumero(item.estoque_min_d7)}
                    </td>
                    <td class="text-center">
                        ${item.data_producao ? 
                            `<span class="badge bg-primary">
                                ${formatarData(item.data_producao)}
                                <br>
                                <small>${formatarNumero(item.qtd_producao)} un</small>
                            </span>` : 
                            '<span class="badge bg-danger">Sem Produção</span>'
                        }
                    </td>
                    <td class="text-center">
                        ${item.data_disponivel ? 
                            `<span class="badge bg-success">
                                ${formatarData(item.data_disponivel)}
                            </span>` : 
                            '<span class="badge bg-secondary">Indisponível</span>'
                        }
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        // Adicionar itens disponíveis
        if (itensDisponiveis.length > 0) {
            const trHeader = document.createElement('tr');
            trHeader.className = 'table-secondary';
            trHeader.innerHTML = `
                <td colspan="7" class="fw-bold">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    Itens Disponíveis (${itensDisponiveis.length})
                </td>
            `;
            tbody.appendChild(trHeader);
            
            itensDisponiveis.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.cod_produto}</td>
                    <td>${item.nome_produto}</td>
                    <td class="text-end">${formatarNumero(item.qtd_saldo)}</td>
                    <td class="text-end text-success">
                        ${formatarNumero(item.estoque_atual || 0)}
                    </td>
                    <td class="text-end text-success">
                        ${formatarNumero(item.estoque_min_d7)}
                    </td>
                    <td class="text-center">
                        <span class="badge bg-success">
                            <i class="fas fa-check"></i> Disponível
                        </span>
                    </td>
                    <td class="text-center">
                        <span class="badge bg-success">Agora</span>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        if (itensRuptura.length === 0 && itensDisponiveis.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        Nenhum item encontrado
                    </td>
                </tr>
            `;
        }
    };
    
    // Criar modal de ruptura para lote (igual ao da carteira agrupada)
    function criarModalRupturaLote() {
        const modalHtml = `
            <div class="modal fade" id="modalRupturaLote" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title" id="modalRupturaLoteTitulo">
                                Análise de Ruptura
                            </h5>
                            <button type="button" class="btn-close btn-close-white" 
                                    data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="modalRupturaLoteResumo" class="alert alert-light">
                                <!-- Resumo -->
                            </div>
                            
                            <h6 class="mt-3">
                                <i class="fas fa-exclamation-triangle text-danger me-2"></i>
                                Itens com Ruptura de Estoque:
                            </h6>
                            <div class="table-responsive">
                                <table class="table table-sm table-hover">
                                    <thead>
                                        <tr>
                                            <th>Código</th>
                                            <th>Produto</th>
                                            <th class="text-end">Qtd Pedido</th>
                                            <th class="text-end">Estoque Atual</th>
                                            <th class="text-end">Estoque D+7</th>
                                            <th class="text-center">Produção</th>
                                            <th class="text-center">Disponibilidade</th>
                                        </tr>
                                    </thead>
                                    <tbody id="modalRupturaLoteItens">
                                        <!-- Itens -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Fechar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        return document.getElementById('modalRupturaLote');
    }
    
    // CONFIRMAÇÃO: Data expedição mudou - calcular D+1 automaticamente
    function handleDataExpedicaoChange(e) {
        const input = e.target;
        const cnpj = input.dataset.cnpj;
        const dataExpedicao = input.value;
        
        if (dataExpedicao) {
            // REGRA CONFIRMADA: Agendamento = D+1 da expedição
            const data = new Date(dataExpedicao);
            data.setDate(data.getDate() + 1);
            
            const inputAgendamento = document.querySelector(`.data-agendamento[data-cnpj="${cnpj}"]`);
            if (inputAgendamento) {
                inputAgendamento.value = data.toISOString().split('T')[0];
                console.log(`Agendamento auto-calculado: D+1 de ${dataExpedicao}`);
            }
        }
    }
    
    // Expandir detalhes
    function handleExpandir(e) {
        const btn = e.currentTarget;
        const cnpj = btn.dataset.cnpj;
        const detailRow = document.querySelector(`tr[data-cnpj-detail="${cnpj}"]`);
        const icon = btn.querySelector('i');
        
        if (detailRow) {
            detailRow.classList.toggle('d-none');
            
            if (detailRow.classList.contains('d-none')) {
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            } else {
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            }
        }
    }
    
    // Selecionar todos
    function handleCheckTodos(e) {
        const isChecked = e.target.checked;
        
        // Limpar seleções anteriores
        cnpjsSelecionados.clear();
        
        document.querySelectorAll('.check-cnpj').forEach(checkbox => {
            const status = checkbox.dataset.status;
            
            // Selecionar apenas CNPJs com status "Pendente" ou "Reagendar"
            if (isChecked && (status === 'Pendente' || status === 'Reagendar')) {
                checkbox.checked = true;
                cnpjsSelecionados.add(checkbox.value);
            } else {
                checkbox.checked = false;
            }
        });
        
        atualizarBotaoProcessar();
        
        // Mostrar mensagem informativa se alguns foram selecionados
        if (isChecked && cnpjsSelecionados.size > 0) {
            console.log(`${cnpjsSelecionados.size} CNPJs selecionados (apenas Pendente e Reagendar)`);
            
            // Mostrar toast informativo
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'info',
                title: `${cnpjsSelecionados.size} CNPJs selecionados`,
                text: 'Apenas status Pendente e Reagendar',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        }
    }
    
    // Botão selecionar todos
    function handleSelecionarTodos() {
        const checkboxes = document.querySelectorAll('.check-cnpj');
        
        // Filtrar apenas checkboxes com status "Pendente" ou "Reagendar"
        const checkboxesRelevantes = Array.from(checkboxes).filter(cb => {
            const status = cb.dataset.status;
            return status === 'Pendente' || status === 'Reagendar';
        });
        
        const todosRelevantesChecados = checkboxesRelevantes.every(cb => cb.checked);
        
        // Limpar seleções anteriores
        cnpjsSelecionados.clear();
        
        // Desmarcar todos primeiro
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Marcar apenas os relevantes se não estavam todos marcados
        if (!todosRelevantesChecados) {
            checkboxesRelevantes.forEach(checkbox => {
                checkbox.checked = true;
                cnpjsSelecionados.add(checkbox.value);
            });
        }
        
        if (checkTodos) {
            checkTodos.checked = !todosRelevantesChecados;
        }
        
        btnSelecionarTodos.innerHTML = todosRelevantesChecados ? 
            '<i class="fas fa-check-square"></i> Selecionar Todos' :
            '<i class="fas fa-square"></i> Desselecionar Todos';
        
        atualizarBotaoProcessar();
        
        // Mostrar mensagem informativa
        if (!todosRelevantesChecados && cnpjsSelecionados.size > 0) {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'info',
                title: `${cnpjsSelecionados.size} CNPJs selecionados`,
                text: 'Apenas status Pendente e Reagendar',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        }
    }
    
    // Checkbox individual
    function handleCheckCnpj(e) {
        const cnpj = e.target.value;
        
        if (e.target.checked) {
            cnpjsSelecionados.add(cnpj);
        } else {
            cnpjsSelecionados.delete(cnpj);
        }
        
        const totalCheckboxes = document.querySelectorAll('.check-cnpj').length;
        if (checkTodos) {
            checkTodos.checked = cnpjsSelecionados.size === totalCheckboxes;
        }
        
        atualizarBotaoProcessar();
    }
    
    // Atualizar botão processar
    function atualizarBotaoProcessar() {
        if (btnProcessarLote) {
            btnProcessarLote.disabled = cnpjsSelecionados.size === 0;
            
            if (cnpjsSelecionados.size > 0) {
                btnProcessarLote.innerHTML = `<i class="fas fa-calendar-alt"></i> Agendar Selecionados (${cnpjsSelecionados.size})`;
            } else {
                btnProcessarLote.innerHTML = '<i class="fas fa-calendar-alt"></i> Agendar Selecionados';
            }
        }
    }
    
    // Processar lote
    async function handleProcessarLote() {
        if (cnpjsSelecionados.size === 0) {
            Swal.fire('Atenção', 'Selecione pelo menos um CNPJ', 'warning');
            return;
        }
        
        // Coletar datas
        const dadosAgendamento = [];
        let todasTemDatas = true;
        
        cnpjsSelecionados.forEach(cnpj => {
            const expedicao = document.querySelector(`.data-expedicao[data-cnpj="${cnpj}"]`)?.value;
            const agendamento = document.querySelector(`.data-agendamento[data-cnpj="${cnpj}"]`)?.value;
            
            if (!expedicao) {
                todasTemDatas = false;
            }
            
            dadosAgendamento.push({
                cnpj: cnpj,
                expedicao: expedicao,
                agendamento: agendamento
            });
        });
        
        if (!todasTemDatas) {
            Swal.fire('Atenção', 'Preencha as datas de expedição para todos os CNPJs selecionados', 'warning');
            return;
        }
        
        // Verificar se é portal Sendas
        const portal = window.PORTAL_CONFIG?.portal;
        
        if (portal === 'sendas') {
            // Fluxo específico do Sendas
            await processarAgendamentoSendas(dadosAgendamento);
        } else {
            // Fluxo padrão (Atacadão ou outros)
            Swal.fire({
                icon: 'info',
                title: 'Processamento em Lote',
                html: `Pronto para processar ${cnpjsSelecionados.size} CNPJs<br>` +
                      'Portal: ' + (portal || 'Não identificado'),
                confirmButtonText: 'OK'
            });
        }
    }
    
    // Processar agendamento específico do Sendas
    async function processarAgendamentoSendas(dadosAgendamento) {
        // Mostrar loading com etapas
        Swal.fire({
            title: 'Processando Agendamento Sendas',
            html: `
                <div class="text-start">
                    <p><strong>Executando processo automatizado:</strong></p>
                    <ol>
                        <li>📥 Baixando planilha do portal...</li>
                        <li>📝 Preenchendo dados selecionados...</li>
                        <li>📤 Fazendo upload no portal Sendas...</li>
                        <li>🗂️ Gerando separações no sistema...</li>
                    </ol>
                    <br>
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Processando...</span>
                        </div>
                        <p class="mt-2"><small>Este processo pode levar alguns minutos...</small></p>
                    </div>
                </div>
            `,
            allowOutsideClick: false,
            showConfirmButton: false,
            width: '500px',
            didOpen: () => {
                Swal.showLoading();
            }
        });
        
        try {
            // SEMPRE usar endpoint assíncrono
            const endpoint = '/carteira/programacao-lote/api/processar-agendamento-sendas-async';
            
            // Chamar endpoint de processamento Sendas
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    portal: 'sendas',
                    agendamentos: dadosAgendamento,
                    cnpjs: dadosAgendamento  // O endpoint assíncrono espera 'cnpjs'
                })
            });
            
            const result = await response.json();
            
            // Fazer polling do status do job assíncrono
            if (result.job_id) {
                // Mostrar notificação simples e continuar trabalhando
                Swal.fire({
                    icon: 'info',
                    title: 'Agendamento em Processamento',
                    html: `
                        <div class="text-center">
                            <p><strong>${result.total_cnpjs || cnpjsSelecionados.size} CNPJs</strong> estão sendo agendados no portal Sendas.</p>
                            <div class="progress mt-3" style="height: 25px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated bg-success" 
                                     role="progressbar" style="width: 100%">
                                    Processando no servidor...
                                </div>
                            </div>
                            <div class="alert alert-info mt-3 text-start" style="font-size: 0.9em;">
                                <i class="fas fa-server"></i> <strong>Processamento no Servidor</strong><br>
                                <small>
                                    • O agendamento continua mesmo se você fechar esta página<br>
                                    • Você pode fazer outras tarefas enquanto processa<br>
                                    • Se permanecer na página, será notificado quando concluir
                                </small>
                            </div>
                        </div>
                    `,
                    confirmButtonText: 'OK, Entendi',
                    timer: 8000,  // Aumentar para 8 segundos para dar tempo de ler
                    timerProgressBar: true,
                    didClose: () => {
                        // Iniciar verificação em background (sem bloquear a tela)
                        checkJobStatusSilently(result.job_id);
                    }
                });
                
                // Mostrar notificação toast no canto
                showToastNotification('info', 'Agendamento iniciado', 'Processando em segundo plano...');
                return;
            }
            
            if (result.success) {
                // Se tiver URL de download, baixar automaticamente
                if (result.download_url) {
                    // Criar link temporário para download
                    const link = document.createElement('a');
                    link.href = result.download_url;
                    link.download = result.arquivo;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
                
                // Mostrar sucesso com detalhes
                let detalhesHtml = '<div class="text-start">';
                detalhesHtml += '<h5>✅ Processo concluído com sucesso!</h5>';
                detalhesHtml += '<hr>';
                
                detalhesHtml += '<p><strong>Etapas realizadas:</strong></p>';
                detalhesHtml += '<ol>';
                detalhesHtml += '<li>✅ Planilha baixada do portal</li>';
                detalhesHtml += '<li>✅ Dados preenchidos automaticamente</li>';
                detalhesHtml += '<li>✅ Upload realizado no portal Sendas</li>';
                detalhesHtml += '<li>✅ Separações geradas no sistema</li>';
                detalhesHtml += '</ol>';
                
                if (result.separacoes_criadas && result.separacoes_criadas.length > 0) {
                    detalhesHtml += '<hr>';
                    detalhesHtml += '<p><strong>Separações criadas:</strong></p>';
                    detalhesHtml += '<ul>';
                    result.separacoes_criadas.forEach(sep => {
                        detalhesHtml += `<li>Pedido ${sep.num_pedido}: ${sep.qtd_itens} itens</li>`;
                    });
                    detalhesHtml += '</ul>';
                }
                
                detalhesHtml += '<hr>';
                detalhesHtml += '<p class="text-success"><strong>Agendamento enviado para o portal Sendas!</strong></p>';
                detalhesHtml += '<p class="text-muted">Aguarde a confirmação do protocolo no portal.</p>';
                detalhesHtml += '</div>';
                
                Swal.fire({
                    icon: 'success',
                    title: 'Sucesso!',
                    html: detalhesHtml,
                    confirmButtonText: 'OK',
                    width: '600px'
                }).then(() => {
                    // Recarregar a página para atualizar a lista
                    window.location.reload();
                });
            } else {
                // Verificar se tem CNPJs ignorados
                let mensagemErro = result.error || 'Erro desconhecido';
                
                if (result.cnpjs_ignorados && result.cnpjs_ignorados.length > 0) {
                    mensagemErro += '\n\nCNPJs ignorados (sem data de agendamento):\n';
                    result.cnpjs_ignorados.forEach(cnpj => {
                        mensagemErro += `• ${cnpj}\n`;
                    });
                    mensagemErro += '\n⚠️ Data de agendamento é OBRIGATÓRIA para o portal Sendas';
                }
                
                Swal.fire({
                    icon: 'error',
                    title: 'Erro ao processar',
                    html: mensagemErro.replace(/\n/g, '<br>'),
                    width: '600px'
                });
            }
        } catch (error) {
            console.error('Erro ao processar agendamento Sendas:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro de comunicação',
                text: 'Não foi possível processar o agendamento. Tente novamente.'
            });
        }
    }
    
    // Função para verificar status do job em background (sem bloquear interface)
    async function checkJobStatusSilently(jobId) {
        try {
            const response = await fetch(`/carteira/programacao-lote/api/status-job-sendas/${jobId}`);
            const data = await response.json();
            
            if (data.status === 'finished') {
                // Job concluído com sucesso - notificação amigável
                showToastNotification('success', 'Agendamento Concluído!', 'Todos os CNPJs foram processados com sucesso.');
                
                // Modal de sucesso com opção de atualizar
                Swal.fire({
                    icon: 'success',
                    title: 'Agendamento Realizado!',
                    html: `
                        <div class="text-center">
                            <p class="mb-3">
                                <i class="fas fa-check-circle text-success" style="font-size: 3em;"></i>
                            </p>
                            <p><strong>Todos os CNPJs foram agendados com sucesso no portal Sendas.</strong></p>
                            <p class="text-muted mt-2">As separações foram geradas e estão prontas para processamento.</p>
                            <hr class="my-3">
                            <p class="text-info">
                                <i class="fas fa-info-circle"></i> 
                                <small>O processamento foi concluído mesmo que você tenha fechado a página.</small>
                            </p>
                        </div>
                    `,
                    confirmButtonText: 'Atualizar Página',
                    confirmButtonColor: '#28a745',
                    showCancelButton: true,
                    cancelButtonText: 'Continuar na Página',
                    cancelButtonColor: '#6c757d'
                }).then((result) => {
                    // Só atualiza se o usuário escolher
                    if (result.isConfirmed) {
                        location.reload();
                    } else {
                        // Limpar os checkboxes selecionados
                        cnpjsSelecionados.clear();
                        document.querySelectorAll('.check-cnpj:checked').forEach(cb => {
                            cb.checked = false;
                        });
                        document.getElementById('checkTodos').checked = false;
                        atualizarBotaoProcessar();
                        
                        // Mostrar notificação de que pode continuar
                        showToastNotification('info', 'Pronto!', 'Você pode continuar selecionando outros CNPJs.');
                    }
                });
                
            } else if (data.status === 'failed') {
                // Erro no processamento - notificação amigável
                showToastNotification('error', 'Erro no Agendamento', 'Houve um problema ao processar os agendamentos.');
                
                Swal.fire({
                    icon: 'error',
                    title: 'Erro no Agendamento',
                    html: `
                        <div class="text-center">
                            <p class="mb-3">
                                <i class="fas fa-times-circle text-danger" style="font-size: 3em;"></i>
                            </p>
                            <p>Não foi possível completar o agendamento no portal Sendas.</p>
                            <p class="text-muted mt-2">Por favor, tente novamente ou entre em contato com o suporte.</p>
                        </div>
                    `,
                    confirmButtonText: 'Entendi',
                    confirmButtonColor: '#dc3545'
                });
                
            } else if (data.status === 'not_found') {
                // Job expirou - não mostrar nada técnico
                console.log('Job expirou ou foi cancelado:', jobId);
                
            } else {
                // Ainda processando - continuar verificando silenciosamente
                setTimeout(() => {
                    checkJobStatusSilently(jobId);
                }, 5000); // Verificar novamente em 5 segundos
            }
            
        } catch (error) {
            console.error('Erro ao verificar status do job:', error);
            // Em caso de erro de rede, tentar novamente em 10 segundos
            setTimeout(() => {
                checkJobStatusSilently(jobId);
            }, 10000);
        }
    }
        
    // Função auxiliar para mostrar notificações toast
    function showToastNotification(type, title, message) {
        // Verificar se já existe container de toasts
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
            document.body.appendChild(toastContainer);
        }
        
        // Criar elemento do toast
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast show align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0 mb-2" 
                 role="alert" aria-live="assertive" aria-atomic="true" style="min-width: 300px;">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>
                        <small>${message}</small>
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            onclick="document.getElementById('${toastId}').remove()"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Auto remover após 5 segundos
        setTimeout(() => {
            const toast = document.getElementById(toastId);
            if (toast) toast.remove();
        }, 5000);
    }
    
    // Converter número
    function converterParaNumero(texto) {
        let limpo = texto.replace('R$', '').trim();
        limpo = limpo.replace(/,/g, '');
        return parseFloat(limpo) || 0;
    }
    
    // Calcular totais
    function calcularTotais() {
        let valorTotal = 0;
        let pesoTotal = 0;
        let palletsTotal = 0;
        
        document.querySelectorAll('.cnpj-row').forEach(row => {
            // Nova estrutura de colunas após unificação:
            // 0: Checkbox, 1: Cliente, 2: Cidade, 3: Valor, 4: Peso, 5: Pallets
            const valorText = row.cells[3].textContent;
            const pesoText = row.cells[4].textContent;
            const palletsText = row.cells[5].textContent;
            
            const valor = converterParaNumero(valorText);
            const peso = converterParaNumero(pesoText);
            const pallets = converterParaNumero(palletsText);
            
            valorTotal += valor;
            pesoTotal += peso;
            palletsTotal += pallets;
        });
        
        const valorEl = document.getElementById('valorTotalGeral');
        const pesoEl = document.getElementById('pesoTotalGeral');
        const palletsEl = document.getElementById('palletsTotalGeral');
        
        if (valorEl) {
            valorEl.textContent = valorTotal.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        
        if (pesoEl) {
            pesoEl.textContent = pesoTotal.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        
        if (palletsEl) {
            palletsEl.textContent = palletsTotal.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
    }
    
    // ====== IMPORTAÇÃO DE AGENDAMENTOS ASSAI ======
    // ⚠️ REMOVIDO: Funcionalidade não é mais utilizada

    /*
    // Handler para abrir modal de importação
    function handleImportarAgendamentos() {
        console.log('Abrindo modal de importação de agendamentos...');
        
        // Resetar formulário
        const fileInput = document.getElementById('fileImportarAgendamentos');
        const btnConfirmar = document.getElementById('btnConfirmarImportacao');
        const progressoArea = document.getElementById('progressoImportacao');
        const resultadoArea = document.getElementById('resultadoImportacao');
        
        if (fileInput) fileInput.value = '';
        if (progressoArea) progressoArea.classList.add('d-none');
        if (resultadoArea) resultadoArea.classList.add('d-none');
        if (btnConfirmar) {
            btnConfirmar.disabled = false;
            btnConfirmar.innerHTML = '<i class="fas fa-upload"></i> Importar';
        }
        
        // Abrir modal
        const modal = new bootstrap.Modal(document.getElementById('modalImportarAgendamentos'));
        modal.show();
        
        // Configurar evento de confirmação
        if (btnConfirmar) {
            btnConfirmar.onclick = processarImportacao;
        }
    }
    
    // Processar importação do arquivo
    async function processarImportacao() {
        const fileInput = document.getElementById('fileImportarAgendamentos');
        const btnConfirmar = document.getElementById('btnConfirmarImportacao');
        const progressoArea = document.getElementById('progressoImportacao');
        const resultadoArea = document.getElementById('resultadoImportacao');
        
        // Validar arquivo
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            Swal.fire({
                icon: 'warning',
                title: 'Arquivo não selecionado',
                text: 'Por favor, selecione um arquivo Excel para importar.',
                confirmButtonText: 'OK'
            });
            return;
        }
        
        const file = fileInput.files[0];
        
        // Validar extensão
        const fileName = file.name.toLowerCase();
        if (!fileName.endsWith('.xlsx') && !fileName.endsWith('.xls')) {
            Swal.fire({
                icon: 'error',
                title: 'Formato inválido',
                text: 'Por favor, selecione um arquivo Excel (.xlsx ou .xls).',
                confirmButtonText: 'OK'
            });
            return;
        }
        
        // Mostrar progresso
        if (progressoArea) progressoArea.classList.remove('d-none');
        if (resultadoArea) resultadoArea.classList.add('d-none');
        if (btnConfirmar) {
            btnConfirmar.disabled = true;
            btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
        }
        
        // Criar FormData
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // Enviar arquivo para o servidor
            const response = await fetch('/carteira/programacao-lote/api/importar-agendamentos-assai', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Exibir resultados
                exibirResultadosImportacao(result);
                
                // Recarregar a página após 3 segundos se houver alterações
                if (result.resumo.criados > 0 || result.resumo.atualizados > 0) {
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                }
            } else {
                // Erro na importação
                Swal.fire({
                    icon: 'error',
                    title: 'Erro na Importação',
                    text: result.error || 'Erro desconhecido ao processar arquivo.',
                    confirmButtonText: 'OK'
                });
            }
            
        } catch (error) {
            console.error('Erro ao importar:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro de Comunicação',
                text: 'Erro ao enviar arquivo para o servidor. Tente novamente.',
                confirmButtonText: 'OK'
            });
            
        } finally {
            // Resetar botão
            if (progressoArea) progressoArea.classList.add('d-none');
            if (btnConfirmar) {
                btnConfirmar.disabled = false;
                btnConfirmar.innerHTML = '<i class="fas fa-upload"></i> Importar';
            }
        }
    }
    
    // Exibir resultados da importação
    function exibirResultadosImportacao(result) {
        const resultadoArea = document.getElementById('resultadoImportacao');
        
        if (!resultadoArea) return;
        
        resultadoArea.classList.remove('d-none');
        
        // Atualizar resumo
        const resumo = result.resumo;
        document.getElementById('totalProcessados').textContent = resumo.total_processados || 0;
        document.getElementById('totalCriados').textContent = resumo.criados || 0;
        document.getElementById('totalAtualizados').textContent = resumo.atualizados || 0;
        document.getElementById('totalNaoEncontrados').textContent = resumo.nao_encontrados || 0;
        document.getElementById('totalErros').textContent = resumo.erros || 0;
        
        // Exibir CNPJs não encontrados
        const naoEncontrados = result.detalhes.nao_encontrados;
        if (naoEncontrados && naoEncontrados.length > 0) {
            const areaNaoEncontrados = document.getElementById('areaNaoEncontrados');
            const tabelaNaoEncontrados = document.getElementById('tabelaNaoEncontrados');
            
            if (areaNaoEncontrados && tabelaNaoEncontrados) {
                areaNaoEncontrados.classList.remove('d-none');
                
                // Limpar tabela
                tabelaNaoEncontrados.innerHTML = '';
                
                // Adicionar linhas
                naoEncontrados.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="text-nowrap">${item.cnpj}</td>
                        <td>${item.protocolo}</td>
                        <td>${item.unidade || '-'}</td>
                        <td>
                            <span class="badge ${item.status === 'Aprovada' ? 'bg-success' : 'bg-warning text-dark'}">
                                ${item.status}
                            </span>
                        </td>
                        <td>${item.data || '-'}</td>
                    `;
                    tabelaNaoEncontrados.appendChild(tr);
                });
            }
        }
        
        // Exibir erros
        const erros = result.detalhes.erros;
        if (erros && erros.length > 0) {
            const areaErros = document.getElementById('areaErros');
            const listaErros = document.getElementById('listaErros');
            
            if (areaErros && listaErros) {
                areaErros.classList.remove('d-none');
                
                // Limpar lista
                listaErros.innerHTML = '';
                
                // Adicionar erros
                erros.forEach(erro => {
                    const li = document.createElement('li');
                    li.textContent = erro;
                    listaErros.appendChild(li);
                });
            }
        }
        
        // Mostrar mensagem de sucesso se houver alterações
        if (resumo.criados > 0 || resumo.atualizados > 0) {
            Swal.fire({
                icon: 'success',
                title: 'Importação Concluída!',
                html: `
                    <div class="text-start">
                        <p><strong>Resumo:</strong></p>
                        <ul>
                            <li>${resumo.criados} registros criados</li>
                            <li>${resumo.atualizados} registros atualizados</li>
                            ${resumo.nao_encontrados > 0 ? `<li class="text-warning">${resumo.nao_encontrados} CNPJs não encontrados</li>` : ''}
                            ${resumo.erros > 0 ? `<li class="text-danger">${resumo.erros} erros encontrados</li>` : ''}
                        </ul>
                        <p class="text-info mt-3">A página será recarregada em 3 segundos...</p>
                    </div>
                `,
                timer: 3000,
                timerProgressBar: true,
                showConfirmButton: false
            });
        }
    }
    */
});