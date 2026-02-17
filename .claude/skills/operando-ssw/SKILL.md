---
description: Executa operacoes de escrita no SSW via Playwright. Cadastra unidades (401), cidades atendidas (402) e futuras operacoes. Requer --dry-run na primeira execucao. Usa ssw_defaults.json para valores padrao CarVia.
decision_tree: |
  Cadastrar unidade parceira (tipo T)?
    → cadastrar_unidade_401.py --sigla X --tipo T --razao-social "..." --dry-run
  Cadastrar cidades atendidas para unidade?
    → cadastrar_cidades_402.py --uf XX --unidade XXX --cidades '[...]' --dry-run
  Consultar/navegar SSW (sem alterar)?
    → NÃO usar esta skill. Usar **acessando-ssw**
---

# operando-ssw

Executa operacoes de **ESCRITA** no SSW via scripts Playwright standalone.
Separada de `acessando-ssw` (apenas consulta/documentacao).

## Principio de Safety

1. `--dry-run` e **OBRIGATORIO** na primeira execucao — preview sem submeter
2. Screenshot capturado antes de qualquer submit — evidencia do formulario
3. Agente DEVE usar AskUserQuestion para confirmar antes de executar sem --dry-run
4. Output JSON detalhado — cada campo preenchido e logado

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

## Scripts

### cadastrar_unidade_401.py — Opcao 401

Cadastra nova unidade operacional no SSW.

```bash
source .venv/bin/activate
python .claude/skills/operando-ssw/scripts/cadastrar_unidade_401.py \
  --sigla CGR --tipo T \
  --razao-social "ALEMAR - CAMPO GRANDE/MS" \
  --nome-fantasia "ALEMAR CGR" \
  --ie "ISENTO" \
  [--cnpj 62312605000175] \
  [--defaults-file .claude/skills/operando-ssw/ssw_defaults.json] \
  --dry-run
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

**Regra tipo T**: Usa CNPJ, IE, banco e dados fiscais da **CarVia** (nao do parceiro).
Veja POP-A02 para detalhes.

### cadastrar_cidades_402.py — Opcao 402

Cadastra cidades atendidas para uma unidade.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_cidades_402.py \
  --uf MS --unidade CGR \
  --cidades '[
    {"cidade": "CAMPO GRANDE", "polo": "P", "prazo": 2},
    {"cidade": "DOURADOS", "polo": "R", "prazo": 3},
    {"cidade": "CORUMBA", "polo": "I", "prazo": 5}
  ]' \
  --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --uf | Sim | UF para filtrar cidades (ex: MS, SP) |
| --unidade | Sim | Sigla da unidade responsavel (ex: CGR) |
| --cidades | Sim | JSON array (ver formato abaixo) |
| --dry-run | -- | Preview sem submeter |

**Formato cidades** (JSON array):
```json
[
  {
    "cidade": "CAMPO GRANDE",
    "polo": "P",
    "prazo": 2,
    "tipo_frete": "A",
    "coleta": "S",
    "entrega": "S"
  }
]
```

Campos obrigatorios por cidade: `cidade`, `polo` (P/R/I). `prazo` recomendado.
Demais campos usam defaults do ssw_defaults.json se omitidos.

## Defaults (ssw_defaults.json)

Valores padrao CarVia carregados automaticamente. Campos `null` serao solicitados
ao usuario na primeira execucao real (ex: dados bancarios).

## Fluxo Completo: Nova Rota (POP-A10)

Para implantar uma nova rota completa, o agente orquestra em sequencia:
1. **401** — Cadastrar unidade parceira (esta skill)
2. **402** — Cadastrar cidades atendidas (esta skill)
3. **403** — Cadastrar rota CAR → [SIGLA] (futuro)
4. **478** — Cadastrar fornecedor (futuro)
5. **408** — Cadastrar custos/comissao (futuro)
6. **420** — Cadastrar tabelas de preco (futuro)

## References

- POP-A02: `.claude/references/ssw/pops/POP-A02-cadastrar-unidade-parceira.md`
- POP-A03: `.claude/references/ssw/pops/POP-A03-cadastrar-cidades.md`
- Doc 401: `.claude/references/ssw/cadastros/401-cadastro-unidades.md`
- Doc 402: `.claude/references/ssw/cadastros/402-cidades-atendidas.md`
