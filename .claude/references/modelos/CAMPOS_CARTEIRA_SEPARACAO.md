# Modelos Criticos: CarteiraPrincipal e Separacao

**Ultima Atualizacao**: 31/01/2026
**Verificado contra**: app/carteira/models.py e app/separacao/models.py (codigo real)

---

## CarteiraPrincipal (app/carteira/models.py)

**Tabela**: `carteira_principal`
**Uso**: Pedidos originais com saldo pendente (fonte de verdade para demanda)
**Total de campos**: 73

### Chaves de Negocio
```python
id = db.Column(db.Integer, primary_key=True)
num_pedido = db.Column(db.String(50), nullable=False, index=True)       # Chave principal
cod_produto = db.Column(db.String(50), nullable=False, index=True)      # Chave produto
# UniqueConstraint('num_pedido', 'cod_produto', name='uq_carteira_pedido_produto')
```

### Dados do Pedido
```python
pedido_cliente = db.Column(db.String(100), nullable=True)               # Pedido de Compra do Cliente
data_pedido = db.Column(db.Date, nullable=True, index=True)             # Data de criacao
data_atual_pedido = db.Column(db.Date, nullable=True)                   # Data ultima alteracao
status_pedido = db.Column(db.String(50), nullable=True, index=True)     # Cancelado, Pedido de venda, Cotacao
```

### Dados do Cliente
```python
cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)        # CNPJ/CPF cliente
raz_social = db.Column(db.String(255), nullable=True)                   # Razao Social completa
raz_social_red = db.Column(db.String(100), nullable=True)               # Nome reduzido
municipio = db.Column(db.String(100), nullable=True)                    # Cidade do cliente
estado = db.Column(db.String(2), nullable=True)                         # UF do cliente
vendedor = db.Column(db.String(100), nullable=True, index=True)         # Vendedor responsavel
equipe_vendas = db.Column(db.String(100), nullable=True)                # Equipe de vendas
```

### Dados do Produto
```python
nome_produto = db.Column(db.String(255), nullable=False)                # Descricao do produto
unid_medida_produto = db.Column(db.String(20), nullable=True)           # Unidade de medida
embalagem_produto = db.Column(db.String(100), nullable=True)            # Categoria
materia_prima_produto = db.Column(db.String(100), nullable=True)        # Sub categoria
categoria_produto = db.Column(db.String(100), nullable=True)            # Sub sub categoria
```

### Quantidades e Valores
```python
qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)       # Quantidade original
qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False) # Saldo a faturar
qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)  # Quantidade cancelada
preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)      # Preco unitario
```

### Impostos da Linha (Odoo sale.order.line)
```python
icms_valor = db.Column(db.Numeric(15, 2), nullable=True)               # l10n_br_icms_valor
icmsst_valor = db.Column(db.Numeric(15, 2), nullable=True)             # l10n_br_icmsst_valor
pis_valor = db.Column(db.Numeric(15, 2), nullable=True)                # l10n_br_pis_valor
cofins_valor = db.Column(db.Numeric(15, 2), nullable=True)             # l10n_br_cofins_valor
```

### Desconto Contratual (Odoo res.partner)
```python
desconto_contratual = db.Column(db.Boolean, default=False, nullable=True)   # x_studio_desconto_contratual
desconto_percentual = db.Column(db.Numeric(5, 2), nullable=True)            # x_studio_desconto (%)
```

### Condicoes Comerciais
```python
cond_pgto_pedido = db.Column(db.String(100), nullable=True)             # Condicoes de pagamento
forma_pgto_pedido = db.Column(db.String(100), nullable=True)            # Forma de pagamento
incoterm = db.Column(db.String(20), nullable=True)                      # Incoterm (FOB, CIF, etc)
metodo_entrega_pedido = db.Column(db.String(100), nullable=True)        # Metodo de entrega (aumentado de 50 para 100)
data_entrega_pedido = db.Column(db.Date, nullable=True)                 # Data de entrega solicitada pelo comercial
cliente_nec_agendamento = db.Column(db.String(10), nullable=True)       # Sim/Nao
observ_ped_1 = db.Column(db.Text, nullable=True)                        # Observacoes
```

### Dados Operacionais
```python
forma_agendamento = db.Column(db.String(50), nullable=True)             # Portal, Telefone, E-mail, WhatsApp, ODOO, SEM AGENDAMENTO
# NOTA: Campos de agendamento/expedicao/carga estao em Separacao (fonte unica da verdade)
```

### Endereco de Entrega
```python
cnpj_endereco_ent = db.Column(db.String(20), nullable=True)             # CNPJ entrega
empresa_endereco_ent = db.Column(db.String(255), nullable=True)         # Nome local entrega
cep_endereco_ent = db.Column(db.String(10), nullable=True)              # CEP
nome_cidade = db.Column(db.String(100), nullable=True)                  # Cidade extraida
cod_uf = db.Column(db.String(2), nullable=True)                         # UF extraida
bairro_endereco_ent = db.Column(db.String(100), nullable=True)          # Bairro
rua_endereco_ent = db.Column(db.String(255), nullable=True)             # Rua
endereco_ent = db.Column(db.String(20), nullable=True)                  # Numero
telefone_endereco_ent = db.Column(db.String(50), nullable=True)         # Telefone (aumentado de 20 para 50)
```

### Sincronizacao Incremental
```python
odoo_write_date = db.Column(db.DateTime, nullable=True, index=True)     # write_date do Odoo
ultima_sync = db.Column(db.DateTime, nullable=True)                     # Momento da ultima sincronizacao
```

### Controle de Exclusao
```python
motivo_exclusao = db.Column(db.Text, nullable=True)                     # Motivo do cancelamento/exclusao
```

### Marcadores
```python
importante = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Marcador de pedido importante
```

### Tags do Pedido (Odoo)
```python
tags_pedido = db.Column(db.Text, nullable=True)  # JSON: [{"name": "VIP", "color": 5}]
# SINCRONIZACAO: Vem do campo tag_ids do sale.order no Odoo
# MODELO ODOO: crm.tag com campos id, name, color
```

### Snapshot de Custo (gravado na importacao do Odoo)
```python
custo_unitario_snapshot = db.Column(db.Numeric(15, 6), nullable=True)    # Custo unitario no momento
custo_tipo_snapshot = db.Column(db.String(20), nullable=True)            # MEDIO_MES, ULTIMO_CUSTO, MEDIO_ESTOQUE, BOM
custo_vigencia_snapshot = db.Column(db.DateTime, nullable=True)          # Data do custo usado
custo_producao_snapshot = db.Column(db.Numeric(15, 6), nullable=True)    # Custo adicional de producao
```

### Margens Calculadas
```python
margem_bruta = db.Column(db.Numeric(15, 2), nullable=True)
margem_bruta_percentual = db.Column(db.Numeric(7, 2), nullable=True)     # Suporta ate +/-99999.99%
margem_liquida = db.Column(db.Numeric(15, 2), nullable=True)
margem_liquida_percentual = db.Column(db.Numeric(7, 2), nullable=True)   # Suporta ate +/-99999.99%
comissao_percentual = db.Column(db.Numeric(5, 2), nullable=True, default=0)  # Soma das regras de comissao
```

### Snapshot de Parametros (rastreabilidade do calculo de margem)
```python
frete_percentual_snapshot = db.Column(db.Numeric(5, 2), nullable=True)          # % Frete usado
custo_financeiro_pct_snapshot = db.Column(db.Numeric(5, 2), nullable=True)      # % Custo financeiro
custo_operacao_pct_snapshot = db.Column(db.Numeric(5, 2), nullable=True)        # % Custo operacao
percentual_perda_snapshot = db.Column(db.Numeric(5, 2), nullable=True)          # % Perda
```

### Auditoria
```python
created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
created_by = db.Column(db.String(100), nullable=True)
updated_by = db.Column(db.String(100), nullable=True)
ativo = db.Column(db.Boolean, default=True, index=True)
```

### CAMPOS QUE NAO EXISTEM EM CarteiraPrincipal - NUNCA USAR
```python
# NAO EXISTEM neste modelo (estao na Separacao):
# separacao_lote_id  -> Separacao.separacao_lote_id
# expedicao          -> Separacao.expedicao
# agendamento        -> Separacao.agendamento
# protocolo          -> Separacao.protocolo
# status             -> Separacao.status
# data_entrega       -> usar data_entrega_pedido
# hora_agendamento   -> nao existe em nenhum modelo
# data_expedicao_pedido -> nao existe
# data_agendamento_pedido -> nao existe
# agendamento_confirmado -> Separacao.agendamento_confirmado
```

---

## Separacao (app/separacao/models.py)

**Tabela**: `separacao`
**Uso**: Unica fonte da verdade para projetar as saidas de estoque atraves de sincronizado_nf=False
**Total de campos**: ~48

### REGRA CRITICA: sincronizado_nf
- **sincronizado_nf=False**: Item SEMPRE aparece na carteira e SEMPRE e projetado no estoque
- **sincronizado_nf=True**: Foi faturado (tem NF), NAO aparece na carteira, NAO projeta estoque

### Campos de Identificacao e Cliente
```python
id = db.Column(db.Integer, primary_key=True)
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ID do lote de separacao
num_pedido = db.Column(db.String(50), nullable=True)                    # Numero do pedido
data_pedido = db.Column(db.Date, nullable=True)                         # Data do pedido
cnpj_cpf = db.Column(db.String(20), nullable=True)                      # CNPJ cliente
raz_social_red = db.Column(db.String(255), nullable=True)               # Razao Social reduzida
nome_cidade = db.Column(db.String(100), nullable=True)                  # Cidade
cod_uf = db.Column(db.String(2), nullable=False)                        # UF
cod_produto = db.Column(db.String(50), nullable=True)                   # Codigo produto
nome_produto = db.Column(db.String(255), nullable=True)                 # Nome produto
pedido_cliente = db.Column(db.String(100), nullable=True)               # Pedido de Compra do Cliente
```

### Quantidades e Valores
```python
qtd_saldo = db.Column(db.Float, nullable=True)                          # Quantidade separada
valor_saldo = db.Column(db.Float, nullable=True)                        # Valor separado
pallet = db.Column(db.Float, nullable=True)                             # Pallet (calculado)
peso = db.Column(db.Float, nullable=True)                               # Peso (calculado)
```

### Rotas e Operacional
```python
rota = db.Column(db.String(50), nullable=True)                          # Rota
sub_rota = db.Column(db.String(50), nullable=True)                      # Sub-rota
observ_ped_1 = db.Column(db.String(700), nullable=True)                 # Observacoes (truncado automaticamente)
roteirizacao = db.Column(db.String(255), nullable=True)                 # Transportadora sugerida
tipo_envio = db.Column(db.String(10), default='total', nullable=True)   # total, parcial
```

### Datas e Agendamento
```python
expedicao = db.Column(db.Date, nullable=True)                           # Data expedicao
agendamento = db.Column(db.Date, nullable=True)                         # Data agendamento
agendamento_confirmado = db.Column(db.Boolean, default=False)           # Flag confirmacao agendamento
protocolo = db.Column(db.String(50), nullable=True)                     # Protocolo
data_embarque = db.Column(db.Date, nullable=True)                       # Data de embarque
```

### Sincronizacao com NF
```python
sincronizado_nf = db.Column(db.Boolean, default=False, nullable=True)   # GATILHO PRINCIPAL
numero_nf = db.Column(db.String(20), nullable=True)                     # NF associada quando sincronizada
data_sincronizacao = db.Column(db.DateTime, nullable=True)              # Data/hora da sincronizacao
zerado_por_sync = db.Column(db.Boolean, default=False, nullable=True)   # Indica se foi zerado por sync
data_zeragem = db.Column(db.DateTime, nullable=True)                    # Data/hora quando foi zerado
```

### Campos de Controle
```python
status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)
# Valores REAIS (calculados automaticamente pelo listener):
# 'PREVISAO' - Status manual, pre-separacao (listener NAO sobrescreve)
# 'ABERTO'   - Estado padrao (sem cotacao, sem NF)
# 'COTADO'   - Tem cotacao_id vinculado
# 'FATURADO' - Tem NF (sincronizado_nf=True ou numero_nf preenchido)
# 'NF no CD' - Flag nf_cd=True (NF voltou para o CD)
# ⚠️ 'EMBARCADO' NAO e usado na logica automatica de status

nf_cd = db.Column(db.Boolean, default=False, nullable=False)            # NF voltou para o CD
```

### Normalizacao (para cotacao e agrupamento)
```python
cidade_normalizada = db.Column(db.String(120), nullable=True)
uf_normalizada = db.Column(db.String(2), nullable=True)
codigo_ibge = db.Column(db.String(10), nullable=True)
```

### Controle de Impressao
```python
separacao_impressa = db.Column(db.Boolean, default=False, nullable=False)
separacao_impressa_em = db.Column(db.DateTime, nullable=True)
separacao_impressa_por = db.Column(db.String(100), nullable=True)
```

### Controle de Separacao
```python
obs_separacao = db.Column(db.Text, nullable=True)                       # Observacoes sobre a separacao
falta_item = db.Column(db.Boolean, default=False, nullable=False)       # Indica se falta item no estoque
falta_pagamento = db.Column(db.Boolean, default=False, nullable=False)  # Indica se pagamento esta pendente
```

### Relacionamentos
```python
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'), nullable=True)  # FK para cotacao
```

### Auditoria
```python
criado_em = db.Column(db.DateTime, default=datetime.utcnow)             # Data criacao
criado_por = db.Column(db.String(100), nullable=True)                   # Usuario que criou
```

---

### Event Listeners da Separacao

**4 listeners automaticos** (app/separacao/models.py):

#### 1. setar_falta_pagamento_inicial (BEFORE_INSERT, linhas 198-230)
- **Trigger**: Apenas no INSERT (criacao)
- **Regra**: Se CarteiraPrincipal.cond_pgto_pedido contiver 'ANTECIPADO', seta falta_pagamento=True
- **NAO roda em UPDATEs** (preserva escolha manual do usuario)

#### 2. atualizar_status_automatico (BEFORE_INSERT + BEFORE_UPDATE, linhas 233-281)
- **Trigger**: Toda insercao e atualizacao
- **Regras de Prioridade**:
  1. PREVISAO: Nunca sobrescrever (manual)
  2. NF no CD: nf_cd=True
  3. FATURADO: sincronizado_nf=True ou numero_nf preenchido
  4. COTADO: cotacao_id preenchido
  5. ABERTO: Estado padrao

#### 3. log_reversao_status (AFTER_UPDATE, linhas 283-312)
- **Trigger**: Apos atualizacao
- **Proposito**: Registra reversoes de status para auditoria
- **Reversoes monitoradas**: EMBARCADO->COTADO, COTADO->ABERTO, FATURADO->ABERTO, etc.

#### 4. recalcular_totais_embarque (AFTER_UPDATE + AFTER_DELETE, linhas 315-427)
- **Trigger**: Apos atualizar ou deletar Separacao
- **Proposito**: Recalcula EmbarqueItem.peso/.valor/.pallets e Embarque.peso_total/.valor_total/.pallet_total
- **Condicao**: Somente se separacao_lote_id esta vinculada a EmbarqueItem ativo

---

### Metodos Auxiliares da Separacao

```python
# Classe:
Separacao.atualizar_status(separacao_lote_id, num_pedido=None, novo_status='ABERTO')
Separacao.atualizar_nf_cd(separacao_lote_id, num_pedido=None, nf_cd=False)
Separacao.atualizar_cotacao(separacao_lote_id, cotacao_id, nf_cd=False)
Separacao.save()  # db.session.add + commit

# Funcoes do modulo:
remover_do_embarque(separacao_lote_id, num_pedido=None)     # Zera data_embarque
remover_cotacao(separacao_lote_id, num_pedido=None)         # Zera cotacao_id
cancelar_faturamento(separacao_lote_id, num_pedido=None)    # Limpa sincronizado_nf, numero_nf, data_sincronizacao
```

---

### Diferenca entre Campos de Carteira vs Separacao

| Campo | CarteiraPrincipal | Separacao |
|-------|-------------------|-----------|
| Quantidade | `qtd_saldo_produto_pedido` | `qtd_saldo` |
| Valor | `preco_produto_pedido` | `valor_saldo` |
| Data entrega cliente | `data_entrega_pedido` | NAO TEM |
| Data expedicao | NAO TEM | `expedicao` |
| Agendamento | NAO TEM | `agendamento` |
| Agend. confirmado | NAO TEM | `agendamento_confirmado` |
| Protocolo | NAO TEM | `protocolo` |
| Status | `status_pedido` (Odoo) | `status` (operacional) |
| Data embarque | NAO TEM | `data_embarque` |
| Falta item | NAO TEM | `falta_item` |
| Falta pagamento | NAO TEM | `falta_pagamento` |
| Cotacao | NAO TEM | `cotacao_id` |

### Campos Calculados ao Criar Separacao

| Campo | Calculo | Fonte |
|-------|---------|-------|
| peso | qtd_saldo x peso_bruto | CadastroPalletizacao |
| pallet | qtd_saldo / palletizacao | CadastroPalletizacao |
| rota | buscar_rota_por_uf(cod_uf) | app.carteira.utils.separacao_utils |
| sub_rota | buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade) | app.carteira.utils.separacao_utils |

### Exemplos de Uso

```python
# CORRETO - Ler dados de SEPARACAO:
item.agendamento                # OK
item.expedicao                  # OK
item.protocolo                  # OK
item.agendamento_confirmado     # OK (Boolean)
item.falta_item                 # OK (Boolean)
item.falta_pagamento            # OK (Boolean)
item.data_embarque              # OK (Date)

# INCORRETO - NAO EXISTEM:
item.data_agendamento_pedido    # ERRO - nao existe
item.data_expedicao_pedido      # ERRO - nao existe
item.agendamento_status         # ERRO - nao existe

# Busca na carteira:
items = Separacao.query.filter_by(sincronizado_nf=False).all()
```

---

## Pallets: Calculo Teorico vs Controle Fisico

### GRUPO 1: PALLETS TEORICOS (via CadastroPalletizacao)

Estimativa baseada em pallets padrao (1 produto por pallet).

| Modelo | Campo | Calculo |
|--------|-------|---------|
| `Separacao` | `pallet` | `qtd_saldo / CadastroPalletizacao.palletizacao` |
| `EmbarqueItem` | `pallets` | Soma de `Separacao.pallet` do lote |
| `Embarque` | `pallet_total` | Soma de `EmbarqueItem.pallets` |

Listener: `app/separacao/models.py:315-427` (`recalcular_totais_embarque`) sincroniza automaticamente.

### GRUPO 2: PALLETS FISICOS (Controle Real - Gestao de Ativos PBR)

Rastrear pallets fisicos reais para faturamento de NF remessa.

| Modelo | Campo | Descricao |
|--------|-------|-----------|
| `Embarque` | `nf_pallet_transportadora` | NF remessa de pallet para transportadora |
| `Embarque` | `qtd_pallet_transportadora` | Quantidade na NF remessa |
| `Embarque` | `qtd_pallets_separados` | Pallets fisicos expedidos |
| `Embarque` | `qtd_pallets_trazidos` | Pallets que a transportadora trouxe de volta |
| `EmbarqueItem` | `nf_pallet_cliente` | NF remessa de pallet para o cliente |
| `EmbarqueItem` | `qtd_pallet_cliente` | Quantidade na NF para o cliente |

**REGRA**: GRUPO 1 (Teorico) != GRUPO 2 (Fisico). Sao INDEPENDENTES.

```python
# Embarque.saldo_pallets_pendentes
# = qtd_pallets_separados - qtd_pallets_trazidos - faturados
```
