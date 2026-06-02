# Routing de Skills

**Ultima Atualizacao**: 30/05/2026 (51 skills invocaveis — `faturando-odoo` adicionada ao inventario; estendida em 2026-05-26 v19+: `escriturando-odoo` virou ABRANGENTE com 7 atomos sobre `account.move`+DFe/PO/invoice (`buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida`, `escriturar_dfe`, `gerar_po_from_dfe`, `preencher_po`, `confirmar_po`, `criar_invoice_from_po`); compostos via FLUXOS L3 1.2.1 caminho A (DFe ja veio via SEFAZ) e 1.2.2 caminho B (DFe ausente — upload XML da SAIDA); dispatch `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x` no orchestrator decide caminho A vs B via `buscar_dfe`; wrapper V1 STRICT `criar_recebimento_orchestrado` LF→FB deprecado v20+; `operando-picking-odoo` ganhou atomo `preencher_lotes_picking` (Skill 5 atomo S2 reusado pelos fluxos L3 1.2.x); `criar_picking_entrada_destino_manual` DEPRECATED docblock (museum vivo ate canary v20+); 555 baseline pytest Odoo. Em 2026-05-25 v15a: `operando-picking-odoo` ganhou 3 atomos inter-company para Skill 8 (`criar_picking_inter_company` codifica D-OPS-3 tracking='none' · `validar_picking_inter_company` fluxo F5b completo + G018 peso/volumes · `criar_picking_entrada_destino_manual` ETAPA F com G023 company_id forcado + idempotencia origin); +19 pytest verdes (42→61 stock_picking_service); centralizadas constants ETAPA F (`PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `ACOES_ENTRADA_DESTINO_MANUAL`, `LOCATION_ORIGEM_ENTRADA_INDUSTR`) em `app/odoo/constants/picking_types.py`; smoke PROD validou D-OPS-3 detection em 6 cods v14a-ops; 435 baseline pytest Odoo. Adicionada em 2026-05-25 v14b: `auditando-cadastro-fiscal-odoo` (PRE-FLIGHT perfil V1 'inventario'; sub-skill delegada pela Skill 8 'faturando-odoo' v15+; cobre G017/G018/G035/G014 + D-OPS-2/3; service `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` ~430 LOC; 14 testes pytest verdes; smoke PROD em 6 cods v14a-ops detectou 2 G014 + 1 D-OPS-3 em 987ms). 2026-05-24 v6: `planejando-pre-etapa-odoo` (READ Odoo + WRITE banco local — planejador da pre-etapa D007 do inventario CD/FB; substitui NFs inter-filial CD↔FB R$ 32,9 mi + INDISPONIBILIZAR_* R$ 60,5 mi por transferencias INTERNAS na company + residual minimo CFOP 5152; 4 modos: planejar/propor/listar-onda/aprovar-onda; service `app/odoo/estoque/scripts/pre_etapa.py` capinado de services/; hash sha256 anti-replay no workflow de aprovacao; 19 testes pytest verdes — 13 originais + 6 helpers novos). 2026-05-24 v5: `operando-mo-odoo` (WRITE cancelar Manufacturing Order single ou batch; service novo `app/odoo/estoque/scripts/mo.py`; guard G-MO-01 furo contabil — bloqueia consumo>0; idempotencia validada AO VIVO em MO state=cancel). 2026-05-24 v3: `operando-picking-odoo` (WRITE cancelar/validar/devolver picking; capina StockPickingService para `app/odoo/estoque/scripts/picking.py`; invariante G019/G020 fechada no codigo — re-leitura de state pos-button_validate; novo atomo `devolver` cria stock.return.picking idempotente). 2026-05-24 v2: `transferindo-interno-odoo` (WRITE transferencia interna intra-empresa: lote→lote mesma loc OU loc→loc mesmo lote; composicao de ajustar_quant 2x com delta_esperado propagado, G021/G022/G027 codificados). 2026-05-23: `ajustando-quant-odoo` (WRITE 1 stock.quant), `operando-reservas-odoo` (WRITE cirurgia/cancelamento de pickings com MLs orfas), `consultando-quant-odoo` (READ ao vivo no Odoo — auditoria pos-WRITE). 2026-05-16: `parseando-sped-ecd`, `auditando-sped-contabil`, `auditando-sped-vs-manual`, `comparando-sped-ground-truth` — pipeline de auditoria SPED ECD usado exclusivamente pelo subagent `auditor-sped-ecd`)

**REGRA**: Use a skill MAIS ESPECIFICA. `descobrindo-odoo-estrutura` e ULTIMO RECURSO.

---

## Passo 1: Identificar o CONTEXTO

| Contexto | Sinais | Proximo passo |
|----------|--------|---------------|
| CONSULTA LOCAL (CarteiraPrincipal, Separacao, etc.) | Campos locais, queries SQL, regras de negocio | -> Consultar REFERENCES (sem skill) |
| CONSULTA ANALITICA (agregacoes, rankings, distribuicoes) | "quantos por estado", "top 10", "valor total por", comparacoes | -> `consultando-sql` |
| OPERACAO ODOO (API, modelos, integracoes) | NF, PO, picking, Odoo, pagamento, extrato | -> Passos 2 e 3 abaixo |
| DESENVOLVIMENTO FRONTEND | Criar tela, dashboard, CSS, template | -> `frontend-design` |
| COTACAO DE FRETE | "qual preco", "quanto custa frete", "tabelas para", "cotacao" | -> `cotando-frete` |
| VISAO 360 PRODUTO | "resumo do produto", "producao vs programado", "visao completa do produto" | -> `visao-produto` |
| EXPORTAR/IMPORTAR DADOS | Gerar Excel, CSV, processar planilha | -> `exportando-arquivos` / `lendo-arquivos` |
| LER DOCUMENTOS (Word, bancarios, OFX) | Analisar `.docx`, `.ret`, `.rem`, `.cnab`, `.ofx` | -> `lendo-documentos` |
| SAUDE DO BANCO | "health check", "indices nao usados", "queries lentas", "cache hit rate", "vacuum" | -> `diagnosticando-banco` |
| SSW consulta (sistema transportadora) | "como fazer no SSW", "opcao NNN", "passo a passo", "MDF-e", "CTe no SSW", "CarVia faz X?" | -> `acessando-ssw` |
| SSW escrita (cadastrar/criar no SSW) | "cadastre unidade CGR", "cadastrar cidades MS", "criar unidade parceira no SSW" | -> `operando-ssw` |
| PORTAL ATACADAO (automacao web Hodie Booking) | "portal Atacadao", "site do Atacadao", "Hodie Booking", "entrar no portal", "imprimir protocolo no site", "agendar no portal" + OBRIGATORIO mencionar portal/site/Hodie | -> `operando-portal-atacadao` |
| CARVIA (frete subcontratado) | "operacoes CarVia", "subcontratos pendentes", "cotar subcontrato", "faturas CarVia", "conferencia transportadora" | -> `gerindo-carvia` |
| FINANCEIRO (reconciliacao, auditoria, baixas) | "inconsistencias", "SEM_MATCH", "reconciliar extrato", "auditoria Local vs Odoo", "titulos divergentes" | -> Subagente `auditor-financeiro` |
| CUSTO DE FRETE (divergencia, CTe, despesas extras) | "divergencia CTe", "custo real frete", "conta corrente transportadora", "despesas extras", "frete % receita" | -> Subagente `controlador-custo-frete` |
| RECEBIMENTO (pipeline, DFEs, picking) | "DFE bloqueado", "primeira compra", "match NF x PO", "picking nao valida", "quality check" | -> Subagente `gestor-recebimento` |
| DEVOLUCOES (NFD, retornos, descarte) | "devolucoes pendentes", "status NFD", "De-Para confianca", "descarte vs retorno", "produtos devolvidos" | -> Subagente `gestor-devolucoes` |
| ESTOQUE/PRODUCAO (ruptura, projecao, programacao — READ) | "vai faltar", "estoque comprometido", "producao vs programada", "giro estoque", "estoque parado" | -> Subagente `gestor-estoque-producao` |
| ESTOQUE ODOO (WRITE — ajustar quant, transferir, faturar IC, cancelar MO) | "ajusta saldo do quant", "ajuste +/- residuo", "cria saldo do lote X", "ajuste por planilha", "zera quant fantasma", "corrige reserva orfa", "limpa ML orfa", "cancela picking", "valida picking pendurado em assigned", "re-valida picking false-positive G019", "devolve picking (NF errada)", "cancela 854 fantasmas >7d", "transfere lote A para lote B", "move saldo MIGRACAO -> lote canonico", "manda saldo pra Indisponivel", "Pre-Producao -> Estoque", "Indisponivel -> Estoque", "consolidar grafia MIGRACAO/MIGRAÇÃO", "cancela MO 19713", "cancela MOs zumbi antigas FB", "limpa MOs draft/confirmed sem consumo", "cancela MO travada" | -> Subagente `gestor-estoque-odoo` (orquestra todas as skills WRITE de estoque — fluxos>>skills, NUNCA invocar skill atomica direto) |
| ESTOQUE ODOO (READ AO VIVO — quant/ML/picking) | "saldo restante apos ajuste", "sobrou saldo em loc !=indisp?", "quants em lote MIGRACAO", "auditoria pos-WRITE", "snapshot ao vivo Odoo" | -> `consultando-quant-odoo` |
| ESTOQUE ODOO (PRE-FLIGHT cadastro fiscal — auditoria antes de SEFAZ) | "audita cadastro fiscal", "pre-flight para faturar", "valida NCM/barcode/weight", "checa duplicacao pipeline", "lote vencido com saldo", "limpa barcodes invalidos" | -> `auditando-cadastro-fiscal-odoo` (sub-skill READ-only + opcional WRITE de G035; perfil V1 'inventario'; delegada pela Skill 8 faturando-odoo v15+) |
| PERFORMANCE LOGISTICA (entregas, ranking, KPIs) | "entregas atrasadas", "lead time", "ranking transportadoras", "mes a mes", "em transito" | -> Subagente `analista-performance-logistica` |
| SENTRY (erros, issues, monitoring) | "issues do Sentry", "erros em producao", "bugs no Sentry", "resolver issue", "root cause analysis", "500 errors", "Seer" | -> `consultando-sentry` |
| LOCALIZAR ROTA/TELA/API | "onde fica X?", "qual URL de Y?", "quais APIs de Z?", "como acesso tela de W?" | -> `mcp__routes__search_routes` (MCP tool, agente web) / Grep+Glob (Claude Code) |
| AGENTE (memorias, sessoes, diagnosticos) | "memorias do usuario", "sessoes anteriores", "health score agente", "knowledge graph", "consolidar memorias", "padroes aprendidos" | -> `gerindo-agente` |
| PROBLEMA COMPLEXO (investigacao, root cause) | "resolver problema complexo em...", "investigar bug em...", "por que X esta...", "analisar modulo completo", "mapear dependencias", "root cause analysis" | -> `resolvendo-problemas` |
| LOJAS HORA — ESTOQUE (motos eletricas B2C) | "quantas motos tenho?", "quanto de <modelo>?", "em transito", "estoque por loja" — APENAS no Agente Lojas HORA | -> `consultando-estoque-loja` |
| LOJAS HORA — RASTREAR CHASSI | "cade o chassi XYZ?", "historico do chassi", "essa moto foi vendida?", "em que pedido veio" — APENAS no Agente Lojas HORA | -> `rastreando-chassi` |
| LOJAS HORA — ACOMPANHAR PEDIDO | "meu pedido X ja chegou?", "pedidos pendentes", "faltam quantas motos?" — APENAS no Agente Lojas HORA | -> `acompanhando-pedido` |
| LOJAS HORA — CONFERENCIA | "como esta a conferencia?", "quantos chassis faltam conferir?", "tem divergencia?" — APENAS no Agente Lojas HORA | -> `conferindo-recebimento` |
| LOJAS HORA — PECAS FALTANDO | "pecas faltando?", "pecas pendentes", "chassi doador" — APENAS no Agente Lojas HORA | -> `consultando-pecas-faltando` |
| LOJAS HORA — CROSS-ENTIDADE (orquestra varias skills) | "como esta minha loja hoje?", "o que preciso fazer?", "resumo operacional" — APENAS no Agente Lojas HORA | -> Subagente `orientador-loja` |
| MOTOS ASSAÍ — ESTOQUE/PIPELINE | "quantas motos Q.P.A.?", "estoque Sendas", "pipeline Assaí", "quanto de SOL?" | -> `consultando-estoque-assai` |
| MOTOS ASSAÍ — RASTREAR CHASSI | "cadê chassi MZX...?", "histórico chassi Q.P.A." | -> `rastreando-chassi-assai` |
| MOTOS ASSAÍ — PEDIDOS/COMPRAS | "pedido VOE", "compra Motochefe MA-", "VOE Q.P.A." | -> `acompanhando-pedido-compra-assai` |
| MOTOS ASSAÍ — SAÍDA/NFs | "separações Assaí", "NF Q.P.A.", "match BATEU/DIVERGENTE" | -> `acompanhando-saida-assai` |
| MOTOS ASSAÍ — RECIBO MOTOCHEFE | "recibos pendentes Motochefe", "conferir recibo RM-", "wizard recebimento" | -> `conferindo-recibo-assai` |
| MOTOS ASSAÍ — EVENTOS WRITE | "registra montagem", "disponibiliza", "reverte", "separar chassi" | -> `registrando-evento-moto-assai` |
| MOTOS ASSAÍ — CARREGAMENTO (READ+WRITE) | "carregamentos em andamento", "iniciar/finalizar carregamento", "escanear chassi na carga", "reabre carregamento" | -> `carregando-motos-assai` |
| MOTOS ASSAÍ — CROSS-ENTIDADE | "como está operação Q.P.A.?", "resumo Motos Assaí" | -> Subagente `gestor-motos-assai` |

---

## Passo 2 (ODOO): Tem dado ESTATICO ja documentado?

| Preciso de... | Nao use skill, consulte diretamente: |
|---------------|--------------------------------------|
| ID fixo (company, picking_type, journal) | `.claude/references/odoo/IDS_FIXOS.md` |
| Conversao UoM (Milhar, fator_un) | `.claude/references/odoo/CONVERSAO_UOM.md` |
| Campos ja mapeados do Odoo | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| GOTCHAS conhecidos (timeouts, erros) | `.claude/references/odoo/GOTCHAS.md` |

Se a resposta esta no reference -> NAO usar skill.

---

## Passo 3 (ODOO): Arvore de Decisao de Skills

```
0. CONFIGURACAO ESTATICA ja documentada?
   |-- SIM -> consultou no Passo 2, PARAR
   |-- NAO -> continuar abaixo

1. RECEBIMENTO de compra?
   |-- Match NF x PO           -> validacao-nf-po
   |-- Split/Consolidar PO     -> conciliando-odoo-po
   |-- Vincular/desvincular PO ↔ NF  -> conciliando-odoo-po
   |-- Lotes/Quality Check     -> recebimento-fisico-odoo
   |-- Pipeline completo       -> ver odoo/PIPELINE_RECEBIMENTO.md

2. FINANCEIRO?
   |-- Baseline de extratos pendentes (formato travado 4 abas)     -> gerando-baseline-conciliacao
   |-- Criar pagamento / reconciliar extrato com cliente/fornecedor -> executando-odoo-financeiro
   |-- Transferencia interna entre bancos NACOM GOYA               -> conciliando-transferencias-internas
   |-- Exportar razao geral                                        -> razao-geral-odoo

3. DESENVOLVIMENTO de nova integracao?
   |-- Criar service/route/migration -> integracao-odoo

4. RASTREAMENTO de documento?
   |-- Rastrear NF, PO, SO, pagamento -> rastreando-odoo

5. ESTRUTURA desconhecida (ULTIMO RECURSO)?
   |-- Descobrir campos de modelo NOVO -> descobrindo-odoo-estrutura

6. ESTOQUE WRITE (alterar saldo/lote/quant no Odoo)?
   |-- Ajustar saldo de 1 quant (+/-, zerar, criar, resetar reserva) -> ajustando-quant-odoo
   |-- Transferir interno (lote↔lote / loc↔loc / MIGRA↔Indisp) -> transferindo-interno-odoo
   |-- Limpar MLs orfas / cirurgia em picking -> operando-reservas-odoo
   |-- Cancelar/validar/devolver picking generico (fantasma, G019 false-positive, NF errada) -> operando-picking-odoo
   |-- Cancelar MO single ou batch (guard G-MO-01 furo contabil; idempotencia) -> operando-mo-odoo
   |-- Planejar pre-etapa CD/FB D007 (READ Odoo + WRITE banco local; planejar/propor/listar/aprovar com hash anti-replay) -> planejando-pre-etapa-odoo
   |-- Escriturar ENTRADA inter-company (NF nossa, DFe via SEFAZ OU upload XML SAIDA) -> Skill 7 `escriturando-odoo` ABRANGENTE v19+ (7 atomos) compostos via FLUXO L3 1.2.1 (caminho A) ou 1.2.2 (caminho B); dispatch automatico via `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x`
   |-- Faturar SAIDA inter-company (pipeline A-F + recovery + SEFAZ via Playwright) -> orchestrator C3 `inventario_pipeline` (atual `faturamento_pipeline.py`; refator AP6 v20+ extrai Skill 8 ATOMICA L2) — invocavel via SKILL.md fachada `.claude/skills/faturando-odoo/SKILL.md` ou diretamente via `python -m app.odoo.estoque.orchestrators.faturamento_pipeline`

7. ESTOQUE READ AO VIVO (consultar Odoo, nao DB local)?
   |-- Saldo restante por (cod, empresa), agregado, filtros — auditoria pos-WRITE -> consultando-quant-odoo
   |-- Snapshot de quants por filtro versatil (com_lote, only_principal, etc.) -> consultando-quant-odoo
   |-- Auditar N pares (cod, empresa) classificando em zerado/so_indisp/com_saldo -> consultando-quant-odoo (atomo `auditar_pares`)

8. PRE-FLIGHT cadastro fiscal (auditoria antes de SEFAZ — Skill 8 v15+ delega)?
   |-- G017 NCM ausente, G035 barcode invalido, G018 weight=0 (warn), G014 lote vencido (warn) -> auditando-cadastro-fiscal-odoo --perfil inventario
   |-- D-OPS-2 duplicacao em pipeline ativo (cod+company em F5a..F5e) -> auditando-cadastro-fiscal-odoo --ciclo X
   |-- Auto-fix G035 (limpar barcode invalido) -> auditando-cadastro-fiscal-odoo --auto-corrigir-barcode --confirmar
```

---

## Desambiguacao (quando 2 skills parecem servir)

| Duvida entre... | Regra de desempate |
|-----------------|-------------------|
| rastreando vs executando-financeiro | READ/consultar -> rastreando. WRITE/criar/modificar -> executando |
| rastreando vs validacao-nf-po | Fluxo completo -> rastreando. Apenas Fase 2 match -> validacao |
| conciliando vs validacao-nf-po | Fase 3 (split/consolidar) -> conciliando. Fase 2 (match) -> validacao |
| integracao vs descobrindo | CRIAR novo service -> integracao. EXPLORAR modelo -> descobrindo |
| executando-odoo-financeiro vs conciliando-transferencias-internas | Extrato de cliente/fornecedor (CNPJ terceiro) -> executando-odoo-financeiro. Extrato NACOM GOYA/61.724.241 (propria empresa) com par espelhado em outro journal -> conciliando-transferencias-internas. Sinal: "is_internal_transfer", "NACOM GOYA no extrato", "transferencia entre bancos proprios" -> conciliando-transferencias-internas |
| gerando-baseline-conciliacao vs executando-odoo-financeiro | **Relatorio agregado** de pendentes por Mes x Journal (4 abas travadas) -> gerando-baseline-conciliacao. **Operacao** sobre linha individual (criar pagamento, reconciliar 1 extrato) -> executando-odoo-financeiro. Sinal: "atualizar baseline", "foto das conciliacoes", "extratos pendentes por mes" -> gerando-baseline-conciliacao. "reconcilie stmt X" -> executando-odoo-financeiro |
| gerando-baseline-conciliacao vs razao-geral-odoo | **Extratos pendentes** de conciliacao (account.bank.statement.line is_reconciled=False) -> gerando-baseline-conciliacao. **Razao geral contabil** (account.move.line com saldo acumulado) -> razao-geral-odoo. Sinal: "baseline", "pendentes" -> baseline. "razao geral", "balancete" -> razao |
| Nao sei qual skill Odoo usar | -> Subagente `especialista-odoo` (orquestra todas) |
| Teams tasks vs diagnostico agente | **TeamsTask** (status task, stale cleanup) → `consultando-sql` direto. **Sessoes/memorias Teams** (filtro `--channel teams`, flags) → `gerindo-agente`. **Teams SSO** (config, webhook) → dev manual |
| cotando-frete vs acessando-ssw | **Nacom** (industria, contrata frete) -> cotando-frete. **CarVia** (transportadora, vende frete) -> acessando-ssw. Sinal: "no SSW", "opcao NNN", "CarVia" -> SSW. Sem qualificador -> Nacom. Sinais adicionais CarVia: "parametros de frete" (opcao 062), "resultado CTRC" (opcao 101), "formacao de preco" (opcao 062/004) |
| cotando-frete vs gerindo-carvia | **Nacom** (cotacao outbound, tabela de frete da Nacom) -> cotando-frete. **CarVia** (cotacao subcontrato inbound, operacao + transportadora) -> gerindo-carvia. Sinal: "subcontrato", "operacao CarVia", "frete subcontratado" -> gerindo-carvia. "frete para Manaus", "pedido VCD" -> cotando-frete |
| gerindo-carvia vs gerindo-expedicao | **CarVia** (frete subcontratado, operacao inbound) -> gerindo-carvia. **Nacom** (separacao, embarque outbound) -> gerindo-expedicao. Sinal: "subcontrato", "fatura CarVia" -> gerindo-carvia. "separacao", "pedido VCD" -> gerindo-expedicao |
| acessando-ssw vs operando-ssw | **Consultar/entender** SSW -> acessando-ssw. **Executar/cadastrar/criar** no SSW -> operando-ssw. Sinal: "cadastre", "crie unidade", "inclua cidade" -> operando. "como funciona", "o que e", "passo a passo" -> acessando |
| gerindo-expedicao vs acessando-ssw | Estoque/separacao/embarque **Nacom** -> gerindo-expedicao. Romaneio/manifesto **SSW** -> acessando-ssw |
| monitorando-entregas vs acessando-ssw | Entrega rastreada no **sistema local** -> monitorando-entregas. Baixa/ocorrencia no **SSW** -> acessando-ssw |
| operando-portal-atacadao vs gerindo-expedicao | **Portal web** do Atacadao (imprimir, agendar, consultar saldo no site) -> operando-portal-atacadao. **Dados locais** do Atacadao (pedidos, separacao, estoque) -> gerindo-expedicao. Sinal: "portal", "site", "Hodie", "navegar" -> operando-portal-atacadao. Sem mencao ao portal -> gerindo-expedicao |
| operando-portal-atacadao vs monitorando-entregas | **Portal web** (verificar agendamento no site) -> operando-portal-atacadao. **Sistema local** (status entrega, NF, canhoto) -> monitorando-entregas. Sinal: "no portal", "no site" -> operando-portal-atacadao. Sem mencao -> monitorando-entregas |
| resolvendo-problemas vs ralph-wiggum | Problema **DESCONHECIDO** (investigar, root cause) -> resolvendo-problemas. Problema **CONHECIDO** + spec clara -> ralph-wiggum. Sinal: "por que X?", "investigar", "root cause" -> resolvendo-problemas. "implementar feature Y" -> ralph-wiggum |
| resolvendo-problemas vs diagnosticando-banco | **Saude** do banco (indices, vacuum, cache) -> diagnosticando-banco. **Bug** envolvendo banco (query errada, dados inconsistentes) -> resolvendo-problemas |
| resolvendo-problemas vs prd-generator | Problema que precisa **solucao** -> resolvendo-problemas. Feature que precisa **spec** antes de implementar -> prd-generator |
| consultando-sentry vs diagnosticando-banco | **Erros de aplicacao** (exceptions, 500, issues) -> consultando-sentry. **Saude do banco** (indices, vacuum, cache) -> diagnosticando-banco. Sinal: "issues", "Sentry", "bugs" -> sentry. "queries lentas", "indices" -> banco |
| consultando-sentry vs resolvendo-problemas | **Diagnostico rapido** (ver issue, stacktrace) -> consultando-sentry. **Investigacao profunda** (multi-arquivo, root cause complexo) -> resolvendo-problemas. Combinavel: sentry para dados + resolvendo-problemas para fix |
| auditor-financeiro vs especialista-odoo | **Reconciliacao/auditoria local** (CNAB, extrato, contas a receber/pagar) -> auditor-financeiro. **Operacao Odoo pura** (rastrear NF, criar pagamento) -> especialista-odoo. Sinal: "inconsistencia", "SEM_MATCH" -> auditor. "rastrear NF" -> especialista |
| auditor-financeiro vs controlador-custo-frete | **Contas a receber/pagar, extratos, reconciliacao** -> auditor-financeiro. **Frete, CTe, despesas extras, transportadoras** -> controlador-custo-frete. Sinal: "titulo", "extrato", "CNAB" -> auditor. "frete", "CTe", "transportadora" -> controlador |
| controlador-custo-frete vs cotando-frete | **Custo REAL** (valor_pago, divergencia CTe, despesas extras) -> controlador-custo-frete. **Cotacao TEORICA** (tabela de preco, estimativa) -> cotando-frete. Sinal: "quanto gastei", "divergencia" -> controlador. "quanto custa", "qual preco" -> cotando |
| controlador-custo-frete vs gestor-carvia | **Frete Nacom** (custo outbound, transportadora contratada) -> controlador-custo-frete. **Frete CarVia** (receita, subcontrato, fatura CarVia) -> gestor-carvia. Sinal: "CarVia", "subcontrato" -> gestor-carvia. Sem qualificador -> controlador |
| gestor-recebimento vs especialista-odoo | **Pipeline operacional** (status DFEs, bloqueios, troubleshooting) -> gestor-recebimento. **Execucao Odoo** (criar pagamento, reconciliar) -> especialista-odoo. Sinal: "DFE bloqueado", "picking falhou" -> recebimento. "executar no Odoo" -> especialista |
| gestor-devolucoes vs monitorando-entregas | **Devolucao** (NFD, retorno, descarte, De-Para) -> gestor-devolucoes. **Entrega** (status, canhoto, embarque) -> monitorando-entregas. Sinal: "devolucao", "NFD", "retorno" -> devolucoes. "entregou?", "canhoto" -> entregas |
| gestor-estoque-producao vs gerindo-expedicao | **Estoque/producao** (ruptura, projecao, giro, programacao) -> gestor-estoque-producao. **Expedicao** (separacao, agendamento, embarque) -> gerindo-expedicao. Sinal: "vai faltar", "producao" -> estoque. "separacao", "embarcar" -> expedicao |
| gestor-estoque-producao vs visao-produto | **Estoque agregado** (ruptura multi-produto, giro, parado) -> gestor-estoque-producao. **Produto individual 360** (cadastro+estoque+custo+faturamento) -> visao-produto. Sinal: "quais vao faltar" -> estoque. "tudo sobre palmito" -> visao |
| gestor-estoque-odoo vs gestor-estoque-producao | **WRITE** (ajustar saldo de quant, transferir entre lotes/locais, zerar fantasma, criar saldo, resetar reserva) -> gestor-estoque-odoo. **READ** (consultar/projetar estoque, ruptura, giro) -> gestor-estoque-producao. Sinal: "ajusta", "cria saldo", "zera fantasma", "transfere lote", "ajuste por planilha" -> WRITE (estoque-odoo). "vai faltar", "comprometido", "projecao" -> READ (estoque-producao) |
| ajustando-quant-odoo vs transferindo-interno-odoo (em construcao) | **1 quant** (ajustar saldo +/-, criar, zerar) -> ajustando-quant-odoo. **2 quants** (mover entre lotes/locais — origem -X, destino +X) -> transferindo-interno-odoo. Sinal: "ajusta", "+/-", "zera", "cria saldo" -> ajustando-quant. "transfere", "muda lote", "muda local", "realoca", "net-zero" -> transferindo-interno |
| analista-performance-logistica vs monitorando-entregas | **Agregado/ranking** (lead time medio, taxa sucesso, comparacao mes) -> analista-performance. **Individual** (NF 12345 entregou?) -> monitorando-entregas. Sinal: "ranking", "media", "percentual" -> performance. NF/numero especifico -> entregas |
| analista-performance-logistica vs controlador-custo-frete | **Performance entrega** (atraso, sucesso, lead time) -> analista-performance. **Custo frete** (valor, divergencia, despesa) -> controlador-custo-frete. Sinal: "atrasadas", "ranking" -> performance. "custo", "divergencia" -> controlador |
| consultando-estoque-assai vs gerindo-expedicao | **Motos Q.P.A.** (B2B Sendas) -> consultando-estoque-assai. **Pedidos/separação Nacom Goya** -> gerindo-expedicao |
| rastreando-chassi-assai vs rastreando-chassi (Hora) | **Q.P.A.** (assai_moto) -> rastreando-chassi-assai. **Lojas HORA** (hora_moto) -> rastreando-chassi |
| consultando-estoque-assai vs consultando-estoque-loja | **B2B Q.P.A. Sendas** -> consultando-estoque-assai. **B2C Lojas HORA** -> consultando-estoque-loja |

---

## Skills — Inventario Completo (51 invocaveis em `.claude/skills/`)

Cada skill tem `SKILL.md` em `.claude/skills/<nome>/`. `consultando-sql` e invocavel mas expoe data folder (schemas/queries) descoberto via filesystem.
`SKILL_IMPROVEMENT_ROADMAP.md` na raiz de `.claude/skills/` e DOC, nao skill (nao conta no inventario).

### MCP Custom Tools (agente web, in-process)
`mcp__sql__consultar_sql`, `mcp__memory__*` (6 tools), `mcp__schema__*` (2 tools),
`mcp__sessions__*` (2 tools), `mcp__render__*` (3 tools: logs, erros, status),
`mcp__routes__search_routes` (1 tool: busca semantica rotas)

### Skills Odoo (19)
`rastreando-odoo`, `executando-odoo-financeiro`, `descobrindo-odoo-estrutura`,
`validacao-nf-po`, `conciliando-odoo-po`, `recebimento-fisico-odoo`, `razao-geral-odoo`,
`conciliando-transferencias-internas`, `gerando-baseline-conciliacao`,
`ajustando-quant-odoo` (WRITE — usado pelo subagente `gestor-estoque-odoo`),
`transferindo-interno-odoo` (WRITE — transferencia interna intra-empresa; delega ajustar_quant×2),
`operando-reservas-odoo` (WRITE — cirurgia/cancelamento de reservas e MLs orfas),
`operando-picking-odoo` (WRITE — cancelar/validar/devolver picking generico; invariante G019/G020),
`operando-mo-odoo` (WRITE — cancelar MO single ou batch; guard G-MO-01 furo contabil),
`escriturando-odoo` (WRITE ABRANGENTE v19+ — 7 atomos sobre account.move+DFe/PO/invoice: `buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida` (upload XML autorizado da NF SAIDA), `escriturar_dfe`, `gerar_po_from_dfe` (fire-and-poll robo CIEL IT), `preencher_po`, `confirmar_po`, `criar_invoice_from_po`. Compostos via FLUXOS L3 1.2.1 (caminho A = DFe veio via SEFAZ) e 1.2.2 (caminho B = DFe ausente). Wrapper V1 STRICT `criar_recebimento_orchestrado` LF→FB deprecado v20+ (preservado p/ ETAPA E legacy do orchestrator). Cada atomo dry-run-first + idempotencia por campos Odoo.),
`planejando-pre-etapa-odoo` (READ Odoo + WRITE banco local — planejar/propor/listar/aprovar pre-etapa D007; hash sha256 anti-replay),
`consultando-quant-odoo` (READ-only AO VIVO — auditoria pos-WRITE, snapshots de quants),
`auditando-cadastro-fiscal-odoo` (PRE-FLIGHT V1 inventario — G017/G018/G035/G014 + D-OPS-2/3; READ-only + WRITE opcional G035 fix),
`faturando-odoo` (WRITE Skill 8 — faturamento de NF SAIDA inter-company: 5 atomos sobre account.move + orchestrator pipeline A-F + recovery + FLUXO L3 1.2.x; dry-run default, SEFAZ via Playwright IRREVERSIVEL exige confirmar_sefaz=True)

### Skills SSW (2)
`acessando-ssw`, `operando-ssw`

### Skills Portal Atacadao (1)
`operando-portal-atacadao`

### Skills CarVia (1)
`gerindo-carvia`

### Agente — gestao do sistema (1)
`gerindo-agente` (substitui `memoria-usuario` — deprecated)

### Sentry — monitoramento de erros (1)
`consultando-sentry` (MCP-first, 20 tools, Seer AI)

### Utilitarios compartilhados (11)
`exportando-arquivos`, `lendo-arquivos`, `lendo-documentos`, `consultando-sql`,
`cotando-frete`, `visao-produto`, `resolvendo-entidades`, `gerindo-expedicao`,
`monitorando-entregas`, `diagnosticando-banco`,
`gerando-artifact` (chat web APENAS — bundle.html via React+Tailwind+Parcel, renderizado em modal sandboxed)

### Skills Lojas HORA (5) — APENAS no Agente Lojas HORA (escopo isolado por `<loja_context>`)
`acompanhando-pedido` (pedidos HORA->Motochefe pendentes/faturados),
`conferindo-recebimento` (status conferencia em andamento/concluida),
`consultando-estoque-loja` (motos disponiveis por loja/modelo/chassi),
`consultando-pecas-faltando` (pecas faltando registradas + chassi doador),
`rastreando-chassi` (historico completo de UM chassi: pedido->NF->recebimento->venda)

### Skills motos_assai (7)
`consultando-estoque-assai`, `rastreando-chassi-assai`, `acompanhando-pedido-compra-assai`,
`acompanhando-saida-assai`, `conferindo-recibo-assai`, `registrando-evento-moto-assai`,
`carregando-motos-assai`

### Skills SPED ECD audit (4) — USO EXCLUSIVO do subagent `auditor-sped-ecd`
`parseando-sped-ecd` (parse Leiaute 9 streaming -> dict JSON em /tmp/),
`auditando-sped-vs-manual` (DSL YAML + busca semantica vs Manual ECD oficial),
`auditando-sped-contabil` (equacionalidade I155 + hierarquia I050 + cross-ref I250),
`comparando-sped-ground-truth` (diff estrutural vs SPED da contadora aprovado pela RFB).
NAO invocar do agente principal — fluxo orquestrado dentro do subagent.

> Skills dev (`frontend-design`, `skill-creator`, `ralph-wiggum`, `prd-generator`, `resolvendo-problemas`, `integracao-odoo`) NAO existem em `.claude/skills/` — sao invocaveis apenas via Claude Code global (fora do escopo deste inventario).
