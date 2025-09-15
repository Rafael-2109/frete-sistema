/**
 * 🎯 CARTEIRA AGRUPADA - CONTROLADOR PRINCIPAL
 * Gerencia funcionalidades da página de carteira agrupada
 */

class CarteiraAgrupada {
    constructor() {
        this.dropdownSeparacoes = null;
        this.filtrosAtivos = {
            rotas: new Set(),
            incoterms: new Set(),
            subrotas: new Set(),
            agendamento: null,  // null, 'com', 'sem', 'sep-aguardando', 'sep-confirmado'
            cliente: null,  // null, 'atacadao', 'sendas', 'outros'
            atendimento: null  // null, 'programar', 'revisar-data'
        };
        this.maxFiltrosAtivos = 3; // Máximo de badges selecionados simultaneamente
        
        // 🆕 Controle de requisições assíncronas
        this.abortControllers = new Map(); // pedidoId -> AbortController
        this.pedidosVisiveis = new Set(); // Conjunto de pedidos atualmente visíveis
        
        this.init();
    }

    init() {
        console.log('🚀 Inicializando CarteiraAgrupada...');
        this.setupEventListeners();
        this.initDropdownSeparacoes();
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
        
        // Carregar separações para todos os pedidos visíveis
        console.log(`📦 Carregando separações para ${this.pedidosVisiveis.size} pedidos iniciais...`);
        this.carregarSeparacoesCompactasVisiveis();
        
        // Aguardar um pouco para as separações carregarem antes de atualizar contadores
        setTimeout(() => {
            // Atualizar contadores
            this.atualizarContadorProtocolos();
            this.atualizarContadorPendentesTotal();
        }, 2000); // 2 segundos para dar tempo de carregar
        
        this.setupInterceptadorBotoes(); // 🆕 Interceptar cliques em botões
        console.log('✅ Carteira Agrupada inicializada');
        
        // Debug: verificar se os badges foram encontrados
        const totalBadges = document.querySelectorAll('.bg-filtro').length;
        if (totalBadges === 0) {
            console.error('❌ ERRO: Nenhum badge .bg-filtro encontrado no DOM!');
        } else {
            console.log(`✅ ${totalBadges} badges de filtro encontrados e configurados`);
        }
        
        // 🆕 Carregar separações compactas para todos os pedidos
        this.carregarTodasSeparacoesCompactas();
        
        // Atualizar contador de protocolos
        this.atualizarContadorProtocolos();
    }

    initWorkspace() {
        // Garantir que o workspace seja criado globalmente
        if (!window.workspace && window.WorkspaceMontagem) {
            window.workspace = new window.WorkspaceMontagem();
            console.log('✅ Workspace global criado');
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
    }

    setupFiltros() {
        const filtroBusca = document.getElementById('filtro-busca');
        const filtroStatus = document.getElementById('filtro-status');
        const filtroEquipe = document.getElementById('filtro-equipe');

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
    }

    initBadgesFiltros() {
        // Event listeners para badges - CORREÇÃO: usar .bg-filtro em vez de .badge-filtro
        document.querySelectorAll('.bg-filtro').forEach(badge => {
            // Adicionar cursor pointer para indicar que é clicável
            badge.style.cursor = 'pointer';
            
            badge.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔍 Badge clicado:', badge.dataset.tipo, badge.dataset.valor);
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

        console.log('✅ Badges de filtros inicializados. Total de badges:', document.querySelectorAll('.bg-filtro').length);
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

        // Toggle do badge com classe 'ativo' e estilos
        badge.classList.toggle('ativo');
        
        // Aplicar ou remover estilos visuais
        if (badge.classList.contains('ativo')) {
            // Estado ativo (preenchido)
            if (tipo === 'rota') {
                badge.style.backgroundColor = '#0d6efd';
                badge.style.color = 'white';
                badge.style.borderColor = '#0d6efd';
                this.filtrosAtivos.rotas.add(valor);
                // Se ativou SP, mostrar subrotas
                if (valor === 'SP') {
                    this.mostrarSubrotasSP();
                }
            } else if (tipo === 'incoterm') {
                if (valor === 'FOB') {
                    badge.style.backgroundColor = '#ffc107';
                    badge.style.color = '#000';
                    badge.style.borderColor = '#ffc107';
                } else if (valor === 'RED') {
                    badge.style.backgroundColor = '#dc3545';
                    badge.style.color = 'white';
                    badge.style.borderColor = '#dc3545';
                }
                this.filtrosAtivos.incoterms.add(valor);
            } else if (tipo === 'subrota') {
                badge.style.backgroundColor = '#6c757d';
                badge.style.color = 'white';
                badge.style.borderColor = '#6c757d';
                this.filtrosAtivos.subrotas.add(valor);
            }
        } else {
            // Estado inativo (outline)
            badge.style.backgroundColor = 'transparent';
            if (tipo === 'rota') {
                badge.style.color = '#0d6efd';
                badge.style.borderColor = '#0d6efd';
                this.filtrosAtivos.rotas.delete(valor);
                // Se desativou SP, esconder subrotas
                if (valor === 'SP') {
                    this.esconderSubrotasSP();
                }
            } else if (tipo === 'incoterm') {
                if (valor === 'FOB') {
                    badge.style.color = '#ffc107';
                    badge.style.borderColor = '#ffc107';
                } else if (valor === 'RED') {
                    badge.style.color = '#dc3545';
                    badge.style.borderColor = '#dc3545';
                }
                this.filtrosAtivos.incoterms.delete(valor);
            } else if (tipo === 'subrota') {
                badge.style.color = '#6c757d';
                badge.style.borderColor = '#6c757d';
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
        // Remover ativo de todos os badges de agendamento
        document.querySelectorAll('.badge-agendamento').forEach(b => {
            b.classList.remove('ativo');
            // Restaurar estilo outline (não clicado) baseado no valor do badge
            const valorBadge = b.dataset.valor;
            if (valorBadge === 'sem') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#dc3545';
                b.style.borderColor = '#dc3545';
            } else if (valorBadge === 'com') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#198754';
                b.style.borderColor = '#198754';
            } else if (valorBadge === 'sep-aguardando') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#fd7e14';
                b.style.borderColor = '#fd7e14';
            } else if (valorBadge === 'sep-confirmado') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#0dcaf0';
                b.style.borderColor = '#0dcaf0';
            }
        });
        
        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.agendamento === valor) {
            this.filtrosAtivos.agendamento = null;
            document.getElementById('limpar-agendamento').style.display = 'none';
        } else {
            // Ativar o novo com estilo preenchido
            badge.classList.add('ativo');
            if (valor === 'sem') {
                badge.style.backgroundColor = '#dc3545';
                badge.style.color = 'white';
                badge.style.borderColor = '#dc3545';
            } else if (valor === 'com') {
                badge.style.backgroundColor = '#198754';
                badge.style.color = 'white';
                badge.style.borderColor = '#198754';
            } else if (valor === 'sep-aguardando') {
                badge.style.backgroundColor = '#fd7e14';
                badge.style.color = 'white';
                badge.style.borderColor = '#fd7e14';
            } else if (valor === 'sep-confirmado') {
                badge.style.backgroundColor = '#0dcaf0';
                badge.style.color = 'white';
                badge.style.borderColor = '#0dcaf0';
            }
            this.filtrosAtivos.agendamento = valor;
            document.getElementById('limpar-agendamento').style.display = 'inline-block';
        }
        
        this.aplicarFiltros();
    }

    limparFiltrosRotas() {
        // Limpar badges de rotas e incoterms
        document.querySelectorAll('.badge-rota, .badge-incoterm').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            
            // Restaurar cores outline
            if (badge.classList.contains('badge-rota')) {
                badge.style.color = '#0d6efd';
                badge.style.borderColor = '#0d6efd';
            } else if (badge.dataset.valor === 'FOB') {
                badge.style.color = '#ffc107';
                badge.style.borderColor = '#ffc107';
            } else if (badge.dataset.valor === 'RED') {
                badge.style.color = '#dc3545';
                badge.style.borderColor = '#dc3545';
            }
        });

        this.filtrosAtivos.rotas.clear();
        this.filtrosAtivos.incoterms.clear();
        this.esconderSubrotasSP();

        this.atualizarBotoesLimpar();
        this.aplicarFiltros();
    }

    limparFiltrosSubrotas() {
        // Limpar badges de subrotas
        document.querySelectorAll('.badge-subrota').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            badge.style.color = '#6c757d';
            badge.style.borderColor = '#6c757d';
        });

        this.filtrosAtivos.subrotas.clear();

        this.atualizarBotoesLimpar();
        this.aplicarFiltros();
    }
    
    limparFiltrosAgendamento() {
        document.querySelectorAll('.badge-agendamento').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            
            // Restaurar cores outline baseado no valor do badge
            const valorBadge = badge.dataset.valor;
            if (valorBadge === 'sem') {
                badge.style.color = '#dc3545';
                badge.style.borderColor = '#dc3545';
            } else if (valorBadge === 'com') {
                badge.style.color = '#198754';
                badge.style.borderColor = '#198754';
            } else if (valorBadge === 'sep-aguardando') {
                badge.style.color = '#fd7e14';
                badge.style.borderColor = '#fd7e14';
            } else if (valorBadge === 'sep-confirmado') {
                badge.style.color = '#0dcaf0';
                badge.style.borderColor = '#0dcaf0';
            }
        });
        this.filtrosAtivos.agendamento = null;
        this.aplicarFiltros();
        document.getElementById('limpar-agendamento').style.display = 'none';
    }
    
    toggleCliente(badge, valor) {
        // Remover ativo de todos os badges de cliente
        document.querySelectorAll('.badge-cliente').forEach(b => {
            b.classList.remove('ativo');
            // Restaurar estilo outline (não clicado) baseado no valor do badge
            const valorBadge = b.dataset.valor;
            if (valorBadge === 'atacadao') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#0056b3';
                b.style.borderColor = '#0056b3';
            } else if (valorBadge === 'sendas') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#dc3545';
                b.style.borderColor = '#dc3545';
            } else if (valorBadge === 'outros') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#6c757d';
                b.style.borderColor = '#6c757d';
            }
        });
        
        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.cliente === valor) {
            this.filtrosAtivos.cliente = null;
            document.getElementById('limpar-cliente').style.display = 'none';
        } else {
            // Ativar o novo com estilo preenchido
            badge.classList.add('ativo');
            if (valor === 'atacadao') {
                badge.style.backgroundColor = '#0056b3';
                badge.style.color = 'white';
                badge.style.borderColor = '#0056b3';
            } else if (valor === 'sendas') {
                badge.style.backgroundColor = '#dc3545';
                badge.style.color = 'white';
                badge.style.borderColor = '#dc3545';
            } else if (valor === 'outros') {
                badge.style.backgroundColor = '#6c757d';
                badge.style.color = 'white';
                badge.style.borderColor = '#6c757d';
            }
            this.filtrosAtivos.cliente = valor;
            document.getElementById('limpar-cliente').style.display = 'inline-block';
        }
        
        this.aplicarFiltros();
    }

    toggleAtendimento(badge, valor) {
        // Remover ativo de todos os badges de atendimento
        document.querySelectorAll('.badge-atendimento').forEach(b => {
            b.classList.remove('ativo');
            // Restaurar estilo outline (não clicado) baseado no valor do badge
            const valorBadge = b.dataset.valor;
            if (valorBadge === 'programar') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#6f42c1';
                b.style.borderColor = '#6f42c1';
            } else if (valorBadge === 'revisar-data') {
                b.style.backgroundColor = 'transparent';
                b.style.color = '#e83e8c';
                b.style.borderColor = '#e83e8c';
            }
        });

        // Se clicou no mesmo que já estava ativo, desativar
        if (this.filtrosAtivos.atendimento === valor) {
            this.filtrosAtivos.atendimento = null;
            document.getElementById('limpar-atendimento').style.display = 'none';
        } else {
            // Ativar o novo com estilo preenchido
            badge.classList.add('ativo');
            if (valor === 'programar') {
                badge.style.backgroundColor = '#6f42c1';
                badge.style.color = 'white';
                badge.style.borderColor = '#6f42c1';
            } else if (valor === 'revisar-data') {
                badge.style.backgroundColor = '#e83e8c';
                badge.style.color = 'white';
                badge.style.borderColor = '#e83e8c';
            }
            this.filtrosAtivos.atendimento = valor;
            document.getElementById('limpar-atendimento').style.display = 'inline-block';
        }

        this.aplicarFiltros();
    }

    limparFiltrosCliente() {
        document.querySelectorAll('.badge-cliente').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            const valorBadge = badge.dataset.valor;
            if (valorBadge === 'atacadao') {
                badge.style.color = '#0056b3';
                badge.style.borderColor = '#0056b3';
            } else if (valorBadge === 'sendas') {
                badge.style.color = '#dc3545';
                badge.style.borderColor = '#dc3545';
            } else if (valorBadge === 'outros') {
                badge.style.color = '#6c757d';
                badge.style.borderColor = '#6c757d';
            }
        });
        this.filtrosAtivos.cliente = null;
        this.aplicarFiltros();
        document.getElementById('limpar-cliente').style.display = 'none';
    }

    limparFiltrosAtendimento() {
        document.querySelectorAll('.badge-atendimento').forEach(badge => {
            badge.classList.remove('ativo');
            badge.style.backgroundColor = 'transparent';
            const valorBadge = badge.dataset.valor;
            if (valorBadge === 'programar') {
                badge.style.color = '#6f42c1';
                badge.style.borderColor = '#6f42c1';
            } else if (valorBadge === 'revisar-data') {
                badge.style.color = '#e83e8c';
                badge.style.borderColor = '#e83e8c';
            }
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

    initDropdownSeparacoes() {
        if (window.DropdownSeparacoes) {
            this.dropdownSeparacoes = new window.DropdownSeparacoes();
        } else {
            console.warn('⚠️ DropdownSeparacoes não encontrado');
        }
    }

    // 🎯 FILTROS
    aplicarFiltros() {
        const termoBusca = document.getElementById('filtro-busca')?.value.toLowerCase() || '';
        const statusSelecionado = document.getElementById('filtro-status')?.value || '';
        const equipeSelecionada = document.getElementById('filtro-equipe')?.value || '';

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
                    // Pedidos com separação que têm protocolo mas não confirmados
                    matchAgendamento = (temProtocoloSeparacao || protocolo) && !agendamentoConfirmado;
                } else if (this.filtrosAtivos.agendamento === 'sep-confirmado') {
                    // Pedidos com separação que têm protocolo e confirmados
                    matchAgendamento = (temProtocoloSeparacao || protocolo) && agendamentoConfirmado;
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

            // Filtro de atendimento (Programar, Revisar Data)
            let matchAtendimento = true;
            if (this.filtrosAtivos.atendimento) {
                if (this.filtrosAtivos.atendimento === 'programar') {
                    // Pedidos com data_entrega_pedido sem agendamento
                    matchAtendimento = dataEntregaPedido && !agendamentoData;
                } else if (this.filtrosAtivos.atendimento === 'revisar-data') {
                    // Pedidos com agendamento posterior à data de entrega
                    matchAtendimento = dataEntregaPedido && agendamentoData && agendamentoData > dataEntregaPedido;
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

            const mostrar = matchBusca && matchStatus && matchEquipe && matchAgendamento && matchCliente && matchAtendimento && matchBadges && matchSubrotas;

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

        console.log(`🔍 Filtros aplicados: ${totalVisiveis} pedidos visíveis`);

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
        
        // Somar valores de todos os pedidos visíveis
        document.querySelectorAll('.pedido-row:not([style*="display: none"])').forEach(linha => {
            const valorElement = linha.querySelector('.valor-pedido');
            if (valorElement) {
                // Extrair valor do texto (remover R$, pontos e converter vírgula)
                const valorTexto = valorElement.textContent
                    .replace('R$', '')
                    .replace(/\./g, '')
                    .replace(',', '.')
                    .trim();
                
                const valor = parseFloat(valorTexto) || 0;
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
        console.log('📖 Todos os pedidos expandidos');
    }

    colapsarTodos() {
        document.querySelectorAll('.detalhes-row.show').forEach(detalhesRow => {
            const numPedido = detalhesRow.id.replace('detalhes-', '');
            const linha = document.querySelector(`[data-pedido="${numPedido}"]`);
            const icon = linha?.querySelector('.expand-icon');

            this.colapsarDetalhes(detalhesRow, icon);
        });
        console.log('📖 Todos os pedidos colapsados');
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
                console.log(`🚀 Abrindo workspace para pedido ${numPedido}`);
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
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.moeda) {
            return window.Formatters.moeda(valor);
        }
        
        // Fallback completo
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarQuantidade(qtd) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.quantidade) {
            return window.Formatters.quantidade(qtd);
        }
        
        // Fallback completo
        if (!qtd) return '0';
        return parseFloat(qtd).toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 3
        });
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
        console.log(`🚫 Cancelando ${this.abortControllers.size} requisições assíncronas...`);
        this.abortControllers.forEach((controller) => {
            controller.abort();
        });
        this.abortControllers.clear();
        
        // 🆕 Também cancelar requisições de estoque do workspace
        if (window.workspace && window.workspace.abortControllerEstoque) {
            window.workspace.abortControllerEstoque.abort();
            window.workspace.abortControllerEstoque = null;
            console.log(`✔️ Carregamento de estoque do workspace cancelado`);
        }
    }
    
    formatarData(data) {
        // Usar módulo centralizado se disponível
        if (window.Formatters && window.Formatters.data) {
            return window.Formatters.data(data);
        }
        
        // Fallback completo
        if (!data) return '-';
        
        // Se já está no formato dd/mm/yyyy, retornar como está
        if (typeof data === 'string' && data.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
            return data;
        }
        
        try {
            let d;
            
            // Se está no formato yyyy-mm-dd
            if (typeof data === 'string' && data.match(/^\d{4}-\d{2}-\d{2}$/)) {
                const [ano, mes, dia] = data.split('-');
                d = new Date(parseInt(ano), parseInt(mes) - 1, parseInt(dia));
            }
            // Se inclui tempo (formato ISO)
            else if (typeof data === 'string' && data.includes('T')) {
                d = new Date(data);
            }
            // Se é um objeto Date
            else if (data instanceof Date) {
                d = data;
            }
            // Tentar parsear como string de data
            else {
                d = new Date(data);
            }
            
            // Verificar se a data é válida
            if (isNaN(d.getTime())) {
                console.warn(`⚠️ Data inválida: ${data}`);
                return '-';
            }
            
            // Forçar formato dd/mm/yyyy
            const dia = String(d.getDate()).padStart(2, '0');
            const mes = String(d.getMonth() + 1).padStart(2, '0');
            const ano = d.getFullYear();
            return `${dia}/${mes}/${ano}`;
        } catch (error) {
            console.error('❌ Erro ao formatar data:', data, error);
            return '-';
        }
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
                console.log('🔍 DEBUG API Response (carregarSeparacoesEmLoteUnico):', data);
                
                if (data.success && data.pedidos) {
                    // Salvar no cache
                    Object.keys(data.pedidos).forEach(numPedido => {
                        const separacoes = data.pedidos[numPedido];
                        
                        // LOG DE DEBUG: Verificar estrutura de cada separação
                        console.log(`📦 DEBUG - Pedido ${numPedido} - Separações da API:`, separacoes);
                        if (separacoes && separacoes.length > 0) {
                            console.log(`📅 DEBUG - Primeira separação tem expedição? ${separacoes[0].expedicao}, agendamento? ${separacoes[0].agendamento}`);
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
                    
                    console.log(`✅ Carregado: ${Object.keys(data.pedidos).length} pedidos`);
                    
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
        console.log(`📊 Dados do cache para pedido ${numPedido}:`, separacoes);
        
        // Converter formato do cache para o formato esperado por renderizarSeparacoesCompactas
        const separacoesData = {
            success: true,
            separacoes: separacoes.map(sep => {
                // Log de debug para cada separação
                console.log(`📅 Mapeando separação - expedição: ${sep.expedicao}, agendamento: ${sep.agendamento}`);
                
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
                    embarque: sep.embarque
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
        console.log('📦 Carregando separações compactas para TODOS os pedidos...');
        
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
            console.log('✅ Todas as separações já estão em cache');
            return;
        }
        
        console.log(`📦 Carregando separações em LOTE para ${pedidosParaCarregar.length} pedidos...`);
        
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
                    console.log('🔍 DEBUG API Response (carregarSeparacoesEmLote):', data);
                    
                    if (data.success && data.pedidos) {
                        // Salvar no cache E renderizar
                        Object.keys(data.pedidos).forEach(numPedido => {
                            const separacoes = data.pedidos[numPedido];
                            
                            // LOG DE DEBUG: Verificar estrutura de cada separação
                            console.log(`📦 DEBUG - Pedido ${numPedido} - Separações da API:`, separacoes);
                            if (separacoes && separacoes.length > 0) {
                                console.log(`📅 DEBUG - Primeira separação tem expedição? ${separacoes[0].expedicao}, agendamento? ${separacoes[0].agendamento}`);
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
                        
                        console.log(`✅ Lote ${Math.floor(i/tamanhoLote) + 1}: ${Object.keys(data.pedidos).length} pedidos carregados`);
                        console.log(`   📊 Total separações: ${data.totais.total_separacoes}`);
                        console.log(`   🔖 Protocolos pendentes: ${data.totais.protocolos_unicos_pendentes}`);
                    }
                } else {
                    console.error(`❌ Erro ao carregar lote ${Math.floor(i/tamanhoLote) + 1}`);
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
                    embarque: sep.embarque,
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
            <div class="separacoes-compactas-container bg-white p-2 border-bottom">
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0">
                        <thead style="background-color: #1a2332 !important; border-bottom: 2px solid #2a3442;">
                            <tr>
                                <th width="100" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Tipo</th>
                                <th width="80" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Status</th>
                                <th class="text-end" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Valor</th>
                                <th class="text-end" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Peso</th>
                                <th class="text-end" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Pallet</th>
                                <th class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Expedição</th>
                                <th class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Agendamento</th>
                                <th style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Protocolo</th>
                                <th class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Confirmação</th>
                                <th style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Embarque</th>
                                <th width="220" class="text-center" style="background-color: #1a2332 !important; color: #a8c8e8 !important; border: none !important;">Ações</th>
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
        const tipoClass = item.isSeparacao ? 'text-primary' : 'text-warning';
        const statusBadge = item.status ? 
            (item.status === 'PREVISAO' ? '<span class="badge bg-secondary">PREVISAO</span>' :
             item.status === 'COTADO' ? '<span class="badge bg-warning text-dark">COTADO</span>' : 
             item.status === 'ABERTO' ? '<span class="badge bg-secondary">ABERTO</span>' : '') : '';
        
        const confirmacaoBadge = item.agendamento ? 
            (item.agendamento_confirmado ? 
                '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Confirmado</span>' :
                '<span class="badge bg-warning text-dark"><i class="fas fa-hourglass-half"></i> Aguardando</span>') : '-';
        
        const embarqueInfo = item.embarque ? 
            `<span title="${item.embarque.transportadora || 'Sem transportadora'}" style="cursor: help;">
                #${item.embarque.numero || '-'} | ${item.embarque.data_prevista_embarque ? this.formatarData(item.embarque.data_prevista_embarque) : '-'}
             </span>` : '-';
        
        return `
            <tr>
                <td><strong class="${tipoClass}">${item.tipo}</strong></td>
                <td>${statusBadge}</td>
                <td class="text-end text-success">${this.formatarMoeda(item.valor)}</td>
                <td class="text-end">${this.formatarPeso(item.peso)}</td>
                <td class="text-end">${this.formatarPallet(item.pallet)}</td>
                <td class="text-center">${item.expedicao ? this.formatarData(item.expedicao) : '-'}</td>
                <td class="text-center">${item.agendamento ? this.formatarData(item.agendamento) : '-'}</td>
                <td><small>${item.protocolo || '-'}</small></td>
                <td class="text-center">${confirmacaoBadge}</td>
                <td><small>${embarqueInfo}</small></td>
                <td class="text-center">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary btn-sm" 
                                onclick="carteiraAgrupada.abrirModalDatas('${item.loteId}', ${item.isSeparacao}, '${item.expedicao || ''}', '${item.agendamento || ''}', '${item.protocolo || ''}', ${item.agendamento_confirmado || false})"
                                title="Editar datas">
                            <i class="fas fa-calendar-alt"></i> Datas
                        </button>
                        ${item.status === 'PREVISAO' ? `
                            <button class="btn btn-outline-success btn-sm" 
                                    onclick="carteiraAgrupada.alterarStatusSeparacao('${item.loteId}', 'ABERTO')"
                                    title="Confirmar separação">
                                <i class="fas fa-check"></i> Confirmar
                            </button>
                        ` : item.status === 'ABERTO' ? `
                            <button class="btn btn-outline-warning btn-sm" 
                                    onclick="carteiraAgrupada.alterarStatusSeparacao('${item.loteId}', 'PREVISAO')"
                                    title="Voltar para previsão">
                                <i class="fas fa-undo"></i> Previsão
                            </button>
                        ` : ''}
                        <button class="btn btn-outline-info btn-sm" 
                                onclick="carteiraAgrupada.agendarNoPortal('${item.loteId}', '${item.agendamento || ''}')"
                                title="Agendar no portal">
                            <i class="fas fa-calendar-plus"></i> Agendar
                        </button>
                        ${item.protocolo ? `
                            <button class="btn btn-outline-warning btn-sm" 
                                    onclick="carteiraAgrupada.verificarAgendamento('${item.loteId}', '${item.protocolo}')"
                                    title="Verificar agendamento no portal">
                                <i class="fas fa-search"></i> Ver.Agenda
                            </button>
                        ` : ''}
                        <button class="btn btn-outline-danger btn-sm" 
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
            console.log(`📊 Carregando estoque assíncrono para pedido ${numPedido}`);
            
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
        console.log(`📅 Abrindo modal de datas para ${loteId} (Separação: ${isSeparacao})`);
        console.log(`   Dados: expedição=${expedicao}, agendamento=${agendamento}, protocolo=${protocolo}, confirmado=${agendamentoConfirmado}`);
        
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
        console.log(`🔄 Alterando status da separação ${loteId} para ${novoStatus}`);
        
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
                    console.log('🤖 Agendando automaticamente no portal após confirmação...');
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
                            console.log('🤖 Agendando automaticamente no portal após confirmação...');
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
        console.log(`🗑️ Excluindo separação ${loteId}`);
        
        // Usar separacaoManager se disponível
        if (window.separacaoManager && typeof window.separacaoManager.excluirSeparacao === 'function') {
            // Buscar o número do pedido pela linha da tabela
            const btn = event.target.closest('button');
            const tr = btn.closest('tr');
            const table = tr.closest('table');
            const container = table.closest('.separacoes-compactas-container');
            const pedidoRow = container.closest('.pedido-detalhes')?.previousElementSibling;
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
            
            console.log(`📊 Protocolos únicos encontrados para verificar: ${protocolosParaVerificar.length}`);
            
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
                confirmButtonColor: '#0dcaf0'
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
                        console.log('✅ Verificação concluída:', data.resultados);
                        
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
                    console.log(`🔄 Processando... ${data.processados}/${data.total}`);
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
        
        console.log(`🔍 DEBUG: Total de pedidos visíveis: ${pedidosVisiveis.length}`);
        
        let debugPedidosComProtocolo = 0;
        let debugPedidosSemProtocolo = 0;
        let debugProtocolosConfirmados = 0;
        let debugTotalSeparacoes = 0;
        
        pedidosVisiveis.forEach(pedidoRow => {
            const numPedido = pedidoRow.dataset.numPedido;
            
            // NOVO: Buscar nas separações compactas em cache
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
        
        console.log(`📊 DEBUG Contadores (SEPARAÇÕES):
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
            contador.className = totalProtocolosUnicos > 0 ? 'badge bg-danger ms-1' : 'badge bg-secondary ms-1';
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
                confirmButtonColor: '#ffc107'
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
                        console.log('✅ Verificação de todos protocolos concluída');
                        
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
    
    // Interceptar cliques em botões para pausar carregamento
    setupInterceptadorBotoes() {
        document.addEventListener('click', (e) => {
            const target = e.target;
            const isButton = target.closest('button, .btn, a[href], [onclick]');
            
            if (isButton) {
                console.log('⏸️ Pausando carregamentos - botão clicado');
                
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
                    console.log('▶️ Retomando carregamentos');
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
        console.log(`🔄 Atualizando separação compacta ${loteId}`);
        
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
                    console.log(`✅ Dados atualizados na memória para ${loteId}`);
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
                        console.log(`✅ Dados atualizados em dadosAgrupados para ${loteId}`);
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
}

// 🎯 FUNÇÕES GLOBAIS PARA ONCLICK (BOTÕES DOS CARDS)
function editarSeparacao(loteId) {
    console.log(`✏️ Editar separação ${loteId}`);
    // TODO: Implementar modal de edição
}

function imprimirSeparacao(loteId) {
    console.log(`🖨️ Imprimir separação ${loteId}`);
    // TODO: Implementar impressão
}

function cancelarSeparacao(loteId) {
    if (confirm(`Tem certeza que deseja cancelar a separação ${loteId}?`)) {
        console.log(`🗑️ Cancelar separação ${loteId}`);
        // TODO: Implementar cancelamento
    }
}

function criarSeparacao(numPedido) {
    console.log(`📦 Delegando criação de separação para SeparacaoManager`);
    if (window.separacaoManager) {
        window.separacaoManager.criarSeparacaoCompleta(numPedido);
    } else {
        console.error('❌ Separação Manager não inicializado');
    }
}

function avaliarEstoques(numPedido) {
    console.log(`📊 Avaliar estoques do pedido ${numPedido}`);

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
    console.log(`📍 Abrir modal de endereço do pedido ${numPedido}`);
    if (window.modalEndereco) {
        window.modalEndereco.abrirModalEndereco(numPedido);
    } else {
        console.error('❌ Modal de endereço não inicializado');
    }
}// 🎯 INICIALIZAÇÃO GLOBAL
window.CarteiraAgrupada = CarteiraAgrupada;

