<!-- doc:meta
tipo: scratch
-->
# Resiliência da Emissão de CTe no SSW — Backlog do Exercício (Coleta 3)

> **Criado em**: 2026-06-19
> **Objetivo**: Tornar o fluxo de emissão automática de CTe no SSW (CarVia) resiliente a
> "qualquer vírgula fora do padrão", dirigido por casos reais da **coleta 3** (filial GIG / RJ,
> placa ARMAZEM). Trabalho a 4 mãos: emitir 1 a 1 → ver o erro → tratar no código → seguir.
> **Arquivos do fluxo**: `.claude/skills/operando-ssw/scripts/emitir_cte_004.py` (Camada 1),
> `app/carvia/services/documentos/ssw_emissao_service.py` (Camada 2),
> `app/carvia/workers/ssw_cte_jobs.py` (orquestrador worker).

## ✅ Status de fechamento (sessão 2026-06-19)

**Coleta 3 EMITIDA por completo** — 25 NFs: 3 já estavam FATURADAS (5461/5487/5506) +
**22 CTe emitidos e AUTORIZADOS nesta sessão** (CTRC GIG-456 a GIG-480), todos com **frete
conferido** (`vTPrest` == informado) e **cStat=100**. 3 saíram com frete errado, foram
**cancelados + reemitidos corretos** (39092→GIG-468, 39101→GIG-469, 39111→GIG-480).

**Resiliência implementada no código nesta sessão:**
- **R1** cidade não atendida (402): detecta + classifica (`CIDADE_NAO_ATENDIDA`); runner pula e lista p/ cadastro.
- **R5** cliente bloqueado: desbloqueio robusto (polling da tela 389 até 18s + separa desbloqueio↔emissão com `retentar`).
- **R7** frete-da-tabela por *fallback* de simular: remove `errorpanel` (força clique nativo) + aborta antes de gravar se cair no fallback.
- **R8** frete-da-tabela por avisos extras: **lê `VALOR A RECEBER` do resumo e aborta se ≠ informado** — blindagem final, nunca grava frete errado.
- **Performance (parcial)**: helper `_esperar` (espera condicional) substituiu os sleeps fixos grandes; SEFAZ 20→6s. Emissão completa **~90s → ~40s/NF**.

**Pendente p/ PRÓXIMA SESSÃO** (refactor estrutural — ver seção PERFORMANCE):
1. **Sessão reutilizável** — 1 login por LOTE (não relogar/reabrir a 004 a cada NF).
2. **Baixar XML na 101 interna** do `emitir_cte` (elimina a 2ª sessão Playwright/NF) — extrair função de download de `consultar_ctrc_101` (linhas 218-412); o `emitir_cte` precisa de `accept_downloads=True` no context.
Alvo ~15-20s/NF; atacam a "abertura de tela" (gargalo real apontado pelo dono).

## Arquitetura de tratamento de erro (2 camadas)

- **Camada 1** = `emitir_cte_004.py`, loop de avisos pós-simulação (linhas ~737-1043): tenta
  RESOLVER automaticamente os avisos HTML do SSW. Qualquer aviso não reconhecido → `NAO_RECONHECIDO`
  → `break` → `ctrc_num=None` → emissão vira ERRO.
- **Camada 2** = `SswEmissaoService.detectar_erro_ssw` + `ERROS_SSW` (regex) + `ERROS_SSW_MENSAGENS`:
  varre o JSON do resultado DEPOIS e CLASSIFICA a falha numa mensagem amigável (operador corrige
  manual e retenta). NÃO resolve, só nomeia.

## Decisões fechadas (negócio)

- **Cidade não atendida (402)** → **CADASTRAR na 402** (opção 2 do aviso), NÃO usar tipo FEC.
- **Via de execução**: rodar `emitir_cte_004.py` **local, 1 a 1** (emite CTe fiscal REAL — SSW não
  tem ambiente de teste). Dry-run obrigatório antes do real.
- **Entregável**: **exportar o XML** de cada CTe emitido.

## Achados CONFIRMADOS (com evidência) — tratar primeiro

| # | Gap | Evidência | Camada 1 | Camada 2 | Sev |
|---|-----|-----------|----------|----------|-----|
| R1 | ✅ **TRATADO 2026-06-19** — Painel "Cidade X/UF não é atendida (opc 402)". Aparece DURANTE o preenchimento (5518/MG, trava o frete) OU pós-simular (5524/SP, caía em `NAO_RECONHECIDO`→"Falha na emissao"). Decisão: cadastrar na 402 (não FEC). | NF 5518 (MG) + NF 5524 LENÇÓIS PAULISTA/SP ao vivo. | ✅ Fix `emitir_cte_004.py`: branch no loop detecta o painel, extrai cidade/UF e aborta com `cidade_nao_atendida=True` (sem cair em genérico). Runner PULA a NF e lista p/ cadastro. *Cadastro 402 segue manual.* | ✅ `CIDADE_NAO_ATENDIDA` (regex+msg `ssw_emissao_service`) | TRATADO |
| R2 | **Sem guard anti-duplicata por chave de NF.** `preparar_emissao` só checa mutex de emissão PENDENTE/EM_PROCESSAMENTO; nada impede re-emitir NF que já tem CTe. | Coleta 3: NFs 5461/5487/5506 já têm CTe FATURADO (CTe-411/416/430) mas seguem como linhas da coleta. | n/a | ❌ | **Crítico (fiscal)** |
| R3 | **Falso-erro por SSL drop**: CTe é emitido+autorizado mas marcado ERRO → retry duplicaria. | `carvia_emissao_cte`: "CT-e 161 foi emitido e autorizado... marcado ERRO" (prod). | n/a | parcial | **Crítico (fiscal)** |
| R4 | **Estado "pronto para gravar" não reconhecido quando o frete não calcula** (sem rota/cidade/tabela): tela volta ao form 004 com `Frete:` vazio, loop não acha "Gravar" → `NAO_RECONHECIDO` → "Falha na emissao" genérica. | 9× "Falha na emissao" + `NAO_RECONHECIDO body=CTRC anterior:\nPlaca Coleta:\nFrete:` (5 casos) em prod. | ❌ | ❌ (sem classe) | **Alto** |
| R5 | ✅ **RESOLVIDO 2026-06-19** — Desbloqueio de cliente (389/ssw1105). Era bug de TIMING (script checava em 3s; a 389 carrega ~6-10s → `DESBLOQUEIO_SEM_TARGET` falso) + após gravar, tentava re-simular/gravar NA 389 → `TypeError at concluindo`. | NF 5537 CEZINHA (.3) ao vivo (CTe GIG-457-0). | ✅ Fix `emitir_cte_004.py`: (a) polling pela 389 até 18s (inline OU nova page); (b) separar desbloqueio↔emissão — após gravar Transportar=S retorna `retentar=True` e o orquestrador re-emite do zero (2ª passada não vê bloqueio). | ✅ | RESOLVIDO |

> **Pendente (worker produção, não-bloqueante p/ exercício)**: `ssw_cte_jobs.emitir_cte_ssw_job` ainda NÃO trata `retentar=True` — em produção o desbloqueio grava Transportar=S mas a emissão fica ERRO; operador retentaria (2ª dá certo). Adicionar re-enfileiramento 1x quando `resultado.retentar`. (O wrapper local `emitir_uma.py` já faz o retry.)
| R6 | **`detectar_erro_ssw` não classifica FOB nem cidade-402** — viram "Falha na emissao" inútil ao operador. | `ERROS_SSW` (ssw_emissao_service.py:25-34) sem padrão FOB/402. | n/a | ✅ 402 resolvido (R1) | Médio |
| R7 | ✅ **TRATADO 2026-06-19** — **CTe sai com FRETE DA TABELA (maior) quando o clique de simular cai no fallback JS** (`lnk_env`, porque o overlay `errorpanel` bloqueia o ► nativo). O caminho nativo preserva o frete informado; o fallback recalcula. | NF 39092 (saiu 1567,73 vs 850) e 39101 (748,23 vs 600) — `SIMULAR_CLICK:lnk_env`. CTe 462/464 cancelados+reemitidos OK. | ✅ Fix `_clicar_simular`: remove `errorpanel` antes do clique nativo + flag `simular_fallback` → **aborta antes de gravar** (retentar) se cair no fallback. | n/a | **Crítico (fiscal)** |
| R8 | ✅ **TRATADO 2026-06-19** — **CTe sai com FRETE DA TABELA (menor) mesmo usando native, quando há avisos EXTRAS** (2+ "Continuar" genéricos recalculam e o override se perde; reaplicar falha pois o campo fica oculto no resumo). | NF 39111 MONTES CLAROS (saiu 533,74 vs 600, TAB GENERICA, 2× `CONTINUAR_GENERICO`). CTe 471 cancelado. | ✅ Fix: **salvaguarda de leitura do resumo** — lê `VALOR A RECEBER` e ABORTA (retentar) se ≠ informado. Blindagem final independente da causa. | n/a | **Crítico (fiscal)** |

> **Salvaguardas de frete (defesa em profundidade, `emitir_cte_004.py`)**: (1) remover `errorpanel` força o clique nativo; (2) abortar se simulação caiu no fallback; (3) **ler `VALOR A RECEBER` do resumo e abortar se ≠ informado**. O runner faz retry 1x e PARA se algum frete divergir pós-emissão. Resultado: **nunca grava CTe com frete errado**.

## PERFORMANCE (gap aberto pelo dono 2026-06-19) — ~3 min/NF é lento demais

Medido no lote real: **~3,0 min/NF**. Causas e plano (alvo ~1,5 min/NF):

| Gargalo | Custo | Fix | Ganho | Status |
|---------|-------|-----|-------|--------|
| **2 sessões Playwright/NF** — `emitir_cte` abre a 101 interna (linha ~1520) mas NÃO baixa o XML (só lê onclicks); o runner abre 2ª sessão inteira (`consultar_ctrc_101`: novo browser + novo login) só p/ baixar | ~40-60s/NF | Extrair `baixar_xml_dacte(popup, output_dir, download_info, …)` de `consultar_ctrc_101` (lógica linhas 218-412) e chamá-la na 101 interna do `emitir_cte`; runner deixa de chamar a 2ª. Beneficia tbm o worker (Fase B redundante) | **~35%** | ⏳ pendente |
| **43 `asyncio.sleep` fixos (170s no código)** — folgados (chave 10s×2, gravar 12s, SEFAZ 20s, simular 8s) | ~40-60s/NF | Trocar os do caminho feliz por espera condicional (poll do campo/estado) — sai assim que pronto | **~15-20%** | ⏳ pendente |
| **Login do zero a cada NF** | ~12s/NF | Reusar 1 sessão Playwright p/ o lote (maior refactor) | — | futuro |

## Catálogo de candidatos (workflow `mapa-resiliencia-cte-ssw`)

> Fase Descobrir (6 lentes adversariais) mapeou **74 pontos**; a verificação/síntese caiu em
> rate-limit temporário do servidor (re-sintetizar via resume quando estabilizar:
> `Workflow({scriptPath: ".../mapa-resiliencia-cte-ssw-wf_b66596fd-4a5.js", resumeFromRunId: "wf_b66596fd-4a5"})`).
> Abaixo os slugs agrupados — **verificação ainda pendente** (alguns podem ser falso-positivo).

**Captura CTRC / falso-erro / duplicata (P0):** popup-fechou-perde-ctrc-e-sefaz · ctrc-capture-define-sucesso · ctrc-falso-positivo-regex-dialog · regex-ctrc-anterior-formato-fragil · ctrc-gravado-mas-101-falha-cte-orfao · retry-sem-anti-duplicata-por-nf · mutex-nao-cobre-operacao-existente · stuck-em-processamento-mutex-deadlock · ssl-retry-esgotado-raise-no-finally-perde-status

**SEFAZ / autorização (P0):** sucesso-sem-autorizacao-sefaz · fatura-437-sobre-cte-nao-autorizado · envio-007-fire-and-forget · status-fila-007-capturado-nunca-usado · sefaz-rem-envia-todos-digitados · rejeicao-sefaz-deixa-pre-ctrc-orfao · 101-nao-acha-cte-recem-emitido · inconclusiva-sefaz-enviado-mensagem-enganosa

**Avisos / loop Camada 1:** cidade-nao-atendida-402-sem-branch · rota-gig-destino-nao-cadastrada-403 · destino-sem-unidade-ssw-nao-validado · fob-cif-tomador-nao-aceita · valor-minimo-frete-nao-tratado · seguro-averbacao-rctrc-nao-tratado · icms-isencao-reducao-cfop-especial · max-avisos-6-corta-fluxo-sem-gravar · nao-reconhecido-vira-falha-generica · fallback-continuar-cego-grava-errado · carta-correcao-pre-simulacao-fragil · email-branch-acento-obrigatorio · gnre-pode-mascarar-bloqueio · peso-real-invalido-resimula-perde-frete · frete-reconfirm-quebra-resumo-gera-inconclusiva

**Input / validação:** frete-valor-zero-ou-negativo-aceito · cnpj-tomador-nao-valida-digito-verificador · chave-acesso-44-mas-nao-numerica · uf-emitente-nula-sem-fallback · filial-derivada-de-uf-emitente-errada-fracionado · sem-item-com-modelo-moto-id-medidas-vazias · modelo-moto-inativo-bloqueia-lote · data-vencimento-silenciosamente-descartada

**Fatura 437 / infra:** fatura-437-falha-silenciosa · fatura-437-grid-match-flexivel-seleciona-cte-errado · fatura-437-cnpj-tomador-divergente · except-amplo-importacao-engole-erro-real · consulta-101-fill-via-interpolacao-string · job-na-fila-high-roda-em-worker-concorrente · sleeps-fixos-timing-sefaz

## Coleta 3 — progresso da emissão (22 pendentes)

> 3 já FATURADAS (NÃO re-emitir): 5461→CTe-411, 5487→CTe-416, 5506→CTe-430.

| nf_id | NF | Cidade/UF | Motos | Frete R$ | Status emissão |
|-------|----|-----------|-------|----------|----------------|
| 534 | 5518 | JOÃO PINHEIRO/MG | 12 JOY SUPER | 1.800 | ✅ EMITIDO GIG-456-1 (CTe 451 AUTORIZADO, R$1.800, CFOP 6932+GNRE) · XML entregue |
| 535 | 5524 | LENÇÓIS PAULISTA/SP | 5 DOT | 1.350 | pendente |
| 536 | 5537 | BOA ESPERANÇA/MG | 3 DOT | 750 | ✅ EMITIDO GIG-457-0 (Autorizado, R$750) · cliente CEZINHA desbloqueado · XML entregue |
| 537 | 39079 | PATROCÍNIO/MG | 6 FANTON | 1.500 | pendente |
| 538 | 39086 | CRUZ ALTA/RS | 4 FANTON | 1.000 | pendente |
| 539 | 39087 | ITAPECERICA/MG | 1 FANTON | 300 | pendente |
| 540 | 39089 | URUAÇU/GO | 5 FANTON | 850 | pendente |
| 541 | 39092 | GOIANÉSIA/GO | 5 FANTON | 850 | pendente |
| 542 | 39099 | JOÃO PINHEIRO/MG | 2 FANTON | 300 | pendente |
| 543 | 39101 | CONSELHEIRO PENA/MG | 2 BIG TRI | 600 | pendente |
| 544 | 39103 | PRAIA GRANDE/SP | 3 JET + 1 FANTON | 1.000 | pendente |
| 545 | 39106 | UBERABA/MG | 1 X15 | 300 | pendente |
| 546 | 39108 | SOROCABA/SP | 3 X11 MINI | 600 | pendente |
| 547 | 39111 | MONTES CLAROS/MG | 2 FANTON | 600 | pendente |
| 548 | 39121 | GOIANÉSIA/GO | 5 X12 | 850 | pendente |
| 549 | 39131 | CAMAQUÃ/RS | 4 FANTON | 1.000 | pendente |
| 550 | 39132 | UBERABA/MG | 2 X12 | 600 | pendente |
| 551 | 39135 | SANTA CRUZ DO SUL/RS | 3 BIG TRI | 900 | pendente |
| 552 | 39138 | SÃO JOSÉ DO RIO PRETO/SP | 5 JET | 1.250 | pendente |
| 553 | 39141 | PAÇO DO LUMIAR/MA | 14 (mix) | 4.200 | pendente |
| 554 | 39143 | MURIAÉ/MG | 1 FANTON | 270 | pendente |
| 555 | 39153 | UNAÍ/MG | 4 FANTON | 1.000 | pendente |
