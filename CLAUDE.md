# 📋 MAPEAMENTO DE CAMPOS DOS MODELOS - REFERÊNCIA PARA CLAUDE AI

**Objetivo**: Evitar erros de nomes de campos ao desenvolver funcionalidades  
**Data de Criação**: 22/07/2025  
**Última Atualização**: 22/07/2025

---

## 🎯 CarteiraPrincipal (app/carteira/models.py)

### 📅 Campos de Datas e Agendamento
```python
# CAMPOS CORRETOS - SEMPRE USAR ESTES NOMES:
expedicao = db.Column(db.Date, nullable=True)                    # ✅ Data prevista expedição
agendamento = db.Column(db.Date, nullable=True)                  # ✅ Data agendamento
hora_agendamento = db.Column(db.Time, nullable=True)             # ✅ Hora agendamento
protocolo = db.Column(db.String(50), nullable=True)             # ✅ Protocolo agendamento
agendamento_confirmado = db.Column(db.Boolean, default=False)    # ✅ Status confirmação
data_entrega_pedido = db.Column(db.Date, nullable=True)          # ✅ Data entrega prevista
observ_ped_1 = db.Column(db.Text, nullable=True)                # ✅ Observações

# ❌ CAMPOS QUE NÃO EXISTEM - NUNCA USAR:
# data_expedicao_pedido ❌
# data_agendamento_pedido ❌
```

### 📊 Campos de Quantidades e Valores
```python
# CAMPOS CORRETOS:
qtd_produto_pedido = db.Column(db.Numeric(15, 3))               # ✅ Quantidade original
qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3))         # ✅ Saldo disponível
qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3))     # ✅ Quantidade cancelada
preco_produto_pedido = db.Column(db.Numeric(15, 2))             # ✅ Preço unitário

# Campos calculados de carga/lote:
qtd_saldo = db.Column(db.Numeric(15, 3))                        # ✅ Qtd no lote separação
valor_saldo = db.Column(db.Numeric(15, 2))                      # ✅ Valor no lote
peso = db.Column(db.Numeric(15, 3))                             # ✅ Peso no lote
pallet = db.Column(db.Numeric(15, 3))                           # ✅ Pallets no lote
```

### 🆔 Campos de Identificação
```python
# CAMPOS CORRETOS:
num_pedido = db.Column(db.String(50))                           # ✅ Número do pedido
cod_produto = db.Column(db.String(50))                          # ✅ Código do produto
cnpj_cpf = db.Column(db.String(20))                             # ✅ CNPJ/CPF cliente
separacao_lote_id = db.Column(db.String(50))                    # ✅ ID lote separação
```

### 👥 Campos de Cliente e Produto
```python
# CAMPOS CORRETOS:
nome_produto = db.Column(db.String(255))                        # ✅ Nome do produto
raz_social = db.Column(db.String(255))                          # ✅ Razão Social completa
raz_social_red = db.Column(db.String(100))                      # ✅ Razão Social reduzida
municipio = db.Column(db.String(100))                           # ✅ Município cliente
estado = db.Column(db.String(2))                                # ✅ UF cliente
vendedor = db.Column(db.String(100))                            # ✅ Vendedor
```

---

## 🚛 Separacao (app/separacao/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50))                    # ✅ ID do lote
num_pedido = db.Column(db.String(50))                           # ✅ Número do pedido
cod_produto = db.Column(db.String(50))                          # ✅ Código produto
qtd_saldo = db.Column(db.Numeric(15, 3))                        # ✅ Quantidade separada
valor_saldo = db.Column(db.Numeric(15, 2))                      # ✅ Valor separado
peso = db.Column(db.Numeric(15, 3))                             # ✅ Peso
pallet = db.Column(db.Numeric(15, 3))                           # ✅ Pallet

# Campos de data:
expedicao = db.Column(db.Date)                                   # ✅ Data expedição
agendamento = db.Column(db.Date)                                 # ✅ Data agendamento
protocolo = db.Column(db.String(50))                            # ✅ Protocolo
criado_em = db.Column(db.DateTime)                               # ✅ Data criação

# ❌ NOTA IMPORTANTE: Separacao NÃO tem campo 'status'
# O status vem de Pedido.status via JOIN!
```

---

## 📦 Pedido (app/pedidos/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50))                    # ✅ ID do lote
status = db.Column(db.String(20))                               # ✅ Status do pedido
# Valores comuns: 'ABERTO', 'COTADO', 'EMBARCADO', 'FATURADO'
```

---

## 🏗️ PreSeparacaoItem (app/carteira/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
num_pedido = db.Column(db.String(50))                           # ✅ Número pedido
cod_produto = db.Column(db.String(50))                          # ✅ Código produto
qtd_original_carteira = db.Column(db.Numeric(15, 3))            # ✅ Quantidade original
qtd_selecionada_usuario = db.Column(db.Numeric(15, 3))          # ✅ Quantidade selecionada
qtd_restante_calculada = db.Column(db.Numeric(15, 3))           # ✅ Saldo restante

# Campos editáveis preservados:
data_expedicao_editada = db.Column(db.Date)                     # ✅ Data expedição editada
data_agendamento_editada = db.Column(db.Date)                   # ✅ Data agendamento editada
protocolo_editado = db.Column(db.String(50))                   # ✅ Protocolo editado
observacoes_usuario = db.Column(db.Text)                       # ✅ Observações

# Status e controle:
recomposto = db.Column(db.Boolean)                              # ✅ Status recomposição
status = db.Column(db.String(20))                               # ✅ Status geral
```

---

## 🚨 REGRAS DE OURO PARA CLAUDE AI

### ✅ SEMPRE FAZER:
1. **Conferir este arquivo** antes de usar qualquer campo
2. **Usar nomes exatos** conforme documentado aqui
3. **Verificar se campo existe** no modelo antes de usar
4. **Consultar JOINs** quando campo vem de outra tabela

### ❌ NUNCA FAZER:
1. **Inventar nomes de campos** sem consultar este arquivo
2. **Assumir que campo existe** sem verificar
3. **Usar replace_all** sem confirmar impactos
4. **Misturar campos** de tabelas diferentes

### 🔍 QUANDO EM DÚVIDA:
1. **Ler o modelo** no arquivo models.py
2. **Consultar este arquivo** CLAUDE.md
3. **Perguntar ao usuário** se campo não estiver documentado
4. **Testar em ambiente local** se possível

---

## 📖 EXEMPLOS DE USO CORRETO

### ✅ Agendamento - USO CORRETO:
```python
# Ler dados existentes:
item.agendamento  # ✅ CORRETO
item.expedicao    # ✅ CORRETO
item.protocolo    # ✅ CORRETO

# Salvar dados:
item.agendamento = data_agendamento           # ✅ CORRETO
item.expedicao = data_expedicao              # ✅ CORRETO
item.agendamento_confirmado = True           # ✅ CORRETO
```

### ❌ Agendamento - USO INCORRETO:
```python
# NUNCA USAR ESTES CAMPOS (não existem):
item.data_agendamento_pedido    # ❌ ERRO
item.data_expedicao_pedido      # ❌ ERRO  
item.agendamento_status         # ❌ ERRO
```

### ✅ Status - USO CORRETO:
```python
# Status de Pedido (via JOIN):
Pedido.status                   # ✅ CORRETO

# Separacao NÃO tem status próprio:
query = db.session.query(Separacao).join(
    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
).filter(Pedido.status == 'ABERTO')  # ✅ CORRETO
```

---

## 🔄 HISTÓRICO DE ERROS CORRIGIDOS

### 22/07/2025:
- ❌ **Erro**: Usado `data_expedicao_pedido` → ✅ **Corrigido**: `expedicao`
- ❌ **Erro**: Usado `data_entrega` → ✅ **Corrigido**: `data_expedicao` → `expedicao`

---

**📝 Nota**: Este arquivo deve ser consultado SEMPRE antes de trabalhar com campos dos modelos. Manter atualizado conforme evolução do sistema.