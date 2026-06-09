---
name: gerando-artifact
description: >-
  Gera bundle.html (React 18+TS+Tailwind+shadcn/ui) renderizado em modal no chat
  web do agente -- exclusivo canal /agente/chat. Usar quando: "monte um
  dashboard de fretes", "crie visualizacao interativa do estoque", "tela com
  filtros para P1-P7", "painel interativo multi-componente". Nao usar: Teams
  (sem render) -> responder texto+link; tabela simples -> markdown; exportar
  Excel -> exportando-arquivos.
allowed-tools: Bash, Read, Write, Edit
---

# gerando-artifact

Cria **artifact** (bundle.html auto-contido) renderizado em modal no chat web do
Agente. Stack: **React 18 + TypeScript + Tailwind CSS + shadcn/ui** empacotado
via Parcel em arquivo HTML unico (todo JS/CSS/deps inlined).

> **CONTEXTO CRITICO**: artifacts so funcionam no **chat web** do agente
> (`/agente/chat`). NAO renderizam no Teams nem em outros canais. Se o usuario
> esta no Teams, responda com texto + link em vez de invocar esta skill.

---

## WORKFLOW OBRIGATORIO

```
PASSO 1 — VERIFICAR CONTEXTO (canal)
  Se canal != web (Teams, WhatsApp, etc.): NAO usar esta skill.
  Responda em texto e ofereca link compartilhavel.

PASSO 2 — PLANEJAR SPEC
  Decida:
    - titulo: nome curto (max 80 chars)
    - componentes: lista de arquivos React/TS a criar
    - dependencies extras (alem do baseline shadcn/ui): nome + versao

PASSO 3 — CHAMAR TOOL build_artifact
  Argumentos:
    {
      "titulo": str,
      "spec": {
        "components": [
          {"path": "src/App.tsx", "content": "<codigo React>"},
          {"path": "src/components/X.tsx", "content": "..."}
        ],
        "dependencies": {"recharts": "^2.10.0"}   // opcional
      }
    }
  Tool retorna: {uuid, render_url, status_url}

PASSO 4 — RESPONDER AO USUARIO
  Texto curto + marker [ARTIFACT:<uuid>]. Exemplo:
    "Dashboard pronto. [ARTIFACT:abc123]"
  Frontend detecta marker e renderiza card com botao "Abrir visualizacao".
  Build leva 30-60s em segundo plano; card mostra progresso.
```

**VIOLAR ESTA ORDEM = artifact nao renderiza ou nao chega ao usuario.**

---

## QUANDO USAR

| Pedido do usuario | Esta skill? | Alternativa se nao |
|---|---|---|
| "monte um dashboard de fretes do mes" | SIM | — |
| "crie uma visualizacao interativa do estoque" | SIM | — |
| "faca uma tela com filtros para os pedidos P1-P7" | SIM | — |
| "lista de pedidos do Atacadao" | NAO | resposta texto + tabela markdown |
| "quanto eu tenho de palmito?" | NAO | responder direto |
| "exporte para Excel" | NAO | usar `exportando-arquivos` |
| "grafico simples de tendencia" | NAO | responder texto + ASCII ou usar chart inline |
| "fluxograma do processo" | NAO | mermaid em markdown |

---

## REGRAS CRITICAS

### R1: APENAS no chat web
Verificar contexto antes de invocar. Se mensagem contem
`[CONTEXTO: Resposta via Microsoft Teams]` ou similar, NAO usar.

### R2: Bundle precisa ser auto-contido
A spec gera projeto Vite+React+TS que **deve buildar sem nenhuma rede**
durante render. Parcel inline tudo. Sem `<script src="https://...">` no HTML.

### R3: Limite 5MB
Bundle final no S3 nao pode exceder 5MB. Componentes pesados (imagens
grandes inline, libs gigantes) sao rejeitados pelo worker.

### R4: Sem dados sensiveis hardcoded
Spec nao deve conter API keys, senhas, CNPJs reais em tela. Use placeholders
ou dados ja consultados pelo agente. **O bundle e servido em iframe
sandboxed sem cookies do app — mas se um link para fora vazar dado
sensivel, fica gravado no S3.**

### R5: Componentes shadcn/ui pre-instalados (40+ via tarball Anthropic)
Skill usa tarball oficial `anthropics/skills/web-artifacts-builder` com 40+
componentes shadcn + Radix UI deps + utils + hooks. Disponiveis SEM
necessidade de instalar nada extra na spec.

**Componentes** (sob `@/components/ui/<nome>`):
- Layout: `card`, `separator`, `aspect-ratio`, `scroll-area`, `resizable`, `sheet`, `drawer`
- Forms: `button`, `input`, `textarea`, `label`, `checkbox`, `radio-group`, `switch`, `select`, `slider`, `toggle`, `toggle-group`, `form` (react-hook-form + zod)
- Feedback: `alert`, `badge`, `toast`, `toaster`, `sonner`, `progress`, `skeleton`, `tooltip`, `hover-card`
- Navegacao: `tabs`, `breadcrumb`, `navigation-menu`, `menubar`, `pagination`
- Overlays: `dialog`, `popover`, `dropdown-menu`, `context-menu`, `command`
- Data display: `table`, `avatar`, `accordion`, `collapsible`, `calendar`, `carousel`

**Utils**:
- `@/lib/utils` → `cn()` helper para classnames
- `@/hooks/use-toast` → hook do toast

**Bibliotecas extra disponiveis** (instaladas no template):
- `lucide-react` (icones)
- `date-fns` (datas)
- `react-hook-form` + `zod` + `@hookform/resolvers` (forms)
- `next-themes` (dark mode)
- `class-variance-authority` + `clsx` + `tailwind-merge`

**Charts** (NAO vem por default): incluir em `spec.dependencies`, ex:
`{"recharts": "^2.10.0"}`.

Import paths CORRETOS:
- `import { Button } from '@/components/ui/button'`
- `import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'`
- `import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'`
- `import { cn } from '@/lib/utils'`
- `import { CheckCircle, Calendar } from 'lucide-react'`

### R6: Path alias `@/` configurado
`@/` aponta para `src/`. Use `@/components/ui/...`, `@/lib/utils`.

### R7: Evitar "AI slop" no design
NAO usar:
- Layouts excessivamente centralizados
- Gradientes roxos (especialmente from-purple-500 to-pink-500)
- Cantos uniformemente arredondados (rounded-2xl em tudo)
- Fonte Inter explicita (usar default do sistema)

---

## ESTRUTURA DA SPEC (input para a tool)

```json
{
  "titulo": "Dashboard Fretes Mai/2026",
  "spec": {
    "components": [
      {
        "path": "src/App.tsx",
        "content": "import { Dashboard } from './Dashboard'; export default function App() { return <Dashboard />; }"
      },
      {
        "path": "src/Dashboard.tsx",
        "content": "..."
      }
    ],
    "dependencies": {
      "recharts": "^2.10.0"
    }
  }
}
```

**Notas**:
- `path` sempre relativo `src/` (ou subpastas).
- `src/main.tsx` e `src/index.css` ja vem do template — NAO sobrescrever.
- Sempre criar `src/App.tsx` como entry component.
- `dependencies` e opcional. Use para libs alem do baseline (recharts,
  date-fns, lucide-react ja vem).

---

## EXEMPLO DE USO PELO AGENTE

```
Usuario: "monte um dashboard com os custos de frete dos ultimos 3 meses"

Agente:
1. Consulta dados via consultando-sql:
   SELECT mes, total_frete FROM ... LIMIT 3

2. Prepara spec:
   {
     "titulo": "Custos de Frete - Ultimos 3 Meses",
     "spec": {
       "components": [
         {"path": "src/App.tsx", "content": "..."},
         {"path": "src/Chart.tsx", "content": "..."}
       ],
       "dependencies": {"recharts": "^2.10.0"}
     }
   }

3. Chama tool build_artifact -> recebe {uuid: "abc123", render_url, status_url}

4. Responde:
   "Preparei o dashboard com os 3 meses. [ARTIFACT:abc123]"

5. Frontend renderiza card com progresso e, quando ready, botao "Abrir".
```

---

## REFERENCIAS

- Fork local — scripts adaptados do `anthropics/skills/web-artifacts-builder`
- Documentacao shadcn/ui: https://ui.shadcn.com/docs/components
- Backend: `app/agente/services/artifact_service.py`
- Worker: `app/agente/workers/artifact_worker.py`
- Tool: `app/agente/tools/artifact_tool.py`
- Modelo: `app/agente/models.py` (AgenteArtifact)
- Modal frontend: `app/agente/templates/agente/chat.html`
