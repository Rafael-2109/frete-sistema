/**
 * Modal de Projecao de Estoque por Linha de Producao (D0-D14)
 * Exibe Saida, Producao e Saldo dia-a-dia para todos os produtos
 * da mesma linha de producao do item clicado.
 */

class ModalProjecaoLinha {
    constructor() {
        console.log('ModalProjecaoLinha inicializado');
    }

    async abrir(codProduto) {
        try {
            const response = await fetch(`/carteira/api/produto/${codProduto}/projecao-linha`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                alert(data.error || 'Erro ao carregar projecao por linha');
                return;
            }

            this.mostrarModal(data);
        } catch (error) {
            console.error('Erro ao carregar projecao por linha:', error);
            alert(`Erro ao carregar projecao: ${error.message}`);
        }
    }

    mostrarModal(data) {
        const modalId = `modal-projecao-linha-${Date.now()}`;

        // Remover modal anterior se houver
        const existentes = document.querySelectorAll('[id^="modal-projecao-linha-"]');
        existentes.forEach(m => m.remove());

        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = this._renderizar(data);

        document.body.appendChild(modal);

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.addEventListener('hidden.bs.modal', () => {
            setTimeout(() => {
                if (modal.parentNode) modal.remove();
            }, 100);
        });
    }

    _renderizar(data) {
        const { linha_producao, cod_produto_clicado, datas, produtos } = data;

        // Formatar datas para header (DD/MM e dia da semana abreviado)
        const diasSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'];
        const headerDatas = datas.map((iso, i) => {
            const d = new Date(iso + 'T12:00:00');
            const dd = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const ds = diasSemana[d.getDay()];
            return `<th class="plinha-cell text-center" title="${iso}">
                <div style="font-size:8px;color:var(--bs-secondary-color)">${ds}</div>
                <div>D${i}</div>
                <div style="font-size:8px">${dd}/${mm}</div>
            </th>`;
        }).join('');

        // Renderizar linhas de cada produto
        const linhasProdutos = produtos.map(prod => {
            const isClicado = prod.cod_produto === cod_produto_clicado;
            const classeHeader = isClicado ? 'plinha-produto-header plinha-clicado' : 'plinha-produto-header';

            // Header do produto (nome + estoque atual)
            const headerProd = `<tr class="${classeHeader}">
                <td colspan="2" style="font-size:10px">
                    <strong>${this._escape(prod.cod_produto)}</strong> - ${this._escape(prod.nome_produto)}
                    <span style="margin-left:8px;font-weight:400;color:var(--bs-secondary-color)">
                        Est.Atual: ${prod.estoque_atual}
                    </span>
                </td>
                <td colspan="${datas.length}"></td>
            </tr>`;

            // L1: Saida
            const celsSaida = prod.saida.map(v =>
                `<td class="plinha-cell">${v || ''}</td>`
            ).join('');
            const linhaSaida = `<tr>
                <td></td>
                <td class="plinha-row-label">Saida</td>
                ${celsSaida}
            </tr>`;

            // L2: Producao
            const celsProducao = prod.producao.map(v => {
                const classe = v > 0 ? 'plinha-cell plinha-producao-ativa' : 'plinha-cell';
                return `<td class="${classe}">${v || ''}</td>`;
            }).join('');
            const linhaProducao = `<tr>
                <td></td>
                <td class="plinha-row-label">Prod.</td>
                ${celsProducao}
            </tr>`;

            // L3: Saldo
            const celsSaldo = prod.saldo.map(v => {
                let classe = 'plinha-cell';
                if (v < 0) {
                    classe += ' plinha-negativo';
                }
                return `<td class="${classe}">${Math.round(v)}</td>`;
            }).join('');
            const linhaSaldo = `<tr class="plinha-saldo">
                <td></td>
                <td class="plinha-row-label" style="font-weight:700">Saldo</td>
                ${celsSaldo}
            </tr>`;

            // Separador
            const separador = `<tr class="plinha-separator"><td colspan="${datas.length + 2}"></td></tr>`;

            return headerProd + linhaSaida + linhaProducao + linhaSaldo + separador;
        }).join('');

        return `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header py-2">
                    <h6 class="modal-title" style="font-size:12px">
                        Projecao por Linha: <strong>${this._escape(linha_producao)}</strong>
                        <span style="font-weight:400;color:var(--bs-secondary-color);margin-left:8px">
                            ${produtos.length} produto${produtos.length !== 1 ? 's' : ''} | D0-D14
                        </span>
                    </h6>
                    <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body p-2" style="overflow-x:auto">
                    <table class="table table-sm table-bordered mb-0" style="font-size:10px;line-height:1.1">
                        <thead>
                            <tr style="background-color:var(--bs-tertiary-bg)">
                                <th style="min-width:30px"></th>
                                <th style="min-width:45px;font-size:9px">Tipo</th>
                                ${headerDatas}
                            </tr>
                        </thead>
                        <tbody>
                            ${linhasProdutos}
                        </tbody>
                    </table>
                </div>
                <div class="modal-footer py-1">
                    <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Fechar</button>
                </div>
            </div>
        </div>`;
    }

    _escape(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

window.modalProjecaoLinha = new ModalProjecaoLinha();
