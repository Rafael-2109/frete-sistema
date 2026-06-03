# Especificacao: Importador de Pedidos Tenda (Excel)

**Data**: 05/12/2024
**Status**: Especificado - Aguardando Implementacao
**Prioridade**: A definir

---

## 1. Visao Geral

Implementar a importacao de pedidos de compra do cliente Tenda que chegam em formato Excel (.xlsx).

### 1.1 Fluxo Esperado

```
Upload Excel → Leitura → Conversao De-Para → Validacao Precos → Revisao → Insercao Odoo
```

### 1.2 Regra de Agrupamento

Um unico arquivo Excel pode conter multiplas lojas. Deve ser criado **1 pedido no Odoo para cada combinacao unica de**:
- Loja (CNPJ)
- Nº Pedido (pedido_cliente)

---

## 2. Campos do Excel

| Coluna Excel | Campo Interno | Obrigatorio | Conversao Necessaria |
|--------------|---------------|-------------|----------------------|
| Nº Pedido | `pedido_cliente` | Sim | Nao |
| Loja | `cnpj_cliente` | Sim | **Sim** - Loja → CNPJ |
| Material | `nosso_codigo` | Sim | **Sim** - Codigo Tenda → Nosso Codigo |
| Qtd.Pedido | `quantidade` | Sim | Nao |
| Preco Tabela | `preco` | Sim | Nao |

### 2.1 Observacoes sobre os Campos

- **Loja**: Nome da filial do Tenda (texto variavel, pode ter numero ou so letras)
  - Exemplos: "CT03 - AMOREIRAS", "LOJA CENTRO", "FILIAL 045"

- **Material**: Codigo interno do Tenda (NAO e EAN/codigo de barras)
  - Requer tabela De-Para especifica

---

## 3. Campos Obrigatorios para Odoo

Referencia: `app/pedidos/integracao_odoo/service.py:155-280`

| Campo Odoo | Fonte | Status |
|------------|-------|--------|
| `cnpj_cliente` | Loja (apos conversao) | Requer De-Para |
| `nosso_codigo` | Material (apos conversao) | Requer De-Para |
| `quantidade` | Qtd.Pedido | OK |
| `preco` | Preco Tabela | OK |
| `numero_pedido_cliente` | Nº Pedido | OK |

---

## 4. Tabelas a Criar/Modificar

### 4.1 CRIAR: ProdutoDeParaTenda

Substitui a tabela `ProdutoDeParaEAN` (que deve ser deprecada).

```python
class ProdutoDeParaTenda(db.Model):
    """
    Tabela DE-PARA para mapear codigos de produtos
    Codigo Tenda <-> Nosso Codigo (Nacom)
    """
    __tablename__ = 'portal_tenda_produto_depara'

    id = db.Column(db.Integer, primary_key=True)

    # Nosso codigo e descricao
    codigo_nosso = db.Column(db.String(50), nullable=False, index=True)
    descricao_nosso = db.Column(db.String(255))

    # Codigo e descricao do Tenda
    codigo_tenda = db.Column(db.String(50), nullable=False, index=True)
    descricao_tenda = db.Column(db.String(255))

    # Fator de conversao (se houver diferenca de unidade de medida)
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0)
    observacoes = db.Column(db.Text)

    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100))

    # Indice unico para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('codigo_nosso', 'codigo_tenda',
                          name='unique_depara_tenda'),
    )

    @classmethod
    def obter_nosso_codigo(cls, codigo_tenda):
        """Obtem nosso codigo a partir do codigo Tenda"""
        depara = cls.query.filter_by(
            codigo_tenda=codigo_tenda,
            ativo=True
        ).first()
        return depara.codigo_nosso if depara else None
```

### 4.2 CRIAR: LojaTendaCNPJ

Mapeamento de nome da loja para CNPJ do cliente.

```python
class LojaTendaCNPJ(db.Model):
    """
    Tabela DE-PARA para mapear nome da Loja Tenda para CNPJ
    Nome Loja -> CNPJ Cliente

    NOTA: Tenda opera apenas em SP, portanto UF e sempre 'SP' (fixo no codigo)
    """
    __tablename__ = 'portal_tenda_loja_cnpj'

    id = db.Column(db.Integer, primary_key=True)

    # Nome da loja (como vem no Excel)
    loja_nome = db.Column(db.String(255), nullable=False, unique=True, index=True)

    # CNPJ do cliente correspondente
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)

    # Dados adicionais (opcionais, apenas para referencia)
    razao_social = db.Column(db.String(255))

    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100))

    @classmethod
    def obter_cnpj(cls, loja_nome):
        """Obtem CNPJ a partir do nome da loja"""
        loja = cls.query.filter_by(
            loja_nome=loja_nome,
            ativo=True
        ).first()
        return loja.cnpj_cliente if loja else None

    @classmethod
    def obter_dados_completos(cls, loja_nome):
        """Obtem todos os dados da loja (UF sempre SP)"""
        loja = cls.query.filter_by(
            loja_nome=loja_nome,
            ativo=True
        ).first()
        if loja:
            return {
                'cnpj': loja.cnpj_cliente,
                'razao_social': loja.razao_social,
                'uf': 'SP'  # Fixo - Tenda opera apenas em SP
            }
        return None
```

### 4.3 DEPRECAR: ProdutoDeParaEAN

A tabela `portal_tenda_produto_depara_ean` deve ser marcada como obsoleta.

**Arquivo**: `app/portal/tenda/models.py`
**Acao**: Adicionar comentario de depreciacao e nao usar em novos desenvolvimentos.

---

## 5. Validacao de Precos

### 5.1 IMPORTANTE: Tenda Opera Apenas em SP

**DECISAO**: Tenda possui lojas apenas no estado de **Sao Paulo (SP)**.

Consequencias:
- **Preco unico** (nao ha variacao por regiao)
- **NAO precisa** de mapeamento UF → Regiao
- **NAO precisa** do campo `uf` na tabela `LojaTendaCNPJ`
- Simplifica a validacao de precos

### 5.2 Estrutura de Precos para Tenda

Na tabela `TabelaRede`, cadastrar com:
- `rede` = 'TENDA'
- `regiao` = 'SP' (ou 'UNICA' - definir padrao)
- `cod_produto` = codigo Nacom
- `preco` = preco negociado

**NAO e necessario** cadastrar na tabela `RegiaoTabelaRede` para Tenda.

### 5.3 Como Usar para Tenda

```python
from app.pedidos.validacao import validar_precos_documento

resultado = validar_precos_documento(
    rede='TENDA',  # <-- Usar 'TENDA'
    uf='SP',       # <-- Fixo 'SP' (todas lojas sao SP)
    itens=[
        {'nosso_codigo': '35642', 'valor_unitario': 195.00, 'quantidade': 15},
        ...
    ]
)

if resultado.tem_divergencia:
    print(f"Divergencias: {resultado.itens_divergentes}")
```

### 5.4 Pre-requisitos para Validacao

1. **Cadastrar Regioes** (OPCIONAL para Tenda):
   - Cadastrar apenas 1 registro: `rede='TENDA'`, `uf='SP'`, `regiao='SP'`

2. **Cadastrar Precos**: Tabela `tabela_rede_precos` com `rede='TENDA'`
   - `regiao` = 'SP' para todos os produtos

---

## 6. ~~Questao Pendente: UF para Validacao~~ RESOLVIDA

### Decisao Final

**Tenda opera APENAS em Sao Paulo (SP)**, portanto:

- ✅ UF e sempre 'SP' (fixo no codigo)
- ✅ Preco unico (sem variacao por regiao)
- ✅ Campo `uf` na tabela `LojaTendaCNPJ` e **opcional** (apenas para referencia)
- ✅ Nao precisa cadastrar mapeamento UF → Regiao

**Status**: RESOLVIDA - Nao ha necessidade de logica de regiao para Tenda.

---

## 7. Arquivos a Criar/Modificar

### 7.1 Novos Arquivos

| Arquivo | Descricao |
|---------|-----------|
| `app/pedidos/leitura/extratores/tenda.py` | Extrator de dados do Excel Tenda |
| `app/portal/tenda/models_pedido.py` | Modelos ProdutoDeParaTenda e LojaTendaCNPJ |
| `scripts/migrations/criar_tabelas_tenda_pedido.py` | Script de migracao |
| `scripts/migrations/criar_tabelas_tenda_pedido.sql` | SQL para Render |

### 7.2 Arquivos a Modificar

| Arquivo | Modificacao |
|---------|-------------|
| `app/pedidos/leitura/identificador.py` | Adicionar identificacao de Excel Tenda |
| `app/pedidos/leitura/processor.py` | Integrar extrator Tenda |
| `app/pedidos/leitura/routes.py` | Suportar upload de Excel |
| `app/portal/tenda/models.py` | Deprecar ProdutoDeParaEAN |
| `app/__init__.py` | Registrar novos blueprints se necessario |

---

## 8. Interface de Usuario

### 8.1 Tela de Upload

Adicionar opcao "Tenda - Pedido de Compra (Excel)" no seletor de formato.

### 8.2 Telas de Cadastro De-Para

Criar telas CRUD para:
- **Produtos**: Codigo Tenda ↔ Nosso Codigo
- **Lojas**: Nome Loja → CNPJ + UF

### 8.3 Fluxo de Revisao

Similar ao Atacadao:
1. Upload do arquivo
2. Exibicao dos dados extraidos agrupados por Loja/Pedido
3. Alerta de itens sem De-Para
4. Alerta de divergencia de precos
5. Botao de inserir no Odoo (individual ou todos)

---

## 9. Estimativa de Esforco

| Etapa | Descricao | Estimativa |
|-------|-----------|------------|
| 1 | Criar modelos e migrations | 2h |
| 2 | Criar extrator de Excel | 3h |
| 3 | Integrar no processor/identificador | 2h |
| 4 | Criar telas CRUD De-Para | 4h |
| 5 | Adaptar tela de upload | 2h |
| 6 | Testes e ajustes | 3h |
| **Total** | | **~16h** |

---

## 10. Dependencias

- [ ] Definir se usara validacao por regiao (requer UF)
- [ ] Obter planilha modelo do Tenda para validar colunas
- [ ] Cadastrar mapeamento Loja → CNPJ
- [ ] Cadastrar mapeamento Codigo Tenda → Nosso Codigo
- [ ] Cadastrar precos na TabelaRede com rede='TENDA'
- [ ] Cadastrar regioes na RegiaoTabelaRede com rede='TENDA'

---

## 11. Referencias

- Importador Atacadao: `app/pedidos/leitura/`
- De-Para Atacadao: `app/portal/atacadao/models.py`
- De-Para Tenda (atual): `app/portal/tenda/models.py`
- Validacao Precos: `app/pedidos/validacao/`
- Service Odoo: `app/pedidos/integracao_odoo/service.py`
