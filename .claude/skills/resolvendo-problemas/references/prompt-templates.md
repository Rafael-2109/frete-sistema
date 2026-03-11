# Templates de Prompt para Subagentes

Templates prontos para copiar/adaptar ao spawnar subagentes em cada fase.

---

## Protocolo de Output (incluir em TODO prompt)

```
PROTOCOLO DE OUTPUT (OBRIGATORIO):
1. Crie /tmp/subagent-findings/{session-id}/phase{N}/ se nao existir
2. Escreva findings em /tmp/subagent-findings/{session-id}/phase{N}/{nome-arquivo}.md
3. Use EXATAMENTE este formato:

   ## Fatos Verificados
   - {afirmacao} — FONTE: {arquivo-absoluto}:{linhas}

   ## Inferencias
   - {conclusao} — BASEADA EM: {fatos que suportam}

   ## Nao Encontrado
   - {buscado} — BUSCADO EM: {onde procurou}

   ## Assuncoes
   - [ASSUNCAO] {decisao tomada sem confirmacao}

4. DISTINGA fatos de inferencias — NUNCA misture
5. REPORTE o que buscou e NAO encontrou (tao importante quanto o que encontrou)
6. CITE fontes (arquivo:linha) para TODA afirmacao factual
```

---

## Fase 1: Templates de Pesquisa Atomica

### INVENTARIO

```
Voce esta pesquisando o modulo {modulo} do sistema de fretes.

ANTES DE COMECAR:
- Leia {claude_md_path} se existir (CLAUDE.md do modulo)
- Leia o schema relevante em .claude/skills/consultando-sql/schemas/tables/{tabela}.json

TAREFA:
Liste TODOS os arquivos em {path_modulo}/ com:
1. Path absoluto
2. Numero de linhas (LOC)
3. Proposito em 1 frase
4. Exports publicos (funcoes, classes, constantes exportadas)
5. Imports de outros modulos do sistema

Organize por subdiretorio (routes/, services/, templates/, etc).

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-inventario.md
```

### DEPENDENCIA

```
Voce esta mapeando dependencias do arquivo {arquivo}.

TAREFA:
1. Leia o arquivo COMPLETO
2. Liste TODOS os imports, separando:
   - Imports de stdlib Python
   - Imports de libs externas (Flask, SQLAlchemy, etc)
   - Imports internos do sistema (app.*)
3. Para cada import interno, anote:
   - Qual funcao/classe e importada
   - De qual arquivo vem
   - Se e usada (grep pelo nome no arquivo)
4. Liste TODOS os arquivos que importam DE {arquivo}:
   - Use Grep com pattern "from {modulo_path}" e "import {modulo_path}"
   - Para cada match, anote qual funcao/classe importam

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-dependencias.md
```

### COMPORTAMENTO (Call Chain)

```
Voce esta rastreando o fluxo de {operacao} no sistema.

TAREFA:
Trace o caminho COMPLETO do codigo, de entrada a saida:

1. ENTRADA: Onde a operacao comeca? (rota HTTP, job, signal, etc)
   - Qual arquivo e funcao?
   - Quais parametros recebe?

2. PROCESSAMENTO: Quais funcoes sao chamadas em sequencia?
   Para cada chamada:
   - arquivo:funcao:linha
   - O que recebe e o que retorna
   - Se faz IO (banco, API, filesystem)

3. SAIDA: Onde termina?
   - O que retorna ao caller?
   - Efeitos colaterais (writes no banco, mensagens, etc)

4. CAMINHOS ALTERNATIVOS:
   - Quais branches/ifs existem no fluxo?
   - Quais excecoes sao capturadas e onde?

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-comportamento.md
```

### DADOS (Schema)

```
Voce esta documentando o schema de {modelo_ou_tabela}.

ANTES DE COMECAR:
- Leia o schema em .claude/skills/consultando-sql/schemas/tables/{tabela}.json (fonte de verdade)
- Leia o model SQLAlchemy correspondente se existir

TAREFA:
1. Liste TODOS os campos com tipo, nullable, default, constraints
2. Identifique relacionamentos (FK, backref, association tables)
3. Identifique indices (compostos, unique, parciais)
4. Documente campos calculados (@property, @hybrid_property)
5. Liste triggers ou hooks (before_insert, after_update, etc)
6. Compare schema JSON com model Python — reporte divergencias

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-dados.md
```

### PADRAO

```
Voce esta identificando padroes em {escopo} para {concern}.

TAREFA:
1. Leia os arquivos: {lista_arquivos}
2. Para cada arquivo, identifique:
   - Padrao de nomenclatura (funcoes, variaveis, classes)
   - Padrao de estrutura (ordem das secoes, imports, etc)
   - Padrao de tratamento de erros (try/except, retornos, logs)
   - Padrao de comunicacao (response format, status codes, etc)
3. Identifique CONSISTENCIAS (todos fazem igual)
4. Identifique INCONSISTENCIAS (um faz diferente dos outros)
5. Para cada padrao encontrado, cite 2+ exemplos com arquivo:linha

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-padrao.md
```

### NEGATIVO (Gaps)

```
Voce esta procurando o que FALTA em {escopo}.

CONTEXTO: {descricao do que o modulo deveria fazer}

TAREFA:
1. Leia os arquivos em {path}
2. Com base no contexto acima, identifique:
   - Funcionalidades mencionadas mas nao implementadas
   - Tratamentos de erro ausentes (funcoes sem try/except que fazem IO)
   - Validacoes faltando (inputs nao validados)
   - Testes ausentes (funcoes publicas sem teste correspondente)
   - Documentacao incompleta (docstrings faltando em funcoes publicas)
3. Para cada gap, classifique severidade: CRITICO | IMPORTANTE | MENOR

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-negativo.md
```

---

## Fase 1: Template de Onda Relacional

```
Voce esta cruzando resultados de pesquisas anteriores.

LEIA os seguintes findings (JA ESCRITOS por outros pesquisadores):
{lista_de_findings_files}

TAREFA:
Com base nos findings acima:
1. {pergunta_relacional_especifica}
2. Identifique CONTRADICOES entre findings (se existirem)
3. Identifique DEPENDENCIAS nao mapeadas nas pesquisas atomicas
4. Classifique confianca: ALTA (2+ fontes concordam) | MEDIA (1 fonte) | BAIXA (inferencia)

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase1/question-{N}-relacional.md
```

---

## Fase 4: Template Adversarial

```
Voce e um REVISOR DE CODIGO. Seu trabalho e encontrar FALHAS neste plano.

LEIA:
1. O plano em /tmp/subagent-findings/{session-id}/phase3/plan.md
2. Os findings de pesquisa em /tmp/subagent-findings/{session-id}/phase1/
3. A analise em /tmp/subagent-findings/{session-id}/phase2/analysis.md

Depois, para CADA tarefa do plano:
1. Leia os arquivos-fonte listados na tarefa (Read direto, NAO confie no plano)
2. Verifique: os arquivos existem e contem o que o plano afirma?
3. Verifique: a mudanca descrita e compativel com o codigo atual?
4. Tente encontrar pelo menos 1 edge case que o plano PERDEU
5. Verifique: o metodo de validacao realmente pegaria regressoes?
6. Verifique: todos os callers/importers de codigo modificado estao listados?

MENTALIDADE: Assuma que o plano esta ERRADO ate provar o contrario.
NAO seja gentil. Encontre problemas.

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase4/review.md
```

---

## Fase 6: Template de Regressao

```
Voce esta verificando se a implementacao causou REGRESSOES.

CONTEXTO:
- Problema original: {problema}
- Arquivos modificados: {lista de arquivos com git diff --name-only}

LEIA:
1. O inventario da Fase 1: /tmp/subagent-findings/{session-id}/phase1/question-*-inventario.md
2. As dependencias da Fase 1: /tmp/subagent-findings/{session-id}/phase1/question-*-dependencias.md
3. Cada arquivo modificado (versao atual, pos-implementacao)

TAREFA:
Para cada arquivo modificado:
1. Identifique TODOS os callers (quem chama funcoes deste arquivo)
2. Verifique: a interface (parametros, retornos) mudou?
3. Se mudou: os callers foram atualizados tambem?
4. Verifique: imports que este arquivo usa ainda existem com mesma interface?
5. Verifique: nenhuma funcao foi removida sem atualizar quem a usava

{PROTOCOLO_OUTPUT}
Arquivo de saida: /tmp/subagent-findings/{session-id}/phase6/regression-check.md
```

---

## Dicas de Uso

### Parametros do Agent Tool (OBRIGATORIO)

| Parametro | Valor para pesquisa | Valor para adversarial | Valor para implementacao |
|-----------|---------------------|------------------------|-------------------------|
| `model` | **`"opus"`** | **`"opus"`** | **`"opus"`** |
| `subagent_type` | `Explore` | `Plan` | `general-purpose` |
| `mode` | (default) | (default) | (default) |
| `run_in_background` | `false` (precisa do resultado) | `false` | `false` |

> **R2**: TODOS os subagentes DEVEM usar `model: "opus"`. Haiku/Sonnet nao tem capacidade de pesquisa profunda e citacao de fontes necessaria para esta skill.

### Paralelismo

- Fase 1 atomica: spawnar TODOS os subagentes em paralelo (1 Agent call por pergunta)
- Fase 1 relacional: sequencial (depende dos findings atomicos)
- Fase 4: 1 subagente
- Fase 6: 1 subagente

### Quando Ajustar o Prompt

Se um subagente retornar findings com:
- Fatos sem fonte → adicionar ao prompt: "TODA afirmacao DEVE ter FONTE com arquivo:linha"
- Muitas inferencias como fatos → adicionar: "Se voce NAO leu o arquivo, NAO afirme"
- Findings muito longos → adicionar: "Limite a {N} fatos por secao"
- Findings muito curtos → adicionar: "Inclua TODOS os {items}, nao apenas exemplos"
