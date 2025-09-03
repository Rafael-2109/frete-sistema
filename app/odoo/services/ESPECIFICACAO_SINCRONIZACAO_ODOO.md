# 📋 ESPECIFICAÇÃO TÉCNICA: Sincronização Odoo → Sistema Frete

## 📊 VISÃO GERAL
Documentação do processo de sincronização de Notas Fiscais do Odoo com o sistema de frete, incluindo regras de negócio, validações e movimentações de estoque.

**Status**: Especificação para implementação futura  
**Data**: 29/01/2025

---

## 🔄 FLUXO PRINCIPAL DO FaturamentoService

### 1️⃣ BUSCA DE NOTAS FISCAIS
```
FaturamentoService busca NFs dos últimos 5 dias no Odoo
```

### 2️⃣ PROCESSAMENTO DE NFs CANCELADAS
```python
SE NF.status == 'cancelado':
    SE existe em FaturamentoProduto AND status != 'Cancelado':
        - Cancela MovimentacaoEstoque relacionada (status_nf=CANCELADO)
        - Atualizar FaturamentoProduto.status = 'Cancelado'
        - Apaga NF de EmbarqueItem
        - Gera alerta
    SENÃO:
        - Pular NF (já processada ou não existe)
```

### 3️⃣ VERIFICAÇÃO DE NF JÁ PROCESSADA
```python
SE NF existe em FaturamentoProduto:
    - Pular NF (já processada)
SENÃO:
    - Buscar separacao_lote_id
    - Processar NF
```

### 4️⃣ PROCESSAMENTO DE NF NOVA

#### 4.1 Separação Completa
```python
SE Separacao.tipo_envio == 'total':
    - Buscar pelo pedido em EmbarqueItem
    - Processar NF com separacao_lote_id encontrado
```

#### 4.2 Separação Parcial - Caso Simples
```python
SE Separacao.tipo_envio == 'parcial':
    SE existe apenas 1 EmbarqueItem para num_pedido:
        - Processar NF com separacao_lote_id encontrado
```

#### 4.3 Separação Parcial - Caso Complexo
```python
SE Separacao.tipo_envio == 'parcial':
    SE existem 2+ EmbarqueItem para num_pedido AND ambos sem numero_nf:
        - Calcular score: comparar produtos + quantidades
        - Selecionar melhor match
        - Pegar separacao_lote_id do melhor match
        - Processar NF com separacao_lote_id encontrado
```

#### 4.4 Pedido Não Encontrado
```python
SE não encontrar pedido:
    - Gerar MovimentacaoEstoque SEM separacao_lote_id
    - Criar alerta: "NF sem pedido correspondente"
```

---

## 📝 PROCESSAMENTO DE NF (Detalhado)

### Ações ao Processar NF:
1. **Atualizar EmbarqueItem**
   - `EmbarqueItem.nota_fiscal = numero_nf`
   - `EmbarqueItem.erro_validacao = None (verificar se é assim mesmo)`

2. **Atualizar Separacao**
   - `Separacao.numero_nf = numero_nf`
   - `Separacao.sincronizado_nf = True`
   - `Separacao.data_sincronizacao = datetime.now()`

3. **Criar/Atualizar MovimentacaoEstoque**
   - `MovimentacaoEstoque.numero_nf = numero_nf`
   - `MovimentacaoEstoque.separacao_lote_id = separacao_lote_id`
   - `MovimentacaoEstoque.status_nf = 'faturado'`
   - `MovimentacaoEstoque.num_pedido = num_pedido`
   - `MovimentacaoEstoque.codigo_embarque = campo FK`

---

## 🗄️ ALTERAÇÕES EM MovimentacaoEstoque

### Novos Campos Propostos:
```python
class MovimentacaoEstoque(db.Model):
    # Campos existentes...
    
    # Campos estruturados para sincronização NF (NOVO)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    numero_nf = db.Column(db.String(20), nullable=True, index=True)  # Número da NF
    num_pedido = db.Column(db.String(50), nullable=True, index=True)  # Número do pedido
    tipo_origem = db.Column(db.String(20), nullable=True)  # ODOO, TAGPLUS, MANUAL, LEGADO
    status_nf = db.Column(db.String(20), nullable=True)  # FATURADO, CANCELADO
    codigo_embarque = db.Column(db.Integer, db.ForeignKey('embarques.id', ondelete='SET NULL'), nullable=True)
    
    # ⚠️ NÃO CRIAR constraint único sem incluir cod_produto
    # Movimentações não relacionadas a faturamento podem conflitar
    # Índices compostos para performance  
    __table_args__ = (
        db.Index('idx_movimentacao_produto_data', 'cod_produto', 'data_movimentacao'),
        db.Index('idx_movimentacao_tipo_data', 'tipo_movimentacao', 'data_movimentacao'),
        db.Index('idx_movimentacao_nf', 'numero_nf'),
        db.Index('idx_movimentacao_lote', 'separacao_lote_id'),
        db.Index('idx_movimentacao_pedido', 'num_pedido'),
        db.Index('idx_movimentacao_tipo_origem', 'tipo_origem'),
        db.Index('idx_movimentacao_status_nf', 'status_nf'),
    )
```

---

## 📊 CÁLCULO DE SALDOS NA CarteiraPrincipal

### Fórmula do Saldo Disponível:
```sql
qtd_saldo_produto_pedido = qtd_produto_pedido - qtd_cancelada - qtd_faturada

Onde:
- qtd_produto_pedido: Quantidade original do pedido
- qtd_cancelada: CarteiraPrincipal.qtd_cancelada_produto_pedido
- qtd_faturada: SUM(FaturamentoProduto.qtd_produto_faturado) 
                WHERE FaturamentoProduto.origem = CarteiraPrincipal.num_pedido 
                  AND FaturamentoProduto.cod_produto = CarteiraPrincipal.cod_produto
                  AND FaturamentoProduto.status_nf != 'Cancelado'
```

### Validação de Saldo Negativo:
```python
SE qtd_saldo_produto_pedido < 0:
    - Criar alerta: "NF devolvida - saldo negativo"
    - Possível devolução ou erro de faturamento
```

---

## 🔄 REGRAS DE IMPORTAÇÃO DA CARTEIRA

### 1. Adição de Pedidos/Itens
- **Toda importação** adiciona novos pedidos/itens se não existirem
- Verificar duplicação por `num_pedido` + `cod_produto`

### 2. Atualização de Quantidade
```python
SE atualizar qtd_produto_pedido:
    SE tipo_envio == 'total':
        SE existe Separacao com status == 'COTADO':
            - Criar alerta: "Quantidade alterada em pedido já cotado"
            - Atualizar Separacao mesmo assim
    SE tipo_envio == 'parcial':
        # Hierarquia de atualização (sempre com sincronizado_nf=False):
        1. Atualizar saldo da CarteiraPrincipal primeiro
        2. Depois atualizar Separacao na ordem: PREVISAO → ABERTO → COTADO → FATURADO
        3. SEMPRE filtrar por sincronizado_nf=False (não atualizar NF já validada)
```

### 3. Atualização de Cancelamento
```python
SE atualizar qtd_cancelada_produto_pedido:
    SE tipo_envio == 'total':
        SE existe Separacao com status == 'COTADO':
            - Criar alerta: "Cancelamento parcial em pedido já cotado"
            - Atualizar Separacao mesmo assim
    SE tipo_envio == 'parcial':
        # Mesma hierarquia de atualização
        - Aplicar hierarquia: CarteiraPrincipal → PREVISAO → ABERTO → COTADO → FATURADO
        - SEMPRE com sincronizado_nf=False
```

### 4. Atualização de Status
```python
SE CarteiraPrincipal.status muda para 'cancelado':
    SE existe Separacao com status == 'COTADO':
        - Criar alerta: "Pedido cotado foi cancelado no Odoo"
        - Avaliar manualmente se deve cancelar embarque
    SENÃO:
        - Cancelar normalmente
```

---

## 📈 CÁLCULOS E PROJEÇÕES

### Saldo da Carteira:
```sql
saldo_carteira = CarteiraPrincipal.qtd_saldo_produto_pedido 
                - SUM(Separacao.qtd_saldo WHERE sincronizado_nf = FALSE)
```

### Separações na Carteira:
```sql
separacoes_carteira = SELECT * FROM Separacao 
                      WHERE sincronizado_nf = FALSE
```

### Projeção de Estoque:
- **Considerar apenas**: `Separacao.sincronizado_nf = FALSE`
- **Ignorar**: Separações já faturadas (sincronizado_nf = TRUE)

---

## 🚨 ALERTAS E VALIDAÇÕES

### Tipos de Alertas:
1. **NF Devolvida**: `qtd_saldo_produto_pedido < 0`
2. **NF sem Pedido**: MovimentacaoEstoque sem separacao_lote_id
3. **Alteração em Cotado**: Mudança que impacta pedido com Separacao.status = 'COTADO'
4. **Cancelamento em Cotado**: Tentativa de cancelar pedido com Separacao.status = 'COTADO'
5. **Score Baixo**: Match de NF com separação tem score < 80%

### Log de Sincronização:
```python
{
    'timestamp': datetime.now(),
    'tipo': 'sincronizacao_nf',
    'numero_nf': numero_nf,
    'separacao_lote_id': separacao_lote_id,
    'status': 'sucesso/erro',
    'alertas': [...],
    'detalhes': {...}
}
```

---

## 🔍 ALGORITMO DE SCORE PARA MATCH

### Cálculo de Score (Separação Parcial com Múltiplos EmbarqueItem):
```python
def calcular_score(nf_produtos, embarque_item):
    score_total = 0
    matches = 0
    
    for produto_nf in nf_produtos:
        for produto_embarque in embarque_item.produtos:
            if produto_nf.codigo == produto_embarque.codigo:
                # Score baseado na proximidade de quantidade
                diff = abs(produto_nf.qtd - produto_embarque.qtd)
                score_produto = 100 - (diff / produto_nf.qtd * 100)
                score_total += max(0, score_produto)
                matches += 1
    
    if matches == 0:
        return 0
    
    return score_total / matches
```

### Decisão:
- **Score >= 80%**: Match confiável, processar normalmente
- **Score 60-79%**: Match duvidoso, criar alerta mas SEMPRE processar
- **Score < 60%**: Match ruim, criar alerta crítico mas SEMPRE processar
- **REGRA**: NUNCA deixar de processar uma NF, no máximo criar alertas

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1 - Preparação do Banco:
- [ ] Adicionar campos em MovimentacaoEstoque (separacao_lote_id, numero_nf, status)
- [ ] Criar índices únicos
- [ ] Migrar dados existentes

### Fase 2 - FaturamentoService:
- [ ] Implementar busca de NFs dos últimos 5 dias
- [ ] Implementar processamento de cancelamentos
- [ ] Implementar verificação de duplicação
- [ ] Implementar algoritmo de score

### Fase 3 - Processamento de NF:
- [ ] Atualizar EmbarqueItem
- [ ] Atualizar Separacao
- [ ] Criar/Atualizar MovimentacaoEstoque
- [ ] Implementar sistema de alertas

### Fase 4 - Importação da Carteira:
- [ ] Implementar validações de alteração
- [ ] Implementar alertas de pedidos cotados
- [ ] Atualizar cálculo de saldo

### Fase 5 - Testes e Validação:
- [ ] Testes unitários
- [ ] Testes de integração
- [ ] Validação com dados reais
- [ ] Documentação de uso

---

## 🎯 IMPACTOS NO SISTEMA

### Módulos Afetados:
1. **app.odoo.services.faturamento_service** - FaturamentoService
2. **app.odoo.services.carteira_service** - CarteiraService  
3. **app.estoque.models** - MovimentacaoEstoque
4. **app.embarques.models** - EmbarqueItem
5. **app.separacao.models** - Separacao

### Benefícios Esperados:
- ✅ Rastreabilidade completa NF ↔ Separação
- ✅ Detecção automática de devoluções
- ✅ Alertas inteligentes para alterações em pedidos cotados
- ✅ Melhor controle de estoque
- ✅ Alertas proativos de inconsistências

---

## 📝 NOTAS IMPORTANTES

1. **sincronizado_nf = True**: Item sai da carteira e não projeta mais estoque
2. **MovimentacaoEstoque**: Agora terá vínculo direto com Separacao
3. **Alertas**: Sistema proativo de detecção de problemas
4. **Score**: Algoritmo inteligente para match de NFs parciais
5. **Cancelamentos**: Tratamento especial para NFs canceladas

---

**📅 Última Atualização**: 29/01/2025  
**👤 Autor**: Sistema de Documentação Automática  
**📌 Status**: Aguardando Implementação


1- Sim
2- Sim
3- Sim
4- Sim, quando voce cita "CarteiraPrincipal primeiro" voce quer dizer o saldo que não possui Separacao.sincronizado_nf=False correto?
Ou seja, CarteiraPrincipal.qtd_saldo_produto_pedido - SUM(Separacao.qtd_saldo WHERE sincronizado_nf = FALSE)
5- Sim e qtd_cancelada existe, portanto DEVE ser importado (respondendo pois voce citou "se houver", resposta: HÁ)