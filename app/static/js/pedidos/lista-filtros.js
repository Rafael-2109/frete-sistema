/**
 * lista-filtros.js — Geracao de URLs com preservacao de filtros
 * Extraido de lista_pedidos.html (linhas 2434-2621)
 * Usa window.PEDIDOS_URLS.listaPedidos (injetado pelo template)
 */

var BASE_URL = ''; // Sera definido por window.PEDIDOS_URLS.listaPedidos

window.sort_url = function(campo) {
    var urlParams = new URLSearchParams(window.location.search);

    var novaOrdem = 'asc';
    if (urlParams.get('sort_by') === campo && urlParams.get('sort_order') === 'asc') {
        novaOrdem = 'desc';
    }

    urlParams.set('sort_by', campo);
    urlParams.set('sort_order', novaOrdem);

    return BASE_URL + '?' + urlParams.toString();
};

window.filtro_url = function(opcoes) {
    opcoes = opcoes || {};
    var urlParams = new URLSearchParams(window.location.search);

    if (opcoes.status !== undefined) {
        if (opcoes.status === null) {
            urlParams.delete('status');
        } else {
            urlParams.set('status', opcoes.status);
        }
    }

    if (opcoes.data !== undefined) {
        if (opcoes.data === null) {
            urlParams.delete('data');
        } else {
            urlParams.set('data', opcoes.data);
        }
    }

    return BASE_URL + '?' + urlParams.toString();
};

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar BASE_URL
    BASE_URL = window.PEDIDOS_URLS ? window.PEDIDOS_URLS.listaPedidos : '/pedidos/lista_pedidos';

    window.templateHelpers = {
        sort_url: window.sort_url,
        filtro_url: window.filtro_url
    };

    function capturarTodosFiltros() {
        var filtros = {};

        var urlParams = new URLSearchParams(window.location.search);
        urlParams.forEach(function(value, key) {
            filtros[key] = value;
        });

        var campos = [
            'numero_pedido', 'cnpj_cpf', 'cliente', 'uf', 'status',
            'rota', 'sub_rota', 'expedicao_inicio', 'expedicao_fim'
        ];

        campos.forEach(function(campo) {
            var elemento = document.getElementById(campo);
            if (elemento && elemento.value) {
                filtros[campo] = elemento.value;
            }
        });

        return filtros;
    }

    function gerarUrlComFiltros(parametrosNovos) {
        parametrosNovos = parametrosNovos || {};
        var filtros = capturarTodosFiltros();

        Object.assign(filtros, parametrosNovos);

        Object.keys(filtros).forEach(function(key) {
            if (filtros[key] === null || filtros[key] === undefined || filtros[key] === '') {
                delete filtros[key];
            }
        });

        var params = new URLSearchParams(filtros);
        return BASE_URL + '?' + params.toString();
    }

    function atualizarLinksOrdenacao() {
        document.querySelectorAll('.sortable a').forEach(function(link) {
            var campo = link.closest('.sortable').dataset.sort;
            if (campo) {
                var filtros = capturarTodosFiltros();

                var novaOrdem = 'asc';
                if (filtros.sort_by === campo && filtros.sort_order === 'asc') {
                    novaOrdem = 'desc';
                }

                link.href = gerarUrlComFiltros({
                    sort_by: campo,
                    sort_order: novaOrdem
                });
            }
        });
    }

    function atualizarBotoesFiltro() {
        document.querySelectorAll('.filtro-status').forEach(function(btn) {
            if (btn.href) {
                var url = new URL(btn.href);
                var status = url.searchParams.get('status');
                btn.href = gerarUrlComFiltros({ status: status });
            }
        });

        document.querySelectorAll('.filtro-data').forEach(function(btn) {
            if (btn.href) {
                var url = new URL(btn.href);
                var data = url.searchParams.get('data');
                var status = url.searchParams.get('status');
                btn.href = gerarUrlComFiltros({ data: data, status: status });
            }
        });

        document.querySelectorAll('.filtro-aberto').forEach(function(btn) {
            if (btn.href) {
                var url = new URL(btn.href);
                var data = url.searchParams.get('data');
                var status = url.searchParams.get('status');
                btn.href = gerarUrlComFiltros({ data: data, status: status });
            }
        });
    }

    atualizarLinksOrdenacao();
    atualizarBotoesFiltro();

    var camposFiltro = document.querySelectorAll('#numero_pedido, #cnpj_cpf, #cliente, #uf, #status, #rota, #sub_rota, #expedicao_inicio, #expedicao_fim');
    camposFiltro.forEach(function(campo) {
        campo.addEventListener('input', function() {
            setTimeout(function() {
                atualizarLinksOrdenacao();
                atualizarBotoesFiltro();
            }, 100);
        });

        campo.addEventListener('change', function() {
            setTimeout(function() {
                atualizarLinksOrdenacao();
                atualizarBotoesFiltro();
            }, 100);
        });
    });

    document.querySelectorAll('.filtro-data, .filtro-aberto, .filtro-status').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = this.href;
        });
    });
});
