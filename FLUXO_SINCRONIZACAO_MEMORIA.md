# Fluxo de Sincronização com Memória Temporária

## Resumo da Estratégia

### 📊 Passo 1: Criar "Memória" do Estado Atual
```python
# Antes de qualquer alteração, salvar em memória:
carteira_atual = {
    ('PED001', 'PROD001'): {'qtd_saldo': 100, 'qtd_total': 150},
    ('PED001', 'PROD002'): {'qtd_saldo': 50, 'qtd_total': 50},
    ('PED002', 'PROD001'): {'qtd_saldo': 200, 'qtd_total': 200},
    # ... todos os itens atuais
}
```

### 🔄 Passo 2: Buscar Dados Novos do Odoo
```python
dados_odoo = [
    {'num_pedido': 'PED001', 'cod_produto': 'PROD001', 'qtd_saldo': 80},  # Redução de 100→80
    {'num_pedido': 'PED001', 'cod_produto': 'PROD002', 'qtd_saldo': 70},  # Aumento de 50→70
    {'num_pedido': 'PED003', 'cod_produto': 'PROD001', 'qtd_saldo': 30},  # Novo item
    # PED002/PROD001 não veio = foi removido/cancelado
]
```

### 🔍 Passo 3: Comparar e Identificar Mudanças
```python
# Para cada item do Odoo, comparar com a memória:
- PED001/PROD001: 100 → 80 = REDUÇÃO de 20
- PED001/PROD002: 50 → 70 = AUMENTO de 20
- PED003/PROD001: não existia = NOVO
- PED002/PROD001: existia mas não veio = REMOVIDO
```

### ⚡ Passo 4: Aplicar Mudanças ANTES de Alterar Carteira
```python
# 4.1 - Aplicar todas as REDUÇÕES
for reducao in reducoes:
    PreSeparacaoItem.aplicar_reducao_quantidade(
        num_pedido='PED001',
        cod_produto='PROD001', 
        qtd_reduzida=20,
        motivo='SYNC_ODOO'
    )
    # Isso vai consumir: Saldo livre → Pré-separação → Separação

# 4.2 - Aplicar todos os AUMENTOS
for aumento in aumentos:
    PreSeparacaoItem.aplicar_aumento_quantidade(
        num_pedido='PED001',
        cod_produto='PROD002',
        qtd_aumentada=20,
        motivo='SYNC_ODOO'
    )

# 4.3 - Tratar REMOVIDOS (redução total)
for removido in removidos:
    PreSeparacaoItem.aplicar_reducao_quantidade(
        num_pedido='PED002',
        cod_produto='PROD001',
        qtd_reduzida=200,  # toda quantidade
        motivo='SYNC_ODOO_REMOVED'
    )
```

### 💾 Passo 5: Só Então Atualizar a Carteira
```python
# Agora sim, com as quantidades já ajustadas:
db.session.query(CarteiraPrincipal).delete()  # Limpa tudo
for item in dados_odoo:
    db.session.add(CarteiraPrincipal(**item))  # Insere novos
db.session.commit()
```

## 🎯 Vantagens dessa Abordagem

### 1. **Preserva Decisões Operacionais**
```
Cenário: PED001/PROD001 tinha 100 unidades
- 30 em pré-separação
- 40 em separação ABERTO
- 30 livres

Odoo reduz para 80 (-20)
✅ Sistema consome dos 30 livres primeiro
✅ Pré-separações e separações preservadas
```

### 2. **Gera Alertas Críticos**
```
Cenário: Redução afeta separação COTADA
✅ Sistema detecta e gera alerta
✅ Operação sabe que precisa revisar
✅ Mas ainda aplica a redução (Odoo é a fonte da verdade)
```

### 3. **Mantém Consistência**
```
✅ Carteira sempre 100% sincronizada com Odoo
✅ Mas respeitando a hierarquia de impacto
✅ Sem perder decisões já tomadas
```

## 📋 Exemplo Prático Completo

### Estado Inicial:
```
CarteiraPrincipal:
- PED001/PROD001: 100 unidades (30 pré-separadas, 70 livres)
- PED001/PROD002: 50 unidades (todas livres)
- PED002/PROD001: 200 unidades (100 em separação COTADA)
```

### Odoo Envia:
```
- PED001/PROD001: 80 unidades (-20)
- PED001/PROD002: 70 unidades (+20)
- PED003/PROD001: 30 unidades (novo)
- PED002/PROD001: não enviado (cancelado)
```

### Processo:
1. **Memória**: Salva estado atual
2. **Compara**: Identifica -20, +20, novo, cancelado
3. **Aplica**:
   - PED001/PROD001: consome 20 do saldo livre (sobram 50 livres + 30 pré-separadas)
   - PED001/PROD002: adiciona 20 ao saldo livre
   - PED002/PROD001: 🚨 ALERTA! Reduz 200 (afeta COTADA)
4. **Atualiza**: Delete all + Insert com novos dados

### Resultado Final:
```
CarteiraPrincipal (nova):
- PED001/PROD001: 80 unidades
- PED001/PROD002: 70 unidades  
- PED003/PROD001: 30 unidades

PreSeparacao (preservada):
- PED001/PROD001: 30 unidades (intacta)

Alertas:
- 🚨 CRÍTICO: PED002/PROD001 - Separação COTADA afetada por cancelamento
```

## 🔧 Implementação Simplificada

```python
def sync_com_memoria():
    # 1. MEMÓRIA
    memoria = {(i.num_pedido, i.cod_produto): i for i in CarteiraPrincipal.query.all()}
    
    # 2. BUSCAR ODOO
    dados_odoo = self.obter_carteira_pendente()['dados']
    
    # 3. COMPARAR E APLICAR
    for item_odoo in dados_odoo:
        chave = (item_odoo['num_pedido'], item_odoo['cod_produto'])
        
        if chave in memoria:
            qtd_antes = memoria[chave].qtd_saldo_produto_pedido
            qtd_depois = item_odoo['qtd_saldo_produto_pedido']
            
            if qtd_depois < qtd_antes:
                # Aplicar redução ANTES de atualizar
                aplicar_reducao_quantidade(...)
            elif qtd_depois > qtd_antes:
                # Aplicar aumento ANTES de atualizar
                aplicar_aumento_quantidade(...)
    
    # 4. ATUALIZAR CARTEIRA
    CarteiraPrincipal.query.delete()
    # insert all...
```

## Conclusão

Sim, é exatamente isso! A "memória" é temporária (só durante a execução), serve para:
1. Saber o que mudou
2. Aplicar as mudanças respeitando as regras
3. Depois disso, substituir tudo garantindo consistência

É o melhor dos dois mundos: **consistência total** com **respeito às operações**.