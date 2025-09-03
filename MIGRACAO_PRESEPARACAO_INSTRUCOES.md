# 📋 INSTRUÇÕES DE MIGRAÇÃO: PreSeparacaoItem → Separacao

**Data**: 2025-01-29  
**Objetivo**: Migrar gradualmente de PreSeparacaoItem para Separacao com status='PREVISAO'

## 🎯 ESTRATÉGIA DE MIGRAÇÃO GRADUAL

### Fase 1: Preparação ✅ CONCLUÍDA
- [x] Adicionar campo `status` em Separacao
- [x] Adicionar outros campos necessários em Separacao
- [x] Criar adapter PreSeparacaoItem
- [x] Criar APIs alternativas com adapter
- [x] Criar script de teste

### Fase 2: Migração Ponto a Ponto 🚧 EM ANDAMENTO
- [ ] Ativar adapter em desenvolvimento
- [ ] Testar funcionalidades principais
- [ ] Migrar APIs uma por uma
- [ ] Atualizar JavaScript gradualmente

### Fase 3: Limpeza Final
- [ ] Remover PreSeparacaoItem do código
- [ ] Remover tabela do banco
- [ ] Atualizar documentação

---

## 🔧 COMO ATIVAR O ADAPTER

### Opção 1: Substituir Import (Recomendado para Teste)

Em `app/carteira/models.py`, adicione no final:

```python
# ATIVAÇÃO DO ADAPTER - Remover após migração completa
from app.carteira.models_adapter_presep import PreSeparacaoItemAdapter
PreSeparacaoItem = PreSeparacaoItemAdapter
PreSeparacaoItem.query = PreSeparacaoItemAdapter.query_adapter()
```

### Opção 2: Substituir APIs Gradualmente

1. **Testar nova API primeiro**:
```bash
# Testar endpoints v2 que usam adapter
curl http://localhost:5000/api/pre-separacao-v2/salvar
curl http://localhost:5000/api/pedido/TEST-001/pre-separacoes-v2
```

2. **Substituir rotas antigas**:
```python
# Em app/carteira/routes/__init__.py
# Comentar import antigo:
# from .pre_separacao_api import *

# Usar novo com adapter:
from .pre_separacao_api_adapter import *
```

---

## 📝 MAPEAMENTO DE CAMPOS

| PreSeparacaoItem | Separacao | Observação |
|------------------|-----------|------------|
| separacao_lote_id | separacao_lote_id | Mesmo campo |
| num_pedido | num_pedido | Mesmo campo |
| cod_produto | cod_produto | Mesmo campo |
| cnpj_cliente | cnpj_cpf | Nome diferente |
| qtd_selecionada_usuario | qtd_saldo | Nome diferente |
| valor_original_item | valor_saldo | Nome diferente |
| peso_original_item | peso | Nome diferente |
| data_expedicao_editada | expedicao | Nome diferente |
| data_agendamento_editada | agendamento | Nome diferente |
| protocolo_editado | protocolo | Nome diferente |
| observacoes_usuario | observ_ped_1 | Nome diferente |
| recomposto=False | status='PREVISAO' | Lógica diferente |
| recomposto=True | status='ABERTO' | Lógica diferente |
| status='CRIADO' | status='PREVISAO' | Mapeamento |
| status='CONFIRMADO' | status='ABERTO' | Mapeamento |

---

## 🧪 TESTES ANTES DA MIGRAÇÃO

### 1. Testar Adapter Localmente
```bash
python testar_adapter_presep.py
```

### 2. Verificar Dados Existentes
```sql
-- Verificar se existem pré-separações antigas
SELECT COUNT(*) FROM pre_separacao_item WHERE recomposto = false;

-- Verificar separações com novo status
SELECT COUNT(*) FROM separacao WHERE status = 'PREVISAO';
```

### 3. Testar Workspace
1. Abrir carteira agrupada
2. Fazer drag & drop de produtos
3. Verificar se cria Separacao com status='PREVISAO'
4. Transformar em separação definitiva
5. Verificar se muda para status='ABERTO'

---

## 🚀 ROTEIRO DE MIGRAÇÃO POR ARQUIVO

### Backend Python (33 arquivos)

#### PRIORIDADE ALTA - APIs Principais:
1. **app/carteira/routes/pre_separacao_api.py**
   - Substituir imports
   - Usar adapter ou nova API

2. **app/carteira/routes/separacao_api.py**
   - Linhas 23, 43, 72, 360-461: Substituir PreSeparacaoItem

3. **app/carteira/routes/workspace_api.py**
   - Atualizar queries de pré-separação

#### PRIORIDADE MÉDIA - Services:
4. **app/carteira/services/agrupamento_service.py**
5. **app/carteira/services/atualizar_dados_service.py**
6. **app/odoo/services/carteira_service.py**

#### PRIORIDADE BAIXA - Outros:
- Demais arquivos listados em MAPEAMENTO_PRESEPARACAOITEM.md

### Frontend JavaScript (6 arquivos)

#### PRIORIDADE ALTA:
1. **app/templates/carteira/js/pre-separacao-manager.js**
   - Função principal do workspace
   - Adaptar para usar status='PREVISAO'

2. **app/templates/carteira/js/workspace-montagem.js**
   - Drag & drop
   - Verificar compatibilidade

3. **app/templates/carteira/js/separacao-manager.js**
   - Conversão de pré para definitiva
   - Mudar lógica para atualizar status

---

## ⚠️ PONTOS DE ATENÇÃO

### 1. Campo `recomposto`
- **Antes**: PreSeparacaoItem.recomposto = True/False
- **Depois**: Separacao.status = 'PREVISAO'/'ABERTO'
- **Adapter**: Mapeia automaticamente

### 2. Query de busca
- **Antes**: 
```python
PreSeparacaoItem.query.filter_by(
    separacao_lote_id=lote_id,
    recomposto=False
)
```
- **Depois**:
```python
Separacao.query.filter_by(
    separacao_lote_id=lote_id,
    status='PREVISAO'
)
```

### 3. Transformar em definitiva
- **Antes**: Criar nova Separacao e marcar PreSeparacaoItem.recomposto=True
- **Depois**: Apenas UPDATE status de 'PREVISAO' para 'ABERTO'

---

## 📊 MONITORAMENTO DA MIGRAÇÃO

### Queries para Acompanhar:
```sql
-- Contar pré-separações antigas
SELECT COUNT(*) as antigas FROM pre_separacao_item;

-- Contar novas pré-separações
SELECT COUNT(*) as novas FROM separacao WHERE status = 'PREVISAO';

-- Verificar consistência
SELECT 
    p.separacao_lote_id,
    COUNT(DISTINCT p.id) as pre_sep_count,
    COUNT(DISTINCT s.id) as sep_count
FROM pre_separacao_item p
LEFT JOIN separacao s ON s.separacao_lote_id = p.separacao_lote_id
WHERE p.recomposto = false
GROUP BY p.separacao_lote_id
HAVING COUNT(DISTINCT p.id) != COUNT(DISTINCT s.id);
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

Antes de considerar a migração completa:

- [ ] Workspace cria Separacao com status='PREVISAO'
- [ ] Drag & drop funciona normalmente
- [ ] Transformar em separação muda status para 'ABERTO'
- [ ] Agendamento funciona com novo modelo
- [ ] Relatórios mostram dados corretos
- [ ] Integração Odoo continua funcionando
- [ ] Não há mais referências a PreSeparacaoItem no código
- [ ] Tabela pre_separacao_item pode ser removida

---

## 🔄 ROLLBACK (Se Necessário)

Se algo der errado:

1. **Desativar adapter**:
```python
# Comentar em app/carteira/models.py
# from app.carteira.models_adapter_presep import PreSeparacaoItemAdapter
# PreSeparacaoItem = PreSeparacaoItemAdapter
```

2. **Reverter APIs**:
```bash
# Voltar para versão antiga
git checkout app/carteira/routes/pre_separacao_api.py
```

3. **Limpar dados de teste**:
```sql
-- Remover separações de teste
DELETE FROM separacao WHERE status = 'PREVISAO' AND criado_em > '2025-01-29';
```

---

## 📞 SUPORTE

Em caso de dúvidas durante a migração:
1. Verificar logs de erro
2. Executar script de teste: `python testar_adapter_presep.py`
3. Consultar MAPEAMENTO_PRESEPARACAOITEM.md
4. Verificar este documento

---

**IMPORTANTE**: Fazer backup do banco antes de iniciar migração em produção!