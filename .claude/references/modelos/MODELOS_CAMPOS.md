# MAPEAMENTO DE CAMPOS DOS MODELOS - REFERÊNCIA COMPLETA

**Objetivo**: Documentação detalhada de todos os modelos do sistema de fretes
**Ultima Atualizacao**: 31/01/2026
**Uso**: Consultar quando precisar de campos de modelos secundarios

> **NOTA**: Para campos de **CarteiraPrincipal** e **Separacao** (mais usados),
> consulte `.claude/references/modelos/CAMPOS_CARTEIRA_SEPARACAO.md`

---

## 📦 Pedido (app/pedidos/models.py)

### Modelo Pedido que agora é uma VIEW agregando dados de Separacao

### REGRA DA VIEW:
- **IGNORA**: Separacao com status='PREVISAO'
- **AGREGA**: Por separacao_lote_id e num_pedido
- **INCLUI**: Apenas status != 'PREVISAO'

```python
__tablename__ = 'pedidos'
__table_args__ = {'info': {'is_view': True}}  # Marca como VIEW para SQLAlchemy
```

### Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ID do lote
num_pedido = db.Column(db.String(30), index=True)               # Numero do pedido
status = db.Column(db.String(50), default='ABERTO')             # Status do pedido
nf = db.Column(db.String(20))                                   # Numero da NF
nf_cd = db.Column(db.Boolean, default=False)                    # Flag para NF no CD

# Valores comuns de status: 'ABERTO', 'COTADO', 'EMBARCADO', 'FATURADO', 'NF no CD'

# Campos de cliente:
cnpj_cpf = db.Column(db.String(20))                             # CNPJ cliente
raz_social_red = db.Column(db.String(255))                      # Razao Social reduzida
nome_cidade = db.Column(db.String(120))                         # Cidade
cod_uf = db.Column(db.String(2))                                # UF
cidade_normalizada = db.Column(db.String(120))                  # Cidade normalizada
uf_normalizada = db.Column(db.String(2))                        # UF normalizada
codigo_ibge = db.Column(db.String(10))                          # Codigo IBGE da cidade

# Campos de data:
data_pedido = db.Column(db.Date)                                # Data do pedido
expedicao = db.Column(db.Date)                                  # Data expedicao
agendamento = db.Column(db.Date)                                # Data agendamento
data_embarque = db.Column(db.Date)                              # Data embarque
protocolo = db.Column(db.String(50))                            # Protocolo

# Campos de totais:
valor_saldo_total = db.Column(db.Float)                         # Valor total
pallet_total = db.Column(db.Float)                              # Pallet total
peso_total = db.Column(db.Float)                                # Peso total

# Campos de frete:
transportadora = db.Column(db.String(100))                      # Transportadora
valor_frete = db.Column(db.Float)                               # Valor frete
valor_por_kg = db.Column(db.Float)                              # Valor por kg
modalidade = db.Column(db.String(50))                           # Modalidade
melhor_opcao = db.Column(db.String(100))                        # Melhor opcao
valor_melhor_opcao = db.Column(db.Float)                        # Valor melhor opcao
lead_time = db.Column(db.Integer)                               # Lead time

# Relacionamentos:
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'))     # ID cotacao
usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))     # ID usuario
```

---

## 🏗️ PreSeparacaoItem (app/carteira/models.py)

### DEPRECATED - NAO USAR!
### SEMPRE substituir por Separacao com status='PREVISAO'

Agora usamos Separacao com status='PREVISAO' para fazer tudo que PreSeparacaoItem fazia e melhor

### Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ID do lote de pre-separacao
num_pedido = db.Column(db.String(50), nullable=False, index=True)       # Numero pedido
cod_produto = db.Column(db.String(50), nullable=False, index=True)      # Codigo produto
cnpj_cliente = db.Column(db.String(20), index=True)             # CNPJ cliente
nome_produto = db.Column(db.String(255), nullable=True)         # Nome produto

# Quantidades:
qtd_original_carteira = db.Column(db.Numeric(15, 3), nullable=False)    # Quantidade original
qtd_selecionada_usuario = db.Column(db.Numeric(15, 3), nullable=False)  # Quantidade selecionada
qtd_restante_calculada = db.Column(db.Numeric(15, 3), nullable=False)   # Saldo restante

# Dados originais preservados:
valor_original_item = db.Column(db.Numeric(15,2))               # Valor original
peso_original_item = db.Column(db.Numeric(15,3))                # Peso original
hash_item_original = db.Column(db.String(128))                  # Hash para controle

# Campos editaveis preservados:
data_expedicao_editada = db.Column(db.Date, nullable=False)     # Data expedicao editada
data_agendamento_editada = db.Column(db.Date)                   # Data agendamento editada
protocolo_editado = db.Column(db.String(50))                    # Protocolo editado
observacoes_usuario = db.Column(db.Text)                        # Observacoes

# Status e controle:
recomposto = db.Column(db.Boolean, default=False, index=True)   # Status recomposicao
status = db.Column(db.String(20), default='CRIADO', index=True) # Status geral
tipo_envio = db.Column(db.String(10), default='total')          # total, parcial
data_criacao = db.Column(db.DateTime, default=datetime.utcnow)  # Data criacao
criado_por = db.Column(db.String(100))                          # Usuario criador

# Controle de recomposicao:
data_recomposicao = db.Column(db.DateTime)                      # Data recomposicao
recomposto_por = db.Column(db.String(100))                      # Usuario recomposicao
versao_carteira_original = db.Column(db.String(50))             # Versao original
versao_carteira_recomposta = db.Column(db.String(50))           # Versao recomposta
```

---

## 🚢 Embarque (app/embarques/models.py)

### Campos Principais
```python
# CAMPOS CORRETOS:
numero = db.Column(db.Integer, unique=True, nullable=True)       # Numero embarque
data_prevista_embarque = db.Column(db.Date, nullable=True)      # Data prevista
data_embarque = db.Column(db.Date, nullable=True)               # Data real embarque
status = db.Column(db.String(20), default='draft')              # draft, ativo, cancelado
tipo_carga = db.Column(db.String(20))                           # FRACIONADA, DIRETA
tipo_cotacao = db.Column(db.String(20), default='Automatica')   # Automatica, Manual

# Totais:
valor_total = db.Column(db.Float)                               # Valor total embarque
pallet_total = db.Column(db.Float)                              # Pallet total embarque
peso_total = db.Column(db.Float)                                # Peso total embarque

# Transportadora:
transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'))  # ID transportadora
modalidade = db.Column(db.String(50))                           # Tipo veiculo

# Campos de controle:
observacoes = db.Column(db.Text)                                # Observacoes
motivo_cancelamento = db.Column(db.Text, nullable=True)         # Motivo cancelamento
cancelado_em = db.Column(db.DateTime, nullable=True)            # Data cancelamento
cancelado_por = db.Column(db.String(100), nullable=True)        # Usuario cancelamento
criado_em = db.Column(db.DateTime, default=datetime.utcnow)     # Data criacao
criado_por = db.Column(db.String(100), default='Administrador') # Usuario criacao

# Relacionamentos:
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id')) # ID cotacao (para DIRETA)
```

### EmbarqueItem (app/embarques/models.py)
```python
# CAMPOS CORRETOS:
embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False) # ID embarque
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID lote separacao
cnpj_cliente = db.Column(db.String(20), nullable=True)          # CNPJ cliente
cliente = db.Column(db.String(120), nullable=False)             # Nome cliente
pedido = db.Column(db.String(50), nullable=False)               # Numero pedido
nota_fiscal = db.Column(db.String(20))                          # Numero NF
status = db.Column(db.String(20), default='ativo')              # ativo, cancelado

# Agendamento:
protocolo_agendamento = db.Column(db.String(50))                # Protocolo
data_agenda = db.Column(db.String(10))                          # Data agendamento

# Quantidades:
volumes = db.Column(db.Integer, nullable=True)                  # Volumes
peso = db.Column(db.Float)                                      # Peso item
valor = db.Column(db.Float)                                     # Valor item
pallets = db.Column(db.Float, nullable=True)                    # Pallets item

# Destino:
uf_destino = db.Column(db.String(2), nullable=False)            # UF destino
cidade_destino = db.Column(db.String(100), nullable=False)      # Cidade destino

# Validacao:
erro_validacao = db.Column(db.String(500), nullable=True)       # Erros validacao

# Relacionamentos:
cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id')) # ID cotacao (para FRACIONADA)
```

---

## 💰 FaturamentoProduto (app/faturamento/models.py)

### Campos Principais
```python
# CAMPOS CORRETOS:
numero_nf = db.Column(db.String(20), nullable=False, index=True) # Numero NF
data_fatura = db.Column(db.Date, nullable=False, index=True)     # Data fatura
cnpj_cliente = db.Column(db.String(20), nullable=False, index=True) # CNPJ cliente
nome_cliente = db.Column(db.String(255), nullable=False)         # Nome cliente
municipio = db.Column(db.String(100), nullable=True)            # Municipio
estado = db.Column(db.String(2), nullable=True)                 # Estado
vendedor = db.Column(db.String(100), nullable=True)             # Vendedor
equipe_vendas = db.Column(db.String(100), nullable=True)        # Equipe vendas
incoterm = db.Column(db.String(20), nullable=True)              # Incoterm

# Produto:
cod_produto = db.Column(db.String(50), nullable=False, index=True)   # Codigo produto
nome_produto = db.Column(db.String(200), nullable=False)        # Nome produto
qtd_produto_faturado = db.Column(db.Numeric(15, 3), default=0)  # Quantidade faturada
preco_produto_faturado = db.Column(db.Numeric(15, 4), default=0) # Preco faturado
valor_produto_faturado = db.Column(db.Numeric(15, 2), default=0) # Valor faturado
peso_unitario_produto = db.Column(db.Numeric(15, 3), default=0) # Peso unitario
peso_total = db.Column(db.Numeric(15, 3), default=0)            # Peso total

# Origem e status:
origem = db.Column(db.String(20), nullable=True, index=True)     # Numero pedido origem
status_nf = db.Column(db.String(20), default='Provisorio')      # Lancado, Cancelado, Provisorio

# Reversao de NF (Nota de Credito):
revertida = db.Column(db.Boolean, default=False)                # Se esta NF foi revertida
nota_credito_id = db.Column(db.Integer, nullable=True)          # ID da NF de credito que reverteu
data_reversao = db.Column(db.DateTime, nullable=True)           # Data/hora da reversao

# Auditoria:
created_at = db.Column(db.DateTime, default=agora_brasil)        # Data criacao
updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil) # Data atualizacao
created_by = db.Column(db.String(100), nullable=True)           # Usuario criacao
updated_by = db.Column(db.String(100), nullable=True)           # Usuario atualizacao
```

---

## 📋 RelatorioFaturamentoImportado (app/faturamento/models.py)

### Campos Principais
```python
# CAMPOS CORRETOS:
numero_nf = db.Column(db.String(20), nullable=False, index=True, unique=True) # Numero NF unico
data_fatura = db.Column(db.Date, nullable=True)                 # Data fatura
cnpj_cliente = db.Column(db.String(20), nullable=True)          # CNPJ cliente
nome_cliente = db.Column(db.String(255), nullable=True)         # Nome cliente
valor_total = db.Column(db.Float, nullable=True)                # Valor total NF
peso_bruto = db.Column(db.Float, nullable=True)                 # Peso bruto NF
municipio = db.Column(db.String(100), nullable=True)            # Municipio
estado = db.Column(db.String(2), nullable=True)                 # Estado
codigo_ibge = db.Column(db.String(10), nullable=True)           # Codigo IBGE
origem = db.Column(db.String(50), nullable=True)                # Origem
vendedor = db.Column(db.String(100), nullable=True)             # Vendedor
equipe_vendas = db.Column(db.String(100), nullable=True)        # Equipe vendas
incoterm = db.Column(db.String(20), nullable=True)              # Incoterm

# Transportadora:
cnpj_transportadora = db.Column(db.String(20), nullable=True)    # CNPJ transportadora
nome_transportadora = db.Column(db.String(255), nullable=True)  # Nome transportadora

# Controle:
ativo = db.Column(db.Boolean, default=True, nullable=False)     # Ativo/Inativo
inativado_em = db.Column(db.DateTime, nullable=True)            # Data inativacao
inativado_por = db.Column(db.String(100), nullable=True)        # Usuario inativacao
criado_em = db.Column(db.DateTime, default=datetime.utcnow)     # Data criacao
```

---

## 💸 DespesaExtra (app/fretes/models.py)

### Despesas extras vinculadas a fretes com suporte a integracao Odoo

### REGRAS DE STATUS:
- **PENDENTE**: Despesa criada, aguardando processamento
- **VINCULADO_CTE**: CTe Complementar vinculado, pronto para Odoo
- **LANCADO_ODOO**: Lancado com sucesso no Odoo (16 etapas)
- **LANCADO**: Finalizado sem Odoo (NFS/Recibo)
- **CANCELADO**: Despesa cancelada

### Campos Principais
```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)
frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)  # FK Frete
fatura_frete_id = db.Column(db.Integer, db.ForeignKey('faturas_frete.id'), nullable=True)  # FK Fatura

# STATUS DA DESPESA:
status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)  # Status
# Valores: PENDENTE, VINCULADO_CTE, LANCADO_ODOO, LANCADO, CANCELADO

# VINCULO COM CTe COMPLEMENTAR:
despesa_cte_id = db.Column(db.Integer, db.ForeignKey('conhecimento_transporte.id'), nullable=True, index=True)  # FK CTe
chave_cte = db.Column(db.String(44), nullable=True, index=True)  # Chave do CTe

# INTEGRACAO ODOO:
odoo_dfe_id = db.Column(db.Integer, nullable=True, index=True)       # ID do DFe no Odoo
odoo_purchase_order_id = db.Column(db.Integer, nullable=True)        # ID do PO no Odoo
odoo_invoice_id = db.Column(db.Integer, nullable=True)               # ID da Invoice no Odoo
lancado_odoo_em = db.Column(db.DateTime, nullable=True)              # Data/hora lancamento
lancado_odoo_por = db.Column(db.String(100), nullable=True)          # Usuario que lancou

# COMPROVANTE (NFS/RECIBO):
comprovante_path = db.Column(db.String(500), nullable=True)          # Caminho S3 do comprovante
comprovante_nome_arquivo = db.Column(db.String(255), nullable=True)  # Nome original do arquivo

# CLASSIFICACAO:
tipo_despesa = db.Column(db.String(50), nullable=False)      # REENTREGA, TDE, PERNOITE, etc.
setor_responsavel = db.Column(db.String(20), nullable=False) # COMERCIAL, LOGISTICA, etc.
motivo_despesa = db.Column(db.String(50), nullable=False)    # Motivo da despesa

# DOCUMENTO:
tipo_documento = db.Column(db.String(20), nullable=False)    # CTe, NFS, RECIBO, etc.
numero_documento = db.Column(db.String(50), nullable=False)  # Numero do documento

# VALORES:
valor_despesa = db.Column(db.Float, nullable=False)          # Valor da despesa
vencimento_despesa = db.Column(db.Date)                      # Data vencimento

# OBSERVACOES E AUDITORIA:
observacoes = db.Column(db.Text)                             # Observacoes
criado_em = db.Column(db.DateTime, default=datetime.utcnow)  # Data criacao
criado_por = db.Column(db.String(100), nullable=False)       # Usuario criador

# RELACIONAMENTOS:
fatura_frete = db.relationship('FaturaFrete', backref='despesas_extras')
cte = db.relationship('ConhecimentoTransporte', foreign_keys=[despesa_cte_id], backref='despesas_extras_vinculadas')
```

### Logica de Sugestao de CTe para Despesa Extra
```
PRIORIDADE 1: CTe Complementar que referencia CTe vinculado ao Frete da Despesa
PRIORIDADE 2: CTe Complementar que referencia CTe com NFs em comum com Frete
PRIORIDADE 3: CTe Complementar com mesmo CNPJ cliente + prefixo transportadora
```

---

## CadastroPalletizacao (app/producao/models.py)

### Campos Principais
```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)

# Dados do produto (conforme CSV)
cod_produto = db.Column(db.String(50), nullable=False, unique=True, index=True)  # Cod.Produto
nome_produto = db.Column(db.String(255), nullable=False)  # Descricao Produto

# Fatores de conversao (conforme CSV)
palletizacao = db.Column(db.Float, nullable=False)  # PALLETIZACAO: qtd / palletizacao = pallets
peso_bruto = db.Column(db.Float, nullable=False)    # PESO BRUTO: qtd * peso_bruto = peso total

# Dados de dimensoes (interessante para calculos)
altura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
largura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
comprimento_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)

# Subcategorias para filtros avancados
tipo_embalagem = db.Column(db.String(50), nullable=True, index=True)
tipo_materia_prima = db.Column(db.String(50), nullable=True, index=True)
categoria_produto = db.Column(db.String(50), nullable=True, index=True)
subcategoria = db.Column(db.String(50), nullable=True)
linha_producao = db.Column(db.String(50), nullable=True, index=True)

# Classificacao do produto (MTO/MTS/Comprado)
produto_comprado = db.Column(db.Boolean, default=False, nullable=True)    # Produto e comprado (nao produzido)
produto_produzido = db.Column(db.Boolean, default=True, nullable=True)    # Produto e produzido internamente
produto_vendido = db.Column(db.Boolean, default=True, nullable=True)      # Produto e vendido (vs. intermediario)
lead_time_mto = db.Column(db.Integer, nullable=True)                      # Lead time Make-to-Order (dias)
disparo_producao = db.Column(db.Float, nullable=True)                     # Ponto de disparo para producao
custo_produto = db.Column(db.Numeric(15, 6), nullable=True)              # Custo unitario do produto

# Status
ativo = db.Column(db.Boolean, nullable=False, default=True)

# Auditoria
created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

def calcular_pallets(self, quantidade):
   """Calcula quantos pallets para uma quantidade"""
   if self.palletizacao > 0:
      return round(quantidade / self.palletizacao, 2)
   return 0

def calcular_peso_total(self, quantidade):
   """Calcula peso total para uma quantidade"""
   return round(quantidade * self.peso_bruto, 2)
```

---

## 💰 ContasAReceber (app/financeiro/models.py)

### Contas a Receber importadas do Odoo com enriquecimento local

### CHAVE UNICA: empresa + titulo_nf + parcela

### Campos Principais
```python
# CAMPOS DO ODOO (importados automaticamente):
empresa = db.Column(db.Integer, nullable=False, index=True)  # 1=FB, 2=SC, 3=CD
titulo_nf = db.Column(db.String(20), nullable=False, index=True)  # NF-e
parcela = db.Column(db.String(10), nullable=False, index=True)  # Numero da parcela

# Cliente:
cnpj = db.Column(db.String(20), nullable=True, index=True)  # CNPJ do cliente
raz_social = db.Column(db.String(255), nullable=True)  # Razao Social completa
raz_social_red = db.Column(db.String(100), nullable=True)  # Nome fantasia/trade_name
uf_cliente = db.Column(db.String(2), nullable=True, index=True)  # UF do cliente

# Datas do Odoo:
emissao = db.Column(db.Date, nullable=True)  # Data de emissao
vencimento = db.Column(db.Date, nullable=True, index=True)  # Data de vencimento

# Valores do Odoo:
valor_original = db.Column(db.Float, nullable=True)  # Saldo Total (balance + desconto_concedido)
desconto_percentual = db.Column(db.Float, nullable=True)  # desconto_concedido_percentual / 100
desconto = db.Column(db.Float, nullable=True)  # desconto_concedido
tipo_titulo = db.Column(db.String(100), nullable=True)  # Forma de Pagamento
parcela_paga = db.Column(db.Boolean, default=False)  # l10n_br_paga
status_pagamento_odoo = db.Column(db.String(50), nullable=True)  # x_studio_status_de_pagamento

# CAMPOS CALCULADOS:
valor_titulo = db.Column(db.Float, nullable=True)  # valor_original - desconto - SUM(abatimentos)
liberacao_prevista_antecipacao = db.Column(db.Date, nullable=True)  # Via LiberacaoAntecipacao + EntregaMonitorada

# CAMPOS DO SISTEMA (preenchidos manualmente):
confirmacao_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
forma_confirmacao_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
data_confirmacao = db.Column(db.DateTime, nullable=True)  # Log automatico
confirmacao_entrega = db.Column(db.Text, nullable=True)
observacao = db.Column(db.Text, nullable=True)
alerta = db.Column(db.Boolean, default=False, nullable=False)
acao_necessaria_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
obs_acao_necessaria = db.Column(db.Text, nullable=True)
data_lembrete = db.Column(db.Date, nullable=True)

# RELACIONAMENTOS (dados obtidos dinamicamente - NAO sao colunas):
entrega_monitorada_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=True)

# CAMPOS OBTIDOS VIA RELACIONAMENTO entrega_monitorada (NAO existem como colunas):
# - data_entrega_prevista (via entrega_monitorada.data_entrega_prevista)
# - data_hora_entrega_realizada (via entrega_monitorada.data_hora_entrega_realizada)
# - status_finalizacao (via entrega_monitorada.status_finalizacao)
# - nova_nf (via entrega_monitorada.nova_nf)
# - reagendar (via entrega_monitorada.reagendar)
# - data_embarque (via entrega_monitorada.data_embarque)
# - transportadora (via entrega_monitorada.transportadora)
# - vendedor (via entrega_monitorada.vendedor)
# - canhoto_arquivo (via entrega_monitorada.canhoto_arquivo)
# - nf_cd (via entrega_monitorada.nf_cd)
# - ultimo_agendamento_* (via entrega_monitorada.agendamentos)

# PROPERTY nf_cancelada (NAO e coluna, e calculado dinamicamente):
# nf_cancelada = @property que busca FaturamentoProduto.status_nf == 'Cancelado'

# Auditoria:
criado_em = db.Column(db.DateTime, default=datetime.utcnow)
atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
odoo_write_date = db.Column(db.DateTime, nullable=True)  # write_date do Odoo para sync incremental
ultima_sincronizacao = db.Column(db.DateTime, nullable=True)
```

---

## 📋 ContasAReceberTipo (app/financeiro/models.py)

### Tabela de dominio para tipos usados em Contas a Receber e Abatimento

```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)
tipo = db.Column(db.String(100), nullable=False)  # Nome do tipo
considera_a_receber = db.Column(db.Boolean, default=True, nullable=False)  # Se considera na projecao
tabela = db.Column(db.String(50), nullable=False)  # contas_a_receber ou contas_a_receber_abatimento
campo = db.Column(db.String(50), nullable=False)  # confirmacao, forma_confirmacao, acao_necessaria, tipo
explicacao = db.Column(db.Text, nullable=True)
ativo = db.Column(db.Boolean, default=True, nullable=False)
```

---

## 📋 LiberacaoAntecipacao (app/financeiro/models.py)

### Configuracao de prazos de liberacao para antecipacao de recebiveis

### PRIORIDADE DE MATCH: 1. prefixo_cnpj -> 2. nome_exato -> 3. contem_nome

```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)
criterio_identificacao = db.Column(db.String(20), nullable=False)  # prefixo_cnpj, nome_exato, contem_nome
identificador = db.Column(db.String(255), nullable=False)  # Valor para identificacao
uf = db.Column(db.String(100), default='TODOS', nullable=False)  # "TODOS" ou lista de UFs
dias_uteis_previsto = db.Column(db.Integer, nullable=False)  # Dias uteis para liberacao
ativo = db.Column(db.Boolean, default=True, nullable=False)

# Metodos uteis:
# LiberacaoAntecipacao.buscar_configuracao(cnpj, razao_social, uf) - Busca configuracao por prioridade
# LiberacaoAntecipacao.calcular_data_liberacao(data_entrega, dias_uteis) - Calcula data de liberacao
# LiberacaoAntecipacao.extrair_prefixo_cnpj(cnpj) - Extrai os 8 primeiros digitos do CNPJ
```

---

## 📋 ContasAReceberAbatimento (app/financeiro/models.py)

### Abatimentos vinculados a Contas a Receber (1:N)

```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)
conta_a_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), nullable=False, index=True)
tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
motivo = db.Column(db.Text, nullable=True)
doc_motivo = db.Column(db.String(255), nullable=True)  # Documento que justifica
valor = db.Column(db.Float, nullable=False)
previsto = db.Column(db.Boolean, default=True, nullable=False)  # Se e previsto ou ja realizado
data = db.Column(db.Date, nullable=True)
data_vencimento = db.Column(db.Date, nullable=True)
```

---

## 📋 ContasAReceberSnapshot (app/financeiro/models.py)

### Historico de alteracoes em campos vindos do Odoo

```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)
conta_a_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), nullable=False, index=True)
campo = db.Column(db.String(50), nullable=False)  # Nome do campo alterado
valor_anterior = db.Column(db.Text, nullable=True)  # JSON string
valor_novo = db.Column(db.Text, nullable=True)  # JSON string
alterado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
alterado_por = db.Column(db.String(100), nullable=True)
odoo_write_date = db.Column(db.DateTime, nullable=True)

# Metodo util:
# ContasAReceberSnapshot.registrar_alteracao(conta, campo, valor_anterior, valor_novo, usuario, odoo_write_date)
```

---

## Tabelas Auxiliares (usadas pelos scripts do Agente Logistico)

### MovimentacaoEstoque (app/estoque/models.py)

```python
# Campos principais:
cod_produto = db.Column(db.String(50))           # Codigo do produto
qtd_movimentacao = db.Column(db.Float)           # Quantidade (+ entrada, - saida)
tipo_movimentacao = db.Column(db.String)         # ENTRADA, SAIDA, AJUSTE, COMPRA
data_movimentacao = db.Column(db.DateTime)       # Data/hora da movimentacao
ativo = db.Column(db.Boolean)                    # Se o registro esta ativo

# Calculo de estoque atual:
# SELECT SUM(qtd_movimentacao) FROM movimentacao_estoque WHERE cod_produto = ? AND ativo = True
```

### ProgramacaoProducao (app/producao/models.py)

```python
# Campos principais:
cod_produto = db.Column(db.String(50))           # Codigo do produto
data_programacao = db.Column(db.Date)            # Data prevista da producao
qtd_programada = db.Column(db.Float)             # Quantidade a ser produzida
linha_producao = db.Column(db.String(50))        # Linha de producao
status = db.Column(db.String)                    # Status da programacao
```

### ContatoAgendamento (app/cadastros/models.py)

```python
# Campos principais:
cnpj = db.Column(db.String(20))                  # CNPJ do cliente
forma = db.Column(db.String(50))                 # Forma de agendamento
contato = db.Column(db.String(255))              # Usuario/telefone/email
observacao = db.Column(db.String(255))           # Observacoes

# Valores de forma:
# 'SEM AGENDAMENTO' ou NULL -> Nao exige agendamento
# 'Portal' -> Agendamento via portal
# 'Telefone' -> Agendamento por telefone
# 'E-mail' -> Agendamento por email
# 'WhatsApp' -> Agendamento por WhatsApp
```

### CidadeAtendida (app/cotacao/models.py)

```python
# Campos principais:
cidade_id = db.Column(db.Integer)                # FK para tabela cidades
codigo_ibge = db.Column(db.String(10))           # Codigo IBGE da cidade
transportadora_id = db.Column(db.Integer)        # FK para transportadoras
nome_tabela = db.Column(db.String(50))           # Nome da tabela de frete
lead_time = db.Column(db.Integer)                # Dias para entrega
uf = db.Column(db.String(2))                     # UF da cidade
```

### CadastroSubRota (app/cotacao/models.py)

```python
# Campos principais:
cod_uf = db.Column(db.String(2))                 # UF
nome_cidade = db.Column(db.String(100))          # Nome da cidade
sub_rota = db.Column(db.String(50))              # Codigo da sub-rota
```

---

## 📦 Devolucoes (app/devolucao/models.py)

> **Documentacao completa**: `app/devolucao/README.md`

### NFDevolucao - Tabela Principal Unificada

```python
__tablename__ = 'nf_devolucao'

# Campos do registro inicial:
numero_nfd = db.Column(db.String(20), nullable=False)      # Numero da NFD
data_registro = db.Column(db.DateTime)                      # Data do registro
motivo = db.Column(db.String(50), nullable=False)           # AVARIA, FALTA, SOBRA...
descricao_motivo = db.Column(db.Text)                       # Descricao detalhada
numero_nf_venda = db.Column(db.String(20))                  # NF de venda relacionada

# Campos do DFe Odoo:
odoo_dfe_id = db.Column(db.Integer, unique=True)            # ID do DFe no Odoo
chave_nfd = db.Column(db.String(44), unique=True)           # Chave de acesso
valor_total = db.Column(db.Numeric(15, 2))                  # Valor total

# Arquivos:
nfd_xml_path = db.Column(db.String(500))                    # Caminho XML no S3
nfd_pdf_path = db.Column(db.String(500))                    # Caminho PDF no S3

# Status: REGISTRADA -> VINCULADA_DFE -> EM_TRATATIVA -> FINALIZADA
status = db.Column(db.String(30), default='REGISTRADA')
```

### OcorrenciaDevolucao - Tratativa Comercial/Logistica

```python
__tablename__ = 'ocorrencia_devolucao'

numero_ocorrencia = db.Column(db.String(20), unique=True)   # OC-YYYYMM-XXXX

# Secao Logistica:
destino = db.Column(db.String(20))                          # RETORNO, DESCARTE
localizacao_atual = db.Column(db.String(20))                # CLIENTE, EM_TRANSITO, CD

# Secao Comercial:
categoria = db.Column(db.String(30))                        # QUALIDADE, COMERCIAL...
responsavel = db.Column(db.String(30))                      # NACOM, TRANSPORTADORA, CLIENTE
status = db.Column(db.String(30), default='ABERTA')         # ABERTA, EM_ANALISE, RESOLVIDA
```

### DeParaProdutoCliente - Mapeamento de Codigos

```python
__tablename__ = 'depara_produto_cliente'

prefixo_cnpj = db.Column(db.String(8), nullable=False)      # 8 primeiros digitos CNPJ
codigo_cliente = db.Column(db.String(50), nullable=False)   # Codigo usado pelo cliente
nosso_codigo = db.Column(db.String(50), nullable=False)     # Nosso codigo interno
fator_conversao = db.Column(db.Numeric(10, 4), default=1.0) # Fator de conversao

# Constraint unica: prefixo_cnpj + codigo_cliente
```
