# Scripts — Ralph Wiggum (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Nao requer ambiente virtual (script nao usa dependencias do projeto Flask).

---

## 1. init_ralph_project.py

**Proposito:** Inicializa a estrutura Ralph Wiggum em um projeto. Cria arquivos de template para desenvolvimento autonomo com loops de Claude Code.

```bash
python .claude/skills/ralph-wiggum/scripts/init_ralph_project.py [--force]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--force` | Sobrescrever arquivos existentes (default: pula existentes) | `--force` |

**Arquivos criados no diretorio atual (CWD):**

| Arquivo | Descricao |
|---------|-----------|
| `specs/.gitkeep` | Diretorio para especificacoes do projeto |
| `AGENTS.md` | Template com Build/Run/Test commands e patterns |
| `PROMPT_plan.md` | Prompt para modo planejamento (estuda specs + cria IMPLEMENTATION_PLAN.md) |
| `PROMPT_build.md` | Prompt para modo implementacao (executa plano com subagentes) |
| `ralph-loop.sh` | Script executavel para loop autonomo (plan/build) |
| `Dockerfile.ralph` | Dockerfile com Python 3.12 + Claude Code |
| `docker-compose.ralph.yml` | Compose para executar Ralph em container |

**Uso do ralph-loop.sh apos init:**
```bash
./ralph-loop.sh plan 3    # 3 iteracoes de planejamento
./ralph-loop.sh 10        # 10 iteracoes de build
./ralph-loop.sh            # build infinito (ate parar manualmente)
```

**Output:** Texto livre com status de criacao de cada arquivo (nao JSON).

**Nota:** Executa no diretorio atual (`Path.cwd()`). O script `ralph-loop.sh` e marcado como executavel automaticamente.
