# workflow-create

Create reusable workflow templates.

## Usage
```bash
npx claude-flow workflow create [options]
```

## Options
- `--name <name>` - Workflow name
- `--from-history` - Create from history
- `--interactive` - Interactive creation

## Examples
```bash
# Create workflow
npx claude-flow workflow create --name "deploy-api"

# From history
npx claude-flow workflow create --name "test-suite" --from-history

# Interactive mode
npx claude-flow workflow create --interactive
```

npx claude-flow workflow create --name "odoo-sync-reverse-engineering" --steps "
1. swarm init --topology mesh --agents 5
2. task 'Engenharia reversa completa da Sincronização Segura Odoo'
3. memory store análises
4. docs-writer 'Gerar documentação em docs/odoo-sync-analysis/'
" && npx claude-flow workflow execute --name "odoo-sync-reverse-engineering"

📁 Estrutura de Saída Esperada

docs/odoo-sync-analysis/
├── README.md                    # Visão geral da análise
├── pseudocode/
│   ├── frontend-flow.md        # Pseudocódigo do JavaScript
│   ├── backend-flow.md         # Pseudocódigo das rotas Python
│   └── integration-flow.md     # Pseudocódigo da integração Odoo
├── architecture/
│   ├── flow-diagram.md         # Diagrama de fluxo
│   ├── sequence-diagram.md     # Diagrama de sequência
│   └── components.md           # Componentes e dependências
├── security/
│   └── security-analysis.md    # Análise de segurança
├── api/
│   ├── endpoints.md           # Documentação das APIs
│   └── odoo-integration.md    # Detalhes da integração
└── database/
    └── queries.md             # Queries e operações DB
