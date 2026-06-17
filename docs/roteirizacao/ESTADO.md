<!-- doc:meta
tipo: state
camada: L1
sot_de: estado vivo do projeto de ampliacao da roteirizacao "Ver no Mapa" (fonte unica de progresso das 3 fases)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-17
-->
# Roteirizacao "Ver no Mapa" — ESTADO

> **Papel:** fonte UNICA de progresso da ampliacao da roteirizacao. Atualizar AQUI a cada avanco (nao replicar estado em outros docs). Design = spec; passo-a-passo = plano (links abaixo).

## Artefatos

- **Spec (design):** [docs/superpowers/specs/2026-06-16-roteirizacao-ver-no-mapa-design.md](docs/superpowers/specs/2026-06-16-roteirizacao-ver-no-mapa-design.md)
- **Plano Fase 1:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase1.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase1.md)
- **Plano Fase 2:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase2.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase2.md)
- **Plano Fase 3:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase3.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase3.md)

## Decisoes fechadas (Rafael, 16/06/2026)

- Escopo: **mono-veiculo** (1 rota refinavel). VRP multi-veiculo fica para depois.
- Motor de otimizacao: **Google Route Optimization API (Single Vehicle)** — alvo; entra plugavel quando a service account existir (ver R1).
- Custo: **teorico parametrico** (sem comparativo com real/cotacao nesta entrega).
- Fonte de custo: **por tipo** de veiculo (tabela `veiculos`).
- Composicao do custo: combustivel + motorista/dia + **fixo/dia** + **depreciacao** (/30) + pedagio.
- Empacotador 3D de motos: **fora de escopo** (outra sessao).

## Estado atual

As 3 FASES IMPLEMENTADAS + Route Optimization API REAL, **mergeadas na `main`** (origem: branch `worktree-roteirizacao-ver-no-mapa`). **38 testes verdes** (PostgreSQL local); migrations aplicadas no banco local **e em PROD** (`veiculos`+8 campos, `geocode_cache`, `rota_salva`) — ver nota de incidente abaixo; smoke de render dos templates = 200. Toda a demanda original coberta + R1 resolvido (Route Optimization validado contra a API real). **Credenciais GCP gravadas no Render PROD** (`ROUTE_OPTIMIZATION_PROJECT` + `GOOGLE_CREDENTIALS_JSON`) — Route Optimization fica ativo no proximo deploy. PENDENTE: smoke VISUAL no browser; validar Route Optimization ativo em PROD apos o deploy do push.

| Fase | Escopo | Status |
|------|--------|--------|
| **1 — Fundacao de custo + motor** | migration `veiculos` (8 campos) + CRUD; service custo/selecao/motor (chunking 25); API `/api/rota/otimizar`; UI parametros + card de custo | IMPLEMENTADA (branch worktree; 20 testes verdes; falta smoke browser + push) |
| **2 — Interatividade + persistencia** | incluir/remover on-demand; tabela `rota_salva` (salvar/nomear/listar); `geocode_cache` persistente | IMPLEMENTADA (branch worktree; 11 testes F2 verdes; falta smoke browser + push) |
| **3 — Cotacao por rota + extras** | cotar a partir de rota salva (reusa wizard); reordenar drag-and-drop; origem configuravel | IMPLEMENTADA (branch worktree; 3 testes F3 verdes; falta smoke browser + push) |

Tasks da Fase 1:

- [x] T1 — Migration `veiculos` (8 colunas) + model + schema JSON
- [x] T2 — `calcular_custo_operacional` (funcao pura, TDD)
- [x] T3 — `selecionar_veiculo` multidimensional (TDD)
- [x] T4 — Motor `otimizar_rota` + `_chunk_waypoints` (TDD)
- [x] T5 — Backend Directions+chunking + plug Route Optimization (TDD)
- [x] T6 — API `POST /api/rota/otimizar` (TDD)
- [x] T7 — Frontend: CRUD custos + painel de parametros + card de custo (render OK; smoke browser pendente)

Tasks da Fase 2:

- [x] T1 — `GeocodeCache` (L2 persistente) no `geocodificar_endereco`
- [x] T2 — model `RotaSalva` + migration
- [x] T3 — APIs salvar/listar/carregar/excluir rota
- [x] T4 — API adicionar pedido on-demand
- [x] T5 — UI incluir/remover on-demand + salvar/carregar rotas (render OK; smoke browser pendente)

Tasks da Fase 3:

- [x] T1 — API cotar frete a partir de rota salva (reusa wizard)
- [x] T2 — UI cotar rota + origem configuravel + drag-and-drop (render OK; smoke browser pendente)

Ajustes vs plano (durante a execucao TDD): (a) fixture `_isola_veiculos` desativa os 10 veiculos pre-existentes do banco em `test_roteirizacao_selecao` (savepoint reverte); (b) `otimizar_rota` checa lista vazia ANTES de importar o backend (bug pego pelo teste); (c) backend adiciona o ponto que vira destino na ordem quando nao ha volta (espelha `mapa_service` original); (d) `api/lista` converte `Numeric`->float (jsonify nao serializa Decimal).

## Pendencias

- **R1 — Route Optimization API:** RESOLVIDO (17/06/2026). `route_optimization_backend` implementado (optimizeTours via service account / google-auth) e **validado contra a API real** (ordem otimizada + distancia/tempo/polyline; ex.: 3 paradas SP = 72,34 km / 107,6 min). `default_backend` usa Route Optimization quando `ROUTE_OPTIMIZATION_PROJECT` esta setado; senao cai para Directions+chunking (fallback automatico em erro). Projeto = `dynamic-heading-434921-q5`; SA = `sistema-fretes-routes-api@...` (role Route Optimization Editor). Janela global = 7 dias; metrica = `travelDuration`. Credencial: `_ro_token()` prioriza `GOOGLE_CREDENTIALS_JSON` (conteudo do JSON da SA na env var) e cai para ADC padrao (`GOOGLE_APPLICATION_CREDENTIALS`) se ausente — ambos os caminhos cobertos por teste.
- **PROD (Render) — Route Optimization ATIVADO:** env vars gravadas em PROD (`sistema-fretes` / `srv-d13m38vfte5s738t6p60`) via Render API em 17/06/2026: `ROUTE_OPTIMIZATION_PROJECT=dynamic-heading-434921-q5` + `GOOGLE_CREDENTIALS_JSON` (JSON da SA, 2373 bytes). Optou-se por env var JSON em vez de Secret File pois o MCP/automacao so grava env vars; o token OAuth2 foi validado localmente lendo a credencial pela env var. A chave NAO esta no git (vive em `.secrets/route-optimization-sa.json` no dev, gitignorada). Fica efetivo no proximo deploy (o do push desta entrega — gravar env var nao disparou redeploy).
- **R4 — Geocoding sem persistencia:** RESOLVIDO na Fase 2 (`geocode_cache` L2 no banco; L1 memoria -> L2 banco -> Google).
- **Smoke visual (browser):** validar no navegador o painel de parametros + card de custo no mapa e o cadastro de custos no admin de veiculos (nao automatizado nesta sessao).
- **Push/PR:** CONCLUIDO (17/06/2026) — merge fast-forward na `main` + push. Worktree `worktree-roteirizacao-ver-no-mapa` pode ser removida.
- **Custo Google na Fase 1:** o card chama `/api/rota/otimizar` (1 request Directions) ALEM do desenho via `/api/rota-clientes` — 2 roteirizacoes por calculo. Unificar na Fase 2/3 (aceitavel agora; Directions optimize dentro do free tier).
- **Proximo passo:** apos o deploy do push concluir em PROD, validar Route Optimization ativo (1 calculo real no mapa -> conferir `trechos=1` e ausencia de warning de fallback nos logs) + smoke VISUAL no browser. Roadmap das 3 fases + R1 entregue e credencial PROD configurada.

## Atualizado

- **2026-06-16 (1):** criado o ESTADO; spec e plano da Fase 1 escritos e registrados nos indices.
- **2026-06-16 (2):** Fase 1 IMPLEMENTADA no branch worktree (8 commits, T1-T7); 20 testes verdes; migration aplicada no banco local; render 200 nos 2 templates. Pendente: smoke browser + push/PR + R1.
- **2026-06-16 (3):** Fase 2 IMPLEMENTADA (T1-T5): `geocode_cache` (L2) + `RotaSalva` + APIs salvar/listar/carregar/excluir + adicionar pedido on-demand + UI. 28 testes verdes no total; tabelas criadas no banco local; render 200. Pendente: smoke browser + push/PR.
- **2026-06-16 (4):** Fase 3 IMPLEMENTADA (T1-T2): API cotar frete por rota salva (reusa wizard) + origem configuravel + drag-and-drop. **31 testes verdes**; render 200. As 3 fases concluidas. Pendente: smoke browser + push/PR.
- **2026-06-17 (5):** R1 RESOLVIDO — Route Optimization API real (optimizeTours via service account) implementada e VALIDADA contra a API ao vivo; fallback Directions automatico; google-auth==2.55.0; credencial em `.secrets/` (gitignore). **36 testes verdes**. Pendente: smoke browser + push/PR + credenciais no Render.
- **2026-06-17 (6):** ENTREGA — `_ro_token()` passa a aceitar `GOOGLE_CREDENTIALS_JSON` (credencial via env var, p/ Render) alem de ADC, com 2 testes novos (**38 testes verdes**). Env vars gravadas em PROD via Render API (`ROUTE_OPTIMIZATION_PROJECT` + `GOOGLE_CREDENTIALS_JSON`, ambos HTTP 200). Merge fast-forward na `main` + push. Route Optimization ativo no proximo deploy. Pendente: validar em PROD pos-deploy + smoke browser.
- **2026-06-17 (7):** INCIDENTE PROD + FIX — apos o deploy, `/pedidos/lista_pedidos` deu 500 (`UndefinedColumn: veiculos.custo_km`): a migration `2026_06_16_veiculo_parametros_custo.sql` (8 colunas em `veiculos`) nao havia sido aplicada em PROD. O boot (`create_all`) cria TABELAS novas (`geocode_cache`/`rota_salva` ja existiam) mas NAO adiciona colunas a tabela existente — colunas novas exigem rodar o `.sql` em PROD. Apliquei as 3 migrations idempotentes via `DATABASE_URL_PROD`; `lista_pedidos` voltou a 200. LICAO: aplicar migration de coluna em PROD ANTES/junto do push (o deploy do Render nao roda `scripts/migrations/*.sql`).
