# CLAUDE.md - Referência de Modelos e Campos

## ⚠️ ATENÇÃO: Use SEMPRE os nomes EXATOS dos campos listados aqui

## NÃO ALTERE FUNÇÕES QUE NÃO SÃO DO SEU CONTEXTO

## SE NÃO TIVER CERTEZA, NÃO ALTERE E PERGUNTE

Este arquivo contém os nomes corretos dos campos de todos os modelos para evitar erros como `data_expedicao_pedido` (❌ INCORRETO) em vez de `expedicao` (✅ CORRETO).

---

## PreSeparacaoItem - Sistema de Pré-separação

**Propósito**: Modelo para sistema de pré-separação que SOBREVIVE à reimportação do Odoo

**FUNCIONALIDADE CRÍTICA**: 
- Quando Odoo reimporta e SUBSTITUI a carteira_principal
- Este modelo preserva as decisões dos usuários e permite "recompor" as divisões

**FLUXO DE RECOMPOSIÇÃO**:
1. Usuário faz pré-separação (divisão parcial)
2. Sistema salva dados com chave de negócio estável  
3. Odoo reimporta → carteira_principal é substituída
4. Sistema detecta pré-separações não recompostas
5. Aplica novamente as divisões na nova carteira
6. Preserva dados editáveis (datas, protocolos, etc.)

```python
class PreSeparacaoItem(db.Model):
    __tablename__ = 'pre_separacao_item'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True) 
    cnpj_cliente = db.Column(db.String(20), index=True)
    
    # Dados originais preservados
    nome_produto = db.Column(db.String(255), nullable=True)
    qtd_original_carteira = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_selecionada_usuario = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_restante_calculada = db.Column(db.Numeric(15, 3), nullable=False)
    
    # Trabalho do usuário preservado
    data_expedicao_editada = db.Column(db.Date, nullable=False)  # ✅ OBRIGATÓRIO
    data_agendamento_editada = db.Column(db.Date)
    protocolo_editado = db.Column(db.String(50))
    observacoes_usuario = db.Column(db.Text)
    
    # Controle de recomposição
    recomposto = db.Column(db.Boolean, default=False, index=True)
    status = db.Column(db.String(20), default='CRIADO', index=True)
    tipo_envio = db.Column(db.String(10), default='total')
```

### ✅ Campos Críticos PreSeparacaoItem:
- `data_expedicao_editada` (✅ CORRETO)
- `data_agendamento_editada` (✅ CORRETO)  
- `protocolo_editado` (✅ CORRETO)
- `qtd_selecionada_usuario` (✅ CORRETO)
- `qtd_original_carteira` (✅ CORRETO)
- `qtd_restante_calculada` (✅ CORRETO)

---

## CarteiraPrincipal - Modelo Principal

**Propósito**: Modelo principal da carteira de pedidos - Contém todos os 91 campos + projeção D0-D28

```python
class CarteiraPrincipal(db.Model):
    __tablename__ = 'carteira_principal'

    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    
    # 📋 DADOS DO PEDIDO
    pedido_cliente = db.Column(db.String(100), nullable=True)
    data_pedido = db.Column(db.Date, nullable=True, index=True)
    status_pedido = db.Column(db.String(50), nullable=True, index=True)
    
    # 👥 DADOS DO CLIENTE
    cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)
    raz_social = db.Column(db.String(255), nullable=True)
    raz_social_red = db.Column(db.String(100), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    vendedor = db.Column(db.String(100), nullable=True, index=True)
    
    # 📦 DADOS DO PRODUTO
    nome_produto = db.Column(db.String(255), nullable=False)
    unid_medida_produto = db.Column(db.String(20), nullable=True)
    
    # 📊 QUANTIDADES E VALORES
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)
    
    # 📅 DADOS OPERACIONAIS (PRESERVADOS na atualização)
    expedicao = db.Column(db.Date, nullable=True)  # ✅ CAMPO CRÍTICO
    data_entrega = db.Column(db.Date, nullable=True)
    agendamento = db.Column(db.Date, nullable=True)  # ✅ CAMPO CRÍTICO
    protocolo = db.Column(db.String(50), nullable=True)  # ✅ CAMPO CRÍTICO
    
    # 🚛 DADOS DE CARGA/LOTE
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)
    qtd_saldo = db.Column(db.Numeric(15, 3), nullable=True)
    valor_saldo = db.Column(db.Numeric(15, 2), nullable=True)
```

### ✅ Campos Críticos CarteiraPrincipal:
- `expedicao` (✅ CORRETO - NÃO é `data_expedicao_pedido`)
- `agendamento` (✅ CORRETO)
- `protocolo` (✅ CORRETO)
- `num_pedido` (✅ CORRETO)
- `cod_produto` (✅ CORRETO)
- `nome_produto` (✅ CORRETO)
- `qtd_saldo_produto_pedido` (✅ CORRETO)
- `preco_produto_pedido` (✅ CORRETO)
- `cnpj_cpf` (✅ CORRETO)
- `raz_social_red` (✅ CORRETO)
- `separacao_lote_id` (✅ CORRETO)

---

## Embarque - Controle de Embarques

**Propósito**: Controle de embarques e carregamentos

```python
class Embarque(db.Model):
    __tablename__ = 'embarques'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=True)
    data_prevista_embarque = db.Column(db.Date, nullable=True)
    data_embarque = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='draft')  # 'draft', 'ativo', 'cancelado'
    tipo_carga = db.Column(db.String(20))  # 'FRACIONADA' ou 'DIRETA'
    valor_total = db.Column(db.Float)
    peso_total = db.Column(db.Float)
```

### ✅ Campos Críticos Embarque:
- `numero` (✅ CORRETO)
- `data_prevista_embarque` (✅ CORRETO)
- `data_embarque` (✅ CORRETO)
- `status` (✅ CORRETO)
- `tipo_carga` (✅ CORRETO)

---

## EmbarqueItem - Itens do Embarque

**Propósito**: Itens individuais de cada embarque

```python
class EmbarqueItem(db.Model):
    __tablename__ = 'embarque_itens'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=True)
    cliente = db.Column(db.String(120), nullable=False)
    pedido = db.Column(db.String(50), nullable=False)
    protocolo_agendamento = db.Column(db.String(50))
    nota_fiscal = db.Column(db.String(20))
    peso = db.Column(db.Float)
    valor = db.Column(db.Float)
    status = db.Column(db.String(20), nullable=False, default='ativo')
```

### ✅ Campos Críticos EmbarqueItem:
- `separacao_lote_id` (✅ CORRETO)
- `cnpj_cliente` (✅ CORRETO)
- `cliente` (✅ CORRETO)
- `pedido` (✅ CORRETO)
- `nota_fiscal` (✅ CORRETO)
- `status` (✅ CORRETO)

---

## Pedido - Controle de Pedidos

**Propósito**: Controle de pedidos e status

```python
class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)
    num_pedido = db.Column(db.String(30), index=True)
    cnpj_cpf = db.Column(db.String(20))
    raz_social_red = db.Column(db.String(255))
    expedicao = db.Column(db.Date)  # ✅ CAMPO CRÍTICO
    agendamento = db.Column(db.Date)  # ✅ CAMPO CRÍTICO
    protocolo = db.Column(db.String(50))  # ✅ CAMPO CRÍTICO
    data_embarque = db.Column(db.Date)
    nf = db.Column(db.String(20))
    status = db.Column(db.String(50), default='ABERTO')  # ✅ CAMPO CRÍTICO
```

### ✅ Campos Críticos Pedido:
- `separacao_lote_id` (✅ CORRETO)
- `num_pedido` (✅ CORRETO)
- `status` (✅ CORRETO)
- `expedicao` (✅ CORRETO - NÃO é `data_expedicao_pedido`)
- `agendamento` (✅ CORRETO)
- `protocolo` (✅ CORRETO)
- `nf` (✅ CORRETO)
- `data_embarque` (✅ CORRETO)

---

## Separacao - Separações Físicas

**Propósito**: Controle de separações físicas no CD

```python
class Separacao(db.Model):
    __tablename__ = 'separacao'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)
    num_pedido = db.Column(db.String(50), nullable=True)
    cnpj_cpf = db.Column(db.String(20), nullable=True)
    cod_produto = db.Column(db.String(50), nullable=True)
    nome_produto = db.Column(db.String(255), nullable=True)
    qtd_saldo = db.Column(db.Float, nullable=True)
    valor_saldo = db.Column(db.Float, nullable=True)
    expedicao = db.Column(db.Date, nullable=True)  # ✅ CAMPO CRÍTICO
    agendamento = db.Column(db.Date, nullable=True)  # ✅ CAMPO CRÍTICO
    protocolo = db.Column(db.String(50), nullable=True)  # ✅ CAMPO CRÍTICO
    tipo_envio = db.Column(db.String(10), default='total', nullable=True)
```

### ✅ Campos Críticos Separacao:
- `separacao_lote_id` (✅ CORRETO)
- `num_pedido` (✅ CORRETO) 
- `cod_produto` (✅ CORRETO)
- `nome_produto` (✅ CORRETO)
- `qtd_saldo` (✅ CORRETO)
- `expedicao` (✅ CORRETO - NÃO é `data_expedicao_pedido`)
- `agendamento` (✅ CORRETO)
- `protocolo` (✅ CORRETO)

**⚠️ IMPORTANTE**: Separacao NÃO tem campo `status` ou `embarque_status`. Para status, use JOIN com Pedido:
```sql
JOIN Pedido ON Separacao.separacao_lote_id = Pedido.separacao_lote_id
-- Então usar: Pedido.status
```

---

## MovimentacaoEstoque - Controle de Estoque

**Propósito**: Controle das movimentações de estoque

```python
class MovimentacaoEstoque(db.Model):
    __tablename__ = 'movimentacao_estoque'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    data_movimentacao = db.Column(db.Date, nullable=False, index=True)
    tipo_movimentacao = db.Column(db.String(50), nullable=False, index=True)
    qtd_movimentacao = db.Column(db.Numeric(15, 3), nullable=False)
    ativo = db.Column(db.Boolean, default=True, index=True)
```

---

## Outros Modelos (Resumido)

### UnificacaoCodigos:
- `codigo_origem`, `codigo_destino`, `ativo`

### ProgramacaoProducao:
- `data_programacao`, `cod_produto`, `qtd_programada`

### CadastroPalletizacao:
- `cod_produto`, `palletizacao`, `peso_bruto`

---

## ⚠️ ERROS COMUNS A EVITAR:

### ❌ NOMES INCORRETOS:
- `data_expedicao_pedido` → ✅ USE: `expedicao`
- `data_expedicao` → ✅ USE: `expedicao` 
- `embarque_status` (campo inexistente) → ✅ USE: `Pedido.status`

### ✅ JOINS CORRETOS:
```python
# Para obter status de Separacao:
.join(Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id)
# Então usar: Pedido.status

# Para obter nome real do produto:
.outerjoin(CarteiraPrincipal, and_(
    CarteiraPrincipal.num_pedido == Separacao.num_pedido,
    CarteiraPrincipal.cod_produto == Separacao.cod_produto
))
# Então usar: CarteiraPrincipal.nome_produto
```

### ✅ CAMPOS SEMPRE CORRETOS:
- `expedicao` (nunca `data_expedicao_pedido`)
- `agendamento` (nunca `data_agendamento_pedido`)
- `separacao_lote_id` (em Pedido, Separacao, EmbarqueItem)
- `qtd_saldo_produto_pedido` (em CarteiraPrincipal)
- `Pedido.status` (para status de separações via JOIN)