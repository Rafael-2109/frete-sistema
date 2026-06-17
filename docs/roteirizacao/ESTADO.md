<!-- doc:meta
tipo: state
camada: L1
sot_de: estado vivo do projeto de ampliacao da roteirizacao "Ver no Mapa" (fonte unica de progresso das 3 fases)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-16
-->
# Roteirizacao "Ver no Mapa" — ESTADO

> **Papel:** fonte UNICA de progresso da ampliacao da roteirizacao. Atualizar AQUI a cada avanco (nao replicar estado em outros docs). Design = spec; passo-a-passo = plano (links abaixo).

## Artefatos

- **Spec (design):** [docs/superpowers/specs/2026-06-16-roteirizacao-ver-no-mapa-design.md](docs/superpowers/specs/2026-06-16-roteirizacao-ver-no-mapa-design.md)
- **Plano Fase 1:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase1.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase1.md)

## Decisoes fechadas (Rafael, 16/06/2026)

- Escopo: **mono-veiculo** (1 rota refinavel). VRP multi-veiculo fica para depois.
- Motor de otimizacao: **Google Route Optimization API (Single Vehicle)** — alvo; entra plugavel quando a service account existir (ver R1).
- Custo: **teorico parametrico** (sem comparativo com real/cotacao nesta entrega).
- Fonte de custo: **por tipo** de veiculo (tabela `veiculos`).
- Composicao do custo: combustivel + motorista/dia + **fixo/dia** + **depreciacao** (/30) + pedagio.
- Empacotador 3D de motos: **fora de escopo** (outra sessao).

## Estado atual

Design aprovado e plano da Fase 1 escrito (7 tasks TDD). Execucao ainda NAO iniciada — nenhum codigo de producao tocado.

| Fase | Escopo | Status |
|------|--------|--------|
| **1 — Fundacao de custo + motor** | migration `veiculos` (8 campos) + CRUD; service custo/selecao/motor (chunking 25); API `/api/rota/otimizar`; UI parametros + card de custo | PLANEJADA (plano escrito; execucao nao iniciada) |
| **2 — Interatividade + persistencia** | incluir/remover on-demand; tabela `rota_salva` (salvar/nomear/listar); `geocode_cache` persistente | A FAZER (plano a escrever) |
| **3 — Cotacao por rota + extras** | cotar a partir de rota salva (reusa wizard); reordenar drag-and-drop; origem configuravel | A FAZER (plano a escrever) |

Tasks da Fase 1 (marcar ao concluir):

- [ ] T1 — Migration `veiculos` (8 colunas) + model + schema JSON
- [ ] T2 — `calcular_custo_operacional` (funcao pura, TDD)
- [ ] T3 — `selecionar_veiculo` multidimensional (TDD)
- [ ] T4 — Motor `otimizar_rota` + `_chunk_waypoints` (TDD)
- [ ] T5 — Backend Directions+chunking + plug Route Optimization (TDD)
- [ ] T6 — API `POST /api/rota/otimizar` (TDD)
- [ ] T7 — Frontend: painel de parametros + card de custo (smoke)

## Pendencias

- **R1 — Auth do Route Optimization API:** pode exigir service account/OAuth2 (Google Cloud), nao a `GOOGLE_MAPS_API_KEY` atual. A Fase 1 entrega o backend **Directions+chunking** (funcional com a key atual, supera o limite de 25 no desenho); o backend Route Optimization fica plugavel (`_route_optimization_backend`, stub). **Acao do Rafael quando quiser otimizacao global real >25:** criar service account no GCP + habilitar a API.
- **R4 — Geocoding sem persistencia:** ainda re-geocodifica enderecos novos a cada otimizacao na Fase 1; `geocode_cache` resolve na Fase 2.
- **Proximo passo:** executar a Fase 1 task-a-task (TDD), marcando o status por task acima a cada conclusao.

## Atualizado

- **2026-06-16:** criado o ESTADO; spec e plano da Fase 1 escritos e registrados nos indices. Execucao pendente.
