/**
 * SswProgress — tracker global de operacoes SSW (Playwright headless).
 *
 * Exibe toast fixo bottom-right com etapa corrente, persiste operacoes
 * ativas em localStorage (sobrevive a reload/navegacao), polls via
 * fetch num statusUrl fornecido.
 *
 * Uso tipico:
 *   SswProgress.start({
 *     label: 'Emitindo CTe da NF 123',
 *     descricao: 'Conectando ao SSW, preenchendo form, enviando SEFAZ...',
 *     statusUrl: '/carvia/api/emissao-cte/456/status',
 *     statusType: 'emissao_cte',
 *     onDone: () => location.reload(),
 *   });
 *
 * Tipos suportados (statusType):
 *   - 'emissao_cte'       — CarviaEmissaoCte (NF -> CTe). Campos: status, etapa, erro
 *   - 'emissao_cte_comp'  — CarviaEmissaoCteComplementar (CustoEntrega -> 222)
 *   - 'rq_job'            — Job RQ generico (atualizar-ctrc, baixar-pdf-ssw)
 */
(function(window, document) {
    'use strict';

    var STORAGE_KEY = 'carvia_ssw_progress_v1';
    var POLL_DEFAULT_MS = 4000;
    var MINIMIZED_KEY = 'carvia_ssw_progress_minimized';

    var ETAPAS_LABEL = {
        emissao_cte: {
            LOGIN: 'Conectando ao SSW…',
            PREENCHIMENTO: 'Preenchendo formulário CTe…',
            SEFAZ: 'Enviando ao SEFAZ…',
            CONSULTA_101: 'Consultando resultado…',
            IMPORTACAO_CTE: 'Importando XML do CTe…',
            FATURA_437: 'Gerando fatura SSW…',
            IMPORTACAO_FAT: 'Importando fatura…',
        },
        emissao_cte_comp: {
            PREENCHIMENTO: 'Preenchendo CTe Complementar…',
            SEFAZ: 'Enviando ao SEFAZ…',
            CONSULTA_101: 'Consultando resultado…',
        },
        rq_job: {
            queued: 'Na fila…',
            started: 'Executando no SSW…',
            deferred: 'Aguardando…',
            scheduled: 'Agendado…',
        },
    };

    // Operacoes ativas — map jobId -> { meta, interval }
    var ativas = {};

    // ─────────────── Persistencia ───────────────

    function carregarPersistido() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return [];
            var arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr : [];
        } catch (e) {
            return [];
        }
    }

    function salvarPersistido() {
        try {
            var arr = Object.keys(ativas).map(function(k) {
                return ativas[k].meta;
            }).filter(function(m) {
                return m && !m._finalizado;
            });
            localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
        } catch (e) {}
    }

    // ─────────────── DOM ───────────────

    function garantirContainer() {
        var c = document.getElementById('ssw-progress-container');
        if (c) return c;

        c = document.createElement('div');
        c.id = 'ssw-progress-container';
        c.style.cssText =
            'position:fixed;bottom:16px;right:16px;z-index:10500;' +
            'display:flex;flex-direction:column-reverse;gap:8px;' +
            'max-width:380px;';
        document.body.appendChild(c);

        // Botao minimizar/restaurar (compartilhado)
        aplicarEstadoMinimizado(c);
        return c;
    }

    function aplicarEstadoMinimizado(c) {
        var min = localStorage.getItem(MINIMIZED_KEY) === '1';
        c.classList.toggle('ssw-progress-minimized', min);
        if (min) {
            c.style.maxHeight = '60px';
            c.style.overflow = 'hidden';
        } else {
            c.style.maxHeight = '';
            c.style.overflow = '';
        }
    }

    function criarCard(meta) {
        var card = document.createElement('div');
        card.id = 'ssw-progress-' + meta.id;
        card.className = 'card shadow border-warning';
        card.style.cssText = 'border-width:2px;';
        card.innerHTML = (
            '<div class="card-body p-2">' +
              '<div class="d-flex align-items-start justify-content-between mb-1">' +
                '<div class="fw-bold small text-dark" data-role="label">' +
                    escapeHtml(meta.label || 'Operação SSW') +
                '</div>' +
                '<div class="ms-2 d-flex gap-1">' +
                  '<button type="button" class="btn btn-sm btn-link p-0 text-muted" ' +
                    'title="Minimizar/Restaurar" data-action="toggle-min" ' +
                    'style="line-height:1;"><i class="fas fa-compress-arrows-alt"></i></button>' +
                  '<button type="button" class="btn btn-sm btn-link p-0 text-muted d-none" ' +
                    'title="Fechar" data-action="close" ' +
                    'style="line-height:1;"><i class="fas fa-times"></i></button>' +
                '</div>' +
              '</div>' +
              '<div class="small text-muted mb-1" data-role="descricao" ' +
                (meta.descricao ? '' : 'style="display:none"') + '>' +
                escapeHtml(meta.descricao || '') +
              '</div>' +
              '<div class="d-flex align-items-center gap-2">' +
                '<div class="spinner-border spinner-border-sm text-warning" data-role="spinner"></div>' +
                '<div class="small flex-grow-1" data-role="etapa">Iniciando…</div>' +
              '</div>' +
              '<div class="progress mt-1" style="height:4px;">' +
                '<div class="progress-bar progress-bar-striped progress-bar-animated bg-warning" ' +
                    'role="progressbar" data-role="bar" style="width:5%"></div>' +
              '</div>' +
              '<div class="small text-danger mt-1 d-none" data-role="erro"></div>' +
              '<div class="small text-success mt-1 d-none" data-role="sucesso"></div>' +
            '</div>'
        );

        // Handlers
        card.querySelector('[data-action="toggle-min"]').addEventListener('click', function() {
            var c = document.getElementById('ssw-progress-container');
            var min = localStorage.getItem(MINIMIZED_KEY) !== '1';
            localStorage.setItem(MINIMIZED_KEY, min ? '1' : '0');
            aplicarEstadoMinimizado(c);
        });
        card.querySelector('[data-action="close"]').addEventListener('click', function() {
            fechar(meta.id);
        });

        return card;
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function atualizarCard(meta, dados, progresso) {
        var card = document.getElementById('ssw-progress-' + meta.id);
        if (!card) return;

        var etapaEl = card.querySelector('[data-role="etapa"]');
        var barEl = card.querySelector('[data-role="bar"]');
        var erroEl = card.querySelector('[data-role="erro"]');
        var sucessoEl = card.querySelector('[data-role="sucesso"]');
        var spinnerEl = card.querySelector('[data-role="spinner"]');
        var closeBtn = card.querySelector('[data-action="close"]');

        etapaEl.textContent = dados.etapaLabel || 'Processando…';
        if (typeof progresso === 'number') {
            barEl.style.width = Math.max(5, Math.min(100, progresso)) + '%';
        }

        if (dados.status === 'SUCESSO' || dados.status === 'OK' ||
            dados.status === 'CORRIGIDO' || dados.status === 'EXTRAIDO' ||
            dados.status === 'finished') {
            spinnerEl.classList.add('d-none');
            barEl.classList.remove('progress-bar-animated');
            barEl.classList.remove('bg-warning');
            barEl.classList.add('bg-success');
            barEl.style.width = '100%';
            card.classList.remove('border-warning');
            card.classList.add('border-success');
            sucessoEl.classList.remove('d-none');
            sucessoEl.textContent = dados.mensagemSucesso || 'Concluído.';
            closeBtn.classList.remove('d-none');
        } else if (dados.status === 'ERRO' || dados.status === 'failed' ||
                   dados.status === 'SKIPPED') {
            spinnerEl.classList.add('d-none');
            barEl.classList.remove('progress-bar-animated');
            barEl.classList.remove('bg-warning');
            barEl.classList.add('bg-danger');
            barEl.style.width = '100%';
            card.classList.remove('border-warning');
            card.classList.add('border-danger');
            erroEl.classList.remove('d-none');
            erroEl.textContent = dados.erro || dados.mensagemErro || 'Erro na operação.';
            closeBtn.classList.remove('d-none');
        }
    }

    // ─────────────── Mapeamento de status ───────────────

    function normalizar(statusType, resp) {
        // Retorna { status, etapaLabel, erro?, mensagemSucesso?, progresso? }
        var labels = ETAPAS_LABEL[statusType] || {};

        if (statusType === 'emissao_cte' || statusType === 'emissao_cte_comp') {
            var status = resp.status;
            var etapa = resp.etapa;
            var etapaLabel = labels[etapa] || etapa || 'Processando…';

            // Progresso estimado por etapa (emissao_cte tem mais etapas)
            var ordem = (statusType === 'emissao_cte')
                ? ['LOGIN', 'PREENCHIMENTO', 'SEFAZ', 'CONSULTA_101',
                   'IMPORTACAO_CTE', 'FATURA_437', 'IMPORTACAO_FAT']
                : ['PREENCHIMENTO', 'SEFAZ', 'CONSULTA_101'];
            var idx = ordem.indexOf(etapa);
            var progresso = idx >= 0
                ? Math.round(((idx + 0.5) / ordem.length) * 100)
                : 10;

            if (status === 'SUCESSO') progresso = 100;

            var mensagemSucesso = '';
            if (status === 'SUCESSO') {
                if (resp.ctrc) mensagemSucesso = 'CTRC ' + resp.ctrc + ' emitido.';
                else mensagemSucesso = 'Operação concluída.';
                if (resp.fatura_numero) mensagemSucesso += ' Fatura ' + resp.fatura_numero + '.';
            }

            return {
                status: status,
                etapaLabel: etapaLabel,
                progresso: progresso,
                erro: resp.erro,
                mensagemSucesso: mensagemSucesso,
            };
        }

        if (statusType === 'rq_job') {
            var s = resp.status;
            var label = labels[s] || s || 'Processando…';
            var progresso = 10;
            if (s === 'queued') progresso = 10;
            else if (s === 'started') progresso = 50;
            else if (s === 'finished') progresso = 100;
            else if (s === 'failed') progresso = 100;

            var msg = '';
            if (s === 'finished' && resp.result) {
                var r = resp.result;
                if (r.status === 'CORRIGIDO' && r.ctrc_novo) {
                    msg = 'CTRC atualizado: ' + r.ctrc_novo + '.';
                } else if (r.status === 'EXTRAIDO' && r.ctrc_novo) {
                    msg = 'CTRC extraído: ' + r.ctrc_novo + '.';
                } else if (r.status === 'OK') {
                    msg = 'CTRC já estava correto' + (r.cte_pdf_path ? ' (PDF atualizado)' : '') + '.';
                } else if (r.status === 'SUCESSO' && r.cte_pdf_path) {
                    msg = 'PDF DACTE baixado com sucesso.';
                } else {
                    msg = 'Concluído.';
                }
            }

            return {
                status: s === 'finished' ? (resp.result && resp.result.status === 'ERRO' ? 'ERRO' : 'SUCESSO') : s,
                etapaLabel: label,
                progresso: progresso,
                erro: resp.erro || (resp.result && resp.result.erro),
                mensagemSucesso: msg,
            };
        }

        // Fallback
        return {
            status: resp.status,
            etapaLabel: resp.etapa || resp.status || 'Processando…',
            progresso: 20,
            erro: resp.erro,
        };
    }

    // ─────────────── Core ───────────────

    function gerarId() {
        return 'op_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 5);
    }

    function start(opts) {
        if (!opts || !opts.statusUrl) {
            console.warn('SswProgress.start: statusUrl obrigatorio');
            return null;
        }

        var meta = {
            id: opts.id || gerarId(),
            label: opts.label || 'Operação SSW',
            descricao: opts.descricao || '',
            statusUrl: opts.statusUrl,
            statusType: opts.statusType || 'emissao_cte',
            intervalMs: opts.intervalMs || POLL_DEFAULT_MS,
            onDone: opts.onDone,   // nao serializado — apenas sessao atual
            onError: opts.onError,
            reloadOnDone: opts.reloadOnDone !== false, // default true
            criadoEm: Date.now(),
        };

        // Se ja existe, nao duplicar
        if (ativas[meta.id]) return meta.id;

        var container = garantirContainer();
        var card = criarCard(meta);
        container.appendChild(card);

        ativas[meta.id] = { meta: meta, interval: null };
        salvarPersistido();

        // Primeiro tick imediato + polling
        var executarTick = function() {
            fetch(meta.statusUrl, {headers: {'Accept': 'application/json'}})
                .then(function(r) { return r.json().then(function(d) { return {status: r.status, data: d}; }); })
                .then(function(resp) {
                    // 404 + status='not_found' significa que o job RQ expirou
                    // do Redis (TTL). O job JA TERMINOU — apenas o registro foi
                    // evicted. Tratamos como conclusao bem-sucedida (estado
                    // final foi persistido no banco pelo proprio worker).
                    if (resp.status === 404 && resp.data && resp.data.status === 'not_found') {
                        atualizarCard(meta, {
                            status: 'SUCESSO',
                            mensagemSucesso: 'Concluído (job expirou do cache).',
                        }, 100);
                        pararPolling(meta.id, true);
                        if (meta.onDone) { try { meta.onDone(resp.data); } catch (e) {} }
                        if (meta.reloadOnDone) {
                            setTimeout(function() {
                                fechar(meta.id);
                                location.reload();
                            }, 2500);
                        }
                        return;
                    }
                    if (resp.status >= 400) {
                        atualizarCard(meta, {status: 'ERRO', erro: (resp.data && resp.data.erro) || ('HTTP ' + resp.status)});
                        pararPolling(meta.id, false);
                        if (meta.onError) { try { meta.onError(resp.data); } catch (e) {} }
                        return;
                    }
                    var dados = normalizar(meta.statusType, resp.data);
                    atualizarCard(meta, dados, dados.progresso);

                    // Estados terminais. SKIPPED em emissao_cte/emissao_cte_comp
                    // vai para o branch de ERRO (nada foi emitido), enquanto
                    // SKIPPED dentro de resp.result.status (rq_job) ja foi
                    // convertido em 'SUCESSO' por normalizar().
                    var terminaisSucesso = ['SUCESSO', 'OK', 'CORRIGIDO', 'EXTRAIDO', 'finished'];
                    var terminaisErro = ['ERRO', 'failed', 'SKIPPED'];
                    var estado = dados.status;

                    if (terminaisSucesso.indexOf(estado) >= 0) {
                        pararPolling(meta.id, true);
                        if (meta.onDone) { try { meta.onDone(resp.data); } catch (e) {} }
                        if (meta.reloadOnDone) {
                            setTimeout(function() {
                                fechar(meta.id);
                                location.reload();
                            }, 2500);
                        }
                    } else if (terminaisErro.indexOf(estado) >= 0) {
                        pararPolling(meta.id, false);
                        if (meta.onError) { try { meta.onError(resp.data); } catch (e) {} }
                    }
                })
                .catch(function(err) {
                    // Erro de rede — nao para polling, mostra warning
                    console.warn('SswProgress poll falhou:', err);
                });
        };

        ativas[meta.id].interval = setInterval(executarTick, meta.intervalMs);
        executarTick();  // imediato

        return meta.id;
    }

    function pararPolling(id, manter) {
        var a = ativas[id];
        if (!a) return;
        if (a.interval) clearInterval(a.interval);
        a.interval = null;
        a.meta._finalizado = true;
        salvarPersistido();
    }

    function fechar(id) {
        var a = ativas[id];
        if (!a) return;
        if (a.interval) clearInterval(a.interval);
        var card = document.getElementById('ssw-progress-' + id);
        if (card && card.parentNode) card.parentNode.removeChild(card);
        delete ativas[id];
        salvarPersistido();
    }

    // TTL de restauracao: entradas mais antigas que isso sao descartadas
    // (RQ job_timeout default=10min, result_ttl=24h; acima de 30min o
    // tracker ja perdeu valor e apenas geraria ruido/404 repetidos).
    var MAX_AGE_RESTORE_MS = 30 * 60 * 1000;

    function restaurarPersistidos() {
        var pendentes = carregarPersistido();
        var agora = Date.now();
        pendentes.forEach(function(meta) {
            // Skip entradas antigas (usuario fechou browser sem terminar).
            // Sem esse guard, cada page load re-ativaria polls que batem 404
            // permanentemente contra jobs ha muito expirados.
            if (!meta.criadoEm || (agora - meta.criadoEm) > MAX_AGE_RESTORE_MS) {
                return;
            }
            // Reinicia polling (sem callbacks originais — so tracking visual)
            start({
                id: meta.id,
                label: meta.label,
                descricao: meta.descricao,
                statusUrl: meta.statusUrl,
                statusType: meta.statusType,
                intervalMs: meta.intervalMs,
                reloadOnDone: false,  // ja reload-ou antes
            });
        });

        // Cleanup: reescreve localStorage sem entradas descartadas.
        // `salvarPersistido` filtra por _finalizado=true, entao precisamos
        // remover explicitamente as stale (que nao estao em ativas).
        try {
            var vivos = Object.keys(ativas).map(function(k) { return ativas[k].meta; });
            localStorage.setItem(STORAGE_KEY, JSON.stringify(vivos));
        } catch (e) {}
    }

    // ─────────────── API publica ───────────────

    window.SswProgress = {
        start: start,
        fechar: fechar,
        restaurar: restaurarPersistidos,
    };

    // Auto-restaurar pendentes quando DOM pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', restaurarPersistidos);
    } else {
        restaurarPersistidos();
    }
})(window, document);
