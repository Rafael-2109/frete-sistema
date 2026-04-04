# Sistema de Memoria Persistente para Agent SDK

## Objetivo

Refatorar o sistema de memoria do Agent SDK para resolver:
- **Perda de contexto entre sessoes** - Claude esquece conversas anteriores
- **Falta de aprendizado continuo** - Nao aprende com interacoes passadas

## Problemas Atuais

| Problema | Arquivo | Impacto |
|----------|---------|---------|
| Memory Tool nao integrada ao SDK | `app/agente/sdk/client.py:370-379` | Claude nao pode ler/escrever memorias |
| Limite de 50 mensagens | `app/agente/models.py:20` | Contexto truncado em sessoes longas |
| Sem versionamento | `app/agente/hooks/memory_agent.py:181-184` | Memorias acumulam texto infinito |
| Claude nao navega historico | - | So ve ultimas 50 mensagens |

## Requisitos

### 1. Integrar Memory Tool ao SDK (PRIORIDADE 1)

- Passar `DatabaseMemoryTool` no `allowed_tools` do SDK
- Claude podera usar comandos: `view`, `create`, `str_replace`, `delete`
- Arquivo: `app/agente/sdk/client.py`

### 2. Implementar Versionamento de Memorias

- Criar tabela `agent_memory_versions` para historico
- Antes de UPDATE, salvar versao anterior
- Permitir consulta de versoes antigas
- Arquivos: `app/agente/models.py`, nova migration

### 3. Persistencia Cross-Session

- Memorias salvas pelo MemoryAgent ja funcionam
- Foco: permitir Claude ACESSAR via Memory Tool
- Injetar memorias relevantes no contexto automaticamente

## Criterios de Aceite

- [ ] Claude consegue usar Memory Tool (view, create, str_replace)
- [ ] Claude lembra correcoes feitas na semana passada
- [ ] Consigo ver versoes anteriores de uma memoria (auditoria)
- [ ] Sistema funciona sem aumentar muito o custo (~$0.006/msg max)

## Notas Tecnicas

### Arquivos a Modificar

| Arquivo | Mudanca |
|---------|---------|
| `app/agente/sdk/client.py:370-379` | Adicionar Memory Tool em `allowed_tools` |
| `app/agente/models.py` | Criar modelo `AgentMemoryVersion` |
| `app/agente/memory_tool.py` | Adaptar para salvar versoes antes de update |
| Migration nova | Criar tabela `agent_memory_versions` |

### Estrutura da Nova Tabela

```sql
CREATE TABLE agent_memory_versions (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER REFERENCES agent_memories(id),
    content TEXT,
    version INTEGER,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(50)  -- 'user', 'haiku', 'claude'
);
```

### Fluxo com Memory Tool Integrada

```
1. Usuario envia mensagem
2. PRE-HOOK: MemoryAgent injeta contexto (como hoje)
3. Claude processa COM ACESSO a Memory Tool
4. Claude pode ler/escrever memorias diretamente
5. POST-HOOK: MemoryAgent detecta padroes (como hoje)
6. Antes de salvar: criar versao anterior
```

### Padroes a Seguir

- Consultar CLAUDE.md para convencoes
- Manter compatibilidade com sistema atual
- Nao quebrar MemoryAgent (Haiku hooks)

## Verificacao

```bash
# 1. Testar Memory Tool no SDK
# - Enviar mensagem pedindo para Claude salvar algo
# - Verificar se aparece na tabela agent_memories

# 2. Testar versionamento
# - Atualizar uma memoria
# - Verificar se versao anterior foi salva

# 3. Testar persistencia cross-session
# - Fazer correcao em uma sessao
# - Iniciar nova sessao
# - Verificar se Claude lembra
```
