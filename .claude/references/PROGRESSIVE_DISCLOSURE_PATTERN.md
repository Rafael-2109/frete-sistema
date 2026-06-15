<!-- doc:meta
tipo: reference
camada: L2
sot_de: os 3 padroes de progressive disclosure do repo (CLAUDE.md root+modulo, arvore docs L1-L3, memoria narrativa JSONB) e o criterio de quando usar cada um
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Padroes de Progressive Disclosure

> **Papel:** Fonte de verdade dos tres padroes de progressive disclosure do repositorio (CLAUDE.md root+modulo; arvore `docs/` por camada L1-L3; memoria narrativa JSONB) e o criterio de quando aplicar cada um. Ler antes de criar/editar CLAUDE.md de modulo, indice de docs, ou nova reference.

## Contexto

A janela de contexto do modelo e um orcamento finito. Progressive disclosure significa carregar o minimo no boot e puxar o restante sob demanda, por gatilho explicito. O repositorio aplica o principio em tres superficies distintas, cada uma com mecanica propria. As Skills sao o caso nativo de tres niveis; o CLAUDE.md, ao contrario, carrega inteiro no boot — a economia ali vem da separacao entre o arquivo raiz (compartilhado) e o de modulo (lido so ao trabalhar no modulo).

## Indice

- [Padrao 1 — CLAUDE.md root + modulo](#padrao-1--claudemd-root--modulo)
- [Padrao 2 — Arvore docs por camada (L1 a L3)](#padrao-2--arvore-docs-por-camada-l1-a-l3)
- [Padrao 3 — Memoria narrativa (JSONB + indice)](#padrao-3--memoria-narrativa-jsonb--indice)
- [Contraste: Skills (disclosure nativo de 3 niveis)](#contraste-skills-disclosure-nativo-de-3-niveis)
- [Quando usar qual](#quando-usar-qual)
- [Fontes](#fontes)

## Padrao 1 — CLAUDE.md root + modulo

Dois (ou tres) niveis de CLAUDE.md:

- **Raiz** (`CLAUDE.md`): referencia compartilhada, lida por ambos os contextos (Claude Code dev + Agent SDK web) em todo boot. So o essencial universal: tech stack, regras universais, indice de references, caminhos por modulo, subagentes. Conteudo dev-only mora em `.claude/references/REGRAS_DEV_LOCAL.md` (ponteiro, nao copia).
- **Modulo** (`app/<modulo>/CLAUDE.md`): regras e gotchas do modulo, lidos ao entrar no modulo. Quinze modulos tem o seu (ver secao "Module -> CLAUDE.md" no indice de references).
- **Subdir** (`app/<modulo>/<area>/CLAUDE.md`): para sub-area densa o bastante para ter regras proprias. Existem dois: `app/agente/services/CLAUDE.md` e `app/odoo/estoque/CLAUDE.md`.

O disclosure vem da fronteira: o CLAUDE.md de modulo nao polui o boot de quem nao trabalha naquele modulo. O arquivo de modulo aponta de volta para a raiz e para suas references, nunca duplica conteudo. Manual de autoria: `.claude/references/MANUAL_CLAUDE_MD.md`.

**Limite:** cada CLAUDE.md carrega INTEIRO quando lido — nao ha disclosure interno. Fragmentar por eixo-de-tarefa com gatilho imperativo ("ANTES de X: LER Y"); empurrar detalhe para reference ou skill.

## Padrao 2 — Arvore docs por camada (L1 a L3)

A arvore `docs/` (e `.claude/references/`) usa o header `doc:meta` com o campo `camada`:

- **L1** — indice/hub puro de ponteiros (`tipo: index`). Ex.: `docs/INDEX.md`, `.claude/references/INDEX.md`. Carrega cedo; so aponta.
- **L2** — reference duravel, conhecimento estavel (`tipo: reference`/`explanation`). Lida sob demanda via gatilho do hub.
- **L3** — modulo/sessao/fluxo: docs de area especifica, runbooks, gotchas, fluxos (ex.: `docs/inventario-2026-05/`, `docs/odoo/`, `docs/rastreamento/`). Acessado so quando a tarefa toca a area.

O lint `scripts/audits/doc_audit.py` impoe a estrutura: cada doc gerenciado declara `hub`, e o hub lista o doc de volta (regra C8, bidirecional). Assim a navegacao e sempre raiz -> hub -> doc, carregando so o ramo necessario. Criterios de admissao por camada: `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md`.

## Padrao 3 — Memoria narrativa (JSONB + indice)

Aprendizado episodico e comportamental em runtime (Agent SDK web) mora em memoria persistente, com disclosure por indice:

- Cada memoria tem metadados em JSONB + conteudo narrativo.
- O indice (titulo + gancho) fica barato no contexto; o conteudo completo e recuperado sob demanda por relevancia (busca semantica via `app/embeddings/`).
- A injecao no contexto e governada por regras: `app/agente/sdk/memory_injection.py` + `app/agente/sdk/memory_injection_rules.py`.

Mesma logica do disclosure de Skills: indice no contexto, corpo so quando relevante. Protocolo: `.claude/references/MEMORY_PROTOCOL.md`. (No lado Claude Code dev, o equivalente e o `MEMORY.md` + topic files em `memory/`.)

## Contraste: Skills (disclosure nativo de 3 niveis)

A Skill e o exemplo canonico de progressive disclosure:

1. **Descricao** (no boot): nome + `description` — barato, so para o roteamento decidir se invoca.
2. **SKILL.md** (ao invocar): o corpo da skill.
3. **Scripts/references** (sob demanda dentro da skill): `SCRIPTS.md`, `scripts/`, sub-references — carregados so quando o passo precisa.

Ex.: `.claude/skills/cotando-frete/SKILL.md` + `.claude/skills/cotando-frete/SCRIPTS.md`. Diferente do CLAUDE.md, aqui o disclosure e interno e nativo.

## Quando usar qual

| Conhecimento | Padrao | Onde |
|---|---|---|
| Como trabalhar num modulo de codigo (regras, gotchas, caminhos) | 1 | `app/<modulo>/CLAUDE.md` |
| Conhecimento tecnico duravel/narrativo (fluxos, specs, runbooks) | 2 | `docs/<area>/` + `doc:meta` + indexado |
| Aprendizado episodico/comportamental do agente em runtime | 3 | memoria JSONB (web) / `memory/` (dev) |
| Capacidade acionavel por gatilho de tarefa | Skill | `.claude/skills/<skill>/` |
| Ponteiro universal lido em todo boot | 1 (raiz) | `CLAUDE.md` raiz |

Regra de ouro: se o conteudo nao precisa estar no boot, ele vira ponteiro (hub) + corpo sob demanda. Duplicar conteudo entre niveis e o anti-padrao — usar link/hub.

## Fontes

- `CLAUDE.md` (raiz) e `app/*/CLAUDE.md` (15 modulos + 2 subdir `app/agente/services/`, `app/odoo/estoque/`) — Padrao 1.
- `.claude/references/MANUAL_CLAUDE_MD.md` — autoria de CLAUDE.md de modulo.
- `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md` — criterios de admissao por camada (PAD-CTX).
- `scripts/audits/doc_audit.py` + `scripts/audits/artefato_lint.config.json` — lint de camada/hub/bidirecionalidade (Padrao 2).
- `app/agente/sdk/memory_injection.py`, `app/agente/sdk/memory_injection_rules.py`, `.claude/references/MEMORY_PROTOCOL.md` — Padrao 3.
- `.claude/skills/cotando-frete/SKILL.md` + `SCRIPTS.md` — exemplo de Skill.
