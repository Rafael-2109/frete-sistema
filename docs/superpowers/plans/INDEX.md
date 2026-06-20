<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-20
-->
# Plans — indice
> **Papel:** mapa dos planos de implementacao. So ponteiros.

- [Persistência S3 + Recuperação de Uploads do Agente (IMP-19-007)](2026-06-20-s3-uploads-agente-recuperacao.md) — dual-write S3 dos anexos do chat + tabela manifesto `agente_upload` + 2 MCP tools no `mcp__sessions__` (`list_session_uploads`/`recover_upload`) + wiring do resume_notice; resolve a causa-raiz de IMP-20-002/19-008; 5 tasks TDD; decisões A-D batidas com Rafael; PRONTO p/ executar em worktree dedicada
- [Simulador 3D — Conservas Nacom (carga mista pallet + moto)](2026-06-18-simulador-3d-conservas-nacom.md) — expande o simulador de motos p/ conservas palletizadas: Camada 1 monta pallets PBR (regras 1-3, folga 5cm, overbooking 50%, modos A-D) em Python; Camada 2 estende o bin-packer (multi-slab estrado+coluna p/ caminho critico, 2 fases Nacom-embaixo); 10 tasks TDD; EXECUTADO (na main)
- [Roteirizacao "Ver no Mapa" — Fase 1](2026-06-16-roteirizacao-ver-no-mapa-fase1.md) — migration custo em veiculos + service custo/selecao/motor (chunking 25) + API /api/rota/otimizar + UI custo (7 tasks TDD)
- [Roteirizacao "Ver no Mapa" — Fase 2](2026-06-16-roteirizacao-ver-no-mapa-fase2.md) — geocode_cache persistente + model RotaSalva + APIs salvar/listar/carregar/excluir + adicionar pedido on-demand + UI (5 tasks TDD)
- [Roteirizacao "Ver no Mapa" — Fase 3](2026-06-16-roteirizacao-ver-no-mapa-fase3.md) — cotacao por rota salva (reusa wizard) + origem configuravel + drag-and-drop (2 tasks)
- [PAD-A Onda 0 — Fundacao](2026-06-01-pad-a-onda-0-fundacao.md) — lints+hooks+scaffold+skill+SOT
- [PAD-A Onda 1 — Indice mestre](2026-06-02-pad-a-onda-1-indice-mestre.md) — hubs + ligar docs/ ao CLAUDE.md + check C8
- [PAD-A Onda 2 — Conflitos diagnosticados](2026-06-02-pad-a-onda-2-conflitos.md) — reconcilia 6 conflitos doc/memoria + 1 bug worker-RQ + aposenta gold-script
- [PAD-A Onda 3 — Governanca dos scripts inventario/estoque](2026-06-02-pad-a-onda-3-governanca-scripts.md) — indice na zona + aposenta ~29 mortos + headers + estado-1-lugar + 2 ADRs
- [PAD-A Onda 4 — Varredura por cluster](2026-06-02-pad-a-onda-4-varredura-cluster.md) — toolchain migracao + calibracao + sub-ondas 4a-4g (orfao-zero + link-rot-zero + doc:meta) + promove C1/C7/C8 a block
- [GATE-1 — Calibracao do Judge Online (E3) + bugs do verify](2026-06-03-gate1-calibracao-judge-online.md) — sampler 5-10% + rotulagem humana acertou/errou + concordancia >=80% com >=10 rotulos; CUMPRIDO 2026-06-12 (12/12)
- [Grounding de estrutura (cobertura ampla)](2026-06-06-grounding-cobertura-ampla.md) — regra L2 + MCP tool resolver (fonte-que-prova); I2 da estrategia de atuadores; EXECUTADO (merge 07b99fdec)
- [HORA — Desconsiderar moto de NF de compra](2026-06-03-hora-desconsiderar-moto-nf.md) — flag desconsiderado por item + relaxa FK chassi + valida nao-em-pedido/nao-recebido (9 tasks TDD)
- [HORA — Unificar Pedido de Venda + filtro loja/vendedor + fix desconto](2026-06-03-hora-unificar-pedido-venda.md) — tela unica cria+edita (remove venda_detalhe), criterio loja/vendedor por usuario, fix drift centavos (13 tasks)
- [HORA — Pedido de Venda: editar item + Enter=Próximo + chassi autocomplete + regressões](2026-06-03-hora-pedido-venda-edicao-autocomplete.md) — editar moto = só desconto/valor (moto travada); Enter avança campo; chassi autocomplete; restaura CRÍTICOS+ALTOS da unificação (20 tasks, 3 fases)
- [HORA — Pedido de Venda: unificação multi-item + submit único (FU-2/3/5)](2026-06-04-hora-pedido-venda-unificacao-multi-item.md) — componente _lista_motos compartilhado, N motos na criação, salvar_pedido_completo reconciliador (helpers flush-only + 1 commit), 11 tasks em 4 fases
- [Redução de Custo do Agente — Fast-path + Downgrade de Modelo](2026-06-06-reducao-custo-agente-fast-path.md) — tira rotina do loop Opus (41%/$667 do custo é estruturado); FASE 1 baseline Marcus (script já existe) + FASE 2 model_router downgrade + FASE 3 fast-path vinculação Gabriella; mede via session_automation_audit.py; NÃO toca conversa_analise (51% genuíno)
- [Fast-path Vinculação NF×PO (Gabriella)](2026-06-08-fastpath-vinculacao-nf-po.md) — executa a FASE 3 pendente do plano acima: roteamento determinístico (regex N0) + Haiku fallback (N1) reusando validar_dfe/consolidar_pos/reverter_consolidacao; anomalia cai no gestor-recebimento (N2). Tira a Gabriella (~$269/45d, $20/sessão) do subagente Opus xhigh no caminho feliz; flag AGENT_VINCULACAO_FASTPATH
- [Agente Web — 4 Bugs (causas confirmadas) + Handoff Memória](2026-06-08-agente-web-4-bugs-handoff.md) — redesenho do formato canônico de memórias ENTREGUE (meta JSONB + sentinela, list_memories vira índice); 4 bugs restantes com causa-raiz + `arquivo:linha` + fix + esforço/risco: #1 logs boot stdout, #3 --json vs --formato, #4 subagente "local agent" sem nome, #5 transcript 404 pós-deploy. Onda 1 (#3,#1 backend) / Onda 2 (#4,#5 frontend exige browser)
- [Engenharia de Memoria — Reranker + Qualidade na escrita](2026-06-10-engenharia-memoria-rerank-write-quality.md) — continuidade D3/D4 pos-PAD-CTX: FRENTE 1 porta o rerank Voyage (padrao SPED ja provado) p/ memory_search (aceite: precision@4 > 0.673 no harness); FRENTE 2 valida WHEN/DO na escrita + backfill Haiku das 109 longas sem meta.do (40% do estore sem formato operativo)
- [Arquitetura de Contexto do Boot do Agente Web — Plano + Roadmap (PAD-CTX)](2026-06-09-arquitetura-contexto-boot-agente.md) — implementa `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md`; 8 fases (F0 quick-wins env vars/deny-list → F7 features opt-in); origem: estudo 2026-06-09 (16 findings + matriz 38 itens + red-team 4 críticos em `relatorios/estudo_contexto_boot_2026-06-09/`)
- [Arquitetura de Conhecimento — Jeito X (memorias + agents + skills)](2026-06-11-arquitetura-conhecimento.md) — ciclo de vida com trilhos de promocao (memoria→reference NOVO) + enforcement nas duplicacoes (lint por subagente, registro G0xx, path deterministico X1/X2, merge versionado X5); Item 0 + F0/F1 (~1 mes) + F2 gated + NAO-FAZER N1-N10; origem: estudo 2026-06-11 (12 agentes em `relatorios/arquitetura_x_2026-06-11/`)
- [CarVia: Consistência de Comissões — Ajustes (débito/crédito) + data de corte](2026-06-15-carvia-comissao-ajustes.md) — alteração/cancelamento de cte_valor de CTe já comissionado gera CarviaComissaoAjuste (delta) abatido no próximo fechamento do vendedor (FK usuarios); bloqueia total negativo; criação só com data final; 11 tasks TDD (helpers flush-only); ✅ EXECUTADO (na main; +editar_comissao; migration par .sql/.py em scripts/migrations/)
- [CarVia — Viabilidade no Mapa/Embarque + Cidade no Export NF + Resultado por Frete](2026-06-19-carvia-viabilidade-rateio-frete.md) — plano TDD das 3 entregas CarVia da spec de 2026-06-19 (viabilidade de frete no mapa/embarque, cidade no export de NF, resultado por frete com rateio por moto); spec par `2026-06-19-carvia-viabilidade-rateio-frete-design.md`
- [CarVia: Migracao de conferencia de Sub para Frete (Escopo C)](2026-04-14-carvia-frete-conferencia-migration.md)
- [Remessa VORTX — Injeção Direta no Odoo](2026-04-15-remessa-vortx-odoo-injection.md)
- [Agent SDK 0.1.60 Features — Implementation Plan](2026-04-16-agent-sdk-0160-features.md)
- [Memory System Redesign — 3 Channels Implementation Plan](2026-04-16-memory-system-redesign.md)
- [Pessoal F1 — Busca Global e Filtros Avançados](2026-04-20-pessoal-f1-busca-filtros.md)
- [HORA — Transferência entre Filiais + Registro de Avaria — Implementation Plan](2026-04-22-hora-transferencia-e-avaria.md)
- [Chat In-App — Implementation Plan](2026-04-23-chat-inapp.md)
- [HORA Peças — Implementation Plan](2026-05-05-hora-pecas.md)
- [Motos Assaí — Plano 1: Foundation + Cadastros (Implementation Plan)](2026-05-07-motos-assai-foundation.md)
- [Motos Assaí — Plano 2A: Parser VOE + Pedido + Compra Motochefe](2026-05-07-motos-assai-pedido-compra.md)
- [Motos Assaí — Plano 2B: Recibo Motochefe + Recebimento físico](2026-05-07-motos-assai-recibo-recebimento.md)
- [Motos Assaí — Plano 3: Pipeline de Saída + Polish](2026-05-07-motos-assai-saida-polish.md)
- [Motos Assaí Skills + Agente Implementation Plan](2026-05-08-motos-assai-skills-agents.md)
- [Onboarding Tours HORA + Motos Assaí — Implementation Plan](2026-05-08-onboarding-tours-hora-assai.md)
- [Big Bang Callsites List — Status Legados](2026-05-12-bigbang-callsites-list.md)
- [Motos Assaí — Fase 1 (Fundação) Implementation Plan](2026-05-12-motos-assai-fase1-fundacao.md)
- [Motos Assaí — Fase 2-3 (Carregamento Service + UI) Implementation Plan](2026-05-12-motos-assai-fase2-3-carregamento.md)
- [Motos Assaí — Fase 4 (NF + Divergências + Cancelar NF) Implementation Plan](2026-05-12-motos-assai-fase4-nf-divergencias.md)
- [Motos Assaí — Fase 5 (Substituir chassi + UI vincular NF + Parser CCe) Implementation Plan](2026-05-12-motos-assai-fase5-auxiliares.md)
- [Relatorio Final — Subagent UI Enrichment](2026-05-14-subagent-ui-enrichment-RELATORIO.md)
- [Subagent UI Enrichment Implementation Plan](2026-05-14-subagent-ui-enrichment.md)
- [Auditor SPED ECD — Subagente + 4 Skills + Embeddings de Regras Normativas](2026-05-16-auditor-sped-ecd.md)
- [Ajuste de Inventário NACOM/LF — Plano de Implementação](2026-05-17-ajuste-inventario-nacom-lf.md)
- [Transferência de Saldo entre Códigos (Odoo) — Implementation Plan](2026-05-22-transferencia-saldo-codigos-odoo.md)
- [Relatório de Confronto de Inventário — Implementation Plan](2026-05-26-relatorio-confronto-inventario-plan.md)
- [Onda 0 — Fundação Física (entidade de passo + registry descritivo) Implementation Plan](2026-05-30-onda-0-fundacao.md)
- [Plano — A3 como GATE DE REGRESSÃO (fiel à spec)](2026-05-31-a3-gate-regressao.md)
- [Plano — Fix A3: Judge Granular + SSL-drop na persistência](2026-05-31-fix-a3-judge-granular-ssl.md)
- [Inventário Cíclico — Plano enxuto de implementação](2026-05-31-inventario-ciclico-plan.md)
- [Onda 1 — Fundação Semântica (E↔D) Implementation Plan](2026-05-31-onda-1-quality-spine.md)
- [Onda 2 — Atuador de Planejamento (super-loop + VERIFY) Implementation Plan](2026-05-31-onda-2-planejador.md)
- [Onda 3 — Fechar o Flywheel + Ontologia Consultável Implementation Plan](2026-05-31-onda-3-flywheel-ontologia.md)
- [A4 — Promoção Automática de Diretriz (batch) — Implementation Plan](2026-06-01-a4-promocao-diretriz.md)
- [Capacitação do gestor-estoque-odoo p/ remessa FB→LF — Implementation Plan](2026-06-02-capacitacao-gestor-remessa-fb-lf.md)
- [Loop Corretivo Pessoal — a licao que adere](2026-06-02-loop-corretivo-pessoal.md) — memoria pessoal F1 (eixo G): gravar→reconciliar→promover→injetar-garantido→medir-outcome; resolve "expliquei e fez certo, depois errou de novo" (Marcus)
- [Roadmap — Evolucao da skill `gerindo-agente` para top-level](2026-06-03-evolucao-gerindo-agente.md) — skill -> superficie unica de gestao/introspeccao do Agente Web (ondas WRITE flywheel)
- [PAD-A Onda 4g — SSW + SELAGEM (registro de execucao)](2026-06-03-pad-a-onda-4g-ssw-selagem.md) — ultima sub-onda: SSW 309 docs + global-zero + promove C1/C7/C8 a block
- [consultando-venda-loja](2026-06-02-skill-consultando-venda-loja.md) — plano TDD da skill READ de vendas Lojas HORA (Onda F)
- [carregando-motos-assai](2026-06-02-skill-carregando-motos-assai.md) — plano TDD da skill READ+WRITE de carregamento Assai (Onda F)
- [Redesign consultar_sql — SQL-first](2026-06-04-redesign-consultar-sql-sql-first.md) — inverte a tool SQL do agente de tradutor NL→SQL (Generator Haiku que adivinha/trunca) para executor SQL-first + guard-rail determinístico; origem sessão #787
- [Text-to-SQL S0 — Gerador idempotente](2026-06-07-text-to-sql-S0-gerador-idempotente.md) — write-if-changed + ordenacao canonica + --check; mata poluicao de git ao regenerar 303 schemas; pre-req de S1/S2 (pacote MASTER 2026-06-07)
- [Text-to-SQL S1 — Progressive disclosure](2026-06-07-text-to-sql-S1-progressive-disclosure.md) — tool buscar_tabelas (intencao→tabela) + key_fields uteis + agrupamento por dominio; o Opus deixa de adivinhar nome de tabela (pacote MASTER 2026-06-07)
- [Text-to-SQL S2 — Qualidade de schema](2026-06-07-text-to-sql-S2-qualidade-schema.md) — overlay de curadoria (descricao/regra/hint) que sobrevive a regeneracao; prioriza por uso; eleva precisao (pacote MASTER 2026-06-07)
- [Text-to-SQL S3 — Nucleo de geracao](2026-06-07-text-to-sql-S3-nucleo-geracao.md) — Opus autor unico + correcao deterministica/Haiku-testado + separar permissao (DML/tabela/campo) de geracao; fixes F1-F7 (pacote MASTER 2026-06-07)
- [Roadmap de correções do Agente — sessão #787](2026-06-04-roadmap-correcoes-agente-787.md) — rastreador dos 7 achados (P1 TMPDIR feito · P2/P3 Fix B próximo · P4 idioma/schema · P5 frustração · P6 summary · P7 judge/verifier de entrega); ponto de partida da próxima sessão
- [Refactor & Governança do Prompt do Agente](2026-06-04-refactor-governanca-prompt-agente.md) — corrige system_prompt (862 linhas, 6.5x doc defasada) + preset (cutoff errado, dedup) + injeções; 6 fases gated por golden dataset; meta-problema = adição sem poda; G1/G4 corrigidos por verificação de premissa
- [Transferência de Estoque (Odoo) — tela admin 3 modos](2026-06-06-transferencia-estoque-odoo-ui.md) — plano TDD: generaliza TransferenciaSaldoCodigoService (transferir_v2) + reusa átomos transfer.py; tela admin-only com painel A/B/C ao vivo, autocomplete, simular→confirmar; 9 tasks
- [Lojas HORA — Notificação WhatsApp (NF/pedido)](2026-06-06-hora-tagplus-notificacao-whatsapp.md) — plano TDD executado (H1-H4): model+migration hora_45, service (grupo+DM vendedor, PDF DANFE via ApiClient), gatilhos NF aprovada+pedido confirmado (fila hora_nfe), tela require_hora_perm; 16 testes. Reusa send_whatsapp (buffer base64)
- [Aprendizado por Efetividade de Skill — Fase 1](2026-06-07-aprendizado-efetividade-skills-fase1.md) — plano TDD 15 tasks: avaliador pos-sessao (janela ancorada + funil estagio0/Haiku/Sonnet), 3 ramos (lembrete-usuario auto / lembrete-todos+codigo via Inbox de Aprovacao que conserta o directive_promotion shadow sem UI), injecao cirurgica no PreToolUse, tabela agent_skill_effectiveness; separacao de competencias (avaliador descreve o problema, Claude Code resolve)
- [Teams Melhorias — Identidade, Falante do Turno, Entrega Proativa](2026-06-10-teams-melhorias.md) — 4 fases aprovadas (Rafael 2026-06-10): A identidade AAD+email+codigo de pareamento (mata fantasma MD5-do-nome), B falante do turno em grupos (registry por sessao corrige closure congelada dos hooks), C proactive messaging via continue_conversation (mata timeout 5/10 min do polling) + heartbeat, D extras (truncamento 3800, fila, /bot/execute morto, reset, upload)
- [Aprendizado ad-hoc → skill (Fase 2)](2026-06-12-aprendizado-adhoc-fase2.md) — plano TDD 10 tasks: parser de transcript cru (claude_session_store via SQL sync), filtro Bash substantivo, extracao problema/motivo via Haiku, embedding voyage + cluster pgvector 0.85, disparo com thresholds 3/5 + bypass gap nomeado + caps + dedup suggestion_key, job RQ + gatilho pos-sessao; debito Teams ja fechado (ede93a0e2)
- [Limpeza de deprecados — HANDOFF proxima sessao (Onda C restante + Onda E)](2026-06-15-limpeza-handoff-proxima-sessao.md) — estado vivo + guia de retomada do worktree `worktree-limpeza-deprecados` (A/B/D + C-parcial feitas, 6 commits); proxima sessao = Onda C restante (~58 docs raiz via Apendice A do spec) + Onda E (PROGRESSIVE_DISCLOSURE_PATTERN + INDEX); deferidos (ml_models/app/database/cruft local/text_to_SQL follow-up/Onda F) registrados
- [Frente Martha (financeiro) — skills + correcoes (HANDOFF)](2026-06-18-frente-martha-financeiro-handoff.md) — roteiro multi-sessao das 6 demandas da Martha (raiz = logica financeira presa no web -> skill thin-wrapper). Feito: skill F recebiveis (delegada auditor-financeiro `ab7cd1887`) + design/fundacao skill A pagamentos-lote (`16dc513f7`). Proximos: 1=codigo A (preview->WRITE FB/LF+6 guards+reverter+validacao ao vivo; SC/CD=Fase2 cross-company conta-ponte 26868), 2=fix parser OFX virgula-BR (`ofx_parser_service.py:89`), 3=skill B dedup OFX, 4=skill C diff extrato, 5=estender razao-geral (D), 6=Sendas captura (E). Abertos: EMPRESA_MAP bug, Grafeno parado jan/2026
