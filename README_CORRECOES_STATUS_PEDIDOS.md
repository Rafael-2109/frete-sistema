# 🔧 Correções de Status dos Pedidos

## 📋 Problemas Identificados

1. **Embarque FOB**: Pedidos com rota "FOB" não ficavam com status "COTADO" após criar embarque FOB
2. **Inclusão em Embarque**: Ao incluir pedidos em embarques existentes, o status não era atualizado para "COTADO"
3. **Dados Históricos**: Pedidos já em embarques ativos não tinham status correto

## ✅ Correções Implementadas

### 1. **Embarque FOB** (`app/pedidos/routes.py`)
**Problema**: FOB não criava cotação, então `cotacao_id` ficava `None` e status permanecia "ABERTO"

**Solução**:
- Criar cotação fictícia para FOB com tipo "FOB"
- Associar `cotacao_id` aos pedidos FOB
- Definir transportadora como "FOB - COLETA"
- Status calculado automaticamente como "COTADO"

### 2. **Inclusão em Embarque Existente** (`app/cotacao/routes.py`)
**Problema**: Pedidos incluídos em embarques não tinham `cotacao_id` atualizado

**Solução**:
- Copiar `cotacao_id` do embarque para o pedido
- Definir transportadora do embarque
- Resetar flag `nf_cd`
- Status calculado automaticamente como "COTADO"

### 3. **Fechamento de Frete** (`app/cotacao/routes.py`)
**Problema**: Garantir que todos os fluxos de cotação atualizem corretamente

**Solução**:
- Adicionar `pedido.nf_cd = False` em todos os fluxos
- Garantir que `cotacao_id` e `transportadora` sejam definidos
- Status calculado automaticamente pelo trigger

### 4. **Script de Correção Histórica** (`atualizar_status_pedidos_embarques.py`)
**Problema**: Pedidos já em embarques ativos com status incorreto

**Solução**:
- Script para uso único que corrige dados históricos
- Busca todos os embarques ativos
- Atualiza pedidos para status "COTADO"
- Relatório detalhado das alterações

## 🔄 Lógica do Status Calculado

O status é calculado automaticamente pela property `status_calculado` no modelo `Pedido`:

```python
@property
def status_calculado(self):
    if getattr(self, 'nf_cd', False):
        return 'NF no CD'
    elif self.nf and self.nf.strip():
        return 'FATURADO'
    elif self.data_embarque:
        return 'EMBARCADO'
    elif self.cotacao_id:          # ← Aqui que FOB precisa ter cotacao_id
        return 'COTADO'
    else:
        return 'ABERTO'
```

## 🚀 Como Usar

### Script de Correção (Uso Único)
```bash
python atualizar_status_pedidos_embarques.py
```

### Fluxos Corrigidos
1. **Embarque FOB**: Selecionar pedidos FOB → "Embarque FOB" → Status = "COTADO"
2. **Inclusão**: Cotar pedidos → "Incluir ao Embarque" → Status = "COTADO"
3. **Cotação Normal**: Cotar pedidos → "Fechar Frete" → Status = "COTADO"

## 📊 Campos Atualizados

Para todos os fluxos, os seguintes campos são atualizados:
- `cotacao_id`: ID da cotação (real ou fictícia para FOB)
- `transportadora`: Nome da transportadora
- `nf_cd`: Resetado para `False`
- `status`: Calculado automaticamente como "COTADO"

## 🛡️ Validações

- **FOB**: Apenas pedidos com `rota = 'FOB'` podem usar embarque FOB
- **Embarques Ativos**: Só permite inclusão em embarques com `status = 'ativo'`
- **Duplicação**: Verifica se pedido já está em outro embarque ativo

## 🔍 Monitoramento

O sistema agora garante que:
1. Todos os pedidos em embarques ativos tenham status "COTADO"
2. FOB funcione corretamente mesmo sem tabela de frete
3. Inclusões em embarques atualizem o status corretamente
4. Dados históricos possam ser corrigidos via script 