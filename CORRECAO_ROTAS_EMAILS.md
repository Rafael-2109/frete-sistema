# ✅ Correção de Rotas - Sistema de Emails

## 🐛 Erro Identificado
```
BuildError: Could not build url for endpoint 'fretes.detalhes' with values ['id']
```

## ✅ Solução Aplicada

### Problema:
Os templates e rotas estavam usando `fretes.detalhes` mas a rota correta é `fretes.visualizar_frete`.

### Arquivos Corrigidos:

1. **`app/fretes/email_routes.py`**
   - Linha 97: `url_for('fretes.detalhes', id=frete_id)` → `url_for('fretes.visualizar_frete', frete_id=frete_id)`

2. **`app/templates/fretes/visualizar_email.html`**
   - Linha 20: `url_for('fretes.detalhes', id=despesa.frete_id)` → `url_for('fretes.visualizar_frete', frete_id=despesa.frete_id)`
   - Linha 109: Mesma correção

## 📋 Rotas Disponíveis no Sistema

### Rotas de Fretes:
- `fretes.index` → `/fretes/` (Dashboard)
- `fretes.visualizar_frete` → `/fretes/<int:frete_id>` (Visualizar frete)
- `fretes.listar_fretes` → `/fretes/listar`
- `fretes.lancar_cte` → `/fretes/lancar_cte`
- `fretes.criar_despesa_extra_frete` → `/fretes/despesas/criar/<int:frete_id>`

### Rotas de Emails:
- `emails.visualizar_email` → `/fretes/emails/<int:email_id>`
- `emails.download_email` → `/fretes/emails/<int:email_id>/download`
- `emails.excluir_email` → `/fretes/emails/<int:email_id>/excluir`
- `emails.listar_emails_frete` → `/fretes/emails/frete/<int:frete_id>`
- `emails.listar_emails_despesa` → `/fretes/emails/despesa/<int:despesa_id>`

## ✅ Status: CORRIGIDO!

O sistema agora está funcionando corretamente. Todas as referências a `fretes.detalhes` foram substituídas por `fretes.visualizar_frete` com os parâmetros corretos.

---

**Data da correção**: 19/08/2025
**Erro corrigido**: BuildError em rotas de emails