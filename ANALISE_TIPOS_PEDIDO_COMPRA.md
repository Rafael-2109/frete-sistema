# Análise: Tipos de Pedido de Compra (l10n_br_tipo_pedido)

**Data:** 05/11/2025
**Fonte:** Campo `l10n_br_tipo_pedido` do Odoo Brasil
**Objetivo:** Filtrar apenas tipos relevantes para materiais armazenáveis

---

## 🎯 CRITÉRIOS DE FILTRO

### ✅ INCLUIR:
- Materiais armazenáveis (`detailed_type='product'`)
- Operações que **aumentam estoque físico**
- Compras e devoluções reais

### ❌ EXCLUIR:
- Transferências entre filiais
- Remessas (não aumentam estoque próprio)
- Serviços
- Operações temporárias (comodato, demonstração, etc.)
- Ativos imobilizados

---

## 📊 ANÁLISE COMPLETA DOS 38 TIPOS

### 🟢 TIPOS RELEVANTES (Incluir) - 9 tipos

#### 1. **Compras Normais**
| Código | Nome | Justificativa |
|--------|------|--------------|
| `compra` | **Entrada: Compra** | ✅ Compra padrão - PRINCIPAL |
| `importacao` | **Entrada: Importação** | ✅ Compra internacional |
| `comp-importacao` | **Entrada: Complementar de Importação** | ✅ Complemento de importação |

#### 2. **Devoluções (aumentam estoque)**
| Código | Nome | Justificativa |
|--------|------|--------------|
| `devolucao` | **Entrada: Devolução Emissão Própria** | ✅ Cliente devolveu mercadoria |
| `devolucao_compra` | **Entrada: Devolução de Venda** | ✅ Devolução de venda realizada |

#### 3. **Retornos de Industrialização**
| Código | Nome | Justificativa |
|--------|------|--------------|
| `industrializacao` | **Entrada: Retorno de Industrialização** | ✅ Material volta após processamento |
| `rem-industrializacao` | **Entrada: Remessa p/ Industrialização** | ⚠️ **ANALISAR:** Pode ser só remessa |

#### 4. **Bonificações e Amostras**
| Código | Nome | Justificativa |
|--------|------|--------------|
| `ent-bonificacao` | **Entrada: Bonificação** | ✅ Material gratuito que entra no estoque |
| `ent-amostra` | **Entrada: Amostra Grátis** | ⚠️ **ANALISAR:** Depende se vira estoque |

---

### 🔴 TIPOS NÃO RELEVANTES (Excluir) - 29 tipos

#### **A) Transferências (excluídas explicitamente)**
| Código | Nome | Motivo |
|--------|------|--------|
| `transf-filial` | Entrada: Transferencia entre Filiais | ❌ Excluída por requisito |

#### **B) Remessas (não aumentam estoque próprio)**
| Código | Nome | Motivo |
|--------|------|--------|
| `rem-industrializacao` | Entrada: Remessa p/ Industrialização | ❌ Material sai (remessa) |
| `rem-conta-ordem` | Entrada: Remessa por Conta e Ordem | ❌ Material de terceiros |

#### **C) Operações Temporárias (não ficam no estoque)**
| Código | Nome | Motivo |
|--------|------|--------|
| `ent-comodato` | Entrada: Comodato | ❌ Empréstimo temporário |
| `comodato` | Entrada: Retorno de Comodato | ❌ Devolução de empréstimo |
| `ent-demonstracao` | Entrada: Demonstração | ❌ Material para demo |
| `demonstracao` | Entrada: Retorno de Demonstração | ❌ Volta da demo |
| `ent-mostruario` | Entrada: Mostruário | ❌ Material de exposição |
| `mostruario` | Entrada: Retorno de Mostruário | ❌ Volta da exposição |
| `consignacao` | Entrada: Retorno de Consignação | ❌ Consignação não é compra |
| `deposito` | Entrada: Retorno de Depósito | ❌ Depósito temporário |
| `feira` | Entrada: Retorno de Feira | ❌ Material de feira |
| `locacao` | Entrada: Locação | ❌ Aluguel |
| `ret-locacao` | Entrada: Retorno de Locação | ❌ Volta de aluguel |

#### **D) Serviços (não são armazenáveis)**
| Código | Nome | Motivo |
|--------|------|--------|
| `servico` | Entrada: Serviço | ❌ Não é material |
| `serv-industrializacao` | Entrada: Serviço de Industrialização | ❌ Serviço |
| `ent-conserto` | Entrada: Conserto | ❌ Serviço |
| `conserto` | Entrada: Retorno de Conserto | ❌ Serviço |

#### **E) Operações Especiais (não compras regulares)**
| Código | Nome | Motivo |
|--------|------|--------|
| `compra-venda-ordem` | Entrada: Compra Venda à Ordem | ❌ Operação triangular |
| `compra-rec-venda-ordem` | Entrada: Recebimento de Compra Venda à Ordem | ❌ Operação triangular |
| `compra-ent-futura` | Entrada: Compra p/ Entrega Futura | ⚠️ **ANALISAR:** Não entra ainda |
| `compra-rec-ent-futura` | Entrada: Recebimento de Compra p/ Entrega Futura | ✅ **POSSÍVEL:** Quando efetivamente entra |
| `credito-imposto` | Entrada: Crédito de Imposto | ❌ Operação fiscal apenas |
| `importacao-transporte` | Entrada: Transporte de Importação | ❌ Serviço de transporte |

#### **F) Vasilhames e Embalagens Retornáveis**
| Código | Nome | Motivo |
|--------|------|--------|
| `ent-vasilhame` | Entrada: Vasilhame | ⚠️ **ANALISAR:** Se gerencia estoque |
| `vasilhame` | Entrada: Retorno de Vasilhame | ⚠️ **ANALISAR:** Depende |
| `troca` | Entrada: Retorno de Troca | ⚠️ **ANALISAR:** Pode ser relevante |

#### **G) Ativos Imobilizados**
| Código | Nome | Motivo |
|--------|------|--------|
| `ativo-fora` | Entrada: Retorno de bem do ativo imobilizado | ❌ Não é estoque |

#### **H) Outros**
| Código | Nome | Motivo |
|--------|------|--------|
| `outro` | Entrada: Outros | ⚠️ **ANALISAR:** Genérico |
| `retorno` | Entrada: Outros Retorno | ⚠️ **ANALISAR:** Genérico |

---

## 🎯 RECOMENDAÇÃO FINAL

### ✅ TIPOS A INCLUIR (Lista Definitiva)

#### **Núcleo Principal (Obrigatórios) - 8 TIPOS:**
```python
TIPOS_PEDIDO_RELEVANTES = [
    'compra',                   # Compra normal - PRINCIPAL
    'importacao',               # Importação
    'comp-importacao',          # Complementar de importação
    'devolucao',                # Devolução de cliente
    'devolucao_compra',         # Devolução de venda
    'industrializacao',         # Retorno de industrialização (produto acabado volta)
    'serv-industrializacao',    # ✅ Serviço de industrialização (PRODUÇÃO TERCEIRIZADA)
    'ent-bonificacao',          # Bonificação (brinde)
]
```

**⚠️ IMPORTANTE - Serviço de Industrialização:**

`serv-industrializacao` **DEVE SER INCLUÍDO** pois:
- Funciona como **"produção terceirizada"**
- Envia matéria-prima para terceiro processar
- Consome estrutura (BOM) da matéria-prima
- Retorna produto acabado
- Sistema deve:
  - ✅ Projetar consumo de componentes (como produção interna)
  - ✅ Registrar entrada do produto acabado
  - ✅ Rastrear custo de industrialização

#### **Opcional (Analisar com time):**
```python
TIPOS_PEDIDO_OPCIONAIS = [
    'compra-rec-ent-futura',  # Recebimento de compra futura (entra no estoque)
    'ent-amostra',            # Amostra grátis (se virar estoque)
    'troca',                  # Retorno de troca (se for material novo)
    'ent-vasilhame',          # Vasilhame (se gerenciar estoque)
    'outro',                  # Genérico (cuidado!)
]
```

---

## 📊 ESTATÍSTICAS

```
Total de tipos: 38

✅ Relevantes (núcleo):     8 tipos  (21%) ← ATUALIZADO
⚠️  Opcionais (analisar):   5 tipos  (13%)
❌ Excluídos:              25 tipos  (66%) ← ATUALIZADO
```

---

## 💡 IMPLEMENTAÇÃO SUGERIDA

### 1. Adicionar Campo ao Modelo

```python
# app/manufatura/models.py - PedidoCompras

class PedidoCompras(db.Model):
    # ... campos existentes ...

    # ✅ NOVO: Tipo de pedido (para filtros e relatórios)
    tipo_pedido = db.Column(db.String(50), nullable=True, index=True)
```

### 2. Importar do Odoo

```python
# app/odoo/services/pedido_compras_service.py

TIPOS_RELEVANTES = [
    'compra', 'importacao', 'comp-importacao',
    'devolucao', 'devolucao_compra',
    'industrializacao', 'serv-industrializacao',  # ✅ ADICIONADO
    'ent-bonificacao'
]

def _processar_linha_otimizada(self, pedido_odoo, linha_odoo, ...):
    # Verificar tipo de pedido
    tipo_pedido = pedido_odoo.get('l10n_br_tipo_pedido')

    # ✅ Filtrar apenas tipos relevantes
    if tipo_pedido and tipo_pedido not in TIPOS_RELEVANTES:
        self.logger.info(
            f"   Pedido {pedido_odoo['name']} tipo '{tipo_pedido}' "
            f"não é relevante para estoque - IGNORADO"
        )
        return {'processado': False, 'nova': False, 'atualizada': False}

    # Continuar processamento...
    novo_pedido = PedidoCompras(
        # ... campos existentes ...
        tipo_pedido=tipo_pedido,  # ✅ Armazenar tipo
    )
```

### 3. Filtros na Interface

```python
# app/manufatura/routes/pedidos_compras_routes.py

@pedidos_compras_bp.route('/api/listar')
def api_listar_pedidos():
    # ... filtros existentes ...

    # ✅ NOVO: Filtro por tipo de pedido
    tipo_pedido = request.args.get('tipo_pedido')
    if tipo_pedido:
        query = query.filter(PedidoCompras.tipo_pedido == tipo_pedido)
```

---

## 🔍 ANÁLISE DE CASOS ESPECIAIS

### 1. **Compra para Entrega Futura**
- `compra-ent-futura`: Pedido feito, mas não entregue → **NÃO entra no estoque ainda**
- `compra-rec-ent-futura`: Recebimento efetivo → **ENTRA no estoque**
- **Recomendação:** Incluir apenas `compra-rec-ent-futura`

### 2. **Industrialização**
- `rem-industrializacao`: Material SAI para ser processado → **Não é entrada**
- `industrializacao`: Material VOLTA processado → **É entrada**
- **Recomendação:** Incluir apenas `industrializacao`

### 3. **Vasilhames**
- Se sua empresa gerencia estoque de vasilhames → Incluir
- Se vasilhames são apenas comodato → Excluir
- **Recomendação:** Consultar time de negócio

### 4. **Amostras Grátis**
- Se amostras viram estoque vendável → Incluir
- Se amostras são só para demonstração → Excluir
- **Recomendação:** Consultar time de negócio

---

## 📋 PRÓXIMOS PASSOS

1. ✅ **Decidir lista final** com time de negócio
2. ✅ **Adicionar campo** `tipo_pedido` ao modelo
3. ✅ **Criar migração** do banco
4. ✅ **Atualizar serviço** de importação
5. ✅ **Adicionar filtros** na interface
6. ✅ **Documentar regras** de negócio

---

## 📚 REFERÊNCIAS

- **Campo Odoo:** `purchase.order.l10n_br_tipo_pedido`
- **Localização Brasil:** Módulo `l10n_br_purchase`
- **Modelo Local:** [app/manufatura/models.py](app/manufatura/models.py)
- **Serviço:** [app/odoo/services/pedido_compras_service.py](app/odoo/services/pedido_compras_service.py)

---

**Autor:** Claude Code
**Data:** 05/11/2025
**Status:** ⏳ Aguardando validação do time de negócio
