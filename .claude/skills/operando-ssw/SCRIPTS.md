# Scripts — Operando SSW: CT-e (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao para scripts CT-e.

---

## Ambiente Virtual

NAO requer ambiente virtual. Scripts sao Playwright standalone (headless Chromium).
Credenciais lidas do `.env`: `SSW_URL`, `SSW_DOMINIO`, `SSW_CPF`, `SSW_LOGIN`, `SSW_SENHA`.

---

## 1. emitir_cte_004.py

**Proposito:** Emite CT-e completo no SSW. Fluxo: opcao 004 (pre-CTRC) → opcao 007 (SEFAZ) → opcao 101 (consulta). Placa `ARMAZEM` = frete fracionado (cliente entregou no armazem).

```bash
python .claude/skills/operando-ssw/scripts/emitir_cte_004.py \
  --chave-nfe "33260309089839000112550000003571412198449943" \
  --frete-peso 600 \
  [--placa ARMAZEM] [--filial CAR] \
  [--enviar-sefaz] [--consultar-101] [--baixar-dacte] \
  --dry-run
```

| Parametro | Obrig | Default | Descricao |
|-----------|-------|---------|-----------|
| `--chave-nfe` | **Sim** | — | Chave de acesso NF-e (exatamente 44 digitos) |
| `--frete-peso` | **Sim** | — | Valor do frete peso em R$ (float, ex: 600.00) |
| `--placa` | Nao | `ARMAZEM` | Placa coleta. ARMAZEM = fracionado, placa real = carga direta |
| `--filial` | Nao | `CAR` | Filial emissora. DEVE ser CAR |
| `--enviar-sefaz` | Nao | — | Envia ao SEFAZ via opcao 007 apos gravar |
| `--consultar-101` | Nao | — | Consulta resultado na opcao 101 apos emissao |
| `--baixar-dacte` | Nao | — | Baixa DACTE PDF + XML (requer `--consultar-101`) |
| `--dry-run` | — | — | Preenche formulario sem gravar. **OBRIGATORIO 1a execucao** |
| `--discover` | — | — | Modo exploratorio: mapeia campos do formulario |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "ctrc": "94",
  "campos_preenchidos": {
    "placa": "ARMAZEM",
    "chave_nfe": "33260309089839000112550000003571412198449943",
    "chave_metodo": "native_popup_nfepnl",
    "frete_peso": "600,00"
  },
  "resultado": {
    "ctrc": "94",
    "dialogs": [{"tipo": "confirm", "msg": "Confirma a emissao?"}],
    "popup_fechou": false
  },
  "sefaz": {"dialogs": [], "body": "..."},
  "consulta_101": {"body": "...", "dacte_onclick": "...", "xml_onclick": "..."},
  "mensagem": "CT-e 94 — Emitido. SEFAZ enviado."
}
```

`sucesso` = `true` somente se CTRC extraido do resultado (numero capturado dos dialogs ou DOM).

### Atualizacoes 2026-04-09

Mudancas importantes no fluxo interno (sem breaking change nos parametros CLI):

- **Frete informado usa `#lnk_frt_inf_env`** (NAO `fechafrtparc('C')`). Fonte de verdade: codegen manual do usuario. `fechafrtparc('C')` isolado quebra o fluxo com null pointer em `doDis`/`concluindo`. Commit `9e6fd75e` reverteu tentativa anterior.
- **Helper `_clicar_simular()`** com fallback em cascata (commit `74295621`):
  1. Click nativo `get_by_role("link", name="►")` timeout 5s
  2. Fallback 1: `document.getElementById('lnk_env').click()` via evaluate
  3. Fallback 2: scan `querySelectorAll('a')` buscando `onclick` com `calculafrete`
  - Motivo: overlay invisivel `<div id="errorpanel">` sem `pointer-events: none` bloqueia clicks nativos do Playwright.
  - Campo `campos_ok["simular_metodo"]` no retorno indica qual tentativa funcionou.
- **Match "Gravar" via regex** `re.compile(r"Gravar", re.IGNORECASE)` (commit `4428231d`). SSW renderiza link como "1. Gravar", "1.Gravar", "Gravar" ou "gravar" — literal nao funciona.
- **3 tentativas em cascata para Gravar** (commit `4428231d`):
  1. `get_by_role("link", name=re.compile("Gravar", IGNORECASE))` com timeout 5s
  2. JS click no link com onclick contendo `concluindo('C')`
  3. `evaluate("concluindo('C')")` direto
- **NAO_RECONHECIDO dumpa HTML** quando loop de avisos encontra dialog desconhecido: `body[:3000]` + `html[:8000]` em `avisos_tratados[...]['debug']`.
- **Envio SEFAZ via `ajaxEnvia`** (commit `973e9739`): substituido click no botao por `ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')` no popup pos-gravar. Popup 007 aberto apenas para capturar status fila (Digitados/Enviados/Autorizados/Denegados/Rejeitados) via regex sobre body. Fallback: se popup 004 fechou, retry em popup_007.
- **`trocar_filial()` extraida** em helper (commit `973e9739`) — reutilizada entre scripts.
- **Retorno enriquecido**: `campos_ok["frete_metodo"] = "lnk_frt_inf_env"` (observabilidade — se aparecer no JSON, fluxo correto rodou).

---

## 2. consultar_ctrc_101.py

**Proposito:** Consulta CTRC/CT-e na opcao 101. **READ-ONLY** — nao altera dados, nao requer `--dry-run`. Opcionalmente baixa XML (ZIP → extrai) e DACTE (PDF).

```bash
# Por CTRC:
python .claude/skills/operando-ssw/scripts/consultar_ctrc_101.py \
  --ctrc 94 [--baixar-xml] [--baixar-dacte] [--output-dir /tmp/cte]

# Por NF:
python .claude/skills/operando-ssw/scripts/consultar_ctrc_101.py \
  --nf 35714 [--baixar-xml] [--baixar-dacte]
```

| Parametro | Obrig | Default | Descricao |
|-----------|-------|---------|-----------|
| `--ctrc` | Sim* | — | Numero CTRC sem digito verificador (ex: 94) |
| `--nf` | Sim* | — | Numero da NF (ex: 35714, max 10 digitos) |
| `--filial` | Nao | `CAR` | Filial para consulta |
| `--baixar-xml` | Nao | — | Baixar XML do CT-e (servidor retorna ZIP, script extrai) |
| `--baixar-dacte` | Nao | — | Baixar DACTE em PDF |
| `--output-dir` | Nao | `/tmp/ssw_operacoes/consulta_101` | Diretorio para arquivos baixados |

\* `--ctrc` OU `--nf` — mutuamente exclusivos, um obrigatorio.

**Retorno JSON:**
```json
{
  "sucesso": true,
  "ctrc": "94",
  "nf_pesquisada": null,
  "cte": "350940000001234",
  "chave_cte": "3526030908983900011257000000012340000009419",
  "dados": {
    "body_raw": "...",
    "ctrc_completo": "000094-9 CAR 68-0",
    "cte": "350940 000001234",
    "status": "AUTORIZADO",
    "destino": "MANAUS/AM",
    "nf": "35714",
    "volumes": "10",
    "peso": "1.894,40",
    "valor_nf": "14.649,73",
    "frete": "3.200,00",
    "remetente": "NACOM GOYA IND COM ALIMENTOS LTDA",
    "remetente_cnpj": "09089839000112",
    "destinatario": "DESTINO LTDA",
    "destinatario_cnpj": "33119545000251",
    "situacao": "EM ABERTO",
    "cobranca": "CIF",
    "seq_ctrc": "12345",
    "familia": "CTE"
  },
  "xml": "/tmp/ssw_operacoes/consulta_101/CTe_350940000001234.xml",
  "dacte": "/tmp/ssw_operacoes/consulta_101/DACTE_000094.pdf",
  "screenshot": "/tmp/ssw_operacoes/consulta_101/101_ctrc_94_20260327.png",
  "mensagem": "CTRC 94 consultado. XML: /tmp/... DACTE: /tmp/..."
}
```

**Campos extraidos (16):** Cada campo via regex sobre `body.innerText`. Se regex nao encontra, campo = `null`.

---

## 3. cancelar_cte_004.py

**Proposito:** Cancela CT-e autorizado no SSW (opcao 004). Envia cancelamento ao SEFAZ. **OPERACAO FISCAL IRREVERSIVEL** — prazo maximo 7 dias da autorizacao.

```bash
python .claude/skills/operando-ssw/scripts/cancelar_cte_004.py \
  --ctrc 66 \
  --serie "CAR 68-0" \
  --motivo "NF vinculada incorretamente, reemissao necessaria" \
  --dry-run
```

| Parametro | Obrig | Default | Descricao |
|-----------|-------|---------|-----------|
| `--ctrc` | **Sim** | — | Numero CTRC sem DV (ex: 66) |
| `--serie` | **Sim** | — | Serie do CTRC (ex: "CAR 68-0") |
| `--motivo` | **Sim** | — | Justificativa do cancelamento (5-200 caracteres) |
| `--dry-run` | — | — | Preview sem cancelar. **OBRIGATORIO 1a execucao** |
| `--discover` | — | — | Modo exploratorio: mapeia interface de cancelamento |

**Retorno JSON por cenario:**

| Cenario | `sucesso` | `status` | Campos extras |
|---------|-----------|----------|---------------|
| `--dry-run` | `true` | `"dry-run"` | `dados` (preview CT-e), `screenshot` |
| Popup fechou (sucesso SSW) | `true` | `"cancelado"` | `dados`, `mensagem` |
| Indicador sucesso no body | `true` | `"cancelado"` | `dados`, `body_text` |
| Erro SEFAZ / prazo / manifesto | `false` | `"erro"` | `erro_detalhe`, `body_text` |
| Resultado indeterminado | `false` | `"inconclusivo"` | `body_text`, recomenda verificar 101 |
| CT-e nao encontrado | `false` | — | `body_text`, `screenshot` |

**Restricoes criticas:**
- Prazo maximo: 7 dias da data de autorizacao SEFAZ
- Se CT-e incluido em Manifesto: cancelar Manifesto ANTES (opcao 024)
- Se mercadoria ja embarcou: NAO cancelar (risco sinistro sem cobertura seguro)
- POP: `pops/POP-C06-cancelar-cte.md`

---

## 4. gerar_fatura_ssw_437.py

**Proposito:** Gera fatura no SSW (opcao 437, filial MTZ). Seleciona CTe no grid e gera fatura com download PDF. Filial DEVE ser MTZ (nao CAR).

```bash
python .claude/skills/operando-ssw/scripts/gerar_fatura_ssw_437.py \
  --cnpj-tomador "12345678000199" \
  --ctrc 94 \
  --data-vencimento "150426" \
  [--baixar-pdf] \
  --dry-run
```

| Parametro | Obrig | Default | Descricao |
|-----------|-------|---------|-----------|
| `--cnpj-tomador` | **Sim** | — | CNPJ do tomador (14 digitos sem formatacao) |
| `--ctrc` | **Sim** | — | Numero CTRC sem DV (ex: 94) |
| `--data-vencimento` | Nao | — | Data vencimento no formato DDMMYY |
| `--baixar-pdf` | Nao | — | Baixar PDF da fatura gerada |
| `--dry-run` | — | — | Preenche CNPJ e banco sem gerar fatura. **OBRIGATORIO 1a execucao** |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "fatura_numero": "12345",
  "fatura_pdf": "/tmp/ssw_operacoes/fatura_437/fatura_12345.pdf",
  "ctrc_selecionado": "CAR000094-9",
  "campos_preenchidos": {
    "cnpj_tomador": "12345678000199",
    "banco": "auto-preenchido",
    "data_vencimento": "150426"
  }
}
```

**Campos SSW (tela 437):**

| Campo | Name/ID | Acao |
|-------|---------|------|
| CNPJ tomador | `cgc_cliente` | `getcli(value)` no change |
| Banco | — | `findbco('nro_banco','S','S','')` |
| Prosseguir | — | `ajaxEnvia('ENV', 0)` |
| Vencimento | `f2` (id=2) | Formato DDMMYY |
| Apontar docs | — | `ajaxEnvia('APO', 1)` |
| Grid CTes | checkbox + ► (`srimglnk`) | Seleciona CTe |
| Fatura gerada | `nro_fatura` (readonly) | Resultado |
| Download PDF | — | `ajaxEnvia('', 1, 'ssw2701?act=IMP&...')` |

---

## 5. emitir_cte_complementar_222.py

**Proposito:** Emite CT-e complementar no SSW via opcao **222** (+ envio SEFAZ 007 + baixar XML/DACTE via 101). Usado para ajustar valores, complementar ICMS, cobrar custos extras. Fluxo **11 fases** baseado em codegen capturado (NAO adicionar logica defensiva extra).

```bash
# Com auto-calculo de valor (consulta 101 do pai + grossing up):
python .claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py \
  --ctrc-pai CAR-113-9 \
  --motivo D \
  --valor-base 200.00 \
  [--tp-doc C] [--unid-emit D] [--enviar-sefaz] \
  --dry-run

# Com valor final ja calculado (sem consulta 101):
python .claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py \
  --ctrc-pai CAR-113-9 \
  --motivo D \
  --valor-outros 227.90 \
  --dry-run
```

| Parametro | Obrig | Default | Descricao |
|-----------|-------|---------|-----------|
| `--ctrc-pai` | **Sim** | — | CTRC pai no formato `FILIAL-NUMERO-DV` (ex: `CAR-113-9`) |
| `--motivo` | **Sim** | — | Motivo do complemento. Validos: `C`, `D`, `V`, `E`, `R` |
| `--valor-outros` | Sim* | — | Valor final do complementar (pos-grossing up, float) |
| `--valor-base` | Sim* | — | Valor bruto (aciona grossing up automatico via ICMS do pai) |
| `--tp-doc` | Nao | `C` | Tipo de documento. Validos: `C` |
| `--unid-emit` | Nao | `D` | Unidade emissora. Validos: `D`, `O` (SSW pode forcar readonly) |
| `--enviar-sefaz` | Nao | — | Envia ao SEFAZ via opcao 007 pos-emissao |
| `--dry-run` | — | — | Preenche tela inicial, nao submete. **OBRIGATORIO 1a execucao** |

\* `--valor-outros` OU `--valor-base` — **mutuamente exclusivos**, um obrigatorio.

### Pre-fase: auto-calculo do valor_outros

Se `--valor-base` fornecido (sem `--valor-outros`), script executa:

1. Delega para `consultar_ctrc_101.py` (consulta 101 do pai — filial detectada do CTRC)
2. Extrai `ICMS/ISS (R$)` e `Valor frete (R$)` do body via regex
3. Calcula `aliquota = (valor_icms / valor_frete) * 100`
4. Aplica grossing up: `valor_base / 0.9075 / (1 - aliquota/100)` (mesma formula de `custo_entrega_routes.py`)
5. Seta `valor_outros = valor_calculado`

Constante: `PISCOFINS_DIVISOR = 0.9075` (fixo, mesma regra do Nacom).

### Fluxo 11 fases

```
Fase 1:  login_ssw()
Fase 2:  abrir_opcao_popup(222) → popup page1
Fase 3:  Preencher page1:
           #motivo = args.motivo
           [id="1"] = filial_pai (extraida do CTRC-FILIAL-NUMERO-DV)
           [id="2"] = ctrc_concatenado (numero+dv SEM hifen, ex: "1139")
Fase 4:  Click [id="3"] → expect_popup → popup page2
Fase 5:  Preencher page2:
           #vlr_outros = valor BR ("227,90") → click + fill
           #tp_doc = "C" → click + fill
           #unid_emit = "D" → dblclick + fill (OU readonly: respeitar SSW)
Fase 6:  Click ► (get_by_role) OU fallback ajaxEnvia('ENV2') via evaluate
         Loop Continuar (MAX=5x): [id="0"] → get_by_role → evaluate scan onclick btn_200='S'
         HTML de debug salvo em /tmp/ssw_operacoes/222_debug_page2_*.html
Fase 7:  Capturar CTRC complementar:
           - Fonte 1: dialog nativo "Novo CTRC: FILIAL000NUMERO-DV" (regex em handler context.on("page",...))
           - Fonte 2: fallback scan innerText em todos frames/pages
Fase 8:  Trocar filial no main_frame para filial_complementar (pode ser != filial_pai)
Fase 9:  Abrir opcao 007 → click "Enviar à SEFAZ" (page3)
Fase 10: Abrir opcao 101 → baixar XML (ajaxEnvia('XML',0) → extrai ZIP) + DACTE
Fase 11: Retornar resultado consolidado
```

### Retorno JSON

```json
{
  "sucesso": true,
  "ctrc_pai": "CAR-113-9",
  "ctrc_complementar": "CAR-2037-1",
  "filial_complementar": "CAR",
  "motivo": "D",
  "valor_base": 200.00,
  "valor_outros": 227.90,
  "icms_pai": {
    "valor_frete": 1863.72,
    "valor_icms": 223.65,
    "aliquota_icms": 12.0,
    "ctrc_completo": "000113-9 CAR 68-0",
    "cte": "..."
  },
  "tp_doc": "C",
  "unid_emit_usado": "D",
  "unid_emit_readonly": false,
  "sefaz_enviado": true,
  "xml": "/tmp/ssw_operacoes/222/CTe_...xml",
  "dacte": "/tmp/ssw_operacoes/222/DACTE_...pdf",
  "dialog_messages": [
    {"type": "alert", "msg": "Novo CTRC: CAR002037-1"}
  ]
}
```

### Gotchas criticos

- **CTRC formato sem hifen**: `[id="2"]` espera `"1139"` (numero + dv concatenados). Script converte `CAR-113-9` → `"1139"` automaticamente.
- **`unid_emit` pode vir readonly**: SSW decide filial do complementar baseado na carga. Script detecta via `el.readOnly || el.hasAttribute('readonly')` e loga `unid_emit_readonly: true`. NAO tentar forcar.
- **Dialog nativo captura CTRC**: SSW usa `alert()` JavaScript ("Novo CTRC: XXX"). Handler registrado em `context.on("page", ...)` captura em TODAS as pages do context (popup 222, page2, etc.) via `_attach_dialog_handler`.
- **Pre-requisito**: CTe pai autorizado e consultavel na opcao 101 da filial correta (para `--valor-base` funcionar).
- **Loop "Continuar" (MAX=5)**: multiplos avisos CFOP/ICMS/GNRE — script clica todos automaticamente.
- **`valor_base` vs `valor_outros`**: mutuamente exclusivos. NAO passar ambos.
- **Motivos validos**: `C` (correcao), `D` (diferenca), `V` (valor), `E` (estorno), `R` (retificacao). Outro motivo = erro de validacao.

---

## Exemplos de Uso

### Cenario 1: Emitir CT-e fracionado completo
```
Pergunta: "emitir CT-e para NF-e chave 33260309089839000112550000003571412198449943, frete peso R$ 600"
Comando 1 (dry-run): emitir_cte_004.py --chave-nfe "332603..." --frete-peso 600 --dry-run
Comando 2 (real):    emitir_cte_004.py --chave-nfe "332603..." --frete-peso 600 --enviar-sefaz --consultar-101 --baixar-dacte
```

### Cenario 2: Consultar CTRC por numero
```
Pergunta: "consulta o CTRC 94"
Comando: consultar_ctrc_101.py --ctrc 94
```

### Cenario 3: Consultar por NF e baixar DACTE + XML
```
Pergunta: "preciso do DACTE e XML da NF 35714"
Comando: consultar_ctrc_101.py --nf 35714 --baixar-xml --baixar-dacte
```

### Cenario 4: Cancelar CT-e dentro do prazo
```
Pergunta: "cancelar CT-e 66, serie CAR 68-0, motivo: nota vinculada errada"
Comando 1 (dry-run): cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" --motivo "nota vinculada errada" --dry-run
Comando 2 (real):    cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" --motivo "nota vinculada errada"
```

### Cenario 5: Emitir CT-e complementar com auto-calculo de valor
```
Pergunta: "emitir CT-e complementar do CAR-113-9, motivo D (desconto), valor base 200"
Comando 1 (dry-run): emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo D --valor-base 200 --dry-run
  (script consulta 101 do pai → extrai ICMS real → aplica grossing up → preenche valor final)
Comando 2 (real):    emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo D --valor-base 200 --enviar-sefaz
```

### Cenario 6: Emitir CT-e complementar com valor ja calculado
```
Pergunta: "emitir CT-e complementar CAR-113-9, motivo V, valor final R$ 227,90"
Comando 1 (dry-run): emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo V --valor-outros 227.90 --dry-run
Comando 2 (real):    emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo V --valor-outros 227.90 --enviar-sefaz
```
