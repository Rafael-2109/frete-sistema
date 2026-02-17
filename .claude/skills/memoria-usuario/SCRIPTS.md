# Scripts — Memoria Usuario (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. memoria.py

**Proposito:** Gerencia memorias persistentes do usuario via banco de dados (tabela `agent_memories`). Implementa a interface da Memory Tool da Anthropic com 5 comandos: view, save, update, delete e clear.

```bash
source .venv/bin/activate && \
python .claude/skills/memoria-usuario/scripts/memoria.py <comando> [parametros]
```

**Comandos disponiveis:**

### view — Visualizar memorias

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py view --user-id <ID> [--path <PATH>]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--user-id` | ID do usuario (OBRIGATORIO) | `--user-id 1` |
| `--path` | Path da memoria (default: /memories) | `--path /memories/preferences.xml` |

- Sem `--path`: lista diretorio raiz `/memories`
- Com path de diretorio: lista conteudo do diretorio
- Com path de arquivo: mostra conteudo com numeros de linha

### save — Salvar/criar memoria

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py save --user-id <ID> --path <PATH> --content <CONTEUDO>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--user-id` | ID do usuario (OBRIGATORIO) | `--user-id 1` |
| `--path` | Path da memoria (OBRIGATORIO, deve comecar com /memories) | `--path /memories/preferences.xml` |
| `--content` | Conteudo a salvar (OBRIGATORIO) | `--content "<xml>...</xml>"` |

- Cria novo se nao existir, atualiza se ja existir

### update — Atualizar memoria (str_replace)

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py update --user-id <ID> --path <PATH> --old <TEXTO> --new <NOVO>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--user-id` | ID do usuario (OBRIGATORIO) | `--user-id 1` |
| `--path` | Path da memoria (OBRIGATORIO) | `--path /memories/preferences.xml` |
| `--old` | Texto a substituir (OBRIGATORIO, deve ser unico) | `--old "texto antigo"` |
| `--new` | Novo texto (OBRIGATORIO) | `--new "texto novo"` |

- Texto `--old` deve aparecer exatamente 1 vez no conteudo (erro se 0 ou 2+)

### delete — Deletar memoria

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py delete --user-id <ID> --path <PATH>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--user-id` | ID do usuario (OBRIGATORIO) | `--user-id 1` |
| `--path` | Path da memoria (OBRIGATORIO, nao pode ser /memories) | `--path /memories/preferences.xml` |

### clear — Limpar todas as memorias

```bash
python .claude/skills/memoria-usuario/scripts/memoria.py clear --user-id <ID>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--user-id` | ID do usuario (OBRIGATORIO) | `--user-id 1` |

- Remove TODAS as memorias do usuario

**Output:** Texto livre (nao JSON). Mensagens de sucesso ou erro no stdout.

**Nota:** Todos os comandos requerem `create_app()` + `app_context()` para acesso ao banco de dados.
