<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/skills/gerando-artifact/SKILL.md
superseded_by: —
atualizado: 2026-06-02
-->
# Scripts da Skill gerando-artifact

> **Papel:** Scripts da Skill gerando-artifact.

Scripts shell adaptados do `anthropics/skills/web-artifacts-builder` para
gerar bundle.html no contexto do Sistema de Fretes.

> Executados pelo **worker RQ** (`app/agente/workers/artifact_worker.py`),
> NAO pelo agente diretamente. O agente apenas envia a spec via tool
> `build_artifact`.

---

## scripts/init-artifact.sh

**Funcao**: Cria projeto Vite + React 18 + TS + Tailwind + shadcn/ui em um
diretorio temporario.

**Uso**:
```bash
bash .claude/skills/gerando-artifact/scripts/init-artifact.sh <project-dir>
```

**Pre-requisitos**:
- Node 18+ instalado
- npm disponivel

**O que faz**:
1. Cria `<project-dir>` (mkdir -p)
2. Inicializa Vite template react-ts
3. Instala Tailwind + dependencies shadcn baseline
4. Configura `tsconfig.json` com path alias `@/`
5. Copia `40+ componentes shadcn/ui` pre-build
6. Cria `index.html`, `src/main.tsx`, `src/index.css` baseline

**Output**: diretorio com projeto pronto para receber componentes custom
do agente via `src/App.tsx` etc.

---

## scripts/bundle-artifact.sh

**Funcao**: Empacota projeto Vite em `bundle.html` auto-contido (todo JS/CSS
inlined) via Parcel + html-inline.

**Uso**:
```bash
cd <project-dir>
bash .claude/skills/gerando-artifact/scripts/bundle-artifact.sh
```

**Pre-requisitos**:
- Projeto inicializado por `init-artifact.sh`
- `src/App.tsx` populado pelo caller

**O que faz**:
1. Instala bundling deps (`parcel`, `@parcel/config-default`,
   `parcel-resolver-tspaths`, `html-inline`)
2. Cria `.parcelrc` com path alias support
3. Build com `parcel build index.html --no-source-maps`
4. Inline tudo via `html-inline dist/index.html > bundle.html`

**Output**: `bundle.html` no diretorio raiz do projeto. Auto-contido,
shareavel como artifact.

**Timeout esperado**: 30-60s primeira vez (npm install). 5-15s subsequente
se `node_modules` cacheado.

---

## Templates

`templates/base/` (vazio por design): pre-buildado pelo worker para acelerar
init. **Otimizacao futura** — primeira versao roda `init-artifact.sh` fresh
a cada build.

---

## Diferencas vs. anthropics/skills original

| Item | Original | Aqui |
|---|---|---|
| Paths | Relativos ao cwd | Absolutos (worker controla cwd via /tmp/) |
| Cleanup | Manual | Worker remove `<project-dir>` apos upload S3 |
| Logging | stdout | tee para arquivo de log auditavel |
| Timeout | sem | 5 min (RQ job timeout) |
| Output dest | `./bundle.html` | upload para S3 `agente/artifacts/{user_id}/{uuid}.html` |
| Erro | exit code | atualiza `AgenteArtifact.error_message` em DB |
