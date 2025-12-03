# Modelos Conhecidos do Odoo

Indice de modelos com campos mapeados e status de implementacao.

> **ROADMAP COMPLETO:** Para detalhes de campos, relacionamentos e plano de implementacao, consulte [ROADMAP_IMPLEMENTACAO.md](ROADMAP_IMPLEMENTACAO.md)

## Modelos Implementados

### DFE - Documentos Fiscais Eletronicos

| Modelo Odoo | Descricao | Status | Referencia |
|-------------|-----------|--------|------------|
| `l10n_br_ciel_it_account.dfe` | Documento principal | ✅ Implementado | [DFE.md](DFE.md) |
| `l10n_br_ciel_it_account.dfe.line` | Linhas/produtos | ✅ Implementado | [DFE.md](DFE.md#linhas) |
| `l10n_br_ciel_it_account.dfe.pagamento` | Pagamentos/Duplicatas | 🟡 Mapeado | [DFE.md](DFE.md#pagamentos) |

**Subtipos DFE:**
- Devolucao (finnfe=4)
- CTe (is_cte=True)
- Normal (finnfe=1)
- Complementar (finnfe=2)
- Ajuste (finnfe=3)

**Funcionalidades:**
- [x] Consulta por cliente (CNPJ/nome)
- [x] Consulta por produto
- [x] Consulta por quantidade
- [x] Consulta por periodo
- [x] Campos fiscais (--fiscais)
- [ ] Filtro por NCM
- [ ] Filtro por CFOP
- [ ] Filtro por valor de imposto

---

## Modelos Mapeados (Aguardando Implementacao)

### Financeiro

| Modelo Odoo | Descricao | Status | Referencia |
|-------------|-----------|--------|------------|
| `account.move` | Faturas | 📋 Mapeado | [ROADMAP](ROADMAP_IMPLEMENTACAO.md#21-modelo-accountmove) |
| `account.move.line` | Parcelas a pagar/receber | 📋 Mapeado | [ROADMAP](ROADMAP_IMPLEMENTACAO.md#22-modelo-accountmoveline) |
| `account.payment` | Pagamentos | ⬜ Pendente | - |

### Compras

| Modelo Odoo | Descricao | Status | Referencia |
|-------------|-----------|--------|------------|
| `purchase.order` | Pedidos de compra | 📋 Mapeado | [ROADMAP](ROADMAP_IMPLEMENTACAO.md#31-modelo-purchaseorder) |

### Cadastros

| Modelo Odoo | Descricao | Status | Referencia |
|-------------|-----------|--------|------------|
| `res.partner` | Clientes/Fornecedores | 📋 Mapeado | [ROADMAP](ROADMAP_IMPLEMENTACAO.md#41-modelo-respartner) |
| `product.product` | Produtos | ⬜ Pendente | - |
| `mrp.production` | Ordens de Producao | ⬜ Pendente | - |
| `stock.move` | Movimentacoes Estoque | ⬜ Pendente | - |

---

## Legenda de Status

| Status | Significado |
|--------|-------------|
| ✅ Implementado | Script funcional e documentacao completa |
| 🟡 Mapeado | Campos mapeados, falta script |
| 📋 Mapeado | Campos descobertos, aguarda implementacao |
| ⬜ Pendente | Nao mapeado ainda |

---

## Como Adicionar Novo Modelo

1. Usar `consultando_desconhecidas.py --modelo NOME --listar-campos`
2. Documentar campos relevantes em `reference/ROADMAP_IMPLEMENTACAO.md`
3. Criar arquivo especifico em `reference/` se necessario (ex: PARTNER.md)
4. Adicionar configuracao em `consultando_conhecidas.py` no dict `MODELOS_CONHECIDOS`
5. Atualizar este arquivo com novo status

---

## Proximos Passos (Roadmap)

| Fase | Modelo | Prioridade |
|------|--------|------------|
| 1 | DFE Avancado (NCM, CFOP, filtros tributos) | Alta |
| 2 | res.partner (fornecedores, transportadoras) | Alta |
| 3 | account.move.line (contas a pagar/receber) | Media |
| 4 | purchase.order (pedidos de compra) | Media |
| 5 | product.product (produtos) | Baixa |

> Detalhes completos em [ROADMAP_IMPLEMENTACAO.md](ROADMAP_IMPLEMENTACAO.md#roadmap-de-implementacao)
