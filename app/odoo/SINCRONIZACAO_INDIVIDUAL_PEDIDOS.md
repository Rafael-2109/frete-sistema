# 🔄 Sincronização Individual de Pedidos - Documentação

## 📋 Visão Geral

Funcionalidade implementada em `/odoo/sync-integrada/` que permite sincronizar pedidos individuais com o Odoo de forma manual.

**Localização**: `/odoo/sync-integrada/`
**Implementado em**: 2025-01-20

---

## 🎯 Funcionalidades

### 1. Listagem de Pedidos com Saldo

- ✅ Mostra pedidos com `sincronizado_nf=False` e `qtd_saldo > 0`
- ✅ Exibe informações relevantes: cliente, cidade, status, valores
- ✅ Limitado a 100 pedidos mais recentes para performance
- ✅ Ordenação por número de pedido (decrescente)

### 2. Sincronização Individual

Cada pedido tem um botão **"Sincronizar"** que:

#### ✅ Se pedido ENCONTRADO no Odoo:
- Atualiza quantidades conforme Odoo
- Mantém separações existentes
- Aplica alterações via `AjusteSincronizacaoService`
- Recalcula peso e pallets automaticamente

#### ❌ Se pedido NÃO ENCONTRADO no Odoo:
- **EXCLUI completamente** o pedido do sistema
- Remove **TODAS** as `Separacao` (incluindo `sincronizado_nf=False`)
- Cancela `EmbarqueItem` relacionados
- Remove registros de `CarteiraPrincipal`
- **Ação IRREVERSÍVEL**

---

## 🛠️ Arquivos Modificados/Criados

### 1. Backend - Rotas
**Arquivo**: [app/odoo/routes/sincronizacao_integrada.py](app/odoo/routes/sincronizacao_integrada.py)

```python
# Nova função helper (linhas 60-97)
def obter_pedidos_com_saldo():
    """Busca pedidos com saldo > 0 e sincronizado_nf=False"""

# Nova rota (linhas 263-313)
@sync_integrada_bp.route('/sincronizar-pedido/<string:num_pedido>', methods=['POST'])
def sincronizar_pedido_individual(num_pedido):
    """Sincroniza um pedido específico"""
```

**Alterações**:
- ✅ Adicionado import de `PedidoSyncService`
- ✅ Adicionado import de `Separacao` e `func` do SQLAlchemy
- ✅ Modificado `dashboard()` para incluir lista de pedidos
- ✅ Criado `obter_pedidos_com_saldo()`
- ✅ Criado `sincronizar_pedido_individual()`

### 2. Frontend - Template HTML
**Arquivo**: [app/templates/odoo/sync_integrada/dashboard.html](app/templates/odoo/sync_integrada/dashboard.html)

```html
<!-- Nova seção (linhas 155-240) -->
<div class="card">
    <div class="card-header bg-primary text-white">
        <h5><i class="fas fa-sync-alt"></i> Sincronizar Pedido Individual</h5>
    </div>
    <div class="card-body">
        <!-- Tabela de pedidos com botão Sincronizar -->
    </div>
</div>

<!-- Nova função JavaScript (linhas 318-338) -->
function confirmarSincPedido(numPedido) {
    // Confirmação com explicação detalhada
}
```

**Alterações**:
- ✅ Adicionada seção de sincronização individual ANTES do botão "Sincronizar Tudo"
- ✅ Tabela com 9 colunas: Pedido, Cliente, Cidade/UF, Status, Qtd, Valor, Itens, Expedição, Ação
- ✅ Botão "Sincronizar" em cada linha
- ✅ Função JavaScript de confirmação com alertas detalhados
- ✅ Badge com contador de pedidos

### 3. Serviço Backend (Já existia)
**Arquivo**: [app/odoo/services/pedido_sync_service.py](app/odoo/services/pedido_sync_service.py)

**Usado**: Classe `PedidoSyncService` criada anteriormente
- Método: `sincronizar_pedido_especifico(num_pedido)`

### 4. Serviço de Exclusão (Já existia)
**Arquivo**: [app/odoo/services/carteira_service.py](app/odoo/services/carteira_service.py)

**Usado**: `CarteiraService._processar_cancelamento_pedido()`
- Linhas 116-118: Exclui **TODAS** as `Separacao` do pedido

---

## 📊 Estrutura da Tabela

| Coluna | Descrição | Origem |
|--------|-----------|--------|
| **Pedido** | Número do pedido | `Separacao.num_pedido` |
| **Cliente** | Razão social (30 chars) | `Separacao.raz_social_red` |
| **Cidade/UF** | Localização | `Separacao.nome_cidade` / `cod_uf` |
| **Status** | Status atual (badge colorido) | `Separacao.status` |
| **Qtd Total** | Soma das quantidades | `SUM(Separacao.qtd_saldo)` |
| **Valor** | Soma dos valores | `SUM(Separacao.valor_saldo)` |
| **Itens** | Contagem de produtos | `COUNT(Separacao.cod_produto)` |
| **Expedição** | Data de expedição | `MAX(Separacao.expedicao)` |
| **Ação** | Botão Sincronizar | Form POST |

---

## 🔍 Query SQL Executada

```python
pedidos = db.session.query(
    Separacao.num_pedido,
    Separacao.raz_social_red,
    Separacao.nome_cidade,
    Separacao.cod_uf,
    Separacao.status,
    func.sum(Separacao.qtd_saldo).label('qtd_total'),
    func.sum(Separacao.valor_saldo).label('valor_total'),
    func.count(Separacao.cod_produto).label('total_itens'),
    func.max(Separacao.expedicao).label('data_expedicao')
).filter(
    Separacao.sincronizado_nf == False,  # Apenas não sincronizados
    Separacao.qtd_saldo > 0               # Apenas com saldo
).group_by(
    Separacao.num_pedido,
    Separacao.raz_social_red,
    Separacao.nome_cidade,
    Separacao.cod_uf,
    Separacao.status
).order_by(
    Separacao.num_pedido.desc()           # Mais recentes primeiro
).limit(100).all()                        # Máximo 100 pedidos
```

---

## 🎨 Interface do Usuário

### Layout da Tela

```
┌─────────────────────────────────────────────────────┐
│ 🔄 Sincronização Integrada Segura                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│ [Seção de Status do Sistema]                        │
│                                                      │
│ [Botão SINCRONIZAR TUDO (SEGURO)]                   │
│                                                      │
├─────────────────────────────────────────────────────┤
│ 🔄 Sincronizar Pedido Individual    [100 pedidos]  │
├─────────────────────────────────────────────────────┤
│ ℹ️ Como funciona:                                    │
│ • Se encontrado: Atualiza                           │
│ • Se não encontrado: Exclui tudo                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│ ┌────────────────────────────────────────────────┐ │
│ │ Pedido │ Cliente │ Cidade │ ... │ Sincronizar │ │
│ ├────────────────────────────────────────────────┤ │
│ │ VSC001 │ ACME... │ SP/SP  │ ... │   [Botão]   │ │
│ │ VSC002 │ XYZ...  │ RJ/RJ  │ ... │   [Botão]   │ │
│ └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Badges de Status

- **COTADO**: Badge amarelo (`bg-warning`)
- **ABERTO**: Badge verde (`bg-success`)
- **PREVISAO**: Badge cinza (`bg-secondary`)
- **Outros**: Badge azul (`bg-info`)

---

## ⚡ Fluxo de Execução

### 1. Usuário acessa `/odoo/sync-integrada/`
```
GET /odoo/sync-integrada/
  ↓
dashboard() executa
  ↓
verificar_status_sincronizacao()
obter_pedidos_com_saldo()
  ↓
Renderiza template com dados
```

### 2. Usuário clica em "Sincronizar" de um pedido
```
Clique no botão
  ↓
confirmarSincPedido() mostra alerta
  ↓
Usuário confirma
  ↓
POST /odoo/sync-integrada/sincronizar-pedido/VSC12345
  ↓
sincronizar_pedido_individual() executa
  ↓
PedidoSyncService.sincronizar_pedido_especifico()
  ↓
Busca pedido no Odoo
  ├─ Encontrado → Atualiza (AjusteSincronizacaoService)
  └─ Não encontrado → Exclui (CarteiraService._processar_cancelamento_pedido)
  ↓
Flash messages com resultado
  ↓
Redirect para dashboard
```

---

## 🛡️ Proteções e Validações

### 1. Confirmação JavaScript
```javascript
function confirmarSincPedido(numPedido) {
    // Mostra alert detalhado sobre as consequências
    // Retorna true/false baseado na confirmação do usuário
}
```

### 2. Validação Backend
- Verifica se pedido existe antes de processar
- Try/catch em todas as operações
- Logging detalhado de todas as ações

### 3. Exclusão Segura
```python
# Em CarteiraService._processar_cancelamento_pedido()

# Exclui TODAS as Separacao (incluindo sincronizado_nf=False)
separacoes_excluidas = Separacao.query.filter_by(
    num_pedido=num_pedido
).delete(synchronize_session=False)
```

**Garante**: Quando pedido não existe no Odoo, TUDO é removido do sistema.

---

## 📝 Mensagens de Feedback

### Sucesso - Pedido Atualizado
```
✅ Pedido VSC12345 atualizado conforme dados do Odoo (1.23s)
📦 5 itens processados
🔄 3 alterações aplicadas
```

### Sucesso - Pedido Excluído
```
🗑️ Pedido VSC12345 excluído completamente do sistema (não encontrado no Odoo) (0.87s)
✅ Todas as Separacao (sincronizado_nf=False) foram excluídas
```

### Erro
```
❌ Erro ao sincronizar pedido: Conexão com Odoo indisponível
```

---

## 🧪 Casos de Teste

### Teste 1: Pedido Existe no Odoo
1. Acessar `/odoo/sync-integrada/`
2. Localizar pedido VSC12345 na lista
3. Clicar em "Sincronizar"
4. Confirmar no alerta
5. **Resultado esperado**: Pedido atualizado, quantidades ajustadas

### Teste 2: Pedido NÃO Existe no Odoo
1. Acessar `/odoo/sync-integrada/`
2. Localizar pedido VSC99999 na lista
3. Clicar em "Sincronizar"
4. Confirmar no alerta
5. **Resultado esperado**: Pedido excluído completamente, desaparece da lista

### Teste 3: Pedido com Status COTADO
1. Acessar `/odoo/sync-integrada/`
2. Localizar pedido com status COTADO
3. Clicar em "Sincronizar"
4. **Resultado esperado**: Alerta gerado se houver alterações

---

## 🔧 Configurações e Limites

| Configuração | Valor | Motivo |
|--------------|-------|--------|
| **Máximo de pedidos** | 100 | Performance da interface |
| **Timeout sincronização** | 30s (herdado) | Evitar travamento |
| **Ordenação** | Decrescente | Mais recentes primeiro |
| **Filtro obrigatório** | `sincronizado_nf=False` | Apenas pendentes |

---

## 📚 Referências

### Arquivos Relacionados
- [app/odoo/services/pedido_sync_service.py](app/odoo/services/pedido_sync_service.py) - Serviço de sincronização
- [app/odoo/services/carteira_service.py](app/odoo/services/carteira_service.py:65-158) - Função de exclusão
- [app/odoo/services/ajuste_sincronizacao_service.py](app/odoo/services/ajuste_sincronizacao_service.py) - Serviço de ajuste
- [app/odoo/routes/sincronizacao_integrada.py](app/odoo/routes/sincronizacao_integrada.py) - Rotas
- [app/templates/odoo/sync_integrada/dashboard.html](app/templates/odoo/sync_integrada/dashboard.html) - Template

### Documentação Adicional
- [PEDIDO_SYNC_API.md](PEDIDO_SYNC_API.md) - API REST para sincronização programática
- [CLAUDE.md](../../CLAUDE.md) - Referência de modelos e campos

---

## ⚠️ Avisos Importantes

### 1. Exclusão é Irreversível
Quando um pedido não é encontrado no Odoo, **TUDO** é excluído:
- ❌ `Separacao` (todas, incluindo `sincronizado_nf=False`)
- ❌ `CarteiraPrincipal`
- ❌ `EmbarqueItem` (marcados como cancelados)
- ❌ `PreSeparacaoItem` (se existir)

**Não há como recuperar** sem backup.

### 2. Limite de 100 Pedidos
A interface mostra apenas os 100 pedidos mais recentes. Para processar todos os pedidos, use o botão **"SINCRONIZAR TUDO (SEGURO)"**.

### 3. Performance
Para grandes volumes (>100 pedidos), use a sincronização completa ao invés de sincronizar individualmente.

---

## 💡 Dicas de Uso

1. **Use para correções pontuais**: Quando um pedido específico precisa ser ressincronizado
2. **Não abuse**: Para sincronizações em massa, use o botão "Sincronizar Tudo"
3. **Verifique antes**: Sempre confira os dados antes de sincronizar
4. **Monitore logs**: Acompanhe os logs para detectar problemas

---

**Última atualização**: 2025-01-20
**Versão**: 1.0.0
**Autor**: Sistema de Fretes
