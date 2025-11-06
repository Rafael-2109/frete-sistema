# 🚀 Implementação purchase_state e Novo Layout de Requisições

**Data**: 05/11/2025

---

## ✅ COMPLETO

### 1. **Modelo** ([app/manufatura/models.py:194-196](app/manufatura/models.py:194))
```python
purchase_state = db.Column(db.String(20), index=True)
```

### 2. **Sincronização** ([app/odoo/services/requisicao_compras_service.py](app/odoo/services/requisicao_compras_service.py))
- ✅ Linha 235: Adiciona do `purchase_state` nos fields
- ✅ Linha 539: Extrai purchase_state
- ✅ Linha 551: Salva na criação
- ✅ Linha 639-647: Atualiza na sincronização

### 3. **Scripts de Migração**
- ✅ [`scripts/adicionar_purchase_state_requisicao.sql`](scripts/adicionar_purchase_state_requisicao.sql)
- ✅ [`scripts/adicionar_purchase_state_requisicao.py`](scripts/adicionar_purchase_state_requisicao.py)

### 4. **Rota Agrupada** ([app/manufatura/routes/requisicao_compras_routes.py:19-164](app/manufatura/routes/requisicao_compras_routes.py:19))
- ✅ Agrupa por `num_requisicao`
- ✅ Busca pedidos vinculados
- ✅ Paginação manual

---

## 🔴 PENDENTE: Template

### Layout Esperado:

```html
┌─ REQ/FB/05614 - 30/10/2025 ──────────────────────────────────────┐
│ Solicitante: João Silva | Status: Aprovada                       │
├────┬───────┬───────────────────────────┬──────┬──────────┬───────┤
│ ▼  │ Neces │ [Código] Produto          │ Qtd  │ Status   │ Pedido│
├────┼───────┼───────────────────────────┼──────┼──────────┼───────┤
│ >  │05/11  │ [101001] COGUMELO FATIADO │ 100  │ Pedido   │ C2511 │
│    │       │                           │      │ Compras  │ 30/10 │
├────┴───────┴───────────────────────────┴──────┴──────────┴───────┤
│    [Projeção expandida ao clicar]                                │
└───────────────────────────────────────────────────────────────────┘
│ >  │05/11  │ [101002] AZEITONA VERDE   │ 200  │ Aprovada │ -     │
└────┴───────┴───────────────────────────┴──────┴──────────┴───────┘
```

### Código do Template:

```html
{% for req in requisicoes %}
<!-- Cabeçalho da Requisição -->
<div class="card mb-2">
    <div class="card-header bg-light py-2">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <strong>{{ req.num_requisicao }}</strong>
                <span class="text-muted">- {{ req.data_criacao.strftime('%d/%m/%Y') if req.data_criacao else '-' }}</span>
            </div>
            <div class="text-muted small">
                {{ req.usuario or 'Sistema' }} |
                <span class="badge bg-{% if req.status == 'Aprovada' %}success{% else %}secondary{% endif %}">
                    {{ req.status }}
                </span>
            </div>
        </div>
    </div>

    <!-- Linhas da Requisição -->
    <div class="card-body p-0">
        <table class="table table-sm table-hover mb-0">
            <thead class="table-light">
                <tr>
                    <th style="width: 30px;"></th>
                    <th style="width: 80px;">Necessid.</th>
                    <th>Produto</th>
                    <th class="text-end" style="width: 100px;">Qtd</th>
                    <th style="width: 120px;">Status</th>
                    <th style="width: 140px;">Pedido</th>
                </tr>
            </thead>
            <tbody>
                {% for linha in req.linhas %}
                <tr class="linha-produto" data-linha-id="{{ linha.id }}">
                    <td class="text-center">
                        {% if linha.data_necessidade %}
                        <button class="btn btn-sm btn-link p-0 btn-toggle-projecao">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                        {% endif %}
                    </td>
                    <td>
                        {% if linha.data_necessidade %}
                        {{ linha.data_necessidade.strftime('%d/%m') }}
                        {% else %}
                        <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                    <td>
                        <small class="text-muted d-block">[{{ linha.cod_produto }}]</small>
                        <span>{{ linha.nome_produto }}</span>
                    </td>
                    <td class="text-end">
                        {{ linha.qtd|qtd_br(2) }}
                    </td>
                    <td>
                        {% if linha.purchase_state == 'purchase' %}
                        <span class="badge bg-success">Pedido Compras</span>
                        {% elif linha.purchase_state == 'to approve' %}
                        <span class="badge bg-warning">A Aprovar</span>
                        {% elif linha.purchase_state == 'draft' %}
                        <span class="badge bg-secondary">SDC</span>
                        {% else %}
                        <span class="badge bg-secondary">{{ linha.purchase_state or 'N/A' }}</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if linha.pedido %}
                        <a href="{{ url_for('pedidos_compras.index') }}" target="_blank">
                            {{ linha.pedido.num_pedido }}
                        </a>
                        <br><small class="text-muted">{{ linha.pedido.data_pedido.strftime('%d/%m/%Y') if linha.pedido.data_pedido else '-' }}</small>
                        {% else %}
                        <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                </tr>

                <!-- Linha Expansível com Projeção -->
                {% if linha.data_necessidade %}
                <tr class="projecao-row collapse" id="projecao-{{ linha.id }}">
                    <td colspan="6" class="p-0">
                        <div class="p-2 bg-light">
                            <div class="projecao-content">
                                <span class="spinner-border spinner-border-sm"></span> Carregando...
                            </div>
                        </div>
                    </td>
                </tr>
                {% endif %}
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endfor %}
```

---

## 🛠️ PASSOS PARA FINALIZAR

### 1. **Rodar Migração**
```bash
python scripts/adicionar_purchase_state_requisicao.py
```

### 2. **Sincronizar Requisições**
```
/manufatura/requisicoes-compras/sincronizar-manual
```

### 3. **Substituir Template**
Substituir arquivo [`app/templates/manufatura/requisicoes_compras/listar.html`](app/templates/manufatura/requisicoes_compras/listar.html) pelo código acima

### 4. **Ajustar JavaScript**
- Botão toggle agora é `.btn-toggle-projecao` dentro de `.linha-produto`
- `data-linha-id` em vez de `data-requisicao-id`

---

## 📝 OBSERVAÇÕES

- **purchase_state** valores do Odoo:
  - `draft`: SDC
  - `sent`: SDC enviada
  - `to approve`: A ser aprovado
  - `purchase`: Pedido de compra
  - `done`: Travado
  - `cancel`: Cancelado

- **Layout compacto**: Cabeçalho em 1 linha, tabela sem bordas pesadas

- **Pedido vinculado**: Via `RequisicaoCompraAlocacao` com link e data
