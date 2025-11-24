# 🔴 [PRECISION MODE] - MODO PRECISION ENGINEER ATIVO

## REGRAS ABSOLUTAS - NUNCA IGNORAR:

### ✅ SEMPRE FAZER:
1. **INICIAR TODA RESPOSTA COM**: "CONFIRMAÇÃO DO ENTENDIMENTO: Entendi que você precisa..."
2. **MOSTRAR EVIDÊNCIAS**: Citar arquivo:linha ANTES de qualquer modificação
3. **VERIFICAR TUDO**: Ler arquivos completos, verificar imports, testar mentalmente
4. **QUESTIONAR**: Se algo não estiver 100% claro, PARAR e PERGUNTAR

### ❌ NUNCA FAZER:
1. **NUNCA assumir** comportamento pelo nome da função
2. **NUNCA inventar** imports ou caminhos
3. **NUNCA modificar** sem mostrar o código atual primeiro
4. **NUNCA pular** direto para a solução

### 📋 FORMATO OBRIGATÓRIO DE RESPOSTA:
```
1. CONFIRMAÇÃO DO ENTENDIMENTO:
   "Entendi que você precisa [EXATAMENTE o que foi pedido]..."

2. ANÁLISE DETALHADA:
   "Analisando arquivo X, linhas Y-Z, vejo que..."
   [MOSTRAR CÓDIGO ATUAL]

3. QUESTÕES (se houver):
   "Antes de prosseguir, preciso confirmar:..."

4. IMPLEMENTAÇÃO:
   "Com base na análise completa..."
```

### 🎯 PALAVRA DE ATIVAÇÃO:
Quando ver **"pense profundamente"** ou **"[PRECISION MODE]"**: DOBRAR o nível de rigor e detalhe.

---

# CLAUDE.md - Referência de Modelos e Campos

## ⚠️ ATENÇÃO: Use SEMPRE os nomes EXATOS dos campos listados aqui

## SE NÃO TIVER CERTEZA, NÃO ALTERE E PERGUNTE

## 🔴 LEIA TAMBÉM:
- **REGRAS_NEGOCIO.md** - Regras de negócio e comportamento do sistema
- **ESPECIFICACAO_SINCRONIZACAO_ODOO.md** - Processo de sincronização com Odoo (futuro)
- **FLUXO_SINCRONIZACAO_NF.md** - Fluxogramas do processo de NF (futuro)
- **CARD_SEPARACAO.md** - Detalhamento da função do Card de Separação e Separação Compacta na Carteira Agrupada
- **app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md** - 🔴 DOCUMENTAÇÃO CRÍTICA da API TagPlus com endpoints testados e estruturas reais
- **app/claude_ai_lite/README.md** - 🤖 Módulo de IA conversacional (consultas e criação de separações via linguagem natural)

Este arquivo contém os nomes corretos dos campos de todos os modelos para evitar erros como `data_expedicao_pedido` (❌ INCORRETO) em vez de `expedicao` (✅ CORRETO).


# 📋 MAPEAMENTO DE CAMPOS DOS MODELOS - REFERÊNCIA PARA CLAUDE AI

**Objetivo**: Evitar erros de nomes de campos ao desenvolver funcionalidades  
**Data de Criação**: 22/07/2025  
**Última Atualização**: 23/07/2025

# CRIAÇÃO DE TABELAS E CAMPOS:

**Formato esperado**: Todos os campos ou modelos criados, deverá ser gerado um script python para rodar localmente e um script SQL simples para rodar no Shell do Render.
==============================
- Exemplo de script python:

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def tornar_motor_nullable():
    app = create_app()

    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT column_name, is_nullable.....
===========================
---

## 🎯 CarteiraPrincipal (app/carteira/models.py)

### 📅 Campos de Datas e Agendamento
```python
# CAMPOS CORRETOS - SEMPRE USAR ESTES NOMES:
data_entrega_pedido = db.Column(db.Date, nullable=True)          # ✅ Data entrega solicitada pelo comercial
observ_ped_1 = db.Column(db.Text, nullable=True)                # ✅ Observações

# ❌ CAMPOS QUE NÃO EXISTEM - NUNCA USAR:
# data_entrega ❌
# expedicao ❌
# agendamento ❌
# protocolo ❌
# agendamento_confirmado ❌
# hora_agendamento ❌
# data_expedicao_pedido ❌
# data_agendamento_pedido ❌
```

### 📊 Campos de Quantidades e Valores
```python
# CAMPOS CORRETOS E USADOS:
qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)       # ✅ Quantidade original
qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False) # ✅ Saldo disponível
qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)  # ✅ Quantidade cancelada
preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)      # ✅ Preço unitário


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


### 🏷️ Tags do Pedido (Odoo)
```python
# ✅ CAMPO PARA TAGS DO ODOO:
tags_pedido = db.Column(db.Text, nullable=True)  # ✅ JSON: [{"name": "VIP", "color": 5}]

# FORMATO JSON ESPERADO:
# [
#   {"name": "Urgente", "color": 1},
#   {"name": "VIP", "color": 5},
#   {"name": "Grande Volume", "color": 7}
# ]

# SINCRONIZAÇÃO: Vem do campo tag_ids do sale.order no Odoo
# MODELO ODOO: crm.tag com campos id, name, color
# EXIBIÇÃO: Template agrupados_balanceado.html usa badges coloridos
```

---

## 🚛 Separacao (app/separacao/models.py)
### Única fonte da verdade para projetar as saidas de estoque através de sincronizado_nf=False

### ⚠️ REGRA CRÍTICA: sincronizado_nf
- **sincronizado_nf=False**: Item SEMPRE aparece na carteira e SEMPRE é projetado no estoque
- **sincronizado_nf=True**: Foi faturado (tem NF), NÃO aparece na carteira, NÃO projeta estoque


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
numero_nf = db.Column(db.String(20), nullable=True)             # ✅ NF associada quando sincronizada

# Campos de cliente:
pedido_cliente = db.Column(db.String(100), nullable=True)       # ✅ Pedido de Compra do Cliente
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
observ_ped_1 = db.Column(db.String(700), nullable=True)         # ✅ Observações (truncado automaticamente)
roteirizacao = db.Column(db.String(255), nullable=True)         # ✅ Transportadora sugerida
rota = db.Column(db.String(50), nullable=True)                  # ✅ Rota
sub_rota = db.Column(db.String(50), nullable=True)              # ✅ Sub-rota

# 🆕 NOVOS CAMPOS PARA SUBSTITUIR PEDIDO E PRESEPARACAOITEM
status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)  # Valores comuns de status: 'PREVISAO', 'ABERTO', 'COTADO', 'EMBARCADO', 'FATURADO', 'NF no CD'
nf_cd = db.Column(db.Boolean, default=False, nullable=False)  # NF voltou para o CD
sincronizado_nf = db.Column(db.Boolean, default=False, nullable=True)  # Indica se foi sincronizado com NF, gatilho principal para projetar saidas de estoque



## 📦 Pedido (app/pedidos/models.py) 
### Modelo Pedido que agora é uma VIEW agregando dados de Separacao

### ⚠️ REGRA DA VIEW:
- **IGNORA**: Separacao com status='PREVISAO' 
- **AGREGA**: Por separacao_lote_id e num_pedido
- **INCLUI**: Apenas status != 'PREVISAO'
  
    __tablename__ = 'pedidos'
    __table_args__ = {'info': {'is_view': True}}  # Marca como VIEW para SQLAlchemy

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

### ⛔ DEPRECATED - NÃO USAR!
### SEMPRE substituir por Separacao com status='PREVISAO'
Agora usamos Separacao com status='PREVISAO' para fazer tudo que PreSeparacaoItem fazia e melhor

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ✅ ID do lote de pré-separação
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

## 💸 DespesaExtra (app/fretes/models.py)

### Despesas extras vinculadas a fretes com suporte a integração Odoo

### ⚠️ REGRAS DE STATUS:
- **PENDENTE**: Despesa criada, aguardando processamento
- **VINCULADO_CTE**: CTe Complementar vinculado, pronto para Odoo
- **LANCADO_ODOO**: Lançado com sucesso no Odoo (16 etapas)
- **LANCADO**: Finalizado sem Odoo (NFS/Recibo)
- **CANCELADO**: Despesa cancelada

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)
frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)  # ✅ FK Frete
fatura_frete_id = db.Column(db.Integer, db.ForeignKey('faturas_frete.id'), nullable=True)  # ✅ FK Fatura

# STATUS DA DESPESA:
status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)  # ✅ Status
# Valores: PENDENTE, VINCULADO_CTE, LANCADO_ODOO, LANCADO, CANCELADO

# VÍNCULO COM CTe COMPLEMENTAR:
despesa_cte_id = db.Column(db.Integer, db.ForeignKey('conhecimento_transporte.id'), nullable=True, index=True)  # ✅ FK CTe
chave_cte = db.Column(db.String(44), nullable=True, index=True)  # ✅ Chave do CTe

# INTEGRAÇÃO ODOO:
odoo_dfe_id = db.Column(db.Integer, nullable=True, index=True)       # ✅ ID do DFe no Odoo
odoo_purchase_order_id = db.Column(db.Integer, nullable=True)        # ✅ ID do PO no Odoo
odoo_invoice_id = db.Column(db.Integer, nullable=True)               # ✅ ID da Invoice no Odoo
lancado_odoo_em = db.Column(db.DateTime, nullable=True)              # ✅ Data/hora lançamento
lancado_odoo_por = db.Column(db.String(100), nullable=True)          # ✅ Usuário que lançou

# COMPROVANTE (NFS/RECIBO):
comprovante_path = db.Column(db.String(500), nullable=True)          # ✅ Caminho S3 do comprovante
comprovante_nome_arquivo = db.Column(db.String(255), nullable=True)  # ✅ Nome original do arquivo

# CLASSIFICAÇÃO:
tipo_despesa = db.Column(db.String(50), nullable=False)      # ✅ REENTREGA, TDE, PERNOITE, etc.
setor_responsavel = db.Column(db.String(20), nullable=False) # ✅ COMERCIAL, LOGISTICA, etc.
motivo_despesa = db.Column(db.String(50), nullable=False)    # ✅ Motivo da despesa

# DOCUMENTO:
tipo_documento = db.Column(db.String(20), nullable=False)    # ✅ CTe, NFS, RECIBO, etc.
numero_documento = db.Column(db.String(50), nullable=False)  # ✅ Número do documento

# VALORES:
valor_despesa = db.Column(db.Float, nullable=False)          # ✅ Valor da despesa
vencimento_despesa = db.Column(db.Date)                      # ✅ Data vencimento

# OBSERVAÇÕES E AUDITORIA:
observacoes = db.Column(db.Text)                             # ✅ Observações
criado_em = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ Data criação
criado_por = db.Column(db.String(100), nullable=False)       # ✅ Usuário criador

# RELACIONAMENTOS:
fatura_frete = db.relationship('FaturaFrete', backref='despesas_extras')
cte = db.relationship('ConhecimentoTransporte', foreign_keys=[despesa_cte_id], backref='despesas_extras_vinculadas')
```

### 📋 Lógica de Sugestão de CTe para Despesa Extra
```
PRIORIDADE 1: CTe Complementar que referencia CTe vinculado ao Frete da Despesa
PRIORIDADE 2: CTe Complementar que referencia CTe com NFs em comum com Frete
PRIORIDADE 3: CTe Complementar com mesmo CNPJ cliente + prefixo transportadora
```

---

## CadastroPalletizacao (app/producao/models.py)

### 📋 Campos Principais
```python
# CAMPOS CORRETOS:
id = db.Column(db.Integer, primary_key=True)

# Dados do produto (conforme CSV)
cod_produto = db.Column(db.String(50), nullable=False, unique=True, index=True)  # Cód.Produto
nome_produto = db.Column(db.String(255), nullable=False)  # Descrição Produto

# Fatores de conversão (conforme CSV)
palletizacao = db.Column(db.Float, nullable=False)  # PALLETIZACAO: qtd / palletizacao = pallets
peso_bruto = db.Column(db.Float, nullable=False)    # PESO BRUTO: qtd * peso_bruto = peso total

# Dados de dimensões (interessante para cálculos)
altura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
largura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
comprimento_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)

# Subcategorias para filtros avançados
tipo_embalagem = db.Column(db.String(50), nullable=True, index=True)
tipo_materia_prima = db.Column(db.String(50), nullable=True, index=True)
categoria_produto = db.Column(db.String(50), nullable=True, index=True)
subcategoria = db.Column(db.String(50), nullable=True)
linha_producao = db.Column(db.String(50), nullable=True, index=True)

# Status
ativo = db.Column(db.Boolean, nullable=False, default=True)

# Auditoria
created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

def __repr__(self):
   return f'<CadastroPalletizacao {self.cod_produto} - Pallet: {self.palletizacao}>'

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

### ✅ Busca de Carteira - USO CORRETO:
```python
# Para buscar itens na carteira:
items = Separacao.query.filter_by(
    sincronizado_nf=False  # ✅ CORRETO - Critério principal
).all()

# Separacao TEM status próprio:
items = Separacao.query.filter_by(
    status='PREVISAO'  # ✅ CORRETO - Para pré-separações
).all()

# NÃO fazer JOIN desnecessário com Pedido VIEW
```

---


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




