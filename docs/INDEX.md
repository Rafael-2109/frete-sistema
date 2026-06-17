<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Indice mestre da documentacao (docs/)
> **Papel:** ponto de entrada da documentacao tecnica do projeto (arvore `docs/`). So ponteiros (paths a partir da raiz do repo).

## Padrao de artefatos e processo (PAD-A)
- `docs/superpowers/INDEX.md` — planos, specs e baselines do fluxo PAD-A

## Operacoes Odoo / estoque
- `docs/inventario-2026-05/INDEX.md` — ciclo de inventario NACOM/LF/CD/FB
- `docs/industrializacao-fb-lf/README.md` — remessa de industrializacao (indice no proprio README)

## Roteirizacao (Ver no Mapa)
- `docs/roteirizacao/ESTADO.md` — estado vivo da ampliacao da roteirizacao (3 fases; fonte unica de progresso)

## Agente (blueprint)
- `docs/blueprint-agente/INDEX.md` — indice do blueprint do agente (BLUEPRINT_MESTRE, eixos A-G, criticas)

## Modulos
- `docs/pallet/MAPEAMENTO_TELAS_PALLET.md` — pallet: mapeamento de telas
- `docs/pallet/AJUSTES_REALIZADOS_PALLET.md` — pallet: ajustes realizados
- `docs/pallet/TRABALHO_AUTONOMO_PALLET.md` — pallet: trabalho autonomo
- `docs/pallet/UI_DETALHADA_PALLET.md` — pallet: UI detalhada
- `docs/hora/INVARIANTES.md` — Lojas HORA: invariantes
- `docs/hora/CHECKLIST_TAGPLUS_GO_LIVE.md` — Lojas HORA: checklist go-live TagPlus

## Importador de pedidos (redes Sendas/Tenda)
- `docs/planos/PLANO_IMPORTADOR_PEDIDOS_REDES.md` — plano do importador de pedidos das redes
- `docs/NOVO_PROCESSO_SENDAS.md` — novo processo Sendas (4 etapas, `app/portal/sendas/`)
- `docs/RASTREABILIDADE_DADOS_SENDAS.md` — rastreabilidade de dados Sendas
- `docs/RESUMO_EXECUTIVO_RASTREABILIDADE.md` — resumo executivo de rastreabilidade
- `docs/TECHNICAL_SPEC_SENDAS.md` — technical spec Sendas

## Pedido de venda no Odoo
- `docs/ESTUDO_CRIAR_PEDIDO_VENDA_ODOO.md` — estudo criar pedido de venda Odoo (`app/pedidos/integracao_odoo/`)
- `docs/ODOO_CONTAS_RECEBER_EXPLICACAO_CAMPOS.md` — Odoo contas a receber (campos)

## Avulsos
- `docs/BI_MODULO.md` — modulo de BI (`app/bi/`)
- `docs/RELATORIO_AVALIACAO_360_AGENTE_2026-05-29.md` — relatorio de avaliacao 360 do agente (2026-05-29)

## Onda C — docs de modulo reorganizados (2026-06-15)

### Carteira de pedidos
- docs/carteira/arquitetura-cards-separacao.md — Mapa (arquivo:linha) das funcoes JS de cards de separacao na carteira agrupada + duplicacoes workspace x view compacta
- docs/carteira/metodos-js-carteira.md — Mapa de referência dos métodos JS do front-end da Carteira (lote-manager, workspace, agrupada)
- docs/carteira/refatoracao-js-2025-01.md — Refatoracao JS da Carteira (jan/2025): formatacao, seguranca e notificacoes centralizadas em modulos util
- docs/carteira/calculo-estoque-frontend-2025-01.md — Por que o calculo de projecao de estoque da Carteira Simples virou 100% front-end (anti-duplicacao).
- docs/carteira/melhorias-importacao-excel.md — Melhorias da importacao de multiplos Excel da carteira: resiliencia, API Receita, modal, erros (accordion pendente)
- docs/carteira/migracao-preseparacaoitem.md — Mapeamento de usos de PreSeparacaoItem e estrategia de migracao p/ Separacao status='PREVISAO' via adapter
- docs/carteira/botoes-verificacao-agendamento.md — Diferenca entre os 2 botoes de verificacao de agendamento da carteira (Verificar Agendas vs Todos Pendentes)
- docs/carteira/SOLUCAO_TRUNCAMENTO_OBSERVACOES.md — Truncamento automatico de observ_ped_1 (VARCHAR 700) ao gravar em Separacao: solucao e 7 pontos no codigo
- docs/carteira/bug-date-type-estoque-simples.md — Bug de tipo de data (date vs str) que pode zerar entradas de producao na projecao de estoque_simples

### Embarques
- docs/embarques/botao-confirmacao-agendamento.md — Badge de status de agendamento por item de embarque (modal) e sync p/ Separacao/Entrega/Agendamento
- docs/embarques/sincronizacao-totais-embarque.md — Sincronizacao automatica dos totais do Embarque (peso/pallet/valor) ao visualizar; NF validada > Separacao

### Fretes e cotacao
- docs/fretes/mapa-calculos-frete.md — Mapa de onde/como o frete e calculado: motor CalculadoraFrete, simulador unificado e modulos consumidores
- docs/fretes/cte-complementar.md — Conceito, modelo (ConhecimentoTransporte) e fluxo de CTe complementar vinculado a Despesas Extras
- docs/cotacao/mapa-fluxos-cotacao.md — Mapa dos 6 fluxos do modulo de cotacao (frontend -> rotas Flask -> backend de calculo de frete)

### Comercial
- docs/comercial/permissoes-comerciais.md — Permissoes comerciais: vendedor ve so equipes/vendedores liberados; admin/gerente veem tudo. Modelo+regras.
- docs/comercial/PLANO_OTIMIZACAO_COMERCIAL.md — Plano historico de otimizacao de performance do modulo comercial, reconciliado com o codigo real

### Manufatura e producao
- docs/manufatura/melhorias_requisicoes_compras.md — Melhorias no vinculo Requisicao-Pedido, projecao de estoque e data de necessidade (modulo manufatura)
- docs/manufatura/OTIMIZACOES_NECESSIDADE_PRODUCAO.md — Otimizacoes de performance da tela de Necessidade de Producao (batch, cache, indices) + correcao TTL 30s
- docs/manufatura/OTIMIZACOES_PERFORMANCE_PROJECAO.md — Estrategia de cache em memoria do ServicoProjecaoEstoque (projecao de estoque de componentes)

### Motochefe (Lojas HORA) — carga inicial
- docs/motochefe/carga-inicial.md — How-to de importacao Excel do MotoChefe (fases 1-6: cadastros, produtos, pedidos e historico)
- docs/motochefe/carga-inicial-readme.md — How-to: importar cadastros e pedidos historicos em massa no modulo Motochefe (4 fases, via tela web)
- docs/motochefe/exemplos-carga-inicial.md — Dados de exemplo e roteiro de teste da carga inicial (importacao em 3 fases) do modulo Motochefe
- docs/motochefe/extrator_cnpj.md — How-to: usar ExtratorCNPJ (service + script CLI) p/ extrair CNPJ de planilhas Excel (3 padroes)

### Odoo (integracao)
- docs/odoo/circuit_breaker.md — Padrao Circuit Breaker para chamadas Odoo: estados, config, monitoramento e cenarios de falha
- docs/odoo/scheduler_sincronizacao.md — Runbook: operacao, config e diagnostico do scheduler de sincronizacao incremental Odoo (APScheduler).
- docs/odoo/relacao_requisicao_pedido.md — Por que pedidos mostram requisicoes sendo N:N: a granularidade real e linha/produto (1:1) via tabela pivot
- docs/odoo/verificacao_pedidos_excluidos.md — Deteccao de pedidos EXCLUIDOS no Odoo pelo scheduler de sync (exclusao em lote VSC/VCD/VFB)

### Portal e workers
- docs/portal/REDIS_QUEUE_GUIA.md — How-to de instalacao, config, operacao e troubleshooting do Redis Queue (RQ) do portal Atacadao

### Rastreamento GPS (app Capacitor)
- docs/rastreamento/capacitor-readme.md — App nativo de rastreamento GPS (Capacitor): quick start, build dev/prod e troubleshooting.
- docs/rastreamento/capacitor-setup.md — Setup, build (APK/iOS), deploy e troubleshooting do rastreamento GPS background via Capacitor
- docs/rastreamento/guia-build-app-android.md — Guia de build (dev/prod), instalacao e deploy do app Android de rastreamento GPS (Capacitor) Nacom.
- docs/rastreamento/instalacao-rastreamento-gps.md — How-to de instalacao/config/troubleshooting do rastreamento GPS de embarques (LGPD, QR Code, pings)
- docs/rastreamento/configurar-qrcode.md — Como configurar RASTREAMENTO_BASE_URL p/ o QR Code de rastreamento abrir no celular (local e produção)

### Dados e queries
- docs/dados/queries_comparacao_pesos.md — Queries SQL prontas (PSQL/Render) p/ auditar divergencia de peso: faturamento_produto vs cadastro_palletizacao

### Onboarding
- docs/onboarding.md — Guia de onboarding de devs: setup codebase/MCP, skills, subagentes e regras do projeto

## Arquivados (legado morto — `docs/_deprecated/`, fora da auditoria)
- `docs/_deprecated/` — specs/planos nunca construidos ou superseded (CAMPOS_CRIAR_PEDIDO_ODOO, ESPECIFICACAO_IMPORTADOR_PEDIDOS_TENDA, IMPLEMENTATION_PLAN_SENDAS, IMPORTACAO_DADOS, ROADMAP_LICITACAO_FRETE). Ver `docs/_deprecated/README.md`.
