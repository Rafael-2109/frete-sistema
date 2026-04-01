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
