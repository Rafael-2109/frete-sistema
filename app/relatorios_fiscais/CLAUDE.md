# Modulo Relatorios Fiscais — SPED ECD Centralizado

**Ultima atualizacao**: 2026-05-15
**Versao atual**: V1.8 (em construcao — mudancas nao commitadas em `sped_ecd_*.py`)
**Versao em PROD**: V1.7 (commit `dbfc5006`, 2026-05-14)

> Este CLAUDE.md cobre o modulo `app/relatorios_fiscais/`. Apesar de ser pequeno em LOC (~5K), ele consome SPED ECD (fiscal critico) com ciclo iterativo de correcoes contra PVA. Cada iteracao estoura contexto se ler PDF/SPED inteiros.

---

## CONTEXTO CRITICO PARA NOVA SESSAO

**SE voce esta abrindo este CLAUDE.md agora:**

1. **NUNCA leia o PDF de erros nem o SPED gerado inteiros** — consultar `SPED_ECD_PLANO.md` (este diretorio) com inventario das ~30 categorias de erro.
2. **NUNCA leia os 5 services completos de uma vez** (3653 linhas total) — usar offsets `Read(offset=N, limit=M)`.
3. **PROD usa fila `sped_ecd` no worker** — adicionar fila a worker_render.py + start_worker_render.sh (regra `~/.claude/CLAUDE.md`). JA REGISTRADA — bug historico SPED ECD V1.3 (commit `9d4e11d2`).
4. **Modo dev iterativo**: usar `scripts/sped_ecd/gerar_sped.py` (standalone, sem RQ).
5. **Manual ECD em PDF NAO precisa ser lido inteiro** — usar `manual_ecd/INDEX.md` e abrir so o bloco/registro relevante.

---

## TECH STACK ESPECIFICO

| Item | Detalhe |
|------|---------|
| Layout SPED | ECD Leiaute 9 (vigente desde 2021-12, AC 2020+) |
| Manual local refatorado | `manual_ecd/INDEX.md` (10 MDs indexados, ~160KB vs 2.9MB PDF) |
| Manual oficial (PDF online) | http://sped.rfb.gov.br/pasta/show/1569 |
| Encoding | Latin-1 puro (linha termina com `\r\n`) |
| Modalidade | Centralizada (`IND_CENTRALIZADA=0`) — 1 arquivo unico |
| Companies consolidadas | `[1, 3, 4]` = FB matriz + SC + CD (CNPJ raiz 61.724.241) |
| Company NAO consolidada | `5` (LA FAMIGLIA — raiz 18.467.441 — ECD propria) |
| Periodo padrao testes | 01/07/2024 a 31/12/2024 |
| Fila RQ | `sped_ecd` (60min timeout) |
| Output S3 | `bucket/sped_ecd/{user_id}/{ano}/sped_ecd_*.txt` (retencao 90d) |
| Output local dev | `/home/rafaelnascimento/SPED_ECD_NACOM_GOYA_*.txt` (70MB tipico para 6 meses) |

---

## ARQUITETURA — 5 SERVICES

| Arquivo | LOC | Responsabilidade |
|---------|-----|------------------|
| `services/sped_ecd_service.py` | 486 | Orquestrador — sequencia blocos, escreve BytesIO, gerencia S3 |
| `services/sped_ecd_constantes.py` | 247 | IDs Odoo, mapeamentos account_type→COD_NAT/referencial, signatarios |
| `services/sped_ecd_blocks.py` | 1180 | Geradores por bloco (1 funcao por registro/grupo) |
| `services/sped_ecd_data.py` | 1052 | Extracao Odoo XML-RPC (plano contas, saldos, lancamentos) |
| `services/sped_ecd_validator.py` | 688 | Validacao pre-PVA — ~30 regras estruturais e de negocio |
| `workers/sped_ecd_worker.py` | 258 | Job RQ assincrono (chama service, valida, S3) |
| `routes.py` | 579 | Form + status + download (Blueprint `relatorios_fiscais`) |
| `services/razao_geral_service.py` | ~370 | Razao Geral (relatorio fiscal separado, sem relacao com SPED ECD) |

**Total modulo SPED ECD**: ~3911 LOC (services + worker + script standalone)

---

## MAPEAMENTO BLOCO SPED → FUNCAO GERADORA (blocks.py)

| Registro | Funcao | Linha |
|----------|--------|-------|
| 0000, 0001, 0007, 0990 | `construir_bloco_0()` | 226 |
| 0150 (participantes) | `construir_0150()` | 344 |
| I001, I010, I030 | `construir_bloco_I_abertura()` | 304 |
| I050 + I051 + I052 (intercalados) | `construir_I050_com_I051()` | 404 |
| I050 isolado (DEPRECATED) | `construir_I050()` | 372 |
| I051 isolado (DEPRECATED) | `construir_I051()` | 478 |
| I100 (CCUS) | `construir_I100()` | 508 |
| I150 + I155 (saldos mensais) | `construir_I150_I155()` | 527 |
| I200 + I250 (lancamentos, generator) | `construir_I200_I250()` | 586 |
| I350 + I355 (encerramento) | `construir_I350_I355()` | 675 |
| I990 | `construir_I990()` | 715 |
| J001 | `construir_J001()` | 727 |
| J005 + J100 (Balanco BP) | `construir_J005_J100()` | 801 |
| J005 + J150 (DRE) | `construir_J005_J150()` | 934 |
| J800 (notas explicativas RTF) | `construir_J800()` | 1027 |
| J900 (termo encerramento) | `construir_J900()` | 1059 |
| J930 (signatarios) | `construir_J930()` | 1081 |
| J990 | `construir_J990()` | 1134 |
| 9001, 9900, 9990, 9999 | `construir_bloco_9()` | 1146 |

**Helpers criticos:**
- `ContadorRegistros` (classe, blocks.py:183) — conta registros durante streaming para 9900 correto via `.emit(registro)`
- `calcular_saldos_hierarquicos(balanco, plano)` (blocks.py:735) — propaga saldos analiticas→sinteticas via cod_sup. **Resultado usado por J100 + dispara codes_aglutinacao do I052**
- `remover_acentos()` (blocks.py:67) — Unicode→Latin-1 puro
- `formatar_registro(campos)` (blocks.py:114) — monta `|c1|c2|...|`
- `formatar_valor(valor, casas)` (blocks.py:133) — monetario virgula
- `formatar_data(d)` (blocks.py:147) — date → DDMMAAAA
- `formatar_dt_alt(create_date, dt_ini)` (blocks.py:163) — DT_ALT do I050, nunca > inicio periodo

---

## DADOS EXTRAIDOS — data.py

**Entry points (chamados pelo service.py):**

| Funcao | Linha | Retorna |
|--------|-------|---------|
| `buscar_dados_matriz(conn)` | 85 | res.company id=1 + IBGE |
| `buscar_plano_contas_consolidado(conn, companies)` | 158 | Lista consolidada por code |
| `buscar_centros_custo_consolidados(conn, companies)` | 702 | account.analytic.account (V1.8: nao usado) |
| `buscar_participantes_periodo(conn, ini, fim)` | 752 | res.partner (V1.5 Opcao A: nao chamado) |
| `calcular_saldos_periodicos_mensais(conn, ini, fim, id_to_code, companies)` | 335 | dict mensal para I150/I155 |
| `calcular_balanco_consolidado(conn, fim, plano, id_to_code, companies, ini)` | 504 | BP com saldo inicial (V1.6) |
| `calcular_dre_consolidado(conn, ini, fim, plano, id_to_code, companies)` | 588 | DRE para J150 |
| `calcular_saldos_resultado_encerramento(conn, fim, plano, id_to_code, companies)` | 634 | I355 (so 31/12) |
| `stream_lancamentos_consolidados_v11(...)` | 878 | Generator de lancamentos para I200/I250 |

**Modelos Odoo consultados:**

| Modelo | Uso | Campos CIEL IT especificos |
|--------|-----|---------------------------|
| `res.company` | matriz (FB) | `l10n_br_cnpj`, `l10n_br_razao_social`, `l10n_br_ie`, `l10n_br_im`, `l10n_br_nire`, `l10n_br_municipio_id` |
| `l10n_br_ciel_it_account.res.municipio` | codigo IBGE | `codigo_ibge` (V1.8: trocado de `l10n_br_base.municipio.l10n_br_ibge_code` que nao existe) |
| `account.account` | plano contas | `l10n_br_conta_referencial` (I051), `l10n_br_cod_nat` (COD_NAT I050) |
| `account.analytic.account` | CCUS | (V1.8: nao usado — `EMITIR_CCUS_SPED=False`) |
| `account.move.line` | saldos + lancamentos | via `read_group` |
| `account.move` | lista de moves do periodo | (V1.6: pre-fetch para chunking correto) |
| `res.partner` | 0150 | (V1.5: nao chamado) |

**Internal helpers:**
- `_buscar_paginado()` (data.py:41) — search_read com ID-cursor (evita truncamento silencioso)
- `_gerar_hierarquia_sintetica(plano_analiticas)` (data.py:253) — gera sinteticas para cada prefixo de code
- `_read_group_balance(conn, domain, with_dc, companies)` (data.py:439) — abstrai read_group de account.move.line por account_id
- `_extrair_distribuicao_ccus(distrib, id_to_code_ccus)` (data.py:663) — extrai CCUS de analytic_distribution (V1.8: nao usado)
- `_construir_lancamento_v11(num, lines, id_to_code, ccus, partner_code)` (data.py:995) — monta dict de lancamento

---

## CONSTANTES CRITICAS (constantes.py)

| Constante | Valor | Uso |
|-----------|-------|-----|
| `COMPANY_MATRIZ_ID` | 1 | FB |
| `COMPANIES_ECD` | [1, 3, 4] | scope consolidacao |
| `COMPANY_LF_ID` | 5 | LA FAMIGLIA (ECD propria) |
| `CNPJ_MATRIZ` | `'61724241000178'` | campo 0000 |
| `LEIAUTE_VERSAO` | `'9.00'` | campo I010 |
| `COD_PLAN_REF` | `'1'` | 1=PJ Lucro Real — dispara I051 obrigatorio |
| `IND_ESC` | `'G'` | G=Diario Completo |
| `IND_CENTRALIZADA` | `'0'` | 0=Centralizada |
| `IDENT_MF` | `'N'` | Moeda funcional (BUG HISTORICO: era 'M' confundindo Matriz, V1.7 corrigiu) |
| `EMITIR_CCUS_SPED` | `False` | V1.8: I100 nao emite, I250 sem CCUS |
| `QUEUE_NAME` | `'sped_ecd'` | fila RQ |
| `JOB_TIMEOUT` | `'60m'` | RQ |
| `CONTADOR_CPF` | `'41832597890'` | Tamiris Salles |
| `CONTADOR_CRC` | `'1SP041472'` | IND_CRC |
| `CONTADOR_NUM_SEQ_CRC` | `'SP/2026/041472'` | NUM_SEQ_CRC |
| `SOCIO_CPF` | `'27428710804'` | Airton |

**Mapeamentos:**
- `ACCOUNT_TYPE_TO_NAT` (constantes.py:86) — Odoo account_type → COD_NAT SPED (01-09)
- `PLANO_REFERENCIAL` (constantes.py:124) — account_type → codigo plano referencial RFB (I051)
- `ACCOUNT_TYPES_PATRIMONIAIS` (set) — filtro J100
- `ACCOUNT_TYPES_RESULTADO` (set) — filtro J150
- `QUALIFICACOES_J930` (lista de tuplas) — codigos signatario (001-999), `'900'` reservado para contabilista
- `saldo_natural_dc(account_type)` (constantes.py:160) — D ou C natural

---

## ROTAS (routes.py — Blueprint `relatorios_fiscais`)

URL prefix: `/relatorios-fiscais` (registrado em `app/__init__.py:980-981`)

| URL | Metodo | Funcao | O que faz |
|-----|--------|--------|-----------|
| `/sped-ecd` | GET | `sped_ecd()` | Pagina form |
| `/sped-ecd/gerar` | POST | `gerar_sped_ecd()` | Enfileira job RQ → JSON `{job_id}` |
| `/sped-ecd/status/<job_id>` | GET | `sped_ecd_status()` | Polling progresso Redis |
| `/sped-ecd/download/<job_id>` | GET | `sped_ecd_download()` | Download por job_id |
| `/sped-ecd/progress/<job_id>` | GET | `sped_ecd_progress()` | Pagina progresso visual |
| `/sped-ecd/historico` | GET | `sped_ecd_historico()` | Lista S3 do user |
| `/sped-ecd/download-direto` | GET | `sped_ecd_download_direto()` | Download por s3_key (querystring) |

**Guards:** `@requires_financeiro` + `@login_required` (definidos em `app/seguranca/decorators.py`)

**Outras rotas no mesmo blueprint** (IBSCBS, Razao Geral): nao relacionadas ao SPED ECD.

---

## ORDEM DE EMISSAO DOS BLOCOS (service.py:62 — `gerar_sped_ecd_centralizado`)

```
1. Bloco 0      → 0000, 0001, 0007, 0990
2. 0150         → V1.5 Opcao A: SEMPRE vazio (so emite se houver relacionamento societario)
3. Bloco I open → I001, I010, I030
4. I050+I051+I052 INTERCALADOS por conta (PVA exige vinculo posicional)
5. I100 (CCUS)  → V1.8: condicional `if EMITIR_CCUS_SPED and plano_ccus:`
6. I150+I155    → saldos mensais
7. I200+I250    → lancamentos streaming
8. I350+I355    → encerramento (so se date_fim=31/12)
9. I990
10. Bloco J     → J001, J005/J100 BP, J005/J150 DRE, J800 opcional, J900, J930, J990
11. Bloco 9     → 9001, 9900, 9990, 9999
```

---

## VALIDATOR (validator.py — pre-PVA)

**Entry point:** `SpedEcdValidator.validar(bytes, contexto_odoo)` (linha 126) → `{valido, erros, warnings, estatisticas}`

**Dataclass:** `ErroValidacao` (linha 39) — campos: categoria, severidade, titulo, descricao, registro, linha_arquivo, odoo_model, odoo_id, odoo_url, acao_sugerida, quem_resolve, contexto

**Metodos de validacao (sequencia em `validar()`):**

| Metodo | Linha | O que valida |
|--------|-------|--------------|
| `_parse_conteudo()` | 177 | Parse Latin-1, split pipes |
| `_validar_estrutura()` | 216 | Caracteres `?` (Latin-1 mal resolvida) |
| `_validar_bloco_0()` | 231 | 0000: 23 campos, CNPJ, IDENT_MF∈{S,N}, IND_CENTRALIZADA=0 |
| `_validar_bloco_I()` | 303 | I050: hierarquia COD_CTA_SUP, COD_NAT∈{01-09}, IND_CTA∈{S,A}; I250: IND_DC, VL_DC≥0 (V1.8) |
| `_validar_bloco_J()` | 399 | J005 ID_DEM 1+2, J100 IND_GRP_BAL/COD_AGL, J930 12 campos |
| `_validar_bloco_9()` | 508 | 9999 == total linhas; 9900 contagens batem |
| `_validar_referencias_cruzadas()` | 547 | I250.COD_CTA→I050; I250.COD_CCUS→I100; I250.COD_PART→0150 |
| `_validar_batimento_contabil()` | 608 | J100 nivel 1: Ativo≈Passivo+PL (diff>0.01 = BLOQUEANTE) |

**Categorias de erro:** `estrutura`, `mapeamento_ref`, `cadastro_partner`, `batimento`, `ccus`, `hierarquia`, `signatario`, `cross_ref`

---

## HISTORICO DE VERSOES E DECISOES CRITICAS

| Versao | Decisao | Motivo |
|--------|---------|--------|
| V1.1 | Layout I200 (6 campos), I250 (9 campos), J150 (13), J900 (8) | Bugs originais — PVA reprovava bloco inteiro |
| V1.2 | l10n_br_conta_referencial REAL do Odoo CIEL IT (87% cobertura) | Antes: 100% fallback PLANO_REFERENCIAL |
| V1.2 | I051 vinculo IMPLICITO por sequencia (3 campos: REG\|COD_CCUS\|COD_CTA_REF) | Layout 9 nao tem COD_CTA — bug 4 campos rejeitava |
| V1.3 | Worker RQ + fila `sped_ecd` em `start_worker_render.sh` | Sem isso, jobs nao processavam (`9d4e11d2`, 2026-05-14) |
| V1.4 | Validador pre-PVA + UX de erros para contador | UX |
| V1.5 | 0150/COD_PART desativados (participantes=[]) | PVA reprovava 3470 partidas por falta de 0180 — clientes/fornecedores normais nao precisam de 0150 |
| V1.6 | Saldo INICIAL real no balanco (date_ini-1) | Antes: sempre 0,00 |
| V1.6 | I052 emitido para codes em `codes_aglutinacao` (J100/J150) | PVA exige "codigo de aglutinacao em pelo menos um I052" |
| V1.6 | stream: pre-fetch move_ids, depois chunk de lines por moves | Bug anterior `id > last_id` em account.move.line pulava ~98% (2049 I200 em vez de 60000+) |
| V1.7 | I051 filtra referenciais com >4 niveis ou contendo `'99.99'` | 923 contas CIEL IT com mapeamento invalido reprovavam |
| V1.7 | Contas de compensacao (code 5+) excluidas do BP | Odoo CIEL IT classifica mal — Manual ECD diz que compensacao tem natureza propria |
| V1.7 | I250 COD_PART lido do campo[8] (nao [7]) | Validator antigo lia HIST como COD_PART — falso positivo |
| V1.8 | `EMITIR_CCUS_SPED=False` (CCUS off no SPED) | NACOM tem 1 plano analitico/filial; analytic_distribution achatado soma >100%; split gerava VL_DC negativo |
| V1.8 | IBGE via `l10n_br_ciel_it_account.res.municipio.codigo_ibge` | `l10n_br_base.municipio` nao existe na CIEL IT |
| V1.8 | Validator nova regra: `I250 VL_DC < 0 = BLOQUEANTE` | Trava regressao do bug split CCUS |

---

## GOTCHAS — VOCE PRECISA SABER

### 1. PVA exige I050+I051+I052 INTERCALADOS por conta (nao em blocos)

I051 tem so 3 campos (`REG|COD_CCUS|COD_CTA_REF`) — sem COD_CTA. O vinculo e POSICIONAL: I051 deve vir LOGO APOS o I050 da conta a que se refere. Idem para I052 quando emitido. Esta logica esta em `construir_I050_com_I051()` (blocks.py:404), as funcoes isoladas `construir_I050()` e `construir_I051()` sao DEPRECATED.

### 2. I052 so para contas analiticas COM mapeamento de aglutinacao

I052 NAO deve ser emitido para SINTETICAS. Atualmente o codigo emite I052 quando `c['code'] in codes_agl` SEM checar `c['tipo']` (blocks.py:468) — **BUG: sintetica com code em codes_agl gera I052 incorreto**. Ver `SPED_ECD_PLANO.md` categoria 1.

### 3. J100 usa codes REAIS do plano

`construir_J005_J100()` (blocks.py:801) usa codes do plano (1, 11, 111, ...). Era inventado em V1.5 (BP_ATIVO, BP_ATIVO_01) — PVA reprovava por "COD_AGL_SUP nao existe".

### 4. J150 usa codes FICTICIOS (DRE_REC_BRUTA, etc.)

J150 NAO usa codes do plano — usa agrupamentos funcionais. `construir_J005_J150()` (blocks.py:934). Lista hardcoded em `grupos_dre` (blocks.py:990).

### 5. Saldo natural vs IND_DC

Funcao `_ind_dc(saldo, natural)` (blocks.py:908) inverte natural se saldo<0. Manual ECD: VL_CTA SEMPRE positivo, sinal vem do IND_DC.

### 6. Encoding Latin-1 puro

`remover_acentos()` (blocks.py:67) normaliza Unicode. Caracteres como `?` no arquivo final indicam Latin-1 mal resolvida (validator detecta via `_validar_estrutura()`).

### 7. PROD vs DEV worker

Fila `sped_ecd` esta em `start_worker_render.sh` (PROD) E `worker_atacadao.py` (DEV). Manter sincronia — regra global ~/.claude/CLAUDE.md.

### 8. Consolidacao por code (nao por account_id)

`buscar_plano_contas_consolidado()` (data.py:158) consolida 3 companies via code. `id_to_code` mapeia TODOS os account_ids das 3 companies para o mesmo code.

### 9. EncryptedFernetField em params do worker?

Nao — worker recebe params primitivos (date_ini_iso, date_fim_iso, qualif_socio, user_id). Sem secrets.

### 10. RQ Job result NAO retorna o BytesIO

Job retorna `{'s3_key', 'tamanho_bytes', 'valido', 'erros', 'warnings'}`. Download e via S3 presigned URL (`gerar_presigned_url_sped()`).

### 11. SPED da contadora e GROUND TRUTH

Existe um SPED gerado pela contadora oficial (`SpedContabil-61724241000178_35208934897_18_20240701_20241231_G (1).txt` em Downloads) **validado e aceito pela RFB**. Usar como referencia ao investigar formato de campos:
- Layout I030 real (12 campos com IDENT_NUM, NIRE, CPF_RESP_LEG, DT_AB, MUN, DT_ARQ)
- 0000 com COD_MUN IBGE + hash IDENT_HASH
- IND_CRC pode ser formato literal `SP-1303041/O-9` (nao precisa converter para `1SP041472`)
- J150 com codes numericos hierarquicos `9 → 9.3 → 9.3.1 → 9.3.1.1` e COD_AGL_SUP populado (vs nosso DRE_REC_* sem hierarquia)
- J932 (Termo de Verificacao para Substituicao ECD) e obrigatorio para ECD substituta (`IND_FIN_ESC='1'`) — atualmente nao emitimos
- 0000 da contadora tem `TIP_ECD=1` (nao `0`) e `COD_SCP=1` — significados a confirmar

Comandos para comparar: ver secao "Comandos uteis para comparar com SPED da contadora" no `SPED_ECD_PLANO.md`.

### 12. PVA externo vs validador interno: gap esperado

Validador interno (`sped_ecd_validator.py`) cobre apenas ~30 regras. **PVA externo (RFB) detecta muito mais** — desde regras estruturais por campo ate referencia cruzada entre registros. Em V19/V20, validador interno reporta 1 erro mas PVA pode reportar centenas. Sempre considerar PDF do PVA como autoridade.

---

## COMO ITERAR EM CORRECOES (FLUXO)

```bash
# 1. Ativar venv
source .venv/bin/activate

# 2. Editar codigo em app/relatorios_fiscais/services/sped_ecd_*.py

# 3. Bump VERSAO_SPED em services/sped_ecd_constantes.py (ex: V21 -> V22)
#    (fonte unica — script le daqui, output e logs sao auto-versionados)

# 4. Gerar SPED standalone (sem RQ, mais rapido para debug)
python scripts/sped_ecd/gerar_sped.py

# 5. Output: /home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_{VERSAO_SPED}_3COMPANIES.txt
#    (nome muda automaticamente com VERSAO_SPED)

# 6. Validador interno roda automatico. Saida tem:
#    - Validacao: erros + warnings
#    - Sanity check: I250 negativos (deve ser 0)

# 7. Append linha NO TOPO da tabela HISTORICO em SPED_ECD_PLANO.md
#    (ja tem placeholder se script imprime "TBD" — preencher).

# 8. Enviar arquivo gerado ao PVA externo (manualmente).

# 9. Receber PDF de erros → atualizar STATUS das CATEGORIAs no SPED_ECD_PLANO.md → repetir.
```

**NUNCA:**
- Ler o SPED txt (70MB) inteiro — `grep`/`sed -n` com padrao
- Ler o PDF de erros inteiro — categorias estao no SPED_ECD_PLANO.md
- Ler os 5 services Python inteiros de uma vez — usar offsets

---

## PROTOCOLO DE NOVA VERSAO

> Toda iteracao do SPED toca EXATAMENTE 3 lugares. Se voce parar antes do passo 3, a documentacao FICA INCONSISTENTE — proxima sessao perdera tempo.

| # | Onde | O que muda |
|---|------|------------|
| 1 | `services/sped_ecd_constantes.py` linha `VERSAO_SPED = 'VX'` | Bump string (ex: V21 -> V22). UNICA mudanca de "nome de versao" no sistema. |
| 2 | `SPED_ECD_PLANO.md` tabela HISTORICO DE ITERACOES | Append linha NO TOPO: `\| VX \| YYYY-MM-DD HH:MM \| erros validador \| warnings \| tamanho \| mudancas \|`. Preencher TBD do placeholder gerado pelo script. |
| 3 | `SPED_ECD_PLANO.md` STATUS das CATEGORIAs | Apos PVA externo: FIXED_NOT_VALIDATED -> VERIFIED_FIXED. Apos novo fix: PENDING -> FIXED_NOT_VALIDATED. |

**O que NAO precisa mais ser atualizado** (refactor 2026-05-15):
- ~~Nome do script (`gerar_v18.py` etc)~~ — script e `gerar_sped.py`, fixo.
- ~~Titulo do PLANO~~ — e `SPED_ECD_PLANO.md`, fixo.
- ~~OUTPUT_PATH hardcoded com versao~~ — script ja interpola `VERSAO_SPED`.

**Antipattern a evitar**: criar `SPED_ECD_PLANO_VX.md`, `gerar_vX.py`, hardcode `'V18'` em script. UMA fonte de verdade — `VERSAO_SPED`.

---

## REFERENCIAS

| Preciso de... | Documento |
|---------------|-----------|
| Plano de fix em curso | `SPED_ECD_PLANO.md` (este diretorio) |
| **Manual ECD Leiaute 9 (refatorado, indexado)** | **`manual_ecd/INDEX.md` — leitura barata por bloco/registro** |
| Manual ECD oficial (PDF online) | http://sped.rfb.gov.br/pasta/show/1569 |
| IDs Odoo fixos | `.claude/references/odoo/IDS_FIXOS.md` |
| Boilerplate Odoo (REGRA ZERO) | `.claude/references/odoo/AGENT_BOILERPLATE.md` |
| Workers RQ — adicionar fila | `~/.claude/CLAUDE.md` secao "WORKER RQ — DEV vs PROD" |
| Timezone (datas SPED) | `.claude/references/REGRAS_TIMEZONE.md` |
| JSON sanitization | `~/.claude/CLAUDE.md` secao "JSON SANITIZATION" |
