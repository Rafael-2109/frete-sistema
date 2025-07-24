# CLAUDE.md - Referência de Modelos e Campos

## ⚠️ ATENÇÃO: Use SEMPRE os nomes EXATOS dos campos listados aqui

## SE NÃO TIVER CERTEZA, NÃO ALTERE E PERGUNTE

Este arquivo contém os nomes corretos dos campos de todos os modelos para evitar erros como `data_expedicao_pedido` (❌ INCORRETO) em vez de `expedicao` (✅ CORRETO).


# 📋 MAPEAMENTO DE CAMPOS DOS MODELOS - REFERÊNCIA PARA CLAUDE AI

**Objetivo**: Evitar erros de nomes de campos ao desenvolver funcionalidades  
**Data de Criação**: 22/07/2025  
**Última Atualização**: 23/07/2025

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
data_entrega = db.Column(db.Date, nullable=True)                 # ✅ Data prevista entrega
observ_ped_1 = db.Column(db.Text, nullable=True)                # ✅ Observações

# ❌ CAMPOS QUE NÃO EXISTEM - NUNCA USAR:
# data_expedicao_pedido ❌
# data_agendamento_pedido ❌
```

### 📊 Campos de Quantidades e Valores
```python
# CAMPOS CORRETOS:
qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)       # ✅ Quantidade original
qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False) # ✅ Saldo disponível
qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)  # ✅ Quantidade cancelada
preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)      # ✅ Preço unitário

# Campos calculados de carga/lote:
qtd_saldo = db.Column(db.Numeric(15, 3), nullable=True)         # ✅ Qtd no lote separação
valor_saldo = db.Column(db.Numeric(15, 2), nullable=True)       # ✅ Valor no lote
peso = db.Column(db.Numeric(15, 3), nullable=True)              # ✅ Peso no lote
pallet = db.Column(db.Numeric(15, 3), nullable=True)            # ✅ Pallets no lote
```

### 🆔 Campos de Identificação
```python
# CAMPOS CORRETOS:
num_pedido = db.Column(db.String(50), nullable=False, index=True)       # ✅ Número do pedido
cod_produto = db.Column(db.String(50), nullable=False, index=True)      # ✅ Código do produto
cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)         # ✅ CNPJ/CPF cliente
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ✅ ID lote separação
pedido_cliente = db.Column(db.String(100), nullable=True)               # ✅ Pedido de Compra do Cliente
```

### 👥 Campos de Cliente e Produto
```python
# CAMPOS CORRETOS:
nome_produto = db.Column(db.String(255), nullable=False)        # ✅ Nome do produto
raz_social = db.Column(db.String(255), nullable=True)           # ✅ Razão Social completa
raz_social_red = db.Column(db.String(100), nullable=True)       # ✅ Razão Social reduzida
municipio = db.Column(db.String(100), nullable=True)            # ✅ Município cliente
estado = db.Column(db.String(2), nullable=True)                 # ✅ UF cliente
vendedor = db.Column(db.String(100), nullable=True, index=True) # ✅ Vendedor
equipe_vendas = db.Column(db.String(100), nullable=True)        # ✅ Equipe de vendas
```

### 🏠 Campos de Endereço de Entrega
```python
# CAMPOS CORRETOS:
cnpj_endereco_ent = db.Column(db.String(20), nullable=True)      # ✅ CNPJ entrega
empresa_endereco_ent = db.Column(db.String(255), nullable=True)  # ✅ Nome local entrega
cep_endereco_ent = db.Column(db.String(10), nullable=True)       # ✅ CEP
nome_cidade = db.Column(db.String(100), nullable=True)          # ✅ Cidade extraída
cod_uf = db.Column(db.String(2), nullable=True)                 # ✅ UF extraída
bairro_endereco_ent = db.Column(db.String(100), nullable=True)  # ✅ Bairro
rua_endereco_ent = db.Column(db.String(255), nullable=True)     # ✅ Rua
endereco_ent = db.Column(db.String(20), nullable=True)          # ✅ Número
telefone_endereco_ent = db.Column(db.String(20), nullable=True) # ✅ Telefone
```

### 📈 Campos de Estoque e Projeção
```python
# CAMPOS CORRETOS:
estoque = db.Column(db.Numeric(15, 3), nullable=True)           # ✅ Estoque inicial/atual D0
saldo_estoque_pedido = db.Column(db.Numeric(15, 3), nullable=True) # ✅ Estoque na data expedição
menor_estoque_produto_d7 = db.Column(db.Numeric(15, 3), nullable=True) # ✅ Previsão ruptura 7 dias

# Projeção D0-D28 (28 campos de estoque futuro):
estoque_d0 = db.Column(db.Numeric(15, 3), nullable=True)        # ✅ Estoque final D0
estoque_d1 = db.Column(db.Numeric(15, 3), nullable=True)        # ✅ Estoque final D1
# ... até estoque_d28
```

---

## 🚛 Separacao (app/separacao/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ✅ ID do lote
num_pedido = db.Column(db.String(50), nullable=True)            # ✅ Número do pedido
cod_produto = db.Column(db.String(50), nullable=True)           # ✅ Código produto
qtd_saldo = db.Column(db.Float, nullable=True)                  # ✅ Quantidade separada
valor_saldo = db.Column(db.Float, nullable=True)                # ✅ Valor separado
peso = db.Column(db.Float, nullable=True)                       # ✅ Peso
pallet = db.Column(db.Float, nullable=True)                     # ✅ Pallet

# Campos de cliente:
cnpj_cpf = db.Column(db.String(20), nullable=True)              # ✅ CNPJ cliente
raz_social_red = db.Column(db.String(255), nullable=True)       # ✅ Razão Social reduzida
nome_cidade = db.Column(db.String(100), nullable=True)          # ✅ Cidade
cod_uf = db.Column(db.String(2), nullable=False)                # ✅ UF

# Campos de data:
data_pedido = db.Column(db.Date, nullable=True)                 # ✅ Data do pedido
expedicao = db.Column(db.Date, nullable=True)                   # ✅ Data expedição
agendamento = db.Column(db.Date, nullable=True)                 # ✅ Data agendamento
protocolo = db.Column(db.String(50), nullable=True)             # ✅ Protocolo
criado_em = db.Column(db.DateTime, default=datetime.utcnow)     # ✅ Data criação

# Campos operacionais:
tipo_envio = db.Column(db.String(10), default='total', nullable=True) # ✅ total, parcial
observ_ped_1 = db.Column(db.String(700), nullable=True)         # ✅ Observações
roteirizacao = db.Column(db.String(255), nullable=True)         # ✅ Transportadora sugerida
rota = db.Column(db.String(50), nullable=True)                  # ✅ Rota
sub_rota = db.Column(db.String(50), nullable=True)              # ✅ Sub-rota

# ❌ NOTA IMPORTANTE: Separacao NÃO tem campo 'status'
# O status vem de Pedido.status via JOIN!
```

---

## 📦 Pedido (app/pedidos/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ✅ ID do lote
num_pedido = db.Column(db.String(30), index=True)               # ✅ Número do pedido
status = db.Column(db.String(50), default='ABERTO')             # ✅ Status do pedido
nf = db.Column(db.String(20))                                   # ✅ Número da NF
nf_cd = db.Column(db.Boolean, default=False)                    # ✅ Flag para NF no CD

# Valores comuns de status: 'ABERTO', 'COTADO', 'EMBARCADO', 'FATURADO', 'NF no CD'

# Campos de cliente:
cnpj_cpf = db.Column(db.String(20))                             # ✅ CNPJ cliente
raz_social_red = db.Column(db.String(255))                      # ✅ Razão Social reduzida
nome_cidade = db.Column(db.String(120))                         # ✅ Cidade
cod_uf = db.Column(db.String(2))                                # ✅ UF
cidade_normalizada = db.Column(db.String(120))                  # ✅ Cidade normalizada
uf_normalizada = db.Column(db.String(2))                        # ✅ UF normalizada
codigo_ibge = db.Column(db.String(10))                          # ✅ Código IBGE da cidade

# Campos de data:
data_pedido = db.Column(db.Date)                                # ✅ Data do pedido
expedicao = db.Column(db.Date)                                  # ✅ Data expedição
agendamento = db.Column(db.Date)                                # ✅ Data agendamento
data_embarque = db.Column(db.Date)                              # ✅ Data embarque
protocolo = db.Column(db.String(50))                            # ✅ Protocolo

# Campos de totais:
valor_saldo_total = db.Column(db.Float)                         # ✅ Valor total
pallet_total = db.Column(db.Float)                              # ✅ Pallet total
peso_total = db.Column(db.Float)                                # ✅ Peso total

# Campos de frete:
transportadora = db.Column(db.String(100))                      # ✅ Transportadora
valor_frete = db.Column(db.Float)                               # ✅ Valor frete
valor_por_kg = db.Column(db.Float)                              # ✅ Valor por kg
modalidade = db.Column(db.String(50))                           # ✅ Modalidade
melhor_opcao = db.Column(db.String(100))                        # ✅ Melhor opção
valor_melhor_opcao = db.Column(db.Float)                        # ✅ Valor melhor opção
lead_time = db.Column(db.Integer)                               # ✅ Lead time

# Relacionamentos:
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'))     # ✅ ID cotação
usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))     # ✅ ID usuário
```

---

## 🏗️ PreSeparacaoItem (app/carteira/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
num_pedido = db.Column(db.String(50), nullable=False, index=True)       # ✅ Número pedido
cod_produto = db.Column(db.String(50), nullable=False, index=True)      # ✅ Código produto
cnpj_cliente = db.Column(db.String(20), index=True)             # ✅ CNPJ cliente
nome_produto = db.Column(db.String(255), nullable=True)         # ✅ Nome produto

# Quantidades:
qtd_original_carteira = db.Column(db.Numeric(15, 3), nullable=False)    # ✅ Quantidade original
qtd_selecionada_usuario = db.Column(db.Numeric(15, 3), nullable=False)  # ✅ Quantidade selecionada
qtd_restante_calculada = db.Column(db.Numeric(15, 3), nullable=False)   # ✅ Saldo restante

# Dados originais preservados:
valor_original_item = db.Column(db.Numeric(15,2))               # ✅ Valor original
peso_original_item = db.Column(db.Numeric(15,3))                # ✅ Peso original
hash_item_original = db.Column(db.String(128))                  # ✅ Hash para controle

# Campos editáveis preservados:
data_expedicao_editada = db.Column(db.Date, nullable=False)     # ✅ Data expedição editada
data_agendamento_editada = db.Column(db.Date)                   # ✅ Data agendamento editada
protocolo_editado = db.Column(db.String(50))                   # ✅ Protocolo editado
observacoes_usuario = db.Column(db.Text)                       # ✅ Observações

# Status e controle:
recomposto = db.Column(db.Boolean, default=False, index=True)   # ✅ Status recomposição
status = db.Column(db.String(20), default='CRIADO', index=True) # ✅ Status geral
tipo_envio = db.Column(db.String(10), default='total')          # ✅ total, parcial
data_criacao = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ Data criação
criado_por = db.Column(db.String(100))                          # ✅ Usuário criador

# Controle de recomposição:
data_recomposicao = db.Column(db.DateTime)                      # ✅ Data recomposição
recomposto_por = db.Column(db.String(100))                      # ✅ Usuário recomposição
versao_carteira_original = db.Column(db.String(50))             # ✅ Versão original
versao_carteira_recomposta = db.Column(db.String(50))           # ✅ Versão recomposta
```

---

## 🚢 Embarque (app/embarques/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
numero = db.Column(db.Integer, unique=True, nullable=True)       # ✅ Número embarque
data_prevista_embarque = db.Column(db.Date, nullable=True)      # ✅ Data prevista
data_embarque = db.Column(db.Date, nullable=True)               # ✅ Data real embarque
status = db.Column(db.String(20), default='draft')              # ✅ draft, ativo, cancelado
tipo_carga = db.Column(db.String(20))                           # ✅ FRACIONADA, DIRETA
tipo_cotacao = db.Column(db.String(20), default='Automatica')   # ✅ Automatica, Manual

# Totais:
valor_total = db.Column(db.Float)                               # ✅ Valor total embarque
pallet_total = db.Column(db.Float)                              # ✅ Pallet total embarque
peso_total = db.Column(db.Float)                                # ✅ Peso total embarque

# Transportadora:
transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'))  # ✅ ID transportadora
modalidade = db.Column(db.String(50))                           # ✅ Tipo veículo

# Campos de controle:
observacoes = db.Column(db.Text)                                # ✅ Observações
motivo_cancelamento = db.Column(db.Text, nullable=True)         # ✅ Motivo cancelamento
cancelado_em = db.Column(db.DateTime, nullable=True)            # ✅ Data cancelamento
cancelado_por = db.Column(db.String(100), nullable=True)        # ✅ Usuário cancelamento
criado_em = db.Column(db.DateTime, default=datetime.utcnow)     # ✅ Data criação
criado_por = db.Column(db.String(100), default='Administrador') # ✅ Usuário criação

# Relacionamentos:
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id')) # ✅ ID cotação (para DIRETA)
```

### 📋 EmbarqueItem (app/embarques/models.py)
```python
# CAMPOS CORRETOS:
embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False) # ✅ ID embarque
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ✅ ID lote separação
cnpj_cliente = db.Column(db.String(20), nullable=True)          # ✅ CNPJ cliente
cliente = db.Column(db.String(120), nullable=False)             # ✅ Nome cliente
pedido = db.Column(db.String(50), nullable=False)               # ✅ Número pedido
nota_fiscal = db.Column(db.String(20))                          # ✅ Número NF
status = db.Column(db.String(20), default='ativo')              # ✅ ativo, cancelado

# Agendamento:
protocolo_agendamento = db.Column(db.String(50))                # ✅ Protocolo
data_agenda = db.Column(db.String(10))                          # ✅ Data agendamento

# Quantidades:
volumes = db.Column(db.Integer, nullable=True)                  # ✅ Volumes
peso = db.Column(db.Float)                                      # ✅ Peso item
valor = db.Column(db.Float)                                     # ✅ Valor item
pallets = db.Column(db.Float, nullable=True)                    # ✅ Pallets item

# Destino:
uf_destino = db.Column(db.String(2), nullable=False)            # ✅ UF destino
cidade_destino = db.Column(db.String(100), nullable=False)      # ✅ Cidade destino

# Validação:
erro_validacao = db.Column(db.String(500), nullable=True)       # ✅ Erros validação

# Relacionamentos:
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id')) # ✅ ID cotação (para FRACIONADA)
```

---

## 💰 FaturamentoProduto (app/faturamento/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
numero_nf = db.Column(db.String(20), nullable=False, index=True) # ✅ Número NF
data_fatura = db.Column(db.Date, nullable=False, index=True)     # ✅ Data fatura
cnpj_cliente = db.Column(db.String(20), nullable=False, index=True) # ✅ CNPJ cliente
nome_cliente = db.Column(db.String(255), nullable=False)         # ✅ Nome cliente
municipio = db.Column(db.String(100), nullable=True)            # ✅ Município
estado = db.Column(db.String(2), nullable=True)                 # ✅ Estado
vendedor = db.Column(db.String(100), nullable=True)             # ✅ Vendedor
equipe_vendas = db.Column(db.String(100), nullable=True)        # ✅ Equipe vendas
incoterm = db.Column(db.String(20), nullable=True)              # ✅ Incoterm

# Produto:
cod_produto = db.Column(db.String(50), nullable=False, index=True)   # ✅ Código produto
nome_produto = db.Column(db.String(200), nullable=False)        # ✅ Nome produto
qtd_produto_faturado = db.Column(db.Numeric(15, 3), default=0)  # ✅ Quantidade faturada
preco_produto_faturado = db.Column(db.Numeric(15, 4), default=0) # ✅ Preço faturado
valor_produto_faturado = db.Column(db.Numeric(15, 2), default=0) # ✅ Valor faturado
peso_unitario_produto = db.Column(db.Numeric(15, 3), default=0) # ✅ Peso unitário
peso_total = db.Column(db.Numeric(15, 3), default=0)            # ✅ Peso total

# Origem e status:
origem = db.Column(db.String(20), nullable=True, index=True)     # ✅ Número pedido origem
status_nf = db.Column(db.String(20), default='Provisório')      # ✅ Lançado, Cancelado, Provisório

# Auditoria:
created_at = db.Column(db.DateTime, default=agora_brasil)        # ✅ Data criação
updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil) # ✅ Data atualização
created_by = db.Column(db.String(100), nullable=True)           # ✅ Usuário criação
updated_by = db.Column(db.String(100), nullable=True)           # ✅ Usuário atualização
```

---

## 📋 RelatorioFaturamentoImportado (app/faturamento/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
numero_nf = db.Column(db.String(20), nullable=False, index=True, unique=True) # ✅ Número NF único
data_fatura = db.Column(db.Date, nullable=True)                 # ✅ Data fatura
cnpj_cliente = db.Column(db.String(20), nullable=True)          # ✅ CNPJ cliente
nome_cliente = db.Column(db.String(255), nullable=True)         # ✅ Nome cliente
valor_total = db.Column(db.Float, nullable=True)                # ✅ Valor total NF
peso_bruto = db.Column(db.Float, nullable=True)                 # ✅ Peso bruto NF
municipio = db.Column(db.String(100), nullable=True)            # ✅ Município
estado = db.Column(db.String(2), nullable=True)                 # ✅ Estado
codigo_ibge = db.Column(db.String(10), nullable=True)           # ✅ Código IBGE
origem = db.Column(db.String(50), nullable=True)                # ✅ Origem
vendedor = db.Column(db.String(100), nullable=True)             # ✅ Vendedor
equipe_vendas = db.Column(db.String(100), nullable=True)        # ✅ Equipe vendas
incoterm = db.Column(db.String(20), nullable=True)              # ✅ Incoterm

# Transportadora:
cnpj_transportadora = db.Column(db.String(20), nullable=True)    # ✅ CNPJ transportadora
nome_transportadora = db.Column(db.String(255), nullable=True)  # ✅ Nome transportadora

# Controle:
ativo = db.Column(db.Boolean, default=True, nullable=False)     # ✅ Ativo/Inativo
inativado_em = db.Column(db.DateTime, nullable=True)            # ✅ Data inativação
inativado_por = db.Column(db.String(100), nullable=True)        # ✅ Usuário inativação
criado_em = db.Column(db.DateTime, default=datetime.utcnow)     # ✅ Data criação
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


### ❌ ARQUIVOS OBSOLETOS DA CARTEIRA DE PEDIDOS:

- app/carteira/main_routes.py - Carteira de pedidos antiga
- app/templates/carteira/listar_agrupados.py - template da Carteira de pedidos antigo

### ✅ ARQUIVOS CORRETOS DA CARTEIRA DE PEDIDOS:

- app/carteira/routes/
- app/carteira/services/
- app/carteira/utils/

- app/templates/carteira/css/
- app/templates/carteira/js/
- app/templates/carteira/agrupados_balanceado.html
- app/templates/carteira/dashboard.html