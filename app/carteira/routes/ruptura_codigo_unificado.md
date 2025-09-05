modal-cardex.js:

<div id="modal-cardex-4759098-1757074236214" class="modal fade show" tabindex="-1" aria-modal="true" role="dialog" style="display: block; padding-left: 0px;">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <!-- Header -->
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-chart-line me-2"></i>
                            Cardex - 4759098
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>

                    <!-- Body -->
                    <div class="modal-body">
                        <!-- Info do Produto -->
                        <div class="produto-cardex-header mb-4">
                            <div class="row">
                                <div class="col-md-8">
                                    <h6 class="text-primary">OLEO DE SOJA MISTO - VD 12X500 ML - ST ISABEL</h6>
                                    <p class="text-muted mb-0">Análise de estoque para os próximos 28 dias</p>
                                </div>
                                <div class="col-md-4 text-end">
                                    <div class="cardex-resumo">
                                        <small class="text-muted">Estoque Atual</small>
                                        <br><strong class="h4 text-success">-3.155</strong>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Gráfico Resumo -->
                        <div class="cardex-resumo-visual mb-4">
                            <div class="row text-center">
                                <div class="col-3">
                                    <div class="stat-card bg-success bg-opacity-10 p-3 rounded">
                                        <h5 class="text-success mb-1">2.845</h5>
                                        <small class="text-muted">Maior Pico</small>
                                        <br><small class="text-success">D+4</small>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="stat-card bg-warning bg-opacity-10 p-3 rounded">
                                        <h5 class="text-warning mb-1">-3.155</h5>
                                        <small class="text-muted">Menor Estoque</small>
                                        <br><small class="text-warning">D+0</small>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="stat-card bg-info bg-opacity-10 p-3 rounded">
                                        <h5 class="text-info mb-1">6.000</h5>
                                        <small class="text-muted">Produção Total</small>
                                        <br><small class="text-info">28 dias</small>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="stat-card bg-danger bg-opacity-10 p-3 rounded">
                                        <h5 class="text-danger mb-1">200</h5>
                                        <small class="text-muted">Saídas Total</small>
                                        <br><small class="text-danger">28 dias</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Tabela Cardex -->
                        <div class="cardex-tabela">
                            <div class="table-responsive" style="max-height: 400px;">
                                <table class="table table-sm table-striped table-hover">
                                    <thead class="table-dark sticky-top">
                                        <tr>
                                            <th>Dia</th>
                                            <th>Data</th>
                                            <th class="text-end">Est. Inicial</th>
                                            <th class="text-end">
                                                Saídas
                                                <button class="btn btn-sm btn-link text-white p-0 ms-2" onclick="modalCardex.abrirCardexExpandido('4759098')" title="Ver detalhes de todas as saídas">
                                                    <i class="fas fa-expand-arrows-alt"></i>
                                                </button>
                                            </th>
                                            <th class="text-end">Saldo</th>
                                            <th class="text-end">Produção</th>
                                            <th class="text-end">Est. Final</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        
                <tr class="table-danger">
                    <td><strong>D+0</strong></td>
                    <td>05/09/25</td>
                    <td class="text-end">-3.155</td>
                    <td class="text-end text-danger">
                        -0
                    </td>
                    <td class="text-end">
                        <span class="badge bg-danger">
                            -3.155
                        </span>
                    </td>
                    <td class="text-end text-success">
                        +0
                    </td>
                    <td class="text-end">
                        <strong class="text-danger">
                            -3.155
                        </strong>
                    </td>
                    <td>
                        <span class="badge bg-danger">
                            Ruptura
                        </span>
                    </td>
                </tr>
            
                <tr class="table-danger">
                    <td><strong>D+1</strong></td>
                    <td>06/09/25</td>
                    <td class="text-end">-3.155</td>
                    <td class="text-end text-danger">
                        -0
                    </td>
                    <td class="text-end">
                        <span class="badge bg-danger">
                            -3.155
                        </span>
                    </td>
                    <td class="text-end text-success">
                        +0
                    </td>
                    <td class="text-end">
                        <strong class="text-danger">
                            -3.155
                        </strong>
                    </td>
                    <td>
                        <span class="badge bg-danger">
                            Ruptura
                        </span>
                    </td>
                </tr>
            
                <tr class="table-danger">
                    <td><strong>D+2</strong></td>
                    <td>07/09/25</td>
                    <td class="text-end">-3.155</td>
                    <td class="text-end text-danger">
                        -0
                    </td>
                    <td class="text-end">
                        <span class="badge bg-danger">
                            -3.155
                        </span>
                    </td>
                    <td class="text-end text-success">
                        +0
                    </td>
                    <td class="text-end">
                        <strong class="text-danger">
                            -3.155
                        </strong>
                    </td>
                    <td>
                        <span class="badge bg-danger">
                            Ruptura
                        </span>
                    </td>
                </tr>
            
                <tr class="table-danger">
                    <td><strong>D+3</strong></td>
                    <td>08/09/25</td>
                    <td class="text-end">-3.155</td>
                    <td class="text-end text-danger">
                        -0
                    </td>
                    <td class="text-end">
                        <span class="badge bg-danger">
                            -3.155
                        </span>
                    </td>
                    <td class="text-end text-success">
                        +3.000
                    </td>
                    <td class="text-end">
                        <strong class="text-danger">
                            -155
                        </strong>
                    </td>
                    <td>
                        <span class="badge bg-danger">
                            Ruptura
                        </span>
                    </td>
                </tr>
            
                <tr class="">
                    <td><strong>D+4</strong></td>
                    <td>09/09/25</td>
                    <td class="text-end">-155</td>
                    <td class="text-end text-danger">
                        -0
                    </td>
                    <td class="text-end">
                        <span class="badge bg-danger">
                            -155
                        </span>
                    </td>
                    <td class="text-end text-success">
                        +3.000
                    </td>
                    <td class="text-end">
                        <strong class="text-success">
                            2.845
                        </strong>
                    </td>
                    <td>
                        <span class="badge bg-info">
                            Produção
                        </span>
                    </td>
                </tr>



<div class="modal fade show" id="modalRuptura" tabindex="-1" style="display: block;" aria-modal="true" role="dialog">
                <div class="modal-dialog modal-xl" style="margin-top: 70px;">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title" id="modalRupturaTitulo">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    Análise de Ruptura - Pedido VCD2543401
                    <span class="badge bg-secondary ms-2">
                        BAIXA
                    </span>
                </div>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-danger active" onclick="rupturaManager.mostrarItensRuptura()">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        Ruptura (1)
                    </button>
                    <button type="button" class="btn btn-outline-success" onclick="rupturaManager.mostrarItensDisponiveis()">
                        <i class="fas fa-check-circle me-1"></i>
                        Disponíveis (2)
                    </button>
                    <button type="button" class="btn btn-outline-primary" onclick="rupturaManager.mostrarTodosItens()">
                        <i class="fas fa-list me-1"></i>
                        Todos (3)
                    </button>
                </div>
            </div>
        </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="modalRupturaResumo" class="alert alert-light">
            <div class="row">
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Disponibilidade</strong><br>
                        <span class="h4 text-success">74%</span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Em Ruptura</strong><br>
                        <span class="h4 text-danger">26.08%</span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Valor Total</strong><br>
                        <span class="h5">R$ 33663,90</span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <strong>Valor em Risco</strong><br>
                        <span class="h5 text-danger">R$ 8778,40</span>
                    </div>
                </div>
            </div>
        </div>
                            
                            <h6 class="mt-3"><i class="fas fa-exclamation-triangle text-danger me-2"></i>Itens com Ruptura de Estoque:</h6>
                            <div class="table-responsive">
                                <table class="table table-sm table-striped">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>Código</th>
                                            <th>Produto</th>
                                            <th class="text-end">Qtd Saldo</th>
                                            <th class="text-end">Est.Min D+7</th>
                                            <th class="text-end">Ruptura</th>
                                            <th class="text-center">Produção</th>
                                            <th class="text-center">Disponível em</th>
                                        </tr>
                                    </thead>
                                    <tbody id="modalRupturaItens">
            <tr>
                <td>
                    4759098
                    <button class="btn btn-sm btn-link p-0 ms-2" onclick="rupturaManager.abrirCardex('4759098')" title="Ver Cardex">
                        <i class="fas fa-chart-line"></i>
                    </button>
                </td>
                <td>OLEO DE SOJA MISTO - VD 12X500 ML - ST ISABEL</td>
                <td class="text-end">80</td>
                <td class="text-end text-danger">
                    -3.155
                </td>
                <td class="text-end text-danger fw-bold">
                    3.235
                </td>
                <td class="text-center">
                    <span class="badge bg-danger">Sem Produção</span>
                </td>
                <td class="text-center">
                    <span class="badge bg-secondary">Indisponível</span>
                </td>
            </tr>
        </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                </div>
            </div>



Botão const isRupturaInicial = target.closest('.btn-analisar-ruptura');

console log após clicar no botão:

Pausando análises - Usuário clicou em: Disp. 74% | Total Não Disp.
workspace:98151 ⏸️ Pausando carregamentos - botão clicado
workspace:106726 🔍 Analisando ruptura do pedido VCD2543401...
workspace:106740 📦 Resposta da API: {data_disponibilidade_total: null, itens: Array(1), itens_disponiveis: Array(2), pedido_ok: false, percentual_disponibilidade: 74, …}data_disponibilidade_total: nullitens: [{…}]itens_disponiveis: (2) [{…}, {…}]pedido_ok: falsepercentual_disponibilidade: 74performance_ms: 13.35query_ms: 4.04resumo: {criticidade: 'BAIXA', data_disponibilidade_total: null, num_pedido: 'VCD2543401', percentual_disponibilidade: 74, percentual_itens_disponiveis: 67, …}sem_cache: truesuccess: trueversion: "sem-cache-v1"[[Prototype]]: Object
workspace:105976 🧭 Push modal: Pedido VCD2543401 (modalRuptura). Stack atual: (12) ['Pedido VCD2543403', 'Cardex - 4759098', 'Pedido VCD2543427', 'Pedido VCD2543430', 'Cardex - 4870112', 'Pedido VCD2543430', 'Pedido VCD2543426', 'Cardex - 4729098', 'Pedido VCD2543426', 'Cardex - 4729098', 'Pedido VCD2543401', 'Cardex - 4759098']0: "Pedido VCD2543403"1: "Cardex - 4759098"2: "Pedido VCD2543427"3: "Pedido VCD2543430"4: "Cardex - 4870112"5: "Pedido VCD2543430"6: "Pedido VCD2543426"7: "Cardex - 4729098"8: "Pedido VCD2543426"9: "Cardex - 4729098"10: "Pedido VCD2543401"11: "Cardex - 4759098"length: 12[[Prototype]]: Array(0)
workspace:105988 🧭 Stack após push: (13) ['Pedido VCD2543403', 'Cardex - 4759098', 'Pedido VCD2543427', 'Pedido VCD2543430', 'Cardex - 4870112', 'Pedido VCD2543430', 'Pedido VCD2543426', 'Cardex - 4729098', 'Pedido VCD2543426', 'Cardex - 4729098', 'Pedido VCD2543401', 'Cardex - 4759098', 'Pedido VCD2543401']0: "Pedido VCD2543403"1: "Cardex - 4759098"2: "Pedido VCD2543427"3: "Pedido VCD2543430"4: "Cardex - 4870112"5: "Pedido VCD2543430"6: "Pedido VCD2543426"7: "Cardex - 4729098"8: "Pedido VCD2543426"9: "Cardex - 4729098"10: "Pedido VCD2543401"11: "Cardex - 4759098"12: "Pedido VCD2543401"length: 13[[Prototype]]: Array(0)
workspace:106380 📋 Modal aberto - pausando análises
workspace:106372 ✅ Retomando análises
workspace:98169 ▶️ Retomando carregamentos

