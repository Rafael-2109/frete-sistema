---
name: analise-carteira
description: Executa analise completa da carteira de pedidos seguindo algoritmo P1-P7
---

Execute a analise COMPLETA da carteira de pedidos da Nacom Goya.

## Instrucoes

1. Use o script `analisando_carteira_completa.py` da skill `gerindo-expedicao`
2. Siga o algoritmo de priorizacao P1-P7 rigorosamente
3. Identifique gargalos (agendas, materia-prima, producao)

## Output Esperado

Retorne no formato estruturado:

### 1. Resumo Executivo
- Total de pedidos analisados
- Valor total em carteira
- Principais gargalos identificados

### 2. Acoes Imediatas (HOJE)
- Separacoes a criar
- Agendamentos a solicitar
- Pedidos criticos

### 3. Comunicacoes Necessarias
- Mensagens para PCP (agregado por produto)
- Mensagens para Comercial (por gestor)

### 4. Proximos Passos
- Acompanhamentos necessarios
- Datas de retorno esperadas

$ARGUMENTS
