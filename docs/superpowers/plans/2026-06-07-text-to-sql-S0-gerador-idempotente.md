<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano S0 — gerador de schemas idempotente (anti-poluicao git)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-07
-->

# S0 — Gerador de Schemas Idempotente

> **Papel:** plano executavel da sessao dedicada ao subsistema S0 (higiene). Torna
> `generate_schemas.py` idempotente e deterministico, para que regenerar schemas nao
> polua o git. Pre-requisito de S1 e S2 (sem isto, diffs de schema sao ilegiveis).
> Faz parte do pacote `2026-06-07-text-to-sql-arquitetura-MASTER` (ler o MASTER antes).

## Indice

- [Contexto herdado](#contexto-herdado)
- [Objetivo e criterio de sucesso](#objetivo-e-criterio-de-sucesso)
- [Escopo](#escopo)
- [Arquivos-alvo](#arquivos-alvo)
- [Passo 0 — descobrir a causa raiz (OBRIGATORIO antes de codar)](#passo-0-descobrir-a-causa-raiz-obrigatorio-antes-de-codar)
- [Abordagens](#abordagens)
- [Design proposto](#design-proposto)
- [Edge cases](#edge-cases)
- [Pre-mortem](#pre-mortem)
- [Decisoes em aberto (perguntar na sessao)](#decisoes-em-aberto-perguntar-na-sessao)
- [Testes e verificacao](#testes-e-verificacao)
- [Conformidade](#conformidade)

## Contexto herdado

O pipeline Text-to-SQL le schemas JSON gerados por
`.claude/skills/consultando-sql/scripts/generate_schemas.py` a partir dos modelos
SQLAlchemy. Sao 303 arquivos em `.claude/skills/consultando-sql/schemas/tables/*.json`
+ `catalog.json` + `relationships.json`. O usuario relatou que **regenerar reescreve
TODOS os arquivos mesmo os sem alteracao real**, poluindo o git e impedindo revisao de
diffs. Isso bloqueia S1 (progressive disclosure) e S2 (qualidade de schema), que
precisam editar schemas e ver diffs limpos.

Fonte da escrita atual (sem comparacao previa):
- `generate_schemas.py:742` — `open(output_path, 'w')` + `json.dump(...)` por tabela.
- `generate_schemas.py:787` — escrita do `catalog.json`.
- `generate_schemas.py:805` — escrita do `relationships.json`.
- `generate_schemas.py:679` — `generate_all()` orquestra tudo.
- `generate_schemas.py:587,664` — `import_all_models()` itera modelos (ordem pode
  variar por filesystem / `inspect.getmembers`).
- `generate_schemas.py:401-411` — `extract_field_description` usa `inspect.getsource`
  + regex (fonte potencial de instabilidade textual).

Gatilho (achado 2026-06-07): o hook `lembrar-regenerar-schemas.py` esta registrado no
settings GLOBAL `~/.claude/settings.json` (PostToolUse Write|Edit) e dispara a regeneracao
a cada edicao de `models.py`/`models/*.py`. Logo, a poluicao nao vem de execucao manual —
vem desse disparo somado a serializacao nao-deterministica das colecoes globais.

## Objetivo e criterio de sucesso

**Objetivo:** rodar `generate_schemas.py` duas vezes seguidas, sem mudanca de modelo,
deve deixar o `git status` limpo na segunda execucao.

**Criterio de sucesso (verificavel):**
1. `python .claude/skills/consultando-sql/scripts/generate_schemas.py` rodado 2x →
   `git status --porcelain .claude/skills/consultando-sql/schemas/` vazio na 2a.
2. Mudar 1 descricao de 1 modelo → regenerar → git mostra **exatamente 1** arquivo
   alterado (o da tabela afetada) + `catalog.json` se a descricao for de catalogo.
3. Ordenacao de `catalog.json` e `relationships.json` estavel entre execucoes.

## Escopo

**Inclui:**
- Escrita condicional (write-if-changed) para tables/, catalog.json, relationships.json.
- Serializacao canonica deterministica (ordenacao estavel + newline final fixo).
- Revisao do gatilho do hook (`lembrar-regenerar-schemas.py` no settings global): filtro de
  path correto + apagar orfaos so com import 100% completo.
- Modo `--check` (nao escreve; exit != 0 se houver drift) como ferramenta manual.

**Exclui (vai para S1/S2):**
- Mudar o CONTEUDO dos schemas (key_fields melhores → S1; descricoes/regras → S2).
- Tocar `text_to_sql.py` ou tools MCP.

## Arquivos-alvo

| Arquivo | Mudanca |
|---|---|
| `.claude/skills/consultando-sql/scripts/generate_schemas.py` | write-if-changed + ordenacao canonica + flag `--check` |
| `.claude/hooks/lembrar-regenerar-schemas.py` | revisar (ja existe; alinhar mensagem ao novo fluxo) |
| (novo) teste pytest de idempotencia | em `tests/` conforme padrao do projeto |

## Passo 0 — descobrir a causa raiz (OBRIGATORIO antes de codar)

Antes de qualquer fix, a sessao DEVE provar a causa empiricamente:
1. `git stash` / arvore limpa.
2. Rodar o gerador 1x; `git diff --stat` dos schemas.
3. Pegar 1 arquivo de tabela cujo modelo NAO mudou e rodar `git diff` nele.
4. Classificar a diferenca: ordenacao de chaves? ordem de tabelas (catalog)? texto de
   descricao via `inspect.getsource`? whitespace/newline final? `ensure_ascii`?

A correcao depende do que o diff revelar. Nao assumir — medir. Registrar o achado no
rastreamento do MASTER.

## Abordagens

**A. Write-if-changed + serializacao canonica (RECOMENDADA).**
Gerar o conteudo em memoria, serializar de forma canonica, comparar com o arquivo no
disco (normalizado) e so escrever se diferir. Ordenar listas globais (`catalog.tabelas`,
`relationships`) por nome. Trade-off: pequeno custo de leitura previa; ganho = git limpo
e diffs minimos. Resolve a raiz.

**B. `--check` mode para CI/pre-commit (COMPLEMENTAR a A).**
Sem escrever, regenera em memoria e compara; exit code != 0 se drift. Permite um hook de
pre-commit barrar schema desatualizado sem reescrever a arvore. Trade-off: so detecta,
nao corrige — por isso e complemento de A.

**C. Deixar como esta e confiar no `git checkout` manual (REJEITADA).**
Nao resolve a raiz; mantem working tree suja; quebra revisao de diffs em S1/S2.

## Design proposto

- Helper `_write_if_changed(path, content_str)`: le o arquivo existente (se houver),
  compara string normalizada (mesma serializacao), escreve so se diferente; retorna
  bool "mudou". Logar contagem de "escritos vs inalterados" no fim.
- Serializacao canonica unica `_dump_canonical(obj) -> str`: `json.dumps(obj,
  ensure_ascii=False, indent=2, sort_keys=<decisao>)` + newline final fixo. Aplicar a
  TODOS os 3 destinos (tables, catalog, relationships).
- Ordenacao estavel das colecoes globais: `catalog['tabelas']` e `relationships`
  ordenados por nome de tabela antes de serializar.
- Flag CLI `--check`: roda `generate_all` em memoria; compara cada destino com o disco;
  imprime os que estao defasados; exit 1 se algum diferir; nao escreve nada.

## Edge cases

- **Modelo removido** → arquivo `tables/<tabela>.json` orfao. Decisao aberta: apagar ou
  manter (ver decisoes).
- **Tabela nova** → arquivo novo (write-if-changed escreve por nao existir). OK.
- **Mudanca de tipo/descricao de 1 coluna** → so o arquivo daquela tabela muda.
- **Ordenacao de campos dentro da tabela**: a ordem das colunas no modelo e estavel por
  tabela; decidir se mantem ordem do modelo (preserva semantica de leitura) ou ordena
  por nome (mais robusto a refactors). Ver decisoes.
- **`extract_field_description` instavel**: se o regex sobre `inspect.getsource` produz
  texto diferente entre rodadas (improvavel, mas o Passo 0 confirma), normalizar a saida.

## Pre-mortem

> "3 meses depois, S0 falhou. Por que?"
1. **Ordenei tudo por nome e quebrei a leitura semantica dos schemas** (campos fora de
   ordem logica). → Mitigacao: ordenar so as colecoes GLOBAIS (catalog/relationships);
   manter ordem de coluna do modelo dentro de cada tabela (decisao a confirmar).
2. **`--check` no pre-commit virou friccao** (bloqueia commit sempre que alguem esquece
   de regenerar). → Mitigacao: `--check` opt-in; mensagem clara com o comando de fix.
3. **Write-if-changed mascarou um schema realmente defasado** (comparou serializacao
   diferente da gravada). → Mitigacao: a MESMA funcao `_dump_canonical` para comparar e
   gravar; teste de idempotencia cobre isso.
4. **Apaguei arquivos orfaos e perdi overlays/curadoria de S2.** → Mitigacao: nunca
   apagar nada em `schemas/overlays/`; orfaos so em `tables/` e so com decisao explicita.

## Decisoes fechadas (2026-06-07)

1. **Apagar orfaos SIM**, com **salvaguarda inviolavel**: so apagar `tables/<t>.json` de
   modelo removido se a importacao de modelos foi 100% completa (zero modulo com
   ImportError). Import parcial NUNCA apaga — senao o hook, ao rodar com um models.py
   quebrado no meio de uma edicao, apagaria schemas validos.
2. **Gatilho via hook (sem `--check` no pre-commit)**: a regeneracao roda pelo hook
   `lembrar-regenerar-schemas.py`, registrado no settings GLOBAL `~/.claude/settings.json`
   (PostToolUse Write|Edit), que dispara `generate_schemas.py` a cada edicao de models.
   `--check` fica como ferramenta manual, fora do pre-commit. A sessao DEVE revisar o
   filtro de path do gatilho (Passo 0) e a idempotencia torna cada disparo inofensivo.
3. **Ordem do modelo nas colunas**: dentro de cada `tables/<t>.json`, manter a ordem das
   colunas do modelo (estavel, preserva leitura semantica).
4. **Ordenacao POR NOME nas colecoes globais**: `catalog.json` (`tabelas`) e
   `relationships.json` ordenados por nome de tabela. Esta e a correcao que mata o ruido —
   hoje saem na ordem de IMPORT (varia entre disparos do hook). NAO usar `sort_keys`
   global (preserva a ordem de coluna do item 3).

## Testes e verificacao

- pytest determinista: chama `generate_all` (modo memoria) 2x e afirma saida identica;
  afirma que rodar e re-rodar nao muda bytes. Sem LLM (regra do projeto: evals LLM
  caros → preferir pytest).
- Manual: rodar 2x e `git status --porcelain` dos schemas vazio na 2a.
- `--check` retorna 0 em arvore regenerada e != 0 apos editar 1 schema a mao.

## Conformidade

- Sem DDL → sem migration (so script + arquivos gerados).
- Nao tocar `schemas/overlays/` (reservado a S2).
- Atualizar `lembrar-regenerar-schemas.py` se a interface CLI mudar.
