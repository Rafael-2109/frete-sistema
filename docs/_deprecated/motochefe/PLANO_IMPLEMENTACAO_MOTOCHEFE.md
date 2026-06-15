# 🎯 PLANO DE IMPLEMENTAÇÃO - MotoChefe Refatoração

**Data**: 07/10/2025
**Status**: Modelos criados ✅ | Services e Frontend PENDENTES ⚠️

---

## ✅ ETAPA 1: MODELOS - CONCLUÍDO

Todos os modelos foram criados e campos adicionados conforme especificação.

---

## ⚠️ ETAPA 2: CORRIGIR IMPORTAÇÃO (PENDENTE)

### 2.1 Importação de Valores Brasileiros
**Arquivo**: `app/motochefe/routes/produtos.py`

**Status Atual** (linhas 222-223, 607-608):
- ✅ JÁ USA `converter_valor_brasileiro` para preços

**Ação**: VERIFICAR se está funcionando corretamente. Se sim, marcar como concluído.

---

### 2.2 Busca Case-Insensitive no Vínculo Chassi-Modelo
**Arquivo**: `app/motochefe/routes/produtos.py:532-665`

**Problema Atual** (linha 605):
```python
modelo = ModeloMoto.query.filter_by(nome_modelo=modelo_nome, ativo=True).first()
```

**Correção Necessária**:
```python
from sqlalchemy import func

# Busca case-insensitive
modelo = ModeloMoto.query.filter(
    func.upper(ModeloMoto.nome_modelo) == modelo_nome.strip().upper(),
    ModeloMoto.ativo == True
).first()

if modelo:
    # ✅ ATUALIZAR o nome do modelo na moto para seguir o padrão
    # (se houver diferença de case, corrigir)
    # Não precisa alterar nada, apenas vincular corretamente
```

---

## ⚠️ ETAPA 3: CRIAR SERVICES (PENDENTE)

### 3.1 Service de Regras de Precificação
**Arquivo**: `app/motochefe/services/precificacao_service.py` (CRIAR)

```python
"""
Service de Precificação - MotoChefe
Aplica regras de CrossDocking ou EquipeVendasMoto
"""
from decimal import Decimal
from app.motochefe.models import ClienteMoto, EquipeVendasMoto, CrossDocking

def obter_regras_aplicaveis(cliente_id, equipe_id):
    """
    Retorna objeto de regras (CrossDocking ou EquipeVendasMoto)

    Returns:
        dict: {
            'tipo': 'crossdocking' ou 'equipe',
            'objeto': CrossDocking ou EquipeVendasMoto,
            'preco_metodo': callable
        }
    """
    cliente = ClienteMoto.query.get(cliente_id)

    if cliente and cliente.crossdocking and cliente.crossdocking_id:
        crossdocking = CrossDocking.query.get(cliente.crossdocking_id)
        return {
            'tipo': 'crossdocking',
            'objeto': crossdocking,
            'preco_metodo': crossdocking.obter_preco_modelo
        }
    else:
        equipe = EquipeVendasMoto.query.get(equipe_id)
        return {
            'tipo': 'equipe',
            'objeto': equipe,
            'preco_metodo': equipe.obter_preco_modelo if equipe else None
        }


def obter_preco_venda(cliente_id, equipe_id, modelo_id):
    """
    Retorna preço de venda considerando CrossDocking ou Equipe
    """
    regras = obter_regras_aplicaveis(cliente_id, equipe_id)

    if regras['preco_metodo']:
        return regras['preco_metodo'](modelo_id)

    return Decimal('0')
```

---

### 3.2 Service de Alocação de Títulos em Parcelas
**Arquivo**: `app/motochefe/services/parcelamento_service.py` (CRIAR)

```python
"""
Service de Parcelamento - MotoChefe
Distribui títulos financeiros entre parcelas (algoritmo FIFO)
"""
from decimal import Decimal
from app import db
from app.motochefe.models import ParcelaPedido, ParcelaTitulo, TituloFinanceiro

def alocar_titulos_em_parcelas(pedido, parcelas_data):
    """
    Distribui títulos do pedido entre parcelas usando algoritmo FIFO

    Args:
        pedido: PedidoVendaMoto
        parcelas_data: [
            {'numero_parcela': 1, 'valor_parcela': 15000, 'prazo_dias': 30},
            {'numero_parcela': 2, 'valor_parcela': 15000, 'prazo_dias': 60}
        ]

    Returns:
        list de ParcelaPedido criadas
    """
    from datetime import timedelta

    # 1. Buscar TODOS os títulos do pedido (ordenados por moto/FIFO)
    titulos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido.id
    ).order_by(TituloFinanceiro.id).all()  # Ordem de criação (FIFO por moto)

    # 2. Criar parcelas
    parcelas_criadas = []
    for p_data in parcelas_data:
        parcela = ParcelaPedido(
            pedido_id=pedido.id,
            numero_parcela=p_data['numero_parcela'],
            valor_parcela=Decimal(str(p_data['valor_parcela'])),
            prazo_dias=p_data['prazo_dias'],
            data_vencimento=pedido.data_expedicao + timedelta(days=p_data['prazo_dias']) if pedido.data_expedicao else None
        )
        db.session.add(parcela)
        db.session.flush()
        parcelas_criadas.append(parcela)

    # 3. Algoritmo de alocação (FIFO - consome títulos sequencialmente)
    valor_restante_parcela = parcelas_criadas[0].valor_parcela
    parcela_atual = parcelas_criadas[0]
    indice_parcela = 0

    for titulo in titulos:
        valor_titulo = titulo.valor_total

        while valor_titulo > 0:
            if valor_restante_parcela == 0:
                # Parcela atual cheia, ir para próxima
                indice_parcela += 1
                if indice_parcela >= len(parcelas_criadas):
                    raise Exception('Valor total das parcelas é menor que soma dos títulos')

                parcela_atual = parcelas_criadas[indice_parcela]
                valor_restante_parcela = parcela_atual.valor_parcela

            # Quanto do título cabe nesta parcela?
            valor_alocado = min(valor_titulo, valor_restante_parcela)
            percentual = (valor_alocado / titulo.valor_total) * 100

            # Criar vínculo Parcela-Título
            parcela_titulo = ParcelaTitulo(
                parcela_id=parcela_atual.id,
                titulo_id=titulo.id,
                percentual_titulo=Decimal(str(round(percentual, 2))),
                valor_parcial=Decimal(str(valor_alocado))
            )
            db.session.add(parcela_titulo)

            # Atualizar contadores
            valor_titulo -= valor_alocado
            valor_restante_parcela -= valor_alocado

    return parcelas_criadas
```

---

## ⚠️ ETAPA 4: REFATORAR PEDIDO_SERVICE (PENDENTE)

**Arquivo**: `app/motochefe/services/pedido_service.py`

**Adicionar** após linha 140 (função `criar_pedido_completo`):

```python
    # 🆕 5. CRIAR PARCELAS (se houver parcelas_data)
    if 'parcelas' in dados_pedido and dados_pedido['parcelas']:
        from app.motochefe.services.parcelamento_service import alocar_titulos_em_parcelas
        parcelas_criadas = alocar_titulos_em_parcelas(pedido, dados_pedido['parcelas'])
    else:
        parcelas_criadas = []

    db.session.flush()

    return {
        'pedido': pedido,
        'itens': itens_criados,
        'titulos_financeiros': titulos_financeiros_criados,
        'titulos_a_pagar': titulos_a_pagar_criados,
        'parcelas': parcelas_criadas  # 🆕 ADICIONAR
    }
```

---

## ⚠️ ETAPA 5: CRIAR APIs DE CASCATA (PENDENTE)

**Arquivo**: `app/motochefe/routes/vendas.py`

**Adicionar** após linha 431:

```python
# ===== APIs DE CASCATA =====

@motochefe_bp.route('/api/vendedores-por-equipe')
@login_required
@requer_motochefe
def api_vendedores_por_equipe():
    """API: Retorna vendedores de uma equipe"""
    equipe_id = request.args.get('equipe_id', type=int)

    if not equipe_id:
        return jsonify([])

    vendedores = VendedorMoto.query.filter_by(
        equipe_vendas_id=equipe_id,
        ativo=True
    ).order_by(VendedorMoto.vendedor).all()

    return jsonify([{
        'id': v.id,
        'vendedor': v.vendedor
    } for v in vendedores])


@motochefe_bp.route('/api/clientes-por-vendedor')
@login_required
@requer_motochefe
def api_clientes_por_vendedor():
    """API: Retorna clientes de um vendedor"""
    vendedor_id = request.args.get('vendedor_id', type=int)

    if not vendedor_id:
        return jsonify([])

    clientes = ClienteMoto.query.filter_by(
        vendedor_id=vendedor_id,
        ativo=True
    ).order_by(ClienteMoto.cliente).all()

    return jsonify([{
        'id': c.id,
        'cliente': c.cliente,
        'cnpj': c.cnpj_cliente,
        'crossdocking': c.crossdocking
    } for c in clientes])


@motochefe_bp.route('/api/cores-disponiveis')
@login_required
@requer_motochefe
def api_cores_disponiveis():
    """API: Retorna cores disponíveis de um modelo com quantidade"""
    modelo_id = request.args.get('modelo_id', type=int)

    if not modelo_id:
        return jsonify([])

    from sqlalchemy import func

    cores = db.session.query(
        Moto.cor,
        func.count(Moto.numero_chassi).label('quantidade')
    ).filter(
        Moto.modelo_id == modelo_id,
        Moto.status == 'DISPONIVEL',
        Moto.reservado == False,
        Moto.ativo == True
    ).group_by(Moto.cor).all()

    return jsonify([{
        'cor': c.cor,
        'quantidade': c.quantidade,
        'label': f'{c.cor} ({c.quantidade} unidades)'
    } for c in cores])
```

---

## ⚠️ ETAPA 6: REFATORAR FRONTEND (PENDENTE)

**Arquivo**: `app/templates/motochefe/vendas/pedidos/form.html`

### 6.1 JavaScript - Corrigir Cálculo de Frete (linhas 335-337)

**SUBSTITUIR**:
```javascript
const total = itens.reduce((sum, item) => sum + item.total, 0);
document.getElementById('td_total').textContent = 'R$ ' + total.toFixed(2);
document.getElementById('valor_total_pedido').value = total.toFixed(2);
```

**POR**:
```javascript
function calcularTotalComFrete() {
    const totalItens = itens.reduce((sum, item) => sum + item.total, 0);
    const frete = parseFloat(document.querySelector('[name="valor_frete_cliente"]').value || 0);
    return totalItens + frete;
}

function atualizarTabelaItens() {
    // ... código existente até linha 333 ...

    const totalComFrete = calcularTotalComFrete();
    document.getElementById('td_total').textContent = 'R$ ' + totalComFrete.toFixed(2);
    document.getElementById('valor_total_pedido').value = totalComFrete.toFixed(2);
}

// Adicionar listener no campo de frete
document.querySelector('[name="valor_frete_cliente"]').addEventListener('input', atualizarTabelaItens);
```

---

### 6.2 JavaScript - Corrigir Função adicionarParcela() (linhas 352-363)

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

### 6.3 HTML - Cascata Equipe → Vendedor → Cliente

**SUBSTITUIR** (linhas 46-73):
```html
<div class="row">
    <div class="col-md-4 mb-3">
        <label class="form-label">Cliente *</label>
        <select name="cliente_id" class="form-select" required>
            <option value="">Selecione...</option>
            {% for c in clientes %}
            <option value="{{ c.id }}">{{ c.cliente }} - {{ c.cnpj_cliente }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Vendedor *</label>
        <select name="vendedor_id" class="form-select" required>
            <option value="">Selecione...</option>
            {% for v in vendedores %}
            <option value="{{ v.id }}">{{ v.vendedor }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-4 mb-3">
        <label class="form-label">Equipe de Vendas</label>
        <select name="equipe_vendas_id" class="form-select">
            <option value="">Selecione...</option>
            {% for e in equipes %}
            <option value="{{ e.id }}">{{ e.equipe_vendas }}</option>
            {% endfor %}
        </select>
    </div>
</div>
```

**POR**:
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

<script>
// Cascata: Equipe → Vendedor
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

    // Mostrar/ocultar campos de montagem
    const divMontagem = document.getElementById('div_montagem');
    if (divMontagem) {
        divMontagem.style.display = permitirMontagem ? 'block' : 'none';
    }

    // Mostrar/ocultar campos de prazo e parcelamento
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

// Cascata: Vendedor → Cliente
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

// Evento no cliente: aplicar regras de crossdocking
document.getElementById('sel_cliente').addEventListener('change', function() {
    const option = this.options[this.selectedIndex];
    const crossdocking = option.dataset.crossdocking === 'true';

    // Mostrar/ocultar tipo_frete baseado em crossdocking
    const divTipoFrete = document.querySelector('[name="tipo_frete"]').closest('.col-md-6');
    if (divTipoFrete) {
        divTipoFrete.style.display = crossdocking ? 'none' : 'block';
    }
});
</script>
```

---

### 6.4 HTML - Substituir Campo Cor por SELECT

**SUBSTITUIR** (linhas 140-143):
```html
<div class="col-md-2 mb-3">
    <label class="form-label">Cor</label>
    <input type="text" id="txt_cor" class="form-control" placeholder="Ex: Vermelho">
</div>
```

**POR**:
```html
<div class="col-md-3 mb-3">
    <label class="form-label">Cor *</label>
    <select id="sel_cor" class="form-select" required>
        <option value="">Selecione modelo primeiro...</option>
    </select>
</div>
```

**E ADICIONAR** no JavaScript (após linha 265):
```javascript
// Atualizar SELECT de cores ao selecionar modelo
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

## ⚠️ ETAPA 7: CRUD CROSSDOCKING (PENDENTE)

Criar arquivos:
1. `app/motochefe/routes/crossdocking.py` (rotas CRUD)
2. `app/templates/motochefe/cadastros/crossdocking/listar.html`
3. `app/templates/motochefe/cadastros/crossdocking/form.html`

(Estrutura análoga às rotas de Equipe de Vendas)

---

## 📝 SCRIPT DE MIGRAÇÃO DO BANCO

**Criar arquivo**: `app/motochefe/scripts/migration_crossdocking_e_parcelas.py`

```python
"""
Migração: Adiciona suporte a CrossDocking e Parcelamento
Data: 07/10/2025
"""
from app import db

def executar_migracao():
    print("🚀 Iniciando migração: CrossDocking e Parcelamento...")

    try:
        # 1. Criar tabelas novas
        db.create_all()
        print("✅ Tabelas criadas com sucesso")

        # 2. Migrar dados (se necessário)
        # Como você informou que vai apagar o banco, não precisa migrar

        print("✅ Migração concluída com sucesso!")

    except Exception as e:
        print(f"❌ Erro na migração: {str(e)}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    executar_migracao()
```

---

## 🎯 ORDEM DE EXECUÇÃO FINAL

1. ✅ **Modelos** - CONCLUÍDO
2. ⚠️ **Verificar importação** valores brasileiros
3. ⚠️ **Corrigir** busca case-insensitive
4. ⚠️ **Criar** services (precificacao_service.py, parcelamento_service.py)
5. ⚠️ **Refatorar** pedido_service.py
6. ⚠️ **Criar** APIs de cascata
7. ⚠️ **Refatorar** frontend (form.html)
8. ⚠️ **Criar** CRUD CrossDocking
9. ⚠️ **Executar** migração do banco
10. ⚠️ **Testar** fluxo completo

---

## ⚡ COMANDOS RÁPIDOS

```bash
# Executar migração
python app/motochefe/scripts/migration_crossdocking_e_parcelas.py

# Testar importação
# (importar planilha com valores "10.000,50" deve funcionar)
```

---

**IMPORTANTE**: Este plano deve ser executado na ordem exata. Cada etapa depende da anterior.
