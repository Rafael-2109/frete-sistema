---
name: memoria-usuario
description: >-
  Esta skill deve ser usada quando o usuario pede para lembrar, salvar,
  anotar ou guardar informacoes pessoais, preferencias ou fatos entre
  sessoes ("lembre que...", "anote isso", "guarde essa informacao",
  "memorize que...", "o que voce sabe sobre mim?", "esqueca minhas
  preferencias", "apague minhas memorias").
  Tambem usar para ver, atualizar ou apagar memorias existentes.
  NAO usar para: consultas SQL ou dados de negocio (usar consultando-sql),
  historico de conversas (automatico), exportacao de arquivos (usar
  exportando-arquivos), busca em sessoes anteriores (usar consultando-sql).
allowed-tools: Read, Bash, Glob, Grep
---

# Skill: Memoria do Usuario

Gerencia memoria persistente por usuario via banco de dados (tabela `agent_memories`).
Permite que o agente lembre informacoes entre sessoes diferentes.

---

## REGRAS CRITICAS

### R1: NUNCA INVENTAR MEMORIAS
- NAO fabricar memorias que nao foram retornadas pelo script `view`
- Se `view` retornar "(empty)" ou "ERRO", reportar EXATAMENTE isso ao usuario
- NAO assumir que existem memorias sem executar `view` primeiro
- NAO inferir preferencias do usuario sem confirmar com ele

### R2: CONFIRMACAO PARA OPERACOES DESTRUTIVAS
- `delete` de um path: informar ao usuario QUAL path sera deletado antes de executar
- `clear` (todas as memorias): OBRIGATORIAMENTE pedir confirmacao explicita antes de executar
- NUNCA executar `clear` automaticamente ou proativamente

### R3: OUTPUT DO SCRIPT = TEXTO LIVRE
- O script `memoria.py` retorna texto livre no stdout (NAO JSON)
- Mensagens de sucesso: "Criado: /path", "Atualizado: /path", "Deletado: /path"
- Mensagens de erro: "ERRO: ..." (saem no stderr com exit code 1)
- NAO tentar parsear como JSON

### R4: USER_ID OBRIGATORIO
- Todo comando requer `--user-id`
- Se o user_id nao estiver disponivel na sessao, PERGUNTAR ao usuario
- Em contexto do Agente Web: usar o `user_id` da sessao ativa
- NAO usar user_id=0 ou valores ficticios

### R5: PATH DEVE COMECAR COM /memories
- O script rejeita paths que nao comecam com `/memories`
- Seguir a estrutura de paths recomendada abaixo

---

## Scripts Disponiveis

Script unico: `.claude/skills/memoria-usuario/scripts/memoria.py`

Detalhes de parametros: ver `SCRIPTS.md`

### Comandos

```bash
# Ver memorias (raiz ou path especifico)
source .venv/bin/activate && python .claude/skills/memoria-usuario/scripts/memoria.py view --user-id USER_ID [--path /memories/preferences.xml]

# Salvar/criar memoria (cria novo ou sobrescreve existente)
source .venv/bin/activate && python .claude/skills/memoria-usuario/scripts/memoria.py save --user-id USER_ID --path /memories/preferences.xml --content "conteudo XML"

# Atualizar (str_replace — texto old deve ser unico no conteudo)
source .venv/bin/activate && python .claude/skills/memoria-usuario/scripts/memoria.py update --user-id USER_ID --path /memories/preferences.xml --old "texto antigo" --new "texto novo"

# Deletar path especifico
source .venv/bin/activate && python .claude/skills/memoria-usuario/scripts/memoria.py delete --user-id USER_ID --path /memories/preferences.xml

# Limpar TUDO (pedir confirmacao antes!)
source .venv/bin/activate && python .claude/skills/memoria-usuario/scripts/memoria.py clear --user-id USER_ID
```

---

## Estrutura de Paths Recomendada

```
/memories/
  user.xml              # Nome, cargo, responsabilidades
  preferences.xml       # Preferencias de comunicacao
  context/
    company.xml         # Informacoes da empresa
    role.xml            # Cargo/responsabilidades
    clients.xml         # Clientes que gerencia
  learned/
    terms.xml           # Termos especificos aprendidos
    rules.xml           # Regras de negocio aprendidas
    patterns.xml        # Padroes observados
  corrections/
    mistakes.xml        # Correcoes de erros comuns
```

---

## Tratamento de Erros

| Erro do script | Acao do agente |
|----------------|----------------|
| "ERRO: Path nao encontrado" | Informar usuario que memoria nao existe. Para `update`: usar `save` para criar. |
| "ERRO: Texto nao encontrado" | Executar `view` para ver conteudo atual, depois tentar `update` com texto correto. |
| "ERRO: Texto aparece N vezes" | Fornecer mais contexto no `--old` para tornar unico. |
| "(empty)" no `view` | Informar usuario que nenhuma memoria foi salva ainda. NAO inventar dados. |

---

## Quando SALVAR (Proativamente)

| Categoria | Exemplos | Path |
|-----------|----------|------|
| Preferencias de comunicacao | "prefiro respostas curtas", "pode detalhar mais" | `/memories/preferences.xml` |
| Fatos pessoais | nome, cargo, responsabilidades | `/memories/user.xml` |
| Clientes que gerencia | "trabalho com Atacadao e Assai" | `/memories/context/clients.xml` |
| Correcoes | "o campo e X, nao Y" | `/memories/corrections/mistakes.xml` |
| Padroes observados | verifica estoque antes de separacao (apos 3+ ocorrencias) | `/memories/learned/patterns.xml` |
| Regras de negocio | "FOB sempre manda completo" (se nao esta no CLAUDE.md) | `/memories/learned/rules.xml` |

### Quando NAO salvar:
- Dados de negocio (estoques, pedidos, valores) → pertencem ao banco via SQL
- Historico de conversas → ja e salvo automaticamente pelo SDK
- Fatos do CLAUDE.md → ja estao documentados no projeto

---

## Quando ATUALIZAR vs CRIAR NOVO

- **ATUALIZAR** (`update`): Informacao no MESMO path mudou (ex: cargo mudou de analista para gerente)
- **CRIAR NOVO** (`save`): Informacao em path que ainda nao existe
- **NAO duplicar**: Se ja existe `/memories/user.xml` com cargo, fazer `update` nele — NAO criar `/memories/context/role.xml` separado

---

## Formato de Conteudo Recomendado

Usar XML simples com `updated_at` para rastreabilidade:

```
Exemplo user.xml:
  tag user com name, role, updated_at

Exemplo preferences.xml:
  tag preferences com communication, detail_level, language, updated_at

Exemplo patterns.xml:
  tag patterns com pattern (type, description, learned_at)
```

Sempre incluir `updated_at` (formato YYYY-MM-DD) para saber quando a memoria foi criada/atualizada.

---

## Importante

- Memorias sao isoladas por usuario (user_id) — um usuario NAO ve memorias de outro
- Persistem entre sessoes diferentes
- NAO armazenar historico de conversas (ja feito automaticamente)
- Usar para FATOS, PREFERENCIAS e PADROES — nao para dados transacionais
