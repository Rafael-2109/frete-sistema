---
name: validacao-nf-po
description: |
  Executa e depura o processo de Validacao NF x PO (Fase 2 do Recebimento de Materiais).

  USAR QUANDO:
  - Depurar erro na validacao NF x PO: "erro ao validar DFE", "DFE nao encontrado"
  - Modificar logica de match: "alterar tolerancia", "mudar regra de preco"
  - Corrigir preview de POs candidatos: "modal nao abre", "erro no modal POs"
  - Entender fluxo de conversao De-Para: "como converte UM", "fator conversao"
  - Implementar nova regra de divergencia: "novo tipo de bloqueio"
  - Entender tabelas locais: "o que tem em MatchNfPoItem", "campos da validacao"

  NAO USAR QUANDO:
  - Rastrear documentos no Odoo -> usar rastreando-odoo
  - Descobrir campos de modelo Odoo desconhecido -> usar descobrindo-odoo-estrutura
  - Criar pagamentos ou reconciliar extratos -> usar executando-odoo-financeiro
  - Criar CTe ou despesas -> usar integracao-odoo
---

# Validacao NF x PO - Processo Completo

## Visao Geral

O processo de Validacao NF x PO compara itens de uma NF-e (DFE no Odoo) contra Pedidos de Compra (POs) do mesmo fornecedor, verificando preco, quantidade e data.

## Arquivo Principal

```
app/recebimento/services/validacao_nf_po_service.py
```

## Modelos/Tabelas Envolvidos

| Tabela Local | Modelo | Proposito |
|---|---|---|
| `validacao_nf_po_dfe` | ValidacaoNfPoDfe | Cabecalho da validacao (status, contadores) |
| `match_nf_po_item` | MatchNfPoItem | Resultado match item-a-item (NF vs PO) |
| `match_nf_po_alocacao` | MatchAlocacao | Alocacao split (1 item NF → N linhas PO) |
| `divergencia_nf_po` | DivergenciaNfPo | Divergencias para resolucao manual |
| `produto_fornecedor_depara` | ProdutoFornecedorDepara | Conversao codigo/UM fornecedor → interno |
| `pedido_compras` | PedidoCompras | POs locais (sincronizados do Odoo) |

| Modelo Odoo | Uso |
|---|---|
| `l10n_br_ciel_it_account.dfe` | NF-e eletronica (cabecalho) |
| `l10n_br_ciel_it_account.dfe.line` | Linhas/itens da NF-e |

## Fluxo Principal

```
┌─────────────────────────────────────────────────────────────┐
│                    validar_dfe(odoo_dfe_id)                  │
│                                                             │
│  1. Buscar DFE no Odoo (_buscar_dfe)                        │
│  2. Verificar se DFE ja tem PO vinculado                    │
│     └─ SIM → status='finalizado_odoo', retorna             │
│  3. Buscar linhas DFE no Odoo (_buscar_dfe_lines)           │
│  4. Converter itens com De-Para BATCH                       │
│     ├─ itens_convertidos (tem cod_produto_interno)          │
│     └─ itens_sem_depara (bloqueio imediato)                 │
│  5. Buscar POs LOCAL (_buscar_pos_fornecedor_local)         │
│  6. Para cada produto: match com split                      │
│     ├─ Filtrar POs por preco (0%) e data (±dias uteis)      │
│     ├─ Alocar qtd_nf nos POs (por data ASC)                │
│     └─ Registrar MatchNfPoItem + MatchAlocacao              │
│  7. Se 100% match → status='aprovado'                       │
│     Se <100% → status='bloqueado' + divergencias            │
└─────────────────────────────────────────────────────────────┘
```

## Constantes de Tolerancia

```python
TOLERANCIA_QTD_PERCENTUAL = Decimal('10.0')       # Qtd NF pode ser ate 10% MAIOR que PO
TOLERANCIA_PRECO_PERCENTUAL = Decimal('0.0')      # Preco deve ser EXATO (0% tolerancia)
TOLERANCIA_DATA_ANTECIPADO_DIAS_UTEIS = 3         # NF pode chegar 3 dias uteis ANTES
TOLERANCIA_DATA_ATRASADO_DIAS_UTEIS = 7           # NF pode chegar 7 dias uteis DEPOIS
```

## REGRA CRITICA: Preview vs Validacao

| Operacao | Fonte de Dados | Chama Odoo? |
|---|---|---|
| `validar_dfe()` | Odoo + Local | SIM (leitura DFE/linhas) |
| `buscar_preview_pos_candidatos()` | 100% LOCAL | **NUNCA** |

O **preview** (modal POs Candidatos) usa EXCLUSIVAMENTE dados locais:
- `ValidacaoNfPoDfe` para cabecalho
- `MatchNfPoItem` para itens (ja convertidos)
- `PedidoCompras` para POs candidatos

## Tipos de Divergencia

| Tipo | Causa | Resolucao |
|---|---|---|
| `sem_depara` | Codigo fornecedor sem cadastro | Criar De-Para |
| `sem_po` | Nenhum PO com saldo para o produto | Ajustar PO ou aprovar |
| `preco_diverge` | Preco NF != Preco PO (0% tolerancia) | Aprovar ou corrigir PO |
| `data_diverge` | Data NF fora da janela ±dias uteis | Aprovar |
| `qtd_diverge` | Qtd NF > saldo PO + 10% | Ajustar PO |
| `saldo_insuficiente` | Mesmo com split, saldo total < qtd NF | Criar PO complementar |

## Referencias

- [Fluxo Completo](references/fluxo-validacao-nf-po.md) - Etapas detalhadas com codigo
- [Erros Comuns](references/erros-comuns.md) - Armadilhas e solucoes

## Skills Relacionadas

- `rastreando-odoo` - Para CONSULTAR documentos (nao executar)
- `descobrindo-odoo-estrutura` - Para explorar campos Odoo desconhecidos
- `executando-odoo-financeiro` - Para operacoes financeiras (pagamentos, reconciliacao)
