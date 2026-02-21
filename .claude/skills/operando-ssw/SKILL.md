---
name: operando-ssw
description: >-
  Esta skill deve ser usada quando o usuario precisa executar operacoes de
  escrita no SSW: "cadastre unidade CGR", "importar cidades da rota",
  "cadastrar CNPJ como fornecedor", "registrar transportadora", "criar
  comissao", ou cotar frete via opcao 002. Requer --dry-run na primeira
  execucao e confirmacao do usuario antes da execucao real.
  Nao usar para consultar documentacao SSW (usar acessando-ssw), cotacao de
  frete interna Nacom (usar cotando-frete), ou navegar no SSW sem operacao
  especifica (usar browser tools diretamente).
  - Criar comissao: "vincular unidade a transportadora", "criar comissao 408"
  - Gerar CSVs comissao por cidade: "gerar CSV 408 por cidade", "importar precos por cidade"
  - Importar CSVs comissao por cidade: "importar comissao por cidade no SSW", "importar CSV 408"
  - Cotar frete no SSW: "cotar frete na 002", "simular frete SSW", "cotacao SSW"
  - Implantar rota: "POP-A10", "nova rota completa"

  NAO USAR QUANDO:
  - Consultar/navegar SSW sem alterar → usar **acessando-ssw**
  - Cotacao de frete INTERNA (sistema local) → usar **cotando-frete**
decision_tree: |
  Cadastrar unidade parceira (tipo T)?
    → cadastrar_unidade_401.py --sigla X --tipo T --razao-social "..." --dry-run
  Alterar/importar cidades na 402 (qualquer quantidade)?
    → PREFERIR CSV: exportar_cidades_402.py --uf XX → modificar → importar_cidades_402.py --csv /tmp/cidades.csv --dry-run [--timeout 30]
  Cadastrar 1-3 cidades VISIVEIS na grid 402?
    → cadastrar_cidades_402.py --uf XX --unidade XXX --cidades '[...]' --dry-run
    (LIMITACAO: so funciona com cidades no viewport da virtual scroll)
  Cadastrar/ativar fornecedor (478)?
    → cadastrar_fornecedor_478.py --cnpj X --nome "..." --especialidade TRANSPORTADORA --dry-run
  Cadastrar transportadora (485)?
    → cadastrar_transportadora_485.py --cnpj X --nome "..." --dry-run
  Criar comissao de unidade (408, geral)?
    → criar_comissao_408.py --unidade XXX --cnpj X --dry-run
  Gerar CSVs comissao por cidade (408, em lote)?
    → gerar_csv_comissao_408.py --excel /tmp/backup_vinculos.xlsx [--unidades BVH,CGR] --dry-run
  Importar CSVs comissao por cidade no SSW (408)?
    → importar_comissao_cidade_408.py --csv-dir /tmp/ssw_408_csvs/ [--unidades BVH,CGR] --dry-run
  Cotar frete no SSW (002)?
    → Perguntar: CNPJ pagador, CEP destino, peso, valor, coletar(S/N), entregar(S/N)
    → Se coletar=N: script auto-resolve CEP origem = CEP CarVia (06530581)
    → Se coletar=S: perguntar CEP origem (local de coleta)
    → cotar_frete_ssw_002.py --cnpj-pagador X --cep-destino X --peso X --valor X [--coletar N] [--entregar S] --dry-run
    → Exibir parametros_assumidos antes de confirmar
  Consultar/navegar SSW (sem alterar)?
    → NÃO usar esta skill. Usar **acessando-ssw**
allowed-tools: Read, Bash, Glob, Grep
---

# operando-ssw

Executa operacoes de **ESCRITA** no SSW via scripts Playwright standalone.
Separada de `acessando-ssw` (apenas consulta/documentacao).

---

## REGRAS CRITICAS

1. `--dry-run` e **OBRIGATORIO** na primeira execucao — preview sem submeter
2. Screenshot capturado antes de qualquer submit — evidencia do formulario
3. Agente DEVE usar AskUserQuestion para confirmar antes de executar sem --dry-run
4. Ordem obrigatoria para nova rota: 401 → 402 → 478 → 485 → 408

---

## Arquitetura

```
Agente Web
  1. Le ssw_defaults.json (campos padronizados CarVia)
  2. AskUserQuestion (campos variaveis: sigla, UF, razao social)
  3. Monta parametros completos (defaults + respostas)
  4. Executa script --dry-run → preview
  5. AskUserQuestion ("Confirmar execucao?")
  6. Executa script sem --dry-run → submete de verdade
```

Scripts sao standalone (Playwright headless), NAO dependem do Flask app.

**Padrao interno**: `FIELD_MAP` → `FIELD_LIMITS` → `VALID_OPTIONS` → `validar_campos()` → `montar_campos()` → loop FIELD_MAP → `gerar_saida()`.

---

## Scripts

| # | Script | Opcao | Proposito |
|---|--------|-------|-----------|
| 0 | `ssw_common.py` | — | Funcoes Playwright compartilhadas (login, popup, campos) |
| 1 | `cadastrar_unidade_401.py` | 401 | Cadastrar unidade operacional (31 campos) |
| 2 | `cadastrar_cidades_402.py` | 402 | Cadastrar 1-3 cidades visiveis na grid (ATU limitado) |
| 3 | `exportar_cidades_402.py` | 402 | Exportar CSV de cidades atendidas (passo 1 workflow CSV) |
| 4 | `importar_cidades_402.py` | 402 | Importar cidades via CSV (PREFERIDO para bulk) |
| 5 | `cadastrar_fornecedor_478.py` | 478 | Cadastrar fornecedor (12 campos, prerequisito 485/408) |
| 6 | `cadastrar_transportadora_485.py` | 485 | Cadastrar transportadora (3 campos) |
| 7 | `criar_comissao_408.py` | 408 | Criar comissao unidade↔transportadora (5 campos, geral) |
| 8 | `gerar_csv_comissao_408.py` | 408 | Gerar CSVs comissao por cidade (238 cols, lote) |
| 9 | `importar_comissao_cidade_408.py` | 408 | Importar CSVs de comissao por cidade no SSW |
| 10 | `cotar_frete_ssw_002.py` | 002 | Cotar frete no SSW (simular proposta) |

---

## References (carregar sob demanda)

| Quando o agente precisa de... | Ler |
|-------------------------------|-----|
| Cadastrar unidade/cidade/fornecedor/transportadora (401, 402, 478, 485) | [CADASTROS.md](references/CADASTROS.md) |
| Criar comissao, gerar/importar CSV 408 | [COMISSOES.md](references/COMISSOES.md) |
| Cotar frete na 002 (params, workflow, gotchas) | [COTACAO.md](references/COTACAO.md) |
| Funcoes ssw_common, defaults, batch, mapeamento | [SSW_COMMON.md](references/SSW_COMMON.md) |
| Cadastrar unidade passo-a-passo | `POP-A02-cadastrar-unidade-parceira.md` |
| Cadastrar cidades passo-a-passo | `POP-A03-cadastrar-cidades.md` |
| Implantar rota completa | `POP-A10-implantar-nova-rota.md` |

---

## Fluxo Completo: Nova Rota (POP-A10)

1. **401** — Cadastrar unidade parceira
2. **402** — Cadastrar cidades atendidas
3. **403** — Cadastrar rota CAR → [SIGLA] (manual / futuro)
4. **478** — Cadastrar fornecedor
5. **485** — Cadastrar transportadora
6. **408** — Cadastrar comissao de unidade
7. **420** — Cadastrar tabelas de preco (futuro)
8. **002** — Verificar cotacao (`cotar_frete_ssw_002.py`)
