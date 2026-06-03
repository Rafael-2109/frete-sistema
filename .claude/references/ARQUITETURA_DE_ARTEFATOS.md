<!-- doc:meta
tipo: reference
camada: L1
sot_de: padrao de arquitetura de artefatos (PAD-A)
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Arquitetura de Artefatos (PAD-A)

> **Papel:** dono vigente do padrao PAD-A para docs e scripts do projeto. **Abra quando:** criar ou mover um artefato, entender as regras de zona/tipo/camada, configurar enforcement, ou rever o que determina conformidade.

## Problema resolvido

Artefatos duplicados, SOTs bicefala e estado replicado em N docs levaram a decisoes divergentes mesmo com regras escritas. O padrao impoe conformidade no momento da criacao (gate) e do commit (lint), nao por memoria do agente.

## Zonas gerenciadas

- **Docs gerenciados:** `docs/`, `.claude/references/`, `.claude/skills/`, `app/*/CLAUDE.md`, `CLAUDE.md` (raiz)
- **Scripts operacionais:** zonas declaradas na allowlist de `scripts/audits/artefato_lint.config.json`
- **Fora de enforcement:** `/tmp`, fixtures de teste, `tipo: scratch`

## Tipos de artefato

| Tipo | Dono de | Camada tipica |
|---|---|---|
| `reference` | fatos, campos, IDs, regras (estavel) | L2 |
| `how-to` / `runbook` | procedimento acionavel | L2 |
| `explanation` | o porque (sem passos) | L3 |
| `adr` | uma decisao datada (imutavel) | L3 |
| `state` | estado vivo/mutavel | L3 |
| `index` | so ponteiros (MOC); o campo `hub:` aponta para um doc deste tipo | L1 |
| `scratch` | efemero, fora de enforcement | — |

## Header doc:meta obrigatorio

```
<!-- doc:meta
tipo: <enum acima>
camada: L1|L2|L3
sot_de: <tema dono ou —>
hub: <caminho do indice que lista este artefato>
superseded_by: <caminho ou —>
atualizado: YYYY-MM-DD
-->
```

Cada tipo tem secoes obrigatorias (ex.: `reference` exige `> **Papel:**` + `## Fontes`). Ver `scripts/audits/artefato_lint.config.json` chave `required_sections`.

## 3 aneis de enforcement

1. **Creation gate (Anel 1):** hook `PreToolUse` em `Write` — valida itens 1–8 do checklist (header, hub existente, secoes, TOC, links) antes de gravar. Arquivo torto nunca chega ao disco.
2. **Commit lint (Anel 2):** `scripts/audits/doc_audit.py` + `scripts/audits/script_audit.py` — valida todos os arquivos tocados no commit, incluindo item 9 (cross-ref bidirecional hub + artefato).
3. **Stop hook (Anel 3):** lista achados/pendencias nao aterrizados ao fim da sessao (advisory).

## Criar artefato conforme

Use o scaffold para gerar o esqueleto correto (header + secoes obrigatorias do tipo):

```bash
python scripts/docs/novo_artefato.py \
    --tipo reference \
    --tema "meu-tema" \
    --hub .claude/references/INDEX.md \
    --out .claude/references/MEU_DOC.md
```

O scaffold carimba `camada: L2` e `sot_de` (= --tema) no header gerado; ajuste a camada no arquivo se o artefato for L1 ou L3.

A skill `padronizando-docs` (T13) guia o fluxo completo: escolha de tipo, template, checklist de 9 itens e registro no hub.

## Convencao de links

O lint (C7 link-rot + C8 alcancabilidade) resolve um link relativo que contem `/` **sem** prefixo `./` como **ROOT-relative** (path a partir da raiz do repo) — regra fixada na Onda 0. Para evitar falso "link morto" ou falso-orfao, siga a convencao (exemplos em bloco para nao virarem links reais):

```text
hub / cross-tree  ->  code-span path-completo:  `docs/superpowers/INDEX.md`  (estilo CLAUDE.md; nao checado por link-rot)
file-relative     ->  prefixe ./ :              [titulo](./sub/y.md)         (clicavel; relativo ao dir do doc, igual GitHub)
mesmo diretorio   ->  nome nu (sem /):          [titulo](y.md)               (ja e file-relative)
```

Links legados file-relative com `/` sem `./` (ex.: `modelos/X.md` em INDEX.md antigos) **nao** sao creditados pelo grafo C8. A varredura por cluster (Onda 4a–4g) **migrou todo o legado gerenciado** e zerou a divida (C8 global = 0). Em **2026-06-03 (SELAGEM, Onda 4g)** os checks `C1` (header), `C7` (link-rot) e `C8` (alcancabilidade) foram **promovidos a `block`**: orfaos, hubs quebrados e links nao-`./` agora **travam o commit**. C8 faz auto-skip sob escopo parcial (grafo incompleto) — so trava no audit completo / commit que toca o grafo.

## Checklist resumido (9 itens)

Itens 1–8 verificados no creation gate (pre-escrita); item 9 no commit lint. Detalhes completos e limiares em [spec](../../docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md) secao 5.

## Fontes
- FONTE: spec PAD-A [2026-06-01](../../docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md) — blueprint aprovado, dono historico (explanation); este arquivo e o dono vigente (reference).
- FONTE: diagnostico topologia/duplicacao: workflows wf_ba978431 e wf_f1b6c258, 2026-06-01.
