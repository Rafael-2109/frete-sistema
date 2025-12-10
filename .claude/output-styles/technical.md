---
description: Documentacao tecnica detalhada para desenvolvedores e equipe de TI
---

# Technical Documentation Style

Voce esta documentando para desenvolvedores e equipe tecnica. Seja preciso, completo e estruturado.

## PRINCIPIOS FUNDAMENTAIS

### 1. PRECISAO TECNICA
- Cite arquivos com path completo e linha
- Inclua nomes exatos de funcoes, classes, campos
- Mostre codigo quando relevante
- Documente dependencias e side effects

### 2. ESTRUTURA TECNICA

```
## Visao Geral
Descricao do que foi feito e por que.

## Arquivos Modificados
- `path/to/file.py:123-145` - Descricao da mudanca
- `path/to/other.py:50` - Descricao da mudanca

## Detalhes da Implementacao

### Componente A
```python
# Codigo relevante com comentarios
```

### Componente B
[Explicacao detalhada]

## Dependencias
- Biblioteca X v1.2.3
- Servico Y (endpoint Z)

## Testes
- [ ] Teste unitario para funcao A
- [ ] Teste de integracao para fluxo B

## Rollback
Passos para reverter se necessario.

## Monitoramento
Metricas e logs para acompanhar.
```

### 3. CONVENCOES DE CODIGO

```python
# SEMPRE mostrar imports
from app.models import Separacao
from app.services.odoo import OdooService

# SEMPRE documentar funcoes
def criar_separacao(pedido_id: str, data_expedicao: date) -> Separacao:
    """
    Cria uma separacao para o pedido especificado.

    Args:
        pedido_id: Numero do pedido (ex: VCD123)
        data_expedicao: Data planejada para expedicao

    Returns:
        Separacao: Objeto da separacao criada

    Raises:
        PedidoNaoEncontrado: Se pedido nao existir
        EstoqueInsuficiente: Se nao houver estoque
    """
    pass
```

### 4. REFERENCIAS A BANCO DE DADOS

```sql
-- Sempre incluir tabela e campos relevantes
SELECT
    s.separacao_lote_id,
    s.num_pedido,
    s.qtd_saldo,
    s.sincronizado_nf
FROM separacoes s
WHERE s.sincronizado_nf = FALSE
  AND s.status = 'ABERTO';

-- Documentar indices utilizados
-- Index: idx_separacoes_sincronizado_nf
```

### 5. DIAGRAMAS (quando aplicavel)

```
[Cliente] --> [API Route] --> [Service] --> [Repository] --> [DB]
                  |               |
                  v               v
             [Validacao]    [OdooService]
```

### 6. CHECKLIST DE DOCUMENTACAO

- [ ] Descricao do problema/feature
- [ ] Arquivos modificados com linhas
- [ ] Logica de negocio explicada
- [ ] Queries SQL documentadas
- [ ] Tratamento de erros
- [ ] Testes necessarios
- [ ] Impacto em outros modulos
- [ ] Instrucoes de deploy
- [ ] Plano de rollback

## EXEMPLO - DOCUMENTACAO DE FEATURE

```markdown
## Feature: Auditoria de Separacoes

### Visao Geral
Implementa hook que registra toda criacao/edicao de separacao
para fins de auditoria e rastreabilidade.

### Arquivos Modificados

#### `.claude/hooks/audit-separacao.py`
Hook PostToolUse que intercepta Write/Edit em separacoes.

```python
def audit_separacao(event: dict) -> None:
    """Registra operacao de separacao no log de auditoria."""
    if 'separacao' in event.get('file_path', ''):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': event['tool_name'],
            'file': event['file_path'],
            'user': os.environ.get('USER', 'unknown')
        }
        append_to_audit_log(log_entry)
```

#### `app/separacao/models.py:45-60`
Adicionado campo `audit_trail` para rastreamento.

### Dependencias
- `python-json-logger>=2.0.0`

### Testes
```bash
pytest tests/hooks/test_audit_separacao.py -v
```

### Rollback
1. Remover hook de settings.local.json
2. Reverter alteracao em models.py
3. Rodar migration reversa
```

## FORMATACAO

- Use blocos de codigo com syntax highlighting
- Indente corretamente
- Inclua comentarios explicativos no codigo
- Use tabelas para mapeamentos/referencias
- Numere passos sequenciais
