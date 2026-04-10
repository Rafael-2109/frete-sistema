# CTE — 004, 007, 101, 222

Gotchas de dominio, FIELD_MAP interno e workflow completo para operacoes CT-e no SSW.
Para parametros e retornos dos scripts, consultar [SCRIPTS.md](../SCRIPTS.md).

---

- [FIELD_MAP — emitir_cte_004.py](#field_map--emitir_cte_004py)
- [FIELD_MAP — emitir_cte_complementar_222.py](#field_map--emitir_cte_complementar_222py)
- [Fluxo SSW Detalhado](#fluxo-ssw-detalhado)
- [Fluxo SSW — CTe Complementar (222)](#fluxo-ssw--cte-complementar-222)
- [Dialogs Automaticos](#dialogs-automaticos)
- [Gotchas de Dominio](#gotchas-de-dominio)
- [Restricoes de Cancelamento](#restricoes-de-cancelamento)
- [Workflow CT-e Completo](#workflow-ct-e-completo)

---

## FIELD_MAP — emitir_cte_004.py

Mapeamento dos 3 campos preenchidos pelo script no formulario SSW opcao 004:

| Parametro CLI | Campo SSW (name) | Campo SSW (id) | Notas |
|---------------|------------------|----------------|-------|
| `--placa` | `f13` | `13` | Placa coleta. Blur (`Tab`) dispara validacao SSW. ARMAZEM = fracionado |
| `--chave-nfe` | `chaveAcesso` | `-1` | 44 digitos. `onChange` chama `isSSW(value, 1)` — lookup servidor, aguardar 10s |
| `--frete-peso` | `id_frt_inf_frete_peso` | — | Dentro do painel colapsavel "parc". Abrir com `showhide('parc')`, **confirmar com click em `#lnk_frt_inf_env`** (NAO `fechafrtparc('C')` — quebra fluxo com null pointer em `doDis`/`concluindo`). Fonte: codegen manual validado (commit `9e6fd75e` reverteu tentativa anterior). |
| `--medidas` | `id_dim_{n}_altu/larg/comp/vezes` | — | Dimensoes de moto. Painel "Volume (m3)": abrir com `showhide('volume')`, confirmar com `acabadim('C')`. Valores em metros. `_vezes` dispara `linhadim()` no blur |

### Campos de volume (dimensoes moto) — emitir_cte_004.py

Painel colapsavel "Volume (m3)" com linhas indexadas (n=1,2,3...):

| Campo SSW (name) | Campo SSW (id) | Tipo | Notas |
|-------------------|----------------|------|-------|
| `id_dim_{n}_altu` | `id_dim_{n}_altu` | currencyedit, 3 casas | Altura em metros |
| `id_dim_{n}_larg` | `id_dim_{n}_larg` | currencyedit, 3 casas | Largura em metros |
| `id_dim_{n}_comp` | `id_dim_{n}_comp` | currencyedit, 3 casas | Comprimento em metros |
| `id_dim_{n}_vezes` | `id_dim_{n}_vezes` | numerico, maxlength 4 | Quantidade. `onblur=linhadim()` calcula cubagem |

Botoes:
- Abrir painel: `<a id="lnk_dim" onclick="showhide('volume')">Volume (m3):</a>`
- Confirmar: `<a id="id_dim_env" onclick="acabadim('C')">►</a>`

Conversao: `carvia_modelos_moto` armazena em CM → dividir por 100 para SSW (metros).

### Campos de consulta — consultar_ctrc_101.py

| Parametro CLI | Campo SSW (id) | Acao AJAX |
|---------------|----------------|-----------|
| `--ctrc` | `t_nro_ctrc` | `ajaxEnvia('P1', 1)` |
| `--nf` | `t_nro_nf` | `ajaxEnvia('P2', 1)` |

### Campos de cancelamento — cancelar_cte_004.py

O script tenta multiplos nomes para cada campo (SSW nao e consistente):

| Campo | Nomes tentados (em ordem) | Fallback |
|-------|---------------------------|----------|
| CTRC | `2`, `ctrc`, `numero`, `num_ctrc`, `nrctrc`, `nr_ctrc` | Primeiro input numerico visivel |
| Motivo | `motivo`, `obs`, `observacao`, `justificativa`, `mot_cancel`, `motivo_cancel` | — |

---

## FIELD_MAP — emitir_cte_complementar_222.py

Mapeamento dos campos preenchidos pelo script no formulario SSW opcao 222 (2 telas: page1 + page2).

### Campos tela inicial (page1) — emitir_cte_complementar_222.py

| Parametro CLI | Campo SSW (id) | Tipo | Notas |
|---------------|----------------|------|-------|
| `--motivo` | `#motivo` | letra | Validos: `C`, `D`, `V`, `E`, `R` |
| filial_pai (extraida do CTRC) | `[id="1"]` | texto | Ex: `"CAR"`. Script extrai do CTRC `FILIAL-NUMERO-DV` |
| ctrc_concatenado (numero+dv, sem hifen) | `[id="2"]` | texto | Ex: `"1139"` para CTRC `113-9`. SEM hifen |

Submit page1: `[id="3"]` (link `►`) → abre popup `page2` via `expect_popup`.

### Campos tela principal (page2) — emitir_cte_complementar_222.py

| Parametro CLI | Campo SSW (id) | Tipo | Notas |
|---------------|----------------|------|-------|
| `--valor-outros` (ou auto-calc) | `#vlr_outros` | currency BR | Formato `"227,90"` (virgula decimal). `click()` + `fill()` |
| `--tp-doc` | `#tp_doc` | letra | Validos: `C`. `click()` + `fill()` |
| `--unid-emit` | `#unid_emit` | letra | Validos: `D`, `O`. `dblclick()` + `fill()`. **Pode vir readonly** — script respeita |

Submit page2: link `►` (via `get_by_role("link", name="►")`) OU fallback `ajaxEnvia('ENV2')` via evaluate.

Loop "Continuar" (MAX=5x): tentativas em ordem
1. `[id="0"]` (link com `onclick` `ajaxEnviah('ENV2', btn_200='S')`)
2. `get_by_role("link", name=re.compile("Continuar"))`
3. `evaluate` scan `querySelectorAll('a')` buscando `onclick` com `btn_200='S'` ou `ajaxEnviah('ENV2'`

Captura "Novo CTRC": dialog nativo `alert()` → regex `Novo CTRC: ([A-Z]+)0*(\d+)-(\d)` em `_capture_dialog`. Handler registrado em `context.on("page", _attach_dialog_handler)` para cobrir todas as pages do context.

### Constantes do script

```python
MOTIVOS_VALIDOS = {'C', 'D', 'V', 'E', 'R'}
TP_DOC_VALIDOS = {'C'}
UNID_EMIT_VALIDOS = {'D', 'O'}
PISCOFINS_DIVISOR = 0.9075   # grossing up PIS/COFINS fixo
```

Grossing up: `valor_calculado = valor_base / PISCOFINS_DIVISOR / (1 - aliquota_icms / 100)`.
Identico ao calculo da rota `app/carvia/routes/custo_entrega_routes.py`.

---

## Fluxo SSW Detalhado

### Emissao (004 → 007 → 101)

```
1. login_ssw()
2. trocar_filial(CAR)
3. abrir_opcao_popup(004)
4. CREATE_NEW_DOC_OVERRIDE (monkey-patch createNewDoc)
5. ajaxEnvia('NORMAL', 1) → formulario CT-e Normal
6. Preencher f13 (placa) → fill() + Tab → aguardar 3s (validacao blur)
7. Campo chaveAcesso aparece automaticamente (popup nfepnl apos Tab no ARMAZEM)
8. Preencher chaveAcesso → fill() + click away → isSSW() lookup → aguardar 10s
9. showhide('parc') → preencher id_frt_inf_frete_peso → fechafrtparc('C')
10. calculafrete(this) → simular frete → aguardar 8s
11. concluindo('C') → GRAVAR → dialogs → capturar CTRC do alert/DOM
12. [--enviar-sefaz] ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024') → aguardar 15s
13. [--consultar-101] abrir opcao 101 → preencher t_nro_ctrc → ajaxEnvia('P1', 1)
```

### Consulta (101)

```
1. login_ssw()
2. Setar filial via elemento #2
3. abrir_opcao_popup(101)
4. Preencher t_nro_ctrc (CTRC) OU t_nro_nf (NF)
5. ajaxEnvia('P1', 1) para CTRC ou ajaxEnvia('P2', 1) para NF
6. CREATE_NEW_DOC_OVERRIDE (so para CTRC, antes do ajax; para NF, 0.5s depois)
7. Extrair 16 campos via regex sobre body.innerText
8. [--baixar-xml] ajaxEnvia('XML', 0) → download ZIP → extrair XML → re-pesquisar
9. [--baixar-dacte] onclick link_imp_dacte → download PDF
```

### Cancelamento (004)

```
1. login_ssw()
2. abrir_opcao_popup(004)
3. CREATE_NEW_DOC_OVERRIDE
4. Encontrar link "Cancelar" (texto match OU 'CAN' em onclick)
5. interceptar_ajax_response → injetar HTML da tela de cancelamento
6. Preencher campo CTRC (multi-estrategia) → ajaxEnvia('PES', 0) → verificar CT-e existe
7. Extrair dados do CT-e (remetente, destinatario, valores, status, chave)
8. [--dry-run] Retornar preview
9. Preencher campo motivo (multi-estrategia)
10. Registrar handler confirm (auto-accept) + listener response
11. ajaxEnvia('CAN', 0) ou ajaxEnvia('EXC', 0) → aguardar 5s SEFAZ
12. Detectar resultado: popup fechou (sucesso), indicadores no body, ou <foc> (erro)
```

---

## Fluxo SSW — CTe Complementar (222)

Fluxo completo do `emitir_cte_complementar_222.py` (11 fases). Baseado em codegen capturado pelo usuario.

```
PRE-FASE: Auto-calculo do valor_outros (se --valor-base fornecido)
   1. Delega para consultar_ctrc_101.py(ctrc=ctrc_num, filial=filial_pai)
   2. Extrai ICMS/ISS (R$) e Valor frete (R$) do body via regex
   3. aliquota = (valor_icms / valor_frete) * 100
   4. valor_outros = valor_base / 0.9075 / (1 - aliquota / 100)

Fase 1:  login_ssw()
Fase 2:  abrir_opcao_popup(222) → popup page1
Fase 3:  Preencher page1:
           #motivo = args.motivo (C/D/V/E/R)
           [id="1"] = filial_pai (extraida do CTRC FILIAL-NUMERO-DV)
           [id="2"] = f"{ctrc_num}{ctrc_dv}" (sem hifen, ex: "1139")
Fase 4:  page1.locator('[id="3"]').click() → expect_popup → popup page2
         await page2.wait_for_load_state("networkidle", timeout=15000)
Fase 5:  Preencher page2:
           #vlr_outros: click() + fill(valor_BR)  (formato "227,90")
           #tp_doc:     click() + fill("C")
           #unid_emit:  evaluate({readonly, value})
                        - Se NAO readonly: dblclick() + fill(args.unid_emit)
                        - Se readonly:     respeita SSW (loga unid_emit_readonly: true)
Fase 6:  Salva HTML page2 antes do submit em /tmp/ssw_operacoes/222_debug_page2_antes_submit.html
         Click ► → 3 estrategias em cascata:
           1. page2.get_by_role("link", name="►").first.click()
           2. evaluate scan onclick contendo "ajaxEnvia('ENV2'"
         Salva HTML page2 apos submit em 222_debug_page2_pos_submit.html
         Loop Continuar (MAX=5x):
           1. page2.locator('[id="0"]').click()
           2. page2.get_by_role("link", name=re.compile("Continuar")).first.click()
           3. evaluate scan onclick contendo "ajaxEnviah('ENV2'" OU "btn_200" + "'S'"
Fase 7:  Capturar CTRC complementar:
           - Fonte 1: dialog nativo "Novo CTRC: FILIAL000NUMERO-DV" capturado por context.on("page", ...)
                      regex: r'Novo CTRC:\s*([A-Z]+)0*(\d+)-(\d)'
           - Fonte 2: fallback scan innerText em todos frames/pages
Fase 8:  Trocar filial no main_frame para filial_complementar (pode ser != filial_pai)
         Via main_frame.evaluate (mesma logica de trocar_filial)
Fase 9:  abrir_opcao_popup(007) → page3.get_by_role("link", name="Enviar à SEFAZ").click(timeout=15000)
Fase 10: abrir_opcao_popup(101) (popup page5)
         Pesquisar CTRC complementar via Enter no #t_nro_ctrc
         baixar XML (ajaxEnvia('XML',0) → response intercept → extrai ZIP → extrai .xml)
         baixar DACTE (extrai onclick de link_imp_dacte → response intercept → grava .pdf)
Fase 11: Retornar resultado consolidado (ver SCRIPTS.md secao 5)
```

---

## Dialogs Automaticos

### emitir_cte_004.py

| Dialog | Tipo | Conteudo (match) | Acao script |
|--------|------|-------------------|-------------|
| Email nao disponivel | `confirm` | "email", "disponivel" | `dismiss()` (rejeita) |
| Confirma emissao | `confirm` | "confirma", "gravar", "emiss" | `accept()` (confirma) |
| CTRC gravado | `alert` | regex `(\d{2,6})` | `accept()` + captura numero |

### cancelar_cte_004.py

| Dialog | Tipo | Acao script |
|--------|------|-------------|
| "Confirma cancelamento?" | `confirm` | `accept()` (confirma) |

### emitir_cte_complementar_222.py

| Dialog | Tipo | Acao script |
|--------|------|-------------|
| "Novo CTRC: XXXNNNNNN-D" | `alert` | `accept()` + regex `r'Novo CTRC:\s*([A-Z]+)0*(\d+)-(\d)'` extrai filial, numero, dv |
| Avisos CFOP/ICMS/GNRE (loop) | link `Continuar` | Click via `[id="0"]` → `get_by_role(name=re.compile("Continuar"))` → `evaluate` scan `btn_200='S'` (loop MAX=5x) |

Handler registrado em `context.on("page", _attach_dialog_handler)` captura dialogs nativos em
TODAS as pages do context (popup 222, page2, page3 SEFAZ, etc.). Mensagens armazenadas em
`dialog_messages` no resultado JSON.

---

## Gotchas de Dominio

### Emissao (004)

1. **Placa ARMAZEM = fracionado**: Indica mercadoria ja no armazem CarVia. Para carga direta (POP-C02), usar placa REAL do veiculo.
2. **isSSW() lookup assincrono**: O campo `chaveAcesso` dispara `isSSW(value, 1)` ao perder foco — busca NF-e no servidor. Aguardar 10s. Se falhar, script tenta fallback via `evaluate()`.
3. **Painel "parc" colapsavel — usar `#lnk_frt_inf_env`**: O campo `id_frt_inf_frete_peso` esta oculto dentro de painel. `showhide('parc')` abre. **Confirmar com click em `#lnk_frt_inf_env`** — NAO `fechafrtparc('C')` (quebra fluxo com null pointer em `doDis`/`concluindo`). Fonte de verdade: codegen manual. Commit `9e6fd75e` reverteu tentativa anterior de usar `fechafrtparc`.
4. **Pre-CTRC != CT-e autorizado**: Apos gravar na 004, o pre-CTRC NAO tem valor fiscal. So se torna CT-e valido apos envio ao SEFAZ via `--enviar-sefaz` (opcao 007).
5. **CREATE_NEW_DOC_OVERRIDE**: Monkey-patch em `createNewDoc()` para manter referencia DOM do Playwright. Sem ele, SSW abre nova janela e Playwright perde controle.
6. **Ordem do override para NF**: Na consulta 101 por NF (`ajaxEnvia('P2', 1)`), o override deve ser aplicado 0.5s DEPOIS do ajax (nao antes), pois interfere com a validacao de NF.
7. **Filial DEVE ser CAR**: Emissao em MTZ ou outra filial produz dados fiscais incorretos.
8. **`errorpanel` bloqueia clicks nativos**: `<div id="errorpanel">` invisivel e sem `pointer-events: none` bloqueia clicks do Playwright em `►` e "Gravar". Script usa `_clicar_simular()` com fallback JS em cascata: `getElementById('lnk_env').click()` → scan `onclick=calculafrete`. Commit `74295621`.
9. **Link "Gravar" nao e literal**: SSW renderiza como "1. Gravar", "1.Gravar", "Gravar", "gravar". SEMPRE usar `re.compile(r"Gravar", re.IGNORECASE)`. Script tem 3 fallbacks: regex → JS click no link com `onclick="concluindo('C')"` → `evaluate("concluindo('C')")` direto. Commit `4428231d`.
10. **Envio SEFAZ NAO e click**: Usar `ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')` em popup pos-gravar. Popup 007 aberto apenas para capturar status fila (Digitados, Enviados, Autorizados, Denegados, Rejeitados) via regex sobre body. Commit `973e9739`.

### Consulta (101)

11. **Apos baixar XML, DOM e substituido**: O download XML aciona `ajaxEnvia('XML', 0)` que substitui o body. O script re-pesquisa automaticamente para restaurar os dados no DOM.
12. **seq_ctrc e familia**: Extraidos do atributo `onclick` de `link_imp_dacte`. Necessarios para downloads de DACTE/XML.

### Cancelamento (004)

13. **Prazo SEFAZ**: 7 dias corridos a partir da data de autorizacao. Apos esse prazo, SEFAZ rejeita.
14. **Manifesto**: Se CT-e foi incluido em Manifesto (MDF-e), cancelar o Manifesto PRIMEIRO na opcao 024.
15. **Mercadoria embarcada**: NAO cancelar CT-e se mercadoria ja saiu. Risco de sinistro sem cobertura de seguro.
16. **Efeitos colaterais SSW**: Cancelamento cancela automaticamente fatura, boleto e averbacao vinculados.
17. **Popup fechou = sucesso**: No SSW, popup fechar apos submit de cancelamento e indicador de sucesso (padrao `TargetClosedError`).
18. **Resultado inconclusivo**: Se nenhum indicador claro (sucesso ou erro), script retorna `status="inconclusivo"`. Verificar manualmente na opcao 101.

### CT-e Complementar (222)

19. **CTRC formato sem hifen**: O campo `[id="2"]` no SSW espera numero+dv concatenados SEM hifen. Ex: CTRC `CAR-113-9` → `[id="2"]="1139"`. Script faz `f"{ctrc_num}{ctrc_dv}"` automaticamente apos `parsear_ctrc()`.
20. **`unid_emit` pode vir readonly**: SSW decide a filial do CTe complementar baseado na carga. Script detecta via `el.readOnly || el.hasAttribute('readonly')` e respeita SSW. Loga `unid_emit_readonly: true` no resultado. NAO tentar forcar com fill.
21. **Pre-requisito do auto-calc**: Para `--valor-base` funcionar, o CTe pai deve estar autorizado e consultavel na opcao 101 da filial correta. Script delega para `consultar_ctrc_101.py` na pre-fase. Se 101 falhar, retorna erro com campo `icms_pai`.
22. **Auto-calculo via grossing up**: `valor_outros = valor_base / 0.9075 / (1 - aliquota_icms / 100)`. Identico a `app/carvia/routes/custo_entrega_routes.py`. Constantes: `PISCOFINS_DIVISOR = 0.9075` (fixo).
23. **Dialog nativo captura CTRC**: SSW usa `alert()` JavaScript ("Novo CTRC: XXX"). Handler em `context.on("page", _attach_dialog_handler)` registra capture em TODAS as pages do context (popup 222, page2, page3 SEFAZ, page5 101). Sem isso, Playwright auto-dismiss perde a mensagem.
24. **Loop "Continuar" (MAX=5x)**: Multiplos avisos CFOP/ICMS/GNRE — normal. Script clica todos via 3 estrategias (`[id="0"]` → role → evaluate). NAO e erro.
25. **`valor_base` vs `valor_outros`**: Mutuamente exclusivos. Script valida em `validar_args()` — passar ambos = erro `ValueError`.

---

## Workflow CT-e Completo

```
1. EMITIR (004)
   emitir_cte_004.py --chave-nfe "..." --frete-peso 600 --placa ARMAZEM --dry-run
   → Confirmar preview
   emitir_cte_004.py --chave-nfe "..." --frete-peso 600 --enviar-sefaz --consultar-101 --baixar-dacte

2. CONSULTAR (101) — a qualquer momento, read-only
   consultar_ctrc_101.py --ctrc 94 --baixar-xml --baixar-dacte

3. CANCELAR (004) — se necessario, dentro de 7 dias
   Checklist pre-cancelamento:
     [ ] Prazo < 7 dias da autorizacao
     [ ] Manifesto cancelado (se existir)
     [ ] Mercadoria NAO embarcada
   cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" --motivo "..." --dry-run
   → Confirmar preview
   cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" --motivo "..."

4. EMITIR COMPLEMENTAR (222) — se precisar ajustar valor/ICMS apos autorizacao
   Checklist pre-complementar:
     [ ] CTe pai autorizado
     [ ] Pai consultavel na 101 da filial correta (para auto-calc funcionar)
     [ ] Motivo definido (C/D/V/E/R)
     [ ] Valor base OU valor final calculado
   emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo D --valor-base 200 --dry-run
   → Confirmar preview
   emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo D --valor-base 200 --enviar-sefaz

POPs relacionados:
  POP-C01: Emitir CT-e fracionado (placa ARMAZEM)
  POP-C02: Emitir CT-e carga direta (placa real)
  POP-C03: Emitir CT-e complementar (opcao 222, auto-calc ICMS via 101 do pai)
  POP-C05: Imprimir CT-e / DACTE
  POP-C06: Cancelar CT-e
```
