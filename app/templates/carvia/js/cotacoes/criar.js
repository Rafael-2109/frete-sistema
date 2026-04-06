/* ===== Veiculo DIRETA (criar) ===== */
function toggleVeiculoCriar() {
    const tc = document.getElementById('selTipoCargaCriar').value;
    const bloco = document.getElementById('blocoVeiculoCriar');
    if (bloco) bloco.classList.toggle('d-none', tc !== 'DIRETA');
}

/* ===== Enderecos por cliente ===== */
function carregarEnderecos() {
    const clienteId = document.getElementById('selCliente').value;
    if (!clienteId) return;

    fetch(`/carvia/api/cotacoes/enderecos-cliente/${clienteId}`)
    .then(r => r.json())
    .then(data => {
        const origens = data.enderecos.filter(e => e.tipo === 'ORIGEM');
        const destinos = data.enderecos.filter(e => e.tipo === 'DESTINO');

        const selOrigem = document.getElementById('selOrigem');
        const selDestino = document.getElementById('selDestino');

        selOrigem.innerHTML = '<option value="">Selecione...</option>';
        selDestino.innerHTML = '<option value="">Selecione...</option>';

        const todosEnderecos = data.enderecos;
        const listaOrigem = origens.length > 0 ? origens : todosEnderecos;
        const listaDestino = destinos.length > 0 ? destinos : todosEnderecos;

        listaOrigem.forEach(e => {
            selOrigem.innerHTML += `<option value="${e.id}" ${e.principal ? 'selected' : ''}>${e.label}</option>`;
        });
        listaDestino.forEach(e => {
            selDestino.innerHTML += `<option value="${e.id}" ${e.principal ? 'selected' : ''}>${e.label}</option>`;
        });
    });
}

/* ===== Modelos de moto (dados do backend) ===== */
const modelosMoto = CARVIA_DATA.modelosMoto;

/* ===== Show/hide por tipo material ===== */
document.getElementById('selTipoMaterial').addEventListener('change', function() {
    const isMoto = this.value === 'MOTO';
    document.getElementById('secaoCargaGeral').classList.toggle('d-none', isMoto);
    document.getElementById('secaoMoto').classList.toggle('d-none', !isMoto);
    if (isMoto && document.querySelectorAll('#tbodyMotos tr').length === 0) {
        adicionarLinhaMotos();
    }
});

/* ===== Tabela dinamica de motos ===== */
let motoRowIdx = 0;

function buildOpcoesModelo() {
    let html = '<option value="">Selecione...</option>';
    modelosMoto.forEach(m => {
        html += `<option value="${m.id}">${m.nome}</option>`;
    });
    return html;
}

function adicionarLinhaMotos() {
    const tbody = document.getElementById('tbodyMotos');
    const idx = motoRowIdx++;
    const tr = document.createElement('tr');
    tr.id = `motoRow${idx}`;
    tr.innerHTML = `
        <td><select class="form-select form-select-sm" id="motoModelo${idx}" onchange="onModeloChange(${idx})">${buildOpcoesModelo()}</select></td>
        <td><input type="number" class="form-control form-control-sm" id="motoQtd${idx}" value="1" min="1" oninput="recalcularMoto(${idx})"></td>
        <td><input type="number" class="form-control form-control-sm" id="motoValorUnit${idx}" step="0.01" min="0" oninput="recalcularMoto(${idx})"></td>
        <td><input type="text" class="form-control form-control-sm bg-light" id="motoPesoUnit${idx}" readonly tabindex="-1"></td>
        <td><input type="text" class="form-control form-control-sm bg-light" id="motoValorTotal${idx}" readonly tabindex="-1"></td>
        <td><input type="text" class="form-control form-control-sm bg-light" id="motoPesoTotal${idx}" readonly tabindex="-1"></td>
        <td><button type="button" class="btn btn-outline-danger btn-sm" onclick="removerLinhaMotos(${idx})" title="Remover"><i class="fas fa-trash"></i></button></td>
    `;
    tbody.appendChild(tr);
}

function onModeloChange(idx) {
    const modeloId = parseInt(document.getElementById(`motoModelo${idx}`).value);
    const modelo = modelosMoto.find(m => m.id === modeloId);
    document.getElementById(`motoPesoUnit${idx}`).value =
        modelo && modelo.peso_cubado ? modelo.peso_cubado.toFixed(3) : '';
    recalcularMoto(idx);
}

function recalcularMoto(idx) {
    const pesoUnit = parseFloat(document.getElementById(`motoPesoUnit${idx}`).value) || 0;
    const qtd = parseInt(document.getElementById(`motoQtd${idx}`).value) || 0;
    const valorUnit = parseFloat(document.getElementById(`motoValorUnit${idx}`).value) || 0;

    document.getElementById(`motoValorTotal${idx}`).value =
        valorUnit && qtd ? (valorUnit * qtd).toFixed(2) : '';
    document.getElementById(`motoPesoTotal${idx}`).value =
        pesoUnit && qtd ? (pesoUnit * qtd).toFixed(3) : '';

    recalcularTotaisMotos();
}

function recalcularTotaisMotos() {
    let totalValor = 0, totalPeso = 0;
    document.querySelectorAll('#tbodyMotos tr').forEach(tr => {
        totalValor += parseFloat(tr.querySelector('[id^="motoValorTotal"]')?.value) || 0;
        totalPeso += parseFloat(tr.querySelector('[id^="motoPesoTotal"]')?.value) || 0;
    });
    document.getElementById('totalValorMotos').textContent =
        `R$ ${totalValor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('totalPesoMotos').textContent =
        totalPeso.toLocaleString('pt-BR', {minimumFractionDigits: 3, maximumFractionDigits: 3});
}

function removerLinhaMotos(idx) {
    const row = document.getElementById(`motoRow${idx}`);
    if (row) row.remove();
    recalcularTotaisMotos();
    // Garantir pelo menos 1 linha
    if (document.querySelectorAll('#tbodyMotos tr').length === 0) {
        adicionarLinhaMotos();
    }
}

/* ===== Setup NF: parsear + wizard cliente/enderecos ===== */
let _setupData = null; // dados retornados pelo setup-nf
let _wizStep = 1;
let _wizSteps = []; // passos necessarios (1=cliente, 2=origem, 3=destino)

function iniciarSetupNF() {
    const fileInput = document.getElementById('inpNFPrePreencher');
    if (!fileInput.files || !fileInput.files[0]) { alert('Selecione o arquivo da NF.'); return; }

    const isAddMode = _nfsCollection.length > 0;
    const formData = new FormData();
    formData.append('arquivo', fileInput.files[0]);

    document.getElementById('btnPrePreencher').disabled = true;
    const fb = document.getElementById('prePreencherFeedback');
    fb.innerHTML = '<span class="text-muted small"><i class="fas fa-spinner fa-spin"></i> Parseando ' + (isAddMode ? 'NF...' : 'e verificando...') + '</span>';
    fb.style.display = 'block';

    fetch('/carvia/api/cotacoes/setup-nf', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(d => {
        document.getElementById('btnPrePreencher').disabled = false;
        if (!d.sucesso) { fb.innerHTML = '<div class="alert alert-danger py-1 small">' + (d.erro || 'Erro') + '</div>'; return; }

        // Modo adicionar: pular wizard, apenas adicionar ao collection
        if (isAddMode) {
            const jaExiste = _nfsCollection.some(n =>
                n.nf.numero_nf === d.nf.numero_nf && n.nf.cnpj_emitente === d.nf.cnpj_emitente
            );
            if (jaExiste) {
                fb.innerHTML = '<div class="alert alert-warning py-1 small">NF ' + d.nf.numero_nf + ' ja esta na lista.</div>';
                return;
            }
            adicionarNfAoCollection(d);
            fb.innerHTML = '<div class="alert alert-success py-1 small">NF ' + (d.nf.numero_nf || '') + ' adicionada!</div>';
            setTimeout(() => { fb.style.display = 'none'; }, 2000);
            fileInput.value = '';
            return;
        }

        _setupData = d;

        // Determinar quais passos do wizard sao necessarios
        _wizSteps = [];
        if (!d.cliente.existe) _wizSteps.push(1);
        if (!d.enderecos.origem_existe) _wizSteps.push(2);
        if (!d.enderecos.destino_existe) _wizSteps.push(3);

        if (_wizSteps.length > 0) {
            // Pre-preencher wizard
            const nf = d.nf;
            const re = d.receita_emitente;
            const rd = d.receita_destinatario;

            // Ajuste 1: se cliente existe, usar nome cadastrado (nao sobrescrever com NF)
            if (d.cliente.existe && d.cliente.nome) {
                document.getElementById('wizNomeCliente').value = d.cliente.nome;
            } else {
                document.getElementById('wizNomeCliente').value = nf.nome_emitente || '';
            }
            document.getElementById('wizOrigCnpj').value = nf.cnpj_emitente || '';
            document.getElementById('wizOrigRazao').value = nf.nome_emitente || '';
            document.getElementById('wizDestCnpj').value = nf.cnpj_destinatario || '';
            document.getElementById('wizDestRazao').value = nf.nome_destinatario || '';

            // Steps 2/3: Pre-preencher enderecos da Receita ou da NF
            if (re) {
                document.getElementById('wizOrigLogradouro').value = re.logradouro || '';
                document.getElementById('wizOrigNumero').value = re.numero || '';
                document.getElementById('wizOrigBairro').value = re.bairro || '';
                document.getElementById('wizOrigCidade').value = re.cidade || '';
                document.getElementById('wizOrigUf').value = re.uf || '';
                document.getElementById('wizOrigCep').value = re.cep || '';
                document.getElementById('wizOrigComplemento').value = re.complemento || '';
            } else {
                document.getElementById('wizOrigCidade').value = nf.cidade_emitente || '';
                document.getElementById('wizOrigUf').value = nf.uf_emitente || '';
            }
            if (rd) {
                document.getElementById('wizDestLogradouro').value = rd.logradouro || '';
                document.getElementById('wizDestNumero').value = rd.numero || '';
                document.getElementById('wizDestBairro').value = rd.bairro || '';
                document.getElementById('wizDestCidade').value = rd.cidade || '';
                document.getElementById('wizDestUf').value = rd.uf || '';
                document.getElementById('wizDestCep').value = rd.cep || '';
                document.getElementById('wizDestComplemento').value = rd.complemento || '';
            } else {
                document.getElementById('wizDestCidade').value = nf.cidade_destinatario || '';
                document.getElementById('wizDestUf').value = nf.uf_destinatario || '';
                if (d.receita_destinatario_erro) {
                    fb.innerHTML = '<div class="alert alert-warning py-1 small mb-2">' +
                        '<i class="fas fa-exclamation-triangle me-1"></i>' +
                        '<strong>Destinatario:</strong> ' + d.receita_destinatario_erro +
                        '. Preencha o endereco manualmente.' +
                        '</div>';
                    fb.style.display = 'block';
                }
            }
            if (!re && d.receita_emitente_erro) {
                const existingHtml = fb.innerHTML || '';
                fb.innerHTML = existingHtml +
                    '<div class="alert alert-warning py-1 small mb-2">' +
                    '<i class="fas fa-exclamation-triangle me-1"></i>' +
                    '<strong>Emitente:</strong> ' + d.receita_emitente_erro +
                    '. Preencha o endereco manualmente.' +
                    '</div>';
                fb.style.display = 'block';
            }

            // Abrir wizard no primeiro passo necessario
            _wizStep = 0;
            wizMostrarPasso(_wizSteps[0]);
            new bootstrap.Modal(document.getElementById('modalWizardNF')).show();
        } else {
            // Cliente e enderecos ja existem — preencher direto
            aplicarDadosNF(d);
        }
    })
    .catch(err => {
        document.getElementById('btnPrePreencher').disabled = false;
        fb.innerHTML = '<div class="alert alert-danger py-1 small">Erro: ' + err.message + '</div>';
    });
}

function wizMostrarPasso(passo) {
    _wizStep = passo;
    document.getElementById('wizStep1').classList.toggle('d-none', passo !== 1);
    document.getElementById('wizStep2').classList.toggle('d-none', passo !== 2);
    document.getElementById('wizStep3').classList.toggle('d-none', passo !== 3);
    const idx = _wizSteps.indexOf(passo);
    document.getElementById('btnWizVoltar').style.display = idx > 0 ? '' : 'none';
    document.getElementById('btnWizAvancar').textContent = idx === _wizSteps.length - 1 ? 'Concluir' : 'Proximo';
    document.getElementById('wizardTitulo').textContent = 'Passo ' + (idx + 1) + ' de ' + _wizSteps.length;
}

function wizVoltar() {
    const idx = _wizSteps.indexOf(_wizStep);
    if (idx > 0) wizMostrarPasso(_wizSteps[idx - 1]);
}

/* Toggle destino provisorio (sem CNPJ) */
function toggleDestinoProvisorio() {
    const provisorio = document.getElementById('wizDestProvisorio').checked;
    const cnpjBlock = document.getElementById('wizDestCnpjBlock');
    const alertBlock = document.getElementById('wizDestProvisorioAlert');
    if (provisorio) {
        cnpjBlock.classList.add('d-none');
        alertBlock.classList.remove('d-none');
    } else {
        cnpjBlock.classList.remove('d-none');
        alertBlock.classList.add('d-none');
    }
}

function wizAvancar() {
    const idx = _wizSteps.indexOf(_wizStep);
    if (idx < _wizSteps.length - 1) {
        wizMostrarPasso(_wizSteps[idx + 1]);
    } else {
        // Ultimo passo — salvar tudo
        wizConcluir();
    }
}

function wizConcluir() {
    const payload = {
        nome_comercial: document.getElementById('wizNomeCliente').value.trim(),
        origem: {
            cnpj: document.getElementById('wizOrigCnpj').value,
            razao_social: document.getElementById('wizOrigRazao').value,
            receita: _setupData.receita_emitente || {},
            fisico: {
                logradouro: document.getElementById('wizOrigLogradouro').value,
                numero: document.getElementById('wizOrigNumero').value,
                bairro: document.getElementById('wizOrigBairro').value,
                cidade: document.getElementById('wizOrigCidade').value,
                uf: document.getElementById('wizOrigUf').value,
                cep: document.getElementById('wizOrigCep').value,
                complemento: document.getElementById('wizOrigComplemento').value,
            }
        },
        destino: {
            cnpj: document.getElementById('wizDestCnpj').value,
            razao_social: document.getElementById('wizDestRazao').value,
            provisorio: document.getElementById('wizDestProvisorio').checked,
            receita: _setupData.receita_destinatario || {},
            fisico: {
                logradouro: document.getElementById('wizDestLogradouro').value,
                numero: document.getElementById('wizDestNumero').value,
                bairro: document.getElementById('wizDestBairro').value,
                cidade: document.getElementById('wizDestCidade').value,
                uf: document.getElementById('wizDestUf').value,
                cep: document.getElementById('wizDestCep').value,
                complemento: document.getElementById('wizDestComplemento').value,
            }
        }
    };

    document.getElementById('btnWizAvancar').disabled = true;
    fetch('/carvia/api/cotacoes/criar-cliente-rapido', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(d => {
        document.getElementById('btnWizAvancar').disabled = false;
        if (!d.sucesso) {
            const fb = document.getElementById('wizFeedback');
            fb.innerHTML = '<div class="alert alert-danger py-1 small">' + (d.erro || 'Erro') + '</div>';
            fb.style.display = 'block';
            return;
        }
        // Atualizar _setupData com IDs criados
        _setupData.cliente.id = d.cliente_id;
        _setupData.cliente.nome = d.nome_comercial;
        _setupData.cliente.existe = true;
        if (d.endereco_origem_id) { _setupData.enderecos.origem_id = d.endereco_origem_id; _setupData.enderecos.origem_existe = true; }
        if (d.endereco_destino_id) { _setupData.enderecos.destino_id = d.endereco_destino_id; _setupData.enderecos.destino_existe = true; }

        bootstrap.Modal.getInstance(document.getElementById('modalWizardNF')).hide();
        aplicarDadosNF(_setupData);
        aplicarRestricoesTardia();
    })
    .catch(err => {
        document.getElementById('btnWizAvancar').disabled = false;
        alert('Erro: ' + err.message);
    });
}

/* ===== Multi-NF Collection ===== */
let _nfsCollection = [];

function adicionarNfAoCollection(d) {
    if (d.nf_id) d.nf_db_id = d.nf_id;
    _nfsCollection.push(d);
    renderNfsList();
    atualizarTotaisNfs();
}

function removerNfDoCollection(idx) {
    _nfsCollection.splice(idx, 1);
    renderNfsList();
    atualizarTotaisNfs();
}

function renderNfsList() {
    const tbody = document.getElementById('tbodyNfsImportadas');
    const card = document.getElementById('cardNfsImportadas');
    if (!tbody || !card) return;

    if (_nfsCollection.length === 0) {
        card.classList.add('d-none');
        return;
    }

    card.classList.remove('d-none');
    tbody.innerHTML = '';
    _nfsCollection.forEach((d, idx) => {
        const nf = d.nf;
        const tr = document.createElement('tr');
        tr.innerHTML =
            '<td><strong>' + (nf.numero_nf || '-') + '</strong>' +
            (d.nf_db_id ? ' <span class="badge bg-info bg-opacity-75">BD</span>' : '') + '</td>' +
            '<td class="text-truncate" style="max-width:200px">' + (nf.nome_emitente || '-') + '</td>' +
            '<td class="text-center">' + (d.itens || []).length + '</td>' +
            '<td class="text-end">' + (nf.peso_bruto || 0).toLocaleString('pt-BR', {maximumFractionDigits: 3}) + '</td>' +
            '<td class="text-end">R$ ' + (nf.valor_total || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</td>' +
            '<td><button type="button" class="btn btn-outline-danger btn-sm py-0 px-1" onclick="removerNfDoCollection(' + idx + ')" title="Remover"><i class="fas fa-times"></i></button></td>';
        tbody.appendChild(tr);
    });
}

function atualizarTotaisNfs() {
    let totalPeso = 0, totalValor = 0, totalVolumes = 0;
    _nfsCollection.forEach(d => {
        totalPeso += d.nf.peso_bruto || 0;
        totalValor += d.nf.valor_total || 0;
        totalVolumes += d.nf.quantidade_volumes || 0;
    });

    const elPeso = document.getElementById('totalPesoNfs');
    const elValor = document.getElementById('totalValorNfs');
    if (elPeso) elPeso.textContent = totalPeso.toLocaleString('pt-BR', {maximumFractionDigits: 3});
    if (elValor) elValor.textContent = 'R$ ' + totalValor.toLocaleString('pt-BR', {minimumFractionDigits: 2});

    // Atualizar campos do form com totais
    const pesoCampo = document.querySelector('[name="peso"]');
    const valorCampo = document.querySelector('[name="valor_mercadoria"]');
    const volumesCampo = document.querySelector('[name="volumes"]');
    if (pesoCampo) pesoCampo.value = totalPeso || '';
    if (valorCampo) valorCampo.value = totalValor || '';
    if (volumesCampo) volumesCampo.value = totalVolumes || '';

    // Serializar todas as NFs no hidden input
    document.getElementById('nfDadosJson').value = JSON.stringify(_nfsCollection);
}

function aplicarDadosNF(d) {
    const nf = d.nf;
    const fb = document.getElementById('prePreencherFeedback') || document.getElementById('nfExistenteFeedback');
    const isFirstNf = _nfsCollection.length === 0;

    // Selecionar cliente (apenas primeira NF)
    if (isFirstNf && d.cliente.id) {
        const selCliente = document.getElementById('selCliente');
        if (!selCliente.querySelector('option[value="' + d.cliente.id + '"]')) {
            const opt = document.createElement('option');
            opt.value = d.cliente.id;
            opt.textContent = d.cliente.nome;
            selCliente.appendChild(opt);
        }
        selCliente.value = d.cliente.id;
        carregarEnderecos();
        setTimeout(() => {
            if (d.enderecos.origem_id) document.getElementById('selOrigem').value = d.enderecos.origem_id;
            if (d.enderecos.destino_id) document.getElementById('selDestino').value = d.enderecos.destino_id;
        }, 800);
    }

    // Tipo material (apenas primeira NF)
    if (isFirstNf && d.tipo_material) {
        document.getElementById('selTipoMaterial').value = d.tipo_material;
        document.getElementById('selTipoMaterial').dispatchEvent(new Event('change'));
    }

    // Adicionar ao collection (atualiza totais e hidden input automaticamente)
    adicionarNfAoCollection(d);

    // Auto-preencher motos se reconhecidas (apenas primeira NF)
    if (isFirstNf && d.tipo_material === 'MOTO' && d.motos_reconhecidas && d.motos_reconhecidas.length > 0) {
        const _preencherMotos = () => {
            const tbody = document.getElementById('tbodyMotos');
            if (!tbody) { setTimeout(_preencherMotos, 200); return; }
            tbody.innerHTML = '';
            motoRowIdx = 0;
            d.motos_reconhecidas.forEach((moto) => {
                adicionarLinhaMotos();
                const idx = motoRowIdx - 1;
                if (moto.modelo_moto_id) {
                    document.getElementById(`motoModelo${idx}`).value = moto.modelo_moto_id;
                    onModeloChange(idx);
                }
                document.getElementById(`motoQtd${idx}`).value = Math.round(moto.quantidade || 1);
                if (moto.valor_unitario) {
                    document.getElementById(`motoValorUnit${idx}`).value = moto.valor_unitario;
                }
                recalcularMoto(idx);
            });
        };
        setTimeout(_preencherMotos, 300);
    }

    // Feedback resumido no card de upload
    if (fb) {
        fb.innerHTML = '<div class="alert alert-success py-1 small mb-0">' +
            '<i class="fas fa-check-circle me-1"></i>' +
            _nfsCollection.length + ' NF(s) importada(s). Veja a lista abaixo.' +
            '</div>';
        fb.style.display = 'block';
    }

    // Transformar card de upload para modo "Adicionar NF"
    const cardUpload = document.getElementById('cardUploadNF');
    if (cardUpload) {
        cardUpload.style.display = '';
        document.getElementById('lblUploadNF').textContent = 'Adicionar NF';
        document.getElementById('txtUploadNF').textContent = 'Envie outro PDF (DANFE) ou XML (NF-e) para adicionar a cotacao.';
        document.getElementById('btnPrePreencher').innerHTML = '<i class="fas fa-plus"></i> Adicionar';
        document.getElementById('inpNFPrePreencher').value = '';
    }
}

/* ===== Toggle Destino Manual ===== */
let _modoDestinoManual = false;

function toggleModoDestinoManual() {
    _modoDestinoManual = !_modoDestinoManual;
    const dropdown = document.getElementById('blocoDestinoDropdown');
    const manual = document.getElementById('blocoDestinoManual');
    const btn = document.getElementById('btnToggleDestinoManual');
    const selDestino = document.getElementById('selDestino');
    const endInline = document.getElementById('enderecoEntregaInline');

    if (_modoDestinoManual) {
        dropdown.classList.add('d-none');
        manual.classList.remove('d-none');
        selDestino.removeAttribute('required');
        selDestino.removeAttribute('name');
        if (endInline) endInline.classList.add('d-none');
        btn.textContent = '\u2190 Selecionar da lista';
    } else {
        dropdown.classList.remove('d-none');
        manual.classList.add('d-none');
        selDestino.setAttribute('required', '');
        selDestino.setAttribute('name', 'endereco_destino_id');
        btn.textContent = 'Inserir manualmente';
        // Limpar campos manuais e hidden inputs
        ['manDestUf','manDestCidade','manDestCep','manDestLogradouro','manDestNumero','manDestBairro','manDestRazao'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        ['hidManDestUf','hidManDestCidade','hidManDestCep','hidManDestLogradouro','hidManDestNumero','hidManDestBairro','hidManDestRazao'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        document.getElementById('manDestFeedback').style.display = 'none';
    }
}

/* ===== Form submit: destino manual + serializar motos ===== */
document.getElementById('formCotacao').addEventListener('submit', async function(e) {
    e.preventDefault();

    // Se modo manual: criar destino provisorio via API
    if (_modoDestinoManual) {
        const cidade = (document.getElementById('manDestCidade').value || '').trim();
        const uf = (document.getElementById('manDestUf').value || '').trim().toUpperCase();
        const clienteId = parseInt(document.getElementById('selCliente').value) || 0;

        if (!cidade || !uf) {
            alert('Cidade e UF do destino sao obrigatorios.');
            return;
        }
        if (!clienteId) {
            alert('Selecione o cliente primeiro.');
            return;
        }

        const fb = document.getElementById('manDestFeedback');
        fb.innerHTML = '<small class="text-muted"><i class="fas fa-spinner fa-spin"></i> Criando destino provisorio...</small>';
        fb.style.display = 'block';

        // Copiar para hidden inputs (fallback server-side)
        document.getElementById('hidManDestUf').value = uf;
        document.getElementById('hidManDestCidade').value = cidade;
        document.getElementById('hidManDestCep').value = (document.getElementById('manDestCep').value || '').trim();
        document.getElementById('hidManDestLogradouro').value = (document.getElementById('manDestLogradouro').value || '').trim();
        document.getElementById('hidManDestNumero').value = (document.getElementById('manDestNumero').value || '').trim();
        document.getElementById('hidManDestBairro').value = (document.getElementById('manDestBairro').value || '').trim();
        document.getElementById('hidManDestRazao').value = (document.getElementById('manDestRazao').value || '').trim();

        try {
            const resp = await fetch('/carvia/api/cotacoes/destino-provisorio', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cliente_id: clienteId,
                    razao_social: document.getElementById('manDestRazao').value.trim() || null,
                    fisico: {
                        uf: uf,
                        cidade: cidade,
                        cep: document.getElementById('manDestCep').value.trim() || null,
                        logradouro: document.getElementById('manDestLogradouro').value.trim() || null,
                        numero: document.getElementById('manDestNumero').value.trim() || null,
                        bairro: document.getElementById('manDestBairro').value.trim() || null,
                    }
                })
            });
            const data = await resp.json();
            if (!data.sucesso) {
                fb.innerHTML = '<small class="text-danger"><i class="fas fa-times"></i> ' + (data.erro || 'Erro ao criar destino.') + '</small>';
                return;
            }
            // Injetar ID do destino criado no form
            let hidDest = document.getElementById('hidDestinoProvId');
            if (!hidDest) {
                hidDest = document.createElement('input');
                hidDest.type = 'hidden';
                hidDest.name = 'endereco_destino_id';
                hidDest.id = 'hidDestinoProvId';
                this.appendChild(hidDest);
            }
            hidDest.value = data.endereco_id;
            fb.innerHTML = '<small class="text-success"><i class="fas fa-check"></i> Destino provisorio criado.</small>';
        } catch (err) {
            fb.innerHTML = '<small class="text-danger"><i class="fas fa-times"></i> Erro de rede: ' + err.message + '</small>';
            return;
        }
    }

    // Serializar motos (se tipo MOTO)
    if (document.getElementById('selTipoMaterial').value === 'MOTO') {
        const motos = [];
        document.querySelectorAll('#tbodyMotos tr').forEach(tr => {
            const modeloId = parseInt(tr.querySelector('[id^="motoModelo"]')?.value);
            const qtd = parseInt(tr.querySelector('[id^="motoQtd"]')?.value);
            const valorUnit = parseFloat(tr.querySelector('[id^="motoValorUnit"]')?.value) || null;
            if (modeloId && qtd > 0) {
                motos.push({ modelo_moto_id: modeloId, quantidade: qtd, valor_unitario: valorUnit });
            }
        });

        if (motos.length === 0) {
            alert('Adicione pelo menos uma moto com modelo selecionado.');
            return;
        }
        document.getElementById('motosJson').value = JSON.stringify(motos);
    }

    // Submeter form
    this.submit();
});

/* ===== Auto-setup quando vem de NF existente ===== */
(function() {
    const nfId = CARVIA_DATA.nfIdParam;
    if (!nfId) return;

    fetch('/carvia/api/cotacoes/setup-nf-existente/' + nfId)
    .then(r => r.json())
    .then(d => {
        const fb = document.getElementById('nfExistenteFeedback');
        if (!fb) return;

        if (!d.sucesso) {
            fb.innerHTML = '<div class="alert alert-danger py-2 small mb-0">' + (d.erro || 'Erro ao carregar NF') + '</div>';
            return;
        }

        // Aviso de cotacao existente com link
        if (d.aviso_cotacao_existente && d.cotacao_existente_info) {
            const info = d.cotacao_existente_info;
            fb.innerHTML = '<div class="alert alert-warning py-2 small mb-0">' +
                '<i class="fas fa-exclamation-triangle me-1"></i> ' +
                'Esta NF ja possui cotacao ' +
                '<a href="/carvia/cotacoes/' + info.cotacao_id + '" class="fw-bold">' +
                info.numero_cotacao + '</a> (' + info.status + '). ' +
                'Continuar criara uma nova cotacao para a mesma NF.' +
                '</div>';
        } else {
            const nf = d.nf;
            fb.innerHTML = '<div class="alert alert-success py-2 small mb-0">' +
                '<i class="fas fa-check-circle me-1"></i> ' +
                '<strong>NF ' + (nf.numero_nf || '?') + '</strong> carregada — ' +
                (d.itens ? d.itens.length : 0) + ' item(ns), ' +
                'R$ ' + (nf.valor_total || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2}) +
                ', ' + (nf.peso_bruto || 0) + ' kg. Tipo: <strong>' + d.tipo_material + '</strong>' +
                '</div>';
        }

        _setupData = d;

        // Determinar quais passos do wizard sao necessarios
        _wizSteps = [];
        if (!d.cliente.existe) _wizSteps.push(1);
        if (!d.enderecos.origem_existe) _wizSteps.push(2);
        if (!d.enderecos.destino_existe) _wizSteps.push(3);

        if (_wizSteps.length > 0) {
            // Pre-preencher wizard com dados da NF do banco
            const nf = d.nf;

            // Ajuste 1: se cliente existe, usar nome cadastrado (nao sobrescrever com NF)
            if (d.cliente.existe && d.cliente.nome) {
                document.getElementById('wizNomeCliente').value = d.cliente.nome;
            } else {
                document.getElementById('wizNomeCliente').value = nf.nome_emitente || '';
            }
            document.getElementById('wizOrigCnpj').value = nf.cnpj_emitente || '';
            document.getElementById('wizOrigRazao').value = nf.nome_emitente || '';
            document.getElementById('wizDestCnpj').value = nf.cnpj_destinatario || '';
            document.getElementById('wizDestRazao').value = nf.nome_destinatario || '';

            // Pre-preencher enderecos da Receita ou fallback NF
            const re = d.receita_emitente;
            const rd = d.receita_destinatario;
            const fbNfEx = document.getElementById('nfExistenteFeedback');

            if (re) {
                document.getElementById('wizOrigLogradouro').value = re.logradouro || '';
                document.getElementById('wizOrigNumero').value = re.numero || '';
                document.getElementById('wizOrigBairro').value = re.bairro || '';
                document.getElementById('wizOrigCidade').value = re.cidade || '';
                document.getElementById('wizOrigUf').value = re.uf || '';
                document.getElementById('wizOrigCep').value = re.cep || '';
                document.getElementById('wizOrigComplemento').value = re.complemento || '';
            } else {
                document.getElementById('wizOrigCidade').value = nf.cidade_emitente || '';
                document.getElementById('wizOrigUf').value = nf.uf_emitente || '';
            }
            if (rd) {
                document.getElementById('wizDestLogradouro').value = rd.logradouro || '';
                document.getElementById('wizDestNumero').value = rd.numero || '';
                document.getElementById('wizDestBairro').value = rd.bairro || '';
                document.getElementById('wizDestCidade').value = rd.cidade || '';
                document.getElementById('wizDestUf').value = rd.uf || '';
                document.getElementById('wizDestCep').value = rd.cep || '';
                document.getElementById('wizDestComplemento').value = rd.complemento || '';
            } else {
                document.getElementById('wizDestCidade').value = nf.cidade_destinatario || '';
                document.getElementById('wizDestUf').value = nf.uf_destinatario || '';
                if (d.receita_destinatario_erro && fbNfEx) {
                    fbNfEx.innerHTML += '<div class="alert alert-warning py-1 small mb-2 mt-2">' +
                        '<i class="fas fa-exclamation-triangle me-1"></i>' +
                        '<strong>Destinatario:</strong> ' + d.receita_destinatario_erro +
                        '. Preencha o endereco manualmente.</div>';
                }
            }
            if (!re && d.receita_emitente_erro && fbNfEx) {
                fbNfEx.innerHTML += '<div class="alert alert-warning py-1 small mb-2 mt-2">' +
                    '<i class="fas fa-exclamation-triangle me-1"></i>' +
                    '<strong>Emitente:</strong> ' + d.receita_emitente_erro +
                    '. Preencha o endereco manualmente.</div>';
            }

            _wizStep = 0;
            wizMostrarPasso(_wizSteps[0]);
            new bootstrap.Modal(document.getElementById('modalWizardNF')).show();
        } else {
            // Cliente e enderecos ja existem — preencher form direto
            aplicarDadosNF(d);
            aplicarRestricoesTardia();
        }
    })
    .catch(err => {
        const fb = document.getElementById('nfExistenteFeedback');
        if (fb) {
            fb.innerHTML = '<div class="alert alert-danger py-2 small mb-0">Erro ao carregar NF: ' + err.message + '</div>';
        }
    });
})();

/* ===== Criacao Tardia: lock campos apos setup ===== */
function aplicarRestricoesTardia() {
    if (!CARVIA_DATA.criacaoTardia || !_setupData) return;

    const cteInfo = _setupData.cte_info;
    if (!cteInfo || !cteInfo.tem_cte) return;

    // Info CTe no card de feedback
    const fb = document.getElementById('nfExistenteFeedback');
    if (fb) {
        const valorFmt = cteInfo.cte_valor_total.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
        fb.innerHTML += '<div class="alert alert-info py-1 small mb-0 mt-2">' +
            '<i class="fas fa-file-invoice-dollar me-1"></i>' +
            '<strong>Valor CTe:</strong> ' + valorFmt + ' (' + cteInfo.qtd_ctes + ' CTe' +
            (cteInfo.qtd_ctes > 1 ? 's' : '') + ') — sera usado como valor vendido.' +
            '</div>';
    }

    // Desabilitar campos que nao podem ser alterados na criacao tardia
    const camposReadonly = [
        'selCliente', 'selTipoMaterial',
    ];
    camposReadonly.forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.disabled = true; }
    });

    // Esconder secao de upload de NF adicional (nao faz sentido na tardia)
    const cardUpload = document.getElementById('cardUploadNF');
    if (cardUpload) cardUpload.style.display = 'none';
}

/* ===== Condicoes Comerciais: toggle campos ===== */
function togglePrazoDias() {
    const v = document.getElementById('selCondicaoPgto').value;
    document.getElementById('blocoPrazoDias').style.display = v === 'PRAZO' ? '' : 'none';
    if (v !== 'PRAZO') document.getElementById('inpPrazoDias').value = '';
}

function togglePercentuais() {
    const v = document.getElementById('selResponsavelFrete').value;
    const remEl = document.getElementById('inpPctRem');
    const destEl = document.getElementById('inpPctDest');
    const showCustom = v === 'PERSONALIZADO';
    document.getElementById('blocoPercentualRem').style.display = showCustom ? '' : 'none';
    document.getElementById('blocoPercentualDest').style.display = showCustom ? '' : 'none';

    if (v === '100_REMETENTE') { remEl.value = '100'; destEl.value = '0'; }
    else if (v === '100_DESTINATARIO') { remEl.value = '0'; destEl.value = '100'; }
    else if (v === '50_50') { remEl.value = '50'; destEl.value = '50'; }
    else if (!v) { remEl.value = ''; destEl.value = ''; }
}
