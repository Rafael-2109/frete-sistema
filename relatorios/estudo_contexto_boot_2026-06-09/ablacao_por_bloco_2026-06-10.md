<!-- doc:meta
tipo: relatorio
camada: L3
sot_de: —
hub: docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md
superseded_by: —
atualizado: 2026-06-10
-->
# Ablacao por bloco — hook dinamico (F6 PAD-CTX)

> **Papel:** medicao da contribuicao de CADA bloco do hook dinamico para turnos
> reais (item da F6 do plano `2026-06-09-arquitetura-contexto-boot-agente.md`).
> Mesma metodologia judge-cetico do `precision_at_k_baseline_2026-06-10.md`.
> Anexo do plano — registra EVIDENCIA; decisoes de poda ficam para fases futuras.

## Metodo

- **Mesmos 20 turnos reais** do baseline precision@k (`/tmp/f5_baseline/dataset.json`,
  9 usuarios, dominios expedicao/estoque/financeiro/CarVia/Odoo).
- **Payload POS-F6 reconstruido** por turno com dados PROD read-only
  (`/tmp/f6_ablacao/build_payloads.py`): replica as queries reais de
  `memory_injection.py` e usa os helpers REAIS de destilacao (caps F6 aplicados:
  `TIER1_PATH_CAPS`, `USER_RULE_CHAR_CAP`, dedup L1×Tier1).
- **Tier 2** = top-4 voyage-4-large@0.40 dos artefatos F5 (`/tmp/f5_braco_b/`).
- **Julgamento**: 20 judges Sonnet ceticos (1/turno; workflow `ablacao-por-bloco-f6`),
  veredito por bloco: `muda_resposta` (remover degradaria ESTE turno) / `inerte` /
  `risco` (pode induzir erro NESTE turno). Criterio identico ao precision@k
  ("util = muda concretamente a resposta DESTE turno").
- Artefatos: `/tmp/f6_ablacao/` (payloads.json, ablacao_result.json, script).

### Aproximacoes declaradas

- `intersession_briefing` NAO reconstruido (condicional a eventos; ~0,4KB) — fora
  do estudo.
- `session_context`/`debug`/`sql_admin` fora do estudo (1-3 linhas, condicionais).
- Corpus do Tier 2 sem `meta` (artefato F5) → destilado caiu no truncate de content.
- Criterio TURN-LEVEL subestima blocos de conduta rara: a diretiva constitucional
  `registro-melhorias` dispara em situacoes especificas (bug/atrito) que podem nao
  ocorrer em 20 turnos — o 0% das directives NAO prova que a constitucional e inutil;
  prova que as ORGANICAS (a maior parte dos 4,3KB) nao tocaram nenhum turno real.

## Resultados (20 turnos, payload pos-F6)

| Bloco | Presente | muda_resposta | inerte | risco | % util (muda/presente) | Tamanho medio |
|---|---:|---:|---:|---:|---:|---:|
| tier1_perfil (user/prefs/expertise, DESTILADO F6) | 19/20 | 18 | 1 | 0 | **95%** | 3,3K |
| recent_sessions | 20/20 | 15 | 5 | 0 | **75%** | 2,5K |
| tier2_rag (large@0.40, top-4 destilado) | 18/20 | 13 | 4 | 1 | **72%** | 1,4K |
| user_rules (cap F6) | 8/20 | 4 | 4 | 0 | 50% | 1,1K |
| pendencias_acumuladas | 17/20 | 5 | 12 | 0 | 29% | 0,4K |
| tier15_perfil_empresa | 4/20 | 1 | 3 | 0 | 25% | 0,1K |
| routing_context | 20/20 | 4 | 14 | **2** | 20% | 0,8K |
| operational_directives | 20/20 | **0** | 20 | 0 | **0%** | **4,3K** |

## Leituras principais

1. **O cap F6 nao destruiu o valor do tier1**: destilado a ~metade do tamanho
   (3,3K vs 6,6-9,1K), o perfil segue sendo o bloco MAIS util (95%) — as
   preferencias de formato/expertise mudam concretamente quase toda resposta.
2. **O retrieval consertado (F5) entrega**: tier2 large@0.40 destilado = 72% de
   utilidade por turno (vs precision 0.013 do fallback de recencia pre-F5).
   1 risco observado (heuristica financeira pescada em turno de estoque).
3. **operational_directives e o bloco mais caro e o menos util**: 4,3KB TODO
   turno, 0/20 turn-level. As organicas (nivel 5 por effective_count) nao
   tocaram nenhum turno real da amostra. CANDIDATO (decisao futura, nao agir
   sem validacao): injetar organicas por INTENT (como o Tier 2) ou reduzir o
   cap de 5 organicas; constitucional fica (conduta, fora do criterio turn-level).
4. **routing_context confirma C5 em nova dimensao**: unico bloco com 2 riscos —
   `preferred_skills` derivado de DOMINIO HISTORICO induziu skill errada em
   turnos cujo intent divergia do dominio (ex: picking de producao tratado como
   recebimento). Refor​ca F7.5 (derivar preferred_skills de uso real) ou remover
   `preferred_skills` mantendo `active_traps`.
5. **pendencias 29%**: TTL de 2 dias mantem itens que os judges consideraram
   ja resolvidos/irrelevantes ao turno — coerente com o lifecycle existente
   (resolve_pendencia); sem acao.

## Encaminhamentos (registrados no plano, F7/backlog)

- Directives organicas por intent OU cap menor — exige validacao comportamental
  (golden dataset agora com 54+20 casos) antes de mudar; NAO incluido na F6.
- `preferred_skills`: ja ha item F7.5 (derivacao por uso real). Os 2 riscos
  desta ablacao sao evidencia adicional.
- Re-rodar esta ablacao apos dias de trafego com o retrieval large (mesma
  janela do aceite formal F5) — payloads/script reexecutaveis.
