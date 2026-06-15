<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Verificacao de pedidos EXCLUIDOS do Odoo no scheduler de sincronizacao (deteccao + exclusao em lote)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🔍 Verificação de Pedidos Excluídos do Odoo

> **Papel:** explicar como o scheduler de sincronização detecta pedidos EXCLUÍDOS (deletados) no Odoo e processa sua exclusão completa no sistema de fretes.

## Contexto

Documento de design da funcionalidade `verificar_pedidos_excluidos_odoo()`: o scheduler tratava pedidos CANCELADOS no Odoo, mas não detectava pedidos EXCLUÍDOS (deletados). Este doc descreve a solução implementada, sua integração ao scheduler e o comportamento de exclusão.

**Data de Implementação:** 2025-01-04
**Versão:** 1.0.0
**Status:** ✅ Implementado e Ativo

## Indice

- [Problema Identificado](#problema-identificado)
- [Solução Implementada](#solução-implementada)
- [Performance Estimada](#performance-estimada)
- [Integração com Scheduler](#integração-com-scheduler)
- [Comportamento Detalhado](#comportamento-detalhado)
- [Estatísticas e Monitoramento](#estatísticas-e-monitoramento)
- [Segurança e Validações](#segurança-e-validações)
- [Impacto no Scheduler](#impacto-no-scheduler)
- [Configuração](#configuração)
- [Checklist de Implementação](#checklist-de-implementação)
- [Próximos Passos](#próximos-passos-opcional)
- [Suporte](#suporte)

---

## Problema Identificado

O scheduler de sincronização automática detectava e tratava **pedidos CANCELADOS** no Odoo, mas **NÃO detectava pedidos EXCLUÍDOS** (deletados completamente).

#### Diferenças entre Sincronização Manual vs Automática

| Cenário | Sincronização Manual (`/odoo/sync-integrada/pedidos`) | Sincronização Automática (Scheduler) |
|---------|------------------------------------------------------|-------------------------------------|
| **Pedido CANCELADO** | ✅ Detecta e exclui | ✅ Detecta e exclui |
| **Pedido EXCLUÍDO** | ✅ Detecta e exclui | ❌ **NÃO detectava** |
| **Modo de detecção** | Busca direta por pedido | Incremental por `write_date` |

---

## Solução Implementada

### Nova Funcionalidade: `verificar_pedidos_excluidos_odoo()`

**Arquivo:** `app/odoo/services/carteira_service.py` (função inicia na linha 170; a linha 161 ainda faz parte do método anterior `_processar_cancelamento_pedido`, que termina na linha 168)

**Características:**

1. ✅ **Query única** para pegar pedidos pendentes com `qtd_saldo_produto_pedido > 0`
2. ✅ **Filtra apenas pedidos do Odoo** (VSC, VCD, VFB)
3. ✅ **Busca em LOTE no Odoo** (100 pedidos por vez) - MUITO MAIS RÁPIDO
4. ✅ **Exclui automaticamente** os que não foram encontrados ou estão cancelados

---

## Performance Estimada

| Cenário | Pedidos Pendentes | Tempo Estimado |
|---------|-------------------|----------------|
| **Pequeno** | ~50 pedidos | **~1-2 segundos** |
| **Médio** | ~200 pedidos | **~3-5 segundos** |
| **Grande** | ~500 pedidos | **~8-12 segundos** |
| **Muito Grande** | ~1000 pedidos | **~15-20 segundos** |

### Otimizações Implementadas

- **Busca em lote:** Ao invés de 1 query por pedido, busca 100 de uma vez
- **Campos mínimos:** Retorna apenas `name` e `state` do Odoo
- **Filtro prévio:** Busca apenas pedidos com saldo > 0
- **Tratamento de erros:** Continua processamento mesmo se um lote falhar

---

## Integração com Scheduler

**Arquivo:** `app/scheduler/sincronizacao_incremental_definitiva.py`

### Ordem de Execução (a cada 30 minutos)

```
1️⃣ Faturamento (STATUS_FATURAMENTO = 5760 min / 96h)
2️⃣ Carteira (JANELA_CARTEIRA = 40 min)
2.5️⃣ Verificação de Pedidos Excluídos ← 🆕 NOVO
3️⃣ Requisições (JANELA_REQUISICOES = 90 min)
4️⃣ Pedidos de Compra (JANELA_PEDIDOS = 90 min)
5️⃣ Alocações (JANELA_ALOCACOES = 90 min)
```

### Log de Execução

```
🔍 Verificando pedidos excluídos do Odoo (tentativa 1/3)...
📊 Buscando pedidos pendentes com saldo > 0...
   ✅ 245 pedidos pendentes encontrados
   ✅ 198 pedidos do Odoo para verificar
🔍 Verificando existência de 198 pedidos no Odoo (em lotes)...
   📦 Verificando lote 1/2 (100 pedidos)...
      ✅ Todos os 100 pedidos do lote encontrados no Odoo
   📦 Verificando lote 2/2 (98 pedidos)...
      ⚠️ 3 pedidos NÃO encontrados ou cancelados neste lote
🚨 3 pedidos NÃO encontrados no Odoo - processando exclusão...
   🗑️ Excluindo pedido VSC12345...
   ✅ CANCELAMENTO COMPLETO: Pedido VSC12345 EXCLUÍDO DO SISTEMA
✅ 3/3 pedidos excluídos com sucesso
================================================================================
✅ VERIFICAÇÃO CONCLUÍDA em 4.23s
   Pedidos verificados: 198
   Pedidos excluídos: 3
================================================================================
```

---

## Comportamento Detalhado

### O que é verificado?

- ✅ Todos os pedidos na `CarteiraPrincipal` com `qtd_saldo_produto_pedido > 0`
- ✅ Apenas pedidos do Odoo (prefixos VSC, VCD, VFB)

### O que é excluído?

1. **Pedidos não encontrados no Odoo** (foram deletados)
2. **Pedidos com `state = 'cancel'`** no Odoo

### Processo de Exclusão (`_processar_cancelamento_pedido`)

Ao detectar um pedido excluído/cancelado:

1. ✅ **EmbarqueItem**: Cancela itens vinculados (`status='cancelado'`)
2. ✅ **Separacao**: EXCLUI todas as separações do pedido
3. ✅ **CarteiraPrincipal**: EXCLUI todos os itens do pedido
4. ✅ **PreSeparacaoItem**: Remove pré-separações (se existirem)

---

## Estatísticas e Monitoramento

### Retorno da Função

```python
{
    'sucesso': True,
    'pedidos_verificados': 198,      # Total de pedidos verificados
    'pedidos_excluidos': 3,           # Quantos foram excluídos
    'pedidos_nao_encontrados': [      # Lista de pedidos excluídos
        'VSC12345',
        'VCD67890',
        'VFB11111'
    ],
    'tempo_execucao': 4.23            # Tempo em segundos
}
```

### Logs de Auditoria

Todos os pedidos excluídos são registrados no log com:
- Número do pedido
- Motivo (não encontrado ou cancelado)
- Quantidade de separações/itens excluídos
- Quantidade de embarques cancelados

---

## Segurança e Validações

### Proteção contra Exclusões Incorretas

1. ✅ **Filtra por estado:** Só exclui se `state != 'cancel'` no Odoo OU se não encontrado
2. ✅ **Retry automático:** 3 tentativas em caso de erro de conexão
3. ✅ **Tratamento de erros:** Se um lote falhar, continua com próximo
4. ✅ **Rollback automático:** Em caso de erro, desfaz alterações
5. ✅ **Logs detalhados:** Rastreabilidade completa de todas as ações

### Pedidos Protegidos

- ❌ Pedidos **não-Odoo** (outros prefixos) **NUNCA são tocados**
- ❌ Pedidos com `qtd_saldo_produto_pedido = 0` **NÃO são verificados**

---

## Impacto no Scheduler

### Tempo Total Estimado (30min)

```
Faturamento:       ~8-15s  (varia com volume de NFs)
Carteira:          ~10-20s (varia com pedidos alterados)
Verificação:       ~3-10s  ← NOVO (varia com total de pedidos)
Requisições:       ~5-10s
Pedidos Compra:    ~5-10s
Alocações:         ~5-10s
────────────────────────────
TOTAL:            ~36-75s  (bem abaixo dos 30min = 1800s)
```

### Conclusão de Viabilidade

✅ **SIM, é VIÁVEL rodar a cada 30 minutos**

- Tempo adicional: **~3-10 segundos** (para 200-500 pedidos)
- Impacto: **< 1% do intervalo total** (30 minutos)
- Benefício: **Detecção imediata** de pedidos excluídos/cancelados

---

## Configuração

### Variáveis de Ambiente (Futuro)

Caso queira tornar configurável:

```bash
# .env
VERIFICACAO_EXCLUSOES_ATIVA=true          # Ativar/desativar
VERIFICACAO_EXCLUSOES_LOTE_SIZE=100       # Tamanho do lote
VERIFICACAO_EXCLUSOES_MAX_RETRIES=3       # Tentativas
```

### Desativar Verificação (se necessário)

**Opção 1:** Comentar no scheduler (linhas 252-298)

```python
# # 2.5️⃣ VERIFICAÇÃO DE PEDIDOS EXCLUÍDOS DO ODOO - com retry
# sucesso_verificacao = False
# ...
```

**Opção 2:** Criar flag condicional

```python
VERIFICACAO_ATIVA = os.environ.get('VERIFICACAO_EXCLUSOES_ATIVA', 'true').lower() == 'true'

if VERIFICACAO_ATIVA:
    # ... código de verificação
```

---

## Checklist de Implementação

- [x] Método `verificar_pedidos_excluidos_odoo()` criado
- [x] Integração com scheduler implementada
- [x] Retry automático configurado
- [x] Logs detalhados adicionados
- [x] Tratamento de erros robusto
- [x] Resumo final atualizado (6 módulos)
- [x] Performance otimizada (busca em lote)
- [x] Documentação completa

---

## Próximos Passos (Opcional)

1. **Monitorar performance real** no ambiente de produção
2. **Ajustar tamanho do lote** se necessário (atualmente 100)
3. **Criar dashboard** para visualizar pedidos excluídos
4. **Adicionar notificações** quando muitos pedidos forem excluídos
5. **Criar endpoint API** para verificação sob demanda

---

## Suporte

Em caso de dúvidas ou problemas:

1. Verificar logs do scheduler em `/logs/`
2. Buscar por `🔍 VERIFICAÇÃO` ou `verificar_pedidos_excluidos`
3. Verificar estatísticas no resumo final da sincronização

---

**Última Atualização:** 2025-01-04
**Autor:** Sistema de Fretes - Sincronização Odoo
