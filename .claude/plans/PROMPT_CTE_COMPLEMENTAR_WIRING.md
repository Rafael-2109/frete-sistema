# Prompt — Wiring CTe Complementar (carvia) para producao

## Contexto

Na sessao anterior, reescrevi do zero o script Playwright `emitir_cte_complementar_222.py` que emite CTe Complementar no SSW a partir de Custos de Entrega (modulo carvia). O fluxo completo **ja esta funcionando end-to-end** (emissao + envio SEFAZ + download DACTE/XML), validado com CTe real autorizado (CAR-143-1, cStat=100, protocolo 135261679947334).

**O que falta**: wiring do worker RQ → script novo, persistencia no banco, e UI para exibir o ICMS do pai e o valor calculado.

**Restricao importante**: As alteracoes da sessao anterior NAO foram commitadas ainda. Antes de tudo, faca `git status` e revise as mudancas pendentes.

---

## Arquivos ja modificados (pendentes de commit)

### 1. `.claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py` — **refactor completo**

Reescrito do zero baseado em Playwright codegen do proprio SSW. Segue o fluxo de 11 fases:

1. **Login** (via `login_ssw` de `ssw_common`)
2. **Abrir opcao 222** → popup page1 (via `abrir_opcao_popup`)
3. **Preencher tela inicial** (page1): `#motivo`, `[id="1"]` (filial), `[id="2"]` (ctrc concatenado sem hifen, ex: `591`)
4. **Click [id="3"] (►)** → abre **novo popup page2** (via `page1.expect_popup()`)
5. **Preencher tela principal** (page2): `#vlr_outros`, `#tp_doc` (default "C"), `#unid_emit` (default "D" mas pode vir readonly — SSW decide)
6. **Click ► + loop de "Continuar"** — SSW mostra aviso CFOP/ICMS/GNRE antes de gerar o CTRC; precisa clicar em "2. Continuar" ate nao aparecer mais (loop com 5 tentativas)
7. **Captura aviso "Novo CTRC: XXX000YYY-Z"** — extraido do `document.body.innerText` de todas as pages/frames do context (aparece na page1 apos popup fechar)
8. **Trocar filial no menu principal** (via `main_frame.evaluate`) para a filial do novo CTRC (que pode diferir da filial do pai, ex: interestadual vai para filial do destino)
9. **Opcao 007** → popup page3 → click `"Enviar à SEFAZ"`
10. **Dismiss DCe dialog** se aparecer
11. **Opcao 101** → page4 → `#t_nro_ctrc.fill(num)` → Enter → popup page5 → download **DACTE** (link name "DACTE") + **XML** (link name "XML"). Ambos vem em ZIP

**Novos parametros CLI**:
- `--valor-base FLOAT` — valor bruto do custo entrega (ex: 182.00). Script consulta opcao 101 do pai automaticamente, extrai ICMS real, e calcula grossing up.
- `--valor-outros FLOAT` — valor ja com grossing up (modo manual, back-compat)
- `--tp-doc` default "C"
- `--unid-emit` default "D"
- `--enviar-sefaz` flag — se omitido, para apos pre-CTRC criado

**Funcoes novas** adicionadas ao arquivo:
- `consultar_icms_pai(ctrc_num, filial)` — async, usa `consultar_ctrc_101.consultar_ctrc` para extrair frete + ICMS do body_raw e calcular aliquota (`valor_icms / valor_frete * 100`)
- `calcular_valor_cte_complementar(valor_base, aliquota_icms)` — grossing up `valor_base / 0.9075 / (1 - icms/100)`. **Identico ao calculo da rota em `custo_entrega_routes.py:745`**
- `_parse_valor_brasileiro(s)` — converte "1.863,72" → 1863.72

**Uso testado**:
```bash
python emitir_cte_complementar_222.py \
  --ctrc-pai CAR-59-1 --motivo D \
  --valor-base 182.00 --enviar-sefaz
```

Resultado validado (CAR-143-1, autorizado SEFAZ):
- Script extraiu do pai: `valor_frete=33.00, valor_icms=7.26, aliquota_icms=22.0`
- Calculou: `182 / 0.9075 / 0.78 = 257.12`
- Emitiu CTRC CAR-143-1, chave `35260462312605000175570010000001401000001410`
- XML confirma `vTPrest=257.12, vICMSOutraUF=56.57, pICMSOutraUF=22.00, vBC=181.53` (IBS/CBS base muito proxima de 182, confirmando o grossing up)

### 2. `.claude/skills/operando-ssw/scripts/ssw_common.py` — `capturar_screenshot` nao-bloqueante

Screenshot agora tem `timeout=8000` ms, `full_page=False`, e try/except que loga warning e retorna None em caso de falha. Motivo: `injetar_html_no_dom` usa `document.open/write/close` que re-dispara font loading, causando trava em "waiting for fonts" quando full_page=True. Screenshot e evidencia, nao deve quebrar operacao fiscal.

### 3. `app/carvia/routes/custo_entrega_routes.py:719` — **bug critico fixado**

```diff
- xml_bytes = storage.get_file_content(operacao.cte_xml_path)
+ xml_bytes = storage.download_file(operacao.cte_xml_path)
```

`get_file_content()` nao existe em `FileStorage` — o metodo correto e `download_file()`. Esse bug fazia a rota `POST /carvia/custos-entrega/<id>/gerar-cte-complementar` SEMPRE cair em "ICMS nao encontrado" quando `operacao.icms_aliquota` era NULL (tentava lazy-load do XML no S3 e falhava silenciosamente).

---

## Gotchas descobertos sobre SSW opcao 222 (documentar)

Esses gotchas estao no script mas ainda nao foram adicionados a documentacao da skill `operando-ssw`. Considere criar `.claude/skills/operando-ssw/references/OPCAO_222.md` ou adicionar secao a `SCRIPTS.md` / `CTE.md`.

1. **Popup chain**: opcao 222 abre popup page1 (tela inicial com motivo+filial+ctrc). Ao clicar `[id="3"]` (►) na page1, **abre novo popup page2** (tela principal com valores). Nao e mesma page.

2. **Campo valor correto**: `#vlr_outros` (nao `outros`, `frete`, nem `valor`).

3. **Campo obrigatorio escondido**: `#tp_doc` = "C" (tipo documento: Complementar). Deve ser preenchido.

4. **`#unid_emit` pode vir READONLY**: SSW decide o local da prestacao (D=Destino, O=Origem) baseado na carga. Pode ou nao permitir alterar. Detectar via `el.readOnly || hasAttribute('readonly')` e respeitar o valor se readonly.

5. **Aviso CFOP/ICMS/GNRE**: Apos click ►, SSW mostra um errormsg div com texto tipo "CTRC será gerado com CFOP 5932. O ICMS deve ser recolhido antecipadamente a SEFAZ RJ mediante Guia de Recolhimento (opcao 160)." + botoes "1. Corrigir" (id=-1) e "2. Continuar" (id=0). Precisa clicar no "2. Continuar" para prosseguir.

6. **Nome do link "Continuar"**: Tem prefixo numerado — "2. Continuar", nao apenas "Continuar". Use `re.compile(r"Continuar")` ou clique pelo id (`[id="0"]`).

7. **Loop de avisos**: Pode haver MULTIPLOS avisos "Corrigir/Continuar" em sequencia. Implementar loop (max 5 iteracoes) que verifica HTML por "Continuar" e clica ate nao aparecer mais. **Gotcha adicional**: Apos o ultimo Continuar, a page2 **fecha automaticamente** — capturar esse estado com try/except (Page.content lanca "Target page, context or browser has been closed").

8. **Aviso "Novo CTRC"**: Aparece na page1 (nao na page2, que ja fechou). Formato: `Aviso × Novo CTRC: XXX000YYY-Z`. Capture com regex `r'Novo CTRC:\s*([A-Z]+)0*(\d+)-(\d)'` no `document.body.innerText` de todas as pages/frames do context.

9. **Dialogs nativos dismissed**: Playwright async auto-dismissa dialogs. Se SSW usar `alert()` nativo (nao HTML), registre handler `context.on("page", lambda p: p.on("dialog", handler))` ANTES do click. No caso do 222, o aviso veio em HTML (nao alert), mas e boa pratica manter o handler.

10. **Filial do complementar ≠ filial do pai**: SSW decide a filial de emissao do complementar baseado na rota/cidade do destinatario.
    - CAR-59-1 (RJ→RJ, intraestadual) → complementar em CAR (mesma filial)
    - CAR-86-8 (SP→ES, interestadual, destino SERRA/ES) → complementar em VIX (filial do destino)
    - Importante: apos capturar o CTRC novo, **trocar filial no menu principal** via `main_frame.evaluate(document.getElementById('2').value = filial_complementar)` antes de abrir opcao 007.

11. **Opcao 007 envio SEFAZ**: Apos trocar filial, abrir opcao 007 (popup page3) e clicar no link `"Enviar à SEFAZ"` (com acento). Um dialog DCe pode aparecer — ignorar (sleep 3s e seguir).

12. **Opcao 101 download**: Abrir 101 (popup page4), preencher `#t_nro_ctrc` com numero (sem filial, sem DV), `press('Enter')` → abre popup page5. Nela, `get_by_role("link", name="DACTE")` e `get_by_role("link", name="XML")` disparam downloads. **XML vem em ZIP** — use `zipfile.ZipFile` para extrair.

13. **Filial GIG vs CAR na captura**: Se o pai e CAR mas o complementar sai em VIX/GIG/outra filial, o `consultar_ctrc_101.py` na fase 11 precisa usar `--filial <filial_complementar>`. O script ja faz isso corretamente.

---

## Estado do banco (Render producao)

Query para verificar:

```sql
SELECT
  ce.id, ce.numero_custo, ce.operacao_id, ce.cte_complementar_id,
  ce.tipo_custo, ce.valor, ce.status, ce.criado_em,
  op.ctrc_numero, op.icms_aliquota, op.cnpj_cliente, op.nome_cliente
FROM carvia_custos_entrega ce
LEFT JOIN carvia_operacoes op ON op.id = ce.operacao_id
WHERE ce.id IN (14, 17, 18)
ORDER BY ce.id;
```

Resultados esperados (em 2026-04-09):
- **CE-014** (id=14): TAXA_DESCARGA, R$ 182,00, PENDENTE, operacao 63, CTRC `CAR-59-1`, cliente NOTCO → SUPER MERCADO ZONA SUL (RJ→RJ). `cte_complementar_id=NULL`.
- **CE-017** (id=17): TAXA_DESCARGA, R$ 55,00, PENDENTE, operacao 106, CTRC `CAR-86-8`, NOTCO → DISTRIMAX (SP→ES via VIX). `cte_complementar_id=NULL`.
- **CE-018** (id=18): TAXA_DESCARGA, R$ 156,00, PAGO, operacao 129, CTRC `GIG-114-7`, NOTCO → RJ. `cte_complementar_id=NULL`.

```sql
SELECT * FROM carvia_emissao_cte_complementar ORDER BY criado_em DESC;
```

**Tabela vazia** — nenhuma emissao via rota RQ jamais aconteceu. Esperado, porque a rota sempre caia em "ICMS nao encontrado" devido ao bug A (ja fixado mas nao testado em producao).

```sql
SELECT id, numero_comp, operacao_id, ctrc_numero, cte_numero, cte_chave_acesso, status, criado_em FROM carvia_cte_complementares ORDER BY criado_em DESC;
```

**So 1 registro**: COMP-001 (operacao 138, criado 2026-04-03 manualmente). **Os CTes gerados pelo script (CAR-141-4, CAR-142-2, CAR-143-1) NAO estao no banco** porque o script standalone nao persiste — so emite no SSW.

### Pendencia no SSW
- **CAR-141-4** e **CAR-142-2** foram CANCELADOS pelo usuario manualmente (eram duplicatas de teste com ICMS errado 12%).
- **CAR-143-1** esta AUTORIZADO no SSW mas **nao vinculado ao banco** — CE-014 continua com `cte_complementar_id=NULL`.

---

## Arquitetura atual (antes do wiring)

```
┌─────────────────────────────────────────────────────────────────┐
│ UI: /carvia/custos-entrega/<id>/gerar-cte-complementar (POST)   │
│    custo_entrega_routes.py:gerar_cte_complementar()             │
│                                                                  │
│ 1. Pega custo + operacao                                        │
│ 2. Lazy-load ICMS do XML (bug A fixado)                         │
│ 3. Calcula valor_cte = valor_base / 0.9075 / (1 - icms/100)     │
│ 4. Cria CarviaCteComplementar (status=RASCUNHO)                 │
│ 5. Cria CarviaEmissaoCteComplementar (status=PENDENTE)          │
│ 6. Enfileira job RQ: emitir_cte_complementar_job(emissao.id)    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Worker RQ: ssw_cte_complementar_jobs.py                          │
│    emitir_cte_complementar_job(emissao_comp_id)                 │
│                                                                  │
│ 1. Busca emissao no DB                                          │
│ 2. Resolve CTRC real via _resolver_ctrc_ssw (fallback)          │
│ 3. Monta args.Namespace com ctrc_pai, motivo_ssw, valor_calc    │
│ 4. Chama _executar_script_222(args) = asyncio.run do script     │
│ 5. Atualiza emissao.status + cte_complementar baseado resultado │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Script: emitir_cte_complementar_222.py (REFATORADO)              │
│    emitir_cte_complementar(args)                                │
│                                                                  │
│ Se args.valor_base: consultar_icms_pai → calcular valor_outros  │
│ Senao: usar args.valor_outros direto                            │
│ Fluxo 11 fases (login → 222 → 007 → 101)                        │
│ Retorna: {sucesso, ctrc_complementar, sefaz_enviado, xml, dacte}│
└─────────────────────────────────────────────────────────────────┘
```

---

## Tarefas da nova sessao

### Task 1: Wiring do worker RQ → script com `valor_base`

Arquivo: `app/carvia/workers/ssw_cte_complementar_jobs.py`

Hoje o worker monta `args_222` com `valor_outros=float(emissao.valor_calculado)`. Mudar para passar `valor_base=float(emissao.custo_entrega.valor)` e deixar o script calcular o ICMS real do pai.

**Racional**: a rota ja calcula `valor_calculado` baseado no `operacao.icms_aliquota` (pode estar stale). O script extrai o ICMS **ao vivo** do SSW via opcao 101, garantindo frescor de dados e tratando o caso de frete fechado (`CAR` na pratica usa a aliquota destacada no CTe original).

Passos:
1. Ler `ssw_cte_complementar_jobs.py` completo para entender fluxo atual (especialmente `_executar_script_222`).
2. Modificar `args_222 = argparse.Namespace(...)` para passar `valor_base` em vez de `valor_outros`. Tambem passar `tp_doc='C'`, `unid_emit='D'`, `enviar_sefaz=True`, `dry_run=False`, `valor_outros=None`, `valor_base=float(emissao.custo_entrega.valor)`.
3. Apos o script retornar, persistir `resultado['icms_pai']` (dict) em `emissao.resultado_json` (ja feito via `_sanitize_resultado`).
4. Atualizar `emissao.icms_aliquota_usada = resultado['icms_pai']['aliquota_icms']` se presente.
5. Se `resultado['sefaz_enviado']` true, marcar `emissao.etapa = 'SEFAZ'` antes de prosseguir.
6. Se `resultado['xml']` retornado, registrar o path (mas atencao: XML vem em ZIP; talvez precise extrair e salvar no S3 do projeto).

### Task 2: Persistir XML/DACTE do CTe complementar no S3

Apos o script retornar com `resultado['xml']` (path local temporario em `/tmp/ssw_operacoes/cte_complementar/<FILIAL>-<NUM>-<DV>.xml`), o worker deve:

1. Abrir o ZIP (`zipfile.ZipFile(path)`)
2. Extrair o XML interno (nome `{chave}-cte.xml`)
3. Subir o XML para S3 via `get_file_storage().save_file(bytes, folder='carvia/ctes_complementares_xml')`
4. Subir o DACTE PDF similarmente
5. Preencher `cte_comp.cte_xml_path`, `cte_comp.cte_xml_nome_arquivo`
6. Parsear XML para preencher `cte_comp.cte_chave_acesso`, `cte_numero` (nCT), `cte_data_emissao`, `cte_valor` (vTPrest)
7. Atualizar `cte_comp.ctrc_numero = resultado['ctrc_complementar']`
8. Atualizar `cte_comp.status = 'EMITIDO'`
9. Atualizar `emissao.status = 'SUCESSO'`

**Importante**: `CarviaCteComplementar` ja tem todos esses campos no schema (`.claude/skills/consultando-sql/schemas/tables/carvia_cte_complementares.json`).

### Task 3: UI — exibir ICMS do pai e valor calculado

Arquivo: `app/templates/carvia/custos_entrega/detalhe.html`

Apos o worker terminar, `emissao.resultado_json` vai conter:
```json
{
  "icms_pai": {
    "valor_frete": 33.00,
    "valor_icms": 7.26,
    "aliquota_icms": 22.0,
    "ctrc_completo": "CAR000059-1",
    "cte": "001 000000057"
  },
  "sefaz_enviado": true,
  "ctrc_complementar": "CAR-143-1",
  "dacte": "/tmp/...",
  "xml": "/tmp/..."
}
```

Adicionar uma secao no detalhe do custo entrega mostrando:
- **CTe pai**: {ctrc_completo} (CT-e {cte})
- **ICMS do pai**: {aliquota_icms}% (R$ {valor_icms} sobre frete R$ {valor_frete})
- **Valor complementar calculado**: R$ {valor_calculado}
- **CTRC complementar**: {ctrc_numero} (se emitido)
- Links para DACTE PDF / XML (usar presigned URL do FileStorage)

Seguir padroes UI ja estabelecidos (`GUIA_COMPONENTES_UI.md`). Usar tokens de design, nao hex hardcoded.

### Task 4: Code review + commit

**NAO commitar antes de**:
1. Testar o fluxo completo via UI: criar custo entrega novo (ou usar CE-014 pendente) → clicar "Gerar CTe Complementar" → polling status → verificar persistencia no banco
2. Confirmar que `CarviaCteComplementar` e `CarviaEmissaoCteComplementar` ficam populados corretamente
3. Verificar que XML + DACTE ficam no S3 e links funcionam
4. Revisar `app/carvia/CLAUDE.md` para adicionar nota sobre o fluxo de emissao (ja tem menção no R4 mas pode expandir)

**Mensagem de commit sugerida**:
```
feat(carvia): CTe Complementar end-to-end — extração automática de ICMS do pai

- Refactor emitir_cte_complementar_222.py: 11 fases (login → 222 → 007 → 101),
  popup chain, loop de Continuar, auto-calculo via consulta 101 do pai
- Worker ssw_cte_complementar_jobs: wiring para passar valor_base (script
  extrai ICMS real) + persistência XML/DACTE no S3 + backfill cte_comp
- Bug fix: custo_entrega_routes:719 usa download_file (não get_file_content)
- Bug fix: ssw_common.capturar_screenshot não-bloqueante (timeout 8s, full_page=False)
- UI: detalhe do custo entrega exibe ICMS do pai, valor calculado, status SEFAZ
- Gotchas SSW 222 documentados: popup chain, vlr_outros, tp_doc, unid_emit
  readonly, loop Continuar, filial do complementar vs pai

Testado com CAR-59-1 → CAR-143-1 (autorizado SEFAZ, protocolo 135261679947334,
ICMS 22% extraído automaticamente do pai, grossing up 182 → 257,12).
```

---

## Validacao end-to-end (fazer apos completar tasks)

1. **Pre-condicao**: CE existente com `cte_complementar_id=NULL` e operacao com CTe autorizado no SSW (ex: CE-017 e CE-018 ainda estao disponiveis, ou criar novo).
2. Chamar `POST /carvia/custos-entrega/<id>/gerar-cte-complementar` via UI (botão no detalhe).
3. Acompanhar polling de status: `GET /carvia/api/custos-entrega/emissao-comp/<id>/status`.
4. Verificar que `emissao.status` passa de PENDENTE → EM_PROCESSAMENTO → SUCESSO em ~60-120s.
5. Query no banco: `SELECT * FROM carvia_cte_complementares WHERE id = (SELECT cte_complementar_id FROM carvia_custos_entrega WHERE id = <custo_id>)`. Confirmar que tem `ctrc_numero`, `cte_chave_acesso`, `cte_xml_path`, `status='EMITIDO'`.
6. Verificar que `emissao.resultado_json.icms_pai.aliquota_icms` bate com ICMS real do CTe pai.
7. Abrir tela de detalhe na UI e confirmar que exibicao do ICMS do pai + CTRC novo + links DACTE/XML estao funcionando.
8. **Cancelar o CTe complementar gerado via SSW** (opcao 006, POP-C06) para nao deixar duplicata.

---

## Referencias importantes

| Arquivo | Uso |
|---------|-----|
| `app/carvia/CLAUDE.md` | Guia do modulo carvia (R4: fluxo de status, R11: conciliacao) |
| `.claude/references/INFRAESTRUTURA.md` | IDs Render (postgresId=`dpg-d13m38vfte5s738t6p50-a`) |
| `.claude/skills/operando-ssw/SKILL.md` | Skill de operacoes SSW — leia ANTES de modificar scripts |
| `.claude/skills/operando-ssw/scripts/ssw_common.py` | Helpers (login_ssw, abrir_opcao_popup, capturar_screenshot) |
| `.claude/skills/consultando-sql/schemas/tables/carvia_custos_entrega.json` | Campos da tabela |
| `.claude/skills/consultando-sql/schemas/tables/carvia_cte_complementares.json` | Campos do CTe complementar |
| `app/utils/file_storage.py:243` | `download_file()` (nao `get_file_content`) |
| `app/carvia/services/parsers/cte_xml_parser_carvia.py` | Parser para extrair ICMS do XML (se precisar) |

---

## Checklist de inicio

Antes de modificar codigo, execute:

1. `git status` — ver mudancas pendentes da sessao anterior
2. Ler os 3 arquivos modificados para entender o estado:
   - `.claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py` (script refatorado)
   - `.claude/skills/operando-ssw/scripts/ssw_common.py:397` (capturar_screenshot)
   - `app/carvia/routes/custo_entrega_routes.py:719` (bug A)
3. `grep -n "emitir_cte_complementar_job" app/carvia/workers/ssw_cte_complementar_jobs.py` — entender o worker atual
4. `ls /tmp/ssw_operacoes/cte_complementar/CAR-143-1.*` — confirmar que os arquivos de teste existem
5. Consultar Render via MCP: verificar estado de CE-014 (cte_complementar_id=NULL) e `carvia_emissao_cte_complementar` (vazia)

**Acao inicial sugerida**: dry-run do script novo para confirmar que a instalacao local continua funcionando:

```bash
source .venv/bin/activate && python .claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py \
  --ctrc-pai CAR-59-1 --motivo D --valor-base 182.00 --dry-run
```

Deve retornar `{"sucesso": true, "dry_run": true, ...}`.

---

## Observacoes finais

- **Nao comitar** ate fluxo end-to-end estar validado via UI
- **Cancelar CAR-143-1** no SSW apos validacao (senao vira 4o CTe cancelado no historico)
- O usuario preferiu **nao commitar** ainda para poder revisar o script
- Regra P1-P7 nao se aplica aqui (nao e carteira, e fluxo operacional carvia)
- Nao usar `AskUserQuestion` para perguntas triviais — use bom senso e avance
- Nao usar emojis em codigo. Mensagens de commit em pt-BR tecnico
