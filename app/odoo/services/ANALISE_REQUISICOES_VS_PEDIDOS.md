# 📊 Análise: Requisições vs Pedidos de Compras

## 🎯 OBJETIVO
Avaliar se vale mais a pena:
- **Opção A**: Enriquecer as requisições com dados de pedidos (1 entidade)
- **Opção B**: Manter separado (2 entidades independentes)

---

## 📋 ESTRUTURA ATUAL

### 1. RequisicaoCompras (Necessidade)
```python
# Informações da Necessidade
num_requisicao                 # REQ/FB/06611
data_requisicao_criacao        # Quando foi criada
usuario_requisicao_criacao     # Quem criou
data_requisicao_solicitada     # Quando precisa

# Produto e Quantidade
cod_produto                    # O que precisa
nome_produto
qtd_produto_requisicao         # Quanto precisa
qtd_produto_sem_requisicao     # Quanto ainda falta

# Status e Prazos
status                         # Pendente, Aprovada, Concluída
lead_time_requisicao          # Prazo necessário
necessidade                   # É crítico?
data_necessidade              # Até quando

# Rastreamento Odoo
odoo_id                       # ID da linha no Odoo
requisicao_odoo_id            # ID da requisição pai
status_requisicao             # rascunho, aprovada
```

**CONSTRAINT**: `UNIQUE (num_requisicao, cod_produto)`
- 1 requisição pode ter **N produtos**
- Cada produto aparece **1 vez** por requisição

---

### 2. PedidoCompras (Compra Efetiva)
```python
# Informações do Pedido
num_pedido                    # PO/FB/01234  (UNIQUE)
num_requisicao               # REQ/FB/06611 (informativo, SEM FK)
data_pedido_criacao
usuario_pedido_criacao

# Fornecedor
cnpj_fornecedor
raz_social
numero_nf                    # NF do fornecedor

# Produto e Preços
cod_produto
nome_produto
qtd_produto_pedido
preco_produto_pedido         # ⚠️ REQUISIÇÃO NÃO TEM
icms_produto_pedido          # ⚠️ REQUISIÇÃO NÃO TEM
pis_produto_pedido           # ⚠️ REQUISIÇÃO NÃO TEM
cofins_produto_pedido        # ⚠️ REQUISIÇÃO NÃO TEM

# Datas e Prazos
data_pedido_previsao
data_pedido_entrega
lead_time_pedido
lead_time_previsto

# Confirmação
confirmacao_pedido
confirmado_por
confirmado_em

# Rastreamento Odoo
odoo_id
```

**CONSTRAINT**: `UNIQUE (num_pedido)`
- 1 pedido = 1 fornecedor + 1 produto
- Para comprar 3 produtos = 3 pedidos

---

## 🔄 RELACIONAMENTO ATUAL

```
RequisicaoCompras (1 requisição, N produtos)
    ↓ (relação fraca via num_requisicao)
PedidoCompras (1 pedido, 1 produto, 1 fornecedor)
```

**PROBLEMAS IDENTIFICADOS:**
1. ❌ Sem FK formal entre Requisição → Pedido
2. ❌ 1 requisição pode gerar N pedidos (1 por fornecedor)
3. ❌ Difícil rastrear: "Qual pedido atende qual requisição?"
4. ❌ Requisição pode ser parcialmente atendida por múltiplos pedidos

---

## 💡 CENÁRIOS DE USO

### Cenário 1: Requisição Simples
```
REQUISIÇÃO REQ/FB/06611
- Produto A: 100 unidades
- Produto B: 50 unidades

PEDIDOS GERADOS:
PO/001 → Fornecedor X → Produto A: 100 un → R$ 10,00/un
PO/002 → Fornecedor Y → Produto B: 50 un → R$ 5,00/un
```

**Relação**: 1 Requisição → 2 Pedidos

---

### Cenário 2: Requisição Parcialmente Atendida
```
REQUISIÇÃO REQ/FB/06612
- Produto C: 1000 unidades

PEDIDOS GERADOS:
PO/003 → Fornecedor Z → Produto C: 600 un → Entrega: 10/11
PO/004 → Fornecedor W → Produto C: 400 un → Entrega: 15/11
```

**Relação**: 1 Requisição → 2 Pedidos (mesmo produto, fornecedores diferentes)

---

### Cenário 3: Múltiplas Requisições em 1 Pedido
```
REQUISIÇÃO REQ/FB/06613 → Produto D: 50 un
REQUISIÇÃO REQ/FB/06614 → Produto D: 30 un

PEDIDO GERADO:
PO/005 → Fornecedor A → Produto D: 80 un
```

**Relação**: 2 Requisições → 1 Pedido (consolidação)

---

## ⚖️ COMPARAÇÃO: OPÇÃO A vs OPÇÃO B

### OPÇÃO A: Enriquecer Requisições (1 Entidade)

#### ✅ VANTAGENS:
1. **Simplicidade**: Apenas 1 tabela para gerenciar
2. **Menos JOINs**: Queries mais simples
3. **Dados centralizados**: Tudo em um lugar
4. **Histórico único**: Fácil rastrear mudanças

#### ❌ DESVANTAGENS:
1. **Redundância**: Mesma requisição com múltiplos pedidos = dados duplicados
2. **Complexidade**: Como armazenar N pedidos em 1 requisição?
   - JSON de pedidos?
   - Múltiplas linhas?
3. **Perda de granularidade**: Difícil distinguir status de cada pedido
4. **Campos incompatíveis**:
   - Requisição tem N produtos
   - Pedido tem 1 produto + 1 fornecedor + preços
5. **Consolidação**: Como representar cenário 3?

#### 🤔 IMPLEMENTAÇÃO:
```python
class RequisicaoCompras:
    # Campos atuais...

    # ❌ PROBLEMA: Como adicionar campos de pedido?
    pedidos_relacionados = db.Column(JSONB)  # Lista de IDs?
    # Mas e os campos de fornecedor?
    # E os preços?
    # E os impostos?
```

**CONCLUSÃO**: ❌ **NÃO RECOMENDADO**
- Muita complexidade
- Perde semântica de negócio
- Difícil manter integridade

---

### OPÇÃO B: Manter Separado (2 Entidades) ✅ RECOMENDADO

#### ✅ VANTAGENS:
1. **Separação clara de responsabilidades**:
   - Requisição = "O QUE preciso"
   - Pedido = "DE QUEM vou comprar"
2. **Flexibilidade total**:
   - 1 requisição → N pedidos ✅
   - N requisições → 1 pedido ✅ (consolidação)
   - 1 requisição parcialmente atendida ✅
3. **Granularidade**: Status independente por pedido
4. **Auditoria**: Histórico separado e claro
5. **Campos específicos**: Cada entidade tem o que precisa
6. **Escalabilidade**: Fácil adicionar mais entidades (NF de compra, etc)

#### ❌ DESVANTAGENS:
1. **Mais JOINs**: Queries precisam cruzar tabelas
2. **Mais complexo**: Precisa gerenciar relacionamento
3. **Risco de inconsistência**: Se não houver FK forte

#### ✅ IMPLEMENTAÇÃO RECOMENDADA:

```python
# ✅ Tabela Intermediária para Relacionamento N:N
class RequisicaoPedidoVinculo(db.Model):
    """
    Tabela de vínculo entre Requisições e Pedidos
    Permite relação N:N flexível
    """
    __tablename__ = 'requisicao_pedido_vinculo'

    id = db.Column(db.Integer, primary_key=True)

    # FKs
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao_compras.id'), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido_compras.id'), nullable=False)

    # Controle de Atendimento
    qtd_atendida = db.Column(db.Numeric(15, 3))  # Quanto deste pedido atende a requisição
    percentual_atendimento = db.Column(db.Numeric(5, 2))  # % atendido

    # Datas
    vinculado_em = db.Column(db.DateTime, default=datetime.utcnow)
    vinculado_por = db.Column(db.String(100))

    # Relacionamentos
    requisicao = db.relationship('RequisicaoCompras', backref='vinculos_pedidos')
    pedido = db.relationship('PedidoCompras', backref='vinculos_requisicoes')

    __table_args__ = (
        db.UniqueConstraint('requisicao_id', 'pedido_id'),
        db.Index('idx_vinculo_requisicao', 'requisicao_id'),
        db.Index('idx_vinculo_pedido', 'pedido_id'),
    )
```

---

## 🎯 RECOMENDAÇÃO FINAL: OPÇÃO B + TABELA DE VÍNCULO

### Arquitetura Recomendada:

```
┌─────────────────────┐
│ RequisicaoCompras   │  (O QUE preciso)
│ - num_requisicao    │
│ - cod_produto       │
│ - qtd_requisitada   │
│ - status            │
└──────────┬──────────┘
           │
           │ N:N via RequisicaoPedidoVinculo
           │
           ↓
┌─────────────────────┐
│ PedidoCompras       │  (DE QUEM compro)
│ - num_pedido        │
│ - cnpj_fornecedor   │
│ - cod_produto       │
│ - qtd_pedido        │
│ - preco             │
│ - impostos          │
└─────────────────────┘
```

### Benefícios da Tabela de Vínculo:
1. ✅ Permite qualquer tipo de relacionamento
2. ✅ Rastreabilidade total
3. ✅ Controle de atendimento (qtd_atendida)
4. ✅ Auditoria de quando foi vinculado
5. ✅ Facilita queries do tipo:
   - "Quais pedidos atendem requisição X?"
   - "Qual o status de atendimento da requisição Y?"
   - "Requisição Z está 60% atendida"

---

## 📊 EXEMPLOS DE QUERIES ÚTEIS

### Query 1: Ver pedidos de uma requisição
```python
requisicao = RequisicaoCompras.query.get(id)
pedidos = db.session.query(PedidoCompras)\
    .join(RequisicaoPedidoVinculo)\
    .filter(RequisicaoPedidoVinculo.requisicao_id == requisicao.id)\
    .all()
```

### Query 2: % de atendimento de uma requisição
```python
atendimento = db.session.query(
    func.sum(RequisicaoPedidoVinculo.qtd_atendida)
).filter(
    RequisicaoPedidoVinculo.requisicao_id == requisicao.id
).scalar()

percentual = (atendimento / requisicao.qtd_produto_requisicao) * 100
```

### Query 3: Requisições pendentes (não totalmente atendidas)
```python
requisicoes_pendentes = db.session.query(RequisicaoCompras)\
    .outerjoin(RequisicaoPedidoVinculo)\
    .group_by(RequisicaoCompras.id)\
    .having(
        func.coalesce(func.sum(RequisicaoPedidoVinculo.qtd_atendida), 0)
        < RequisicaoCompras.qtd_produto_requisicao
    )\
    .all()
```

---

## 🚀 ROADMAP DE IMPLEMENTAÇÃO

### Fase 1: Criar Tabela de Vínculo ✅
- Criar modelo `RequisicaoPedidoVinculo`
- Gerar migration
- Testar relacionamentos

### Fase 2: Importar Pedidos do Odoo
- Criar service de importação (similar a requisições)
- Aplicar batch loading (evitar Query N+1)
- Vincular automaticamente com requisições

### Fase 3: Interface de Visualização
- Tela de requisições mostra pedidos vinculados
- Tela de pedidos mostra requisições atendidas
- Dashboard de atendimento (%)

### Fase 4: Regras de Negócio
- Validar: Pedido só pode atender requisição do mesmo produto
- Alertar: Requisição crítica sem pedido vinculado
- Calcular: Lead time real vs previsto

---

## 📝 CONCLUSÃO

✅ **MANTER SEPARADO (OPÇÃO B) + TABELA DE VÍNCULO**

**Motivos:**
1. Maior clareza semântica
2. Flexibilidade total de relacionamentos
3. Facilita evolução futura (NF de compra, recebimento, etc)
4. Queries complexas, mas com valor de negócio
5. Escalável para cenários avançados

**NÃO enriquecer requisições** porque:
- Perde semântica de negócio
- Redundância de dados
- Complexidade desnecessária
- Difícil manter integridade

---

**Status**: ✅ ANÁLISE CONCLUÍDA
**Decisão**: OPÇÃO B + Tabela de Vínculo
**Próximo passo**: Criar modelo `RequisicaoPedidoVinculo`
