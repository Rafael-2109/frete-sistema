/**
 * SERVICO GPS HIBRIDO - NACOM RASTREAMENTO
 *
 * Detecta automaticamente se está rodando como:
 * - App Nativo (Capacitor) -> Usa GPS Background Real
 * - Web Browser -> Usa navigator.geolocation tradicional
 *
 * Integrado 100% com a lógica de negócio existente
 */

// Design token helper for native notification colors
// Note: Native Android needs hex colors, but we try CSS first
const getNotificationColor = () => {
    try {
        const cssColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--semantic-success').trim();
        // If CSS variable exists and is HSL, convert to hex (simplified)
        if (cssColor && cssColor.startsWith('hsl')) {
            // For native Android, use hardcoded hex as HSL parsing is complex
            // This is the semantic-success equivalent
            return '#22c55e';
        }
        return cssColor || '#22c55e';
    } catch {
        return '#22c55e'; // Fallback to green
    }
};

class PlatformDetector {
    /**
     * Detecta se está rodando no Capacitor (app nativo)
     */
    static isCapacitor() {
        return typeof window.Capacitor !== 'undefined';
    }

    /**
     * Detecta se é plataforma nativa (Android/iOS)
     */
    static isNative() {
        return this.isCapacitor() && window.Capacitor.isNativePlatform();
    }

    /**
     * Detecta se é web browser
     */
    static isWeb() {
        return !this.isNative();
    }

    /**
     * Retorna nome da plataforma
     */
    static getPlatform() {
        if (this.isNative()) {
            return window.Capacitor.getPlatform(); // 'android' ou 'ios'
        }
        return 'web';
    }

    /**
     * Log contextualizado por plataforma
     */
    static log(message, data = null) {
        const platform = this.getPlatform().toUpperCase();
        const prefix = this.isNative() ? '📱' : '🌐';

        if (data) {
            console.log(`${prefix} [${platform}] ${message}`, data);
        } else {
            console.log(`${prefix} [${platform}] ${message}`);
        }
    }
}

class GPSServiceHibrido {
    constructor(config = {}) {
        this.token = config.token; // Token de autenticação
        this.apiBaseUrl = config.apiBaseUrl || window.location.origin;
        this.intervaloPing = config.intervaloPing || 120000; // 2 minutos
        this.distanciaChegada = config.distanciaChegada || 200; // metros

        // Estado interno
        this.watchId = null;
        this.intervalId = null;
        this.ultimaLocalizacao = null;
        this.isRastreando = false;
        this.backgroundTaskId = null;

        // Callbacks
        this.onLocalizacaoAtualizada = config.onLocalizacaoAtualizada || null;
        this.onPingEnviado = config.onPingEnviado || null;
        this.onChegouProximo = config.onChegouProximo || null;
        this.onErro = config.onErro || null;

        PlatformDetector.log('GPS Service inicializado', {
            plataforma: PlatformDetector.getPlatform(),
            token: this.token ? 'definido' : 'indefinido',
            intervaloPing: this.intervaloPing / 1000 + 's'
        });
    }

    /**
     * Inicia rastreamento (detecta plataforma automaticamente)
     */
    async iniciar() {
        if (this.isRastreando) {
            PlatformDetector.log('⚠️ Rastreamento já está ativo');
            return;
        }

        try {
            if (PlatformDetector.isNative()) {
                await this.iniciarGPSNativo();
            } else {
                await this.iniciarGPSWeb();
            }

            this.isRastreando = true;
            PlatformDetector.log('✅ Rastreamento iniciado com sucesso');
        } catch (error) {
            PlatformDetector.log('❌ Erro ao iniciar rastreamento', error);
            if (this.onErro) {
                this.onErro('Erro ao iniciar rastreamento: ' + error.message);
            }
            throw error;
        }
    }

    /**
     * GPS NATIVO (Capacitor) - Background Real
     */
    async iniciarGPSNativo() {
        PlatformDetector.log('Iniciando GPS NATIVO com Background Geolocation...');

        const { BackgroundGeolocation } = window.Capacitor.Plugins;

        // Solicitar permissões primeiro
        const permissao = await this.solicitarPermissoesNativas();
        if (!permissao) {
            throw new Error('Permissão de localização negada');
        }

        // Configurar plugin de background
        await BackgroundGeolocation.configure({
            // Provedor de localização
            locationProvider: BackgroundGeolocation.ACTIVITY_PROVIDER,
            desiredAccuracy: BackgroundGeolocation.HIGH_ACCURACY,

            // Parâmetros de rastreamento
            stationaryRadius: 50, // Raio em metros para considerar "parado"
            distanceFilter: 30,   // Mínimo de movimento (metros) para atualizar

            // Intervalos de atualização
            interval: 120000,           // 2 minutos (igual ao sistema web)
            fastestInterval: 60000,     // Mínimo de 1 minuto entre updates
            activitiesInterval: 300000, // Detecção de atividade a cada 5 min

            // Notificacao persistente (Android)
            notificationTitle: 'Rastreamento Ativo',
            notificationText: 'Enviando localização para a empresa',
            notificationIconColor: getNotificationColor(),
            notificationIconLarge: 'ic_launcher',
            notificationIconSmall: 'ic_stat_icon',

            // Comportamento em background
            stopOnTerminate: false,      // Continua após fechar app
            startOnBoot: false,          // NÃO inicia no boot (apenas quando usuário ativar)
            startForeground: true,       // Notificação persistente (Android)

            // Modo de economia de bateria
            saveBatteryOnBackground: true,

            // Debug (desativar em produção)
            debug: false,
            debugNotification: false
        });

        // Listener de localização
        BackgroundGeolocation.on('location', (location) => {
            this.processarLocalizacaoNativa(location);
        });

        // Listener de erro
        BackgroundGeolocation.on('error', (error) => {
            PlatformDetector.log('❌ Erro no Background Geolocation', error);
            if (this.onErro) {
                this.onErro('Erro GPS: ' + error.message);
            }
        });

        // Listener de status
        BackgroundGeolocation.on('stationary', (location) => {
            PlatformDetector.log('🛑 Veículo parado detectado', location);
        });

        BackgroundGeolocation.on('activity', (activity) => {
            PlatformDetector.log('🏃 Atividade detectada', activity);
        });

        // Iniciar tracking
        await BackgroundGeolocation.start();

        PlatformDetector.log('✅ Background Geolocation ATIVADO');

        // Também configurar intervalo de ping (redundância)
        this.intervalId = setInterval(() => this.enviarPingAgora(), this.intervaloPing);
    }

    /**
     * GPS WEB (Navigator) - Tradicional
     */
    async iniciarGPSWeb() {
        PlatformDetector.log('Iniciando GPS WEB (navigator.geolocation)...');

        if (!('geolocation' in navigator)) {
            throw new Error('Geolocalização não suportada neste navegador');
        }

        const opcoes = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        };

        // WatchPosition para monitoramento contínuo
        this.watchId = navigator.geolocation.watchPosition(
            (position) => this.processarLocalizacaoWeb(position),
            (error) => this.tratarErroGeolocalizacao(error),
            opcoes
        );

        // Intervalo fixo de ping (a cada 2 minutos)
        this.intervalId = setInterval(() => this.enviarPingAgora(), this.intervaloPing);

        PlatformDetector.log('✅ Navigator Geolocation ATIVADO');
    }

    /**
     * Processar localização vinda do plugin nativo
     */
    processarLocalizacaoNativa(location) {
        this.ultimaLocalizacao = {
            latitude: location.latitude,
            longitude: location.longitude,
            precisao: location.accuracy,
            altitude: location.altitude || null,
            velocidade: location.speed ? location.speed * 3.6 : null, // m/s para km/h
            direcao: location.bearing || null,
            timestamp: location.time ? new Date(location.time).toISOString() : new Date().toISOString(),
            fonte: 'nativo'
        };

        PlatformDetector.log('📍 Localização NATIVA atualizada', {
            lat: this.ultimaLocalizacao.latitude.toFixed(6),
            lng: this.ultimaLocalizacao.longitude.toFixed(6),
            precisao: `${Math.round(this.ultimaLocalizacao.precisao)}m`,
            velocidade: this.ultimaLocalizacao.velocidade ? `${Math.round(this.ultimaLocalizacao.velocidade)}km/h` : 'N/A'
        });

        if (this.onLocalizacaoAtualizada) {
            this.onLocalizacaoAtualizada(this.ultimaLocalizacao);
        }
    }

    /**
     * Processar localização vinda do navegador web
     */
    processarLocalizacaoWeb(position) {
        this.ultimaLocalizacao = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            precisao: position.coords.accuracy,
            altitude: position.coords.altitude,
            velocidade: position.coords.speed ? position.coords.speed * 3.6 : null,
            direcao: position.coords.heading,
            timestamp: new Date(position.timestamp).toISOString(),
            fonte: 'web'
        };

        PlatformDetector.log('📍 Localização WEB atualizada', {
            lat: this.ultimaLocalizacao.latitude.toFixed(6),
            lng: this.ultimaLocalizacao.longitude.toFixed(6),
            precisao: `${Math.round(this.ultimaLocalizacao.precisao)}m`
        });

        if (this.onLocalizacaoAtualizada) {
            this.onLocalizacaoAtualizada(this.ultimaLocalizacao);
        }
    }

    /**
     * Tratar erros de geolocalização (web)
     */
    tratarErroGeolocalizacao(error) {
        let mensagem = 'Erro ao obter localização.';

        switch(error.code) {
            case error.PERMISSION_DENIED:
                mensagem = 'Permissão de localização negada. Ative nas configurações do navegador.';
                break;
            case error.POSITION_UNAVAILABLE:
                mensagem = 'Localização indisponível. Verifique se o GPS está ativo.';
                break;
            case error.TIMEOUT:
                mensagem = 'Tempo esgotado ao obter localização. Tentando novamente...';
                break;
        }

        PlatformDetector.log('❌ Erro de geolocalização', mensagem);

        if (this.onErro) {
            this.onErro(mensagem);
        }
    }

    /**
     * Enviar ping GPS para o servidor
     */
    async enviarPingAgora() {
        if (!this.ultimaLocalizacao) {
            PlatformDetector.log('⏳ Aguardando primeira localização...');
            return;
        }

        if (!this.token) {
            PlatformDetector.log('❌ Token não definido, não é possível enviar ping');
            return;
        }

        try {
            // Obter nível de bateria
            let bateriaNivel = null;
            let bateriaCarregando = false;

            if (PlatformDetector.isNative()) {
                // Tentar obter bateria via Capacitor
                try {
                    const { Device } = window.Capacitor.Plugins;
                    const info = await Device.getBatteryInfo();
                    bateriaNivel = Math.round(info.batteryLevel * 100);
                    bateriaCarregando = info.isCharging;
                } catch (e) {
                    PlatformDetector.log('⚠️ Não foi possível obter info de bateria', e);
                }
            } else if ('getBattery' in navigator) {
                // Web Battery API
                const battery = await navigator.getBattery();
                bateriaNivel = Math.round(battery.level * 100);
                bateriaCarregando = battery.charging;
            }

            const dadosPing = {
                ...this.ultimaLocalizacao,
                bateria_nivel: bateriaNivel,
                bateria_carregando: bateriaCarregando
            };

            PlatformDetector.log('📤 Enviando ping GPS...', {
                lat: dadosPing.latitude.toFixed(6),
                lng: dadosPing.longitude.toFixed(6),
                bateria: bateriaNivel ? `${bateriaNivel}%` : 'N/A'
            });

            const response = await fetch(`${this.apiBaseUrl}/rastreamento/api/ping/${this.token}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(dadosPing)
            });

            const data = await response.json();

            if (data.success) {
                PlatformDetector.log('✅ Ping enviado com sucesso', data.data);

                if (this.onPingEnviado) {
                    this.onPingEnviado(data.data);
                }

                // Verificar se chegou próximo
                if (data.data.chegou_proximo && this.onChegouProximo) {
                    this.onChegouProximo(data.data);
                }
            } else {
                throw new Error(data.message || 'Erro desconhecido');
            }

        } catch (error) {
            PlatformDetector.log('❌ Erro ao enviar ping', error);
            if (this.onErro) {
                this.onErro('Erro ao enviar ping: ' + error.message);
            }
        }
    }

    /**
     * Solicitar permissões nativas (Android/iOS)
     */
    async solicitarPermissoesNativas() {
        if (!PlatformDetector.isNative()) {
            return true; // Web não precisa solicitar aqui
        }

        try {
            const { Geolocation } = window.Capacitor.Plugins;
            const permissao = await Geolocation.checkPermissions();

            if (permissao.location === 'granted') {
                PlatformDetector.log('✅ Permissão de localização já concedida');
                return true;
            }

            PlatformDetector.log('📋 Solicitando permissão de localização...');
            const resultado = await Geolocation.requestPermissions();

            if (resultado.location === 'granted') {
                PlatformDetector.log('✅ Permissão de localização concedida');
                return true;
            } else {
                PlatformDetector.log('❌ Permissão de localização negada');
                return false;
            }

        } catch (error) {
            PlatformDetector.log('❌ Erro ao solicitar permissões', error);
            return false;
        }
    }

    /**
     * Parar rastreamento
     */
    async parar() {
        if (!this.isRastreando) {
            return;
        }

        try {
            if (PlatformDetector.isNative()) {
                const { BackgroundGeolocation } = window.Capacitor.Plugins;
                await BackgroundGeolocation.stop();
                PlatformDetector.log('🛑 Background Geolocation PARADO');
            }

            if (this.watchId) {
                navigator.geolocation.clearWatch(this.watchId);
                this.watchId = null;
            }

            if (this.intervalId) {
                clearInterval(this.intervalId);
                this.intervalId = null;
            }

            this.isRastreando = false;
            PlatformDetector.log('🛑 Rastreamento PARADO');

        } catch (error) {
            PlatformDetector.log('❌ Erro ao parar rastreamento', error);
        }
    }

    /**
     * Obter última localização conhecida
     */
    obterUltimaLocalizacao() {
        return this.ultimaLocalizacao;
    }

    /**
     * Verificar se está rastreando
     */
    estaRastreando() {
        return this.isRastreando;
    }
}

// Exportar para uso global
window.PlatformDetector = PlatformDetector;
window.GPSServiceHibrido = GPSServiceHibrido;
