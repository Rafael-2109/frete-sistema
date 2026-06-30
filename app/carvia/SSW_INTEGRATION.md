# CarVia — Integracao SSW (Playwright)

> **Criado em**: 2026-04-09
> **Escopo**: Documentacao tecnica da emissao automatizada de CTe no SSW via scripts Playwright.
> **Referencia no dev guide**: `app/carvia/CLAUDE.md` (link na secao "Emissao SSW").

A CarVia emite CTe diretamente no SSW via scripts Playwright standalone (skill `operando-ssw`).
O SSW NAO possui API/XML-RPC — toda interacao e via navegacao web automatizada.

Arquitetura: **Route → Service → Model tracking → Worker RQ → Script Playwright → Service importar**.

---

## Indice

- [Arquitetura geral](#arquitetura-geral)
- [Modelos de tracking](#modelos-de-tracking)
- [Padrao SSL Drop Resilience (R15)](#padrao-ssl-drop-resilience-r15)
- [Preview automatico de motos](#preview-automatico-de-motos)
- [Worker auxiliar verificar_ctrc_ssw_jobs](#worker-auxiliar-verificar_ctrc_ssw_jobs)
- [Endpoints REST](#endpoints-rest)
- [Refactor "use CTe+CTRC instead of #id"](#refactor-use-cte-ctrc-instead-of-id)
- [Referencias cruzadas](#referencias-cruzadas)

---

## Arquitetura geral

### Fluxo CTe normal (NF → CTe + Fatura)

```
UI Browser
    │ POST /carvia/api/nfs/<nf_id>/emitir-cte-ssw
    ▼
Route (app/carvia/routes/api_routes.py ou nf_routes.py)
    │
    ▼
SswEmissaoService.preparar_emissao()
    [app/carvia/services/documentos/ssw_emissao_service.py]
    │ 1. Resolve filial via UF_FILIAL_MAP (SP→CAR, RJ→GIG)
    │ 2. Auto-extrai medidas motos via extrair_medidas_da_nf() (se vazio)
    │ 3. Cria CarviaEmissaoCte (status=PENDENTE)
    │ 4. Enfileira job RQ na fila `high`, timeout 10m
    ▼
Worker RQ: ssw_cte_jobs.emitir_cte_ssw_job(emissao_id)
    [app/carvia/workers/ssw_cte_jobs.py]
    │ 1. Snapshot ORM → variaveis locais (ctrc_numero_local, etc.)
    │ 2. _liberar_conexao_antes_playwright()  [R15]
    ▼
Script Playwright headless: emitir_cte_004.py
    │ --chave-nfe X --frete-peso Y --enviar-sefaz --consultar-101 --baixar-dacte
    │ Duracao tipica: 60-120s
    ▼
Retorno JSON
    │
    ▼
_commit_pos_playwright(emissao_id, etapa=IMPORTACAO_CTE, ...)
    [retry 3x com backoff 1s/2s/4s em SSL/DBAPI errors]
    │
    ▼
SswEmissaoService.importar_resultado_cte(emissao, resultado_cte)
    │ 1. Le bytes do XML local (xml_path) e DACTE (dacte_path)
    │ 2. processar_arquivos([(xml_nome, bytes), (dacte_nome, bytes)], criado_por=...)
    │    → Sobe S3: carvia/ctes_xml/ + carvia/ctes_pdf/
    │ 3. salvar_importacao(nfs_data, ctes_data, matches, criado_por)
    │    → Cria CarviaOperacao com ctrc_numero, cte_xml_path, cte_pdf_path
    │ 4. Busca CarviaOperacao por cte_chave_acesso → seta emissao.operacao_id
    ▼
[Opcional] Script gerar_fatura_ssw_437.py + importar_resultado_fatura()
    │ Cria CarviaFaturaCliente via salvar_importacao(faturas_data=...)
    ▼
emissao.status = SUCESSO  (ou ERRO)
```

### Fluxo CTe Complementar (CustoEntrega → CTe Complementar)

```
UI Browser
    │ POST /carvia/api/custos-entrega/<id>/emitir-cte-comp
    ▼
Service: cria CarviaEmissaoCteComplementar (status=PENDENTE)
    │ Enfileira job RQ
    ▼
Worker: ssw_cte_complementar_jobs.emitir_cte_complementar_job(emissao_comp_id)
    [app/carvia/workers/ssw_cte_complementar_jobs.py]
    │
    │ Fase 0: resolver_ctrc_ssw(ctrc_num, filial) → formato CAR-NUM-DV
    │         [services/cte_complementar_persistencia.py]
    │
    │ _liberar_conexao_antes_playwright()
    ▼
Script Playwright: emitir_cte_complementar_222.py
    │ --ctrc-pai CAR-113-9 --motivo D --valor-base custo.valor --enviar-sefaz
    │
    │ Pre-fase: consultar_icms_pai() → consulta 101 do pai → grossing up
    │   valor_outros = valor_base / 0.9075 / (1 - aliquota_icms / 100)
    │
    │ 11 fases: login → 222 page1 → page2 → click ► → loop Continuar
    │   → captura "Novo CTRC" → troca filial → 007 SEFAZ → 101 baixa XML/DACTE
    ▼
_commit_pos_playwright(emissao_comp_id, ...) [retry 3x]
    ▼
_persistir_artefatos_complementar()
    [services/cte_complementar_persistencia.py]
    │ 1. Extrai XML do ZIP retornado pela 101
    │ 2. upload_xml_s3() → carvia/ctes_xml/{nome}.xml
    │ 3. upload_dacte_s3() → carvia/ctes_pdf/{nome}.pdf
    │ 4. Backfill CarviaCteComplementar:
    │      ctrc_numero, cte_chave_acesso, cte_xml_path, cte_pdf_path
    ▼
emissao.status = SUCESSO  (ou ERRO)

Retry de emissao em ERRO:
    POST /carvia/api/custos-entrega/emissao-comp/<id>/retry
    → Valida emissao.status == ERRO e cte_comp.status == RASCUNHO
    → Reseta status=PENDENTE, re-enfileira job
```

---

## Modelos de tracking

### CarviaEmissaoCte (tabela `carvia_emissao_cte`)

Arquivo: `app/carvia/models/frete.py:182`

Tracking de emissoes automaticas de CTe principal (opcao 004 → 007 → 101 → 437).

**Funcoes**:
- **Mutex**: evita dupla emissao para a mesma NF (verificar status PENDENTE/EM_PROCESSAMENTO)
- **Progresso**: campo `etapa` atualizado pelo job para polling pela UI
- **Auditoria**: historico completo de tentativas por NF

**Status lifecycle**:
```
STATUSES = ('PENDENTE', 'EM_PROCESSAMENTO', 'SUCESSO', 'ERRO', 'CANCELADO')
ETAPAS   = ('LOGIN', 'PREENCHIMENTO', 'SEFAZ', 'CONSULTA_101',
            'IMPORTACAO_CTE', 'FATURA_437', 'IMPORTACAO_FAT')
```

**Campos principais** (ver `models/frete.py` L182-239):

| Campo | Tipo | Notas |
|-------|------|-------|
| `nf_id` | FK `carvia_nfs` | NF que motivou a emissao (NOT NULL) |
| `operacao_id` | FK `carvia_operacoes` | Preenchido por `importar_resultado_cte` via `cte_chave_acesso` |
| `status` | String(20) | Ver STATUSES acima |
| `etapa` | String(30) | Ver ETAPAS acima — atualizada pelo worker |
| `job_id` | String(100) | ID do job RQ |
| `ctrc_numero` | String(20) | CTRC SSW (ex: `CAR 113-9`) |
| `placa` | String(20) | Default `ARMAZEM` (frete fracionado) |
| `uf_origem` | String(2) | Para resolver filial via UF_FILIAL_MAP |
| `filial_ssw` | String(10) | Resolvido em `preparar_emissao()` |
| `cnpj_tomador` | String(20) | Para fatura 437 |
| `frete_valor` | Numeric(15,2) | Valor passado para script 004 |
| `data_vencimento` | Date | Para fatura 437 |
| `medidas_json` | JSON | `[{modelo_id, qtd}]` (auto-extraido se vazio) |
| `erro_ssw` | Text | Erro reportado pelo script Playwright |
| `resultado_json` | JSON | Resultado completo do script (snapshot) |
| `xml_path` | String(500) | Caminho LOCAL temporario do XML (`/tmp/ssw_operacoes/...`) |
| `dacte_path` | String(500) | Caminho LOCAL temporario do DACTE |
| `fatura_numero` | String(20) | Numero da fatura 437 (se gerada) |
| `fatura_pdf_path` | String(500) | Caminho LOCAL temporario do PDF da fatura |
| `criado_em` | DateTime | naive UTC |
| `criado_por` | String(100) | Usuario que iniciou |

**Properties**:
- `em_andamento` → `True` se status in PENDENTE/EM_PROCESSAMENTO
- `finalizado` → `True` se status in SUCESSO/ERRO/CANCELADO

**Service**: `SswEmissaoService` (`app/carvia/services/documentos/ssw_emissao_service.py`)

| Metodo | Linha | Funcao |
|--------|-------|--------|
| `preparar_emissao(nf_id, placa, cnpj_tomador, frete_valor, data_vencimento, medidas_motos=None)` | L71 | Cria `CarviaEmissaoCte`, resolve filial, auto-extrai medidas, enfileira job |
| `preparar_emissao_lote(nf_ids, ...)` | L186 | Lote (max 20 NFs) |
| `extrair_medidas_da_nf(nf_id)` | L260 | Auto-extracao de motos via GROUP BY `modelo_moto_id` em `CarviaNfItem` |
| `importar_resultado_cte(emissao, resultado_cte)` | L356 | **Reescrito em commit `35820900`** — le bytes XML/DACTE, sobe S3, cria CarviaOperacao, vincula `operacao_id` via `cte_chave_acesso` |
| `importar_resultado_fatura(emissao, resultado_fatura)` | L466 | **Corrigido em `35820900`** — chama `salvar_importacao(faturas_data=...)` para criar `CarviaFaturaCliente` |

**Worker**: `app/carvia/workers/ssw_cte_jobs.py` → `emitir_cte_ssw_job(emissao_id)`

> Aplica padrao SSL drop resilience (R15) — ver secao abaixo.

---

### CarviaEmissaoCteComplementar (tabela `carvia_emissao_cte_complementar`)

Arquivo: `app/carvia/models/cte_custos.py:226`

Tracking de emissao automatizada de CTe Complementar (opcao 222 + 007 + 101). 1:1 com `CarviaCustoEntrega`.

**Status lifecycle**:
```
PENDENTE → EM_PROCESSAMENTO → SUCESSO | ERRO
ETAPAS:    PREENCHIMENTO | SEFAZ | CONSULTA_101
```

**Campos principais** (ver `models/cte_custos.py` L226-285):

| Campo | Tipo | Notas |
|-------|------|-------|
| `custo_entrega_id` | FK `carvia_custos_entrega` | NOT NULL — motiva a emissao |
| `cte_complementar_id` | FK `carvia_cte_complementares` | NOT NULL — preenchido pos-sucesso |
| `operacao_id` | FK `carvia_operacoes` | NOT NULL — referencia ao CTe pai |
| `ctrc_pai` | String(30) | Formato `FILIAL-NUMERO-DV` (ex: `CAR-113-9`) |
| `motivo_ssw` | String(5) | C/D/E/R |
| `filial_ssw` | String(10) | Default `CAR` |
| `valor_calculado` | Numeric(15,2) | Valor final apos grossing up (passado como `--valor-outros` ao script) |
| `icms_aliquota_usada` | Numeric(5,2) | Snapshot do ICMS do pai usado no calculo |
| `status` | String(20) | PENDENTE / EM_PROCESSAMENTO / SUCESSO / ERRO |
| `etapa` | String(30) | PREENCHIMENTO / SEFAZ / CONSULTA_101 |
| `job_id` | String(100) | ID do job RQ |
| `erro_ssw` | Text | Erro reportado pelo script |
| `resultado_json` | JSON | Resultado completo do script |
| `criado_por` | String(100) | NOT NULL |

**Worker**: `app/carvia/workers/ssw_cte_complementar_jobs.py` → `emitir_cte_complementar_job(emissao_comp_id)`

**Persistencia**: `app/carvia/services/cte_complementar_persistencia.py`
- `resolver_ctrc_ssw(ctrc_num, filial)` — normaliza para formato `FILIAL-NUMERO-DV`
- `persistir_cte_complementar_completo()` — orquestrador upload S3 + backfill
- Upload S3 para `carvia/ctes_xml/` e `carvia/ctes_pdf/` via `app/utils/file_storage.py`

**Retry**: rota `POST /carvia/api/custos-entrega/emissao-comp/<id>/retry` (commit `6ca7b942`)
- Valida `emissao.status == ERRO` e `cte_comp.status == RASCUNHO`
- Reseta `status=PENDENTE`, re-enfileira job

---

### Campos S3 ficam em CarviaOperacao / CarviaCteComplementar

**IMPORTANTE**: Os caminhos `xml_path`/`dacte_path` em `CarviaEmissaoCte` sao LOCAIS temporarios
(`/tmp/ssw_operacoes/...`). Os caminhos S3 finais ficam nos modelos de DOMINIO:

**CarviaOperacao** (`models/documentos.py` L173):
```python
cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
ctrc_numero      = db.Column(db.String(30), index=True)  # CAR-{nCT}-{cDV}
cte_xml_path     = db.Column(db.String(500))  # S3: carvia/ctes_xml/...
cte_pdf_path     = db.Column(db.String(500))  # S3: carvia/ctes_pdf/...
icms_aliquota    = db.Column(db.Numeric(5, 2))  # Para grossing up complementares
```

**CarviaCteComplementar** (`models/cte_custos.py` L11):
```python
cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
ctrc_numero      = db.Column(db.String(30), index=True)
cte_xml_path     = db.Column(db.String(500))  # S3
cte_pdf_path     = db.Column(db.String(500))  # S3
```

**CarviaSubcontrato** (`models/documentos.py` L307+) tem os mesmos campos para CTes de subcontrato.

---

## Padrao SSL Drop Resilience (R15)

Workers Playwright duram 60-120s+. PostgreSQL (Render) tem `tcp_keepalive` que pode matar conexoes
idle durante o script. `pool_pre_ping=True` NAO resolve — a conexao ja estava checked-out antes.

### Solucao canonica (`ssw_cte_jobs.py`)

```python
def _liberar_conexao_antes_playwright():
    """Libera conexao do pool ANTES do Playwright (60-120s+)."""
    db.session.commit()   # Flush pendencias
    db.session.close()    # Libera transacao
    db.engine.dispose()   # Fecha pool (conexoes idle morrem)


def _commit_pos_playwright(emissao_id, **updates):
    """Re-busca objeto e commita updates com retry 3x backoff."""
    ensure_connection()                                    # SELECT 1 para revivar pool
    obj = db.session.get(CarviaEmissaoCte, emissao_id)    # Re-busca (antigo stale)

    for k, v in updates.items():
        setattr(obj, k, v)

    # Retry 3x com backoff 1s, 2s, 4s em SSL/DBAPI errors
    for tentativa in range(3):
        try:
            db.session.commit()
            return
        except (OperationalError, DBAPIError) as e:
            db.session.rollback()
            if tentativa == 2:
                raise
            time.sleep(2 ** tentativa)
```

### Snapshot de campos ORM antes do Playwright

**Variaveis locais** capturam os campos ANTES de liberar a conexao — o objeto fica stale durante o
Playwright, entao nao confiar nele:

```python
# Snapshot ANTES de liberar
ctrc_numero_local = emissao.ctrc_numero
filial_local      = emissao.filial_ssw
chave_local       = emissao.cte_chave_acesso

_liberar_conexao_antes_playwright()
# ... chamar Playwright via subprocess ...
# `emissao` agora esta stale — usar variaveis locais
```

### Quando aplicar

**TODOS** os workers que chamam scripts Playwright:
- `ssw_cte_jobs.py`
- `ssw_cte_complementar_jobs.py`
- `verificar_ctrc_ssw_jobs.py`

Documentado tambem em `app/carvia/CLAUDE.md` como **R15**.

---

## Preview automatico de motos

`SswEmissaoService.extrair_medidas_da_nf(nf_id)` (commit `baffaaad`):

```python
# Equivalente SQL:
# SELECT modelo_moto_id, SUM(quantidade) AS qtd
# FROM carvia_nf_itens
# WHERE nf_id = :nf_id AND modelo_moto_id IS NOT NULL
# GROUP BY modelo_moto_id
```

Retorna `[{modelo_id, qtd}]` no formato esperado por `emitir_cte_004.py --medidas`.

### Uso em `preparar_emissao()`

- Se `medidas_motos` parametro vier vazio → aciona auto-extracao
- Se vier populado → override manual prevalece (UI envia explicitamente)
- O `SswEmissaoService` faz a conversao CM→metros automaticamente (modelo_moto.dimensoes / 100)
  ANTES de passar ao script (script ja espera metros)

### UI

`app/templates/carvia/nfs/detalhe.html` (commit `9e6fd75e`):
- Preview auto-detectado mostra modelos + qtds via `selectattr modelo_moto_id` no Jinja
- Campo manual fica em `<details>` colapsado (edge case quando deteccao automatica falha)
- Submit do form usa `medidas` apenas se usuario preencheu manualmente

---

## Worker auxiliar verificar_ctrc_ssw_jobs

Job low-priority na fila `default` que corrige `ctrc_numero` divergente via consulta 101.

**Arquivo**: `app/carvia/workers/verificar_ctrc_ssw_jobs.py`

**Funcao**:
- Query: `CarviaOperacao` sem `ctrc_numero` mas com `cte_chave_acesso` populado
- Executa `consultar_ctrc_101.py --nf {nf_numero}` (read-only)
- Extrai `ctrc` do retorno → atualiza `CarviaOperacao.ctrc_numero`
- Usado para backfill de CTes legados (pre-automacao Playwright) e correcao de divergencias

Aplica o padrao SSL drop resilience (R15) tambem.

---

## Tratamento de avisos SSW e salvaguardas de frete (2026-06-19)

O script `emitir_cte_004.py` (skill `operando-ssw`) ganhou tratamento robusto dos avisos HTML
do SSW pos-simulacao e **3 salvaguardas que garantem que NUNCA grava um CTe com frete errado**.
Construido a 4 maos sobre a coleta 3 (filial GIG). Backlog/evidencias:
`docs/superpowers/plans/2026-06-19-resiliencia-emissao-cte-ssw.md`.

### Avisos tratados (Camada 1 — loop pos-simulacao)

| Aviso SSW | Tratamento |
|-----------|-----------|
| Email indisponivel | clica "E-mail nao disponivel" |
| **Cliente pagador bloqueado** | abre tela 389/ssw1105 (**polling ate 18s** — a 389 carrega ~6-10s apos o clique), seta `Transportar=S`, grava (`EN2`), retorna `retentar=True` + `cliente_desbloqueado=True` → o orquestrador **re-emite 1x** via `ssw_cte_jobs._emitir_cte_com_retry_desbloqueio` (a 2a passada nao ve mais o bloqueio). Desbloqueio e emissao sao operacoes SEPARADAS — tentar voltar da 389 p/ a 004 com estado gerava `TypeError at concluindo`. **Bug corrigido 2026-06-22 (NF 39058 MGS ELETRO)**: o contrato `retentar` entrou no script (commit f728e5cb5, 19/06) sem a contraparte no worker — o desbloqueio gravava `Transportar=S` mas o worker marcava ERRO "Cliente bloqueado" falso (classificador `CLIENTE_BLOQUEADO` casava ate dentro de "des**bloqueado**"; regex agora usa `(?<!des)bloqueado`). O retry exige AMBAS as flags (`retentar` **e** `cliente_desbloqueado`) — `frete_nao_confiavel` (salvaguarda 2) tem so `retentar` e NAO re-emite |
| GNRE / ICMS antecipado | clica "Continuar" |
| **Cidade nao atendida (opc 402)** | extrai cidade/UF, retorna `cidade_nao_atendida=True` — operador cadastra na 402 (decisao: NAO usar tipo FEC). Camada 2 classifica `CIDADE_NAO_ATENDIDA`. O lote PULA e lista |
| Peso real invalido | re-preenche 50% do cubado e re-simula |

### Salvaguardas de frete (defesa em profundidade)

O "Frete informado" (override do valor cobrado) pode ser DESCARTADO pelo SSW e substituido pelo
frete da TABELA. As 3 salvaguardas impedem gravar o valor errado:
1. **Forcar clique nativo** — `_clicar_simular` remove o overlay `errorpanel` antes de clicar o ►. O caminho NATIVO preserva o frete; o fallback JS (`lnk_env`) recalcula pela tabela (bug NF 39092: saiu 1567,73 vs 850).
2. **Abortar se fallback** — se alguma simulacao caiu no fallback, aborta ANTES de gravar (`frete_nao_confiavel`, `retentar=True`).
3. **Ler o resumo (definitiva)** — antes de gravar, le `VALOR A RECEBER` e aborta se != informado. Pega QUALQUER divergencia, inclusive avisos "Continuar" extras que recalculam (bug NF 39111: saiu 533,74 vs 600). O runner faz retry 1x e para se persistir.

> Resultado: das 22 emissoes da coleta 3, 3 sairam com frete errado ANTES das salvaguardas (canceladas+reemitidas); com as 3 salvaguardas, nenhum CTe e gravado com valor divergente.

### Performance (parcial — 2026-06-19)

Helper `_esperar(target, cond_js, timeout)` (polling) substituiu os `asyncio.sleep` fixos grandes
(NORMAL/chave/simular/gravar/101) — sai assim que o estado aparece em vez de esperar 8-20s. SEFAZ
20→6s (fire-and-forget; a 101 confirma a autorizacao depois). Emissao completa **~90s → ~40s/NF**.
**Pendente (proxima sessao)**: sessao reutilizavel (1 login/lote) + baixar XML na 101 interna (mata
a 2a sessao Playwright/NF) → alvo ~15-20s/NF. Ver backlog.

### Limite de concorrencia — semaforo Redis (2026-06-29)

**Problema**: `emitir_cte_ssw_job` e enfileirado na fila `high`, consumida por VARIOS workers
(`start_workers` `NUM_WORKERS` + `worker_atacadao --workers 2`). Ao emitir N CTes (ex.: 10 NFs de
destinatarios diferentes), N jobs Playwright rodavam **simultaneos** e saturavam o SSW — o popup do
frete nao abria em 30s e a salvaguarda abortava. Medido: **~55% de erro com 9-12 simultaneas vs ~0%
com ≤5**.

**Correcao** (`ssw_cte_jobs.py`): um **semaforo Redis** (`_adquirir_slot_ssw`/`_liberar_slot_ssw`,
chave `carvia:ssw:emissao:slots`) limita as emissoes **concorrentes** a `CARVIA_SSW_MAX_CONCORRENTES`
(env, **default 1 = SERIAL**, 1 emissao por vez — zero concorrencia no SSW). No `emitir_cte_ssw_job`:
adquire 1 slot antes de rodar; se esta no teto, **re-enfileira** (backoff 12s) sem abrir sessao SSW e
segue PENDENTE; libera o slot no `finally`. **Fail-open**: sem Redis nao limita (degrada para o
comportamento anterior). Contador com TTL 30min (auto-cura slot vazado por crash apos a rajada). NAO
ha mudanca de UI nem de fila — cada emissao continua sendo 1 job; o semaforo so as serializa.

> Ajuste fino: `CARVIA_SSW_MAX_CONCORRENTES` no worker. Default **1** (serial, pedido do dono).
> Subir so se o SSW comprovadamente aguentar mais (medido ~0% de erro ate ~5 simultaneas).
> Os outros jobs Playwright SSW (`emitir_cte_complementar_job`, `verificar_ctrc_operacao_job`) NAO
> compartilham este slot hoje — esporadicos; se virarem fonte de saturacao, usar a mesma chave.

---

## Endpoints REST

| Endpoint | Metodo | Proposito |
|----------|--------|-----------|
| `/carvia/api/nfs/<id>/emitir-cte-ssw` | POST | Enfileira emissao CTe (`CarviaEmissaoCte` PENDENTE → fila `high`) |
| `/carvia/api/emitir-cte-ssw/lote` | POST | Lote (max 20 NFs) |
| `/carvia/api/emissao-cte/<id>/status` | GET | Polling status (usado pelo JS, intervalo 5s) |
| `/carvia/api/custos-entrega/emissao-comp/<id>/retry` | POST | Retry CTe Complementar em ERRO (commit `6ca7b942`) |
| `/carvia/ctes-complementares/<id>/download-xml` | GET | Presigned S3 XML (rota `cte_complementar_routes.py`) |
| `/carvia/ctes-complementares/<id>/download-dacte` | GET | Presigned S3 DACTE |

---

## Refactor "use CTe+CTRC instead of #id"

> **Commit `672a1836` (2026-04-09)**: 23 templates atualizados para exibir
> `CTe-### + CTRC SSW` em vez de `#id` (PK) ou `numero_comp = COMP-###`.

### Macro `carvia_ref`

Arquivo: `app/templates/carvia/_macros.html`

Renderiza identificador unificado de `CarviaOperacao` ou `CarviaCteComplementar`:

```jinja
{{ carvia_ref(operacao) }}
{# → "CTe-042 | CTRC SSW CAR-113-9" #}

{{ carvia_ref(cte_complementar) }}
{# → "CTe Comp. 2037 | CTRC SSW CAR-2037-1" #}
```

### Templates afetados (12 arquivos)

- `detalhe_operacao.html`, `listar_operacoes.html` (legado)
- `ctes_complementares/{listar,criar,detalhe,editar}.html`
- `subcontratos/{criar,detalhe}.html`
- `faturas_cliente/{nova,detalhe}.html`
- `faturas_transportadora/detalhe.html`
- `custos_entrega/detalhe.html`

### APIs enriquecidas

`api_routes.py` retorna `ctrc_numero` e `operacao_cte_numero` nos payloads de listagem para
alimentar a macro. Antes do refactor, as APIs retornavam apenas IDs internos.

### Razao do refactor

Identificadores internos (`#id`, `COMP-###`) eram **incompreensiveis** para o usuario CarVia, que
opera no SSW e ve **CTe-042**, **CAR-113-9**. As UIs agora espelham 1:1 o que o usuario ve no SSW.

---

## Referencias cruzadas

### Scripts Playwright (skill `operando-ssw`)

| Arquivo | Opcao | Proposito |
|---------|-------|-----------|
| `.claude/skills/operando-ssw/scripts/emitir_cte_004.py` | 004 | Emissao CTe completo (004 → 007 → 101) |
| `.claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py` | 222 | Emissao CTe complementar (222 → 007 → 101) com auto-calc ICMS |
| `.claude/skills/operando-ssw/scripts/consultar_ctrc_101.py` | 101 | Consulta CTRC + baixa XML/DACTE (read-only) |
| `.claude/skills/operando-ssw/scripts/gerar_fatura_ssw_437.py` | 437 | Gerar fatura SSW (filial MTZ) |

### Documentacao das opcoes SSW

- `.claude/skills/operando-ssw/SKILL.md` — entry point operacional
- `.claude/skills/operando-ssw/SCRIPTS.md` — parametros, retornos JSON, gotchas dos scripts
- `.claude/skills/operando-ssw/references/CTE.md` — FIELD_MAP, fluxo SSW detalhado, gotchas
- `.claude/agents/gestor-ssw.md` — agente operador (decision tree, pre-mortem, erros)

### POPs (status de adocao CarVia)

- `.claude/references/ssw/CARVIA_STATUS.md` — C03 (CTe Complementar) marcado ATIVO desde 2026-04-09
- `.claude/references/ssw/pops/POP-C01-emitir-cte-fracionado.md` — emissao CTe fracionado
- `.claude/references/ssw/pops/POP-C03-emitir-cte-complementar.md` — emissao CTe complementar (opcao 222)
- `.claude/references/ssw/pops/POP-E02-faturar-manualmente.md` — fatura SSW (opcao 437)

### Commits de origem

| Commit | Descricao |
|--------|-----------|
| `35820900` | `SswEmissaoService.importar_resultado_cte` reescrito — XML+DACTE no S3 + cria CarviaOperacao |
| `baffaaad` | Auto-extracao de medidas motos da NF (`extrair_medidas_da_nf`) |
| `9e6fd75e` | Reverter `fechafrtparc` → `#lnk_frt_inf_env` + preview auto motos no template |
| `06f27d0d` | CTe Complementar end-to-end — auto-calc ICMS via 101 do pai + grossing up |
| `1b2e1ac0` | SSW 222 — primeiro funcional (field names, ajaxEnvia flow, 101 lookup) |
| `6ca7b942` | Retry de emissao CTe Complementar travada em ERRO |
| `dd8da687` | Worker CTe sobrevive a SSL drop pos-Playwright longo (R15) |
| `672a1836` | Refactor "use CTe+CTRC instead of #id/numero_comp" em 23 templates |
| `4428231d` | Match "Gravar" flexivel no script 004 + dump HTML no NAO_RECONHECIDO |
| `74295621` | Click simular CTe 004 com fallback JS (`_clicar_simular`) |
| `973e9739` | Refactor `emitir_cte_004` — SEFAZ via `ajaxEnvia('', 1, 'ssw0767?act=REM')` |
