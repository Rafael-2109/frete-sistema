# SCRIPTS.md — operando-ssw

Documentacao detalhada: FIELD_MAP, limites, gotchas e batch operations para escrita no SSW.

---

## ssw_common.py

Funcoes Playwright reutilizaveis compartilhadas por todos os scripts.

| Funcao | Descricao |
|--------|-----------|
| `verificar_credenciais()` | Valida env vars SSW obrigatorias |
| `carregar_defaults(path)` | Carrega ssw_defaults.json |
| `login_ssw(page)` | Login no SSW (reutiliza sessao ativa) |
| `abrir_opcao_popup(context, frame, opcao)` | Navega para opcao e captura popup |
| `interceptar_ajax_response(popup, frame, action)` | Executa acao e intercepta response HTML |
| `injetar_html_no_dom(popup, html)` | Injeta HTML via `document.write()` |
| `preencher_campo_js(popup, field, value)` | Preenche campo SEM eventos (evita geocoding) |
| `preencher_campo_no_html(popup, field, value)` | Preenche campo COM eventos change/input |
| `preencher_campo_inline(frame, field_id, value)` | Preenche campo em grids (402) |
| `capturar_campos(target)` | Captura snapshot de todos campos visiveis |
| `capturar_screenshot(page, nome)` | Screenshot para evidencia |
| `gerar_saida(sucesso, **kwargs)` | Output JSON padrao |
| `verificar_mensagem_ssw(popup)` | Verifica erro/sucesso no DOM |

**Env vars obrigatorias**: `SSW_URL`, `SSW_DOMINIO`, `SSW_CPF`, `SSW_LOGIN`, `SSW_SENHA`

**createNewDoc override** (obrigatorio em TODA operacao de popup):
```javascript
createNewDoc = function(pathname) {
    document.open("text/html", "replace");
    document.write(valSep.toString());
    document.close();
    if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
};
```
Sem isso, `ajaxEnvia()` tenta abrir nova janela em vez de atualizar DOM.

---

## cadastrar_unidade_401.py

Cadastra nova unidade operacional. 31 campos com defaults do ssw_defaults.json.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_unidade_401.py \
  --sigla CGR --tipo T --razao-social "ALEMAR - CAMPO GRANDE/MS" \
  --nome-fantasia "ALEMAR CGR" [--ie "ISENTO"] [--cnpj 62312605000175] \
  [--defaults-file .claude/skills/operando-ssw/ssw_defaults.json] --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --sigla | Sim | Codigo IATA 3 chars (ex: CGR, CWB, POA) |
| --tipo | Nao | T=Terceiro, F=Filial, M=Matriz (default: T) |
| --razao-social | Sim | Max 45 chars. Padrao: "[Parceiro] - [Cidade]/[UF]" |
| --nome-fantasia | Nao | Max 30 chars (default: razao social truncada) |
| --cnpj | Nao | 14 digitos (default: CNPJ CarVia do ssw_defaults.json) |
| --ie | Nao | Inscricao Estadual (vazio se isento) |
| --dry-run | -- | Preview sem submeter |

**Regra tipo T**: Usa CNPJ, IE, banco e dados fiscais da CarVia (nao do parceiro). Veja POP-A02.

---

## cadastrar_cidades_402.py

Cadastra cidades individualmente na grid da 402. Usar SOMENTE para 1-3 cidades que estejam no viewport.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_cidades_402.py \
  --uf MS --unidade CGR \
  --cidades '[{"cidade":"CAMPO GRANDE","polo":"P","prazo":2}]' --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --uf | Sim | UF para filtrar cidades (ex: MS, SP) |
| --unidade | Sim | Sigla da unidade responsavel (ex: CGR) |
| --cidades | Sim | JSON array com objetos {cidade, polo, prazo, ...} |
| --dry-run | -- | Preview sem submeter |

Campos obrigatorios por cidade: `cidade`, `polo` (P/R/I). `prazo` recomendado.
Demais campos usam defaults do ssw_defaults.json se omitidos.

**LIMITACAO CRITICA**: SSW 402 usa **virtual scroll** — apenas ~90 cidades existem no DOM por vez
(de 400+ por UF). Cidades fora do viewport NAO podem ser alteradas via ATU.
A injecao de hidden inputs (Estrategia 2/XML) localiza a cidade mas o **ATU falha** no submit
("Erro ao processar a requisição"). **Para >3 cidades ou cidades fora do viewport, USAR `importar_cidades_402.py`**.

---

## exportar_cidades_402.py

Exporta CSV completo de cidades atendidas de uma UF na 402. Passo 1 do workflow CSV (exportar → modificar → importar).

```bash
python .claude/skills/operando-ssw/scripts/exportar_cidades_402.py \
  --uf BA [--output /tmp/ba_402_export.csv] [--dry-run]
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --uf | Sim | UF para exportar (ex: BA, SP, MS) |
| --output | Nao | Caminho do CSV (default: /tmp/{uf}_402_export.csv) |
| --dry-run | -- | Mostra o que seria exportado sem executar |

**Mecanismo**: Abre 402, preenche UF, chama `_MOD_CSV` na tela INICIAL (ANTES de VIS_UF), captura CSV via 3 estrategias (download handler, response interceptor, JS variable).

**CRITICO**: `_MOD_CSV` so funciona na tela INICIAL. Apos VIS_UF o botao CSV desaparece.

**Retorno JSON**:
```json
{
  "sucesso": true,
  "arquivo": "/tmp/ba_402_export.csv",
  "uf": "BA",
  "total_linhas": 417,
  "total_colunas": 45,
  "cidades_com_unidade": 388,
  "cidades_sem_unidade": 29,
  "unidades_encontradas": ["BPS", "EUN", "SSA", "VCQ", "VDC"],
  "amostra": "BA;ABAIRA;VCQ;I;A;..."
}
```

**CSV exportado**: 45 colunas, separador `;`, encoding ISO-8859-1. Preserva formato exato do SSW (feriados `00/00`, sabado ` `, trailing `;`).

---

## importar_cidades_402.py

Importa cidades atendidas via CSV na opcao 402. **Metodo PREFERIDO para qualquer alteracao bulk.**

```bash
python .claude/skills/operando-ssw/scripts/importar_cidades_402.py \
  --csv /tmp/cidades_cgr.csv --dry-run

python .claude/skills/operando-ssw/scripts/importar_cidades_402.py \
  --csv /tmp/cidades_cgr.csv --timeout 30
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --csv | Sim | Caminho do CSV (formato 402, separador `;`, ISO-8859-1) |
| --dry-run | -- | Valida CSV sem importar |
| --timeout | -- | Timeout em segundos apos IMPORTA2 (default: 20). Aumentar para CSVs grandes |

**Formato CSV**: 45 colunas, separador `;`, encoding ISO-8859-1.
Colunas essenciais: UF, CIDADE, UNIDADE, POLO, TIPO_FRETE, RESTRITA, COLETA, ENTREGA, PRAZO_ENTREGA.

**CRITICO — PRACA_COMERCIAL**: Para INCLUIR cidades novas (sem UNIDADE existente no SSW),
o CSV DEVE ter o campo PRACA_COMERCIAL (indice 15) = UNIDADE + POLO (ex: "SSAI", "JPAI").
Sem este campo, cidades sem UNIDADE sao silenciosamente ignoradas pelo SSW.

**FIX MULTIPART**: Playwright `set_input_files()` registra arquivo no DOM, mas `ajaxEnvia('IMPORTA2')`
envia body vazio no POST multipart para ssw0475. Script intercepta via `page.route()` e reconstroi
o body com bytes reais do CSV.

### Retorno

```json
{
  "sucesso": true,
  "resposta": "Processamento concluido. Inclusoes: 2 Alteracoes: 15 Nao inclusas: 3",
  "inclusoes": 2,
  "alteracoes": 15,
  "nao_inclusas": 3
}
```

**Contadores SSW**: Inclusoes = cidades novas adicionadas. Alteracoes = cidades existentes atualizadas.
Nao inclusas = cidades com valores IDENTICOS ao SSW (NAO significa "nao sobrescreve").

### Workflow recomendado: Exportar → Modificar → Importar

Para alterar cidades existentes (mudar unidade, polo, prazo), o fluxo mais confiavel e:

1. **Exportar CSV atual do SSW**: `exportar_cidades_402.py --uf XX`
   - CSV exportado preserva todos 45 campos exatamente como SSW espera
2. **Modificar CSV com Python**:
   - Ler CSV (encoding ISO-8859-1, separador `;`)
   - Alterar somente campos necessarios (UNIDADE, POLO, PRAZO, etc.)
   - Preservar todos os demais campos (feriados, distancias, pracas) intactos
   - Pode filtrar para incluir somente cidades alteradas (reduz risco)
3. **Importar CSV modificado**: `importar_cidades_402.py --csv /tmp/modificado.csv`
   - SSW atualiza cidades existentes ("Alteracoes: N") e adiciona novas ("Inclusoes: N")

**IMPORTANTE**: Gerar CSV do zero (sem exportar primeiro) e fragil — formatos de feriado
(`00/00` vs vazio), sabado (espaco vs vazio) e trailing `;` causam 0 matches na importacao.

---

## cadastrar_fornecedor_478.py

Cadastra fornecedor no SSW. Prerequisito para 485 e 408.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_fornecedor_478.py \
  --cnpj 42769176000152 --nome "UNI BRASIL TRANSPORTES" \
  --especialidade TRANSPORTADORA [--ie ISENTO] [--contribuinte N] \
  [--ddd 11] [--telefone 30001234] [--cep 06460040] \
  [--logradouro "RUA JOSE SOARES"] [--numero 100] [--bairro JAGUARE] \
  [--fg-cc N] [--defaults-file ssw_defaults.json] --dry-run
```

**FIELD_MAP** (12 campos):

| Parametro CLI | Campo SSW | Limite | Obrigatorio |
|---------------|-----------|--------|-------------|
| cnpj | `2` (id) | 14 | Sim |
| nome | `nome` | 45 | Sim |
| inscr_estadual | `inscr_estadual` | 20 | Nao (default: ISENTO) |
| contribuinte | `contribuinte` | 1 | Nao (default: N) |
| especialidade | `especialidade` | — | Nao (default: TRANSPORTADORA) |
| ddd | `ddd_principal` | 2 | Nao |
| telefone | `fone_principal` | 8 | Nao |
| cep | `cep_end` | 8 | Nao |
| logradouro | `logradouro` | 40 | Nao |
| numero | `numero_end` | 10 | Nao |
| bairro | `bairro_end` | 30 | Nao |
| fg_cc | `fg_cc` | 1 | Nao (default: N) |

**Validacoes especiais**: CNPJ 14 digitos. DDD: rejeita '00', '01'. Telefone: rejeita '00000000', '99999999', min 8 digitos.

**Fluxo SSW**: CNPJ → `ajaxEnvia('PES', 0)` → preencher campos → `ajaxEnvia('GRA', 0)`

**Campo `inclusao` (hidden)**:
- `S` = registro em modo de inclusao, NAO finalizado
- Ausente do DOM = registro finalizado/salvo
- **GOTCHA CRITICO**: Se `inclusao=S`, a opcao 408 rejeita o CNPJ com "CNPJ nao cadastrado como fornecedor"
- **Causa**: Campos obrigatorios faltando impedem o GRA de finalizar o registro
- **Solucao**: Preencher TODOS os campos obrigatorios e re-executar GRA

**Campo `fg_cc` (Conta Corrente Fornecedor)**:
- `N` = CCF inativa (padrao seguro para cadastro)
- `S` = CCF ativa — **REQUER** campo `evento` preenchido (ex: 5224 = REDESPACHO)
- **Recomendacao**: Cadastrar com `fg_cc='N'` na 478. CCF NAO e prerequisito para 408.

**Erros comuns no GRA**:

| Mensagem SSW | Causa | Solucao |
|-------------|-------|---------|
| "Informe a especialidade do fornecedor" | `especialidade` vazio | Preencher com 'TRANSPORTADORA' |
| "DDD do telefone invalido" | DDD = '01' ou '00' | Usar DDD real (ex: '11' SP, '92' AM) |
| "Telefone invalido" | '00000000' ou '99999999' | Usar formato valido: '30001234' |
| "Informar ISENTO ou codigo em Inscricao Estadual" | `inscr_estadual` vazio | Preencher com 'ISENTO' |
| "Endereco invalido" | Campos de endereco vazios | Preencher cep, logradouro, numero, bairro |
| "Se o fornecedor possui conta corrente..." | `fg_cc='S'` sem `evento` | Salvar com `fg_cc='N'` |

---

## cadastrar_transportadora_485.py

Cadastra transportadora no SSW. Mais simples que 478.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_transportadora_485.py \
  --cnpj 42769176000152 --nome "UNI BRASIL TRANSPORTES" [--ativo S] --dry-run
```

**FIELD_MAP** (3 campos):

| Parametro CLI | Campo SSW | Limite | Obrigatorio |
|---------------|-----------|--------|-------------|
| cnpj | `2` (id) | 14 | Sim |
| nome | `nome` | 45 | Sim |
| ativo | `fg_ativo` | 1 | Nao (default: S) |

**Fluxo SSW**: CNPJ → `ajaxEnvia('PES', 0)` → preencher → `ajaxEnvia('INC', 0)`

**Deteccao de existencia**: Apos PES, checar se `nome` esta preenchido no DOM. Se sim, transportadora ja existe.

**LIMITACAO**: Se o CNPJ raiz tem multiplas filiais cadastradas, PES pode retornar uma **lista**
em vez do formulario individual. Nesse caso, o script da timeout ("Timeout aguardando form 485 apos PES")
e o screenshot mostra a listagem. **Workaround**: verificar visualmente no screenshot se a transportadora
com a sigla desejada ja existe na lista.

---

## criar_comissao_408.py

Cria comissao de unidade no SSW. Vincula unidade a transportadora com despachos.

```bash
python .claude/skills/operando-ssw/scripts/criar_comissao_408.py \
  --unidade VIX --cnpj 42769176000152 [--data-inicio 180226] \
  [--despacho-exp "1,00"] [--despacho-rec "1,00"] \
  [--defaults-file ssw_defaults.json] --dry-run
```

**FIELD_MAP** (5 campos):

| Parametro CLI | Campo SSW | Limite | Obrigatorio |
|---------------|-----------|--------|-------------|
| unidade | `2` (id) | 3 | Sim |
| cnpj | `3` (id) | 14 | Sim |
| data_inicio | `data_ini` | 6 | Nao (default: 180226) |
| despacho_exp | `exp_emit_despacho_pol` | 10 | Nao (default: 1,00) |
| despacho_rec | `rec_dest_despacho_pol` | 10 | Nao (default: 1,00) |

**Fluxo SSW**: Unidade → `ajaxEnvia('ENV', 1)` → preencher CNPJ + campos → `ajaxEnvia('ENV2', 0)`

**Deteccao de existencia**: Apos ENV, checar `document.getElementById('acao')?.value`:
- `'A'` = comissao ja existe para esta unidade
- `'I'` ou outro = inclusao (nao existe ainda)

**Deteccao de sucesso**: Popup fecha automaticamente (TargetClosedError). Popup aberto = erro.

**Erros comuns**:

| Mensagem SSW | Causa | Solucao |
|-------------|-------|---------|
| "CNPJ nao cadastrado como fornecedor" | 478 com `inclusao=S` (nao finalizado) | Corrigir 478 primeiro |
| "CNPJ nao cadastrado como fornecedor" | Fornecedor nao existe na 478 | Cadastrar na 478 primeiro |
| (popup nao fecha, sem mensagem) | Nao cadastrado como transportadora na 485 | Cadastrar na 485 primeiro |

**Prerequisitos**: 478 finalizado (`inclusao` != 'S') + 485 cadastrado + 401 unidade existente.

---

## gerar_csv_comissao_408.py

Gera CSVs de comissao **por cidade** para importacao em lote na 408. Nao usa Playwright — Python puro (pandas + csv).

```bash
python .claude/skills/operando-ssw/scripts/gerar_csv_comissao_408.py \
  --excel /tmp/backup_vinculos.xlsx \
  [--aba Sheet] \
  [--output-dir /tmp/ssw_408_csvs/] \
  [--unidades BVH,CGR] \
  [--template ../comissao_408_template.json] \
  [--dry-run]
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --excel | Sim | Caminho do Excel com precos por cidade (backup_vinculos.xlsx) |
| --aba | Nao | Nome da aba (default: Sheet) |
| --output-dir | Nao | Diretorio de saida (default: /tmp/ssw_408_csvs/) |
| --unidades | Nao | Filtrar por IATA virgula-sep (ex: BVH,CGR). Sem = todas |
| --template | Nao | Caminho do template JSON (default: ../comissao_408_template.json) |
| --dry-run | -- | Mostra estatisticas sem gerar arquivos |

**Formato CSV de saida**: 238 colunas, separador `;`, encoding ISO-8859-1, decimais com virgula.
- Linha 1: metadata (descricao das colunas de origem)
- Linha 2: headers (nomes das 238 colunas)
- Linhas 3+: dados (2 linhas por cidade: E=expedicao, R=recepcao)

**Conversoes Excel → CSV** (verificadas contra BVH/Colorado do Oeste):

| Excel (col#, nome) | CSV targets | Conversao |
|---|---|---|
| 21, Acr. Frete | EXP/REC_1_PERC_FRETE_* | x100 (decimal → %) |
| 18, GRIS/ADV | EXP/REC_2_PERC_VLR_MERC_* | x100 (decimal → %) |
| 19, DESPACHO/CTE/TAS | EXP/REC_3_DESPACHO_* | as-is (R$) |
| 17, FRETE PESO | EXP/REC_3_APOS_ULT_FX_* | x1000 (R$/KG → R$/TON) |
| 16, VALOR MINIMO | EXP/REC_4_MINIMO_R$_* | as-is (R$) |
| 20, PEDAGIO | EXP/REC_5_PEDAGIO_FRACAO_100KG | as-is (R$) |

**POLO/REGIAO/INTERIOR**: Recebem o MESMO valor (comissao por cidade).

**CIDADE/UF**: `{CIDADE_UPPERCASE_SEM_ACENTO}/{UF}` (ex: `COLORADO DO OESTE/RO`). Apostrofos e hifens sao convertidos para espaco (SSW usa `D OESTE`, nao `D'OESTE`).

**Template**: `comissao_408_template.json` contem 238 headers, metadata, 202 defaults e 6 conversoes. Extraido do BVH CSV de referencia.

**Cada linha (E ou R) contem ambas as secoes EXP e REC** preenchidas com os mesmos valores. O campo EXPEDICAO/RECEPCAO identifica o tipo, mas os dados sao duplicados.

**Importacao no SSW**: Usar `importar_comissao_cidade_408.py` (Playwright automatizado).

---

## importar_comissao_cidade_408.py

Importa CSVs de comissao por cidade na opcao 408 do SSW via Playwright. Suporta importacao individual ou em lote.

```bash
# Importar uma unidade:
python .claude/skills/operando-ssw/scripts/importar_comissao_cidade_408.py \
  --csv /tmp/ssw_408_csvs/BVH_comissao_408.csv --unidade BVH --dry-run

# Importar todas (lote):
python .claude/skills/operando-ssw/scripts/importar_comissao_cidade_408.py \
  --csv-dir /tmp/ssw_408_csvs/ [--unidades BVH,CGR,SSA] --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --csv | Sim* | Caminho do CSV (modo individual) |
| --unidade | Nao | Sigla IATA (auto-detectado do nome se omitido) |
| --csv-dir | Sim* | Diretorio com CSVs `*_comissao_408.csv` (modo lote) |
| --unidades | Nao | Filtrar por IATA virgula-sep (sem = todas) |
| --dry-run | -- | Valida CSVs sem importar |

*Obrigatorio: `--csv` OU `--csv-dir` (um dos dois). Default: `/tmp/ssw_408_csvs/`.

**Fluxo SSW por unidade**:
1. Abrir 408 popup
2. Preencher unidade no campo `f2` (id='2')
3. `ajaxEnvia('CSV_CID', 1)` → abre popup de importacao
4. Upload CSV via `<input type="file">`
5. `ajaxEnvia('IMP_CSV', 0)` → submete importacao
6. Coleta resultado: "Tabelas incluídas: N Alteradas: N Não inclusas: N"
7. Fechar popups e repetir proxima unidade

**AJAX actions (descobertos via exploracao DOM)**:
- `CSV_CID` (flag 1) — Abre popup de importacao CSV para cidade
- `IMP_CSV` (flag 0) — Submete a importacao do CSV carregado
- `LINK_CID` (flag 1) — Visualiza tabelas especificas por cidade
- `LINK_DOWN_CID` (flag 0) — Baixa CSV das tabelas por cidade

**Validacao pre-import**: 238 colunas, headers corretos, formato CIDADE/UF, tipos E/R.

**Resposta SSW**: "Processamento concluído. Tabelas incluídas: N Alteradas: N Não inclusas: N"
- HTML entities decodificadas automaticamente (`&iacute;` → `í`, etc.)
- "Incluidas" = novas (nao existiam). "Alteradas" = existiam com valores diferentes (atualizadas). "Nao inclusas" = existiam com mesmos valores (nenhuma alteracao necessaria). O SSW SOBRESCREVE dados existentes quando valores diferem.

**Prerequisitos**:
- CSVs gerados por `gerar_csv_comissao_408.py` (238 cols, `;`, ISO-8859-1)
- Comissao geral ja existente (`criar_comissao_408.py`)
- Credenciais SSW no .env

**Pausa entre unidades**: 3 segundos entre imports para nao sobrecarregar SSW.

---

## Sequencia de Execucao Batch

Para registrar N transportadoras em lote:

```
1. Batch 478 (fornecedores):
   Para cada CNPJ: PES → preencher campos obrigatorios → GRA
   Verificar: inclusao != 'S' (registro finalizado)

2. Batch 485 (transportadoras):
   Para cada CNPJ: PES → preencher nome + ativo → INC/GRA
   Verificar: nome preenchido no DOM

3. Batch 408 (comissoes):
   Para cada unidade: ENV → preencher CNPJ + data + despacho → ENV2
   Verificar: popup fecha (sucesso) ou acao='A' (ja existe)
```

**IMPORTANTE**: Executar na ordem 478 → 485 → 408.

---

## Mapeamento: Unidade → Transportadora (POP-A10 Feb/2026)

| Unidades | Transportadora | CNPJ |
|----------|---------------|------|
| SSA, JPA, MCZ, NAT | CAZAN | 07797011000193 |
| FLN, AJU, CWB, PAS, POA | DAGO | 11758701000100 |
| VIX | UNI BRASIL | 42769176000152 |
| OAL, LDB, MGF, PVH | TRANSPEROLA | 44433407000188 |
| PAU | MONTENEGRO | 22188831000252 |
| VDC, EUN, IOS, BPS, FEI, TXF, VCQ | REIS ARAGAO | 17706435000744 (VCQ) / 17706435000230 (demais) |
| MAO | ACOLOGIS | 40272996000109 |
| GIG | TRANSMENEZES | 20341933000150 |

**Total**: 23 unidades, 8 transportadoras. 23/23 comissoes 408 criadas (2026-02-18).

---

## Licoes Aprendidas (Feb/2026)

1. **DDD '01' nao existe** — SSW valida DDDs reais. Usar DDD da cidade sede do parceiro.
2. **Telefone generico**: '30001234' funciona; '00000000' e '99999999' sao rejeitados.
3. **`inclusao=S` e bloqueante**: Fornecedor com `inclusao=S` na 478 bloqueia 408 silenciosamente.
4. **CCF (`fg_cc`) NAO e prerequisito para 408**: Muitas transportadoras operam com `fg_cc=N`.
5. **`especialidade` e obrigatoria**: Sem ela, GRA na 478 rejeita silenciosamente.
6. **Acentos nas mensagens SSW**: Comparar texto normalizado (sem acentos) ou usar ambas formas.
7. **Popup fecha = sucesso na 408**: TargetClosedError e indicador de ENV2 bem-sucedido.
8. **Sempre verificar apos GRA**: Re-abrir 478, PES novamente e conferir que `inclusao` sumiu.
9. **Response interceptor pode capturar resposta errada**: SSW envia multiplas responses AJAX. O interceptor `/bin/ssw` pode pegar uma resposta de versao ("v.10.2") em vez do resultado real. Usar `html.unescape()` nas respostas para decodificar `&iacute;` etc.
10. **"Nao inclusas" na 408 = valores identicos**: SSW compara dados existentes com CSV. Se iguais → "nao inclusas". Se diferentes → "alteradas" (sobrescreve). NAO precisa excluir para atualizar.
11. **Apostrofos em nomes de cidade**: SSW usa espaco onde IBGE usa apostrofo. `D'OESTE` → `D OESTE`, `D'AGUA` → `D AGUA`, `GRAO-PARA` → `GRAO PARA`. O script `gerar_csv_comissao_408.py` normaliza automaticamente (apostrofo e hifen → espaco). Excecoes SSW-especificas (ex: `OLHO-D AGUA DO BORGES`) requerem correcao manual.
12. **JANUARIO CICCO/RN**: Cidade nao existe no cadastro SSW (402). Ignorar na importacao.
13. **402 ATU com hidden inputs NAO funciona**: Injetar `<input type="hidden">` para cidades fora do virtual scroll e submeter via ATU resulta em "Erro ao processar a requisicao". O SSW nao reconhece inputs injetados. Usar CSV import (exportar → modificar → importar) em vez de ATU para cidades fora do viewport.
14. **402 _MOD_CSV deve ser chamado ANTES de VIS_UF**: O botao CSV esta na tela INICIAL da 402. Apos VIS_UF, a tela muda e o botao desaparece. Para exportar: preencher UF → `_MOD_CSV` (sem VIS_UF antes).
15. **402 CSV formato exato**: Feriados usam `00/00` (NAO vazio), sabado usa ` ` (espaco, NAO vazio), trailing `;` apos ultimo campo. CSV gerado do zero sem esses detalhes resulta em 0 matches na importacao.
16. **485 timeout com multiplas filiais**: Se CNPJ raiz tem multiplas filiais na 485, PES retorna lista em vez de formulario. Script da timeout. Verificar screenshot para confirmar existencia.
