# Refatoração: Baixa Dinâmica de Pedidos

## Problema Atual
- `baixa_produto_pedido` é um campo que é incrementado durante importação
- Pode ficar dessincronizado se houver reimportações ou correções
- Validações impedem reprocessamento de NFs já existentes

## Solução Proposta
Transformar `baixa_produto_pedido` em um campo calculado dinamicamente a partir de `FaturamentoProduto`.

## Implementação

### 1. Adicionar Property em CarteiraCopia

```python
# app/carteira/models.py - classe CarteiraCopia

@property
def baixa_produto_pedido_calculada(self):
    """
    Calcula dinamicamente a baixa do produto baseada em FaturamentoProduto
    Soma todas as quantidades faturadas onde:
    - origem = num_pedido
    - cod_produto = cod_produto
    """
    from app.faturamento.models import FaturamentoProduto
    from sqlalchemy import func
    
    total_baixa = db.session.query(
        func.sum(FaturamentoProduto.qtd_produto_faturado)
    ).filter(
        FaturamentoProduto.origem == self.num_pedido,
        FaturamentoProduto.cod_produto == self.cod_produto
    ).scalar()
    
    return total_baixa or 0

def recalcular_saldo(self):
    """Recalcula saldo usando a baixa dinâmica"""
    # Usa a property calculada ao invés do campo
    self.qtd_saldo_produto_calculado = (
        self.qtd_produto_pedido - 
        self.qtd_cancelada_produto_pedido - 
        self.baixa_produto_pedido_calculada  # Usa property
    )
```

### 2. Migração para Manter Compatibilidade

```python
# Nova migration
def upgrade():
    # Renomeia campo antigo para backup
    op.alter_column('carteira_copia', 'baixa_produto_pedido', 
                    new_column_name='baixa_produto_pedido_old')
    
    # Cria view ou computed column (dependendo do banco)
    # Para PostgreSQL:
    op.execute("""
        ALTER TABLE carteira_copia 
        ADD COLUMN baixa_produto_pedido NUMERIC(15,3) 
        GENERATED ALWAYS AS (
            SELECT COALESCE(SUM(fp.qtd_produto_faturado), 0)
            FROM faturamento_produto fp
            WHERE fp.origem = carteira_copia.num_pedido
            AND fp.cod_produto = carteira_copia.cod_produto
        ) STORED
    """)
```

### 3. Remover Atualizações do Processador

```python
# app/integracoes/tagplus/processador_faturamento_tagplus.py

def processar_nf_tagplus(self, faturamento_produto):
    """Processa uma NF do TagPlus"""
    try:
        # 1. Encontrar separação (mantém)
        embarque_item_match = self._encontrar_separacao_por_score(faturamento_produto)
        
        # 2. Criar movimentação de estoque (mantém)
        self._criar_movimentacao_estoque(faturamento_produto, separacao_lote_id)
        
        # 3. Atualizar EmbarqueItem (mantém)
        if embarque_item_match:
            self._atualizar_embarque_item(faturamento_produto, embarque_item_match)
        
        # 4. REMOVER atualização de baixa - será calculada dinamicamente
        # if num_pedido:
        #     self._atualizar_baixa_carteira(...)  # REMOVER
        
        # 5. Atualizar origem no FaturamentoProduto (MANTER!)
        if num_pedido:
            faturamento_produto.origem = num_pedido
        
        # 6. Consolidar (mantém)
        self._consolidar_relatorio(faturamento_produto, num_pedido)
```

### 4. Ajustar Validações de Importação

```python
# app/integracoes/tagplus/servico_importacao_excel.py

def criar_registros_faturamento(numero_nf, razao_social, cnpj, itens):
    """Cria ou atualiza registros de FaturamentoProduto"""
    try:
        # REMOVER validação que impede reprocessamento
        # Permitir sempre criar/atualizar FaturamentoProduto
        
        # Verificar se já existe para UPDATE ao invés de INSERT
        for item in itens:
            faturamento_existente = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf,
                cod_produto=item['cod_produto']
            ).first()
            
            if faturamento_existente:
                # Atualiza registro existente
                faturamento_existente.qtd_produto_faturado = item['qtd_produto_faturado']
                faturamento_existente.valor_produto_faturado = item['valor_produto_faturado']
                # ... outros campos
            else:
                # Cria novo registro
                faturamento = FaturamentoProduto(...)
                db.session.add(faturamento)
```

## Benefícios

1. **Sempre Sincronizado**: Baixa sempre reflete realidade de FaturamentoProduto
2. **Permite Correções**: Reimportações e ajustes são refletidos automaticamente
3. **Sem Duplicação**: Lógica centralizada em um único lugar
4. **Auditável**: FaturamentoProduto é a fonte única da verdade

## Alternativa Mais Simples (Sem Migration)

Se não quiser usar computed column no banco, pode usar hybrid_property do SQLAlchemy:

```python
from sqlalchemy.ext.hybrid import hybrid_property

class CarteiraCopia(db.Model):
    # ... campos existentes ...
    
    _baixa_produto_pedido = db.Column('baixa_produto_pedido', db.Numeric(15, 3), default=0)
    
    @hybrid_property
    def baixa_produto_pedido(self):
        """Sempre calcula dinamicamente"""
        from app.faturamento.models import FaturamentoProduto
        total = db.session.query(
            func.sum(FaturamentoProduto.qtd_produto_faturado)
        ).filter(
            FaturamentoProduto.origem == self.num_pedido,
            FaturamentoProduto.cod_produto == self.cod_produto
        ).scalar()
        return total or 0
    
    @baixa_produto_pedido.expression
    def baixa_produto_pedido(cls):
        """Para queries SQL"""
        from app.faturamento.models import FaturamentoProduto
        return db.session.query(
            func.coalesce(func.sum(FaturamentoProduto.qtd_produto_faturado), 0)
        ).filter(
            FaturamentoProduto.origem == cls.num_pedido,
            FaturamentoProduto.cod_produto == cls.cod_produto
        ).as_scalar()
```

## Passos de Implementação

1. Adicionar property/hybrid_property em CarteiraCopia
2. Remover `_atualizar_baixa_carteira` do processador
3. Ajustar validações para permitir reprocessamento
4. Testar cálculo dinâmico
5. (Opcional) Criar migration para computed column