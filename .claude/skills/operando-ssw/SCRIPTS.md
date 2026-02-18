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

Cadastra cidades individualmente na grid da 402. Usar para poucas cidades (<5).

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

---

## importar_cidades_402.py

Importa cidades atendidas via CSV na opcao 402. Metodo preferido para bulk (>5 cidades).

```bash
python .claude/skills/operando-ssw/scripts/importar_cidades_402.py \
  --csv /tmp/cidades_cgr.csv --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --csv | Sim | Caminho do CSV (formato 402, separador `;`, ISO-8859-1) |
| --dry-run | -- | Valida CSV sem importar |

**Formato CSV**: 45 colunas, separador `;`, encoding ISO-8859-1.
Colunas essenciais: UF, CIDADE, UNIDADE, POLO, TIPO_FRETE, RESTRITA, COLETA, ENTREGA, PRAZO_ENTREGA.

**CRITICO**: A tela de importacao DEVE ser popup nativo (NAO usar `createNewDoc` override).

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
| VDC, EUN, IOS, BPS, FEI, TXF | REIS ARAGAO | 17706435000230 |
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
