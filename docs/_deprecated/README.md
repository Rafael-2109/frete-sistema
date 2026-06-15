# docs/_deprecated/ — legado morto arquivado

> Zona **fora da auditoria PAD-A** (`ignore_globs: **/_deprecated/**`). Conteudo
> mantido apenas para historico. **NAO seguir** — descreve features nunca
> construidas ou ja superseded.

Arquivados na PAD-A Onda 4g (2026-06-03) apos avaliacao vivo/morto contra o
codebase (13 docs/raiz; 8 vivos carimbados, estes 5 mortos arquivados):

| Arquivo | Motivo (evidencia verificada) |
|---------|-------------------------------|
| `CAMPOS_CRIAR_PEDIDO_ODOO.md` | Rascunho com placeholders `_____`; superseded por `docs/ESTUDO_CRIAR_PEDIDO_VENDA_ODOO.md` (citado pelo codigo em `app/pedidos/integracao_odoo/service.py:4`). |
| `ESPECIFICACAO_IMPORTADOR_PEDIDOS_TENDA.md` | Status "Aguardando Implementacao"; extractores comentados como futuros (`app/pedidos/leitura/processor.py:53-54`); tabela `portal_tenda_produto_depara` nunca criada. |
| `IMPLEMENTATION_PLAN_SENDAS.md` | Arquivos-alvo deletados no commit `e81146c5c` (transicao p/ export manual); endpoint proposto nunca criado. |
| `IMPORTACAO_DADOS.md` | Scripts-nucleo inexistentes; `ProcessadorFaturamentoTagPlus` descartado (`app/integracoes/tagplus/FLUXO_REAL_IMPORTACAO_TAGPLUS.md:217`). |
| `ROADMAP_LICITACAO_FRETE.md` | Auto-declara "Planejado (nao iniciado)"; zero codigo (`app/despacho/` inexistente; `LoteDespacho`/`OfertaFreteiro` = 0 hits). |

## Onda C — docs one-shot da raiz (limpeza-deprecados, 2026-06-15)

23 docs `.md` da raiz arquivados apos re-verificacao adversarial (1 agente por doc: re-grep na hora + Q3 contra o codigo atual). Subpastas: `motochefe/` (relatorios/planos de implementacao concluidos) e `raiz-oneshot-2026-06/` (setups/snapshots one-shot ja executados). Inventario verificado: `docs/superpowers/specs/2026-06-15-limpeza-deprecados-design.md` (Apendice A).

| Arquivo | Motivo (evidencia verificada) |
|---------|-------------------------------|
| `CHANGELOG_INDUSTRIALIZACAO_E_STANDBY.md` | Changelog one-shot historico de 2025-01-29; mudancas foram aplicadas e o codigo evoluiu alem do escopo documentado (adicionou 'exportacao' e 'venda-industrializacao'). |
| `CHECKLIST_PORTAL.md` | Checklist temporario de deploy inicial do portal de agendamento; feature em producao, scripts referenciados nao existem. |
| `COMO_RODAR_RUPTURA_WORKERS.md` | Documenta addon RQ-worker de ruptura nunca integrado ao sistema ativo; ruptura usa `ruptura_api.py` e `ruptura_api_sem_cache.py` (sincronos, sem Redis Queue). Superseded: `app/carteira/CLAUDE.md`. |
| `DOCUMENTACAO_CTE_IMPLEMENTACAO.md` | Pre-implementation spec de 13/11/2025 superado pela implementacao real (divergiu em campos e escopo); orfao. Superseded: `app/fretes/models.py` (ConhecimentoTransporte, L618) + `app/odoo/services/cte_service.py` + `app/fretes/cte_routes.py`. |
| `INSTRUCOES_ATUALIZAR_FRETE.md` | Runbook one-time para bug `optante_simples` ja corrigido; script `atualizar_embarque_frete_manual.py` referenciado nao existe mais. |
| `INSTRUCOES_DEPLOY_FINAL.md` | Guia de deploy one-shot concluido em out/2025; arquitetura evoluiu (parcelamento_service.py e modelos ParcelaPedido/ParcelaTitulo removidos). Superseded: `app/motochefe/documentacao/FLUXO_PARCELAMENTO_FIFO.md`. |
| `INSTRUCOES_FRONTEND_FORM.md` | Instrucao de refatoracao one-shot cujas 13 alteracoes foram integralmente executadas. Superseded: `app/templates/motochefe/vendas/pedidos/form.html`. |
| `MELHORIAS_CTES_NFS_DASHBOARD.md` | Registro one-shot de sprint concluida em 13/11/2025; implementacao integrada ao codigo e evoluiu alem do descrito. Superseded: `app/fretes/CLAUDE.md`. |
| `MUDANCAS_FOB_MONITORAMENTO.md` | Changelog one-time de 13/10/2025 incorporado ao codigo: filtro FOB removido e logica FOB adicionada em `sincronizar_entregas.py` (L80-96 e L255-272). |
| `PROGRESS-chat-inapp-2026-04-23.md` | Notebook de sessao 100% concluido (25/25 tasks), sem citacoes vivas. SoT do modulo chat e `app/chat/CLAUDE.md`. Superseded: `app/chat/CLAUDE.md`. |
| `README_RUPTURA_ASYNC.md` | Descreve implementacao (ruptura_api_async.py, ruptura-estoque-async.js, ruptura_jobs.py) que nao existe no codebase. Superseded: `app/carteira/CLAUDE.md`. |
| `RELATORIO_CORRECAO_TIMEZONE.md` | Relatorio de incidente (19/11/2025) supersedido: as 6 correcoes pendentes foram aplicadas e `app/utils/timezone.py` foi criado. Superseded: `app/utils/timezone.py`. |
| `SISTEMA_ESTOQUE_TEMPO_REAL.md` | Arquitetura de tabelas-cache com triggers (EstoqueTempoReal, MovimentacaoPrevista) substituida por ServicoEstoqueSimples (queries diretas). Superseded: `app/estoque/api_tempo_real.py` + `app/estoque/services/estoque_simples.py`. |
| `TAGPLUS_INTEGRACAO.md` | Setup one-shot com URLs OAuth2 erradas e arquivos inexistentes; supersedido pelos docs em `app/integracoes/tagplus/`. Superseded: `app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md`. |
| `V2_QUERY_CLEANUP.md` | Checklist one-shot de remocao de dead code v2 — parte executada, parte pendente; o proprio doc instrui auto-delete ao final. Superseded: `.claude/references/ROADMAP_SDK_CLIENT.md`. |
| `investigacao-status-inconsistente-2025-01.md` | Investigacao pontual (pedido VCD2563375) sem implementacao resultante; companion scripts nao existem; numeros de linha defasados. |
| `motochefe/CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md` | Relatorio one-shot de out/2025 com divergencias vs codigo atual (ParcelaPedido/ParcelaTitulo nao criados, parcelamento_service.py inexistente). Superseded: `app/motochefe/documentacao/FLUXO_PARCELAMENTO_FIFO.md`. |
| `motochefe/PLANO_IMPLEMENTACAO_MOTOCHEFE.md` | Plano de implementacao one-shot de out/2025 com etapas concluidas. Superseded: `app/motochefe/documentacao/IMPLEMENTACAO_CONCLUIDA.md`. |
| `motochefe/STATUS_FINAL_IMPLEMENTACAO.md` | Snapshot de progresso (07/10/2025, 85%) superseded pelo CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE. Superseded: `motochefe/CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md`. |
| `raiz-oneshot-2026-06/CHROME_WINDOWS_INSTRUCOES.md` | Setup Chrome/WSL one-shot; scripts auxiliares (executar_migracao_protocolo.py, testar_chrome_wsl.py) nao existem e a migracao ja foi executada. Superseded: `chrome_wsl_universal.bat`. |
| `raiz-oneshot-2026-06/DIAGRAMA_FLUXO_AGRUPADOS.md` | Analise de refatoracao one-shot parcialmente executada (ETAPA 1 ja aplicada: globals removidos, funcoes mortas inexistentes). |
| `raiz-oneshot-2026-06/RASTREAMENTO_PRODUCAO.md` | Snapshot de debugging de 2025 (campo `producao_hoje`); os 3 problemas foram resolvidos no codigo atual. |
| `raiz-oneshot-2026-06/README_INSTALACAO_ENTREGAS_RASTREADAS.md` | Guia de instalacao one-shot; scripts auxiliares nao existem mais (tabela gerida pelo ORM). Superseded: `app/rastreamento/models.py` (EntregaRastreada, L246). |
