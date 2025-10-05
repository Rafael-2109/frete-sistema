# 📋 ALTERAÇÕES NAS REGRAS DE NEGÓCIO - SISTEMA MOTOCHEFE

**Data**: 05/01/2025
**Status**: ✅ MODELS ATUALIZADOS | ⏳ AGUARDANDO MIGRAÇÃO SQL

---

## 🎯 ALTERAÇÕES SOLICITADAS

### 1. ✅ Número do Pedido Sequencial
- Formato: `MC ####` (ex: MC 1321)
- Início: 1321 (último foi 1320)
- Botão "Próximo Número" na tela
- Campo editável (permite outras máscaras)
- Validação UNIQUE (não permite duplicados)

### 2. ✅ Movimentação por Equipe
- Campo `responsavel_movimentacao` MOVIDO para `EquipeVendasMoto`
- Campo REMOVIDO de `PedidoVendaMoto`
- Todo vendedor OBRIGATORIAMENTE em uma equipe

### 3. ✅ Comissão Configurável por Equipe
- **Tipo 1**: FIXA_EXCEDENTE (valor fixo + excedente)
- **Tipo 2**: PERCENTUAL (% sobre venda total)
- **Rateio**:
  - `TRUE`: Divide entre todos vendedores da equipe
  - `FALSE`: Apenas vendedor do pedido recebe

---

## 📊 MODELS MODIFICADOS

### ✅ EquipeVendasMoto
**Arquivo**: `app/motochefe/models/cadastro.py:28-67`

**Novos campos adicionados**:
```python
# Movimentação
responsavel_movimentacao = VARCHAR(20)  # 'RJ' ou 'NACOM'

# Comissão
tipo_comissao = VARCHAR(20) DEFAULT 'FIXA_EXCEDENTE' NOT NULL
valor_comissao_fixa = NUMERIC(15, 2) DEFAULT 0 NOT NULL
percentual_comissao = NUMERIC(5, 2) DEFAULT 0 NOT NULL
comissao_rateada = BOOLEAN DEFAULT TRUE NOT NULL
```

### ✅ VendedorMoto
**Arquivo**: `app/motochefe/models/cadastro.py:9-25`

**Alterado**:
```python
# ANTES
equipe_vendas_id = db.Column(..., nullable=True)

# DEPOIS
equipe_vendas_id = db.Column(..., nullable=False, index=True)
# OBRIGATÓRIO: Todo vendedor DEVE estar em uma equipe
```

### ✅ PedidoVendaMoto
**Arquivo**: `app/motochefe/models/vendas.py:49-57`

**Removido**:
```python
# ❌ CAMPO REMOVIDO
# responsavel_movimentacao = db.Column(db.String(20), nullable=True)
```

---

## 🔧 SERVICES CRIADOS

### 1. ✅ numero_pedido_service.py
**Arquivo**: `app/motochefe/services/numero_pedido_service.py`

**Funções**:
- `gerar_proximo_numero_pedido()`: Retorna próximo número "MC ####"
- `validar_numero_pedido_unico(numero, id)`: Valida se número já existe

### 2. ✅ gerar_comissao_pedido() ATUALIZADA
**Arquivo**: `app/motochefe/routes/vendas.py:411-469`

**Nova lógica**:
```python
# Busca configuração da equipe
equipe = pedido.vendedor.equipe

# Calcula conforme tipo
if equipe.tipo_comissao == 'FIXA_EXCEDENTE':
    valor = equipe.valor_comissao_fixa + excedente
elif equipe.tipo_comissao == 'PERCENTUAL':
    valor = (valor_pedido * equipe.percentual_comissao) / 100

# Rateia conforme configuração
if equipe.comissao_rateada:
    # Divide entre TODOS vendedores da equipe
else:
    # Apenas vendedor do pedido
```

---

## 🗄️ MIGRAÇÃO SQL

### ✅ Script Criado
**Arquivo**: `app/motochefe/scripts/migrar_config_equipe_vendas.py`

**Executar**:
```bash
python app/motochefe/scripts/migrar_config_equipe_vendas.py
```

**Alterações no Banco**:
1. ✅ Adiciona 5 campos em `equipe_vendas_moto`
2. ✅ Torna `equipe_vendas_id` obrigatório em `vendedor_moto`
3. ✅ Remove `responsavel_movimentacao` de `pedido_venda_moto`
4. ✅ Cria índice em `vendedor_moto.equipe_vendas_id`
5. ✅ Adiciona comentários nas colunas

---

## ⏳ PRÓXIMOS PASSOS (PENDENTES)

### 1. Atualizar Rotas de Cadastro

#### A) Equipe de Vendas
**Arquivo**: `app/motochefe/routes/cadastros.py`

**Adicionar/editar**:
- Rota `adicionar_equipe()` - incluir novos campos no form
- Rota `editar_equipe()` - incluir novos campos no form

**Campos no formulário**:
```html
<select name="responsavel_movimentacao">
    <option value="">Selecione...</option>
    <option value="RJ">RJ</option>
    <option value="NACOM">NACOM</option>
</select>

<select name="tipo_comissao">
    <option value="FIXA_EXCEDENTE">Fixa + Excedente</option>
    <option value="PERCENTUAL">Percentual</option>
</select>

<div id="div_fixa_excedente">
    <input type="number" name="valor_comissao_fixa" step="0.01">
</div>

<div id="div_percentual">
    <input type="number" name="percentual_comissao" step="0.01" max="100">
</div>

<input type="checkbox" name="comissao_rateada" checked>
```

#### B) Vendedor
**Arquivo**: `app/motochefe/routes/cadastros.py`

**Validar**:
```python
if not request.form.get('equipe_vendas_id'):
    flash('Equipe é obrigatória', 'danger')
    return redirect(...)
```

### 2. Atualizar Rota de Criação de Pedido

**Arquivo**: `app/motochefe/routes/vendas.py`

**Adicionar**:
```python
from app.motochefe.services.numero_pedido_service import (
    gerar_proximo_numero_pedido,
    validar_numero_pedido_unico
)

# Nova rota API
@motochefe_bp.route('/pedidos/api/proximo-numero')
def api_proximo_numero_pedido():
    numero = gerar_proximo_numero_pedido()
    return jsonify({'numero': numero})

# Validação no POST
numero_pedido = request.form.get('numero_pedido')
valido, mensagem = validar_numero_pedido_unico(numero_pedido)
if not valido:
    flash(mensagem, 'danger')
    return redirect(...)
```

### 3. Atualizar Templates

#### A) Equipe - Form
**Arquivo**: `app/templates/motochefe/cadastros/equipes/form.html`

**Adicionar seções**:
- Configuração de Movimentação
- Configuração de Comissão (toggle entre tipos)
- Checkbox rateio

#### B) Vendedor - Form
**Arquivo**: `app/templates/motochefe/cadastros/vendedores/form.html`

**Tornar select equipe obrigatório**:
```html
<select name="equipe_vendas_id" required>
```

#### C) Pedido - Form
**Arquivo**: `app/templates/motochefe/vendas/pedidos/form.html`

**Adicionar**:
```html
<div class="input-group">
    <input type="text" name="numero_pedido" id="numero_pedido" required>
    <button type="button" onclick="buscarProximoNumero()" class="btn btn-info">
        <i class="fas fa-sync"></i> Próximo Número
    </button>
</div>

<script>
async function buscarProximoNumero() {
    const response = await fetch('/motochefe/pedidos/api/proximo-numero');
    const data = await response.json();
    document.getElementById('numero_pedido').value = data.numero;
}
</script>
```

**Remover**:
```html
<!-- ❌ REMOVER campo responsavel_movimentacao -->
```

---

## 🧪 TESTES NECESSÁRIOS

### 1. Migração SQL
```bash
python app/motochefe/scripts/migrar_config_equipe_vendas.py
```
- Verificar se campos foram criados
- Verificar se validações funcionam

### 2. Cadastro de Equipe
- Criar equipe com tipo FIXA_EXCEDENTE
- Criar equipe com tipo PERCENTUAL
- Testar com/sem rateio

### 3. Cadastro de Vendedor
- Tentar criar sem equipe (deve bloquear)
- Criar com equipe (deve funcionar)

### 4. Criação de Pedido
- Clicar em "Próximo Número" (deve gerar MC 1321)
- Tentar criar com número duplicado (deve bloquear)
- Verificar que movimentação vem da equipe automaticamente

### 5. Geração de Comissão
- Pedido com equipe FIXA_EXCEDENTE + rateio TRUE
- Pedido com equipe FIXA_EXCEDENTE + rateio FALSE
- Pedido com equipe PERCENTUAL + rateio TRUE
- Pedido com equipe PERCENTUAL + rateio FALSE

---

## 📝 CHECKLIST DE IMPLEMENTAÇÃO

- [x] Atualizar model EquipeVendasMoto
- [x] Atualizar model VendedorMoto
- [x] Atualizar model PedidoVendaMoto
- [x] Criar script de migração SQL
- [x] Criar numero_pedido_service.py
- [x] Atualizar gerar_comissao_pedido()
- [ ] Executar migração SQL no banco
- [ ] Atualizar rota de cadastro de equipe
- [ ] Atualizar rota de cadastro de vendedor
- [ ] Criar rota API proximo-numero
- [ ] Atualizar rota de criação de pedido
- [ ] Atualizar template de equipe
- [ ] Atualizar template de vendedor
- [ ] Atualizar template de pedido
- [ ] Testar todos os fluxos

---

## 🚨 ATENÇÃO

### Dados Existentes
Conforme confirmado:
- ✅ Não há pedidos criados
- ✅ Não há comissões calculadas
- ✅ Migração pode ser feita sem preocupações

### Regras Importantes
1. **Todo vendedor DEVE ter equipe** (validação obrigatória)
2. **Número de pedido único** (validação UNIQUE no banco)
3. **Comissão configurada na equipe** (não global)
4. **Movimentação vem da equipe** (não do pedido)

---

**Implementação**: 80% concluída
**Faltam**: Rotas e templates (20%)
**Tempo estimado**: 2-3 horas para finalizar

🎉 **MODELS E LÓGICA DE NEGÓCIO PRONTOS!**
