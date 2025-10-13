# 🔧 Implementação: Ajustes em Movimentação, Devolução e Montagem

**Data**: 12/10/2025
**Módulo**: `app/motochefe`

---

## 📋 RESUMO DAS ALTERAÇÕES

### ✅ TAREFA 1: Títulos de Movimentação com valor = 0

**Problema**: Quando `incluir_custo_movimentacao=False`, sistema gerava TituloFinanceiro MOVIMENTACAO com valor=0, mas ainda criava TituloAPagar com custo real.

**Solução Implementada**:
1. **TituloFinanceiro MOVIMENTACAO**: Continua sendo criado (mesmo com R$ 0), mas será ocultado nas telas
2. **TituloAPagar MOVIMENTACAO**:
   - Sempre criado com custo real (de `EquipeVendasMoto.custo_movimentacao`)
   - Status inicial: `PENDENTE`
   - **LIBERAÇÃO AUTOMÁTICA**: Ao quitar TituloFinanceiro VENDA da moto, TituloAPagar de MOVIMENTACAO é automaticamente liberado (status → `ABERTO`)

**Arquivos Alterados**:
- [app/motochefe/services/titulo_a_pagar_service.py](app/motochefe/services/titulo_a_pagar_service.py:137-185)
  - Nova função: `quitar_titulo_movimentacao_ao_pagar_moto()`
- [app/motochefe/services/titulo_service.py](app/motochefe/services/titulo_service.py:306-312)
  - Trigger adicionado ao pagar título VENDA
- [app/motochefe/services/titulo_service.py](app/motochefe/services/titulo_service.py:508-516)
  - Trigger adicionado no recebimento individual

---

### ✅ TAREFA 2: Devolução de Motos com Recebimento Automático

**Problema**: Devoluções não geravam movimentação financeira, não havia empresa "DevolucaoMoto" e não havia lógica de recebimento em lote.

**Solução Implementada**:
1. **Campo novo**: `CustosOperacionais.custo_movimentacao_devolucao`
   - Custo cobrado do fabricante por moto devolvida
2. **Empresa DevolucaoMoto**:
   - Criada automaticamente se não existir
   - `tipo_conta='OPERACIONAL'`
   - Recebe automaticamente os valores de devolução
3. **Recebimento Automático**:
   - Gera TituloFinanceiro (tipo='DEVOLUCAO', status='PAGO')
   - Origem: `Moto.fornecedor`
   - Gera MovimentacaoFinanceira automaticamente
   - **Se >1 moto**: Usa lote (PAI + FILHOS)
   - Atualiza saldo de DevolucaoMoto

**Arquivos Alterados**:
- [app/motochefe/models/operacional.py](app/motochefe/models/operacional.py:24-25)
  - Novo campo: `custo_movimentacao_devolucao`
- [app/motochefe/services/devolucao_service.py](app/motochefe/services/devolucao_service.py:153-316)
  - Nova função: `processar_recebimento_devolucao()`

**Scripts de Migração**:
- Python: [app/motochefe/scripts/add_custo_movimentacao_devolucao.py](app/motochefe/scripts/add_custo_movimentacao_devolucao.py)
- SQL: [app/motochefe/scripts/add_custo_movimentacao_devolucao.sql](app/motochefe/scripts/add_custo_movimentacao_devolucao.sql)

---

### ✅ TAREFA 3: Pagamento de Montagens em Lote com Parcial

**Problema**: Tela "Contas a Pagar" pagava montagens individualmente, sem usar estrutura de lote e sem suporte a pagamento parcial proporcional.

**Solução Implementada**:
- Refatorado para usar `processar_pagamento_lote_montagens()`
- Converte `TituloAPagar.id` → `PedidoVendaMotoItem.id`
- Usa estrutura PAI + FILHOS
- **Suporte a pagamento parcial**: Já existe em `processar_pagamento_lote_montagens()` via parâmetro `valor_limite`

**Arquivos Alterados**:
- [app/motochefe/routes/financeiro.py](app/motochefe/routes/financeiro.py:336-364)
  - Refatorado bloco de pagamento de montagens

---

## 🚀 COMO USAR

### 1️⃣ Executar Migration Local

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python app/motochefe/scripts/add_custo_movimentacao_devolucao.py
```

### 2️⃣ Executar Migration no Render

```sql
-- Conectar ao Shell do Render e executar:
ALTER TABLE custos_operacionais
ADD COLUMN IF NOT EXISTS custo_movimentacao_devolucao NUMERIC(15, 2) NOT NULL DEFAULT 0;

-- Configurar valor (exemplo: R$ 50)
UPDATE custos_operacionais
SET custo_movimentacao_devolucao = 50.00
WHERE ativo = TRUE AND data_vigencia_fim IS NULL;
```

### 3️⃣ Configurar Custo de Devolução

Acessar tela de CustosOperacionais e configurar `custo_movimentacao_devolucao` (exemplo: R$ 50,00)

### 4️⃣ Processar Devolução com Recebimento

```python
from app.motochefe.services.devolucao_service import processar_recebimento_devolucao

# Após devolver motos (status=DEVOLVIDO), processar recebimento:
resultado = processar_recebimento_devolucao(
    documento_devolucao='DEV-001',
    usuario='Nome Usuário'
)

# Retorna:
# - empresa_devolucao: EmpresaVendaMoto
# - titulos_criados: list[TituloFinanceiro]
# - movimentacoes_criadas: list[MovimentacaoFinanceira]
# - valor_total: Decimal
# - quantidade_motos: int
```

---

## 📊 FLUXOS IMPLEMENTADOS

### Fluxo 1: Pedido sem Custo de Movimentação

```
1. Cliente cria pedido (incluir_custo_movimentacao=False)
2. TituloFinanceiro MOVIMENTACAO criado com R$ 0 (oculto)
3. TituloAPagar MOVIMENTACAO criado com R$ 50 (status=PENDENTE)
4. Cliente paga TituloFinanceiro VENDA
5. ✨ TituloAPagar MOVIMENTACAO automaticamente liberado (status=ABERTO)
6. Empresa pode pagar MargemSogima via Contas a Pagar
```

### Fluxo 2: Devolução de Motos

```
1. Moto avariada → status=AVARIADO
2. Devolver moto → status=DEVOLVIDO, documento_devolucao='DEV-001'
3. Processar recebimento:
   - Cria/busca EmpresaVendaMoto "DevolucaoMoto"
   - Gera TituloFinanceiro (tipo=DEVOLUCAO, status=PAGO)
   - Gera MovimentacaoFinanceira (origem=Moto.fornecedor, destino=DevolucaoMoto)
   - Se >1 moto: PAI + FILHOS
   - Atualiza saldo DevolucaoMoto
4. Saldo disponível para pagar títulos via DevolucaoMoto
```

### Fluxo 3: Pagamento de Montagens em Lote

```
1. Acessar Contas a Pagar
2. Selecionar múltiplas montagens
3. Selecionar empresa pagadora
4. Clicar "Pagar"
5. Sistema:
   - Converte TituloAPagar → PedidoVendaMotoItem
   - Chama processar_pagamento_lote_montagens()
   - Cria MovimentacaoFinanceira PAI + FILHOS
   - Atualiza TituloAPagar → PAGO
   - Sincroniza PedidoVendaMotoItem.montagem_paga
   - Atualiza saldo empresa
```

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **TituloFinanceiro MOVIMENTACAO com R$ 0**:
   - Não deve ser exibido em telas de recebimento
   - Adicionar filtro `WHERE valor_original > 0` nas queries de exibição

2. **EmpresaVendaMoto "DevolucaoMoto"**:
   - Criada automaticamente na primeira devolução processada
   - Pode ser usada para pagar outros títulos (como movimentação de devolução cobrada do fabricante)

3. **Pagamento Parcial de Montagens**:
   - Já suportado por `processar_pagamento_lote_montagens()`
   - Adicionar campo de "valor limite" na interface se necessário

4. **Sincronização TituloAPagar ↔ PedidoVendaMotoItem**:
   - Ao pagar montagem via lote, ambos são atualizados
   - `TituloAPagar.status = 'PAGO'`
   - `PedidoVendaMotoItem.montagem_paga = True`

---

## 🧪 TESTES RECOMENDADOS

### Teste 1: Movimentação R$ 0
1. Criar pedido com `incluir_custo_movimentacao=False`
2. Verificar TituloAPagar criado (status=PENDENTE)
3. Pagar TituloFinanceiro VENDA completamente
4. Verificar TituloAPagar liberado (status=ABERTO)

### Teste 2: Devolução Individual
1. Marcar moto como AVARIADO
2. Devolver moto (status=DEVOLVIDO, doc='DEV-001')
3. Chamar `processar_recebimento_devolucao('DEV-001')`
4. Verificar TituloFinanceiro, MovimentacaoFinanceira e saldo DevolucaoMoto

### Teste 3: Devolução em Lote (>1 moto)
1. Devolver 3 motos no mesmo documento
2. Processar recebimento
3. Verificar MovimentacaoFinanceira PAI + 3 FILHOS

### Teste 4: Montagens em Lote
1. Selecionar 5 montagens em Contas a Pagar
2. Pagar via lote
3. Verificar PAI + FILHOS criados
4. Verificar TituloAPagar e PedidoVendaMotoItem sincronizados

---

## 📁 ARQUIVOS MODIFICADOS

### Models
- `app/motochefe/models/operacional.py` - Campo `custo_movimentacao_devolucao`

### Services
- `app/motochefe/services/titulo_service.py` - Trigger para liberar TituloAPagar
- `app/motochefe/services/titulo_a_pagar_service.py` - Função `quitar_titulo_movimentacao_ao_pagar_moto()`
- `app/motochefe/services/devolucao_service.py` - Função `processar_recebimento_devolucao()`

### Routes
- `app/motochefe/routes/financeiro.py` - Refatoração pagamento montagens

### Scripts
- `app/motochefe/scripts/add_custo_movimentacao_devolucao.py` - Migration Python
- `app/motochefe/scripts/add_custo_movimentacao_devolucao.sql` - Migration SQL

---

## ✅ CHECKLIST DE DEPLOY

- [ ] Executar migration local
- [ ] Executar migration no Render
- [ ] Configurar `custo_movimentacao_devolucao` em CustosOperacionais
- [ ] Testar pedido sem custo de movimentação
- [ ] Testar devolução individual
- [ ] Testar devolução em lote
- [ ] Testar pagamento de montagens em lote
- [ ] Verificar saldos das empresas após operações
- [ ] Verificar MovimentacoesFinanceiras PAI + FILHOS corretas
