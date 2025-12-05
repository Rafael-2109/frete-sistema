# Plano de Implementação: Importador de Pedidos de Redes de Atacarejo

**Data**: 04/12/2025
**Status**: ✅ Em Implementação
**Versão**: 2.0

---

## 1. Resumo do Projeto

Sistema para importar PDFs de Propostas/Pedidos de redes de atacarejo (Tenda, Atacadão, Assaí), identificar automaticamente o tipo e rede, extrair dados, validar preços e inserir pedidos no Odoo.

---

## 2. Decisões Confirmadas

| Questão | Decisão |
|---------|---------|
| **Assaí De-Para** | Usa mesma tabela que Sendas (`ProdutoDeParaSendas`) |
| **Estrutura de Regiões** | MACRO (SUDESTE, NORDESTE, etc.) - UF N:1 Região |
| **População de Tabelas** | CRUD manual + interface |
| **Modal S/ Cadastro** | Usuário cadastra na hora, **não permite** inserir sem De-Para |
| **Armazenamento PDF** | Amazon S3 (padrão existente) |
| **Aprovação Divergência** | Qualquer usuário, por pedido completo, **com justificativa** |

---

## 3. Arquitetura

### 3.1 Estrutura de Módulos

```
app/pedidos/
├── leitura/
│   ├── __init__.py
│   ├── base.py                    # ✅ Existe - Classe base PDFExtractor
│   ├── atacadao.py                # ✅ Existe - Extrator Atacadão Proposta
│   ├── atacadao_pedido.py         # 🆕 Novo - Extrator Atacadão Pedido
│   ├── tenda.py                   # 🔜 Futuro - Extrator Tenda
│   ├── assai.py                   # 🔜 Futuro - Extrator Assaí (usa Sendas)
│   ├── identificador.py           # 🆕 Novo - Identifica Rede + Tipo
│   ├── processor.py               # ✅ Existe - Expandir
│   └── routes.py                  # ✅ Existe - Expandir
├── validacao/
│   ├── __init__.py                # 🆕 Novo
│   ├── validador_precos.py        # 🆕 Novo
│   └── models.py                  # 🆕 Novo - TabelaRede, RegiaoTabelaRede
├── integracao_odoo/
│   ├── __init__.py                # 🆕 Novo
│   ├── service.py                 # 🆕 Novo
│   └── models.py                  # 🆕 Novo - RegistroPedidoOdoo
└── routes.py                      # ✅ Existe
```

### 3.2 Fluxo do Sistema

```
┌─────────────────┐
│  Upload PDF     │  → Armazena no S3
└───────┬─────────┘
        ▼
┌─────────────────┐
│  Identificador  │  → Detecta: Rede + Tipo (Proposta/Pedido)
└───────┬─────────┘
        ▼
┌─────────────────┐
│   Extrator      │  → Usa extrator específico por Rede+Tipo
│   Específico    │
└───────┬─────────┘
        ▼
┌─────────────────┐
│   Conversão     │  → Tabela De-Para por Rede:
│   De-Para       │     - Atacadão: ProdutoDeParaAtacadao
└───────┬─────────┘     - Tenda: ProdutoDeParaEAN
        │               - Assaí: ProdutoDeParaSendas
        ▼
┌─────────────────┐
│  S/ Cadastro?   │  → Modal para cadastrar De-Para na hora
│  (Obrigatório)  │     NÃO permite inserir sem De-Para
└───────┬─────────┘
        ▼
┌─────────────────┐
│   Validação     │  → Compara: Rede + Região (via UF) + Produto
│   de Preços     │     vs TabelaRede
└───────┬─────────┘
        ▼
┌───────────────────────────────────────────────────┐
│              Tela de Revisão                      │
│  ┌─────────────────┐  ┌───────────────────────┐   │
│  │ Preços OK ✅    │  │ Divergentes ⚠️        │   │
│  │ [Inserir Odoo]  │  │ [Aprovar c/ Justif.]  │   │
│  └─────────────────┘  └───────────────────────┘   │
│                                                   │
│  Aprovação: Por pedido completo + Justificativa   │
└───────────────────────────────────────────────────┘
        ▼
┌─────────────────┐
│ Inserção Odoo   │  → sale.order via XML-RPC
└───────┬─────────┘
        ▼
┌─────────────────┐
│ Registro Log    │  → RegistroPedidoOdoo (auditoria)
└─────────────────┘
```

---

## 4. Identificação de Documentos (Atacadão)

### 4.1 Proposta de Compra
- **Header**: "Proposta de Compra"
- **Código**: `CCPMERM01`
- **Formato**: PDF tabular/gráfico
- **Identificador**: `Proposta: XXXXXX`
- **Código produto**: `35642-114` (código-sequencial)

### 4.2 Pedido de Compra
- **Header**: "PEDIDO DE COMPRA"
- **Código**: `ATACADAO S.A.`
- **Formato**: PDF texto matricial
- **Identificador**: `Pedido EDI: N XXXXXXXXX`
- **Código produto**: `35642/114 CXA 0001X0006X2KG` (código/seq CXA barcode)

---

## 5. Modelos de Dados

### 5.1 TabelaRede (Preços por Rede)

```python
class TabelaRede(db.Model):
    """Tabela de preços por Rede/Região/Produto"""
    __tablename__ = 'tabela_rede_precos'

    id = db.Column(db.Integer, primary_key=True)
    rede = db.Column(db.String(50), nullable=False, index=True)  # 'ATACADAO', 'TENDA', 'ASSAI'
    regiao = db.Column(db.String(50), nullable=False, index=True)  # 'SUDESTE', 'SUL', etc.
    cod_produto = db.Column(db.String(50), nullable=False, index=True)  # Código Nacom
    preco = db.Column(db.Numeric(15, 2), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    vigencia_inicio = db.Column(db.Date, nullable=True)
    vigencia_fim = db.Column(db.Date, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('rede', 'regiao', 'cod_produto', name='uq_tabela_rede_produto'),
        db.Index('idx_tabela_rede_regiao', 'rede', 'regiao'),
    )
```

### 5.2 RegiaoTabelaRede (Mapeamento UF → Região)

```python
class RegiaoTabelaRede(db.Model):
    """Mapeia UF para Região por Rede (N UFs → 1 Região)"""
    __tablename__ = 'regiao_tabela_rede'

    id = db.Column(db.Integer, primary_key=True)
    rede = db.Column(db.String(50), nullable=False, index=True)
    uf = db.Column(db.String(2), nullable=False, index=True)
    regiao = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('rede', 'uf', name='uq_regiao_rede_uf'),
    )
```

### 5.3 RegistroPedidoOdoo (Log de Inserções)

```python
class RegistroPedidoOdoo(db.Model):
    """Registro de pedidos inseridos no Odoo"""
    __tablename__ = 'registro_pedido_odoo'

    id = db.Column(db.Integer, primary_key=True)

    # Origem do documento
    rede = db.Column(db.String(50), nullable=False, index=True)
    tipo_documento = db.Column(db.String(50), nullable=False)  # 'PROPOSTA', 'PEDIDO'
    numero_documento = db.Column(db.String(100), nullable=True)
    arquivo_pdf_s3 = db.Column(db.String(500), nullable=True)  # URL S3

    # Cliente
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=True)
    uf_cliente = db.Column(db.String(2), nullable=True)

    # Resultado Odoo
    odoo_order_id = db.Column(db.Integer, nullable=True)
    odoo_order_name = db.Column(db.String(50), nullable=True)
    status_odoo = db.Column(db.String(50), nullable=False)  # 'SUCESSO', 'ERRO', 'PENDENTE'
    mensagem_erro = db.Column(db.Text, nullable=True)

    # Dados do documento (JSON)
    dados_documento = db.Column(db.JSON, nullable=True)

    # Validação de preços
    divergente = db.Column(db.Boolean, default=False, nullable=False)
    divergencias = db.Column(db.JSON, nullable=True)
    justificativa_aprovacao = db.Column(db.Text, nullable=True)  # Se divergente

    # Auditoria
    inserido_por = db.Column(db.String(100), nullable=False)
    aprovado_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_registro_rede_cnpj', 'rede', 'cnpj_cliente'),
        db.Index('idx_registro_odoo_order', 'odoo_order_id'),
    )
```

---

## 6. Código Existente a Reutilizar

| Componente | Arquivo | Status |
|------------|---------|--------|
| Extrator Atacadão Proposta | `app/pedidos/leitura/atacadao.py` | ✅ Pronto |
| De-Para Atacadão | `app/portal/atacadao/models.py` | ✅ Pronto |
| De-Para Tenda (EAN) | `app/portal/tenda/models.py` | ✅ Pronto |
| De-Para Sendas (Assaí) | `app/portal/sendas/models.py` | ✅ Pronto |
| CadastroPalletizacao | `app/producao/models.py` | ✅ Pronto |
| Upload S3 | `app/utils/s3_upload.py` | ✅ Pronto |
| Integração Odoo | `docs/ESTUDO_CRIAR_PEDIDO_VENDA_ODOO.md` | ✅ Documentado |

---

## 7. Cronograma de Implementação

| Fase | Descrição | Status |
|------|-----------|--------|
| 1 | Modelos de dados + Scripts SQL | 🔄 Em andamento |
| 2 | Identificador de Rede/Tipo | ⏳ Pendente |
| 3 | Extrator Atacadão Pedido | ⏳ Pendente |
| 4 | Validador de Preços | ⏳ Pendente |
| 5 | Service Integração Odoo | ⏳ Pendente |
| 6 | Interface de Revisão | ⏳ Pendente |
| 7 | Modal Cadastro De-Para | ⏳ Pendente |
| 8 | CRUD Tabelas de Preços | ⏳ Pendente |
| 9 | Testes e Ajustes | ⏳ Pendente |

---

*Documento atualizado em 04/12/2025*
