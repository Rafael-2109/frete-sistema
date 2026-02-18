---
name: operando-ssw
description: |
  Executa operacoes de escrita no SSW via Playwright. Cadastra unidades (401), cidades atendidas (402), fornecedores (478), transportadoras (485) e comissoes (408). Requer --dry-run na primeira execucao. Usa ssw_defaults.json para valores padrao CarVia.

  USAR QUANDO:
  - Cadastrar unidade: "cadastre unidade CGR no SSW", "criar unidade parceira"
  - Cadastrar cidades: "importar cidades da rota CGR", "adicionar cidades atendidas"
  - Cadastrar fornecedor: "cadastrar CNPJ como fornecedor no SSW"
  - Cadastrar transportadora: "registrar transportadora no SSW"
  - Criar comissao: "vincular unidade a transportadora", "criar comissao 408"
  - Gerar CSVs comissao por cidade: "gerar CSV 408 por cidade", "importar precos por cidade"
  - Importar CSVs comissao por cidade: "importar comissao por cidade no SSW", "importar CSV 408"
  - Implantar rota: "POP-A10", "nova rota completa"

  NAO USAR QUANDO:
  - Consultar/navegar SSW sem alterar → usar **acessando-ssw**
  - Cotacao de frete → usar **cotando-frete**
decision_tree: |
  Cadastrar unidade parceira (tipo T)?
    → cadastrar_unidade_401.py --sigla X --tipo T --razao-social "..." --dry-run
  Importar cidades em massa via CSV (>5 cidades)?
    → importar_cidades_402.py --csv /tmp/cidades.csv --dry-run
  Cadastrar poucas cidades na grid (<5)?
    → cadastrar_cidades_402.py --uf XX --unidade XXX --cidades '[...]' --dry-run
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
Padrao interno: `FIELD_MAP` → `FIELD_LIMITS` → `VALID_OPTIONS` → `validar_campos()` → `montar_campos()` → loop FIELD_MAP → `gerar_saida()`.

---

## Scripts — Referencia Detalhada

**Para parametros completos, FIELD_MAP, limites e gotchas**: LER `SCRIPTS.md`

| # | Script | Opcao | Proposito |
|---|--------|-------|-----------|
| 0 | `ssw_common.py` | — | Funcoes Playwright compartilhadas (login, popup, campos) |
| 1 | `cadastrar_unidade_401.py` | 401 | Cadastrar unidade operacional (31 campos) |
| 2 | `cadastrar_cidades_402.py` | 402 | Cadastrar cidades na grid (<5 cidades) |
| 3 | `importar_cidades_402.py` | 402 | Importar cidades via CSV (>5 cidades) |
| 4 | `cadastrar_fornecedor_478.py` | 478 | Cadastrar fornecedor (12 campos, prerequisito 485/408) |
| 5 | `cadastrar_transportadora_485.py` | 485 | Cadastrar transportadora (3 campos) |
| 6 | `criar_comissao_408.py` | 408 | Criar comissao unidade↔transportadora (5 campos, geral) |
| 7 | `gerar_csv_comissao_408.py` | 408 | Gerar CSVs comissao por cidade (238 cols, importacao em lote) |
| 8 | `importar_comissao_cidade_408.py` | 408 | Importar CSVs de comissao por cidade no SSW via Playwright |

---

## Fluxo Completo: Nova Rota (POP-A10)

1. **401** — Cadastrar unidade parceira
2. **402** — Cadastrar cidades atendidas
3. **403** — Cadastrar rota CAR → [SIGLA] (manual / futuro)
4. **478** — Cadastrar fornecedor
5. **485** — Cadastrar transportadora
6. **408** — Cadastrar comissao de unidade
7. **420** — Cadastrar tabelas de preco (futuro)
8. **002** — Verificar cotacao (futuro)

---

## References (sob demanda)

| Gatilho | Reference a Ler |
|---------|-----------------|
| Cadastrar unidade passo-a-passo | `POP-A02-cadastrar-unidade-parceira.md` |
| Cadastrar cidades passo-a-passo | `POP-A03-cadastrar-cidades.md` |
| Implantar rota completa | `POP-A10-implantar-nova-rota.md` |
| FIELD_MAP, limites, erros SSW | `SCRIPTS.md` |
