# Regras de Negocio - Sistema de Fretes

Este documento descreve as regras de negocio especificas do sistema logistico.

---

## 1. Grupos Empresariais (por CNPJ)

Clientes sao identificados por grupo empresarial atraves dos primeiros 8 digitos do CNPJ.

**IMPORTANTE:** CNPJs no banco estao FORMATADOS com pontos e barras: `93.209.765/XXXX-XX`

| Grupo | Nome Completo | Prefixos CNPJ (formatados) |
|-------|---------------|----------------------------|
| `atacadao` | Rede Atacadao | 93.209.76, 75.315.33, 00.063.96 |
| `assai` | Rede Assai (Sendas) | 06.057.22 |
| `tenda` | Rede Tenda | 01.157.55 |

**Como buscar (usar formato com pontos):**
```sql
-- Atacadao
WHERE cnpj_cpf LIKE '93.209.76%'
   OR cnpj_cpf LIKE '75.315.33%'
   OR cnpj_cpf LIKE '00.063.96%'

-- Assai
WHERE cnpj_cpf LIKE '06.057.22%'

-- Tenda
WHERE cnpj_cpf LIKE '01.157.55%'
```

**Busca por nome (complementar):**
```sql
WHERE raz_social_red ILIKE '%atacadao%'
   OR raz_social_red ILIKE '%assai%'
```

---

## 2. Bonificacao

**Definicao:** Itens enviados sem cobranca como parte de promocao comercial.

**Identificacao:**
```sql
WHERE forma_pgto_pedido LIKE 'Sem Pagamento%'
```

**Regra critica:** Venda e bonificacao do mesmo cliente devem ser enviados JUNTOS na mesma separacao.

**Verificacao:**
1. Identificar CNPJs que tem bonificacao na CarteiraPrincipal
2. Verificar se AMBOS (venda e bonificacao) estao em Separacao.sincronizado_nf=False
3. Alertar se apenas um esta separado

---

## 3. Roteirizacao

**Prioridade para consolidar pedidos:** CEP > CIDADE > SUB_ROTA

### 3.1 Mesmo CEP
Pedidos com mesmo `cep_endereco_ent` podem ir na mesma entrega.

### 3.2 Mesma Cidade
Pedidos com mesmos `cod_uf + nome_cidade` podem ser consolidados.

### 3.3 Mesma Sub-Rota
```sql
SELECT sub_rota FROM cadastro_sub_rotas
WHERE cod_uf = ? AND nome_cidade ILIKE ?
```

**Candidatos para consolidacao:**
- Pedidos SEM separacao (num_pedido NOT IN Separacao)
- OU com Separacao.status = 'ABERTO' (nao roteirizado ainda)

---

## 4. Estoque e Projecao

### 4.1 Estoque Atual
```
estoque_atual = SUM(MovimentacaoEstoque.qtd_movimentacao) WHERE ativo=True
```

### 4.2 Estoque Disponivel
```
estoque_disponivel = estoque_atual - SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)
```

### 4.3 Projecao Futura
```
projecao[dia] = estoque_atual
              + SUM(ProgramacaoProducao ate dia)
              - SUM(Separacao.qtd_saldo WHERE expedicao <= dia AND sincronizado_nf=False)
              - SUM(CarteiraPrincipal.qtd_saldo nao separado)
```

### 4.4 Ruptura
- **Ruptura absoluta:** estoque_atual < demanda_total (nao ha estoque suficiente)
- **Ruptura relativa:** estoque_atual >= demanda_A mas < demanda_total (estoque comprometido com outros)

---

## 5. Status de Separacao

| Status | Descricao | Aparece na Carteira | Projeta Estoque |
|--------|-----------|---------------------|-----------------|
| PREVISAO | Pre-separacao | Nao (ignorado) | Sim |
| ABERTO | Separado, nao roteirizado | Sim | Sim |
| COTADO | Com cotacao de frete | Sim | Sim |
| EMBARCADO | Enviado | Sim | Sim |
| FATURADO | Com NF (sincronizado_nf=True) | Nao | Nao |

**Regra critica:** `sincronizado_nf = False` eh o criterio PRINCIPAL para projetar estoque.

---

## 6. Pedidos Pendentes vs Separados

### 6.1 Pedido Pendente (na carteira)
```
CarteiraPrincipal.qtd_saldo_produto_pedido > 0
```

### 6.2 Quantidade Separada
```
SUM(Separacao.qtd_saldo) WHERE num_pedido = ? AND sincronizado_nf = False
```

### 6.3 Falta Separar
```
falta_separar = CarteiraPrincipal.qtd_saldo_produto_pedido - quantidade_separada
```

### 6.4 Classificacao do Pedido

| Situacao | Condicao |
|----------|----------|
| Totalmente faturado | qtd_saldo_produto_pedido = 0 para todos itens |
| 100% em separacao | Separacao existe E qtd_saldo = qtd_saldo_produto_pedido |
| Parcialmente separado | Separacao existe MAS qtd_saldo < qtd_saldo_produto_pedido |
| Nao separado | Nao existe em Separacao |

---

## 7. Completude de Pedido ("Matar")

**Definicao:** "Matar o pedido" = completar 100% do pedido original.

**Calculo:**
```
valor_original = SUM(qtd_produto_pedido * preco_produto_pedido)
valor_pendente = SUM(qtd_saldo_produto_pedido * preco_produto_pedido)
percentual_completado = 1 - (valor_pendente / valor_original)
```

**Exemplo:**
- Valor original: R$ 60.000
- Valor pendente: R$ 15.000
- Completude: 75% (falta 25% para "matar")

---

## 8. Atraso de Pedido

**Definicao:** Pedido com data de expedicao no passado e ainda nao faturado.

**Busca:**
```sql
SELECT * FROM separacoes
WHERE expedicao < CURRENT_DATE
  AND sincronizado_nf = False
  AND status NOT IN ('FATURADO', 'EMBARCADO')
```

**Dias de atraso:**
```
dias_atraso = CURRENT_DATE - expedicao
```

---

## 9. Agendamento

### 9.1 Cliente Exige Agendamento
```sql
SELECT forma FROM contatos_agendamento WHERE cnpj = ?
```

Se `forma` existe E != 'SEM AGENDAMENTO' -> Exige agendamento

### 9.2 Cliente Nao Exige Agendamento
- CNPJ nao existe em `contatos_agendamento`
- OU `forma = 'SEM AGENDAMENTO'`

---

## 10. Lead Time (Prazo de Entrega)

**Calculo:**
1. Buscar cidade do cliente pelo codigo_ibge
2. Buscar transportadoras que atendem a cidade
3. Obter lead_time de cada transportadora
4. Data entrega = data_embarque + lead_time (dias)

```sql
SELECT t.razao_social, ca.lead_time
FROM cidades_atendidas ca
JOIN transportadoras t ON t.id = ca.transportadora_id
WHERE ca.codigo_ibge = ?
ORDER BY ca.lead_time ASC
```

---

## 11. Concentracao de Item no Pedido

**Definicao:** Quanto um item representa do valor total do pedido.

**Calculo:**
```
valor_item = qtd_saldo_produto_pedido * preco_produto_pedido
valor_total_pedido = SUM(qtd_saldo_produto_pedido * preco_produto_pedido) GROUP BY num_pedido
concentracao = valor_item / valor_total_pedido
```

**Uso:** Priorizar qual pedido adiar quando produto tem estoque insuficiente.
- Adiar pedido com MAIOR concentracao primeiro (libera mais estoque do produto)
- Desempate: data de expedicao mais recente (adiar o mais tardio)

---

## 12. Termos Comuns (Glossario)

| Termo do Usuario | Significado Tecnico |
|------------------|---------------------|
| "Matar pedido" | Completar 100% do pedido |
| "Ruptura" | Falta de estoque para atender demanda |
| "Travando a carteira" | Pedidos consumindo estoque que impede outros |
| "Chegou?" | Verificar entrada recente no estoque |
| "Falta embarcar" | qtd na carteira ainda nao separada |
| "Vai sobrar" | Estoque apos atender toda demanda |
| "Mandar junto" | Consolidar entregas na mesma viagem |
