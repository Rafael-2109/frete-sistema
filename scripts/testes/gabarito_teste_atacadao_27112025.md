# GABARITO - Teste Estruturado Claude AI Lite
## Cliente: ATACADÃO
## Data do teste: 27/11/2025

---

## DADOS DO BANCO (Snapshot)

### 1. CARTEIRA PRINCIPAL
- Total pedidos: **543**
- Total itens: **7630**

### 2. SEPARAÇÕES POR STATUS
| Status | Itens | Pedidos |
|--------|-------|---------|
| ABERTO | 50 | 14 |
| FATURADO | 1612 | 141 |
| PREVISAO | 1 | 1 |
| **COTADO** | **0** | **0** |

### 3. SEPARAÇÕES ABERTAS (status=ABERTO)
| Pedido | Itens | Valor |
|--------|-------|-------|
| VCD2563522 | 9 | R$ 4.230,30 |
| VCD2542845 | 1 | R$ 47.650,56 |
| VCD2542868 | 1 | R$ 218.400,00 |
| VCD2543430 | 1 | R$ 36,14 |
| VCD2543432 | 1 | R$ 108,42 |

### 4. PEDIDOS COTADOS
**NENHUM** - Não há pedidos com status=COTADO

### 5. PEDIDOS SEM SEPARAÇÃO (Candidatos a envio)
- Total: **529 pedidos**

### 6. ANÁLISE DE DISPONIBILIDADE
| Pedido | Cliente | Itens Disponíveis | Valor | Status |
|--------|---------|-------------------|-------|--------|
| VCD2543013 | ATACADAO 949 | 1/1 (100%) | R$ 2.774,40 | ✅ 100% |
| VCD2564039 | ATACADAO 295 | 0/1 (0%) | R$ 1.565,70 | ❌ |
| VCD2564040 | ATACADAO 297 | 0/1 (0%) | R$ 939,42 | ❌ |

---

## FLUXO DE TESTE ESPERADO

### Pergunta 1: "O que de pedido do Atacadao?"
**Esperado:**
- Sistema deve mostrar resumo dos pedidos do Atacadão
- Pode mostrar quantidade total de pedidos (543) ou resumo

### Pergunta 2: "E em Separação?"
**Esperado:**
- Sistema deve entender que é follow-up do Atacadão
- Mostrar separações do Atacadão por status
- ABERTO: 14 pedidos, 50 itens
- COTADO: 0 pedidos
- FATURADO: 141 pedidos (pode ignorar pois já faturado)

### Pergunta 3: "Tem algum cotado?"
**Esperado:**
- Sistema deve responder: **NÃO há pedidos COTADOS do Atacadão**
- Pode sugerir: "Há 14 pedidos ABERTOS que podem ser cotados"

### Pergunta 4: "Do que tem em aberto, da pra mandar algum?"
**Esperado:**
- Sistema deve analisar disponibilidade dos pedidos ABERTOS
- Verificar estoque vs qtd_saldo de cada item
- Sugerir quais pedidos têm disponibilidade total ou parcial
- Pedido VCD2543013: 100% disponível (1/1 itens)

### Pergunta 5: "Qual o maior que da pra mandar?"
**Esperado:**
- Sistema deve identificar o pedido com maior valor que tenha disponibilidade
- Pode ser VCD2543013 (R$ 2.774,40 - 100% disponível)
- OU mostrar pedidos parciais com maior valor

### Pergunta 6: "Programe o que vai ter disponivel desse pedido X pro dia 01/12"
**Esperado:**
- Sistema deve criar Separacao com status='ABERTO'
- Data expedicao = 2025-12-01
- Qtd = quantidade disponível do pedido

---

## CRITÉRIOS DE SUCESSO

1. ✅ **Herança de contexto**: Sistema mantém "Atacadão" entre perguntas
2. ✅ **Entende "Em Separação"**: Consulta tabela Separacao
3. ✅ **Entende "COTADO"**: Filtra por status='COTADO'
4. ✅ **Análise de disponibilidade**: Compara estoque com qtd_saldo
5. ✅ **Criação de Separação**: Cria registro com dados corretos

---

## OBSERVAÇÕES

- Não há pedidos COTADOS no momento (resposta esperada é "não")
- Pedido VCD2543013 é o único com 100% de disponibilidade no top 5
- O teste deve validar toda a cadeia de contexto sem pistas extras
