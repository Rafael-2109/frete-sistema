---
name: padronizando-docs
description: >-
  Esta skill deve ser usada ao CRIAR ou EDITAR documentacao ou scripts do
  projeto: "onde documento isso?", "criar uma reference", "novo runbook",
  "registrar um ADR", "padronizar este doc", "registrar no indice", "esse
  script tem dono?". Garante header doc:meta, tipo/camada corretos, registro
  no hub e passagem no doc_audit. Nao usar para criar uma SKILL nova (usar
  skill-creator), gerar PRD ou spec (usar prd-generator), nem para consultar
  dados (usar a skill de consulta apropriada).
---

# Padronizando docs e scripts (PAD-A)

> **Papel:** guia o fluxo de criar/editar artefato conforme o padrao PAD-A, sem gerar duplicata nem orfao. **Abra quando:** for escrever ou mover um doc ou script do projeto.

## Arvore de decisao: o que voce tem em maos?

- **Fato novo (campo, ID, regra estavel):** NAO crie doc novo. Ache o dono com `python scripts/audits/doc_audit.py --report-only` ou `grep`; atualize o dono existente.
- **Decisao tomada (datada, imutavel):** crie um ADR (`tipo: adr`).
- **Estado vivo (progresso, pendencias):** mantenha um unico doc `tipo: state` do assunto; atualize-o, nao replique.
- **Achado / investigacao:** aterrisse o fato no dono certo e linke a 1 hub. Nunca deixe doc solto na raiz.
- **Procedimento acionavel:** `tipo: how-to` ou `tipo: runbook`.

## Como criar um artefato conforme

```bash
python scripts/docs/novo_artefato.py \
    --tipo reference \
    --tema "meu-tema" \
    --hub .claude/references/INDEX.md \
    --out .claude/references/MEU_DOC.md
```

O scaffold nasce com o header e as secoes obrigatorias do tipo. Ajuste `camada` no header gerado se o artefato for L1 ou L3.

## Checklist (9 itens)

Itens 1-8 = forma do arquivo (header valido, hub existente, secoes do tipo, TOC quando passa de 100 linhas, links vivos, sem markers ou termos banidos em reference). Item 9 = registro bidirecional: o hub lista o artefato e o artefato aponta o hub. Limiares e detalhes em [Arquitetura de Artefatos](../../references/ARQUITETURA_DE_ARTEFATOS.md).

## Verificar antes de commitar

```bash
python scripts/audits/doc_audit.py --enforce-touched
python scripts/audits/script_audit.py --enforce-touched
```
