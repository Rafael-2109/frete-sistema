# 🧪 Roteiro de Teste - Claude AI Sistema de Fretes

## 📋 Instruções
1. Envie cada pergunta ao Claude AI
2. Anote a resposta recebida
3. Compare com os dados reais do sistema
4. Marque ✅ se correto, ❌ se incorreto, ⚠️ se parcialmente correto

## 🎯 Perguntas de Teste

### 1. Consultas Básicas de Status
```
1.1) Qual o status do sistema?
Resposta esperada: Informações gerais sobre módulos ativos, estatísticas básicas

1.2) Quantos clientes existem no sistema?
Resposta esperada: Número total de clientes cadastrados

1.3) Quais são as transportadoras ativas?
Resposta esperada: Lista de transportadoras com razão social
```

### 2. Consultas de Faturamento
```
2.1) Quanto faturou hoje?
Resposta esperada: Valor total faturado no dia atual

2.2) Qual o faturamento de ontem?
Resposta esperada: Valor total do dia anterior

2.3) Quanto faturou essa semana?
Resposta esperada: Soma do faturamento dos últimos 7 dias

2.4) Qual o faturamento do mês de junho de 2025?
Resposta esperada: Valor total de junho/2025
```

### 3. Consultas Específicas por Cliente
```
3.1) Mostre as entregas do Assai
Resposta esperada: Lista de entregas/pedidos do cliente Assai

3.2) Qual o faturamento do Atacadão este mês?
Resposta esperada: Valor faturado para Atacadão no mês atual

3.3) Quantas entregas pendentes tem o Carrefour?
Resposta esperada: Número de entregas não finalizadas

3.4) Mostre os pedidos do Fort Atacadista
Resposta esperada: Lista de pedidos ou mensagem se não existir
```

### 4. Consultas com Filtro Geográfico
```
4.1) Quais entregas estão pendentes em SP?
Resposta esperada: Entregas com destino São Paulo não finalizadas

4.2) Mostre o faturamento do RJ esta semana
Resposta esperada: Valor faturado com destino Rio de Janeiro

4.3) Quantas entregas foram feitas em MG hoje?
Resposta esperada: Número de entregas realizadas em Minas Gerais
```

### 5. Consultas de Status e Problemas
```
5.1) Quais entregas estão atrasadas?
Resposta esperada: Lista de entregas com data prevista vencida

5.2) Mostre os pedidos pendentes de cotação
Resposta esperada: Pedidos sem frete cotado

5.3) Quais embarques estão ativos?
Resposta esperada: Embarques com status="ativo"

5.4) Tem alguma entrega com problema?
Resposta esperada: Entregas com status de problema/pendência
```

### 6. Consultas Complexas
```
6.1) Qual o faturamento do Assai em SP nos últimos 30 dias?
Resposta esperada: Valor específico do cliente + UF + período

6.2) Quantas entregas o Atacadão tem pendentes em São Paulo?
Resposta esperada: Número específico com múltiplos filtros

6.3) Mostre os fretes aprovados mas não pagos
Resposta esperada: Lista de fretes com status específico

6.4) Quais transportadoras são freteiros?
Resposta esperada: Lista filtrando por tipo freteiro=true
```

### 7. Testes de Validação e Erros
```
7.1) Mostre dados da Magazine Luiza
Resposta esperada: Cliente não encontrado no sistema

7.2) Qual o faturamento de 2030?
Resposta esperada: Mensagem sobre data futura/inválida

7.3) asai (com erro de digitação)
Resposta esperada: Deve entender como "Assai" e processar

7.4) Mostre entregas de São Paulo do cliente Renner
Resposta esperada: Cliente não existe (não inventar dados)
```

### 8. Consultas de Agregação
```
8.1) Qual o ticket médio de hoje?
Resposta esperada: Valor médio das NFs do dia

8.2) Quantos pedidos foram criados esta semana?
Resposta esperada: Contagem de pedidos novos

8.3) Qual transportadora tem mais fretes este mês?
Resposta esperada: Ranking de transportadoras

8.4) Qual o prazo médio de entrega?
Resposta esperada: Média de dias entre embarque e entrega
```

### 9. Consultas Operacionais
```
9.1) Tem algum embarque na portaria?
Resposta esperada: Embarques sem data_embarque

9.2) Quantos veículos estão no pátio?
Resposta esperada: Controle de portaria status="DENTRO"

9.3) Quais entregas tem agendamento para hoje?
Resposta esperada: Agendamentos com data atual

9.4) Mostre as despesas extras pendentes
Resposta esperada: DespesaExtra sem número_documento
```

### 10. Teste de Contexto e Memória
```
10.1) Primeira pergunta: "Mostre dados do Assai"
10.2) Segunda pergunta: "E de SP?" 
      (deve entender que é Assai + SP pelo contexto)

10.3) Primeira: "Qual o faturamento de junho?"
10.4) Segunda: "E de julho?"
      (deve manter o contexto de faturamento)
```

## 📊 Relatório de Resultados

| Pergunta | Resposta Correta? | Observações |
|----------|------------------|-------------|
| 1.1      | [ ] ✅ [ ] ❌ [ ] ⚠️ |             |
| 1.2      | [ ] ✅ [ ] ❌ [ ] ⚠️ |             |
| 1.3      | [ ] ✅ [ ] ❌ [ ] ⚠️ |             |
| ...      | ...              | ...         |

## 🔍 Pontos de Atenção

1. **Dados Reais**: O sistema deve usar apenas dados existentes no banco
2. **Não Inventar**: Nunca criar clientes ou dados fictícios
3. **Filtros Corretos**: Verificar se aplica filtros de vendedor quando necessário
4. **Formatação**: Valores em R$ com 2 casas decimais
5. **Performance**: Anotar se alguma consulta demora muito

## 💡 Dicas para Análise

- Compare totais com queries diretas no banco
- Verifique se detecta corretamente nomes com acentos
- Teste se entende variações (SP, São Paulo, Sao Paulo)
- Confirme que não mostra dados de outros vendedores (se aplicável)
- Valide cálculos de períodos (hoje, ontem, semana, mês) 