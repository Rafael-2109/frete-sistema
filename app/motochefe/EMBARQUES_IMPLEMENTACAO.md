# 🚛 IMPLEMENTAÇÃO DE EMBARQUES - SISTEMA MOTOCHEFE

**Data**: 2025-01-04
**Status**: ✅ **COMPLETO**

---

## 📋 RESUMO DA IMPLEMENTAÇÃO

Sistema de agrupamento de pedidos para entrega com rateio proporcional de frete por quantidade de motos.

---

## 🔧 ALTERAÇÕES NO MODELO

### 1. **EmbarquePedido** - NOVO CAMPO

**Arquivo**: [app/motochefe/models/logistica.py:93](app/motochefe/models/logistica.py#L93)

```python
# Status de envio (trigger para rateio e atualização do pedido)
enviado = db.Column(db.Boolean, default=False, nullable=False, index=True)
```

**⚠️ MIGRAÇÃO SQL OBRIGATÓRIA**:
```bash
# Executar no PostgreSQL do Render:
psql -f app/motochefe/scripts/add_enviado_embarque_pedido.sql
```

---

## 🎯 FLUXO COMPLETO DO SISTEMA

### 1. **Criar Embarque Vazio**
```
Rota: /motochefe/embarques/adicionar
- Número gerado automaticamente: EMB-001, EMB-002...
- Selecionar transportadora
- Definir valor_frete_contratado
- Status inicial: PLANEJADO
```

### 2. **Adicionar Pedidos ao Embarque**
```
Rota: /motochefe/embarques/<id>/adicionar-pedido
- Mostrar TODOS os pedidos (sem filtro de faturado)
- Permitir adicionar MESMO pedido em múltiplos embarques
- Cria EmbarquePedido com enviado=False
- qtd_motos_pedido = pedido.quantidade_motos
```

### 3. **Marcar Pedido como Enviado** (TRIGGER)
```
Rota: /motochefe/embarques/<id>/marcar-enviado/<ep_id>
- Marcar EmbarquePedido.enviado = True
- TRIGGER 1: Chama calcular_rateio()
  - Fórmula: (valor_frete_contratado / total_motos) * qtd_motos_pedido
- TRIGGER 2: Marca PedidoVendaMoto.enviado = True
```

### 4. **Desmarcar Enviado** (REVERSÃO)
```
- Marcar EmbarquePedido.enviado = False
- Zerar valor_frete_rateado
- REVERTER PedidoVendaMoto.enviado = False
```

### 5. **Remover Pedido do Embarque** (REVERSÃO)
```
Rota: /motochefe/embarques/<id>/remover-pedido/<ep_id>
- Se ep.enviado == True: Reverter PedidoVendaMoto.enviado = False
- Deletar EmbarquePedido
```

### 6. **Pagar Frete** (MODAL)
```
Rota: /motochefe/embarques/<id>/pagar-frete
- Preencher valor_frete_pago
- Preencher data_pagamento_frete
- Alterar status_pagamento_frete = 'PAGO'
```

---

## 📁 ARQUIVOS CRIADOS/MODIFICADOS

### MODIFICADOS:
1. ✅ `app/motochefe/models/logistica.py` (linha 93)
   - Adicionado campo `enviado`

2. ✅ `app/motochefe/routes/__init__.py` (linha 11)
   - Importado módulo `logistica`

### CRIADOS:
3. ✅ `app/motochefe/routes/logistica.py` (290 linhas)
   - 8 rotas completas

4. ✅ `app/templates/motochefe/logistica/embarques/listar.html`
   - Listagem com filtros e badges de status

5. ✅ `app/templates/motochefe/logistica/embarques/form.html` (270 linhas)
   - Form completo com tabela de pedidos
   - Checkbox para marcar enviado
   - Modal de pagamento de frete
   - Info card com instruções

6. ✅ `app/motochefe/scripts/add_enviado_embarque_pedido.sql`
   - Script de migração SQL

---

## 🔑 ROTAS IMPLEMENTADAS

| Rota | Método | Função |
|------|--------|--------|
| `/embarques` | GET | `listar_embarques()` |
| `/embarques/adicionar` | GET/POST | `adicionar_embarque()` |
| `/embarques/<id>/editar` | GET/POST | `editar_embarque()` |
| `/embarques/<id>/remover` | POST | `remover_embarque()` |
| `/embarques/<id>/adicionar-pedido` | POST | `adicionar_pedido_embarque()` |
| `/embarques/<id>/remover-pedido/<ep_id>` | POST | `remover_pedido_embarque()` |
| `/embarques/<id>/marcar-enviado/<ep_id>` | POST | `marcar_pedido_enviado()` |
| `/embarques/<id>/pagar-frete` | POST | `pagar_frete_embarque()` |

---

## 💡 LÓGICA DE NEGÓCIO

### Geração de Número de Embarque
```python
def gerar_numero_embarque():
    ultimo = EmbarqueMoto.query.order_by(EmbarqueMoto.id.desc()).first()
    if not ultimo:
        return 'EMB-001'
    numero = int(ultimo.numero_embarque.replace('EMB-', ''))
    return f'EMB-{(numero + 1):03d}'
```

### Cálculo de Rateio
```python
# Método existente em EmbarquePedido.calcular_rateio()
valor_frete_rateado = (
    embarque.valor_frete_contratado / embarque.total_motos
) * self.qtd_motos_pedido
```

### Trigger ao Marcar Enviado
```python
if novo_valor:  # Marcar True
    ep.enviado = True
    ep.calcular_rateio()  # Trigger 1
    ep.pedido.enviado = True  # Trigger 2
else:  # Desmarcar
    ep.enviado = False
    ep.valor_frete_rateado = 0
    ep.pedido.enviado = False  # Reversão
```

---

## ✅ REGRAS IMPLEMENTADAS

1. ✅ **Número Automático**: EMB-001, EMB-002 (sequencial)
2. ✅ **Criar Vazio**: Form inicial sem pedidos
3. ✅ **Todos Pedidos**: Sem filtro (mostra faturados e não faturados)
4. ✅ **Campo Enviado**: Trigger de rateio + atualização do pedido
5. ✅ **Reversão ao Desmarcar**: PedidoVendaMoto.enviado volta para False
6. ✅ **Reversão ao Remover**: Se estava enviado, reverte
7. ✅ **Permitir Duplicatas**: Mesmo pedido em múltiplos embarques
8. ✅ **Modal Pagamento**: Separado do form principal

---

## 🎨 INTERFACE DO USUÁRIO

### Template Listar (listar.html)
- ✅ Filtro por status
- ✅ Badges coloridos (PLANEJADO, EM_TRANSITO, ENTREGUE, CANCELADO)
- ✅ Colunas: Número, Transportadora, Data, Pedidos, Motos, Frete, Status
- ✅ Botões Editar e Remover

### Template Form (form.html)
- ✅ Seção: Dados do Embarque
- ✅ Seção: Gerenciamento de Pedidos
- ✅ Select com TODOS os pedidos
- ✅ Tabela com checkbox "Enviado" por linha
- ✅ Linha verde quando enviado=True
- ✅ Coluna rateio (só mostra se enviado)
- ✅ Total de motos no footer
- ✅ Modal para pagar frete
- ✅ Card de instruções

---

## 📊 EXEMPLO DE USO

### Cenário Completo:

1. **Criar Embarque**:
   ```
   Número: EMB-001 (auto)
   Transportadora: JadLog
   Valor Frete Contratado: R$ 1.000,00
   Status: PLANEJADO
   ```

2. **Adicionar 3 Pedidos**:
   ```
   Pedido P-001: 5 motos → enviado=False
   Pedido P-002: 3 motos → enviado=False
   Pedido P-003: 2 motos → enviado=False
   Total: 10 motos
   ```

3. **Marcar P-001 como Enviado**:
   ```
   TRIGGER:
   - calcular_rateio():
     (1.000 / 10) * 5 = R$ 500,00
   - P-001.enviado = True ✅
   ```

4. **Marcar P-002 como Enviado**:
   ```
   TRIGGER:
   - calcular_rateio():
     (1.000 / 10) * 3 = R$ 300,00
   - P-002.enviado = True ✅
   ```

5. **Pagar Frete**:
   ```
   Valor Pago: R$ 980,00
   Data: 04/01/2025
   Status: PAGO ✅
   ```

---

## ⚠️ IMPORTANTE - ANTES DE USAR

### 1. **EXECUTAR MIGRAÇÃO SQL**:
```bash
# No shell do Render PostgreSQL:
\i app/motochefe/scripts/add_enviado_embarque_pedido.sql

# Ou diretamente:
ALTER TABLE embarque_pedido ADD COLUMN enviado BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX idx_embarque_pedido_enviado ON embarque_pedido(enviado);
```

### 2. **VERIFICAR IMPORT**:
```python
# Em app/motochefe/routes/__init__.py deve ter:
from . import cadastros, produtos, operacional, logistica
```

### 3. **REINICIAR SERVIDOR FLASK**:
```bash
# Para carregar novos módulos
```

---

## 🧪 CHECKLIST DE VALIDAÇÃO

- [ ] Executar SQL de migração
- [ ] Reiniciar servidor Flask
- [ ] Criar embarque vazio → Deve gerar EMB-001
- [ ] Adicionar pedido ao embarque → Deve aparecer na tabela
- [ ] Marcar pedido como enviado → Deve calcular rateio e marcar pedido original
- [ ] Desmarcar enviado → Deve reverter pedido e zerar rateio
- [ ] Remover pedido do embarque → Deve reverter se estava enviado
- [ ] Adicionar mesmo pedido em 2 embarques → Deve permitir
- [ ] Pagar frete → Deve atualizar status para PAGO
- [ ] Filtrar por status → Deve funcionar

---

## 📖 DOCUMENTAÇÃO RELACIONADA

- **Modelos**: [app/motochefe/models/logistica.py](app/motochefe/models/logistica.py)
- **Rotas**: [app/motochefe/routes/logistica.py](app/motochefe/routes/logistica.py)
- **Doc Técnica Vendas**: [app/motochefe/doc_tecnica.md](app/motochefe/doc_tecnica.md)

---

## 🎉 CONCLUSÃO

**Sistema de Embarques está 100% implementado e pronto para uso.**

Funcionalidades:
- ✅ CRUD completo de embarques
- ✅ Geração automática de números
- ✅ Gerenciamento de pedidos
- ✅ Trigger de rateio ao marcar enviado
- ✅ Reversão completa ao desmarcar/remover
- ✅ Suporte a duplicatas
- ✅ Pagamento de frete via modal

**Próximo passo**: Executar migração SQL e testar.

---

**Desenvolvido com**: Flask, SQLAlchemy, Bootstrap 5
**Data de Conclusão**: 04/01/2025
