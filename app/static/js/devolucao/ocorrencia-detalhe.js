/**
 * Ocorrencia Detalhe - JavaScript
 *
 * Requer variaveis globais definidas no template:
 * - ocorrenciaId
 * - nfdId
 * - ufOrigemPreset
 * - cidadeOrigemPreset
 * - PREFIXO_CNPJ
 */

// =========================================================================
// Variaveis de estado do modulo
// =========================================================================
let modoComparacao = false;
let dadosComparacao = null;
let produtoSelecionadoInfo = null;
let timeoutBuscaProd = null;
let resultadosResolverTodos = [];

// =========================================================================
// Carregar Dados ao Iniciar
// =========================================================================
document.addEventListener('DOMContentLoaded', function() {
    carregarTransportadoras();
    carregarUFs();
    calcularPesoAuto();
    calcularTotalDescarte();

    // Inicializar tooltips do Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) { return new bootstrap.Tooltip(el); });

    // Event listeners para botoes de editar produto
    document.querySelectorAll('.btn-editar-produto').forEach(btn => {
        btn.addEventListener('click', function() {
            const linhaId = this.dataset.linhaId;
            const codigoCliente = this.dataset.codigoCliente || '';
            const descricaoCliente = this.dataset.descricaoCliente || '';
            const quantidade = parseFloat(this.dataset.quantidade) || 0;
            const unidade = this.dataset.unidade || '';
            const codigoInterno = this.dataset.codigoInterno || '';
            const descricaoInterna = this.dataset.descricaoInterna || '';
            const qtdConvertida = this.dataset.qtdConvertida ? parseFloat(this.dataset.qtdConvertida) : null;
            const fatorConversao = this.dataset.fatorConversao ? parseFloat(this.dataset.fatorConversao) : null;

            abrirModalEditarProduto(linhaId, codigoCliente, descricaoCliente, quantidade, unidade, codigoInterno, descricaoInterna, qtdConvertida, fatorConversao);
        });
    });

    // Event listeners para status do frete
    document.querySelectorAll('.status-frete').forEach(select => {
        select.addEventListener('change', function() {
            atualizarStatusFrete(this.dataset.freteId, this.value);
        });
    });

    // Event listeners para status do descarte
    document.querySelectorAll('.status-descarte').forEach(select => {
        select.addEventListener('change', function() {
            atualizarStatusDescarte(this.dataset.descarteId, this.value);
        });
    });

    // Toggle campos de custo descarte
    const temCustoCheckbox = document.getElementById('tem-custo-descarte');
    if (temCustoCheckbox) {
        temCustoCheckbox.addEventListener('change', function() {
            const fields = document.querySelectorAll('.custo-descarte-fields');
            fields.forEach(field => {
                field.classList.toggle('d-none', !this.checked);
            });
        });
    }

    // Fechar dropdown ao clicar fora
    document.addEventListener('click', function(e) {
        if (!e.target.closest('#prod-nosso-codigo') && !e.target.closest('#autocomplete-produtos-aba')) {
            const dropdown = document.getElementById('autocomplete-produtos-aba');
            if (dropdown) dropdown.classList.remove('show');
        }
    });
});

// =========================================================================
// Carregar UFs e Cidades
// =========================================================================
async function carregarUFs() {
    try {
        const response = await fetch('/devolucao/frete/api/ufs');
        const result = await response.json();

        if (result.sucesso) {
            const selectOrigem = document.getElementById('uf_origem');
            const selectDestino = document.getElementById('uf_destino');

            selectOrigem.innerHTML = '<option value="">UF</option>';
            result.ufs.forEach(uf => {
                const option = document.createElement('option');
                option.value = uf;
                option.textContent = uf;
                if (uf === ufOrigemPreset) option.selected = true;
                selectOrigem.appendChild(option);
            });

            selectDestino.innerHTML = '<option value="">UF</option>';
            result.ufs.forEach(uf => {
                const option = document.createElement('option');
                option.value = uf;
                option.textContent = uf;
                if (uf === 'SP') option.selected = true;
                selectDestino.appendChild(option);
            });

            if (ufOrigemPreset) {
                await carregarCidades('uf_origem', 'cidade_origem', cidadeOrigemPreset);
            }
            await carregarCidades('uf_destino', 'cidade_destino', 'Santana de Parnaiba');

            selectOrigem.addEventListener('change', function() {
                carregarCidades('uf_origem', 'cidade_origem');
            });

            selectDestino.addEventListener('change', function() {
                carregarCidades('uf_destino', 'cidade_destino');
            });
        }
    } catch (error) {
        console.error('Erro ao carregar UFs:', error);
    }
}

async function carregarCidades(ufSelectId, cidadeSelectId, cidadePreset = null) {
    const ufSelect = document.getElementById(ufSelectId);
    const cidadeSelect = document.getElementById(cidadeSelectId);
    const uf = ufSelect.value;

    if (!uf) {
        cidadeSelect.innerHTML = '<option value="">Selecione UF</option>';
        return;
    }

    try {
        cidadeSelect.innerHTML = '<option value="">Carregando...</option>';

        const response = await fetch(`/devolucao/frete/api/cidades/${uf}`);
        const result = await response.json();

        if (result.sucesso) {
            cidadeSelect.innerHTML = '<option value="">Selecione...</option>';
            result.cidades.forEach(cidade => {
                const option = document.createElement('option');
                option.value = cidade.nome;
                option.textContent = cidade.nome;
                if (cidadePreset && normalizeStr(cidade.nome) === normalizeStr(cidadePreset)) {
                    option.selected = true;
                }
                cidadeSelect.appendChild(option);
            });
        } else {
            cidadeSelect.innerHTML = '<option value="">Erro ao carregar</option>';
        }
    } catch (error) {
        console.error('Erro ao carregar cidades:', error);
        cidadeSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

function normalizeStr(str) {
    if (!str) return '';
    return str.toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim();
}

// =========================================================================
// Carregar Transportadoras no Select
// =========================================================================
async function carregarTransportadoras() {
    const select = document.getElementById('select-transportadora');
    if (!select) return;

    try {
        const response = await fetch('/devolucao/frete/api/transportadoras');
        const result = await response.json();

        if (result.sucesso) {
            select.innerHTML = '<option value="">Selecione...</option>';
            result.transportadoras.forEach(t => {
                const option = document.createElement('option');
                option.value = t.nome;
                option.dataset.id = t.id;
                option.dataset.cidade = t.cidade;
                option.dataset.uf = t.uf;
                option.textContent = `${t.nome} (${t.cidade}/${t.uf})`;
                select.appendChild(option);
            });

            select.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const transportadoraId = selectedOption.dataset.id || '';
                document.getElementById('transportadora_id').value = transportadoraId;

                const btnEstimar = document.getElementById('btn-estimar-retorno');
                if (transportadoraId) {
                    btnEstimar.disabled = false;
                    btnEstimar.title = 'Estimar frete de retorno';
                } else {
                    btnEstimar.disabled = true;
                    btnEstimar.title = 'Selecione uma transportadora';
                }
            });
        } else {
            select.innerHTML = '<option value="">Erro ao carregar</option>';
        }
    } catch (error) {
        console.error('Erro ao carregar transportadoras:', error);
        select.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

// =========================================================================
// Calcular Peso
// =========================================================================
async function calcularPeso() {
    const pesoInput = document.getElementById('peso_kg');

    try {
        const response = await fetch(`/devolucao/frete/api/${ocorrenciaId}/calcular-peso`);
        const result = await response.json();

        if (result.sucesso) {
            pesoInput.value = result.peso_total.toFixed(3);

            if (result.detalhes && result.detalhes.length > 0) {
                let mensagem = `Peso total: ${result.peso_total.toFixed(3)} kg\n\nDetalhes:\n`;
                result.detalhes.forEach(d => {
                    mensagem += `- ${d.codigo}: ${d.quantidade} x ${d.peso_unitario.toFixed(3)} = ${d.peso_total.toFixed(3)} kg`;
                    if (!d.cadastro_encontrado) {
                        mensagem += ' (sem cadastro)';
                    }
                    mensagem += '\n';
                });
                alert(mensagem);
            }
        } else {
            alert(result.erro || 'Erro ao calcular peso');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao calcular peso. Verifique se os produtos estao resolvidos.');
    }
}

async function calcularPesoAuto() {
    const pesoInput = document.getElementById('peso_kg');
    if (!pesoInput) return;

    try {
        const response = await fetch(`/devolucao/frete/api/${ocorrenciaId}/calcular-peso`);
        const result = await response.json();

        if (result.sucesso && result.peso_total > 0) {
            pesoInput.value = result.peso_total.toFixed(3);
            console.log(`[Peso Auto] Peso calculado: ${result.peso_total.toFixed(3)} kg`);
        }
    } catch (error) {
        console.log('[Peso Auto] Erro ao calcular peso automaticamente:', error);
    }
}

// =========================================================================
// Estimar Frete de Retorno (50%)
// =========================================================================
// Variavel global para armazenar detalhes do frete estimado
let dadosFreteEstimado = null;

async function estimarFreteRetorno() {
    const transportadoraId = document.getElementById('transportadora_id').value;
    const ufOrigem = document.getElementById('uf_origem').value;
    const btnEstimar = document.getElementById('btn-estimar-retorno');
    const btnVerDetalhes = document.getElementById('btn-ver-detalhes');
    const infoEstimativa = document.getElementById('info-estimativa');
    const valorCotado = document.getElementById('valor_cotado');
    const pesoKg = document.getElementById('peso_kg');

    if (!transportadoraId) {
        alert('Selecione uma transportadora');
        return;
    }

    if (!ufOrigem) {
        alert('Selecione a UF de origem');
        return;
    }

    const textoOriginal = btnEstimar.innerHTML;
    btnEstimar.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    btnEstimar.disabled = true;

    try {
        const response = await fetch(`/devolucao/frete/api/${ocorrenciaId}/estimar-retorno`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify({
                transportadora_id: parseInt(transportadoraId),
                uf_origem: ufOrigem
            })
        });

        const result = await response.json();

        if (result.sucesso) {
            valorCotado.value = result.valor_estimado.toFixed(2);

            if (!pesoKg.value || pesoKg.value === '0') {
                pesoKg.value = result.peso_kg.toFixed(3);
            }

            infoEstimativa.innerHTML = `<i class="bi bi-info-circle"></i> ${result.percentual_nf.toFixed(1)}% NF | R$ ${result.valor_por_kg.toFixed(2)}/kg`;
            infoEstimativa.classList.remove('d-none');
            infoEstimativa.classList.add('text-success');

            // Armazenar dados para o modal de detalhes
            dadosFreteEstimado = {
                transportadora: result.transportadora,
                tabela: result.tabela,
                rota: result.rota,
                peso_kg: result.peso_kg,
                valor_nf: result.valor_nf,
                valor_estimado: result.valor_estimado,
                percentual_nf: result.percentual_nf,
                valor_por_kg: result.valor_por_kg,
                componentes: result.componentes
            };

            // Exibir botao de ver detalhes
            if (btnVerDetalhes && result.componentes) {
                btnVerDetalhes.classList.remove('d-none');
            }

            alert(`Estimativa de Frete de Retorno:\n\n` +
                  `Transportadora: ${result.transportadora}\n` +
                  `Tabela: ${result.tabela}\n` +
                  `Rota: ${result.rota}\n\n` +
                  `Peso: ${result.peso_kg.toFixed(3)} kg\n` +
                  `Valor NF: R$ ${result.valor_nf.toFixed(2)}\n\n` +
                  `Frete Estimado: R$ ${result.valor_estimado.toFixed(2)}\n\n` +
                  `% sobre NF: ${result.percentual_nf.toFixed(2)}%\n` +
                  `R$/kg: R$ ${result.valor_por_kg.toFixed(2)}\n\n` +
                  `Clique em "Ver detalhes" para breakdown completo.`);
        } else {
            alert(result.erro || 'Erro ao estimar frete');
            infoEstimativa.classList.add('d-none');
            if (btnVerDetalhes) btnVerDetalhes.classList.add('d-none');
            dadosFreteEstimado = null;
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao estimar frete. Tente novamente.');
    } finally {
        btnEstimar.innerHTML = textoOriginal;
        btnEstimar.disabled = false;
    }
}

// Funcao para abrir modal de detalhes do frete
function abrirModalDetalhesFrete() {
    if (!dadosFreteEstimado || !dadosFreteEstimado.componentes) {
        alert('Nenhuma estimativa disponivel. Clique em "Estimar" primeiro.');
        return;
    }

    const c = dadosFreteEstimado.componentes;
    const formatarMoeda = (valor) => {
        const num = parseFloat(valor) || 0;
        return 'R$ ' + num.toFixed(2);
    };

    // Preencher informacoes gerais
    document.getElementById('det-transportadora').textContent = dadosFreteEstimado.transportadora;
    document.getElementById('det-tabela').textContent = dadosFreteEstimado.tabela;
    document.getElementById('det-rota').textContent = dadosFreteEstimado.rota;

    // Preencher componentes
    document.getElementById('det-frete-peso').textContent = formatarMoeda(c.frete_peso);
    document.getElementById('det-gris').textContent = formatarMoeda(c.gris);
    document.getElementById('det-adv').textContent = formatarMoeda(c.adv);
    document.getElementById('det-rca').textContent = formatarMoeda(c.rca);
    document.getElementById('det-pedagio').textContent = formatarMoeda(c.pedagio);
    document.getElementById('det-tas').textContent = formatarMoeda(c.tas);
    document.getElementById('det-despacho').textContent = formatarMoeda(c.despacho);
    document.getElementById('det-cte').textContent = formatarMoeda(c.cte);
    document.getElementById('det-subtotal').innerHTML = '<strong>' + formatarMoeda(c.subtotal) + '</strong>';

    // ICMS
    const icmsPerc = c.icms_percentual || 0;
    document.getElementById('det-icms-perc').textContent = icmsPerc.toFixed(1);
    const icmsValor = (c.total || 0) - (c.subtotal || 0);
    document.getElementById('det-icms').textContent = formatarMoeda(icmsValor > 0 ? icmsValor : 0);

    document.getElementById('det-total').innerHTML = '<strong>' + formatarMoeda(c.total) + '</strong>';

    // Indicador de frete minimo
    const infoFreteMinimo = document.getElementById('det-frete-minimo');
    if (c.frete_minimo_aplicado) {
        infoFreteMinimo.classList.remove('d-none');
    } else {
        infoFreteMinimo.classList.add('d-none');
    }

    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('modal-detalhes-frete'));
    modal.show();
}

// =========================================================================
// Salvar Logistica e Comercial
// =========================================================================
function salvarLogistica() {
    const form = document.getElementById('form-logistica');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    fetch(`/devolucao/ocorrencias/api/${ocorrenciaId}/logistica`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const feedback = document.getElementById('feedback-logistica');
        if (result.sucesso) {
            feedback.className = 'alert alert-success';
            feedback.textContent = result.mensagem || 'Salvo com sucesso';
        } else {
            feedback.className = 'alert alert-danger';
            feedback.textContent = result.erro || 'Erro ao salvar';
        }
        feedback.classList.remove('d-none');
        setTimeout(() => feedback.classList.add('d-none'), 3000);
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao salvar. Tente novamente.');
    });
}

function salvarComercial() {
    const form = document.getElementById('form-comercial');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    fetch(`/devolucao/ocorrencias/api/${ocorrenciaId}/comercial`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const feedback = document.getElementById('feedback-comercial');
        if (result.sucesso) {
            feedback.className = 'alert alert-success';
            feedback.textContent = result.mensagem || 'Salvo com sucesso';
        } else {
            feedback.className = 'alert alert-danger';
            feedback.textContent = result.erro || 'Erro ao salvar';
        }
        feedback.classList.remove('d-none');
        setTimeout(() => feedback.classList.add('d-none'), 3000);
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao salvar. Tente novamente.');
    });
}

// =========================================================================
// Funcoes de Anexos
// =========================================================================
function uploadAnexo() {
    const form = document.getElementById('form-upload-anexo');
    const fileInput = document.getElementById('arquivo-anexo');
    const spinner = document.getElementById('spinner-upload');
    const feedback = document.getElementById('feedback-anexo');

    if (!fileInput.files.length) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Selecione um arquivo';
        feedback.classList.remove('d-none');
        return;
    }

    const formData = new FormData(form);

    spinner.classList.remove('d-none');
    feedback.classList.add('d-none');

    fetch(`/devolucao/ocorrencias/api/${ocorrenciaId}/anexos`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: formData
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            feedback.className = 'alert alert-success';
            feedback.textContent = result.mensagem || 'Anexo enviado com sucesso';
            feedback.classList.remove('d-none');
            form.reset();
            setTimeout(() => location.reload(), 1000);
        } else {
            feedback.className = 'alert alert-danger';
            feedback.textContent = result.erro || 'Erro ao enviar anexo';
            feedback.classList.remove('d-none');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        feedback.className = 'alert alert-danger';
        feedback.textContent = 'Erro de conexao. Tente novamente.';
        feedback.classList.remove('d-none');
    })
    .finally(() => {
        spinner.classList.add('d-none');
    });
}

function excluirAnexo(anexoId, nomeAnexo) {
    if (!confirm(`Deseja excluir o anexo "${nomeAnexo}"?`)) {
        return;
    }

    fetch(`/devolucao/ocorrencias/api/${ocorrenciaId}/anexos/${anexoId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            const row = document.getElementById(`anexo-row-${anexoId}`);
            if (row) row.remove();

            const feedback = document.getElementById('feedback-anexo');
            if (feedback) {
                feedback.className = 'alert alert-success';
                feedback.textContent = result.mensagem || 'Anexo excluido';
                feedback.classList.remove('d-none');
                setTimeout(() => feedback.classList.add('d-none'), 3000);
            }
        } else {
            alert(result.erro || 'Erro ao excluir anexo');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao. Tente novamente.');
    });
}

// =========================================================================
// Funcoes de Frete
// =========================================================================
function criarFrete() {
    const form = document.getElementById('form-novo-frete');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    const spinner = document.getElementById('spinner-frete');
    const feedback = document.getElementById('feedback-frete');

    if (!data.transportadora_nome || !data.valor_cotado) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Preencha a transportadora e o valor cotado';
        feedback.classList.remove('d-none');
        return;
    }

    data.transportadora_id = document.getElementById('transportadora_id').value || null;

    spinner.classList.remove('d-none');
    feedback.classList.add('d-none');

    fetch(`/devolucao/frete/api/${ocorrenciaId}/fretes`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            feedback.className = 'alert alert-success';
            feedback.textContent = result.mensagem || 'Cotacao criada com sucesso';
            feedback.classList.remove('d-none');
            form.reset();
            setTimeout(() => location.reload(), 1000);
        } else {
            feedback.className = 'alert alert-danger';
            feedback.textContent = result.erro || 'Erro ao criar cotacao';
            feedback.classList.remove('d-none');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        feedback.className = 'alert alert-danger';
        feedback.textContent = 'Erro de conexao. Tente novamente.';
        feedback.classList.remove('d-none');
    })
    .finally(() => {
        spinner.classList.add('d-none');
    });
}

function excluirFrete(freteId) {
    if (!confirm('Deseja excluir esta cotacao de frete?')) {
        return;
    }

    fetch(`/devolucao/frete/api/frete/${freteId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            const row = document.getElementById(`frete-row-${freteId}`);
            if (row) row.remove();
        } else {
            alert(result.erro || 'Erro ao excluir frete');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao. Tente novamente.');
    });
}

function atualizarStatusFrete(freteId, novoStatus) {
    fetch(`/devolucao/frete/api/frete/${freteId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify({ status: novoStatus })
    })
    .then(response => response.json())
    .then(result => {
        if (!result.sucesso) {
            alert(result.erro || 'Erro ao atualizar status');
            location.reload();
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao');
        location.reload();
    });
}

// =========================================================================
// Funcoes de Descarte
// =========================================================================
function atualizarQtdDescarte(input, tipo) {
    const row = input.closest('tr');
    const qtdPorCaixa = parseFloat(row.dataset.qtdPorCaixa) || 1;
    const valorUnitario = parseFloat(row.dataset.valorUnitario) || 0;
    const qtdOriginal = parseFloat(row.dataset.qtdOriginal) || 0;

    const inputUn = row.querySelector('.qtd-un-descarte');
    const inputCx = row.querySelector('.qtd-cx-descarte');
    const inputValor = row.querySelector('.valor-descarte-linha');

    let qtdUnidades;

    if (tipo === 'un') {
        qtdUnidades = parseFloat(inputUn.value) || 0;
        if (qtdUnidades > qtdOriginal) {
            qtdUnidades = qtdOriginal;
            inputUn.value = qtdUnidades;
        }
        inputCx.value = (qtdUnidades / qtdPorCaixa).toFixed(2);
    } else {
        const qtdCaixas = parseFloat(inputCx.value) || 0;
        qtdUnidades = qtdCaixas * qtdPorCaixa;
        if (qtdUnidades > qtdOriginal) {
            qtdUnidades = qtdOriginal;
            inputCx.value = (qtdUnidades / qtdPorCaixa).toFixed(2);
        }
        inputUn.value = Math.round(qtdUnidades);
    }

    const valorLinha = qtdUnidades * valorUnitario;
    inputValor.value = valorLinha.toFixed(2);

    calcularTotalDescarte();
}

function calcularTotalDescarte() {
    let total = 0;
    document.querySelectorAll('.valor-descarte-linha').forEach(input => {
        total += parseFloat(input.value) || 0;
    });

    const totalElement = document.getElementById('total-valor-descarte');
    if (totalElement) {
        totalElement.textContent = `R$ ${total.toFixed(2)}`;
    }

    const valorMercadoriaInput = document.getElementById('valor_mercadoria_descarte');
    if (valorMercadoriaInput) {
        valorMercadoriaInput.value = total.toFixed(2);
    }
}

function downloadTermoDescarte(descarteId) {
    window.open(`/devolucao/frete/api/descarte/${descarteId}/termo/download`, '_blank');
}

function imprimirTermoDescarte(descarteId) {
    const printWindow = window.open(`/devolucao/frete/api/descarte/${descarteId}/termo/imprimir`, '_blank');
    printWindow.onload = function() {
        printWindow.print();
    };
}

function criarDescarte() {
    const form = document.getElementById('form-novo-descarte');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    const spinner = document.getElementById('spinner-descarte');
    const feedback = document.getElementById('feedback-descarte');

    data.tem_custo = document.getElementById('tem-custo-descarte').checked;

    if (!data.empresa_autorizada_nome || data.empresa_autorizada_nome.trim() === '') {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Informe o nome da empresa autorizada a descartar';
        feedback.classList.remove('d-none');
        return;
    }

    if (!data.empresa_autorizada_documento || data.empresa_autorizada_documento.trim() === '') {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Informe o CNPJ/CPF da empresa autorizada';
        feedback.classList.remove('d-none');
        return;
    }

    if (!data.motivo_descarte) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Selecione o motivo do descarte';
        feedback.classList.remove('d-none');
        return;
    }

    spinner.classList.remove('d-none');
    feedback.classList.add('d-none');

    fetch(`/devolucao/frete/api/${ocorrenciaId}/descartes`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            feedback.className = 'alert alert-success';
            feedback.textContent = result.mensagem || 'Descarte autorizado';
            feedback.classList.remove('d-none');
            form.reset();
            setTimeout(() => location.reload(), 1000);
        } else {
            feedback.className = 'alert alert-danger';
            feedback.textContent = result.erro || 'Erro ao autorizar descarte';
            feedback.classList.remove('d-none');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        feedback.className = 'alert alert-danger';
        feedback.textContent = 'Erro de conexao. Tente novamente.';
        feedback.classList.remove('d-none');
    })
    .finally(() => {
        spinner.classList.add('d-none');
    });
}

function excluirDescarte(descarteId) {
    if (!confirm('Deseja excluir este descarte?')) {
        return;
    }

    fetch(`/devolucao/frete/api/descarte/${descarteId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            const row = document.getElementById(`descarte-row-${descarteId}`);
            if (row) row.remove();
        } else {
            alert(result.erro || 'Erro ao excluir descarte');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao. Tente novamente.');
    });
}

function atualizarStatusDescarte(descarteId, novoStatus) {
    fetch(`/devolucao/frete/api/descarte/${descarteId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify({ status: novoStatus })
    })
    .then(response => response.json())
    .then(result => {
        if (!result.sucesso) {
            alert(result.erro || 'Erro ao atualizar status');
            location.reload();
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao');
        location.reload();
    });
}

// =========================================================================
// Funcoes de Upload de Termo
// =========================================================================
function uploadTermoDescarte(descarteId, tipo) {
    document.getElementById('upload-descarte-id').value = descarteId;
    document.getElementById('upload-tipo-documento').value = tipo;
    document.getElementById('arquivo-termo').value = '';

    const titulos = {
        'termo': 'Upload do Termo de Descarte',
        'termo_assinado': 'Upload do Termo Assinado',
        'comprovante': 'Upload do Comprovante de Descarte'
    };
    document.querySelector('#modal-upload-termo .modal-title').textContent = titulos[tipo] || 'Upload de Documento';

    const modal = new bootstrap.Modal(document.getElementById('modal-upload-termo'));
    modal.show();
}

function enviarTermoDescarte() {
    const fileInput = document.getElementById('arquivo-termo');
    const spinner = document.getElementById('spinner-upload-termo');
    const descarteId = document.getElementById('upload-descarte-id').value;
    const tipo = document.getElementById('upload-tipo-documento').value;

    if (!fileInput.files.length) {
        alert('Selecione um arquivo');
        return;
    }

    const formData = new FormData();
    formData.append('arquivo', fileInput.files[0]);

    spinner.classList.remove('d-none');

    fetch(`/devolucao/frete/api/descarte/${descarteId}/upload/${tipo}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: formData
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modal-upload-termo')).hide();
            location.reload();
        } else {
            alert(result.erro || 'Erro ao enviar arquivo');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao. Tente novamente.');
    })
    .finally(() => {
        spinner.classList.add('d-none');
    });
}

// =========================================================================
// Funcoes para Editar NFs de Venda Referenciadas
// =========================================================================
function abrirModalEditarNFs() {
    carregarNFsReferenciadas();
    const modal = new bootstrap.Modal(document.getElementById('modal-editar-nfs'));
    modal.show();
}

function carregarNFsReferenciadas() {
    const container = document.getElementById('lista-nfs-modal');
    container.innerHTML = '<span class="text-muted">Carregando...</span>';

    fetch(`/devolucao/vinculacao/api/${nfdId}/nfs-referenciadas`)
        .then(response => response.json())
        .then(result => {
            if (result.sucesso && result.nfs_referenciadas && result.nfs_referenciadas.length > 0) {
                let html = '<ul class="list-group">';
                result.nfs_referenciadas.forEach(nf => {
                    html += `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <span>
                                <strong>NF ${nf.numero_nf}</strong>
                                ${nf.serie_nf ? `<small class="text-muted">(Serie ${nf.serie_nf})</small>` : ''}
                                <br>
                                <small class="text-muted">Origem: ${nf.origem || 'N/A'}</small>
                            </span>
                            <button class="btn btn-sm btn-outline-danger" onclick="removerNF(${nf.id})" title="Remover NF">
                                <i class="fas fa-trash"></i> Remover
                            </button>
                        </li>
                    `;
                });
                html += '</ul>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<span class="text-muted">Nenhuma NF de venda vinculada</span>';
            }
        })
        .catch(error => {
            console.error('Erro ao carregar NFs:', error);
            container.innerHTML = '<span class="text-danger">Erro ao carregar NFs</span>';
        });
}

function adicionarNF() {
    const numero = document.getElementById('nova-nf-numero').value.trim();
    const serie = document.getElementById('nova-nf-serie').value.trim() || '1';
    const chave = document.getElementById('nova-nf-chave').value.trim();
    const spinner = document.getElementById('spinner-add-nf');

    if (!numero) {
        alert('Informe o numero da NF');
        return;
    }

    spinner.classList.remove('d-none');

    fetch(`/devolucao/vinculacao/api/${nfdId}/nfs-referenciadas`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify({
            numero_nf: numero,
            serie_nf: serie,
            chave_nf: chave || null,
            origem: 'MANUAL'
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            document.getElementById('nova-nf-numero').value = '';
            document.getElementById('nova-nf-chave').value = '';
            carregarNFsReferenciadas();
            atualizarListaNFsNaTela();
        } else {
            alert(result.erro || 'Erro ao adicionar NF');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao. Tente novamente.');
    })
    .finally(() => {
        spinner.classList.add('d-none');
    });
}

function removerNF(refId) {
    if (!confirm('Confirma remover esta NF de venda?')) {
        return;
    }

    fetch(`/devolucao/vinculacao/api/${nfdId}/nfs-referenciadas/${refId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.sucesso) {
            carregarNFsReferenciadas();
            atualizarListaNFsNaTela();
        } else {
            alert(result.erro || 'Erro ao remover NF');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexao. Tente novamente.');
    });
}

function atualizarListaNFsNaTela() {
    fetch(`/devolucao/vinculacao/api/${nfdId}/nfs-referenciadas`)
        .then(response => response.json())
        .then(result => {
            const container = document.getElementById('lista-nfs-referenciadas');
            if (result.sucesso && result.nfs_referenciadas && result.nfs_referenciadas.length > 0) {
                let html = '';
                result.nfs_referenciadas.forEach(nf => {
                    html += `<span class="badge bg-secondary me-1 mb-1">NF ${nf.numero_nf}</span>`;
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = '<span class="text-muted">-</span>';
            }
        });
}

// =========================================================================
// ABA PRODUTOS - Toggle Comparacao NF de Venda
// =========================================================================
function toggleComparacaoNF() {
    const btn = document.getElementById('btn-comparar-nf');
    const tabelaNFD = document.getElementById('tabela-produtos-nfd');
    const tabelaComparacao = document.getElementById('tabela-comparacao-nf');

    modoComparacao = !modoComparacao;

    if (modoComparacao) {
        btn.innerHTML = '<i class="bi bi-list-ul"></i> Ver qtds da NFD';
        btn.classList.remove('btn-outline-info');
        btn.classList.add('btn-info');
        tabelaNFD.classList.add('d-none');
        tabelaComparacao.classList.remove('d-none');

        if (!dadosComparacao) {
            carregarComparacaoNF();
        }
    } else {
        btn.innerHTML = '<i class="bi bi-arrow-left-right"></i> Comparar com NF de venda';
        btn.classList.remove('btn-info');
        btn.classList.add('btn-outline-info');
        tabelaNFD.classList.remove('d-none');
        tabelaComparacao.classList.add('d-none');
    }
}

async function carregarComparacaoNF() {
    const loading = document.getElementById('loading-comparacao');
    const resultado = document.getElementById('resultado-comparacao');

    loading.classList.remove('d-none');
    resultado.classList.add('d-none');

    try {
        const response = await fetch(`/devolucao/ocorrencias/api/${ocorrenciaId}/comparar-nf-venda`);
        const data = await response.json();

        if (data.sucesso) {
            dadosComparacao = data;
            renderizarComparacao(data);
        } else {
            document.getElementById('tbody-comparacao').innerHTML = `
                <tr><td colspan="8" class="text-center text-danger">${data.erro || 'Erro ao carregar dados'}</td></tr>
            `;
        }
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('tbody-comparacao').innerHTML = `
            <tr><td colspan="8" class="text-center text-danger">Erro de conexao: ${error.message}</td></tr>
        `;
    } finally {
        loading.classList.add('d-none');
        resultado.classList.remove('d-none');
    }
}

function renderizarComparacao(data) {
    const tbody = document.getElementById('tbody-comparacao');
    const tfoot = document.getElementById('tfoot-comparacao');
    let html = '';
    let totalValorDevol = 0;

    if (data.produtos && data.produtos.length > 0) {
        data.produtos.forEach(p => {
            const qtdDevolvida = parseFloat(p.qtd_devolvida) || 0;
            const qtdVendida = parseFloat(p.qtd_vendida) || 0;
            const precoDevol = parseFloat(p.preco_devolvido) || parseFloat(p.preco_venda) || 0;

            const percDevol = qtdVendida > 0 ? ((qtdDevolvida / qtdVendida) * 100).toFixed(1) : '-';
            const valorDevol = qtdDevolvida * precoDevol;
            totalValorDevol += valorDevol;

            const percClass = parseFloat(percDevol) > 100 ? 'text-danger' :
                              parseFloat(percDevol) > 50 ? 'text-warning' : 'text-success';

            html += `
                <tr>
                    <td><code>${p.codigo || '-'}</code></td>
                    <td>${p.descricao || '-'}</td>
                    <td class="text-end">${qtdVendida ? qtdVendida.toFixed(4) : '-'}</td>
                    <td class="text-end">${qtdDevolvida ? qtdDevolvida.toFixed(4) : '-'}</td>
                    <td class="text-end ${percClass}">${percDevol}%</td>
                    <td class="text-end">${p.preco_venda ? 'R$ ' + parseFloat(p.preco_venda).toFixed(2) : '-'}</td>
                    <td class="text-end">${p.preco_devolvido ? 'R$ ' + parseFloat(p.preco_devolvido).toFixed(2) : '-'}</td>
                    <td class="text-end"><strong>R$ ${valorDevol.toFixed(2)}</strong></td>
                </tr>
            `;
        });
    } else {
        html = '<tr><td colspan="8" class="text-center text-muted">Nenhum produto encontrado para comparar</td></tr>';
    }

    tbody.innerHTML = html;

    tfoot.innerHTML = `
        <tr>
            <td colspan="7" class="text-end"><strong>Total Valor Devolucao:</strong></td>
            <td class="text-end"><strong>R$ ${totalValorDevol.toFixed(2)}</strong></td>
        </tr>
    `;

    if (data.nfs_nao_encontradas && data.nfs_nao_encontradas.length > 0) {
        document.getElementById('nfs-nao-encontradas').classList.remove('d-none');
        document.getElementById('lista-nfs-nao-encontradas').textContent = data.nfs_nao_encontradas.join(', ');
    } else {
        document.getElementById('nfs-nao-encontradas').classList.add('d-none');
    }
}

// =========================================================================
// ABA PRODUTOS - Modal Resolver/Editar
// =========================================================================
function abrirModalResolverProduto(linhaId, codigoCliente, descricaoCliente, quantidade, unidade) {
    document.getElementById('modal-produto-titulo').textContent = 'Resolver Produto';
    document.getElementById('modal-sugestoes-ia').classList.remove('d-none');
    document.getElementById('prod-linha-id').value = linhaId;

    document.getElementById('modal-produto-cliente-info').innerHTML = `
        <code>${codigoCliente || '-'}</code> - ${descricaoCliente || '-'}
        <br><small class="text-muted">Qtd: ${quantidade || '-'} ${unidade || ''}</small>
    `;

    document.getElementById('prod-nosso-codigo').value = '';
    document.getElementById('prod-nosso-descricao').value = '';
    document.getElementById('prod-qtd-original').value = `${quantidade || ''} ${unidade || ''}`;
    document.getElementById('prod-fator-conversao').value = '';
    document.getElementById('prod-qtd-convertida').value = '';
    document.getElementById('prod-peso').value = '';
    document.getElementById('prod-info-extra').classList.add('d-none');
    produtoSelecionadoInfo = null;

    const modal = new bootstrap.Modal(document.getElementById('modal-produto'));
    modal.show();

    buscarSugestoesIA(linhaId, codigoCliente, descricaoCliente, quantidade, unidade);
}

function abrirModalEditarProduto(linhaId, codigoCliente, descricaoCliente, quantidade, unidade, codigoInterno, descricaoInterna, qtdConvertida, fatorConversao) {
    document.getElementById('modal-produto-titulo').textContent = 'Editar Produto';
    document.getElementById('modal-sugestoes-ia').classList.add('d-none');
    document.getElementById('prod-linha-id').value = linhaId;

    document.getElementById('modal-produto-cliente-info').innerHTML = `
        <code>${codigoCliente || '-'}</code> - ${descricaoCliente || '-'}
        <br><small class="text-muted">Qtd: ${quantidade || '-'} ${unidade || ''}</small>
    `;

    document.getElementById('prod-nosso-codigo').value = codigoInterno || '';
    document.getElementById('prod-nosso-descricao').value = descricaoInterna || '';
    document.getElementById('prod-qtd-original').value = `${quantidade || ''} ${unidade || ''}`;
    document.getElementById('prod-fator-conversao').value = fatorConversao || '';
    document.getElementById('prod-qtd-convertida').value = qtdConvertida || '';
    document.getElementById('prod-peso').value = '';
    document.getElementById('prod-info-extra').classList.add('d-none');
    produtoSelecionadoInfo = null;

    const modal = new bootstrap.Modal(document.getElementById('modal-produto'));
    modal.show();
}

async function buscarSugestoesIA(linhaId, codigoCliente, descricaoCliente, quantidade, unidade) {
    const container = document.getElementById('modal-sugestoes-lista');
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm"></div>
            <span class="ms-2">Consultando IA...</span>
        </div>
    `;

    try {
        const response = await fetch('/devolucao/ai/api/resolver-produto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefixo_cnpj: PREFIXO_CNPJ,
                codigo_cliente: codigoCliente,
                descricao_cliente: descricaoCliente,
                quantidade: quantidade,
                unidade_cliente: unidade
            })
        });

        const data = await response.json();

        if (data.sucesso && data.sugestao_principal) {
            renderizarSugestoesModal(data, quantidade);
        } else {
            container.innerHTML = `
                <div class="alert alert-warning mb-0">
                    Nenhuma sugestao encontrada. Preencha manualmente.
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro:', error);
        container.innerHTML = `
            <div class="alert alert-danger mb-0">
                Erro ao consultar IA: ${error.message}
            </div>
        `;
    }
}

function renderizarSugestoesModal(data, quantidade) {
    const container = document.getElementById('modal-sugestoes-lista');
    const confiancaClass = data.confianca >= 0.9 ? 'bg-success' :
                           data.confianca >= 0.5 ? 'bg-warning' : 'bg-danger';

    let html = `
        <div class="mb-2">
            <span class="badge ${confiancaClass}">${(data.confianca * 100).toFixed(0)}% confianca</span>
            ${data.metodo_resolucao ? `<span class="badge bg-secondary ms-1">${data.metodo_resolucao}</span>` : ''}
        </div>
        <div class="list-group">
    `;

    const sp = data.sugestao_principal;
    html += criarItemSugestao(sp, quantidade, true);

    if (data.outras_sugestoes && data.outras_sugestoes.length > 0) {
        data.outras_sugestoes.forEach(s => {
            html += criarItemSugestao(s, quantidade, false);
        });
    }

    html += '</div>';
    container.innerHTML = html;

    selecionarSugestaoModal(sp.codigo, sp.nome, sp.qtd_por_caixa, sp.qtd_convertida_caixas, sp.peso_calculado, quantidade);
}

function criarItemSugestao(sugestao, quantidade, principal) {
    const s = sugestao;
    return `
        <button type="button" class="list-group-item list-group-item-action ${principal ? 'active' : ''}"
                onclick="selecionarSugestaoModal('${s.codigo}', '${(s.nome || '').replace(/'/g, "\\'")}', ${s.qtd_por_caixa || 'null'}, ${s.qtd_convertida_caixas || 'null'}, ${s.peso_calculado || 'null'}, ${quantidade || 'null'})">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${s.codigo}</strong>
                    <br><small>${s.nome || ''}</small>
                </div>
                <div class="text-end">
                    ${s.qtd_por_caixa ? `<span class="badge bg-info">${s.qtd_por_caixa} un/cx</span>` : ''}
                    ${s.qtd_convertida_caixas ? `<br><small class="text-success">${quantidade} un -> ${s.qtd_convertida_caixas} cx</small>` : ''}
                </div>
            </div>
        </button>
    `;
}

function selecionarSugestaoModal(codigo, nome, qtdPorCaixa, qtdConvertida, peso, qtdOriginal) {
    document.getElementById('prod-nosso-codigo').value = codigo;
    document.getElementById('prod-nosso-descricao').value = nome;
    document.getElementById('prod-fator-conversao').value = qtdPorCaixa || '';
    document.getElementById('prod-qtd-convertida').value = qtdConvertida || '';
    document.getElementById('prod-peso').value = peso || '';

    produtoSelecionadoInfo = {
        codigo: codigo,
        nome: nome,
        qtd_por_caixa: qtdPorCaixa,
        qtd_convertida: qtdConvertida,
        peso: peso,
        peso_bruto: peso  // Necessario para calcularQtdConvertida() que busca peso_bruto
    };

    document.querySelectorAll('#modal-sugestoes-lista .list-group-item').forEach(el => {
        el.classList.remove('active');
        if (el.querySelector('strong')?.textContent === codigo) {
            el.classList.add('active');
        }
    });
}

// =========================================================================
// ABA PRODUTOS - Autocomplete de Produtos
// =========================================================================
async function buscarProdutosAba(query) {
    if (timeoutBuscaProd) clearTimeout(timeoutBuscaProd);

    if (!query || query.length < 2) {
        document.getElementById('autocomplete-produtos-aba').classList.remove('show');
        return;
    }

    timeoutBuscaProd = setTimeout(async () => {
        try {
            const response = await fetch(`/devolucao/ai/api/produtos/buscar?q=${encodeURIComponent(query)}&limit=15`);
            const data = await response.json();

            const dropdown = document.getElementById('autocomplete-produtos-aba');

            if (data.sucesso && data.produtos.length > 0) {
                let html = '';
                data.produtos.forEach(p => {
                    html += `
                        <a class="dropdown-item" href="#"
                           onclick="selecionarProdutoAba('${p.codigo}', '${(p.nome || '').replace(/'/g, "\\'")}', '${p.embalagem || ''}', '${p.materia_prima || ''}', ${p.peso_bruto || 'null'}); return false;">
                            <strong>${p.codigo}</strong>
                            <br><small class="text-muted">${p.nome}</small>
                        </a>
                    `;
                });
                dropdown.innerHTML = html;
                dropdown.classList.add('show');
            } else {
                dropdown.innerHTML = '<span class="dropdown-item text-muted">Nenhum produto encontrado</span>';
                dropdown.classList.add('show');
            }
        } catch (error) {
            console.error('Erro ao buscar produtos:', error);
        }
    }, 300);
}

function selecionarProdutoAba(codigo, nome, embalagem, materia, pesoBruto) {
    document.getElementById('prod-nosso-codigo').value = codigo;
    document.getElementById('prod-nosso-descricao').value = nome;
    document.getElementById('autocomplete-produtos-aba').classList.remove('show');

    document.getElementById('prod-info-extra').classList.remove('d-none');
    document.getElementById('prod-info-embalagem').textContent = embalagem || '-';
    document.getElementById('prod-info-materia').textContent = materia || '-';
    document.getElementById('prod-info-peso-cx').textContent = pesoBruto || '-';

    produtoSelecionadoInfo = {
        codigo: codigo,
        nome: nome,
        peso_bruto: pesoBruto
    };

    calcularQtdConvertida();
}

function calcularQtdConvertida() {
    const qtdOriginalStr = document.getElementById('prod-qtd-original').value;
    const fator = parseFloat(document.getElementById('prod-fator-conversao').value);

    if (!qtdOriginalStr || !fator || fator <= 0) return;

    const qtdMatch = qtdOriginalStr.match(/[\d.,]+/);
    if (!qtdMatch) return;

    const qtdOriginal = parseFloat(qtdMatch[0].replace(',', '.'));
    const qtdConvertida = qtdOriginal / fator;

    document.getElementById('prod-qtd-convertida').value = qtdConvertida.toFixed(2);

    if (produtoSelecionadoInfo && produtoSelecionadoInfo.peso_bruto) {
        const peso = qtdConvertida * produtoSelecionadoInfo.peso_bruto;
        document.getElementById('prod-peso').value = peso.toFixed(2);
    }
}

// =========================================================================
// ABA PRODUTOS - Salvar Produto
// =========================================================================
async function salvarProduto() {
    const linhaId = document.getElementById('prod-linha-id').value;
    const codigo = document.getElementById('prod-nosso-codigo').value;
    const descricao = document.getElementById('prod-nosso-descricao').value;
    const fatorConversao = document.getElementById('prod-fator-conversao').value;
    const qtdConvertida = document.getElementById('prod-qtd-convertida').value;
    const gravarDepara = document.getElementById('prod-gravar-depara').checked;

    if (!codigo) {
        alert('Informe o nosso codigo');
        return;
    }

    const spinner = document.getElementById('spinner-salvar-prod');
    spinner.classList.remove('d-none');

    try {
        const response = await fetch(`/devolucao/ai/api/linha/${linhaId}/confirmar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                codigo_interno: codigo,
                descricao_interno: descricao,
                gravar_depara: gravarDepara,
                qtd_por_caixa: fatorConversao ? parseInt(fatorConversao) : null,
                quantidade_convertida: qtdConvertida ? parseFloat(qtdConvertida) : null
            })
        });

        const data = await response.json();

        if (data.sucesso) {
            const row = document.getElementById(`prod-linha-${linhaId}`);
            if (row) {
                row.classList.add('table-success');

                document.getElementById(`prod-nosso-${linhaId}`).innerHTML = `
                    <strong class="text-primary">${codigo}</strong>
                    <br><small class="text-muted">${descricao}</small>
                `;

                if (data.quantidade_convertida) {
                    document.getElementById(`prod-qtd-${linhaId}`).innerHTML = `
                        <span class="badge bg-success">${data.quantidade_convertida.toFixed(3)} cx</span>
                    `;
                }

                if (data.peso_bruto) {
                    document.getElementById(`prod-peso-${linhaId}`).innerHTML = `
                        <span class="badge bg-info">${data.peso_bruto.toFixed(2)} kg</span>
                    `;
                }

                document.getElementById(`prod-status-${linhaId}`).innerHTML = `
                    <span class="badge bg-success">Resolvido</span>
                `;
            }

            recalcularTotalPeso();
            bootstrap.Modal.getInstance(document.getElementById('modal-produto')).hide();
        } else {
            alert('Erro: ' + (data.erro || 'Falha ao salvar'));
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro de conexao: ' + error.message);
    } finally {
        spinner.classList.add('d-none');
    }
}

// =========================================================================
// RESOLVER TODOS COM IA
// =========================================================================
async function resolverTodosComIA() {
    const modal = new bootstrap.Modal(document.getElementById('modal-resolver-todos'));
    const loading = document.getElementById('resolver-loading');
    const resultado = document.getElementById('resolver-resultado');
    const aplicando = document.getElementById('resolver-aplicando');
    const footer = document.getElementById('resolver-footer');
    const resumo = document.getElementById('resolver-resumo');
    const tbody = document.getElementById('resolver-tbody');

    loading.classList.remove('d-none');
    resultado.classList.add('d-none');
    aplicando.classList.add('d-none');
    footer.classList.add('d-none');
    tbody.innerHTML = '';
    resultadosResolverTodos = [];
    document.getElementById('resolver-selecionar-todos').checked = false;
    atualizarContadorSelecionadas();

    modal.show();

    try {
        const response = await fetch(`/devolucao/ai/api/nfd/${nfdId}/resolver-linhas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_gravar_depara: false })
        });

        const data = await response.json();

        loading.classList.add('d-none');
        resultado.classList.remove('d-none');
        footer.classList.remove('d-none');

        if (data.sucesso) {
            resultadosResolverTodos = data.linhas || [];

            resumo.innerHTML = `
                <strong>Sugestoes encontradas!</strong> Selecione as linhas que deseja aplicar.<br>
                Total: ${data.total_linhas || 0} linhas |
                <span class="text-success">Auto (>=90%): ${data.resolvidas_auto || 0}</span> |
                <span class="text-warning">Confirmar: ${data.requerem_confirmacao || 0}</span> |
                <span class="text-danger">Nao identificadas: ${data.nao_identificadas || 0}</span>
            `;

            if (resultadosResolverTodos.length > 0) {
                resultadosResolverTodos.forEach((r, index) => {
                    const confianca = r.confianca || 0;
                    const confiancaClass = confianca >= 0.9 ? 'text-success' :
                                          confianca >= 0.5 ? 'text-warning' : 'text-danger';
                    const temSugestao = r.sugestao && r.sugestao.codigo;
                    const statusClass = r.status === 'AUTO_RESOLVIDO' ? 'bg-success' :
                                        r.status === 'REQUER_CONFIRMACAO' ? 'bg-warning' : 'bg-secondary';
                    const statusText = r.status === 'AUTO_RESOLVIDO' ? 'Auto (>=90%)' :
                                       r.status === 'REQUER_CONFIRMACAO' ? 'Confirmar' : 'Nao identificado';

                    const checkboxHtml = temSugestao ?
                        `<input type="checkbox" class="form-check-input resolver-checkbox" data-index="${index}" onchange="atualizarContadorSelecionadas()" ${confianca >= 0.9 ? 'checked' : ''}>` :
                        `<span class="text-muted">-</span>`;

                    const qtdNfd = r.quantidade ? parseFloat(r.quantidade).toFixed(2) : '-';
                    const unidade = r.unidade_cliente || '';

                    let conversaoHtml = '-';
                    if (temSugestao && r.sugestao.qtd_por_caixa) {
                        const fator = r.sugestao.qtd_por_caixa;
                        const qtdConv = r.sugestao.qtd_convertida_caixas;
                        conversaoHtml = `<small class="text-info">÷ ${fator}</small>`;
                        if (qtdConv) {
                            conversaoHtml += `<br><strong class="text-success">${parseFloat(qtdConv).toFixed(3)} cx</strong>`;
                        }
                    }

                    tbody.innerHTML += `
                        <tr id="resolver-row-${index}" class="${temSugestao && confianca >= 0.9 ? 'table-success' : ''}">
                            <td class="text-center">${checkboxHtml}</td>
                            <td>
                                <code>${r.codigo_cliente || '-'}</code>
                                <br><small class="text-muted">${(r.descricao_cliente || '-').substring(0, 50)}</small>
                            </td>
                            <td>
                                ${temSugestao ? `<strong class="text-primary">${r.sugestao.codigo}</strong>` : '-'}
                                ${temSugestao ? `<br><small class="text-muted">${(r.sugestao.nome || '').substring(0, 50)}</small>` : ''}
                            </td>
                            <td class="text-center">
                                <strong>${qtdNfd}</strong>
                                ${unidade ? `<br><small class="text-muted">${unidade}</small>` : ''}
                            </td>
                            <td class="text-center">
                                ${conversaoHtml}
                            </td>
                            <td class="text-center ${confiancaClass}">
                                ${confianca ? (confianca * 100).toFixed(0) + '%' : '-'}
                            </td>
                            <td>
                                <span class="badge ${statusClass}" id="resolver-status-${index}">${statusText}</span>
                            </td>
                        </tr>
                    `;
                });
                atualizarContadorSelecionadas();
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Nenhuma linha pendente para processar</td></tr>';
            }
        } else {
            resumo.innerHTML = `<span class="text-danger"><strong>Erro:</strong> ${data.erro || 'Erro ao processar'}</span>`;
            resumo.classList.remove('alert-info');
            resumo.classList.add('alert-danger');
        }
    } catch (error) {
        console.error('Erro:', error);
        loading.classList.add('d-none');
        resultado.classList.remove('d-none');
        footer.classList.remove('d-none');
        resumo.innerHTML = `<span class="text-danger"><strong>Erro de conexao:</strong> ${error.message}</span>`;
        resumo.classList.remove('alert-info');
        resumo.classList.add('alert-danger');
    }
}

function toggleSelecionarTodosResolver() {
    const checked = document.getElementById('resolver-selecionar-todos').checked;
    document.querySelectorAll('.resolver-checkbox').forEach(cb => {
        cb.checked = checked;
    });
    atualizarContadorSelecionadas();
}

function atualizarContadorSelecionadas() {
    const count = document.querySelectorAll('.resolver-checkbox:checked').length;
    document.getElementById('count-selecionadas').textContent = count;
    const btn = document.getElementById('btn-aplicar-resolucoes');
    if (btn) btn.disabled = count === 0;
}

async function aplicarResolucoesSelecionadas() {
    const checkboxes = document.querySelectorAll('.resolver-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('Selecione ao menos uma linha para aplicar');
        return;
    }

    const gravarDepara = document.getElementById('resolver-gravar-depara').checked;
    const resultado = document.getElementById('resolver-resultado');
    const aplicando = document.getElementById('resolver-aplicando');
    const footer = document.getElementById('resolver-footer');
    const progresso = document.getElementById('resolver-aplicando-progresso');

    resultado.classList.add('d-none');
    footer.classList.add('d-none');
    aplicando.classList.remove('d-none');

    let aplicadas = 0;
    let erros = 0;
    const total = checkboxes.length;

    for (const cb of checkboxes) {
        const index = parseInt(cb.dataset.index);
        const r = resultadosResolverTodos[index];

        if (!r || !r.sugestao || !r.sugestao.codigo) continue;

        progresso.textContent = `${aplicadas + erros + 1}/${total}`;

        try {
            const response = await fetch(`/devolucao/ai/api/linha/${r.linha_id}/confirmar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    codigo_interno: r.sugestao.codigo,
                    descricao_interno: r.sugestao.nome || '',
                    gravar_depara: gravarDepara,
                    qtd_por_caixa: r.sugestao.qtd_por_caixa || null,
                    quantidade_convertida: r.sugestao.qtd_convertida_caixas || null
                })
            });

            const data = await response.json();

            if (data.sucesso) {
                aplicadas++;
                const statusEl = document.getElementById(`resolver-status-${index}`);
                if (statusEl) {
                    statusEl.className = 'badge bg-success';
                    statusEl.textContent = 'Aplicado';
                }
                atualizarLinhaProdutoNaTabela(r.linha_id, r.sugestao.codigo, r.sugestao.nome, data.quantidade_convertida, data.peso_bruto);
            } else {
                erros++;
                const statusEl = document.getElementById(`resolver-status-${index}`);
                if (statusEl) {
                    statusEl.className = 'badge bg-danger';
                    statusEl.textContent = 'Erro';
                }
            }
        } catch (error) {
            console.error(`Erro ao aplicar linha ${r.linha_id}:`, error);
            erros++;
        }
    }

    aplicando.classList.add('d-none');
    resultado.classList.remove('d-none');
    footer.classList.remove('d-none');

    recalcularTotalPeso();

    const resumo = document.getElementById('resolver-resumo');
    resumo.className = erros === 0 ? 'alert alert-success mb-3' : 'alert alert-warning mb-3';
    resumo.innerHTML = `
        <strong>Aplicacao concluida!</strong><br>
        <span class="text-success">Aplicadas: ${aplicadas}</span> |
        <span class="text-danger">Erros: ${erros}</span>
    `;

    checkboxes.forEach(cb => {
        cb.checked = false;
        cb.disabled = true;
    });
    atualizarContadorSelecionadas();
}

function recalcularTotalPeso() {
    const totalPesoEl = document.getElementById('tfoot-total-peso');
    if (!totalPesoEl) return;

    let totalPeso = 0;
    // Percorrer todas as linhas de produto da tabela NFD
    document.querySelectorAll('[id^="prod-peso-"]').forEach(el => {
        // Extrair numero do texto (ex: "12.50 kg" ou badge com "12.50 kg")
        const texto = el.textContent.trim();
        const match = texto.match(/([\d.,]+)\s*kg/i);
        if (match) {
            totalPeso += parseFloat(match[1].replace(',', '.')) || 0;
        }
    });

    totalPesoEl.innerHTML = `<strong>${totalPeso.toFixed(2)} kg</strong>`;
}

function atualizarLinhaProdutoNaTabela(linhaId, codigo, descricao, qtdConvertida, peso) {
    const row = document.getElementById(`prod-linha-${linhaId}`);
    if (row) {
        row.classList.add('table-success');

        const nossoEl = document.getElementById(`prod-nosso-${linhaId}`);
        if (nossoEl) {
            nossoEl.innerHTML = `
                <strong class="text-primary">${codigo}</strong>
                <br><small class="text-muted">${descricao || ''}</small>
            `;
        }

        if (qtdConvertida) {
            const qtdEl = document.getElementById(`prod-qtd-${linhaId}`);
            if (qtdEl) {
                qtdEl.innerHTML = `<span class="badge bg-success">${parseFloat(qtdConvertida).toFixed(3)} cx</span>`;
            }
        }

        if (peso) {
            const pesoEl = document.getElementById(`prod-peso-${linhaId}`);
            if (pesoEl) {
                pesoEl.innerHTML = `<span class="badge bg-info">${parseFloat(peso).toFixed(2)} kg</span>`;
            }
        }

        const statusEl = document.getElementById(`prod-status-${linhaId}`);
        if (statusEl) {
            statusEl.innerHTML = `<span class="badge bg-success">Resolvido</span>`;
        }
    }
}
