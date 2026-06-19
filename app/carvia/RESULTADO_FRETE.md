# CarVia — Resultado por Frete + Viabilidade

**Referenciado por**: `app/carvia/CLAUDE.md` (secao Estrutura)
**Atualizado**: 2026-06-19

Cobre: o rateio coerente receita vs custo por moto (`resultado_frete_service`), a tela admin-only `/carvia/resultado-frete` (+ export Excel 2 abas) e a viabilidade CarVia exibida no mapa da carteira e no embarque (`viabilidade_service`). Origem: spec `docs/superpowers/specs/2026-06-19-carvia-viabilidade-rateio-frete-design.md`.

---

## Regra de rateio coerente (o nucleo)

A **NF e o atomo**. Receita e custo descem ate a NF pela MESMA base de motos, entao a soma fecha em qualquer eixo de resumo (CTe / embarque / UF-mes) — "laranja com laranja" por construcao.

```
base_NF = motos_NF / Σ(motos das NFs da entidade)    # cascata quando Σ motos = 0:
                                                      #   peso_NF / Σ peso  →  1 / nº NFs
receita_NF      = cte_valor(operacao)        × base_NF_op
custo_sub_NF    = Σ subcontratos(operacao)   × base_NF_op
custo_coleta_NF = valor_coleta(coleta da NF) × (qtd_motos_linha / Σ qtd_motos_linhas_da_coleta)
resultado_NF    = receita_NF − custo_sub_NF − custo_coleta_NF
resultado_moto  = resultado_NF / motos_NF             # None (exibe "—") quando motos_NF = 0
```

- **Cascata** `Direto(1 NF) → Motos → Peso → Qtd NFs`, `quantize(0.01, ROUND_HALF_UP)`, ajuste de centavos na 1ª NF. Espelha `gerencial_service._aplicar_rateio_itens` (nivel NF).
- **NAO duplicar a contagem de motos**: `resultado_frete_service` REUSA `gerencial_service._build_moto_count_per_nf_subquery` (`GREATEST(chassis, ROUND(SUM itens-modelo))`). Alias proprio `moto_nf_rf` evita colisao.

## Fontes de receita e custo

| Componente | Fonte | Observacao |
|-----------|-------|-----------|
| Receita | `CarviaOperacao.cte_valor` | rateado entre as NFs da operacao |
| Custo subcontrato | `SUM(CarviaSubcontrato)` por `operacao_id` | valor por sub = `COALESCE(cte_valor, valor_acertado, valor_cotado)`. 1 operacao pode ter N subcontratos (prod: CTe-5 tem 7) |
| Custo coleta | `CarviaColeta.valor_coleta` | rateado pela `CarviaColetaNf.qtd_motos` (papel de pao). `UNIQUE(carvia_nf_id)` garante 1 NF ↔ ≤1 linha de coleta |

**Flag `REAL` vs `ESTIMADO`** (coluna na tela/Excel): `REAL` se algum subcontrato da operacao tinha `cte_valor` (CTe autorizado); `ESTIMADO` se so havia cotado/acertado; `—` se sem custo de subcontrato.

## Eixos de resumo

`ResultadoFreteService.resumo(eixo, data_inicio, data_fim, uf=None)`, `eixo ∈ {cte, embarque, uf_mes}` — agrega SUM das parcelas + `receita_moto` / `custo_moto` / `resultado_moto` / `margem_pct` (todos guardados contra divisao por zero).

- **Por CTe CarVia**: 1 linha por operacao. Visao onde os prejuizos aparecem (prod: CTe-67 receita R$4.000 vs custo R$4.309 = prejuizo).
- **Por Embarque** (`carvia_fretes.embarque_id`): junta as operacoes do mesmo veiculo fisico. **E o eixo que cobre o caso "1 subcontrato fisico cobre N CTes CarVia" (ex.: 14 motos = CTe de 10 + CTe de 4)** sem mudar o modelo — o modelo NAO tem FK subcontrato→N operacoes.
- **Por UF/mes**: visao gerencial por destino e periodo.

`detalhe_por_nf(...)` = 1 linha por NF (sempre o detalhe das duas abas/tela). Ordenacao: pior resultado primeiro.

## Viabilidade no mapa e no embarque (`viabilidade_service`)

`receita_carvia_por_lotes(lotes)` e `receita_carvia_por_embarque(embarque_id)` somam a receita CarVia BRUTA (sem rateio): CTe (`cte_valor`) quando ja existe, senao a cotacao (`CarviaCotacao.valor_final_aprovado`).

- **Ver no Mapa** (`app/carteira/routes/mapa_routes.py:rota_otimizar`): retorna `carvia_receita_total` + `viabilidade` (= receita − custo da rota). `mapa_pedidos.html` mostra os cards "CarVia (receita)" + "Viabilidade" (verde/vermelho). **NAO admin-only** — visivel a quem acessa o mapa.
- **Embarque** (`app/embarques/models.py:Embarque.receita_carvia()` + `visualizar_embarque.html`): badge **admin-only** (`current_user.perfil == 'administrador'`).
- **Isolamento R1**: carteira e embarque importam `viabilidade_service` via **lazy import** (dentro da funcao/metodo); CarVia nunca importa carteira/embarque.

## Gotchas

- **`motos = 0` e comum mesmo com receita/custo altos** (NF sem item-modelo nem chassi — prod: CTe-129/128). O rateio cai para peso e depois nº NFs; `resultado_moto` vira `None` ("—").
- **Banco LOCAL de teste tem ~11 NFs ATIVAS de 2026 residuais** (nao limpas pelo rollback por SAVEPOINT — sao dados pre-commitados). Testes de `detalhe_por_nf`/`resumo` escopam por `operacao_id`/`label` proprios, NAO por `len(det)` global.
- **Lazy `payload.lotes`**: o mapa so envia os lotes selecionados (`_lotesSelecionados()`); `carvia_por_lote` ja vai no JSON (tooltip por unidade = melhoria futura).

## Arquivos

| Camada | Arquivo |
|--------|---------|
| Rateio (core) | `app/carvia/services/financeiro/resultado_frete_service.py` |
| Receita bruta (mapa/embarque) | `app/carvia/services/financeiro/viabilidade_service.py` |
| Tela + export | `app/carvia/routes/resultado_frete_routes.py` · `app/templates/carvia/resultado_frete/index.html` |
| Consumo carteira | `app/carteira/routes/mapa_routes.py` · `app/templates/carteira/mapa_pedidos.html` |
| Consumo embarque | `app/embarques/models.py` · `app/templates/embarques/visualizar_embarque.html` |
| Export NF (cidade) | `app/carvia/routes/exportacao_routes.py` (`exportar_nfs` / `exportar_operacoes`) |
| Testes | `tests/carvia/test_resultado_frete_service.py` · `test_resultado_frete_routes.py` · `test_viabilidade_service.py` · `test_export_nf_cidade.py` |
