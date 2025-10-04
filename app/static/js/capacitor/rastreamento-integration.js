/**
 * 🚀 INTEGRAÇÃO RASTREAMENTO - Usa GPSServiceHibrido
 * Substitui a lógica antiga mantendo 100% da funcionalidade
 */

// Configurações vindas do template
let TOKEN, INTERVALO_PING, DISTANCIA_CHEGADA;
let totalPingsEnviados = 0;

// Instância do serviço GPS
let gpsService = null;

// Elementos DOM
let statusBadge, distanciaDestino, ultimaAtualizacao, totalPings, precisaoGPS;
let bateriaIndicator, bateriaNivel, btnEntregue, loadingOverlay, alertFixed;

/**
 * Inicializar sistema de rastreamento
 */
function inicializarRastreamento(config) {
    // Armazenar configurações
    TOKEN = config.token;
    INTERVALO_PING = config.intervaloPing * 1000; // Converter para ms
    DISTANCIA_CHEGADA = config.distanciaChegada;
    totalPingsEnviados = config.pingsIniciais || 0;

    // Buscar elementos DOM
    statusBadge = document.getElementById('statusBadge');
    distanciaDestino = document.getElementById('distanciaDestino');
    ultimaAtualizacao = document.getElementById('ultimaAtualizacao');
    totalPings = document.getElementById('totalPings');
    precisaoGPS = document.getElementById('precisaoGPS');
    bateriaIndicator = document.getElementById('bateriaIndicator');
    bateriaNivel = document.getElementById('bateriaNivel');
    btnEntregue = document.getElementById('btnEntregue');
    loadingOverlay = document.getElementById('loadingOverlay');
    alertFixed = document.getElementById('alertFixed');

    // Criar instância do GPS Service Híbrido
    gpsService = new GPSServiceHibrido({
        token: TOKEN,
        apiBaseUrl: window.location.origin,
        intervaloPing: INTERVALO_PING,
        distanciaChegada: DISTANCIA_CHEGADA,
        onLocalizacaoAtualizada: handleLocalizacaoAtualizada,
        onPingEnviado: handlePingEnviado,
        onChegouProximo: handleChegouProximo,
        onErro: handleErro
    });

    // Iniciar rastreamento
    iniciarGPS();

    // Configurar botão de entrega
    if (btnEntregue) {
        btnEntregue.addEventListener('click', function() {
            window.location.href = config.urlUploadCanhoto;
        });
    }

    // Cleanup ao sair
    window.addEventListener('beforeunload', function() {
        if (gpsService) {
            gpsService.parar();
        }
    });

    // Monitorar bateria (mantém lógica existente para web)
    if (PlatformDetector.isWeb()) {
        monitorarBateriaWeb();
    }
}

/**
 * Iniciar GPS
 */
async function iniciarGPS() {
    try {
        mostrarLoading(true);

        // Detectar plataforma e informar usuário
        const plataforma = PlatformDetector.getPlatform();
        const emoji = PlatformDetector.isNative() ? '📱' : '🌐';

        console.log(`${emoji} Plataforma detectada:`, plataforma.toUpperCase());

        if (PlatformDetector.isNative()) {
            mostrarAlerta(`📱 App Nativo Detectado - GPS Background Ativado!`, 'success');
        } else {
            mostrarAlerta(`🌐 Web Browser - Mantenha esta página aberta`, 'info');
        }

        await gpsService.iniciar();

        mostrarLoading(false);
        atualizarStatusBadge('RASTREANDO', 'success');

    } catch (error) {
        mostrarLoading(false);
        mostrarAlerta('Erro ao iniciar rastreamento: ' + error.message, 'danger');
        atualizarStatusBadge('ERRO', 'danger');
    }
}

/**
 * Handler: Localização atualizada
 */
function handleLocalizacaoAtualizada(localizacao) {
    // Atualizar UI
    if (precisaoGPS) {
        const precisaoTexto = `${Math.round(localizacao.precisao)}m`;
        const precisaoClass = localizacao.precisao < 20 ? 'text-success' :
                             localizacao.precisao < 50 ? 'text-warning' : 'text-danger';
        precisaoGPS.innerHTML = `<i class="fas fa-bullseye ${precisaoClass}"></i> ${precisaoTexto}`;
    }

    if (ultimaAtualizacao) {
        ultimaAtualizacao.textContent = new Date().toLocaleTimeString('pt-BR');
    }

    // Log com ícone baseado na plataforma
    const emoji = PlatformDetector.isNative() ? '📱' : '🌐';
    console.log(`${emoji} Localização atualizada:`, {
        lat: localizacao.latitude.toFixed(6),
        lng: localizacao.longitude.toFixed(6),
        precisao: `${Math.round(localizacao.precisao)}m`,
        fonte: localizacao.fonte
    });
}

/**
 * Handler: Ping enviado com sucesso
 */
function handlePingEnviado(data) {
    totalPingsEnviados++;

    // Atualizar contador de pings
    if (totalPings) {
        totalPings.textContent = totalPingsEnviados;
    }

    // Atualizar distância
    if (data.distancia_destino && distanciaDestino) {
        const distanciaKm = (data.distancia_destino / 1000).toFixed(1);
        distanciaDestino.innerHTML = `<i class="fas fa-map-marker-alt"></i> ${distanciaKm} km`;
    }

    // Atualizar bateria (se vier do backend)
    if (data.bateria_nivel !== undefined && data.bateria_nivel !== null) {
        atualizarBateriaUI(data.bateria_nivel, data.bateria_carregando || false);
    }

    console.log('✅ Ping #' + totalPingsEnviados + ' enviado com sucesso');
}

/**
 * Handler: Chegou próximo ao destino
 */
function handleChegouProximo(data) {
    mostrarAlerta('🎯 Você está próximo do destino!', 'warning', 10000);
    atualizarStatusBadge('PRÓXIMO', 'warning');

    // Vibrar se disponível
    if ('vibrate' in navigator) {
        navigator.vibrate([200, 100, 200]);
    }

    console.log('🎯 CHEGOU PRÓXIMO AO DESTINO:', data);
}

/**
 * Handler: Erro
 */
function handleErro(mensagem) {
    mostrarAlerta(mensagem, 'danger');
    console.error('❌ Erro:', mensagem);
}

/**
 * Atualizar badge de status
 */
function atualizarStatusBadge(texto, tipo) {
    if (!statusBadge) return;

    const classes = {
        'success': 'bg-success',
        'warning': 'bg-warning',
        'danger': 'bg-danger',
        'info': 'bg-info'
    };

    statusBadge.className = `badge ${classes[tipo] || 'bg-secondary'} fs-6`;
    statusBadge.textContent = texto;
}

/**
 * Mostrar/ocultar loading
 */
function mostrarLoading(mostrar) {
    if (loadingOverlay) {
        loadingOverlay.style.display = mostrar ? 'flex' : 'none';
    }
}

/**
 * Mostrar alerta fixo
 */
function mostrarAlerta(mensagem, tipo = 'info', duracao = 5000) {
    if (!alertFixed) return;

    const classes = {
        'success': 'alert-success',
        'warning': 'alert-warning',
        'danger': 'alert-danger',
        'info': 'alert-info'
    };

    alertFixed.className = `alert ${classes[tipo] || 'alert-info'} alert-dismissible fade show`;
    alertFixed.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertFixed.style.display = 'block';

    if (duracao > 0) {
        setTimeout(() => {
            alertFixed.style.display = 'none';
        }, duracao);
    }
}

/**
 * Monitorar bateria (Web API - fallback)
 */
async function monitorarBateriaWeb() {
    if (!('getBattery' in navigator)) return;

    try {
        const battery = await navigator.getBattery();

        const atualizarBateria = () => {
            const nivel = Math.round(battery.level * 100);
            atualizarBateriaUI(nivel, battery.charging);
        };

        atualizarBateria();

        battery.addEventListener('levelchange', atualizarBateria);
        battery.addEventListener('chargingchange', atualizarBateria);

    } catch (error) {
        console.log('Bateria API não disponível');
    }
}

/**
 * Atualizar UI de bateria
 */
function atualizarBateriaUI(nivel, carregando) {
    if (!bateriaIndicator || !bateriaNivel) return;

    bateriaNivel.textContent = `${nivel}%`;

    // Definir cor do indicador
    let corClasse = 'text-success';
    if (nivel < 20) corClasse = 'text-danger';
    else if (nivel < 50) corClasse = 'text-warning';

    // Ícone
    let icone = 'fa-battery-full';
    if (nivel < 20) icone = 'fa-battery-empty';
    else if (nivel < 50) icone = 'fa-battery-half';
    else if (nivel < 80) icone = 'fa-battery-three-quarters';

    if (carregando) {
        icone = 'fa-charging-station';
        corClasse = 'text-success';
    }

    bateriaIndicator.className = `fas ${icone} ${corClasse}`;
}

// Exportar para uso global
window.inicializarRastreamento = inicializarRastreamento;
