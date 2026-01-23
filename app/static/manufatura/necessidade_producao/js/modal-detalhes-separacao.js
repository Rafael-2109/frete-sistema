/**
 * Modal de Detalhes da Separação - VERSÃO CORRIGIDA COM ORDEM CORRETA
 *
 * ORDEM CORRETA:
 * 1. Buscar dados da API
 * 2. Inserir HTML no modal
 * 3. DEPOIS abrir o modal
 */

async function abrirModalDetalhesSeparacao(separacaoLoteId) {
    console.log('=== MODAL DETALHES INICIANDO ===');
    console.log('1. separacao_lote_id recebido:', separacaoLoteId);

    // ✅ FUNÇÕES INTERNAS
    function formatarNumeroLocal(num, decimais = 2) {
        if (!num) return decimais === 0 ? '0' : '0,00';
        return parseFloat(num).toLocaleString('pt-BR', {
            minimumFractionDigits: decimais,
            maximumFractionDigits: decimais
        });
    }

    function formatarDataLocal(dataISO) {
        if (!dataISO) return '-';
        const [ano, mes, dia] = dataISO.split('-');
        return `${dia}/${mes}/${ano}`;
    }

    // PASSO 1: VERIFICAR SE ELEMENTOS EXISTEM
    // ✅ ID correto do modal definido em _modal-pedidos.html linha 73
    const modalElement = document.getElementById('modalDetalhesSeparacao');
    // ✅ ID correto do body definido em _modal-pedidos.html linha 83
    const modalBody = document.getElementById('conteudo-detalhes-separacao');

    console.log('2. Modal element encontrado?', modalElement ? 'SIM' : 'NÃO');
    console.log('3. Modal body encontrado?', modalBody ? 'SIM' : 'NÃO');

    if (!modalElement || !modalBody) {
        Swal.fire({
            icon: 'error',
            title: 'Erro',
            text: 'Elementos do modal não encontrados!',
            confirmButtonText: 'OK'
        });
        return;
    }

    try {
        // PASSO 2: BUSCAR DADOS DA API
        const url = `/manufatura/api/necessidade-producao/separacao-detalhes?separacao_lote_id=${separacaoLoteId}`;
        console.log('4. Buscando API:', url);

        const response = await fetch(url);
        console.log('5. Status da resposta:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const dados = await response.json();
        console.log('6. Dados recebidos:', dados);

        if (dados.erro) {
            Swal.fire({
                icon: 'error',
                title: 'Erro da API',
                text: dados.erro,
                confirmButtonText: 'OK'
            });
            return;
        }

        // PASSO 3: MONTAR HTML
        console.log('7. Montando HTML...');

        let html = '<div class="container-fluid">';

        // INFORMAÇÕES GERAIS
        html += '<h6 class="text-primary mb-3"><i class="fas fa-info-circle me-2"></i>Informações Gerais</h6>';
        html += '<table class="table table-sm table-bordered mb-4">';
        html += `<tr><th style="width: 150px;">Pedido:</th><td><strong>${dados.num_pedido || '-'}</strong></td></tr>`;
        html += `<tr><th>Cliente:</th><td>${dados.raz_social_red || '-'}</td></tr>`;
        html += `<tr><th>CNPJ:</th><td>${dados.cnpj_cpf || '-'}</td></tr>`;
        html += `<tr><th>Cidade/UF:</th><td>${dados.nome_cidade || '-'} / ${dados.cod_uf || '-'}</td></tr>`;
        html += `<tr><th>Expedição:</th><td>${formatarDataLocal(dados.expedicao)}</td></tr>`;
        html += `<tr><th>Agendamento:</th><td>${formatarDataLocal(dados.agendamento)}</td></tr>`;
        html += `<tr><th>Protocolo:</th><td>${dados.protocolo || '-'}</td></tr>`;
        html += '</table>';

        // TOTAIS
        html += '<h6 class="text-success mb-3"><i class="fas fa-calculator me-2"></i>Totais</h6>';
        html += '<div class="row mb-4">';
        html += '<div class="col-4"><div class="card border-success"><div class="card-body text-center p-2">';
        html += '<small class="text-muted">Valor Total</small><br>';
        html += `<strong class="text-success">R$ ${formatarNumeroLocal(dados.total_valor, 2)}</strong>`;
        html += '</div></div></div>';
        html += '<div class="col-4"><div class="card border-info"><div class="card-body text-center p-2">';
        html += '<small class="text-muted">Peso Total</small><br>';
        html += `<strong class="text-info">${formatarNumeroLocal(dados.total_peso, 0)} kg</strong>`;  // ✅ SEM decimais
        html += '</div></div></div>';
        html += '<div class="col-4"><div class="card border-warning"><div class="card-body text-center p-2">';
        html += '<small class="text-muted">Pallets</small><br>';
        html += `<strong class="text-warning">${formatarNumeroLocal(dados.total_pallet, 2)}</strong>`;
        html += '</div></div></div>';
        html += '</div>';

        // ITENS
        html += `<h6 class="text-dark mb-3"><i class="fas fa-boxes me-2"></i>Itens (${dados.itens ? dados.itens.length : 0})</h6>`;
        html += '<table class="table table-sm table-bordered table-hover">';
        html += '<thead class="table-light"><tr>';
        html += '<th>Código</th><th>Produto</th><th class="text-end">Qtd</th>';
        html += '<th class="text-end">Valor</th><th class="text-end">Peso</th><th class="text-end">Pallet</th>';
        html += '</tr></thead><tbody>';

        if (dados.itens && dados.itens.length > 0) {
            dados.itens.forEach(item => {
                html += '<tr>';
                html += `<td><code>${item.cod_produto}</code></td>`;
                html += `<td>${item.nome_produto || '-'}</td>`;
                html += `<td class="text-end">${formatarNumeroLocal(item.qtd_saldo, 0)}</td>`;  // ✅ SEM decimais
                html += `<td class="text-end">R$ ${formatarNumeroLocal(item.valor_saldo, 2)}</td>`;
                html += `<td class="text-end">${formatarNumeroLocal(item.peso, 0)} kg</td>`;  // ✅ SEM decimais
                html += `<td class="text-end">${formatarNumeroLocal(item.pallet, 2)}</td>`;
                html += '</tr>';
            });
        } else {
            html += '<tr><td colspan="6" class="text-center text-muted">Nenhum item</td></tr>';
        }

        html += '</tbody></table>';

        // ✅ EMBARQUE E TRANSPORTADORA - SEMPRE EXIBIR
        html += '<h6 class="text-info mb-3 mt-4"><i class="fas fa-truck me-2"></i>Informações de Embarque</h6>';

        if (dados.embarque) {
            console.log('[MODAL] Embarque encontrado:', dados.embarque);
            console.log('[MODAL] Transportadora:', dados.transportadora);

            html += '<div class="row">';

            // Coluna 1: Dados do Embarque
            html += '<div class="col-md-6">';
            html += '<table class="table table-sm table-bordered">';
            html += `<tr><th style="width: 150px;">Nº Embarque:</th><td><strong>${dados.embarque.numero || '-'}</strong></td></tr>`;
            html += `<tr><th>Tipo de Carga:</th><td><span class="badge bg-secondary">${dados.embarque.tipo_carga || '-'}</span></td></tr>`;
            html += `<tr><th>Data Embarque:</th><td>${formatarDataLocal(dados.embarque.data_embarque)}</td></tr>`;
            html += `<tr><th>Data Prevista:</th><td>${formatarDataLocal(dados.embarque.data_prevista)}</td></tr>`;
            html += '</table>';
            html += '</div>';

            // Coluna 2: Dados da Transportadora
            if (dados.transportadora) {
                html += '<div class="col-md-6">';
                html += '<table class="table table-sm table-bordered">';
                html += `<tr><th style="width: 150px;">Transportadora:</th><td><strong>${dados.transportadora.razao_social || '-'}</strong></td></tr>`;
                html += `<tr><th>CNPJ:</th><td>${dados.transportadora.cnpj || '-'}</td></tr>`;
                html += '</table>';
                html += '</div>';
            } else {
                html += '<div class="col-md-6">';
                html += '<div class="alert alert-warning mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Transportadora não definida</div>';
                html += '</div>';
            }

            html += '</div>'; // fecha row
        } else {
            console.log('[MODAL] Embarque NÃO encontrado');
            html += '<div class="alert alert-info">';
            html += '<i class="fas fa-info-circle me-2"></i>';
            html += 'Esta separação ainda não foi vinculada a um embarque.';
            html += '</div>';
        }

        html += '</div>'; // fecha container-fluid

        console.log('8. HTML montado, tamanho:', html.length, 'caracteres');

        // PASSO 4: INSERIR HTML NO MODAL (ANTES DE ABRIR!)
        console.log('9. Inserindo HTML no modal body...');
        modalBody.innerHTML = html;
        console.log('10. HTML inserido! Conteúdo do body agora tem:', modalBody.innerHTML.length, 'caracteres');

        // PASSO 5: ABRIR O MODAL (BOOTSTRAP 5.3)
        console.log('11. Criando instância do modal Bootstrap 5...');

        // ✅ Criar nova instância do modal do Bootstrap 5
        const bsModal = new bootstrap.Modal(modalElement, {
            backdrop: true,
            keyboard: true,
            focus: true
        });

        console.log('12. Abrindo modal...');
        bsModal.show();

        console.log('13. ✅ MODAL ABERTO COM SUCESSO!');

    } catch (error) {
        console.error('❌ ERRO:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro ao carregar detalhes',
            text: error.message,
            confirmButtonText: 'OK'
        });
    }
}

// Log de carregamento do script
console.log('✅ Script modal-detalhes-separacao.js carregado');
