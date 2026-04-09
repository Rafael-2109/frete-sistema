# Como Rodar Evals de Subagents — Receita

**Ultima Atualizacao**: 2026-04-09

Este documento descreve o processo manual de execucao de evals dos subagents. NAO e um script automatizado — e uma receita para um desenvolvedor seguir.

---

## Pre-requisitos

1. Claude Code CLI instalado (`claude --version`)
2. Estar no diretorio do projeto: `cd /home/rafaelnascimento/projetos/frete_sistema`
3. Virtual env ativado: `source .venv/bin/activate`
4. Ler o `README.md` deste diretorio

---

## Passo 1: Escolher caso(s) a rodar

```bash
# Listar todos os casos de um agent
cat .claude/evals/subagents/analista-carteira/dataset.yaml | grep -E "^  - id|^    title"

# Ou com Python para parsing estruturado
python3 -c "
import yaml
with open('.claude/evals/subagents/analista-carteira/dataset.yaml') as f:
    data = yaml.safe_load(f)
for case in data['cases']:
    print(f\"{case['id']:10} {case['title']}\")
"
```

---

## Passo 2: Executar o caso manualmente

Cada caso tem um campo `input` que representa a mensagem simulada do usuario. Rodar via Claude Code CLI:

```bash
# Para um caso especifico — copie o input e cole no Claude Code interativo
claude

# Em seguida, explicitamente invocar o agent:
# "@analista-carteira <conteudo do input>"
```

**Ou via Task tool em sessao interativa** do Claude Code:

```
Delegue ao analista-carteira: "<conteudo do campo input>"
```

---

## Passo 3: Comparar output com expected_behavior

Le o output do agent e verifica, item por item:

### Exemplo — caso `ac-01` (Pedido FOB com 15% falta)

**expected_behavior**:
- "Identifica como P2/FOB (regra: FOB SEMPRE completo)" → ✅ agent mencionou "FOB = P2" e "completo"
- "Decisao: aguardar producao, nao enviar parcial" → ✅ agent disse "aguardar producao"
- "Nao menciona envio parcial como opcao" → ✅ agent nao sugeriu parcial

**must_not**:
- "Sugere envio parcial" → ❌ (nao violado — passa)
- "Ignora regra FOB = completo" → ❌ (nao violado — passa)

**Resultado**: **PASS** (3/3 expected, 0/2 must_not violados)

---

## Passo 4: Documentar resultado

Criar arquivo `baseline/{case-id}.md` com o output exato e julgamento:

```markdown
# Caso: ac-01
Data: 2026-04-09
Versao agent: git rev-parse HEAD

## Output
<cola output exato do agent>

## Julgamento
- expected_behavior: 3/3 ✅
- must_not: 0/2 violados ✅
- Status: PASS

## Notas
<observacoes do desenvolvedor>
```

---

## Passo 5: Calcular score geral

Apos rodar todos os casos de um agent:

```
Score = casos PASS / total de casos
Alvo: >= 90% (nenhuma regressao grave)
```

Se score < 90%:
1. Identificar quais casos falharam
2. Analisar output vs expected_behavior
3. Corrigir agent ou corrigir caso (se caso estava errado)
4. Re-rodar

---

## Erros Comuns

**"Agent nao foi invocado"**: verificar se o nome esta correto e se o frontmatter permite a invocacao via Task tool.

**"Output vazio"**: verificar se o agent conseguiu ler as skills (agora em formato lista YAML). Consultar log de startup.

**"Resposta inconsistente entre runs"**: LLMs sao nao-deterministicos. Rodar 3x e considerar o comportamento predominante.

**"Expected_behavior muito subjetivo"**: reformular para comportamento observavel concreto (ex: "menciona X" ao inves de "entende X").

---

## Automatizacao Futura (nao escopo desta revisao)

Quando fizer sentido investir em automacao, considerar:

1. Script Python que le dataset.yaml, invoca `claude --agent` para cada caso, salva output
2. LLM-as-judge para comparar output com expected_behavior (requer eval model)
3. Integracao com CI/CD para rodar em pre-commit

Por enquanto, o fluxo manual acima e suficiente para o piloto.

---

## Referencias

- `.claude/evals/subagents/README.md` — visao geral do framework
- `.claude/references/AGENT_TEMPLATES.md` — blocos reusaveis
- `.claude/references/SUBAGENT_RELIABILITY.md` — protocolo de confiabilidade
