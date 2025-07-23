/**
 * 📍 MODAL DE ENDEREÇO/INCOTERM
 * Responsável pela exibição dos detalhes de endereço quando clica no incoterm
 */

class ModalEndereco {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Modal Endereço inicializado');
    }

    async abrirModalEndereco(numPedido) {
        console.log(`📍 Abrindo modal de endereço para pedido ${numPedido}`);
        
        // Criar modal se não existir
        this.criarModalSeNecessario();
        
        try {
            // Buscar dados do endereço
            const response = await fetch(`/carteira/api/pedido/${numPedido}/endereco`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar dados do endereço');
            }

            // Preencher dados do modal
            this.preencherDadosEndereco(data);
            
            // Mostrar modal
            const modalElement = document.getElementById('modalEndereco');
            if (!window._modalEndereco) {
                window._modalEndereco = new bootstrap.Modal(modalElement);
            }
            window._modalEndereco.show();

        } catch (error) {
            console.error('Erro ao carregar endereço:', error);
            alert(`❌ Erro ao carregar dados do endereço: ${error.message}`);
        }
    }

    criarModalSeNecessario() {
        if (document.getElementById('modalEndereco')) {
            return; // Modal já existe
        }

        const modal = document.createElement('div');
        modal.id = 'modalEndereco';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('role', 'dialog');
        modal.innerHTML = this.renderizarModalEndereco();
        
        document.body.appendChild(modal);
    }

    renderizarModalEndereco() {
        return `
            <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-map-marker-alt"></i> Detalhes do Endereço
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <!-- Dados do Cliente -->
                            <div class="col-md-6">
                                <div class="card h-100">
                                    <div class="card-header bg-primary text-white">
                                        <h6 class="mb-0">
                                            <i class="fas fa-user"></i> Cliente
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <ul class="list-unstyled">
                                            <li class="mb-2">
                                                <strong>Razão Social:</strong><br>
                                                <span id="modal_razao_social"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>CNPJ:</strong><br>
                                                <span id="modal_cnpj_cliente"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>UF:</strong> <span id="modal_cliente_uf"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>Município:</strong><br>
                                                <span id="modal_cliente_municipio"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>Incoterm:</strong><br>
                                                <span id="modal_incoterm" class="badge bg-info"></span>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Endereço de Entrega -->
                            <div class="col-md-6">
                                <div class="card h-100">
                                    <div class="card-header bg-success text-white">
                                        <h6 class="mb-0">
                                            <i class="fas fa-shipping-fast"></i> Endereço de Entrega
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <ul class="list-unstyled">
                                            <li class="mb-2">
                                                <strong>Empresa:</strong><br>
                                                <span id="modal_empresa_endereco"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>CNPJ:</strong><br>
                                                <span id="modal_cnpj_endereco"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>UF:</strong> <span id="modal_uf_endereco"></span>
                                                <strong class="ms-3">Cidade:</strong> <span id="modal_municipio_endereco"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>Bairro:</strong><br>
                                                <span id="modal_bairro_endereco"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>CEP:</strong> <span id="modal_cep_endereco"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>Endereço:</strong><br>
                                                <span id="modal_rua_endereco"></span>
                                            </li>
                                            <li class="mb-2">
                                                <strong>Telefone:</strong><br>
                                                <span id="modal_telefone_endereco"></span>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Informações Adicionais -->
                        <div class="row mt-3">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header bg-info text-white">
                                        <h6 class="mb-0">
                                            <i class="fas fa-info-circle"></i> Informações do Pedido
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row">
                                            <div class="col-md-4">
                                                <strong>Pedido:</strong><br>
                                                <span id="modal_num_pedido" class="badge bg-primary"></span>
                                            </div>
                                            <div class="col-md-4">
                                                <strong>Vendedor:</strong><br>
                                                <span id="modal_vendedor"></span>
                                            </div>
                                            <div class="col-md-4">
                                                <strong>Equipe:</strong><br>
                                                <span id="modal_equipe_vendas"></span>
                                            </div>
                                        </div>
                                        <div class="row mt-2">
                                            <div class="col-md-6">
                                                <strong>Rota:</strong><br>
                                                <span id="modal_rota"></span>
                                            </div>
                                            <div class="col-md-6">
                                                <strong>Sub-rota:</strong><br>
                                                <span id="modal_sub_rota"></span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-1"></i> Fechar
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    preencherDadosEndereco(data) {
        // Dados do cliente
        document.getElementById('modal_razao_social').textContent = data.raz_social || '-';
        document.getElementById('modal_cnpj_cliente').textContent = this.formatarCNPJ(data.cnpj_cpf) || '-';
        document.getElementById('modal_cliente_uf').textContent = data.estado || '-';
        document.getElementById('modal_cliente_municipio').textContent = data.municipio || '-';
        document.getElementById('modal_incoterm').textContent = data.incoterm || 'N/A';

        // Dados do endereço de entrega
        document.getElementById('modal_empresa_endereco').textContent = data.empresa_endereco_ent || '-';
        document.getElementById('modal_cnpj_endereco').textContent = this.formatarCNPJ(data.cnpj_endereco_ent) || '-';
        document.getElementById('modal_uf_endereco').textContent = data.cod_uf || '-';
        document.getElementById('modal_municipio_endereco').textContent = data.nome_cidade || '-';
        document.getElementById('modal_bairro_endereco').textContent = data.bairro_endereco_ent || '-';
        document.getElementById('modal_cep_endereco').textContent = this.formatarCEP(data.cep_endereco_ent) || '-';

        // Combinar rua e número
        let enderecoCompleto = '';
        if (data.rua_endereco_ent && data.endereco_ent) {
            enderecoCompleto = `${data.rua_endereco_ent}, ${data.endereco_ent}`;
        } else if (data.rua_endereco_ent) {
            enderecoCompleto = data.rua_endereco_ent;
        } else if (data.endereco_ent) {
            enderecoCompleto = data.endereco_ent;
        }
        document.getElementById('modal_rua_endereco').textContent = enderecoCompleto || '-';

        document.getElementById('modal_telefone_endereco').textContent = this.formatarTelefone(data.telefone_endereco_ent) || '-';

        // Informações do pedido
        document.getElementById('modal_num_pedido').textContent = data.num_pedido || '-';
        document.getElementById('modal_vendedor').textContent = data.vendedor || '-';
        document.getElementById('modal_equipe_vendas').textContent = data.equipe_vendas || '-';
        document.getElementById('modal_rota').textContent = data.rota || '-';
        document.getElementById('modal_sub_rota').textContent = data.sub_rota || '-';
    }

    // Utilitários de formatação
    formatarCNPJ(cnpj) {
        if (!cnpj) return null;
        const digits = cnpj.replace(/\D/g, '');
        if (digits.length === 14) {
            return digits.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        return cnpj;
    }

    formatarCEP(cep) {
        if (!cep) return null;
        const digits = cep.replace(/\D/g, '');
        if (digits.length === 8) {
            return digits.replace(/(\d{5})(\d{3})/, '$1-$2');
        }
        return cep;
    }

    formatarTelefone(telefone) {
        if (!telefone) return null;
        const digits = telefone.replace(/\D/g, '');
        if (digits.length === 11) {
            return digits.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        } else if (digits.length === 10) {
            return digits.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
        }
        return telefone;
    }

    formatarData(dataStr) {
        const data = new Date(dataStr);
        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }
}

// Disponibilizar globalmente
window.ModalEndereco = ModalEndereco;