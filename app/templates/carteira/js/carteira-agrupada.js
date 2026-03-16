/**
 * 🎯 CARTEIRA AGRUPADA - CONTROLADOR PRINCIPAL
 * Gerencia funcionalidades da página de carteira agrupada
 */

const DEBUG = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

class CarteiraAgrupada {
    constructor() {
        this.filtrosAtivos = {
            rotas: new Set(),
            incoterms: new Set(),
            subrotas: new Set(),
            agendamento: null,  // null, 'com', 'sem', 'sep-aguardando', 'sep-confirmado'
            cliente: null,  // null, 'atacadao', 'sendas', 'outros'
            atendimento: null,  // null, 'programar', 'revisar-data'
            importante: false  // ⭐ Filtro de pedidos importantes
        };
        this.maxFiltrosAtivos = 3; // Máximo de badges selecionados simultaneamente

        // 🆕 Controle de requisições assíncronas
        this.abortControllers = new Map(); // pedidoId -> AbortController
        this.pedidosVisiveis = new Set(); // Conjunto de pedidos atualmente visíveis

        this.init();
    }

    init() {
        if (DEBUG) console.log('🚀 Inicializando CarteiraAgrupada...');
        this.setupEventListeners();
        this.initWorkspace();
        this.initBadgesFiltros();

        // 🆕 CARREGAR SEPARAÇÕES COMPACTAS INICIALMENTE
        // Identificar pedidos visíveis inicialmente
        document.querySelectorAll('.pedido-row:not([style*="display: none"])').forEach(pedidoRow => {
            const numPedido = pedidoRow.dataset.pedido || pedidoRow.dataset.numPedido;
            if (numPedido) {
                this.pedidosVisiveis.add(numPedido);
            }
        });

        // FIX E2: Removida chamada duplicada carregarSeparacoesCompactasVisiveis()
        // carregarTodasSeparacoesCompactas() ja inclui todos os visiveis.
        // FIX E3: Removidas 2 chamadas extras de atualizarContadorProtocolos()
        // A unica chamada necessaria e a que roda apos carregarSeparacoesEmLoteUnico().

        this.atualizarContadoresImportante();
        this.atualizarContadorPendentesTotal();

        this.setupInterceptadorBotoes();

        // Carregar separacoes compactas para TODOS os pedidos (unica chamada)
        this.carregarTodasSeparacoesCompactas();
    }

    initWorkspace() {
        // Garantir que o workspace seja criado globalmente
        if (!window.workspace && window.WorkspaceMontagem) {
            window.workspace = new window.WorkspaceMontagem();
            if (DEBUG) console.log('✅ Workspace global criado');
        } else if (!window.WorkspaceMontagem) {
            console.error('❌ WorkspaceMontagem não encontrado - verifique se o script foi carregado');
        }
    }

    setupEventListeners() {
        // Filtros de busca
        this.setupFiltros();

        // Botões de expandir/colapsar
        this.setupExpandirColapsar();

        // Botões de expansão de detalhes
        this.setupDetalhesExpansao();

        // ⭐ Event listener para botões de importante (event delegation)
        this.setupBotoesImportante();
    }

    setupBotoesImportante() {
        if (DEBUG) console.log('🔧 Configurando listener de botões importante...');

        // Usar event delegation no document para garantir prioridade
        document.addEventListener('click', (e) => {
            // Verificar se clicou no botão de importante ou na estrela dentro dele
            const btnImportante = e.target.closest('.btn-importante');

            if (btnImportante) {
                if (DEBUG) console.log('✅ Detectado clique em botão importante!');
                e.preventDefault();
                e.stopPropagation();

                const numPedido = btnImportante.dataset.pedido;
                if (DEBUG) console.log('📋 Dados do botão:', {
                    numPedido: numPedido,
                    importante: btnImportante.dataset.importante,
                    classes: btnImportante.className
                });

                if (numPedido) {
                    if (DEBUG) console.log('⭐ Chamando toggleImportante para:', numPedido);
                    this.toggleImportante(numPedido);
                } else {
                    console.error('❌ Botão importante sem data-pedido:', btnImportante);
                }
            }
        }, true); // ⚠️ CAPTURE PHASE - executa antes de outros listeners

        if (DEBUG) console.log('✅ Event delegation para botões importante configurado (capture phase)');
    }

    setupFiltros() {
        const filtroBusca = document.getElementById('filtro-busca');
        const filtroStatus = document.getElementById('filtro-status');
        const filtroEquipe = document.getElementById('filtro-equipe');

        // 🆕 Filtros de data
        const filtroDataPedidoDe = document.getElementById('filtro-data-pedido-de');
        const filtroDataPedidoAte = document.getElementById('filtro-data-pedido-ate');
        const filtroDataEntregaDe = document.getElementById('filtro-data-entrega-de');
        const filtroDataEntregaAte = document.getElementById('filtro-data-entrega-ate');

        if (filtroBusca) {
            filtroBusca.addEventListener('input', () => this.aplicarFiltros());
        }

        if (filtroStatus) {
            filtroStatus.addEventListener('change', () => this.aplicarFiltros());
        }

        if (filtroEquipe) {
            filtroEquipe.addEventListener('change', () => this.aplicarFiltros());
            this.popularFiltroEquipes();
        }

        // 🆕 Event listeners para filtros de data
        if (filtroDataPedidoDe) {
            filtroDataPedidoDe.addEventListener('change', () => this.aplicarFiltros());
        }
        if (filtroDataPedidoAte) {
            filtroDataPedidoAte.addEventListener('change', () => this.aplicarFiltros());
        }
        if (filtroDataEntregaDe) {
            filtroDataEntregaDe.addEventListener('change', () => this.aplicarFiltros());
        }
        if (filtroDataEntregaAte) {
            filtroDataEntregaAte.addEventListener('change', () => this.aplicarFiltros());
        }
    }

    initBadgesFiltros() {
        // Event listeners para badges - CORREÇÃO: usar .bg-filtro em vez de .badge-filtro
        document.querySelectorAll('.bg-filtro').forEach(badge => {
            // Adicionar cursor pointer para indicar que é clicável
            badge.style.cursor = 'pointer';

            badge.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (DEBUG) console.log('🔍 Badge clicado:', badge.dataset.tipo, badge.dataset.valor);
                this.toggleBadgeFiltro(badge);
            });
        });

        // Botões de limpar
        const limparRotas = document.getElementById('limpar-rotas');
        const limparSubrotas = document.getElementById('limpar-subrotas');
        const limparAgendamento = document.getElementById('limpar-agendamento');
        const limparCliente = document.getElementById('limpar-cliente');

        if (limparRotas) {
            limparRotas.addEventListener('click', () => this.limparFiltrosRotas());
        }

        if (limparSubrotas) {
            limparSubrotas.addEventListener('click', () => this.limparFiltrosSubrotas());
        }

        if (limparAgendamento) {
            limparAgendamento.addEventListener('click', () => this.limparFiltrosAgendamento());
        }

        if (limparCliente) {
            limparCliente.addEventListener('click', () => this.limparFiltrosCliente());
        }

        const limparAtendimento = document.getElementById('limpar-atendimento');
        if (limparAtendimento) {
            limparAtendimento.addEventListener('click', () => this.limparFiltrosAtendimento());
        }

        // ⭐ Botão limpar importante
        const limparImportante = document.getElementById('limpar-importante');
        if (limparImportante) {
            limparImportante.addEventListener('click', () => this.limparFiltroImportante());
        }

        if (DEBUG) console.log('✅ Badges de filtros inicializados. Total de badges:', document.querySelectorAll('.bg-filtro').length);
    }

    toggleBadgeFiltro(badge) {
        const tipo = badge.dataset.tipo;
        const valor = badge.dataset.valor;

        // Tratamento especial para agendamento (exclusivo mútuo)
        if (tipo === 'agendamento') {
            this.toggleAgendamento(badge, valor);
            return;
        }

        // Tratamento especial para cliente (exclusivo mútuo)
        if (tipo === 'cliente') {
            this.toggleCliente(badge, valor);
            return;
        }

        // Tratamento especial para atendimento (exclusivo mútuo)
        if (tipo === 'atendimento') {
            this.toggleAtendimento(badge, valor);
            return;
        }

        // ⭐ Tratamento especial para importante (exclusivo mútuo)
        if (tipo === 'importante') {
            this.toggleImportanteFiltro(badge);
            return;
        }

        // Verificar limite de filtros ativos (não se aplica a agendamento)
        const totalAtivos = this.filtrosAtivos.rotas.size +
            this.filtrosAtivos.incoterms.size +
            this.filtrosAtivos.subrotas.size;

        const isActive = badge.classList.contains('ativo');

        if (!isActive && totalAtivos >= this.maxFiltrosAtivos) {
            // Mostrar mensagem de limite
            this.mostrarAlerta('Você pode selecionar no máximo 3 filtros simultaneamente');
            return;
        }

        // Toggle do badge - apenas classe 'ativo', CSS controla estilos
        badge.classList.toggle('ativo');

        // Atualizar estado dos filtros ativos
        if (badge.classList.contains('ativo')) {
            // Ativando filtro
            if (tipo === 'rota') {
                this.filtrosAtivos.rotas.add(valor);
                // Se ativou SP, mostrar subrotas
                if (valor === 'SP') {
                    this.mostrarSubrotasSP();
                }
            } else if (tipo === 'incoterm') {
                this.filtrosAtivos.incoterms.add(valor);
            } else if (tipo === 'subrota') {
                this.filtrosAtivos.subrotas.add(valor);
            }
        } else {
            // Desativando filtro
            if (tipo === 'rota') {
                this.filtrosAtivos.rotas.delete(valor);
                // Se desativou SP, esconder subrotas
                if (valor === 'SP') {
                    this.esconderSubrotasSP();
                }
            } else if (tipo === 'incoterm') {
                this.filtrosAtivos.incoterms.delete(valor);
            } else if (tipo === 'subrota') {
                this.filtrosAtivos.subrotas.delete(valor);
            }
        }

        // Mostrar/ocultar botões de limpar
        this.atualizarBotoesLimpar();

        // Aplicar filtros
        this.aplicarFiltros();

        // Verificar e mostrar subrotas SP se necessário
        this.verificarSubrotasSP();
    }

    verificarSubrotasSP() {
        const container = document.querySelector('.subrotas-sp-container');
        if (!container) return;

        // Mostrar subrotas se rota SP estiver ativa
        const spAtivo = this.filtrosAtivos.rotas.has('SP');
        container.style.display = spAtivo ? 'block' : 'none';
    }

    mostrarSubrotasSP() {
        const container = document.querySelector('.subrotas-sp-container');
        if (container) {
            container.style.display = 'block';
        }
    }

    esconderSubrotasSP() {
        const container = document.querySelector('.subrotas-sp-container');
        if (container) {
            container.style.display = 'none';
            // Limpar filtros de subrotas ao esconder
            document.querySelectorAll('.badge-subrota').forEach(badge => {
                badge.classList.remove('ativo');
            });
            this.filtrosAtivos.subrotas.clear();
        }
    }

    atualizarBotoesLimpar() {
        const limparRotas = document.getElementById('limpar-rotas');
        const limparSubrotas = document.getElementById('limpar-subrotas');
        const limparAgendamento = document.getElementById('limpar-agendamento');
        const limparAtendimento = document.getElementById('limpar-atendimento');

        if (limparRotas) {
            const temFiltrosRotas = this.filtrosAtivos.rotas.size > 0 || this.filtrosAtivos.incoterms.size > 0;
            limparRotas.style.display = temFiltrosRotas ? 'inline-block' : 'none';
        }

        if (limparSubrotas) {
            limparSubrotas.style.display = this.filtrosAtivos.subrotas.size > 0 ? 'inline-block' : 'none';
        }

        if (limparAgendamento) {
            limparAgendamento.style.display = this.filtrosAtivos.agendamento ? 'inline-block' : 'none';
        }

        if (limparAtendimento) {
            limparAtendimento.style.display = this.filtrosAtivos.atendimento ? 'inline-block' : 'none';
        }
    }

    toggleAgendamento(badge, valor) {
        // Remover ativo de todos os badges de agendamento (CSS controla estilos)
        document.querySelectorAll('[data-tipo="agendamento"]').forEach(b => {
            b.classList.remove('ativo');
        });

        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.agendamento === valor) {
            this.filtrosAtivos.agendamento = null;
            document.getElementById('limpar-agendamento').style.display = 'none';
        } else {
            // Ativar o novo (CSS controla estilos via classe 'ativo')
            badge.classList.add('ativo');
            this.filtrosAtivos.agendamento = valor;
            document.getElementById('limpar-agendamento').style.display = 'inline-block';
        }

        this.aplicarFiltros();
    }

    limparFiltrosRotas() {
        // Limpar badges de rotas e incoterms (CSS controla estilos)
        document.querySelectorAll('.badge-rota, .badge-incoterm').forEach(badge => {
            badge.classList.remove('ativo');
        });

        this.filtrosAtivos.rotas.clear();
        this.filtrosAtivos.incoterms.clear();
        this.esconderSubrotasSP();

        this.atualizarBotoesLimpar();
        this.aplicarFiltros();
    }

    limparFiltrosSubrotas() {
        // Limpar badges de subrotas (CSS controla estilos)
        document.querySelectorAll('.badge-subrota').forEach(badge => {
            badge.classList.remove('ativo');
        });

        this.filtrosAtivos.subrotas.clear();

        this.atualizarBotoesLimpar();
        this.aplicarFiltros();
    }

    limparFiltrosAgendamento() {
        // Limpar badges de agendamento (CSS controla estilos)
        document.querySelectorAll('[data-tipo="agendamento"]').forEach(badge => {
            badge.classList.remove('ativo');
        });
        this.filtrosAtivos.agendamento = null;
        this.aplicarFiltros();
        document.getElementById('limpar-agendamento').style.display = 'none';
    }

    toggleCliente(badge, valor) {
        // Remover ativo de todos os badges de cliente (CSS controla estilos)
        document.querySelectorAll('[data-tipo="cliente"]').forEach(b => {
            b.classList.remove('ativo');
        });

        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.cliente === valor) {
            this.filtrosAtivos.cliente = null;
            document.getElementById('limpar-cliente').style.display = 'none';
        } else {
            // Ativar o novo (CSS controla estilos via classe 'ativo')
            badge.classList.add('ativo');
            this.filtrosAtivos.cliente = valor;
            document.getElementById('limpar-cliente').style.display = 'inline-block';
        }

        this.aplicarFiltros();
    }

    toggleAtendimento(badge, valor) {
        // Remover ativo de todos os badges de atendimento (CSS controla estilos)
        document.querySelectorAll('[data-tipo="atendimento"]').forEach(b => {
            b.classList.remove('ativo');
        });

        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.atendimento === valor) {
            this.filtrosAtivos.atendimento = null;
            document.getElementById('limpar-atendimento').style.display = 'none';
        } else {
            // Ativar o novo (CSS controla estilos via classe 'ativo')
            badge.classList.add('ativo');
            this.filtrosAtivos.atendimento = valor;
            document.getElementById('limpar-atendimento').style.display = 'inline-block';
        }

        this.aplicarFiltros();
    }

    limparFiltrosCliente() {
        // Limpar badges de cliente (CSS controla estilos)
        document.querySelectorAll('[data-tipo="cliente"]').forEach(badge => {
            badge.classList.remove('ativo');
        });
        this.filtrosAtivos.cliente = null;
        this.aplicarFiltros();
        document.getElementById('limpar-cliente').style.display = 'none';
    }

    limparFiltrosAtendimento() {
        // Limpar badges de atendimento (CSS controla estilos)
        document.querySelectorAll('[data-tipo="atendimento"]').forEach(badge => {
            badge.classList.remove('ativo');
        });
        this.filtrosAtivos.atendimento = null;
        this.aplicarFiltros();
        document.getElementById('limpar-atendimento').style.display = 'none';
    }

    mostrarAlerta(mensagem) {
        // Usar módulo centralizado se disponível
        if (window.Notifications && window.Notifications.warning) {
            return window.Notifications.warning(mensagem);
        }

        // Fallback completo
        // Criar alerta temporário
        const alerta = document.createElement('div');
        alerta.className = 'alert alert-warning alert-dismissible fade show position-fixed';
        alerta.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 350px;';
        alerta.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alerta);

        // Remover após 3 segundos
        setTimeout(() => {
            alerta.remove();
        }, 3000);
    }

    setupExpandirColapsar() {
        const btnExpandir = document.getElementById('expandir-todos');
        const btnColapsar = document.getElementById('colapsar-todos');

        if (btnExpandir) {
            btnExpandir.addEventListener('click', () => this.expandirTodos());
        }

        if (btnColapsar) {
            btnColapsar.addEventListener('click', () => this.colapsarTodos());
        }
    }

    setupDetalhesExpansao() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-expandir')) {
                const btn = e.target.closest('.btn-expandir');
                const numPedido = btn.dataset.pedido;
                this.toggleDetalhes(numPedido);
            }
        });
    }

    // 🎯 FILTROS
    aplicarFiltros() {
        const termoBusca = document.getElementById('filtro-busca')?.value.toLowerCase() || '';
        const statusSelecionado = document.getElementById('filtro-status')?.value || '';
        const equipeSelecionada = document.getElementById('filtro-equipe')?.value || '';

        // 🆕 Filtros de data
        const datasPedido = {
            de: document.getElementById('filtro-data-pedido-de')?.value || '',
            ate: document.getElementById('filtro-data-pedido-ate')?.value || ''
        };
        const datasEntrega = {
            de: document.getElementById('filtro-data-entrega-de')?.value || '',
            ate: document.getElementById('filtro-data-entrega-ate')?.value || ''
        };

        // 🆕 Cancelar todas as requisições assíncronas pendentes
        this.cancelarTodasRequisicoes();

        // Limpar conjunto de pedidos visíveis
        this.pedidosVisiveis.clear();

        const linhasPedidos = document.querySelectorAll('.pedido-row');
        let totalVisiveis = 0;

        linhasPedidos.forEach(linha => {
            const textoFiltro = linha.dataset.filtro || '';
            const status = linha.dataset.status || '';
            const equipe = linha.dataset.equipe || '';
            const rota = linha.dataset.rota || '';
            const subrota = linha.dataset.subrota || '';
            const incoterm = linha.dataset.incoterm || 'CIF';
            const agendamento = linha.dataset.agendamento || 'sem';
            const temProtocoloSeparacao = linha.dataset.temProtocoloSeparacao === 'true';
            const agendamentoConfirmado = linha.dataset.agendamentoConfirmado === 'true';
            const protocolo = linha.dataset.protocolo || '';
            const dataEntregaPedido = linha.dataset.dataEntregaPedido || '';
            const agendamentoData = linha.dataset.agendamentoData || '';
            const grupoCliente = linha.dataset.grupoCliente || 'outros';

            // Aplicar filtros básicos
            const matchBusca = !termoBusca || textoFiltro.includes(termoBusca);
            const matchStatus = !statusSelecionado || status === statusSelecionado;
            const matchEquipe = !equipeSelecionada || equipe === equipeSelecionada;

            // Filtro de agendamento (incluindo filtros de separação com protocolo)
            let matchAgendamento = true;
            if (this.filtrosAtivos.agendamento) {
                if (this.filtrosAtivos.agendamento === 'sep-aguardando') {
                    // Pedidos com separação que NÃO têm agendamento confirmado
                    // (inclui: aguardando aprovação OU sem agendamento realizado)
                    matchAgendamento = status !== 'pendente' && !agendamentoConfirmado;
                } else if (this.filtrosAtivos.agendamento === 'sep-confirmado') {
                    // Pedidos com separação e agendamento confirmado
                    matchAgendamento = status !== 'pendente' && agendamentoConfirmado;
                } else {
                    // Filtros originais (sem/com agendamento)
                    matchAgendamento = agendamento === this.filtrosAtivos.agendamento;
                }
            }

            // Filtro de cliente (Atacadão, Sendas, Outros)
            let matchCliente = true;
            if (this.filtrosAtivos.cliente) {
                matchCliente = grupoCliente === this.filtrosAtivos.cliente;
            }

            // ⭐ Filtro de atendimento (Programar, Revisar Data) - REVISADO
            let matchAtendimento = true;
            if (this.filtrosAtivos.atendimento) {
                const agendamentoPrimeiraSep = linha.dataset.agendamentoPrimeiraSep || '';
                const qtdSeparacoes = parseInt(linha.querySelector('.contador-separacoes')?.textContent || '0');

                if (this.filtrosAtivos.atendimento === 'programar') {
                    // Pedidos com data_entrega_pedido E sem separações (qtd_separacoes == 0)
                    matchAtendimento = dataEntregaPedido && qtdSeparacoes === 0;
                } else if (this.filtrosAtivos.atendimento === 'revisar-data') {
                    // Pedidos com data_entrega_pedido diferente do agendamento da 1ª separação
                    matchAtendimento = dataEntregaPedido && agendamentoPrimeiraSep && agendamentoPrimeiraSep !== dataEntregaPedido;
                }
            }

            // 🆕 Filtros de data (inclusivo)
            let matchDataPedido = true;
            const dataPedido = linha.dataset.dataPedido || '';
            if (datasPedido.de || datasPedido.ate) {
                if (dataPedido) {
                    // Verificar range de data (inclusivo)
                    if (datasPedido.de && dataPedido < datasPedido.de) {
                        matchDataPedido = false;
                    }
                    if (datasPedido.ate && dataPedido > datasPedido.ate) {
                        matchDataPedido = false;
                    }
                } else {
                    // Se não tem data do pedido e filtro está ativo, não mostrar
                    matchDataPedido = false;
                }
            }

            let matchDataEntrega = true;
            const dataEntrega = linha.dataset.dataEntrega || '';
            if (datasEntrega.de || datasEntrega.ate) {
                if (dataEntrega) {
                    // Verificar range de data (inclusivo)
                    if (datasEntrega.de && dataEntrega < datasEntrega.de) {
                        matchDataEntrega = false;
                    }
                    if (datasEntrega.ate && dataEntrega > datasEntrega.ate) {
                        matchDataEntrega = false;
                    }
                } else {
                    // Se não tem data de entrega e filtro está ativo, não mostrar
                    matchDataEntrega = false;
                }
            }

            let matchBadges = true;

            // Filtros de badges (rotas/incoterms)
            if (this.filtrosAtivos.rotas.size > 0 || this.filtrosAtivos.incoterms.size > 0) {
                matchBadges = false;

                // Verificar incoterms FOB e RED primeiro
                if (this.filtrosAtivos.incoterms.has('FOB') && incoterm === 'FOB') {
                    matchBadges = true;
                } else if (this.filtrosAtivos.incoterms.has('RED') && incoterm === 'RED') {
                    matchBadges = true;
                }
                // Se o pedido é CIF, verificar rotas
                else if (incoterm === 'CIF' && this.filtrosAtivos.rotas.size > 0) {
                    if (this.filtrosAtivos.rotas.has(rota)) {
                        matchBadges = true;
                    }
                }
            }

            // Filtros de subrotas (apenas para SP)
            let matchSubrotas = true;
            if (this.filtrosAtivos.subrotas.size > 0) {
                // Se tem filtro de subrota ativo, só mostra pedidos de SP que tenham a subrota selecionada
                if (linha.dataset.uf === 'SP') {
                    matchSubrotas = this.filtrosAtivos.subrotas.has(subrota);
                } else {
                    // Se não é SP, não mostra quando há filtro de subrota ativo
                    matchSubrotas = false;
                }
            }

            // ⭐ Filtro de importante
            let matchImportante = true;
            if (this.filtrosAtivos.importante) {
                matchImportante = linha.dataset.importante === 'true';
            }

            const mostrar = matchBusca && matchStatus && matchEquipe && matchAgendamento && matchCliente && matchAtendimento && matchDataPedido && matchDataEntrega && matchImportante && matchBadges && matchSubrotas;

            linha.style.display = mostrar ? '' : 'none';

            // Ocultar também a linha de detalhes se existe
            const numPedido = linha.dataset.pedido;
            const linhaDetalhes = document.getElementById(`detalhes-${numPedido}`);
            if (linhaDetalhes) {
                linhaDetalhes.style.display = mostrar ? '' : 'none';
            }

            // 🆕 Ocultar também linha de separações/pré-separações quando pedido é filtrado
            const linhaSeparacoes = document.getElementById(`separacoes-compactas-${numPedido}`);
            if (linhaSeparacoes) {
                linhaSeparacoes.style.display = mostrar ? '' : 'none';
            }

            if (mostrar) {
                totalVisiveis++;
                // 🆕 Adicionar ao conjunto de pedidos visíveis
                this.pedidosVisiveis.add(numPedido);

                // NÃO carregar individual aqui!
                // Será carregado em lote após aplicar filtros
            }
        });

        if (DEBUG) console.log(`🔍 Filtros aplicados: ${totalVisiveis} pedidos visíveis`);

        // Atualizar contador de pedidos
        this.atualizarContador(totalVisiveis);

        // Verificar e mostrar/ocultar subrotas SP
        this.verificarSubrotasSP();

        // 🆕 CARREGAR SEPARAÇÕES COMPACTAS PARA TODOS OS PEDIDOS VISÍVEIS
        this.carregarSeparacoesCompactasVisiveis();
    }

    popularFiltroEquipes() {
        const filtroEquipe = document.getElementById('filtro-equipe');
        if (!filtroEquipe) return;

        const equipes = new Set();
        document.querySelectorAll('.pedido-row').forEach(linha => {
            const equipe = linha.dataset.equipe;
            if (equipe) equipes.add(equipe);
        });

        // Limpar e popular
        filtroEquipe.innerHTML = '<option value="">Todas equipes</option>';
        [...equipes].sort().forEach(equipe => {
            const option = document.createElement('option');
            option.value = equipe;
            option.textContent = equipe;
            filtroEquipe.appendChild(option);
        });
    }

    atualizarContador(totalVisiveis) {
        // Atualizar contador de pedidos visíveis
        const contador = document.getElementById('contador-pedidos');
        if (contador) {
            contador.textContent = totalVisiveis;
        }

        // Calcular e atualizar valor total dos pedidos visíveis
        this.atualizarValorTotal();

        // 🆕 ATUALIZAR CONTADOR DE PROTOCOLOS APÓS APLICAR FILTROS
        // Aguardar um pouco para garantir que as separações assíncronas carreguem
        setTimeout(() => {
            this.atualizarContadorProtocolos();
        }, 1500); // 1.5 segundos para dar tempo das separações carregarem
    }

    atualizarValorTotal() {
        let valorTotal = 0;

        // FIX E4: Usar data-valor numerico em vez de parsear texto formatado
        document.querySelectorAll('.pedido-row:not([style*="display: none"])').forEach(linha => {
            const valorElement = linha.querySelector('.valor-pedido');
            if (valorElement) {
                const valor = parseFloat(valorElement.dataset.valor) || 0;
                valorTotal += valor;
            }
        });

        // Formatar e exibir valor total
        const valorFormatado = new Intl.NumberFormat('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(valorTotal);

        const elementoValorTotal = document.getElementById('valor-total-filtro');
        if (elementoValorTotal) {
            elementoValorTotal.textContent = valorFormatado;
        }
    }

    // 🎯 EXPANDIR/COLAPSAR
    expandirTodos() {
        document.querySelectorAll('.pedido-row:not([style*="display: none"])').forEach(linha => {
            const numPedido = linha.dataset.pedido;
            const detalhesRow = document.getElementById(`detalhes-${numPedido}`);
            const icon = linha.querySelector('.expand-icon');

            if (detalhesRow && !detalhesRow.classList.contains('show')) {
                this.expandirDetalhes(numPedido, detalhesRow, icon);
            }
        });
        if (DEBUG) console.log('📖 Todos os pedidos expandidos');
    }

    colapsarTodos() {
        document.querySelectorAll('.detalhes-row.show').forEach(detalhesRow => {
            const numPedido = detalhesRow.id.replace('detalhes-', '');
            const linha = document.querySelector(`[data-pedido="${numPedido}"]`);
            const icon = linha?.querySelector('.expand-icon');

            this.colapsarDetalhes(detalhesRow, icon);
        });
        if (DEBUG) console.log('📖 Todos os pedidos colapsados');
    }

    // 🎯 DETALHES DOS PEDIDOS
    toggleDetalhes(numPedido) {
        const detalhesRow = document.getElementById(`detalhes-${numPedido}`);
        const linha = document.querySelector(`[data-pedido="${numPedido}"]`);
        const icon = linha?.querySelector('.expand-icon');

        if (!detalhesRow) return;

        if (detalhesRow.classList.contains('show')) {
            this.colapsarDetalhes(detalhesRow, icon);
        } else {
            this.expandirDetalhes(numPedido, detalhesRow, icon);
        }
    }

    expandirDetalhes(numPedido, detalhesRow, icon) {
        detalhesRow.classList.add('show');
        if (icon) {
            icon.classList.remove('fa-chevron-right');
            icon.classList.add('fa-chevron-down');
        }

        // SOLUÇÃO: Chamar diretamente o workspace em vez de carregarDetalhes
        const contentDiv = document.getElementById(`content-${numPedido}`);

        // Verificar se o conteúdo já foi carregado
        // Se não tem conteúdo HTML ou está oculto, carregar workspace
        if (contentDiv && (!contentDiv.innerHTML.trim() || contentDiv.style.display === 'none')) {
            // Chamar workspace diretamente
            if (window.workspace && window.workspace.abrirWorkspace) {
                if (DEBUG) console.log(`🚀 Abrindo workspace para pedido ${numPedido}`);
                window.workspace.abrirWorkspace(numPedido);
            } else {
                console.error('❌ WorkspaceMontagem não está disponível');
                contentDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Erro: Sistema de workspace não está carregado
                    </div>
                `;
                contentDiv.style.display = 'block';
            }
        }
    }

    colapsarDetalhes(detalhesRow, icon) {
        detalhesRow.classList.remove('show');
        if (icon) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-right');
        }
    }


    // REMOVED: renderizarDetalhes - Método não utilizado (sem chamadas encontradas)

    // 🎯 UTILITÁRIOS
    formatarMoeda(valor) {
        return window.Formatters.moeda(valor);
    }

    formatarQuantidade(qtd) {
        return window.Formatters.quantidade(qtd);
    }

    /**
     * 🆕 VERIFICAR SE PEDIDO ESTÁ VISÍVEL
     */
    isPedidoVisivel(numPedido) {
        // Sempre verificar diretamente no DOM para garantir precisão
        const pedidoRow = document.querySelector(`.pedido-row[data-pedido="${numPedido}"]`);
        if (!pedidoRow) return false;

        // Verificar se está visível no DOM
        return pedidoRow.style.display !== 'none';
    }

    /**
     * 🆕 CANCELAR TODAS AS REQUISIÇÕES ASSÍNCRONAS
     */
    cancelarTodasRequisicoes() {
        if (DEBUG) console.log(`🚫 Cancelando ${this.abortControllers.size} requisições assíncronas...`);
        this.abortControllers.forEach((controller) => {
            controller.abort();
        });
        this.abortControllers.clear();

        // 🆕 Também cancelar requisições de estoque do workspace
        if (window.workspace && window.workspace.abortControllerEstoque) {
            window.workspace.abortControllerEstoque.abort();
            window.workspace.abortControllerEstoque = null;
            if (DEBUG) console.log(`✔️ Carregamento de estoque do workspace cancelado`);
        }
    }

    formatarData(data) {
        return window.Formatters.data(data) || '-';
    }

    formatarPeso(peso) {
        return window.Formatters.peso(peso);
    }

    formatarPallet(pallet) {
        return window.Formatters.pallet(pallet);
    }

    /**
     * 🆕 CARREGAR SEPARAÇÕES EM LOTE PARA UM ÚNICO PEDIDO
     */
    async carregarSeparacoesEmLoteUnico(pedidos) {
        if (!pedidos || pedidos.length === 0) return;

        // Inicializar cache se não existir
        if (!window.separacoesCompactasCache) {
            window.separacoesCompactasCache = {};
        }

        try {
            const response = await fetch('/carteira/api/separacoes-compactas-lote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    pedidos: pedidos,
                    limite: pedidos.length
                })
            });

            if (response.ok) {
                const data = await response.json();

                // LOG DE DEBUG: Verificar resposta completa da API
                if (DEBUG) console.log('🔍 DEBUG API Response (carregarSeparacoesEmLoteUnico):', data);

                if (data.success && data.pedidos) {
                    // Salvar no cache
                    Object.keys(data.pedidos).forEach(numPedido => {
                        const separacoes = data.pedidos[numPedido];

                        // LOG DE DEBUG: Verificar estrutura de cada separação
                        if (DEBUG) console.log(`📦 DEBUG - Pedido ${numPedido} - Separações da API:`, separacoes);
                        if (separacoes && separacoes.length > 0) {
                            if (DEBUG) console.log(`📅 DEBUG - Primeira separação tem expedição? ${separacoes[0].expedicao}, agendamento? ${separacoes[0].agendamento}`);
                        }

                        window.separacoesCompactasCache[numPedido] = separacoes;

                        // SEMPRE renderizar e tornar visível se houver separações
                        if (separacoes && separacoes.length > 0) {
                            const separacoesRow = document.getElementById(`separacoes-compactas-${numPedido}`);
                            if (separacoesRow) {
                                // Tornar a linha visível
                                separacoesRow.style.display = 'table-row';
                                // Renderizar o conteúdo
                                this.renderizarSeparacaoDoCache(numPedido);
                            }
                        }
                    });

                    if (DEBUG) console.log(`✅ Carregado: ${Object.keys(data.pedidos).length} pedidos`);

                    // Atualizar contador
                    this.atualizarContadorProtocolos();
                }
            }
        } catch (error) {
            console.error('❌ Erro ao carregar separações:', error);
        }
    }

    /**
     * 🆕 RENDERIZAR SEPARAÇÃO DO CACHE
     */
    renderizarSeparacaoDoCache(numPedido) {
        const separacoes = window.separacoesCompactasCache?.[numPedido];
        if (!separacoes || separacoes.length === 0) return;

        const container = document.querySelector(`#separacoes-compactas-${numPedido} .separacoes-compactas-container`);
        if (!container) return;

        // Log de debug para verificar estrutura do cache
        if (DEBUG) console.log(`📊 Dados do cache para pedido ${numPedido}:`, separacoes);

        // Converter formato do cache para o formato esperado por renderizarSeparacoesCompactas
        const separacoesData = {
            success: true,
            separacoes: separacoes.map(sep => {
                // Log de debug para cada separação
                if (DEBUG) console.log(`📅 Mapeando separação - expedição: ${sep.expedicao}, agendamento: ${sep.agendamento}`);

                return {
                    separacao_lote_id: sep.lote_id,
                    status: sep.status,
                    valor_total: sep.valor,
                    peso_total: sep.peso,
                    pallet_total: sep.pallet,
                    expedicao: sep.expedicao,
                    agendamento: sep.agendamento,
                    protocolo: sep.protocolo,
                    agendamento_confirmado: sep.agendamento_confirmado,
                    obs_separacao: sep.obs_separacao  // Observação da separação
                };
            })
        };

        // Usar o método existente de renderização
        const html = this.renderizarSeparacoesCompactas(separacoesData);
        container.innerHTML = html;
    }

    /**
     * 🆕 CARREGAR TODAS AS SEPARAÇÕES COMPACTAS
     */
    async carregarTodasSeparacoesCompactas() {
        if (DEBUG) console.log('📦 Carregando separações compactas para TODOS os pedidos...');

        // Buscar todos os pedidos na página
        const todosPedidos = [];
        document.querySelectorAll('.pedido-row').forEach(row => {
            const numPedido = row.dataset.pedido || row.dataset.numPedido;
            if (numPedido) {
                todosPedidos.push(numPedido);
            }
        });

        // Carregar em lote
        if (todosPedidos.length > 0) {
            // Dividir em lotes de 50 se necessário
            for (let i = 0; i < todosPedidos.length; i += 50) {
                const lote = todosPedidos.slice(i, i + 50);
                await this.carregarSeparacoesEmLoteUnico(lote);
            }
        }
    }

    /**
     * 🆕 CARREGAR SEPARAÇÕES COMPACTAS PARA TODOS OS PEDIDOS VISÍVEIS - OTIMIZADO EM LOTE
     */
    async carregarSeparacoesCompactasVisiveis() {
        // Coletar pedidos que precisam carregar separações
        const pedidosParaCarregar = [];

        this.pedidosVisiveis.forEach(numPedido => {
            // Verificar se as separações já foram carregadas
            if (!window.separacoesCompactasCache || !window.separacoesCompactasCache[numPedido]) {
                pedidosParaCarregar.push(numPedido);
            }
        });

        if (pedidosParaCarregar.length === 0) {
            if (DEBUG) console.log('✅ Todas as separações já estão em cache');
            return;
        }

        if (DEBUG) console.log(`📦 Carregando separações em LOTE para ${pedidosParaCarregar.length} pedidos...`);

        // Inicializar cache se não existir
        if (!window.separacoesCompactasCache) {
            window.separacoesCompactasCache = {};
        }

        try {
            // Dividir em lotes de 50 pedidos para não sobrecarregar
            const tamanhoLote = 50;
            for (let i = 0; i < pedidosParaCarregar.length; i += tamanhoLote) {
                const lote = pedidosParaCarregar.slice(i, i + tamanhoLote);

                // Fazer requisição em lote
                const response = await fetch('/carteira/api/separacoes-compactas-lote', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        pedidos: lote,
                        limite: tamanhoLote
                    })
                });

                if (response.ok) {
                    const data = await response.json();

                    // LOG DE DEBUG: Verificar resposta completa da API
                    if (DEBUG) console.log('🔍 DEBUG API Response (carregarSeparacoesEmLote):', data);

                    if (data.success && data.pedidos) {
                        // Salvar no cache E renderizar
                        Object.keys(data.pedidos).forEach(numPedido => {
                            const separacoes = data.pedidos[numPedido];

                            // LOG DE DEBUG: Verificar estrutura de cada separação
                            if (DEBUG) console.log(`📦 DEBUG - Pedido ${numPedido} - Separações da API:`, separacoes);
                            if (separacoes && separacoes.length > 0) {
                                if (DEBUG) console.log(`📅 DEBUG - Primeira separação tem expedição? ${separacoes[0].expedicao}, agendamento? ${separacoes[0].agendamento}`);
                            }

                            window.separacoesCompactasCache[numPedido] = separacoes;

                            // RENDERIZAR se houver separações
                            if (separacoes && separacoes.length > 0) {
                                const separacoesRow = document.getElementById(`separacoes-compactas-${numPedido}`);
                                if (separacoesRow) {
                                    // Tornar visível
                                    separacoesRow.style.display = 'table-row';
                                    // Renderizar conteúdo
                                    this.renderizarSeparacaoDoCache(numPedido);
                                }
                            }
                        });

                        if (DEBUG) console.log(`✅ Lote ${Math.floor(i / tamanhoLote) + 1}: ${Object.keys(data.pedidos).length} pedidos carregados`);
                        if (DEBUG) console.log(`   📊 Total separações: ${data.totais.total_separacoes}`);
                        if (DEBUG) console.log(`   🔖 Protocolos pendentes: ${data.totais.protocolos_unicos_pendentes}`);
                    }
                } else {
                    console.error(`❌ Erro ao carregar lote ${Math.floor(i / tamanhoLote) + 1}`);
                }
            }

            // Atualizar contador após carregar tudo
            this.atualizarContadorProtocolos();

        } catch (error) {
            console.error('❌ Erro ao carregar separações em lote:', error);
            // Não fazer fallback - carregamento individual é muito lento
        }
    }

    // REMOVIDO: carregarSeparacoesCompactasPedido - método obsoleto de carregamento individual

    /**
     * 🆕 RENDERIZAÇÃO COMPACTA DE SEPARAÇÕES E PRÉ-SEPARAÇÕES
     */
    renderizarSeparacoesCompactas(separacoesData) {
        const todasSeparacoes = [];

        // Adicionar separações confirmadas
        if (separacoesData && separacoesData.success && separacoesData.separacoes) {
            separacoesData.separacoes.forEach(sep => {
                todasSeparacoes.push({
                    tipo: 'Separação',
                    status: sep.status || '',
                    loteId: sep.separacao_lote_id,
                    valor: sep.valor_total || 0,
                    peso: sep.peso_total || 0,
                    pallet: sep.pallet_total || 0,
                    expedicao: sep.expedicao,
                    agendamento: sep.agendamento,
                    protocolo: sep.protocolo,
                    agendamento_confirmado: sep.agendamento_confirmado,
                    obs_separacao: sep.obs_separacao,  // Observação da separação
                    isSeparacao: true
                });
            });
        }


        // Se não houver nenhuma separação
        if (todasSeparacoes.length === 0) {
            return '';
        }

        // Renderizar tabela compacta
        return `
            <div class="separacoes-compactas-container p-2 border-bottom">
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0 table-separacoes-compactas">
                        <thead>
                            <tr>
                                <th width="80">Tipo</th>
                                <th width="70">Status</th>
                                <th width="90" class="text-end">Valor</th>
                                <th width="70" class="text-end">Peso</th>
                                <th width="60" class="text-end">Pallet</th>
                                <th width="85" class="text-center">Expedição</th>
                                <th width="85" class="text-center">Agendamento</th>
                                <th width="80">Protocolo</th>
                                <th width="90" class="text-center">Confirmação</th>
                                <th width="200">Obs. Separação</th>
                                <th width="280" class="text-center">Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${todasSeparacoes.map(item => this.renderizarLinhaSeparacaoCompacta(item)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * 🆕 RENDERIZAR LINHA INDIVIDUAL DA SEPARAÇÃO COMPACTA
     */
    renderizarLinhaSeparacaoCompacta(item) {
        const tipoClass = item.isSeparacao ? '' : 'text-muted';
        const statusBadge = item.status ?
            (item.status === 'PREVISAO' ? '<span class="badge bg-secondary">PREVISAO</span>' :
                item.status === 'COTADO' ? '<span class="badge bg-warning text-dark">COTADO</span>' :
                    item.status === 'FATURADO' ? '<span class="badge bg-success">FATURADO</span>' :
                        item.status === 'EMBARCADO' ? '<span class="badge bg-success">EMBARCADO</span>' :
                            item.status === 'NF no CD' ? '<span class="badge bg-danger">NF no CD</span>' :
                                item.status === 'ABERTO' ? '<span class="badge bg-secondary">ABERTO</span>' : '') : '';

        const confirmacaoBadge = item.agendamento ?
            (item.agendamento_confirmado ?
                '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Confirmado</span>' :
                '<span class="badge bg-warning text-dark"><i class="fas fa-hourglass-half"></i> Aguardando</span>') : '-';

        // Observação da separação com tooltip
        const obsSeparacao = item.obs_separacao ?
            `<span class="obs-separacao-texto obs-ellipsis"
                   title="${item.obs_separacao.replace(/"/g, '&quot;')}">
                <i class="fas fa-comment-alt text-muted me-1"></i>${item.obs_separacao}
             </span>` : '-';

        return `
            <tr data-lote-id="${item.loteId}" id="separacao-compacta-${item.loteId}">
                <td><strong class="${tipoClass}">${item.tipo}</strong></td>
                <td>${statusBadge}</td>
                <td class="text-end text-success">${this.formatarMoeda(item.valor)}</td>
                <td class="text-end">${this.formatarPeso(item.peso)}</td>
                <td class="text-end">${this.formatarPallet(item.pallet)}</td>
                <td class="text-center" data-field="expedicao">${item.expedicao ? this.formatarData(item.expedicao) : '-'}</td>
                <td class="text-center" data-field="agendamento">${item.agendamento ? this.formatarData(item.agendamento) : '-'}</td>
                <td data-field="protocolo"><small>${item.protocolo || '-'}</small></td>
                <td class="text-center" data-field="confirmacao">${confirmacaoBadge}</td>
                <td data-field="obs_separacao"><small>${obsSeparacao}</small></td>
                <td class="text-center">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-secondary btn-sm"
                                onclick="carteiraAgrupada.abrirModalDatas('${item.loteId}', ${item.isSeparacao}, '${item.expedicao || ''}', '${item.agendamento || ''}', '${item.protocolo || ''}', ${item.agendamento_confirmado || false})"
                                title="Editar datas">
                            <i class="fas fa-calendar-alt"></i> Datas
                        </button>
                        ${item.status === 'PREVISAO' ? `
                            <button class="btn btn-outline-secondary btn-sm"
                                    onclick="carteiraAgrupada.alterarStatusSeparacao('${item.loteId}', 'ABERTO')"
                                    title="Confirmar separação">
                                <i class="fas fa-check"></i> Confirmar
                            </button>
                        ` : ''}
                        <button class="btn btn-outline-secondary btn-sm"
                                onclick="carteiraAgrupada.agendarNoPortal('${item.loteId}', '${item.agendamento || ''}')"
                                title="Agendar no portal">
                            <i class="fas fa-calendar-plus"></i> Agendar
                        </button>
                        ${item.protocolo ? `
                            <button class="btn btn-outline-secondary btn-sm"
                                    onclick="carteiraAgrupada.verificarAgendamento('${item.loteId}', '${item.protocolo}')"
                                    title="Verificar agendamento no portal">
                                <i class="fas fa-search"></i> Ver.Agenda
                            </button>
                        ` : ''}
                        <button class="btn btn-outline-secondary btn-sm"
                                onclick="carteiraAgrupada.excluirSeparacao('${item.loteId}')"
                                title="Excluir separação">
                            <i class="fas fa-trash"></i> Excluir
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * 🆕 RENDERIZAR DETALHES BÁSICOS (sem estoque)
     */
    /**
     * 🆕 CARREGAR ESTOQUE DE FORMA ASSÍNCRONA
     */
    async carregarEstoqueAssincrono(numPedido, itens) {
        try {
            if (DEBUG) console.log(`📊 Carregando estoque assíncrono para pedido ${numPedido}`);

            // Mostrar loading
            const loadingSpinner = document.getElementById(`loading-estoque-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'inline-block';
            }

            // Fazer requisição para obter estoque
            const response = await fetch(`/carteira/api/pedido/${numPedido}/estoque`);

            if (!response.ok) {
                throw new Error('Erro ao carregar estoque');
            }

            const estoqueData = await response.json();

            if (estoqueData.success && estoqueData.produtos) {
                // Atualizar cada célula de estoque
                estoqueData.produtos.forEach(produto => {
                    const cellEstoque = document.getElementById(`estoque-${produto.cod_produto}`);
                    const cellMenorEstoque = document.getElementById(`menor-estoque-${produto.cod_produto}`);

                    if (cellEstoque) {
                        const estoque = produto.estoque || produto.estoque_d0 || 0;
                        const badgeClass = estoque > 0 ? 'bg-success' : 'bg-danger';
                        cellEstoque.innerHTML = `
                            <span class="badge ${badgeClass}">
                                ${this.formatarQuantidade(estoque)}
                            </span>
                        `;
                    }

                    if (cellMenorEstoque) {
                        const menorEstoque = produto.menor_estoque_produto_d7 || 0;
                        const badgeClass = menorEstoque <= 0 ? 'bg-danger' : menorEstoque < 10 ? 'bg-warning' : 'bg-secondary';
                        cellMenorEstoque.innerHTML = `
                            <span class="badge ${badgeClass}">
                                ${this.formatarQuantidade(menorEstoque)}
                            </span>
                        `;
                    }
                });
            }

            // Esconder loading
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }

        } catch (error) {
            console.error('❌ Erro ao carregar estoque:', error);

            // Esconder loading
            const loadingSpinner = document.getElementById(`loading-estoque-${numPedido}`);
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }

            // Mostrar erro nas células
            if (itens) {
                itens.forEach(item => {
                    const cellEstoque = document.getElementById(`estoque-${item.cod_produto}`);
                    const cellMenorEstoque = document.getElementById(`menor-estoque-${item.cod_produto}`);

                    if (cellEstoque) {
                        cellEstoque.innerHTML = '<small class="text-muted">-</small>';
                    }
                    if (cellMenorEstoque) {
                        cellMenorEstoque.innerHTML = '<small class="text-muted">-</small>';
                    }
                });
            }
        }
    }

    /**
     * 🆕 FUNÇÕES AUXILIARES PARA BOTÕES
     */
    async abrirModalDatas(loteId, isSeparacao, expedicao, agendamento, protocolo, agendamentoConfirmado) {
        if (DEBUG) console.log(`📅 Abrindo modal de datas para ${loteId} (Separação: ${isSeparacao})`);
        if (DEBUG) console.log(`   Dados: expedição=${expedicao}, agendamento=${agendamento}, protocolo=${protocolo}, confirmado=${agendamentoConfirmado}`);

        // Redirecionar para workspace se disponível
        if (window.workspace) {
            // Passar os dados diretamente para o workspace
            const dadosModal = {
                expedicao: expedicao || '',
                agendamento: agendamento || '',
                protocolo: protocolo || '',
                agendamento_confirmado: agendamentoConfirmado || false
            };

            // Usar método unificado para editar datas
            window.workspace.abrirModalEdicaoDatasDireto('separacao', loteId, dadosModal);
        } else {
            alert('Função de edição de datas em desenvolvimento');
        }
    }

    async alterarStatusSeparacao(loteId, novoStatus) {
        if (DEBUG) console.log(`🔄 Alterando status da separação ${loteId} para ${novoStatus}`);

        try {
            // Buscar dados da separação para verificar se tem agendamento
            const response = await fetch(`/carteira/api/separacao/${loteId}/detalhes`);
            let dadosSeparacao = null;

            if (response.ok) {
                dadosSeparacao = await response.json();
            }

            // Alterar status usando API unificada
            if (window.separacaoManager && window.separacaoManager.alterarStatus) {
                await window.separacaoManager.alterarStatus(loteId, novoStatus);

                // 🆕 Se houver data de agendamento e mudando para ABERTO, agendar automaticamente no portal
                if (novoStatus === 'ABERTO' && dadosSeparacao && dadosSeparacao.agendamento && !dadosSeparacao.protocolo) {
                    if (DEBUG) console.log('🤖 Agendando automaticamente no portal após confirmação...');
                    setTimeout(() => {
                        this.agendarNoPortal(loteId, dadosSeparacao.agendamento);
                    }, 2000); // Aguardar 2 segundos após confirmação
                }
            } else {
                if (confirm(`Alterar status da separação ${loteId} para ${novoStatus}?`)) {
                    // Fazer confirmação via API se workspace não estiver disponível
                    const confirmResponse = await fetch(`/carteira/api/separacao/${loteId}/alterar-status`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                        },
                        body: JSON.stringify({ novo_status: novoStatus })
                    });

                    if (confirmResponse.ok) {
                        // 🆕 Agendar automaticamente se tiver data de agendamento
                        if (dadosSeparacao && dadosSeparacao.agendamento && !dadosSeparacao.protocolo) {
                            if (DEBUG) console.log('🤖 Agendando automaticamente no portal após confirmação...');
                            setTimeout(() => {
                                this.agendarNoPortal(loteId, dadosSeparacao.agendamento);
                            }, 2000);
                        } else {
                            location.reload();
                        }
                    }
                }
            }
        } catch (error) {
            console.error('❌ Erro ao confirmar pré-separação:', error);
            alert('Erro ao confirmar pré-separação. Verifique o console.');
        }
    }


    // Alias para compatibilidade
    async agendarNoPortal(loteId, dataAgendamento) {
        return window.PortalAgendamento.agendarNoPortal(loteId, dataAgendamento);
    }

    // Delegar para módulo centralizado
    async verificarAgendamento(loteId, protocolo) {
        if (protocolo) {
            return window.PortalAgendamento.verificarProtocoloNoPortal(loteId, protocolo);
        } else {
            return window.PortalAgendamento.verificarPortal(loteId);
        }
    }

    /**
     * 🗑️ EXCLUIR SEPARAÇÃO COMPACTA
     * Delega para o separacaoManager que já tem toda a lógica
     */
    async excluirSeparacao(loteId) {
        if (DEBUG) console.log(`🗑️ Excluindo separação ${loteId}`);

        // Usar separacaoManager se disponivel
        if (window.separacaoManager && typeof window.separacaoManager.excluirSeparacao === 'function') {
            // FIX I6: Buscar botao via querySelector em vez de depender de window.event (deprecated)
            const btn = document.querySelector(`button[onclick*="excluirSeparacao('${loteId}')"]`);
            const tr = btn?.closest('tr');
            const table = tr?.closest('table');
            const container = table?.closest('.separacoes-compactas-container');
            const pedidoRow = container?.closest('.pedido-detalhes')?.previousElementSibling;
            const numPedido = pedidoRow?.dataset?.pedido || pedidoRow?.dataset?.numPedido || '';

            const resultado = await window.separacaoManager.excluirSeparacao(loteId, numPedido);

            if (resultado && resultado.success) {
                // Remover a linha da tabela imediatamente
                tr.style.transition = 'opacity 0.3s';
                tr.style.opacity = '0';
                setTimeout(() => {
                    tr.remove();

                    // Se não houver mais linhas, esconder a tabela
                    const tbody = table.querySelector('tbody');
                    if (!tbody || tbody.children.length === 0) {
                        container.remove();
                    }
                }, 300);

                // Atualizar cache se existir
                if (window.separacoesCompactasCache && numPedido) {
                    const cache = window.separacoesCompactasCache[numPedido];
                    if (cache) {
                        const index = cache.findIndex(s => s.lote_id === loteId || s.separacao_lote_id === loteId);
                        if (index > -1) {
                            cache.splice(index, 1);
                        }
                    }
                }

                // Mostrar mensagem de sucesso
                this.mostrarSucesso('Separação excluída com sucesso');
            } else {
                this.mostrarErro(resultado?.error || 'Erro ao excluir separação');
            }
        } else {
            // Fallback direto para API se separacaoManager não estiver disponível
            if (confirm('Confirma a exclusão desta separação?')) {
                try {
                    const response = await fetch(`/carteira/api/separacao/${loteId}/excluir`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                        }
                    });

                    if (response.ok) {
                        location.reload(); // Recarregar página como fallback
                    } else {
                        this.mostrarErro('Erro ao excluir separação');
                    }
                } catch (error) {
                    console.error('Erro:', error);
                    this.mostrarErro('Erro ao excluir separação');
                }
            }
        }
    }

    /**
     * 🔄 VERIFICAÇÃO EM LOTE DE AGENDAMENTOS
     * Verifica até 50 protocolos de uma vez no portal do Atacadão
     */
    async verificarAgendasEmLote() {
        try {
            // CORRIGIDO: Coletar protocolos das SEPARAÇÕES (não dos pedidos)
            const protocolosUnicos = new Map(); // Usar Map para manter dados do primeiro encontrado
            const pedidosVisiveis = document.querySelectorAll('.pedido-row:not([style*="display: none"])');

            pedidosVisiveis.forEach(pedidoRow => {
                const numPedido = pedidoRow.dataset.pedido || pedidoRow.dataset.numPedido;

                // Buscar nas separações compactas em cache
                const separacoesCompactas = window.separacoesCompactasCache?.[numPedido];

                if (separacoesCompactas && separacoesCompactas.length > 0) {
                    separacoesCompactas.forEach(sep => {
                        // Verificar se separação tem protocolo válido e não confirmado
                        if (sep.protocolo &&
                            sep.protocolo !== '' &&
                            sep.protocolo !== 'null' &&
                            sep.protocolo !== 'Vazio' &&
                            sep.protocolo !== 'vazio' &&
                            !sep.agendamento_confirmado) {

                            // Adicionar ao Map apenas se ainda não existe (evita duplicatas)
                            if (!protocolosUnicos.has(sep.protocolo)) {
                                protocolosUnicos.set(sep.protocolo, {
                                    protocolo: sep.protocolo,
                                    lote_id: sep.lote_id || sep.separacao_lote_id,
                                    num_pedido: numPedido
                                });
                            }
                        }
                    });
                }
            });

            // Converter Map para Array
            const protocolosParaVerificar = Array.from(protocolosUnicos.values());

            if (DEBUG) console.log(`📊 Protocolos únicos encontrados para verificar: ${protocolosParaVerificar.length}`);

            if (protocolosParaVerificar.length === 0) {
                Swal.fire({
                    icon: 'info',
                    title: 'Nenhum protocolo para verificar',
                    text: 'Não há protocolos pendentes de confirmação nos pedidos visíveis.',
                    confirmButtonText: 'OK'
                });
                return;
            }

            // Confirmar ação
            const result = await Swal.fire({
                icon: 'question',
                title: 'Verificar Agendamentos',
                html: `
                    <p>Serão verificados <strong>${protocolosParaVerificar.length}</strong> protocolos únicos no portal.</p>
                    <p class="text-muted small">Esta operação será executada em segundo plano e pode levar alguns minutos.</p>
                `,
                showCancelButton: true,
                confirmButtonText: 'Verificar',
                cancelButtonText: 'Cancelar',
                confirmButtonColor: window.Notifications?.colors?.neutral || '#6c757d'
            });

            if (!result.isConfirmed) return;

            // Mostrar loading
            Swal.fire({
                title: 'Enviando para verificação...',
                text: 'Aguarde enquanto os protocolos são enfileirados',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // Enviar para API
            const response = await fetch('/portal/api/verificar-agendas-lote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    protocolos: protocolosParaVerificar,
                    portal: 'atacadao'
                })
            });

            const data = await response.json();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Verificação iniciada!',
                    html: `
                        <p>${data.total_enfileirados} protocolos foram enviados para verificação.</p>
                        <p class="text-muted small">Os status serão atualizados automaticamente conforme forem processados.</p>
                        ${data.task_id ? `<p class="text-muted small">Task ID: ${data.task_id}</p>` : ''}
                    `,
                    confirmButtonText: 'OK'
                });

                // Iniciar polling para atualizar status
                if (data.task_id) {
                    this.iniciarPollingVerificacao(data.task_id);
                }
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: data.message || 'Erro ao enviar protocolos para verificação',
                    confirmButtonText: 'OK'
                });
            }
        } catch (error) {
            console.error('Erro ao verificar agendas em lote:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao comunicar com o servidor',
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * Polling para atualizar status das verificações
     */
    iniciarPollingVerificacao(taskId) {
        let tentativas = 0;
        const maxTentativas = 60; // 5 minutos (5 segundos * 60)

        const interval = setInterval(async () => {
            tentativas++;

            try {
                const response = await fetch(`/portal/api/status-verificacao/${taskId}`);
                const data = await response.json();

                if (data.status === 'completed' || tentativas >= maxTentativas) {
                    clearInterval(interval);

                    // Atualizar contador
                    this.atualizarContadorProtocolos();

                    // Se completou, mostrar resultado
                    if (data.status === 'completed') {
                        if (DEBUG) console.log('✅ Verificação concluída:', data.resultados);

                        // Recarregar página para mostrar atualizações
                        if (data.atualizados > 0) {
                            Swal.fire({
                                icon: 'success',
                                title: 'Verificação concluída!',
                                html: `
                                    <p><strong>${data.atualizados}</strong> agendamentos foram atualizados.</p>
                                    <p>A página será recarregada para mostrar as alterações.</p>
                                `,
                                timer: 3000,
                                timerProgressBar: true,
                                didClose: () => {
                                    location.reload();
                                }
                            });
                        }
                    }
                } else if (data.status === 'processing') {
                    // Atualizar progresso se disponível
                    if (DEBUG) console.log(`🔄 Processando... ${data.processados}/${data.total}`);
                }
            } catch (error) {
                console.error('Erro no polling:', error);
                clearInterval(interval);
            }
        }, 5000); // Verificar a cada 5 segundos
    }

    /**
     * Atualizar contador de protocolos pendentes ÚNICOS (visíveis na tela)
     * CORRIGIDO: Busca protocolos nas SEPARAÇÕES (não nos pedidos)
     */
    atualizarContadorProtocolos() {
        // Coletar protocolos únicos das SEPARAÇÕES dos pedidos visíveis
        const protocolosUnicos = new Set();

        const pedidosVisiveis = document.querySelectorAll(
            '.pedido-row:not([style*="display: none"])'
        );

        if (DEBUG) console.log(`🔍 DEBUG: Total de pedidos visíveis: ${pedidosVisiveis.length}`);

        let debugPedidosComProtocolo = 0;
        let debugPedidosSemProtocolo = 0;
        let debugProtocolosConfirmados = 0;
        let debugTotalSeparacoes = 0;

        pedidosVisiveis.forEach(pedidoRow => {
            // FIX I4: Template usa data-pedido (nao data-num-pedido)
            const numPedido = pedidoRow.dataset.pedido || pedidoRow.dataset.numPedido;

            // Buscar nas separacoes compactas em cache
            const separacoesCompactas = window.separacoesCompactasCache?.[numPedido];

            if (separacoesCompactas && separacoesCompactas.length > 0) {
                let pedidoTemProtocolo = false;

                separacoesCompactas.forEach(sep => {
                    debugTotalSeparacoes++;

                    // Verificar se separação tem protocolo válido e não confirmado
                    if (sep.protocolo &&
                        sep.protocolo !== '' &&
                        sep.protocolo !== 'null' &&
                        sep.protocolo !== 'Vazio' &&
                        sep.protocolo !== 'vazio') {

                        pedidoTemProtocolo = true;

                        if (sep.agendamento_confirmado) {
                            debugProtocolosConfirmados++;
                        } else {
                            // Adicionar protocolo único pendente
                            protocolosUnicos.add(sep.protocolo);
                        }
                    }
                });

                if (pedidoTemProtocolo) {
                    debugPedidosComProtocolo++;
                } else {
                    debugPedidosSemProtocolo++;
                }
            } else {
                // Pedido sem separações carregadas
                debugPedidosSemProtocolo++;
            }
        });

        const totalProtocolosUnicos = protocolosUnicos.size;

        if (DEBUG) console.log(`📊 DEBUG Contadores (SEPARAÇÕES):
            - Pedidos visíveis: ${pedidosVisiveis.length}
            - Pedidos com protocolo: ${debugPedidosComProtocolo}
            - Pedidos sem protocolo: ${debugPedidosSemProtocolo}
            - Total separações verificadas: ${debugTotalSeparacoes}
            - Protocolos confirmados: ${debugProtocolosConfirmados}
            - Protocolos únicos pendentes: ${totalProtocolosUnicos}
            - Exemplos: ${Array.from(protocolosUnicos).slice(0, 5).join(', ')}${protocolosUnicos.size > 5 ? '...' : ''}`);

        const contador = document.getElementById('contador-protocolos');
        if (contador) {
            contador.textContent = totalProtocolosUnicos;
            contador.className = totalProtocolosUnicos > 0 ? 'badge bg-secondary ms-1' : 'badge bg-secondary ms-1';
        }
    }

    /**
     * Atualizar contador de TODOS protocolos pendentes (busca no servidor)
     */
    async atualizarContadorPendentesTotal() {
        try {
            const response = await fetch('/portal/api/buscar-protocolos-pendentes');
            const data = await response.json();

            if (data.success) {
                const contador = document.getElementById('contador-pendentes-total');
                if (contador) {
                    contador.textContent = data.total;
                    contador.className = data.total > 0 ? 'badge bg-dark ms-1' : 'badge bg-secondary ms-1';
                }
            }
        } catch (error) {
            console.error('Erro ao buscar total de pendentes:', error);
        }
    }

    /**
     * Verificar TODOS os protocolos pendentes automaticamente
     */
    async verificarTodosProtocolosPendentes() {
        try {
            // Primeiro buscar para mostrar quantos serão verificados
            const buscaResponse = await fetch('/portal/api/buscar-protocolos-pendentes');
            const buscaData = await buscaResponse.json();

            if (!buscaData.success || buscaData.total === 0) {
                Swal.fire({
                    icon: 'info',
                    title: 'Nenhum protocolo pendente',
                    text: 'Todos os protocolos já estão confirmados ou não há protocolos válidos.',
                    confirmButtonText: 'OK'
                });
                return;
            }

            // Confirmar ação
            const result = await Swal.fire({
                icon: 'question',
                title: 'Verificar Todos os Protocolos Pendentes',
                html: `
                    <p>Foram encontrados <strong>${buscaData.total}</strong> protocolos pendentes de confirmação.</p>
                    <p class="text-muted small">Esta operação verificará TODOS os protocolos no portal Atacadão.</p>
                    <p class="text-warning small"><i class="fas fa-exclamation-triangle"></i> Isso pode levar vários minutos.</p>
                `,
                showCancelButton: true,
                confirmButtonText: 'Verificar Todos',
                cancelButtonText: 'Cancelar',
                confirmButtonColor: window.Notifications?.colors?.neutral || '#6c757d'
            });

            if (!result.isConfirmed) return;

            // Mostrar loading
            Swal.fire({
                title: 'Processando...',
                html: `
                    <p>Enviando ${buscaData.total} protocolos para verificação...</p>
                    <div class="progress mt-3">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
                    </div>
                `,
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // Enviar para verificação
            const response = await fetch('/portal/api/verificar-todos-protocolos-pendentes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    portal: 'atacadao'
                })
            });

            const data = await response.json();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Verificação iniciada!',
                    html: `
                        <p>${data.total_enfileirados} protocolos foram enviados para verificação.</p>
                        <p class="text-muted small">Aguarde o processamento...</p>
                    `,
                    timer: 3000,
                    timerProgressBar: true
                });

                // Iniciar polling detalhado para esta task
                if (data.task_id) {
                    this.iniciarPollingVerificacaoDetalhado(data.task_id);
                }
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: data.message || 'Erro ao enviar protocolos para verificação',
                    confirmButtonText: 'OK'
                });
            }
        } catch (error) {
            console.error('Erro ao verificar todos protocolos pendentes:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao comunicar com o servidor',
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * Polling detalhado para verificação de todos protocolos
     */
    iniciarPollingVerificacaoDetalhado(taskId) {
        let tentativas = 0;
        const maxTentativas = 180; // 15 minutos (5 segundos * 180)

        const interval = setInterval(async () => {
            tentativas++;

            try {
                const response = await fetch(`/portal/api/status-verificacao-detalhado/${taskId}`);
                const data = await response.json();

                // Atualizar progresso no Swal se ainda estiver aberto
                if (Swal.isVisible() && data.status === 'processing') {
                    const percentual = Math.round((data.processados / data.total) * 100);
                    Swal.update({
                        html: `
                            <p>Processando protocolos...</p>
                            <p><strong>${data.processados}</strong> de <strong>${data.total}</strong> verificados</p>
                            <div class="progress mt-3">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     style="width: ${percentual}%">${percentual}%</div>
                            </div>
                        `
                    });
                }

                if (data.status === 'completed' || tentativas >= maxTentativas) {
                    clearInterval(interval);

                    // Atualizar contadores
                    this.atualizarContadorProtocolos();
                    this.atualizarContadorPendentesTotal();

                    // Se completou, mostrar resultado detalhado
                    if (data.status === 'completed') {
                        if (DEBUG) console.log('✅ Verificação de todos protocolos concluída');

                        // Preparar HTML com lista de alterações
                        let alteracoesHtml = '';
                        if (data.alteracoes && data.alteracoes.length > 0) {
                            alteracoesHtml = `
                                <div class="mt-3">
                                    <h6>Alterações detectadas:</h6>
                                    <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Protocolo</th>
                                                    <th>Cliente</th>
                                                    <th>Mudança</th>
                                                    <th>Data Anterior</th>
                                                    <th>Data Nova</th>
                                                    <th>Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>`;

                            data.alteracoes.forEach(alt => {
                                const statusIcon = alt.confirmado ?
                                    '<span class="badge bg-success">Confirmado</span>' :
                                    '<span class="badge bg-warning">Pendente</span>';

                                alteracoesHtml += `
                                    <tr>
                                        <td>${alt.protocolo}</td>
                                        <td>${alt.cliente || '-'}</td>
                                        <td>${alt.tipo_mudanca || 'Atualização'}</td>
                                        <td>${alt.data_anterior || '-'}</td>
                                        <td>${alt.data_nova || '-'}</td>
                                        <td>${statusIcon}</td>
                                    </tr>`;
                            });

                            alteracoesHtml += `
                                            </tbody>
                                        </table>
                                    </div>
                                </div>`;
                        }

                        // Mostrar resultado final
                        Swal.fire({
                            icon: data.atualizados > 0 ? 'success' : 'info',
                            title: 'Verificação Concluída!',
                            html: `
                                <div class="text-start">
                                    <p class="text-center">
                                        <strong>${data.processados}</strong> protocolos verificados<br>
                                        <strong>${data.atualizados}</strong> protocolos atualizados
                                    </p>
                                    ${alteracoesHtml}
                                    ${data.atualizados > 0 ? '<p class="text-center mt-3">A página será recarregada para mostrar as alterações.</p>' : ''}
                                </div>
                            `,
                            confirmButtonText: data.atualizados > 0 ? 'Recarregar Página' : 'OK',
                            width: data.alteracoes && data.alteracoes.length > 0 ? '800px' : '500px',
                            didClose: () => {
                                if (data.atualizados > 0) {
                                    location.reload();
                                }
                            }
                        });
                    }
                }
            } catch (error) {
                console.error('Erro no polling detalhado:', error);
                clearInterval(interval);
            }
        }, 5000); // Verificar a cada 5 segundos
    }

    /**
     * 🆕 SISTEMA DE PRIORIDADES PARA CARREGAMENTO DE ESTOQUE
     */
    filaEstoque = [];
    processandoEstoque = false;
    estoqueTimeoutId = null;
    pausadoPorBotao = false;

    carregarEstoqueComPrioridade(numPedido, itens, prioridade = 'normal') {
        // Se está pausado por botão, adicionar à fila mas não processar
        if (this.pausadoPorBotao) {
            const item = { numPedido, itens, prioridade };
            if (prioridade === 'alta') {
                this.filaEstoque.unshift(item);
            } else {
                this.filaEstoque.push(item);
            }
            return;
        }

        // Cancelar processamento atual se for de prioridade menor
        if (this.processandoEstoque) {
            clearTimeout(this.estoqueTimeoutId);
            this.processandoEstoque = false;
        }

        // Adicionar à fila com prioridade
        const item = { numPedido, itens, prioridade };

        if (prioridade === 'alta') {
            // Alta prioridade vai para o início da fila
            this.filaEstoque.unshift(item);
        } else {
            // Normal vai para o final
            this.filaEstoque.push(item);
        }

        // Processar fila
        this.processarFilaEstoque();
    }

    async processarFilaEstoque() {
        // Se está pausado, não processar
        if (this.pausadoPorBotao) {
            return;
        }

        if (this.processandoEstoque || this.filaEstoque.length === 0) {
            // Se não há mais itens, verificar se RupturaEstoque precisa continuar
            if (this.filaEstoque.length === 0 && window.rupturaManager && !window.rupturaManager.pausado) {
                // Retomar análise de ruptura se estava pausada
                setTimeout(() => {
                    if (window.rupturaManager && window.rupturaManager.filaAnalises.length > 0) {
                        window.rupturaManager.processarFilaAnalises();
                    }
                }, 100);
            }
            return;
        }

        this.processandoEstoque = true;
        const { numPedido, itens } = this.filaEstoque.shift();

        // Processar imediatamente se não houver pausa, senão aguardar
        const delay = this.pausadoPorBotao ? 2000 : 100;

        this.estoqueTimeoutId = setTimeout(async () => {
            // Pausar RupturaEstoque enquanto carrega estoque
            if (window.rupturaManager) {
                window.rupturaManager.pausarAnalises();
            }

            await this.carregarEstoqueAssincrono(numPedido, itens);
            this.processandoEstoque = false;

            // Processar próximo da fila
            if (this.filaEstoque.length > 0) {
                this.processarFilaEstoque();
            } else {
                // Retomar RupturaEstoque quando terminar
                if (window.rupturaManager && !this.pausadoPorBotao) {
                    setTimeout(() => {
                        window.rupturaManager.retomarAnalises();
                    }, 100);
                }
            }
        }, delay);
    }

    // Interceptar cliques em botoes de acao para pausar carregamento
    setupInterceptadorBotoes() {
        document.addEventListener('click', (e) => {
            const target = e.target;
            const isButton = target.closest('button, .btn, [onclick]');

            // FIX E5: Filtrar apenas botoes dentro da tabela de pedidos
            // Antes: qualquer link/botao (incluindo menu, tooltips) pausava por 2s
            if (isButton && isButton.closest('#tabela-carteira, .separacoes-compactas-container, .workspace-container')) {

                // Marcar como pausado
                this.pausadoPorBotao = true;

                // Pausar carregamento de estoque em andamento
                if (this.processandoEstoque) {
                    clearTimeout(this.estoqueTimeoutId);
                    this.processandoEstoque = false;
                }

                // Pausar RupturaEstoque também
                if (window.rupturaManager) {
                    window.rupturaManager.pausarAnalises();
                }

                // Reagendar para 2 segundos depois
                setTimeout(() => {
                    if (DEBUG) console.log('▶️ Retomando carregamentos');
                    this.pausadoPorBotao = false;

                    // Processar fila de estoque com prioridade alta primeiro
                    if (this.filaEstoque.length > 0) {
                        // Reordenar fila por prioridade
                        this.filaEstoque.sort((a, b) => {
                            if (a.prioridade === 'alta' && b.prioridade !== 'alta') return -1;
                            if (a.prioridade !== 'alta' && b.prioridade === 'alta') return 1;
                            return 0;
                        });
                        this.processarFilaEstoque();
                    } else if (window.rupturaManager) {
                        // Se não há estoque para carregar, retomar ruptura
                        window.rupturaManager.retomarAnalises();
                    }
                }, 2000);
            }
        }, true); // Capture phase para interceptar antes
    }

    // Método para atualizar dados de uma separação compacta sem re-renderizar
    atualizarSeparacaoCompacta(loteId, dadosAtualizados) {
        if (DEBUG) console.log(`🔄 Atualizando separação compacta ${loteId}`);

        // Atualizar dados na memória
        if (this.separacoesPorPedido) {
            for (const [pedido, separacoes] of this.separacoesPorPedido) {
                const sep = separacoes.find(s => s.separacao_lote_id === loteId);
                if (sep) {
                    // Atualizar campos
                    if (dadosAtualizados.expedicao !== undefined) sep.expedicao = dadosAtualizados.expedicao;
                    if (dadosAtualizados.agendamento !== undefined) sep.agendamento = dadosAtualizados.agendamento;
                    if (dadosAtualizados.protocolo !== undefined) sep.protocolo = dadosAtualizados.protocolo;
                    if (dadosAtualizados.agendamento_confirmado !== undefined) sep.agendamento_confirmado = dadosAtualizados.agendamento_confirmado;
                    if (DEBUG) console.log(`✅ Dados atualizados na memória para ${loteId}`);
                    break;
                }
            }
        }

        // Atualizar também em dadosAgrupados se existir
        if (this.dadosAgrupados && this.dadosAgrupados.grupos) {
            for (const grupo of this.dadosAgrupados.grupos) {
                if (grupo.separacoes_compactas) {
                    const sepCompacta = grupo.separacoes_compactas.find(s => s.lote_id === loteId);
                    if (sepCompacta) {
                        // Atualizar campos
                        if (dadosAtualizados.expedicao !== undefined) sepCompacta.expedicao = dadosAtualizados.expedicao;
                        if (dadosAtualizados.agendamento !== undefined) sepCompacta.agendamento = dadosAtualizados.agendamento;
                        if (dadosAtualizados.protocolo !== undefined) sepCompacta.protocolo = dadosAtualizados.protocolo;
                        if (dadosAtualizados.agendamento_confirmado !== undefined) sepCompacta.agendamento_confirmado = dadosAtualizados.agendamento_confirmado;
                        if (DEBUG) console.log(`✅ Dados atualizados em dadosAgrupados para ${loteId}`);
                        break;
                    }
                }
            }
        }

        // Chamar método do workspace para atualizar a view
        if (window.workspace && window.workspace.atualizarViewCompactaDireto) {
            window.workspace.atualizarViewCompactaDireto(
                loteId,
                dadosAtualizados.expedicao,
                dadosAtualizados.agendamento,
                dadosAtualizados.protocolo,
                dadosAtualizados.agendamento_confirmado
            );
        }
    }

    // ⭐ MÉTODOS PARA FUNCIONALIDADE DE IMPORTANTE

    // Toggle do estado importante de um pedido
    async toggleImportante(numPedido) {
        try {
            // Buscar botão da estrela
            const btnEstrela = document.querySelector(`.btn-importante[data-pedido="${numPedido}"]`);
            if (!btnEstrela) {
                console.error(`Botão de importante não encontrado para pedido ${numPedido}`);
                return;
            }

            // Estado atual
            const estadoAtual = btnEstrela.dataset.importante === 'true';

            // Fazer requisição para API
            // FIX I5: Adicionar X-CSRFToken (antes ausente, poderia falhar com 403)
            const response = await fetch('/carteira/api/toggle-importante', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || ''
                },
                body: JSON.stringify({
                    num_pedido: numPedido
                })
            });

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Erro ao alterar estado importante');
            }

            // Atualizar estado do botão
            btnEstrela.dataset.importante = data.importante ? 'true' : 'false';

            // Atualizar classe da estrela
            const estrela = btnEstrela.querySelector('i.fa-star');
            if (estrela) {
                if (data.importante) {
                    estrela.classList.remove('text-muted');
                    estrela.classList.add('text-warning');
                    btnEstrela.title = 'Remover marcação de importante';
                } else {
                    estrela.classList.remove('text-warning');
                    estrela.classList.add('text-muted');
                    btnEstrela.title = 'Marcar como importante';
                }
            }

            // Atualizar data-attribute da linha do pedido
            const linha = document.querySelector(`.pedido-row[data-pedido="${numPedido}"]`);
            if (linha) {
                linha.dataset.importante = data.importante ? 'true' : 'false';
            }

            // Atualizar contadores
            this.atualizarContadoresImportante();

            // Notificar sucesso
            if (window.Notifications && window.Notifications.success) {
                window.Notifications.success(data.message);
            }

            if (DEBUG) console.log(`✅ Importante atualizado: ${numPedido} -> ${data.importante}`);

        } catch (error) {
            console.error('Erro ao toggle importante:', error);
            if (window.Notifications && window.Notifications.error) {
                window.Notifications.error('Erro ao alterar estado importante');
            } else {
                alert('Erro ao alterar estado importante');
            }
        }
    }

    // Atualiza os contadores de pedidos importantes
    atualizarContadoresImportante() {
        const linhas = document.querySelectorAll('.pedido-row');
        let totalImportantes = 0;
        let importantesSemSeparacao = 0;

        linhas.forEach(linha => {
            const importante = linha.dataset.importante === 'true';
            const qtdSeparacoes = parseInt(linha.querySelector('.contador-separacoes')?.textContent || '0');

            if (importante) {
                totalImportantes++;
                if (qtdSeparacoes === 0) {
                    importantesSemSeparacao++;
                }
            }
        });

        // Atualizar contadores no badge
        const contadorTotal = document.getElementById('contador-importantes-total');
        const contadorSemSep = document.getElementById('contador-importantes-sem-sep');

        if (contadorTotal) contadorTotal.textContent = totalImportantes;
        if (contadorSemSep) contadorSemSep.textContent = importantesSemSeparacao;

        if (DEBUG) console.log(`📊 Contadores importantes: ${importantesSemSeparacao} / ${totalImportantes}`);
    }

    // Toggle do filtro importante (exclusivo mútuo) - CSS controla estilos
    toggleImportanteFiltro(badge) {
        // Se já está ativo, desativar
        if (this.filtrosAtivos.importante) {
            this.filtrosAtivos.importante = false;
            badge.classList.remove('ativo');
            document.getElementById('limpar-importante').style.display = 'none';
        } else {
            // Ativar
            this.filtrosAtivos.importante = true;
            badge.classList.add('ativo');
            document.getElementById('limpar-importante').style.display = 'inline-block';
        }

        this.aplicarFiltros();
    }

    // Limpa o filtro de importante - CSS controla estilos
    limparFiltroImportante() {
        const badge = document.querySelector('[data-tipo="importante"]');
        if (badge) {
            badge.classList.remove('ativo');
        }
        this.filtrosAtivos.importante = false;
        document.getElementById('limpar-importante').style.display = 'none';
        this.aplicarFiltros();
    }
}

function avaliarEstoques(numPedido) {
    if (DEBUG) console.log(`📊 Avaliar estoques do pedido ${numPedido}`);

    // Abrir workspace para visualizar dados de estoque
    const btnExpandir = document.querySelector(`[data-pedido="${numPedido}"].btn-expandir`);
    if (btnExpandir && window.workspace) {
        // Se já está expandido, focar na tabela de produtos
        const detalhesRow = document.getElementById(`detalhes-${numPedido}`);
        if (detalhesRow && detalhesRow.classList.contains('show')) {
            // Já expandido, focar na tabela de produtos
            const tabelaProdutos = detalhesRow.querySelector('.workspace-produtos-table');
            if (tabelaProdutos) {
                tabelaProdutos.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                detalhesRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } else {
            // Expandir primeiro
            btnExpandir.click();

            // Aguardar expansão e focar na tabela
            setTimeout(() => {
                const detalhesExpandido = document.getElementById(`detalhes-${numPedido}`);
                if (detalhesExpandido) {
                    const tabelaProdutos = detalhesExpandido.querySelector('.workspace-produtos-table');
                    if (tabelaProdutos) {
                        tabelaProdutos.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } else {
                        detalhesExpandido.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }, 800);
        }
    }
}

// Função removida - modal de agendamento não é mais necessário

function abrirModalEndereco(numPedido) {
    if (DEBUG) console.log(`📍 Abrir modal de endereço do pedido ${numPedido}`);
    if (window.modalEndereco) {
        window.modalEndereco.abrirModalEndereco(numPedido);
    } else {
        console.error('❌ Modal de endereço não inicializado');
    }
}

// 🎯 INICIALIZAÇÃO GLOBAL
window.CarteiraAgrupada = CarteiraAgrupada;

