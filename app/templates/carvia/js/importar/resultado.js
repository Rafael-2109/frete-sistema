(function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content
                   || document.querySelector('input[name="csrf_token"]')?.value
                   || '';

    const importacaoChave = CARVIA_DATA.importacaoChave;

    // Campos numericos que devem ser convertidos a float
    const camposNumericos = [
        'valor_total', 'peso_bruto', 'peso_liquido', 'cte_valor', 'quantidade_volumes',
        'quantidade', 'valor_unitario', 'valor_total_item', 'valor_mercadoria', 'peso_kg', 'frete',
    ];

    function parseNumero(campo, valor) {
        if (camposNumericos.includes(campo)) {
            var parsed = parseFloat(valor.replace(',', '.'));
            return isNaN(parsed) ? null : parsed;
        }
        return valor;
    }

    // --- Click-to-edit em celulas da tabela principal ---
    document.querySelectorAll('.carvia-preview-row .carvia-editable-cell').forEach(function(cell) {
        cell.style.cursor = 'pointer';
        cell.addEventListener('click', function(e) {
            e.stopPropagation();
            if (cell.querySelector('.carvia-cell-editor')) return;
            var row = cell.closest('.carvia-preview-row');
            if (!row || row.classList.contains('carvia-preview-removed')) return;

            var campo = cell.dataset.campo;
            var valorAtual = cell.textContent.trim().replace(/^R\$\s*/, '').replace(/\s*kg$/, '');
            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'carvia-cell-editor';
            input.value = valorAtual === '-' ? '' : valorAtual;
            cell.textContent = '';
            cell.appendChild(input);
            input.focus();
            input.select();

            function salvar() {
                var novoValor = input.value.trim();
                cell.textContent = novoValor || '-';
                cell.classList.add('carvia-cell-saved');
                setTimeout(function() { cell.classList.remove('carvia-cell-saved'); }, 600);

                fetch('/carvia/api/importacao/editar-item', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                    body: JSON.stringify({
                        importacao_chave: importacaoChave,
                        tipo: row.dataset.tipo,
                        indice: parseInt(row.dataset.indice),
                        campo: campo,
                        valor: parseNumero(campo, novoValor),
                    }),
                }).then(function(r) { return r.json(); }).then(function(data) {
                    if (!data.sucesso) {
                        cell.classList.add('carvia-cell-error');
                        setTimeout(function() { cell.classList.remove('carvia-cell-error'); }, 600);
                    }
                });
            }

            input.addEventListener('blur', salvar);
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
                if (e.key === 'Escape') { cell.textContent = valorAtual; }
            });
        });
    });

    // --- Click-to-edit em campos de detalhe expandido ---
    document.querySelectorAll('.carvia-detail-field').forEach(function(cell) {
        cell.style.cursor = 'pointer';
        cell.addEventListener('click', function(e) {
            e.stopPropagation();
            if (cell.querySelector('.carvia-cell-editor')) return;

            var campo = cell.dataset.campo;
            var tipo = cell.dataset.tipo;
            var indice = parseInt(cell.dataset.indice);
            var valorAtual = cell.textContent.trim();
            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'carvia-cell-editor form-control form-control-sm';
            input.value = valorAtual === '-' ? '' : valorAtual;
            cell.textContent = '';
            cell.appendChild(input);
            input.focus();
            input.select();

            function salvar() {
                var novoValor = input.value.trim();
                cell.textContent = novoValor || '-';
                cell.classList.add('carvia-cell-saved');
                setTimeout(function() { cell.classList.remove('carvia-cell-saved'); }, 600);

                fetch('/carvia/api/importacao/editar-item', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                    body: JSON.stringify({
                        importacao_chave: importacaoChave,
                        tipo: tipo,
                        indice: indice,
                        campo: campo,
                        valor: parseNumero(campo, novoValor),
                    }),
                }).then(function(r) { return r.json(); }).then(function(data) {
                    if (!data.sucesso) {
                        cell.classList.add('carvia-cell-error');
                        setTimeout(function() { cell.classList.remove('carvia-cell-error'); }, 600);
                    }
                });
            }

            input.addEventListener('blur', salvar);
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
                if (e.key === 'Escape') { cell.textContent = valorAtual; }
            });
        });
    });

    // --- Click-to-edit em sub-itens (itens NF, itens fatura) ---
    document.querySelectorAll('.carvia-sub-edit').forEach(function(cell) {
        cell.style.cursor = 'pointer';
        cell.addEventListener('click', function(e) {
            e.stopPropagation();
            if (cell.querySelector('.carvia-cell-editor')) return;

            var subRow = cell.closest('.carvia-sub-item-row');
            var container = cell.closest('.carvia-sub-items-container');
            if (!subRow || !container) return;

            var campo = cell.dataset.campo;
            var tipo = container.dataset.tipo;
            var indice = parseInt(container.dataset.indice);
            var subTipo = container.dataset.subTipo;
            var subIndice = parseInt(subRow.dataset.subIndice);
            var valorAtual = cell.textContent.trim();

            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'carvia-cell-editor';
            input.style.width = '100%';
            input.value = valorAtual === '-' ? '' : valorAtual;
            cell.textContent = '';
            cell.appendChild(input);
            input.focus();
            input.select();

            function salvar() {
                var novoValor = input.value.trim();
                cell.textContent = novoValor || '-';
                cell.classList.add('carvia-cell-saved');
                setTimeout(function() { cell.classList.remove('carvia-cell-saved'); }, 600);

                fetch('/carvia/api/importacao/editar-item-detalhe', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                    body: JSON.stringify({
                        importacao_chave: importacaoChave,
                        tipo: tipo,
                        indice: indice,
                        sub_tipo: subTipo,
                        sub_indice: subIndice,
                        campo: campo,
                        valor: parseNumero(campo, novoValor),
                    }),
                }).then(function(r) { return r.json(); }).then(function(data) {
                    if (!data.sucesso) {
                        cell.classList.add('carvia-cell-error');
                        setTimeout(function() { cell.classList.remove('carvia-cell-error'); }, 600);
                    }
                });
            }

            input.addEventListener('blur', salvar);
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
                if (e.key === 'Escape') { cell.textContent = valorAtual; }
            });
        });
    });

    // --- Adicionar sub-item ---
    document.querySelectorAll('.carvia-add-sub-item-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tipo = btn.dataset.tipo;
            var indice = parseInt(btn.dataset.indice);
            var subTipo = btn.dataset.subTipo;

            fetch('/carvia/api/importacao/adicionar-item-detalhe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    tipo: tipo,
                    indice: indice,
                    sub_tipo: subTipo,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                if (data.sucesso) {
                    // Recarregar pagina para mostrar novo item
                    location.reload();
                } else {
                    alert('Erro: ' + (data.erro || 'desconhecido'));
                }
            });
        });
    });

    // --- Remover sub-item ---
    document.querySelectorAll('.carvia-remove-sub-item-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (!confirm('Remover este item?')) return;

            var subRow = btn.closest('.carvia-sub-item-row');
            var container = btn.closest('.carvia-sub-items-container');
            if (!subRow || !container) return;

            var tipo = container.dataset.tipo;
            var indice = parseInt(container.dataset.indice);
            var subTipo = container.dataset.subTipo;
            var subIndice = parseInt(subRow.dataset.subIndice);

            fetch('/carvia/api/importacao/remover-item-detalhe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    tipo: tipo,
                    indice: indice,
                    sub_tipo: subTipo,
                    sub_indice: subIndice,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                if (data.sucesso) {
                    subRow.remove();
                    // Re-indexar sub-indices
                    container.querySelectorAll('.carvia-sub-item-row').forEach(function(r, i) {
                        r.dataset.subIndice = i;
                    });
                } else {
                    alert('Erro: ' + (data.erro || 'desconhecido'));
                }
            });
        });
    });

    // --- Remover item principal ---
    document.querySelectorAll('.carvia-preview-remove-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var row = btn.closest('.carvia-preview-row');
            if (!row) return;
            if (!confirm('Remover este item do preview?')) return;

            row.classList.add('carvia-preview-removed');
            btn.disabled = true;

            fetch('/carvia/api/importacao/remover-item', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    tipo: row.dataset.tipo,
                    indice: parseInt(row.dataset.indice),
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                if (data.sucesso) {
                    var tipo = row.dataset.tipo;
                    var cardMap = {nf: 0, cte: 1, fatura: 2};
                    var cards = document.querySelectorAll('.card.border-primary h3, .card.border-info h3, .card.border-warning h3');
                    var idx = cardMap[tipo];
                    if (cards[idx]) cards[idx].textContent = data.restantes;
                    // Tambem ocultar linha expandida se existir
                    var detailRow = row.nextElementSibling;
                    if (detailRow && detailRow.classList.contains('collapse')) {
                        detailRow.remove();
                    }
                    // Re-indexar
                    var rows = document.querySelectorAll('.carvia-preview-row[data-tipo="' + tipo + '"]:not(.carvia-preview-removed)');
                    rows.forEach(function(r, i) { r.dataset.indice = i; });
                } else {
                    row.classList.remove('carvia-preview-removed');
                    btn.disabled = false;
                    alert('Erro ao remover: ' + (data.erro || 'desconhecido'));
                }
            });
        });
    });

    // --- Reclassificar CTe ---
    document.querySelectorAll('.carvia-cte-classificacao').forEach(function(sel) {
        sel.addEventListener('change', function() {
            var indice = parseInt(sel.dataset.indice);
            fetch('/carvia/api/importacao/reclassificar-cte', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    indice: indice,
                    nova_classificacao: sel.value,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                if (data.sucesso) {
                    sel.classList.add('carvia-cell-saved');
                    setTimeout(function() { sel.classList.remove('carvia-cell-saved'); }, 600);
                }
            });
        });
    });

    // --- Reclassificar Fatura (CLIENTE / TRANSPORTADORA) ---
    document.querySelectorAll('.carvia-fatura-reclassificacao').forEach(function(sel) {
        sel.addEventListener('change', function() {
            var indice = parseInt(sel.dataset.indice);
            fetch('/carvia/api/importacao/reclassificar-fatura', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    indice: indice,
                    novo_tipo: sel.value,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                if (data.sucesso) {
                    sel.classList.add('carvia-cell-saved');
                    setTimeout(function() { sel.classList.remove('carvia-cell-saved'); }, 600);
                }
            });
        });
    });

    // --- Viewer de documento fonte ---
    document.querySelectorAll('.carvia-preview-doc-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tipo = btn.dataset.tipo;
            var indice = btn.dataset.indice;
            var url = '/carvia/api/importacao/documento?importacao_chave=' +
                      encodeURIComponent(importacaoChave) +
                      '&tipo=' + encodeURIComponent(tipo) +
                      '&indice=' + encodeURIComponent(indice);
            document.getElementById('docViewerIframe').src = url;
            var modal = new bootstrap.Modal(document.getElementById('modalDocViewer'));
            modal.show();
        });
    });

    // GAP-30: Debounce --- desabilitar botao apos primeiro clique
    var formConfirmar = document.getElementById('form-confirmar-importacao');
    if (formConfirmar) {
        formConfirmar.addEventListener('submit', function(e) {
            var btn = document.getElementById('btn-confirmar-importacao');
            if (btn.dataset.submitted === 'true') {
                e.preventDefault();
                return false;
            }
            btn.dataset.submitted = 'true';
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
        });
    }

    // Preencher modal com dados do botao
    document.querySelectorAll('.transportadora-cadastrar-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var cnpj = this.dataset.cnpj;
            var cnpjFmt = cnpj.length === 14
                ? cnpj.slice(0,2) + '.' + cnpj.slice(2,5) + '.' + cnpj.slice(5,8) + '/' + cnpj.slice(8,12) + '-' + cnpj.slice(12)
                : cnpj;
            document.getElementById('modal-transp-cnpj').value = cnpjFmt;
            document.getElementById('modal-transp-cnpj').dataset.cnpjDigits = cnpj;
            document.getElementById('modal-transp-razao').value = this.dataset.nome || '';
            document.getElementById('modal-transp-cidade').value = this.dataset.cidade || '';
            document.getElementById('modal-transp-uf').value = this.dataset.uf || '';
            document.getElementById('modal-transp-freteiro').checked = false;
            document.getElementById('modal-transp-erro').classList.add('d-none');
            document.getElementById('modal-transp-sucesso').classList.add('d-none');
            document.getElementById('modal-transp-salvar').disabled = false;
            document.getElementById('modal-transp-salvar').innerHTML = '<i class="fas fa-save"></i> Cadastrar';
        });
    });

    // Salvar transportadora via AJAX
    document.getElementById('modal-transp-salvar')?.addEventListener('click', async function() {
        var btn = this;
        var cnpj = document.getElementById('modal-transp-cnpj').dataset.cnpjDigits;
        var razao = document.getElementById('modal-transp-razao').value.trim();
        var cidade = document.getElementById('modal-transp-cidade').value.trim();
        var uf = document.getElementById('modal-transp-uf').value;
        var freteiro = document.getElementById('modal-transp-freteiro').checked;

        if (!razao || !cidade || !uf) {
            document.getElementById('modal-transp-erro').textContent = 'Preencha todos os campos obrigatorios.';
            document.getElementById('modal-transp-erro').classList.remove('d-none');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        try {
            var resp = await fetch('/carvia/api/cadastrar-transportadora', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({cnpj: cnpj, razao_social: razao, cidade: cidade, uf: uf, freteiro: freteiro}),
            });
            var data = await resp.json();

            if (data.sucesso) {
                document.getElementById('modal-transp-sucesso').textContent =
                    'Transportadora "' + data.transportadora.razao_social + '" cadastrada com sucesso!';
                document.getElementById('modal-transp-sucesso').classList.remove('d-none');
                document.getElementById('modal-transp-erro').classList.add('d-none');

                document.querySelectorAll('[id="badge-transp-' + cnpj + '"]').forEach(function(badge) {
                    badge.className = 'badge bg-success';
                    badge.innerHTML = '<i class="fas fa-check"></i> ' + data.transportadora.razao_social;
                });

                var cadastrarBtn = document.getElementById('btn-transp-' + cnpj);
                if (cadastrarBtn) {
                    cadastrarBtn.classList.replace('btn-outline-warning', 'btn-outline-success');
                    cadastrarBtn.disabled = true;
                    cadastrarBtn.innerHTML = '<i class="fas fa-check"></i> ' + data.transportadora.razao_social + ' — Cadastrada';
                }

                setTimeout(function() {
                    var modal = bootstrap.Modal.getInstance(document.getElementById('modalCadastrarTransportadora'));
                    if (modal) modal.hide();
                }, 1500);
            } else {
                document.getElementById('modal-transp-erro').textContent = data.erro || 'Erro ao cadastrar.';
                document.getElementById('modal-transp-erro').classList.remove('d-none');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save"></i> Cadastrar';
            }
        } catch (e) {
            document.getElementById('modal-transp-erro').textContent = 'Erro de conexao: ' + e.message;
            document.getElementById('modal-transp-erro').classList.remove('d-none');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Cadastrar';
        }
    });

    // ─── CTe Complementar: vinculo de Custo Entrega ─────────────────────────
    // Dropdown que selecionar o Custo Entrega para vincular ao CTe Comp.
    // Dispara API que valida + persiste no Redis.
    document.querySelectorAll('.carvia-cte-comp-custo-select').forEach(function(select) {
        select.addEventListener('change', function() {
            var indice = parseInt(select.dataset.indice);
            var custoIdRaw = select.value;
            var custoId = custoIdRaw === '' ? null : parseInt(custoIdRaw);

            select.disabled = true;
            fetch('/carvia/api/importacao/selecionar-custo-entrega-cte-comp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    indice: indice,
                    custo_entrega_id: custoId,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                select.disabled = false;
                if (data.sucesso) {
                    select.classList.add('is-valid');
                    setTimeout(function() { select.classList.remove('is-valid'); }, 1500);
                } else {
                    select.classList.add('is-invalid');
                    alert('Erro ao vincular Custo Entrega: ' + (data.erro || 'desconhecido'));
                    setTimeout(function() { select.classList.remove('is-invalid'); }, 2500);
                }
            }).catch(function(err) {
                select.disabled = false;
                select.classList.add('is-invalid');
                alert('Erro de conexao: ' + err.message);
            });
        });
    });

    // ─── CTe Complementar: edicao do CTRC via input ─────────────────────────
    // Reusa a API generica /api/importacao/editar-item (campo='ctrc_numero').
    document.querySelectorAll('.carvia-cte-comp-ctrc').forEach(function(input) {
        input.addEventListener('change', function() {
            var indice = parseInt(input.dataset.indice);
            var novoValor = input.value.trim() || null;

            fetch('/carvia/api/importacao/editar-item', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    tipo: 'cte',
                    indice: indice,
                    campo: 'ctrc_numero',
                    valor: novoValor,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                if (data.sucesso) {
                    input.classList.add('is-valid');
                    setTimeout(function() { input.classList.remove('is-valid'); }, 1500);
                } else {
                    input.classList.add('is-invalid');
                    setTimeout(function() { input.classList.remove('is-invalid'); }, 2500);
                }
            });
        });
    });

    // ─── CTe Complementar: botao "Verificar SSW" ────────────────────────────
    // Marca/desmarca o flag verificar_ctrc_ssw no preview. Quando o usuario
    // confirmar a importacao, o salvar_importacao enfileira job RQ background
    // que consulta SSW opcao 101 e atualiza ctrc_numero se divergir.
    document.querySelectorAll('.carvia-verificar-ctrc-ssw-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var indice = parseInt(btn.dataset.indice);
            var jaAtivo = btn.classList.contains('active');
            var marcar = !jaAtivo;

            btn.disabled = true;
            fetch('/carvia/api/importacao/marcar-verificar-ctrc-ssw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    importacao_chave: importacaoChave,
                    indice: indice,
                    verificar: marcar,
                }),
            }).then(function(r) { return r.json(); }).then(function(data) {
                btn.disabled = false;
                if (data.sucesso) {
                    if (marcar) {
                        btn.classList.add('active', 'btn-info');
                        btn.classList.remove('btn-outline-info');
                    } else {
                        btn.classList.remove('active', 'btn-info');
                        btn.classList.add('btn-outline-info');
                    }
                } else {
                    alert('Erro: ' + (data.erro || 'desconhecido'));
                }
            }).catch(function(err) {
                btn.disabled = false;
                alert('Erro de conexao: ' + err.message);
            });
        });
    });
})();
