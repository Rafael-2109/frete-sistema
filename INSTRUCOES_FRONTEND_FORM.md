# 🔧 INSTRUÇÕES PARA ATUALIZAR form.html

**Arquivo**: `app/templates/motochefe/vendas/pedidos/form.html`

---

## ⚠️ ALTERAÇÕES NECESSÁRIAS

### 1. SUBSTITUIR BLOCO DE CLIENTE/VENDEDOR/EQUIPE (linhas 46-74)

**REMOVER**:
```html
<div class="row">
    <div class="col-md-4 mb-3">
        <label class="form-label">Cliente *</label>
        <select name="cliente_id" class="form-select" required>
            ...
        </select>
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Vendedor *</label>
        <select name="vendedor_id" class="form-select" required>
            ...
        </select>
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Equipe de Vendas</label>
        <select name="equipe_vendas_id" class="form-select">
            ...
        </select>
    </div>
</div>
```

**ADICIONAR**:
```html
<div class="row">
    <div class="col-md-4 mb-3">
        <label class="form-label">Equipe de Vendas *</label>
        <select name="equipe_vendas_id" id="sel_equipe" class="form-select" required>
            <option value="">Selecione...</option>
            {% for e in equipes %}
            <option value="{{ e.id }}"
                    data-permitir-prazo="{{ e.permitir_prazo|lower }}"
                    data-permitir-parcelamento="{{ e.permitir_parcelamento|lower }}"
                    data-permitir-montagem="{{ e.permitir_montagem|lower }}">
                {{ e.equipe_vendas }}
            </option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Vendedor *</label>
        <select name="vendedor_id" id="sel_vendedor" class="form-select" required disabled>
            <option value="">Selecione equipe primeiro...</option>
        </select>
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Cliente *</label>
        <select name="cliente_id" id="sel_cliente" class="form-select" required disabled>
            <option value="">Selecione vendedor primeiro...</option>
        </select>
    </div>
</div>
```

---

### 2. REMOVER CAMPOS DE PAGAMENTO (linhas 76-89)

**REMOVER COMPLETAMENTE**:
```html
<div class="row">
    <div class="col-md-4 mb-3">
        <label class="form-label">Forma Pagamento</label>
        <input type="text" name="forma_pagamento" class="form-control" placeholder="Ex: Boleto, Cartão">
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Condição Pagamento</label>
        <input type="text" name="condicao_pagamento" class="form-control" placeholder="Ex: 10x sem juros">
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Valor Frete Cliente</label>
        <input type="number" step="0.01" name="valor_frete_cliente" class="form-control" value="0">
    </div>
</div>
```

---

### 3. ADICIONAR CAMPO DE PRAZO CONDICIONAL

**ADICIONAR APÓS** remoção dos campos de pagamento:

```html
<!-- Campo de Prazo (condicional) -->
<div class="row" id="div_prazo" style="display: none;">
    <div class="col-md-4 mb-3">
        <label class="form-label">Prazo (dias) *</label>
        <input type="number" name="prazo_dias" id="input_prazo" class="form-control" min="0" value="0">
        <small class="text-muted">Dias após data de expedição</small>
    </div>
</div>
```

---

### 4. ATUALIZAR BLOCO DE FRETE (linhas 91-109)

**SUBSTITUIR**:
```html
<div class="row">
    <div class="col-md-4 mb-3">
        <label class="form-label">Transportadora</label>
        <select name="transportadora_id" class="form-select">
            ...
        </select>
    </div>
    <div class="col-md-6 mb-3">
        <label class="form-label">Tipo Frete</label>
        <select name="tipo_frete" class="form-select">
            ...
        </select>
    </div>
</div>
```

**POR**:
```html
<div class="row">
    <div class="col-md-3 mb-3">
        <label class="form-label">Valor Frete Cliente</label>
        <input type="number" step="0.01" name="valor_frete_cliente" id="input_frete" class="form-control" value="0">
    </div>
    <div class="col-md-3 mb-3">
        <label class="form-label">Transportadora</label>
        <select name="transportadora_id" class="form-select">
            <option value="">Selecione...</option>
            {% for t in transportadoras %}
            <option value="{{ t.id }}">{{ t.transportadora }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-3 mb-3" id="div_tipo_frete">
        <label class="form-label">Tipo Frete</label>
        <select name="tipo_frete" id="sel_tipo_frete" class="form-select">
            <option value="">Selecione...</option>
            <option value="CIF">CIF</option>
            <option value="FOB">FOB</option>
        </select>
    </div>
</div>
```

---

### 5. SUBSTITUIR CAMPO DE COR (linha ~142)

**REMOVER**:
```html
<div class="col-md-2 mb-3">
    <label class="form-label">Cor</label>
    <input type="text" id="txt_cor" class="form-control" placeholder="Ex: Vermelho">
</div>
```

**ADICIONAR**:
```html
<div class="col-md-3 mb-3">
    <label class="form-label">Cor *</label>
    <select id="sel_cor" class="form-select" required>
        <option value="">Selecione modelo primeiro...</option>
    </select>
</div>
```

---

### 6. MARCAR CAMPOS DE MONTAGEM (linha ~154-163)

**ENVOLVER EM DIV** com ID:

```html
<div id="div_montagem">
    <div class="row">
        <div class="col-md-3 mb-3">
            <div class="form-check">
                <input type="checkbox" id="chk_montagem" class="form-check-input">
                <label class="form-check-label">Montagem Contratada</label>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <label class="form-label">Valor Montagem</label>
            <input type="number" step="0.01" id="txt_valor_montagem" class="form-control" disabled>
        </div>
        <div class="col-md-3 d-flex align-items-end">
            <button type="button" class="btn btn-primary" onclick="adicionarItem()">
                <i class="fas fa-plus"></i> Adicionar Item
            </button>
        </div>
    </div>
</div>
```

---

### 7. MARCAR SEÇÃO DE PARCELAS (linha ~204-225)

**ENVOLVER EM DIV** com ID:

```html
<div id="div_parcelas" style="display: none;">
    <hr class="my-4">
    <h5 class="mb-3"><i class="fas fa-calendar-alt"></i> Parcelamento</h5>
    <div class="card mb-3">
        <div class="card-body">
            <button type="button" class="btn btn-sm btn-primary" onclick="adicionarParcela()">
                <i class="fas fa-plus"></i> Adicionar Parcela
            </button>
            ...
        </div>
    </div>
</div>
```

---

### 8. JAVASCRIPT - ADICIONAR CASCATA (após linha 240)

**ADICIONAR NO INÍCIO DO `<script>`**:

```javascript
let itens = [];
let parcelas = [];
let cliente_crossdocking = false; // 🆕 ADICIONAR

// 🆕 CASCATA: Equipe → Vendedor
document.getElementById('sel_equipe').addEventListener('change', async function() {
    const equipeId = this.value;
    const selVendedor = document.getElementById('sel_vendedor');
    const selCliente = document.getElementById('sel_cliente');

    // Resetar vendedor e cliente
    selVendedor.innerHTML = '<option value="">Carregando...</option>';
    selVendedor.disabled = true;
    selCliente.innerHTML = '<option value="">Selecione vendedor primeiro...</option>';
    selCliente.disabled = true;

    if (!equipeId) {
        selVendedor.innerHTML = '<option value="">Selecione equipe primeiro...</option>';
        return;
    }

    // Buscar vendedores da equipe
    const response = await fetch(`/motochefe/api/vendedores-por-equipe?equipe_id=${equipeId}`);
    const vendedores = await response.json();

    selVendedor.innerHTML = '<option value="">Selecione...</option>';
    vendedores.forEach(v => {
        selVendedor.innerHTML += `<option value="${v.id}">${v.vendedor}</option>`;
    });
    selVendedor.disabled = false;

    // ✅ APLICAR regras de montagem e parcelamento
    const option = this.options[this.selectedIndex];
    const permitirMontagem = option.dataset.permitirMontagem === 'true';
    const permitirPrazo = option.dataset.permitirPrazo === 'true';
    const permitirParcelamento = option.dataset.permitirParcelamento === 'true';

    // Mostrar/ocultar montagem
    const divMontagem = document.getElementById('div_montagem');
    if (divMontagem) {
        divMontagem.style.display = permitirMontagem ? 'block' : 'none';
    }

    // Mostrar/ocultar prazo e parcelamento
    const divPrazo = document.getElementById('div_prazo');
    const divParcelas = document.getElementById('div_parcelas');

    if (!permitirPrazo) {
        if (divPrazo) divPrazo.style.display = 'none';
        if (divParcelas) divParcelas.style.display = 'none';
    } else if (permitirParcelamento) {
        if (divPrazo) divPrazo.style.display = 'block';
        if (divParcelas) divParcelas.style.display = 'block';
    } else {
        if (divPrazo) divPrazo.style.display = 'block';
        if (divParcelas) divParcelas.style.display = 'none';
    }
});

// 🆕 CASCATA: Vendedor → Cliente
document.getElementById('sel_vendedor').addEventListener('change', async function() {
    const vendedorId = this.value;
    const selCliente = document.getElementById('sel_cliente');

    selCliente.innerHTML = '<option value="">Carregando...</option>';
    selCliente.disabled = true;

    if (!vendedorId) {
        selCliente.innerHTML = '<option value="">Selecione vendedor primeiro...</option>';
        return;
    }

    const response = await fetch(`/motochefe/api/clientes-por-vendedor?vendedor_id=${vendedorId}`);
    const clientes = await response.json();

    selCliente.innerHTML = '<option value="">Selecione...</option>';
    clientes.forEach(c => {
        selCliente.innerHTML += `<option value="${c.id}" data-crossdocking="${c.crossdocking}">${c.cliente} - ${c.cnpj}</option>`;
    });
    selCliente.disabled = false;
});

// 🆕 EVENTO: Cliente → CrossDocking
document.getElementById('sel_cliente').addEventListener('change', function() {
    const option = this.options[this.selectedIndex];
    cliente_crossdocking = option.dataset.crossdocking === 'true';

    // Mostrar/ocultar tipo_frete baseado em crossdocking
    const divTipoFrete = document.getElementById('div_tipo_frete');
    if (divTipoFrete) {
        divTipoFrete.style.display = cliente_crossdocking ? 'none' : 'block';
    }
});
```

---

### 9. JAVASCRIPT - ATUALIZAR BUSCA DE ESTOQUE (linha ~245)

**SUBSTITUIR**:
```javascript
document.getElementById('sel_modelo').addEventListener('change', async function() {
    const modeloId = this.value;
    const precoTabela = this.options[this.selectedIndex]?.dataset.preco || 0;
    document.getElementById('txt_preco').value = precoTabela;

    if (!modeloId) {
        document.getElementById('div_estoque').innerHTML = '<small class="text-muted">Selecione um modelo</small>';
        return;
    }

    const response = await fetch(\`{{ url_for('motochefe.api_estoque_modelo') }}?modelo_id=\${modeloId}\`);
    const estoque = await response.json();

    if (estoque.length === 0) {
        document.getElementById('div_estoque').innerHTML = '<small class="text-danger">Sem estoque</small>';
    } else {
        document.getElementById('div_estoque').innerHTML = estoque.map(e =>
            \`<span class="badge bg-success me-1">\${e.cor}: \${e.quantidade}</span>\`
        ).join('');
    }
});
```

**POR**:
```javascript
document.getElementById('sel_modelo').addEventListener('change', async function() {
    const modeloId = this.value;
    const precoTabela = this.options[this.selectedIndex]?.dataset.preco || 0;
    document.getElementById('txt_preco').value = precoTabela;

    const selCor = document.getElementById('sel_cor');

    if (!modeloId) {
        selCor.innerHTML = '<option value="">Selecione modelo primeiro...</option>';
        selCor.disabled = true;
        return;
    }

    // Buscar cores disponíveis
    const response = await fetch(`/motochefe/api/cores-disponiveis?modelo_id=${modeloId}`);
    const cores = await response.json();

    if (cores.length === 0) {
        selCor.innerHTML = '<option value="">Sem estoque disponível</option>';
        selCor.disabled = true;
    } else {
        selCor.innerHTML = '<option value="">Selecione...</option>';
        cores.forEach(c => {
            selCor.innerHTML += `<option value="${c.cor}">${c.label}</option>`;
        });
        selCor.disabled = false;
    }
});
```

---

### 10. JAVASCRIPT - ATUALIZAR adicionarItem() (linha ~274)

**SUBSTITUIR**:
```javascript
const cor = document.getElementById('txt_cor').value;
```

**POR**:
```javascript
const selCor = document.getElementById('sel_cor');
const cor = selCor.value;
```

---

### 11. JAVASCRIPT - CORRIGIR atualizarTabelaItens() (linha ~310)

**SUBSTITUIR**:
```javascript
const total = itens.reduce((sum, item) => sum + item.total, 0);
document.getElementById('td_total').textContent = 'R$ ' + total.toFixed(2);
document.getElementById('valor_total_pedido').value = total.toFixed(2);
```

**POR**:
```javascript
const totalItens = itens.reduce((sum, item) => sum + item.total, 0);
const frete = parseFloat(document.getElementById('input_frete')?.value || 0);
const totalComFrete = totalItens + frete;

document.getElementById('td_total').textContent = 'R$ ' + totalComFrete.toFixed(2);
document.getElementById('valor_total_pedido').value = totalComFrete.toFixed(2);
```

**E ADICIONAR** listener no frete (após a função):
```javascript
// Listener no frete
document.getElementById('input_frete').addEventListener('input', atualizarTabelaItens);
```

---

### 12. JAVASCRIPT - CORRIGIR adicionarParcela() (linha ~352)

**SUBSTITUIR**:
```javascript
function adicionarParcela() {
    const numero = parcelas.length + 1;
    const total = parseFloat(document.getElementById('valor_total_pedido').value || 0);
    const valor = total > 0 ? (total / (numero)).toFixed(2) : 0;

    parcelas.push({
        numero: numero,
        valor: parseFloat(valor),
        prazo_dias: 30 * numero
    });

    atualizarTabelaParcelas();
}
```

**POR**:
```javascript
function adicionarParcela() {
    const numero = parcelas.length + 1;
    const total = parseFloat(document.getElementById('valor_total_pedido').value || 0);
    const valorPorParcela = total > 0 ? (total / numero).toFixed(2) : 0;

    // Adicionar nova parcela
    parcelas.push({
        numero: numero,
        valor: parseFloat(valorPorParcela),
        prazo_dias: 30 * numero
    });

    // ✅ RECALCULAR TODAS as parcelas existentes
    parcelas.forEach((p, index) => {
        p.valor = parseFloat(valorPorParcela);
        p.numero = index + 1;
        p.prazo_dias = 30 * (index + 1);
    });

    atualizarTabelaParcelas();
}
```

---

### 13. JAVASCRIPT - ATUALIZAR limparFormItem() (linha ~340)

**SUBSTITUIR**:
```javascript
document.getElementById('txt_cor').value = '';
```

**POR**:
```javascript
document.getElementById('sel_cor').innerHTML = '<option value="">Selecione modelo primeiro...</option>';
document.getElementById('sel_cor').disabled = true;
```

---

## ✅ CHECKLIST DE ALTERAÇÕES

- [ ] 1. Cascata equipe→vendedor→cliente
- [ ] 2. Remover campos de pagamento
- [ ] 3. Adicionar campo de prazo condicional
- [ ] 4. Atualizar bloco de frete
- [ ] 5. SELECT de cores com quantidade
- [ ] 6. Marcar div de montagem
- [ ] 7. Marcar div de parcelas
- [ ] 8. JavaScript cascata
- [ ] 9. JavaScript busca cores
- [ ] 10. JavaScript adicionarItem
- [ ] 11. JavaScript cálculo total com frete
- [ ] 12. JavaScript adicionarParcela corrigido
- [ ] 13. JavaScript limparFormItem

---

**IMPORTANTE**: Faça um BACKUP do arquivo original antes de modificar!
