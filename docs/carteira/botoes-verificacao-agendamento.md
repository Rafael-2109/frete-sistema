<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Diferenca de comportamento entre os dois botoes de verificacao de agendamento da carteira (Verificar Agendas vs Verificar Todos Pendentes)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 📋 Diferença entre os botões de verificação

> **Papel:** Explicar a diferença de escopo e comportamento entre os dois botões de verificação de protocolos de agendamento da carteira agrupada.

## Contexto

A tela da carteira agrupada expõe dois botões que verificam protocolos de agendamento no portal: "Verificar Agendas" (escopo local, só o visível) e "Verificar Todos Pendentes" (escopo global, todo o banco). Este documento descreve o que cada um faz, quando usar cada um e o estado atual da API de suporte.

## Indice

- [Análise dos dois botões](#-análise-dos-dois-botões)
- [Comparação](#-comparação)
- [Quando usar cada um](#-quando-usar-cada-um)
- [Estado atual da API](#️-estado-atual-da-api)
- [Resumo](#-resumo)

## 🔍 Análise dos dois botões

### 1. **"Verificar Agendas"** (`verificarAgendasEmLote()`)
- **Localização**: Linha 1537 de carteira-agrupada.js
- **O que faz**:
  - Verifica APENAS os protocolos dos **pedidos visíveis na tela**
  - Pega os protocolos dos pedidos que estão sendo exibidos (após filtros)
  - Coleta TODOS os protocolos únicos das linhas visíveis (sem limite de quantidade)
  - Mais rápido e focado no que o usuário está vendo

**Fluxo**:
1. Coleta protocolos dos pedidos visíveis (`.pedido-row:not([style*="display: none"])`)
2. Filtra apenas os que têm protocolo e não estão confirmados
3. Deduplica protocolos via `Map` (cada protocolo único uma vez)
4. Envia para verificação no portal

### 2. **"Verificar Todos Pendentes"** (`verificarTodosProtocolosPendentes()`)
- **Localização**: Linha 1817 de carteira-agrupada.js
- **O que faz**:
  - Busca TODOS os protocolos pendentes **no banco de dados**
  - Independente do que está visível na tela
  - Verifica TODOS os protocolos não confirmados do sistema
  - Pode processar centenas de protocolos

**Fluxo**:
1. Chama `/portal/api/buscar-protocolos-pendentes` para buscar TODOS
2. Mostra quantos foram encontrados
3. Pede confirmação (avisa que pode demorar)
4. Envia TODOS para verificação

## 📊 Comparação

| Aspecto | "Verificar Agendas" | "Verificar Todos Pendentes" |
|---------|-------------------|---------------------------|
| **Escopo** | Pedidos visíveis na tela | Todos do banco de dados |
| **Quantidade** | Sem limite (todos os visíveis) | Sem limite |
| **Velocidade** | Rápido | Pode demorar |
| **Uso ideal** | Verificação focada | Verificação em massa |
| **Filtros** | Respeita filtros aplicados | Ignora filtros |

## 🎯 Quando usar cada um

### Use "Verificar Agendas" quando:
- Você filtrou pedidos específicos
- Quer verificar apenas alguns protocolos
- Precisa de resposta rápida
- Está trabalhando com um conjunto específico

### Use "Verificar Todos Pendentes" quando:
- Quer fazer uma verificação geral do sistema
- No início/fim do dia
- Para limpeza geral de pendências
- Quando há muitos protocolos acumulados

## ⚠️ Estado atual da API

A API `/portal/api/buscar-protocolos-pendentes` já está:
- ✅ Agrupando por protocolo único (linhas 54-66)
- ✅ Retornando contagem correta de protocolos únicos
- ✅ Evitando duplicação

**Código atual está correto**:
```python
# Agrupar por protocolo único
protocolos_unicos = {}
for sep in separacoes:
    if sep.protocolo not in protocolos_unicos:
        protocolos_unicos[sep.protocolo] = {
            'protocolo': sep.protocolo,
            'lote_id': sep.separacao_lote_id,
            'num_pedido': sep.num_pedido,
            'cliente': sep.raz_social_red,
            'data_agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None
        }
```

## 💡 Resumo

- **"Verificar Agendas"** = Verificação **LOCAL** (só o que está visível)
- **"Verificar Todos Pendentes"** = Verificação **GLOBAL** (todo o sistema)

Ambos evitam duplicação verificando cada protocolo apenas uma vez, mesmo que apareça em múltiplas separações.
