#!/usr/bin/env python3
"""
Configuração Stealth Completa para Playwright
Torna o navegador headless praticamente indetectável
"""

STEALTH_SCRIPT = """
(() => {
    // 1. WEBDRIVER - Remover todas as propriedades que denunciam automação
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 2. CHROME - Adicionar objeto chrome completo
    if (!window.chrome) {
        window.chrome = {};
    }
    window.chrome.runtime = {
        connect: () => {},
        sendMessage: () => {},
        onMessage: { addListener: () => {} }
    };
    window.chrome.loadTimes = function() {
        return {
            requestTime: Date.now() / 1000,
            startLoadTime: Date.now() / 1000,
            commitLoadTime: Date.now() / 1000,
            finishDocumentLoadTime: Date.now() / 1000,
            finishLoadTime: Date.now() / 1000,
            firstPaintTime: Date.now() / 1000,
            firstPaintAfterLoadTime: 0,
            navigationType: "Other",
            wasFetchedViaSpdy: false,
            wasNpnNegotiated: false,
            npnNegotiatedProtocol: "",
            wasAlternateProtocolAvailable: false,
            connectionInfo: "http/1.1"
        };
    };
    window.chrome.csi = function() {
        return {
            onloadT: Date.now(),
            pageT: Date.now(),
            startE: Date.now() - 1000,
            tran: 15
        };
    };
    window.chrome.app = {
        isInstalled: false,
        getDetails: () => null,
        getIsInstalled: () => false,
        installState: () => "not_installed",
        runningState: () => "not_running"
    };

    // 3. NAVIGATOR - Corrigir todas as propriedades
    Object.defineProperty(navigator, 'userAgent', {
        get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32'
    });

    Object.defineProperty(navigator, 'vendor', {
        get: () => 'Google Inc.'
    });

    Object.defineProperty(navigator, 'appVersion', {
        get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => 0
    });

    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });

    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });

    // 4. PLUGINS - Adicionar plugins realistas
    const pluginData = [
        {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format'
        },
        {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: ''
        },
        {
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: ''
        }
    ];

    const pluginArray = [];
    pluginData.forEach(p => {
        const plugin = Object.create(Plugin.prototype);
        plugin.name = p.name;
        plugin.filename = p.filename;
        plugin.description = p.description;
        plugin.length = 1;
        plugin[0] = Object.create(MimeType.prototype);
        plugin[0].type = 'application/x-google-chrome-pdf';
        plugin[0].suffixes = 'pdf';
        plugin[0].description = 'Portable Document Format';
        plugin[0].enabledPlugin = plugin;
        pluginArray.push(plugin);
    });

    Object.defineProperty(navigator, 'plugins', {
        get: () => pluginArray
    });

    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => {
            const mimeArray = [];
            pluginArray.forEach(p => {
                for (let i = 0; i < p.length; i++) {
                    mimeArray.push(p[i]);
                }
            });
            return mimeArray;
        }
    });

    // 5. LANGUAGES - Configurar idiomas
    Object.defineProperty(navigator, 'languages', {
        get: () => ['pt-BR', 'pt', 'en-US', 'en']
    });

    Object.defineProperty(navigator, 'language', {
        get: () => 'pt-BR'
    });

    // 6. WEBGL - Adicionar vendor e renderer reais
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';  // UNMASKED_VENDOR_WEBGL
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL
        }
        return getParameter.apply(this, arguments);
    };

    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter2.apply(this, arguments);
    };

    // 7. CANVAS - Adicionar ruído para fingerprint único
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
        const context = this.getContext('2d');
        if (context) {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] = imageData.data[i] ^ 1;     // R
                imageData.data[i+1] = imageData.data[i+1] ^ 1; // G
                imageData.data[i+2] = imageData.data[i+2] ^ 1; // B
            }
            context.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, arguments);
    };

    // 8. SCREEN - Configurar resolução real
    Object.defineProperty(screen, 'width', { get: () => 1920 });
    Object.defineProperty(screen, 'height', { get: () => 1080 });
    Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
    Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
    Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
    Object.defineProperty(window, 'outerWidth', { get: () => 1920 });
    Object.defineProperty(window, 'outerHeight', { get: () => 1040 });

    // 9. PERMISSIONS - Configurar permissões
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: 'default' }) :
            originalQuery(parameters)
    );

    // 10. CONEXÃO - Adicionar informações de rede
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10.0,
            saveData: false
        })
    });

    // 11. BATTERY - Simular bateria
    navigator.getBattery = () => Promise.resolve({
        charging: true,
        chargingTime: 0,
        dischargingTime: Infinity,
        level: 1.0
    });

    // 12. CDP - Remover propriedades do ChromeDriver
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

    // 13. RUNTIME - Esconder Puppeteer/Playwright
    delete window.__puppeteer_evaluation_script__;
    delete window.__playwright_evaluation_script__;

    // 14. CONSOLE - Limpar warnings de automation
    const originalConsoleDebug = console.debug;
    console.debug = function(...args) {
        if (args[0] && args[0].includes('DevTools')) return;
        return originalConsoleDebug.apply(console, args);
    };

    // 15. INTL - Configurar timezone
    const DateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(...args) {
        if (args[1]) {
            args[1].timeZone = 'America/Sao_Paulo';
        }
        return new DateTimeFormat(...args);
    };

    // 16. MEDIA DEVICES - Simular dispositivos de mídia
    if (!navigator.mediaDevices) {
        navigator.mediaDevices = {};
    }
    navigator.mediaDevices.enumerateDevices = () => Promise.resolve([
        {
            deviceId: "default",
            kind: "audioinput",
            label: "Default Audio Device",
            groupId: "default"
        }
    ]);

    // 17. SPEECHSYNTHESIS - Adicionar vozes
    window.speechSynthesis.getVoices = () => [
        { name: 'Microsoft Maria - Portuguese (Brazil)', lang: 'pt-BR', default: true }
    ];

    console.log('✅ Stealth mode ativado - Chrome praticamente indetectável');
})();
"""

def get_stealth_script():
    """Retorna o script stealth completo"""
    return STEALTH_SCRIPT

def get_minimal_stealth_script():
    """Retorna versão mínima do script stealth (mais leve)"""
    return """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt'] });
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.__puppeteer_evaluation_script__;
    """