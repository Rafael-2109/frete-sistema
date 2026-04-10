/**
 * Scanner de Etiqueta Moto — Componente reutilizavel
 * ====================================================
 *
 * Usa camera do celular/tablet para ler etiquetas de moto via barcode
 * detection (html5-qrcode) + Claude Vision API (backend).
 *
 * Extrai: modelo, cor, chassi, numero_motor.
 *
 * Uso (auto-init via data-scanner-moto):
 *
 *   <button data-scanner-moto
 *           data-scanner-campo-modelo="#modelo"
 *           data-scanner-campo-cor="#cor"
 *           data-scanner-campo-chassi="#chassi"
 *           data-scanner-campo-motor="#numero_motor"
 *           data-scanner-titulo="Escanear Etiqueta"
 *           data-scanner-api="/api/v1/scanner/moto">
 *       Escanear Etiqueta
 *   </button>
 *
 * Eventos disparados:
 *   - 'moto-scanned' (CustomEvent) no document, com detail: {modelo, cor, chassi, numero_motor, confianca}
 *
 * Dependencia: html5-qrcode@2.3.8 (CDN ou local)
 *
 * @requires Html5Qrcode
 */

(function () {
    'use strict';

    var DEFAULT_API = '/api/v1/scanner/moto';
    var COOLDOWN_MS = 3000;
    var API_TIMEOUT_MS = 15000;
    var READER_ID = 'scanner-moto-reader';
    var OVERLAY_ID = 'scanner-moto-overlay';

    var html5QrCode = null;
    var isProcessing = false;
    var lastScanTime = 0;
    var currentConfig = {};

    // ══════════════════════════════════════════════════════
    //  INIT
    // ══════════════════════════════════════════════════════

    function init() {
        document.querySelectorAll('[data-scanner-moto]').forEach(attachTrigger);
    }

    function attachTrigger(btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            abrir({
                campoModelo: this.getAttribute('data-scanner-campo-modelo') || '',
                campoCor: this.getAttribute('data-scanner-campo-cor') || '',
                campoChassi: this.getAttribute('data-scanner-campo-chassi') || '',
                campoMotor: this.getAttribute('data-scanner-campo-motor') || '',
                titulo: this.getAttribute('data-scanner-titulo') || 'Escanear Etiqueta',
                apiUrl: this.getAttribute('data-scanner-api') || DEFAULT_API
            });
        });
    }

    // ══════════════════════════════════════════════════════
    //  OVERLAY — Criar/Remover
    // ══════════════════════════════════════════════════════

    function criarOverlay(titulo) {
        // Guard: nao duplicar
        if (document.getElementById(OVERLAY_ID)) return;

        var overlay = document.createElement('div');
        overlay.id = OVERLAY_ID;
        overlay.className = 'scanner-moto-overlay';
        overlay.innerHTML =
            '<div class="scanner-moto-header">' +
                '<h2>' + escapeHtml(titulo) + '</h2>' +
                '<button class="scanner-moto-btn-fechar" id="scanner-moto-btn-fechar">Fechar</button>' +
            '</div>' +
            '<div class="scanner-moto-viewfinder">' +
                '<div id="' + READER_ID + '"></div>' +
            '</div>' +
            '<div class="scanner-moto-status-area">' +
                '<div class="scanner-moto-instructions">' +
                    '<strong>Aponte a camera para a etiqueta da moto.</strong><br>' +
                    'O codigo de barras sera lido automaticamente.' +
                '</div>' +
                '<div class="scanner-moto-status" id="scanner-moto-status"></div>' +
                '<div class="scanner-moto-result" id="scanner-moto-result">' +
                    '<div class="scanner-moto-result-grid" id="scanner-moto-result-grid"></div>' +
                    '<div id="scanner-moto-confianca-area"></div>' +
                    '<div id="scanner-moto-aviso-area"></div>' +
                    '<div class="scanner-moto-actions" id="scanner-moto-actions">' +
                        '<button class="scanner-moto-btn-confirmar" id="scanner-moto-btn-confirmar">Confirmar</button>' +
                        '<button class="scanner-moto-btn-reescanear" id="scanner-moto-btn-reescanear">Reescanear</button>' +
                    '</div>' +
                '</div>' +
                '<button class="scanner-moto-btn-manual" id="scanner-moto-btn-manual">' +
                    'Digitar manualmente' +
                '</button>' +
            '</div>';

        document.body.appendChild(overlay);

        // Eventos
        document.getElementById('scanner-moto-btn-fechar').addEventListener('click', fechar);
        document.getElementById('scanner-moto-btn-manual').addEventListener('click', function () {
            fechar();
            // Focar no primeiro campo configurado
            var primeiro = currentConfig.campoChassi || currentConfig.campoModelo || currentConfig.campoCor;
            if (primeiro) {
                var el = document.querySelector(primeiro);
                if (el) el.focus();
            }
        });
        document.getElementById('scanner-moto-btn-confirmar').addEventListener('click', confirmarResultado);
        document.getElementById('scanner-moto-btn-reescanear').addEventListener('click', reescanear);
    }

    function removerOverlay() {
        var overlay = document.getElementById(OVERLAY_ID);
        if (overlay) overlay.remove();
    }

    // ══════════════════════════════════════════════════════
    //  ABRIR / FECHAR
    // ══════════════════════════════════════════════════════

    function abrir(config) {
        currentConfig = config || {};
        isProcessing = false;

        // Verificar se html5-qrcode esta disponivel
        if (typeof Html5Qrcode === 'undefined') {
            // Tentar carregar dinamicamente
            carregarHtml5QrCode(function () {
                _abrirScanner(config);
            });
            return;
        }

        _abrirScanner(config);
    }

    function _abrirScanner(config) {
        criarOverlay(config.titulo || 'Escanear Etiqueta');

        // Bloquear scroll do body
        document.body.style.overflow = 'hidden';

        // Iniciar scanner de barcode
        html5QrCode = new Html5Qrcode(READER_ID);

        var qrConfig = {
            fps: 8,
            qrbox: { width: 280, height: 150 },
            formatsToSupport: getFormatos()
        };

        html5QrCode.start(
            { facingMode: 'environment' },
            qrConfig,
            onBarcodeDetected,
            function () { /* ignorar erros de scan frame-a-frame */ }
        ).catch(function (err) {
            console.error('Erro ao iniciar camera:', err);
            mostrarStatus('error', 'Erro ao acessar camera. Verifique as permissoes do navegador.');
        });
    }

    function fechar() {
        if (html5QrCode) {
            html5QrCode.stop().catch(function () {});
            html5QrCode = null;
        }

        // Restaurar scroll
        document.body.style.overflow = '';

        removerOverlay();
        isProcessing = false;
    }

    // ══════════════════════════════════════════════════════
    //  BARCODE DETECTED — Trigger principal
    // ══════════════════════════════════════════════════════

    function onBarcodeDetected(decodedText) {
        // Guard: cooldown e processamento
        var now = Date.now();
        if (isProcessing || (now - lastScanTime) < COOLDOWN_MS) return;
        isProcessing = true;
        lastScanTime = now;

        // Feedback haptico
        if (navigator.vibrate) navigator.vibrate(200);

        // Capturar frame do video
        capturarEEnviar();
    }

    function capturarEEnviar() {
        var videoElement = document.querySelector('#' + READER_ID + ' video');

        if (!videoElement) {
            mostrarStatus('error', 'Camera nao disponivel.');
            isProcessing = false;
            return;
        }

        // Capturar frame via Canvas
        var canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth || 640;
        canvas.height = videoElement.videoHeight || 480;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

        // Converter para JPEG base64
        var dataUrl = canvas.toDataURL('image/jpeg', 0.7);
        var base64 = dataUrl.split(',')[1];

        // Pausar scanner
        if (html5QrCode) {
            html5QrCode.pause(true);
        }

        // Mostrar loading
        mostrarStatus('loading', 'Lendo etiqueta...');

        // Enviar para API
        enviarParaApi(base64);
    }

    function enviarParaApi(imageBase64) {
        var apiUrl = currentConfig.apiUrl || DEFAULT_API;

        // CSRF token (interceptor global do base.html cuida, mas garantir)
        var csrfMeta = document.querySelector('meta[name="csrf-token"]');
        var headers = { 'Content-Type': 'application/json' };
        if (csrfMeta) {
            headers['X-CSRFToken'] = csrfMeta.getAttribute('content');
        }

        // AbortController para timeout
        var controller = new AbortController();
        var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

        fetch(apiUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ imagem: imageBase64 }),
            signal: controller.signal
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            clearTimeout(timeoutId);
            if (data.success) {
                mostrarResultado(data.data, data.aviso);
            } else {
                mostrarStatus('error', data.error || 'Erro ao ler etiqueta.');
                setTimeout(function () { reescanear(); }, 2000);
            }
        })
        .catch(function (err) {
            clearTimeout(timeoutId);
            if (err.name === 'AbortError') {
                mostrarStatus('error', 'Tempo esgotado. Tente novamente.');
            } else {
                mostrarStatus('error', 'Erro de conexao: ' + err.message);
            }
            setTimeout(function () { reescanear(); }, 2500);
        });
    }

    // ══════════════════════════════════════════════════════
    //  RESULTADO — Exibir e confirmar
    // ══════════════════════════════════════════════════════

    var _lastResult = null;

    function mostrarResultado(data, aviso) {
        _lastResult = data;

        // Esconder status loading
        var statusEl = document.getElementById('scanner-moto-status');
        if (statusEl) statusEl.style.display = 'none';

        // Preencher grid de resultado
        var grid = document.getElementById('scanner-moto-result-grid');
        if (grid) {
            grid.innerHTML = '';

            var campos = [
                { label: 'Modelo', value: data.modelo },
                { label: 'Cor', value: data.cor },
                { label: 'Chassi', value: data.chassi },
                { label: 'Motor', value: data.numero_motor }
            ];

            campos.forEach(function (campo) {
                var labelEl = document.createElement('span');
                labelEl.className = 'scanner-moto-result-label';
                labelEl.textContent = campo.label;

                var valueEl = document.createElement('span');
                valueEl.className = 'scanner-moto-result-value';
                if (campo.value) {
                    valueEl.textContent = campo.value;
                } else {
                    valueEl.textContent = 'nao detectado';
                    valueEl.classList.add('is-null');
                }

                grid.appendChild(labelEl);
                grid.appendChild(valueEl);
            });
        }

        // Badge de confianca
        var confArea = document.getElementById('scanner-moto-confianca-area');
        if (confArea) {
            var conf = data.confianca || 0;
            var cls = conf >= 0.8 ? 'is-high' : (conf >= 0.5 ? 'is-medium' : 'is-low');
            confArea.innerHTML = '<span class="scanner-moto-confianca ' + cls + '">' +
                'Confianca: ' + Math.round(conf * 100) + '%</span>';
        }

        // Aviso
        var avisoArea = document.getElementById('scanner-moto-aviso-area');
        if (avisoArea) {
            avisoArea.innerHTML = aviso
                ? '<div class="scanner-moto-aviso">' + escapeHtml(aviso) + '</div>'
                : '';
        }

        // Mostrar card de resultado
        var resultEl = document.getElementById('scanner-moto-result');
        if (resultEl) resultEl.classList.add('is-visible');

        // Feedback sonoro via vibracoa
        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
    }

    function confirmarResultado() {
        if (!_lastResult) return;

        // Preencher campos do formulario
        preencherCampo(currentConfig.campoModelo, _lastResult.modelo);
        preencherCampo(currentConfig.campoCor, _lastResult.cor);
        preencherCampo(currentConfig.campoChassi, _lastResult.chassi);
        preencherCampo(currentConfig.campoMotor, _lastResult.numero_motor);

        // Disparar evento customizado
        document.dispatchEvent(new CustomEvent('moto-scanned', {
            detail: _lastResult,
            bubbles: true
        }));

        // Toast de sucesso
        if (window.toastr) {
            toastr.success('Etiqueta lida com sucesso!');
        }

        // Fechar overlay
        fechar();
    }

    function reescanear() {
        isProcessing = false;
        _lastResult = null;

        // Esconder resultado
        var resultEl = document.getElementById('scanner-moto-result');
        if (resultEl) resultEl.classList.remove('is-visible');

        // Esconder status
        var statusEl = document.getElementById('scanner-moto-status');
        if (statusEl) statusEl.style.display = 'none';

        // Retomar scanner
        if (html5QrCode) {
            try {
                html5QrCode.resume();
            } catch (e) {
                console.warn('Nao foi possivel retomar scanner, reiniciando...', e);
                fechar();
                abrir(currentConfig);
            }
        }
    }

    // ══════════════════════════════════════════════════════
    //  HELPERS
    // ══════════════════════════════════════════════════════

    function preencherCampo(selector, value) {
        if (!selector || !value) return;
        var el = document.querySelector(selector);
        if (!el) return;
        el.value = value;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function mostrarStatus(tipo, msg) {
        var statusEl = document.getElementById('scanner-moto-status');
        if (!statusEl) return;

        statusEl.className = 'scanner-moto-status';

        if (tipo === 'loading') {
            statusEl.classList.add('is-loading');
            statusEl.innerHTML = '<div class="scanner-moto-spinner"></div> ' + escapeHtml(msg);
        } else if (tipo === 'error') {
            statusEl.classList.add('is-error');
            statusEl.textContent = msg;
        } else if (tipo === 'success') {
            statusEl.classList.add('is-success');
            statusEl.textContent = msg;
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function getFormatos() {
        // Verificar se constantes estao disponiveis
        if (typeof Html5QrcodeSupportedFormats !== 'undefined') {
            return [
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.CODE_39,
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.DATA_MATRIX
            ];
        }
        return undefined; // html5-qrcode usara todos os formatos
    }

    var _loadingLib = false;
    function carregarHtml5QrCode(callback) {
        if (_loadingLib) return; // Evita carregamento duplicado
        _loadingLib = true;

        var script = document.createElement('script');
        script.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
        script.onload = function () {
            _loadingLib = false;
            callback();
        };
        script.onerror = function () {
            _loadingLib = false;
            console.error('Erro ao carregar html5-qrcode');
            if (window.toastr) {
                toastr.error('Erro ao carregar biblioteca de scanner.');
            }
        };
        document.head.appendChild(script);
    }

    // ══════════════════════════════════════════════════════
    //  CLEANUP
    // ══════════════════════════════════════════════════════

    window.addEventListener('beforeunload', function () {
        if (html5QrCode) {
            html5QrCode.stop().catch(function () {});
        }
    });

    // ══════════════════════════════════════════════════════
    //  AUTO-INIT + EXPORT
    // ══════════════════════════════════════════════════════

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.ScannerMoto = {
        init: init,
        abrir: abrir,
        fechar: fechar
    };
})();
