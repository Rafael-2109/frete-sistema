/**
 * lista-modais.js — Handlers dos modais de separacao
 * Extraido de lista_pedidos.html (Script Block 2 + Block 4 cancelamento)
 */

// Globais compartilhadas (acessadas por outros modulos)
window.loteIdAtual = null;
window.loteParaCancelar = null;

function abrirModalInfoSeparacao(loteId) {
    window.loteIdAtual = loteId;

    fetch('/pedidos/api/info_separacao/' + loteId)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                document.getElementById('info_num_pedido').textContent = data.num_pedido;
                document.getElementById('info_lote_id').textContent = data.lote_id;
                document.getElementById('info_raz_social').textContent = data.raz_social_red;
                document.getElementById('info_cnpj').textContent = data.cnpj_cpf;

                var statusBadge = document.getElementById('info_status_separado');
                if (data.pedido_separado) {
                    statusBadge.textContent = 'Separacao Impressa';
                    statusBadge.className = 'badge bg-success';
                } else {
                    statusBadge.textContent = 'Nao Impressa';
                    statusBadge.className = 'badge bg-secondary';
                }

                document.getElementById('info_valor_total').textContent = data.totais.valor.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
                document.getElementById('info_qtd_total').textContent = data.totais.qtd.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('info_peso_total').textContent = data.totais.peso.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('info_pallet_total').textContent = data.totais.pallet.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});

                document.getElementById('obs_separacao_input').value = data.obs_separacao || '';

                var isAntecipado = data.cond_pgto && data.cond_pgto.toUpperCase().indexOf('ANTECIPADO') !== -1;

                if (isAntecipado) {
                    document.getElementById('badge_antecipado_container').style.display = 'block';
                    document.getElementById('botoes_antecipado_container').style.display = 'block';

                    var btnPagamento = document.getElementById('btn_pagamento_realizado');
                    if (data.falta_pagamento) {
                        btnPagamento.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Pagamento Pendente';
                        btnPagamento.className = 'btn btn-warning';
                    } else {
                        btnPagamento.innerHTML = '<i class="fas fa-check-circle"></i> Pagamento OK';
                        btnPagamento.className = 'btn btn-success';
                    }
                } else {
                    document.getElementById('badge_antecipado_container').style.display = 'none';
                    document.getElementById('botoes_antecipado_container').style.display = 'none';
                }

                // CarVia: esconder elementos nao aplicaveis
                var ehCarvia = data.eh_carvia || false;
                var colFalta = document.getElementById('col_falta_header');
                if (colFalta) colFalta.style.display = ehCarvia ? 'none' : '';
                var btnImprimir = document.getElementById('btn_imprimir_separacao');
                if (btnImprimir) btnImprimir.style.display = ehCarvia ? 'none' : '';
                var badgeCarvia = document.getElementById('badge_carvia_info');
                if (badgeCarvia) badgeCarvia.style.display = ehCarvia ? 'inline-block' : 'none';

                var tbody = document.getElementById('tabela_itens_separacao');
                tbody.innerHTML = '';

                data.itens.forEach(function(item) {
                    var tr = document.createElement('tr');
                    var faltaCell = ehCarvia ? '' :
                        '<td class="text-center">' +
                        '<button class="btn btn-sm ' + (item.falta_item ? 'btn-danger' : 'btn-outline-secondary') + '" ' +
                        'onclick="toggleFaltaItem(' + item.id + ', this)" style="font-size: 0.7rem;">' +
                        (item.falta_item ? 'Falta' : 'OK') +
                        '</button></td>';
                    tr.innerHTML = '<td><small>' + item.cod_produto + '</small></td>' +
                        '<td><small>' + item.nome_produto + '</small></td>' +
                        '<td class="text-end">' + item.qtd_saldo.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</td>' +
                        '<td class="text-end">' + item.valor_saldo.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'}) + '</td>' +
                        '<td class="text-end">' + item.peso.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</td>' +
                        '<td class="text-end">' + item.pallet.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</td>' +
                        faltaCell;
                    tbody.appendChild(tr);
                });

                var modal = new bootstrap.Modal(document.getElementById('modalInfoSeparacao'));
                modal.show();
            } else {
                alert('Erro ao buscar informacoes: ' + data.message);
            }
        })
        .catch(function(error) {
            console.error('Erro:', error);
            alert('Erro ao buscar informacoes da separacao');
        });
}

function toggleFaltaItem(itemId, button) {
    fetch('/pedidos/api/toggle_falta_item/' + itemId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        }
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            if (data.falta_item) {
                button.className = 'btn btn-sm btn-danger';
                button.textContent = 'Falta';
            } else {
                button.className = 'btn btn-sm btn-outline-secondary';
                button.textContent = 'OK';
            }
        } else {
            alert('Erro ao atualizar item: ' + data.message);
        }
    })
    .catch(function(error) {
        console.error('Erro:', error);
        alert('Erro ao atualizar status do item');
    });
}

function abrirModalMotivoExclusao(loteId) {
    window.loteParaCancelar = loteId;
    document.getElementById('input_motivo_exclusao').value = '';
    var modal = new bootstrap.Modal(document.getElementById('modalMotivoExclusao'));
    modal.show();
}

function salvarObsSeparacao() {
    if (!window.loteIdAtual) {
        alert('Erro: lote nao identificado.');
        return;
    }

    var obs = document.getElementById('obs_separacao_input').value.trim();

    var btn = event.target;
    var textoOriginal = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

    fetch('/pedidos/api/salvar_obs_separacao/' + window.loteIdAtual, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({ obs_separacao: obs })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            alert('Observacoes salvas com sucesso!\n' + data.itens_atualizados + ' item(ns) atualizado(s).');
        } else {
            alert('Erro ao salvar observacoes: ' + data.message);
        }
        btn.disabled = false;
        btn.innerHTML = textoOriginal;
    })
    .catch(function(error) {
        console.error('Erro:', error);
        alert('Erro ao salvar observacoes: ' + error.message);
        btn.disabled = false;
        btn.innerHTML = textoOriginal;
    });
}

function togglePagamento() {
    if (!window.loteIdAtual) {
        alert('Erro: lote nao identificado.');
        return;
    }

    var btn = document.getElementById('btn_pagamento_realizado');
    var isPendente = btn.classList.contains('btn-warning');

    fetch('/pedidos/api/toggle_pagamento/' + window.loteIdAtual, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({ falta_pagamento: !isPendente })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            if (data.falta_pagamento) {
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Pagamento Pendente';
                btn.className = 'btn btn-warning';
            } else {
                btn.innerHTML = '<i class="fas fa-check-circle"></i> Pagamento OK';
                btn.className = 'btn btn-success';
            }
        } else {
            alert('Erro ao atualizar pagamento: ' + data.message);
        }
    })
    .catch(function(error) {
        console.error('Erro:', error);
        alert('Erro ao atualizar status do pagamento');
    });
}

function imprimirSeparacao() {
    if (!window.loteIdAtual) {
        alert('Erro: lote nao identificado.');
        return;
    }
    window.open('/pedidos/imprimir_separacao/' + window.loteIdAtual, '_blank');
}

// Handler do botao confirmar exclusao com motivo (era no Block 4)
document.addEventListener('DOMContentLoaded', function() {
    var btnConfirmarExclusao = document.getElementById('btn_confirmar_exclusao');
    if (btnConfirmarExclusao) {
        btnConfirmarExclusao.addEventListener('click', function() {
            var motivo = document.getElementById('input_motivo_exclusao').value.trim();

            if (!motivo) {
                alert('Por favor, informe o motivo do cancelamento.');
                return;
            }

            if (!window.loteParaCancelar) {
                alert('Erro: lote nao identificado.');
                return;
            }

            if (!confirm('Confirma o cancelamento da separacao ' + window.loteParaCancelar + '?\n\nMotivo: ' + motivo)) {
                return;
            }

            var btnOriginal = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';

            var self = this;
            fetch('/pedidos/cancelar_separacao/' + window.loteParaCancelar, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify({ motivo_exclusao: motivo })
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.success) {
                    alert('Separacao cancelada com sucesso!');
                    var modal = bootstrap.Modal.getInstance(document.getElementById('modalMotivoExclusao'));
                    if (modal) modal.hide();
                    window.location.reload();
                } else {
                    alert('Erro ao cancelar separacao: ' + data.message);
                    self.disabled = false;
                    self.innerHTML = btnOriginal;
                }
            })
            .catch(function(error) {
                console.error('Erro:', error);
                alert('Erro ao cancelar separacao: ' + error.message);
                self.disabled = false;
                self.innerHTML = btnOriginal;
            });
        });
    }
});
