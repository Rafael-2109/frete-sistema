# 📚 IMPORTAÇÃO HISTÓRICA - SISTEMA MOTOCHEFE

## 🎯 VISÃO GERAL

Este documento explica como funciona a importação de dados históricos no sistema MotoChefe, com foco nas **Fases 4, 5, 6 e 7**.

---

## 🔧 MODIFICAÇÕES NA FASE 4

### **O QUE MUDOU?**

A Fase 4 agora suporta **2 MODOS DE OPERAÇÃO**:

| Modo | Quando Usar | Títulos Gerados | Títulos A Pagar |
|------|-------------|-----------------|-----------------|
| **COMPLETO** (padrão) | Pedidos NOVOS via interface web | VENDA + FRETE + MONTAGEM + MOVIMENTACAO | SIM (todos) |
| **HISTORICO** | Importação de pedidos históricos | VENDA + FRETE apenas | NÃO (virão das Fases 5/6/7) |

### **CÓDIGO MODIFICADO:**

**Arquivo**: `app/motochefe/services/importacao_fase4_pedidos.py`

```python
def importar_pedidos_completo(df_pedidos, df_itens, usuario='sistema', modo='COMPLETO'):
    """
    Args:
        modo: 'COMPLETO' (padrão) ou 'HISTORICO'
    """
```

**Comportamento por modo:**

#### **Modo COMPLETO (padrão)**:
- ✅ Gera títulos: MOVIMENTACAO, MONTAGEM, FRETE, VENDA
- ✅ Gera títulos A PAGAR: MOVIMENTACAO, MONTAGEM
- ✅ Lê campos de montagem do Excel

#### **Modo HISTORICO**:
- ✅ Gera títulos: VENDA, FRETE apenas
- ❌ **NÃO** gera títulos de MONTAGEM
- ❌ **NÃO** gera títulos de MOVIMENTACAO
- ❌ **NÃO** gera títulos A PAGAR
- ⚠️ Ignora campos montagem_contratada, valor_montagem, fornecedor_montagem do Excel

---

## 📊 FLUXO COMPLETO DE IMPORTAÇÃO HISTÓRICA

### **SEQUÊNCIA OBRIGATÓRIA:**

```
FASE 1 → FASE 2 → FASE 3 → FASE 4 (modo HISTORICO) → FASE 5 → FASE 6 → FASE 7
```

### **Detalhamento:**

#### **FASE 4: Pedidos (modo HISTORICO)**
```python
ImportacaoFase4Service.importar_pedidos_completo(
    df_pedidos,
    df_itens,
    usuario='sistema',
    modo='HISTORICO'  # ← IMPORTANTE!
)
```

**O que cria:**
- ✅ Pedidos
- ✅ Itens (sem montagem)
- ✅ Títulos A RECEBER: VENDA + FRETE
- ❌ **NÃO cria**: Títulos MONTAGEM/MOVIMENTACAO, Títulos A PAGAR

**Excel necessário:**
- Aba "Pedidos" - Dados do pedido
- Aba "Itens" - Chassi + preco_venda

---

#### **FASE 5: Comissões Históricas**
```python
importar_comissoes_historico(df_comissoes, usuario='sistema')
```

**O que cria:**
- ✅ `ComissaoVendedor` (status PAGO ou PENDENTE)
- ✅ `MovimentacaoFinanceira` PAI + FILHOS (se status=PAGO)
- ✅ Atualiza saldo de empresas

**Excel necessário:**
- Aba "Comissoes"
  - numero_pedido
  - numero_chassi
  - valor_comissao
  - status_pagamento (PAGO/PENDENTE)
  - data_pagamento (se PAGO)
  - empresa_pagadora (se PAGO)

---

#### **FASE 6: Montagens Históricas**
```python
importar_montagens_historico(df_montagens, usuario='sistema')
```

**O que cria:**
- ✅ Atualiza `PedidoVendaMotoItem.montagem_contratada = True`
- ✅ `TituloFinanceiro` tipo=MONTAGEM (A RECEBER)
- ✅ **DEDUZ** valor do `TituloFinanceiro` tipo=VENDA ⚠️ OPÇÃO A
- ✅ `TituloAPagar` tipo=MONTAGEM
- ✅ `MovimentacaoFinanceira` RECEBIMENTO (se status_recebimento=PAGO)
- ✅ `MovimentacaoFinanceira` PAGAMENTO (se status_pagamento=PAGO)
- ✅ Atualiza saldos de empresas

**Excel necessário:**
- Aba "Montagens"
  - numero_pedido
  - numero_chassi
  - fornecedor_montagem
  - valor_cliente (quanto cliente pagou)
  - valor_custo (quanto empresa pagou ao fornecedor)
  - status_recebimento (PAGO/PENDENTE)
  - data_recebimento, empresa_recebedora (se PAGO)
  - status_pagamento (PAGO/PENDENTE)
  - data_pagamento, empresa_pagadora (se PAGO)

---

#### **FASE 7: Movimentações Históricas**
```python
importar_movimentacoes_historico(df_movimentacoes, usuario='sistema')
```

**O que cria:**
- ✅ `TituloFinanceiro` tipo=MOVIMENTACAO (A RECEBER)
- ✅ **DEDUZ** valor do `TituloFinanceiro` tipo=VENDA ⚠️ OPÇÃO A
- ✅ `TituloAPagar` tipo=MOVIMENTACAO → MargemSogima
- ✅ `MovimentacaoFinanceira` RECEBIMENTO (se status_recebimento=PAGO)
- ✅ `MovimentacaoFinanceira` PAGAMENTO (se status_pagamento=PAGO)
- ✅ Atualiza saldos de empresas (origem + destino MargemSogima)

**Excel necessário:**
- Aba "Movimentacoes"
  - numero_pedido
  - numero_chassi
  - valor_cliente (quanto cliente pagou)
  - valor_custo (quanto empresa pagou MargemSogima)
  - status_recebimento (PAGO/PENDENTE)
  - data_recebimento, empresa_recebedora (se PAGO)
  - status_pagamento (PAGO/PENDENTE)
  - data_pagamento, empresa_pagadora (se PAGO)

---

## ⚠️ DEDUÇÃO DO TÍTULO VENDA (OPÇÃO A)

### **Como Funciona:**

```python
# INICIAL (após Fase 4 - modo HISTORICO):
TituloFinanceiro(tipo='VENDA', valor_original=10000, valor_saldo=10000)

# Fase 6 - Montagem (cliente pagou R$ 100):
TituloFinanceiro(tipo='MONTAGEM', valor_original=100, ...)
TituloFinanceiro(tipo='VENDA', valor_original=9900, valor_saldo=9900)  # ← DEDUZIDO

# Fase 7 - Movimentação (cliente pagou R$ 50):
TituloFinanceiro(tipo='MOVIMENTACAO', valor_original=50, ...)
TituloFinanceiro(tipo='VENDA', valor_original=9850, valor_saldo=9850)  # ← DEDUZIDO NOVAMENTE
```

### **Resultado Final:**
- Título VENDA original: R$ 10.000
- Montagem cliente pagou: -R$ 100
- Movimentação cliente pagou: -R$ 50
- **Título VENDA final: R$ 9.850**

---

## 🔧 INTERFACE WEB

### **Acessar:**
```
http://localhost:5000/motochefe/carga-inicial/historico
```

### **Funcionalidades:**
1. ✅ Baixar template Excel (com 3 abas + instruções)
2. ✅ Upload e preview dos dados
3. ✅ Validação automática
4. ✅ Execução das 3 fases em sequência
5. ✅ Relatório detalhado de resultados
6. ✅ Rollback total em caso de erro

---

## 📝 USO PROGRAMÁTICO

### **Importar via Script Python:**

```python
from app import create_app, db
import pandas as pd
from app.motochefe.services.importacao_fase4_pedidos import ImportacaoFase4Service
from app.motochefe.services.importacao_historico_service import (
    importar_comissoes_historico,
    importar_montagens_historico,
    importar_movimentacoes_historico
)

app = create_app()

with app.app_context():
    # FASE 4: Pedidos (modo HISTORICO)
    df_pedidos = pd.read_excel('dados.xlsx', sheet_name='Pedidos')
    df_itens = pd.read_excel('dados.xlsx', sheet_name='Itens')

    resultado_f4 = ImportacaoFase4Service.importar_pedidos_completo(
        df_pedidos,
        df_itens,
        usuario='script',
        modo='HISTORICO'  # ← MODO HISTORICO!
    )

    if not resultado_f4.sucesso:
        print(f"Erro Fase 4: {resultado_f4.mensagem}")
        exit(1)

    # FASE 5: Comissões
    df_comissoes = pd.read_excel('dados.xlsx', sheet_name='Comissoes')
    resultado_f5 = importar_comissoes_historico(df_comissoes, usuario='script')

    if not resultado_f5.sucesso:
        db.session.rollback()
        print(f"Erro Fase 5: {resultado_f5.mensagem}")
        exit(1)

    # FASE 6: Montagens
    df_montagens = pd.read_excel('dados.xlsx', sheet_name='Montagens')
    resultado_f6 = importar_montagens_historico(df_montagens, usuario='script')

    if not resultado_f6.sucesso:
        db.session.rollback()
        print(f"Erro Fase 6: {resultado_f6.mensagem}")
        exit(1)

    # FASE 7: Movimentações
    df_movimentacoes = pd.read_excel('dados.xlsx', sheet_name='Movimentacoes')
    resultado_f7 = importar_movimentacoes_historico(df_movimentacoes, usuario='script')

    if not resultado_f7.sucesso:
        db.session.rollback()
        print(f"Erro Fase 7: {resultado_f7.mensagem}")
        exit(1)

    print("✅ Importação histórica concluída com sucesso!")
```

---

## ✅ VALIDAÇÕES IMPORTANTES

### **Antes de Importar:**
1. ✅ Fazer BACKUP do banco de dados
2. ✅ Validar que Fases 1, 2, 3 foram executadas
3. ✅ Validar que pedidos NÃO existem (ou usar modo UPSERT)
4. ✅ Validar que empresas existem

### **Após Importar:**
1. ✅ Verificar saldos de empresas (`empresa.saldo` == `empresa.saldo_calculado`)
2. ✅ Verificar títulos VENDA deduzidos corretamente
3. ✅ Verificar MovimentacaoFinanceira PAI/FILHOS criadas
4. ✅ Verificar totais de comissões, montagens, movimentações

---

## 🚨 TROUBLESHOOTING

### **Problema: Títulos duplicados de montagem**
**Causa**: Executou Fase 4 em modo COMPLETO e depois Fase 6
**Solução**: Usar modo='HISTORICO' na Fase 4

### **Problema: Título VENDA negativo**
**Causa**: Soma de montagem + movimentação > preco_venda
**Solução**: Revisar valores no Excel

### **Problema: Erro "Pedido não encontrado" na Fase 6**
**Causa**: Fase 4 não foi executada antes
**Solução**: Executar Fase 4 primeiro

### **Problema: Erro "Empresa não encontrada"**
**Causa**: Nome da empresa no Excel difere do cadastrado
**Solução**: Verificar nome exato em EmpresaVendaMoto.empresa

---

## 📚 ARQUIVOS RELACIONADOS

- **Services:**
  - `app/motochefe/services/importacao_fase4_pedidos.py` (modificado)
  - `app/motochefe/services/importacao_historico_service.py` (novo)
  - `app/motochefe/services/titulo_service.py` (modificado)

- **Routes:**
  - `app/motochefe/routes/carga_inicial.py` (adicionadas rotas de histórico)

- **Templates:**
  - `app/templates/motochefe/carga_inicial/historico.html` (novo)

- **Scripts:**
  - `app/motochefe/scripts/importar_historico_completo.py`
  - `app/motochefe/scripts/gerar_template_historico.py`

---

**Última atualização**: {{ data atual }}
**Autor**: Sistema MotoChefe - Importação Histórica
