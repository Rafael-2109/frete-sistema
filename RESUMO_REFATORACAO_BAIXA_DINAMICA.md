# Resumo da Refatoração - Baixa Dinâmica TagPlus

## Mudanças Implementadas

### 1. CarteiraCopia (app/carteira/models.py)
- **Adicionado**: `hybrid_property` para calcular `baixa_produto_pedido` dinamicamente
- **Renomeado**: Campo original para `_baixa_produto_pedido_old` (mantém dados históricos)
- **Modificado**: `recalcular_saldo()` agora usa a property calculada

```python
@hybrid_property
def baixa_produto_pedido(self):
    """Calcula dinamicamente baseado em FaturamentoProduto"""
    # Soma qtd_produto_faturado onde:
    # - origem = num_pedido
    # - cod_produto = cod_produto
```

### 2. ProcessadorFaturamentoTagPlus
- **Removido**: Método `_atualizar_baixa_carteira()`
- **Mantido**: Atualização do campo `origem` em FaturamentoProduto
- **Simplificado**: Processo agora apenas vincula pedido via campo origem

### 3. Importação Excel (servico_importacao_excel.py)
- **Removido**: Validação que impedia reimportação
- **Adicionado**: Lógica para atualizar registros existentes
- **Permite**: Correções e reimportações sem duplicar dados

### 4. Movimentações de Estoque
- **Mantido**: Sempre cria movimentação quando `processar_completo=True`
- **Proteção**: Verifica duplicação por produto + NF na observação
- **Casos**:
  - COM separação: "Baixa automática NF XXX - Lote YYY"
  - SEM separação: "Baixa automática NF XXX - Sem Separação"

## Benefícios

1. **Fonte Única da Verdade**: FaturamentoProduto é a única fonte para baixas
2. **Sempre Sincronizado**: Baixa reflete automaticamente a realidade
3. **Permite Correções**: Reimportações atualizam valores automaticamente
4. **Sem Duplicação**: Lógica centralizada em um único lugar
5. **Auditável**: Histórico completo em FaturamentoProduto

## Como Funciona Agora

### Importação
1. Importa Excel criando/atualizando FaturamentoProduto
2. Se `processar_completo=True`:
   - Busca separação por score
   - Cria movimentação de estoque
   - Vincula origem (num_pedido) se encontrar match

### Cálculo de Baixa
1. CarteiraCopia.baixa_produto_pedido é calculada em tempo real
2. Soma todos FaturamentoProduto onde:
   - origem = num_pedido da carteira
   - cod_produto = cod_produto da carteira

### Movimentação de Estoque
- SEMPRE criada quando processamento completo
- Independe de ter separação ou embarque
- Protegida contra duplicação

## Scripts Auxiliares

1. **diagnostico_tagplus_estoque.py**: Verifica status da importação
2. **criar_migration_baixa_dinamica.py**: Cria migration se necessário

## Próximos Passos

1. Testar importação com arquivo Excel
2. Verificar cálculo dinâmico de baixa
3. Confirmar criação de movimentações
4. Validar reimportação/correção de NFs