<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-19
-->
# Spec — Viabilidade CarVia no mapa + Cidade no export NF + Resultado por Frete (rateio por moto)

> **Papel:** especificacao de design (brainstorming) das 3 entregas CarVia pedidas em 2026-06-19.

## Indice

- [Contexto](#contexto)
- [Objetivo](#objetivo)
- [Decisoes do brainstorming (respostas do usuario)](#decisoes-do-brainstorming-respostas-do-usuario)
- [Evidencias de producao (amostra, MCP Render, 2026-06-19)](#evidencias-de-producao-amostra-mcp-render-2026-06-19)
- [Nucleo comum: regra de rateio coerente](#nucleo-comum-regra-de-rateio-coerente)
- [Entrega 1 — Cidade destino no export de NF](#entrega-1-cidade-destino-no-export-de-nf-pontual-sem-migracao)
- [Entrega 2 — Valor CarVia no "Ver no Mapa"](#entrega-2-valor-carvia-no-ver-no-mapa)
- [Entrega 3 — Tela + Excel "Resultado por Frete"](#entrega-3-tela--excel-resultado-por-frete)
- [Fora de escopo (YAGNI)](#fora-de-escopo-yagni)
- [Sequencia de entrega](#sequencia-de-entrega)
- [Documentacao a atualizar no fechamento](#documentacao-a-atualizar-no-fechamento-parte-do-pronto)

## Contexto

Origem: o usuario tem dificuldade de (a) enxergar o resultado da CarVia por frete/CTe e (b) avaliar a
viabilidade ANTES de embarcar enquanto roteiriza em "Ver no Mapa". Esta spec cobre 3 entregas
independentes no dominio CarVia (frete subcontratado) + a tela de roteirizacao da Carteira. As
decisoes de negocio (fonte do valor no mapa, base de rateio, eixos de agregacao) foram fechadas com o
usuario via brainstorming e validadas contra dados de producao (MCP Render). Modulo CarVia e isolado
(R1 em `app/carvia/CLAUDE.md`): qualquer leitura cruzada se faz por lazy import.

## Objetivo

1. **Ver no Mapa**: conectar o valor CarVia (CTe quando houver, senao a cotacao) aos lotes/pedidos
   roteirizados e exibir a somatoria ao lado do **custo calculado da rota**, para comparar viabilidade
   antes de embarcar. A mesma viabilidade tambem aparece na tela de **Embarque**, restrita a admin
   (`perfil='administrador'`).
2. **Export Excel das NF**: incluir a **cidade destino** alem do UF.
3. **Tela + Excel "Resultado por Frete"**: visualizar o resultado por frete considerando o rateio da
   **coleta + CTe Subcontrato pela quantidade de motos**, respeitando a agregacao (comparar
   "laranja com laranja" pela mesma base de motos/NF).

## Decisoes do brainstorming (respostas do usuario)

- **Valor CarVia no mapa**: CTe quando houver (`CarviaOperacao.cte_valor`), senao o valor cotado do
  frete (`CarviaCotacao.valor_final_aprovado`). Funciona pre e pos faturamento.
- **Coerencia do rateio** (ponto central do usuario): receita, subcontrato e coleta sao **todos**
  rateados pela MESMA base — quantidade de motos por NF. A regra do usuario:
  `valor_CarviaOperacao / qtd_total_motos x motos_da_NF` (receita) e
  `valor_CarviaSubcontrato / qtd_total_motos x motos_da_NF` (custo), e idem coleta.
- **Sem mudanca de modelo**: nao criar vinculo novo subcontrato↔N operacoes. O caso "1 subcontrato
  (14) = CTes de 10 + 4" e resolvido pela agregacao por **Embarque/veiculo**, nao por FK nova.
- **Eixos de resumo da tela 3** (multi): **CTe CarVia (operacao)**, **Embarque/veiculo**, **UF/mes**.
  Detalhe sempre 1 linha por NF.
- **Tela 3** = Resumo + Detalhe (2 abas no Excel).

## Evidencias de producao (amostra, MCP Render, 2026-06-19)

> Universo: 528 NFs ATIVAS, 450 operacoes (CTe CarVia) nao-canceladas, 158 subcontratos
> (so 14 com chave de CTe; 140 com `cte_valor` preenchido), 391 fretes, 3 coletas, 521 vinculos
> operacao-NF, 66 NFs em coleta.

Fatos que moldam o design:

- **Rateio por moto confere**: CTe-418 (`op 441`) — receita R$1.440 / 6 motos em 3 NFs de 2 →
  R$240/moto, R$480/NF.
- **Prejuizos hoje invisiveis** (justificam a tela): CTe-67 (`op 81`) receita R$4.000 x custo sub
  R$4.309 = **-R$309**; CTe-87 (`op 97`) R$2.500 x R$2.728 = prejuizo; CTe-27 (`op 6`) R$25.000 x
  R$3.306 = lucro alto.
- **`motos = 0` ocorre com receita/custo altos** (NF sem item-modelo nem chassi): CTe-129/128
  (`op 147/148`) receita ~R$8–11k, custo ~R$7–10k, **0 motos**. → o rateio por moto PRECISA de
  cascata de fallback (motos → peso → nº NFs).
- **1 operacao pode ter N subcontratos**: CTe-5 (`op 24`) tem **7 subcontratos**. → custo = SUM.
- **Subcontrato → no maximo 1 operacao** (nenhuma chave de CTe de subcontrato repetida cobrindo N
  operacoes). Subcontratos orfaos existem (`operacao_id` e `frete_id` NULL): 11 de 158.

## Nucleo comum: regra de rateio coerente

Reaproveita a cascata ja testada de `app/carvia/services/financeiro/gerencial_service.py`:
`_build_moto_count_per_nf_subquery` (L39, `GREATEST(chassis, ROUND(SUM itens-modelo))`),
`_build_moto_count_subquery` (L85) e `_aplicar_rateio_itens` (L446) com criterio em cascata
**Motos (L509) → Peso (L516) → Qtd NFs (L523)**.

Regra por NF (atomo):

```
base_NF = motos_NF / Σ(motos das NFs da entidade)          # cascata quando Σ motos = 0
                                                            #   peso_NF / Σ peso  → 1 / nº NFs

receita_NF       = cte_valor(operacao)         x base_NF_op
custo_sub_NF     = Σ subcontratos(operacao)    x base_NF_op    # COALESCE(cte_valor, valor_acertado, valor_cotado)
custo_coleta_NF  = valor_coleta(coleta da NF)  x base_NF_coleta
resultado_NF     = receita_NF − custo_sub_NF − custo_coleta_NF
resultado_moto   = resultado_NF / motos_NF                     # N/A quando motos_NF = 0
```

A NF e o atomo. Todo eixo de resumo (CTe, embarque, UF/mes) e `SUM` dessas parcelas; por construcao
a soma fecha em qualquer eixo → comparacao "laranja com laranja" garantida.

Flag de qualidade do custo por linha: **REAL** (havia `CarviaSubcontrato.cte_valor`) vs **ESTIMADO**
(`valor_acertado`/`valor_cotado`).

---

## Entrega 1 — Cidade destino no export de NF (pontual, sem migracao)

Arquivo: `app/carvia/routes/exportacao_routes.py`. Campo fonte: `CarviaNf.cidade_destinatario`
(`varchar(100)`, ja populado pelo parser).

- `exportar_nfs`: dado em ~L390 (`'nf_uf_dest': nf.uf_destinatario`) → adicionar
  `'nf_cidade_dest': nf.cidade_destinatario or ''`; coluna em ~L446 (`Campo('nf_uf_dest','UF')`) →
  adicionar `Campo('nf_cidade_dest','Cidade Dest')`.
- `exportar_operacoes`: dado em ~L611 (`'nf_uf_dest': ...`) → adicionar
  `'nf_cidade_dest': (nf.cidade_destinatario if nf else op.cidade_destino) or ''`; coluna em ~L657 →
  `Campo('nf_cidade_dest','Cidade Dest')`.

Ordem sugerida: Cidade Dest **antes** de UF (cidade/UF e a leitura natural). 4 edicoes, 0 migracao.

## Entrega 2 — Valor CarVia no "Ver no Mapa"

Telas: `/carteira/mapa/visualizar`. Mostra a viabilidade enquanto roteiriza (pre-embarque).

**Backend** — `app/carteira/routes/mapa_routes.py` (`rota_otimizar`, L522) + helper novo em
`app/carteira/services/mapa_service.py`:

- O POST `/carteira/mapa/api/rota/otimizar` passa a aceitar `lotes` no payload (ja existe
  `_lotesSelecionados()` no front) e retorna `carvia_receita_total` + `carvia_por_lote` (breakdown).
- Helper `calcular_receita_carvia_lotes(lotes)` (lazy import de `app/carvia`, conforme R1):
  - `CARVIA-PED-{id}` → `CarviaPedido`; se `operacoes_ctes` (cotacao.py:497) tem CTe →
    `SUM(CarviaOperacao.cte_valor)`; senao `CarviaPedido.cotacao.valor_final_aprovado`.
  - `CARVIA-{cot_id}` → `CarviaCotacao.valor_final_aprovado` (fallback `valor_manual`/`valor_tabela`).
  - `CARVIA-NF-{id}` → via `CarviaNf` → operacao → `cte_valor` (se aparecer).
  - Lote NACOM → 0 (esta feature e CarVia).
  - Cada lote sinaliza a fonte: `CTE` (real) | `COTACAO` (estimado).

**Frontend** — `app/templates/carteira/mapa_pedidos.html`:

- Bloco `#custoRotaRow` (L154-161): card novo **"CarVia (receita)"** + card **"Viabilidade"**
  (`receita − custo`, verde se ≥ 0, vermelho se < 0).
- `preencherCardCusto(resp)` (L1165): popular os 2 cards a partir de `resp.carvia_receita_total`.
- `recalcularRota` (L1114): incluir `payload.lotes = _lotesSelecionados()`.
- Valor CarVia por unidade no tooltip do chip (a partir de `carvia_por_lote`).

**Exibicao no Embarque (admin-only)** — `app/embarques/routes.py` (`visualizar_embarque`, L130) +
`app/templates/embarques/visualizar_embarque.html`:

- Gate `{% if current_user.perfil == 'administrador' %}` (admin_only; padrao do projeto =
  `require_admin` / `perfil='administrador'` em `app/utils/auth_decorators.py:65`). O template ja
  condiciona blocos CarVia via `{% if current_user.sistema_carvia %}` (L163) — a viabilidade fica num
  bloco SEPARADO, admin_only.
- A rota soma a **receita CarVia** do embarque (CTe `CarviaOperacao.cte_valor` das NFs CarVia do
  embarque; fallback cotacao) reusando o mesmo helper da Entrega 2, e expoe ao template. Exibe a
  receita CarVia total e, quando o embarque tiver custo de frete associado, a viabilidade
  (receita − custo).
- Somente exibicao (read-only); nenhuma escrita nova no embarque.

Sem persistencia nova (a `RotaSalva` continua snapshot do custo; receita CarVia e calculada ao vivo).

## Entrega 3 — Tela + Excel "Resultado por Frete"

**Service novo** — `app/carvia/services/financeiro/resultado_frete_service.py`:

- Implementa a regra de rateio coerente (acima), reaproveitando as subqueries/cascata do
  `gerencial_service`. NAO duplicar a contagem de motos — importar/usar as funcoes existentes.
- Saidas:
  - `detalhe_por_nf(filtros)` → 1 linha/NF: nf, cliente, cidade/UF, motos, operacao/CTe, embarque,
    receita_NF, custo_sub_NF (+ flag REAL/ESTIMADO), custo_coleta_NF, resultado_NF, resultado_moto.
  - `resumo(eixo, filtros)` com `eixo ∈ {cte, embarque, uf_mes}` → SUM das parcelas por eixo +
    receita, custo_sub, custo_coleta, resultado, motos, R$/moto (receita/custo/resultado),
    % margem.
- Cadeias: operacao via `carvia_operacao_nfs`; subcontratos via `CarviaSubcontrato.operacao_id`
  (SUM, COALESCE cte_valor→acertado→cotado); coleta via `carvia_coleta_nfs.carvia_nf_id` →
  `CarviaColeta.valor_coleta`; embarque via `carvia_fretes.embarque_id`/`operacao_id`.
- **Edge cases**: motos=0 → cascata; subcontrato orfao (sem operacao) → linha de custo "sem CTe
  CarVia" (nao entra no rateio por operacao, aparece destacada no resumo por transportadora/embarque
  quando houver `frete_id`); coleta sem NF real (rascunho) → usa `CarviaColetaNf.qtd_motos` manual.

**Tela** — rota `app/carvia/routes/resultado_frete_routes.py` (`/carvia/resultado-frete`) + template
`app/templates/carvia/resultado_frete/index.html` (padrao das telas CarVia, guard `sistema_carvia`):

- Filtros: periodo (`cte_data_emissao`), UF, status.
- Seletor de eixo do Resumo (CTe / Embarque / UF-mes).
- Tabela Resumo + tabela Detalhe (NF). Resultado negativo em vermelho.
- Botao "Exportar Excel".

**Excel** — `app/carvia/routes/exportacao_routes.py` (nova rota `exportar_resultado_frete`),
helper de duplo cabecalho `app/carvia/utils/excel_export_helper.py` (`ColunaGrupo`, `Campo`):

- Aba **Resumo** (pelo eixo selecionado) + aba **Detalhe (NF)**.

## Fora de escopo (YAGNI)

- Nao criar junction subcontrato↔N operacoes (decisao do usuario; agregacao por embarque cobre).
- Nao alterar o calculo de custo da rota no mapa (so somar a receita CarVia ao lado).
- Nao tocar `app/carteira/main_routes.py` (regra de nao-estender).

## Sequencia de entrega

1. Entrega 1 (cidade no export) — pontual, baixo risco.
2. Entrega 2 (viabilidade no mapa).
3. Entrega 3 (resultado por frete) — maior; service testavel primeiro, depois tela e Excel.

Cada entrega = commit isolado. Isolamento CarVia (R1) preservado: a Entrega 2 le CarVia via lazy
import, como o mapa ja faz.

## Documentacao a atualizar no fechamento (parte do "pronto")

- `app/carvia/CLAUDE.md` (nova regra de rateio/tela; secao Modelos se necessario).
- `app/carteira/CLAUDE.md` (card de receita CarVia no mapa).
- Testes: `tests/carvia/` (service de rateio com os casos da amostra: multi-NF, motos=0, multi-sub,
  coleta).
