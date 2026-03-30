/**
 * lista-alertas.js — Alertas de separacoes COTADAS alteradas
 * Extraido de lista_pedidos.html (Script Block 1 + Block 4)
 */

// Carregar alertas de separacoes
function carregarAlertasSeparacoes() {
    const container = document.getElementById('alertasContainer');
    if (!container) return;

    fetch('/api/alertas-separacao/card-html')
        .then(response => {
            if (response.status === 401 || response.status === 302) return null;
            if (response.status === 204) return '';
            return response.text();
        })
        .then(html => {
            if (html === null) return;
            if (html && html.length > 0) {
                container.innerHTML = html;
            }
        })
        .catch(error => {
            console.error('[ALERTAS] Erro ao carregar alertas:', error);
        });
}

// Reimprimir separacao (chamado via onclick no HTML injetado)
function reimprimirSeparacao(separacaoLoteId, numPedido) {
    if (!confirm('Confirma a reimpressao da separacao do pedido ' + numPedido + '?')) {
        return;
    }

    fetch('/api/alertas-separacao/reimprimir/' + separacaoLoteId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ num_pedido: numPedido })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            if (data.url_impressao && data.url_impressao !== '#') {
                window.open(data.url_impressao, '_blank');
                alert('Separacao marcada como reimpressa. ' + data.alertas_marcados + ' alertas processados.');
                setTimeout(function() { location.reload(); }, 2000);
            } else {
                alert('Erro: URL de impressao nao encontrada.');
            }
        } else {
            alert('Erro ao reimprimir: ' + data.error);
        }
    })
    .catch(function(error) {
        alert('Erro ao processar reimpressao: ' + error.message);
    });
}

// Inicializar ao carregar
document.addEventListener('DOMContentLoaded', function() {
    carregarAlertasSeparacoes();
});
