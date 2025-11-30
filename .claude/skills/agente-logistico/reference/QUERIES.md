# Mapeamento das 20 Queries Representativas

## Indice

1. [Scripts Consolidados](#scripts-consolidados)
2. [analisando_disponibilidade.py](#script-analisando_disponibilidadepy)
   - [Q1: Quando pedido estara disponivel](#q1-quando-o-pedido-vcd123-estara-disponivel)
   - [Q2: Ruptura se enviar amanha](#q2-o-que-vai-ter-de-ruptura-se-eu-enviar-o-pedido-vcd123-amanha)
   - [Q3: Qual pedido adiar](#q3-qual-pedido-eu-precisaria-alterar-a-data-para-enviar-o-vcd123-amanha)
   - [Q4: O que impacta envio completo](#q4-o-que-esta-impactando-para-enviar-os-pedidos-do-assai-de-sp-completo)
   - [Q5: Falta absoluta ou relativa](#q5-esses-itens-sao-por-conta-de-outros-pedidos-ou-falta-mesmo)
   - [Q6: Pedidos sem agendamento](#q6-quais-pedidos-sem-agendamento-posso-enviar-amanha)
   - [Q9: Falta muito pra matar pedido](#q9-falta-muito-pra-matar-o-pedido-do-atacadao-183)
   - [Q11: Atrasados sao por falta](#q11-os-pedidos-atrasados-sao-por-falta)
   - [Q12: Pedidos travando carteira](#q12-quais-pedidos-mais-estao-travando-a-carteira)
3. [consultando_pedidos.py](#script-consultando_pedidospy)
   - [Q8: Pedido pendente pro cliente](#q8-tem-pedido-pendente-pro-atacadao)
   - [Q10: Pedido atrasado](#q10-tem-pedido-atrasado-pra-embarcar)
   - [Q14: Faltando bonificacao](#q14-tem-pedido-faltando-bonificacao)
   - [Q16: Status do pedido](#q16-pedido-vcd123-ta-em-separacao)
   - [Q19: Pedidos para consolidar](#q19-tem-mais-pedido-pra-mandar-junto-com-o-assai-lj-123)
4. [consultando_estoque.py](#script-consultando_estoquepy)
   - [Q13: Chegou produto](#q13-chegou-o-palmito)
   - [Q17: Falta embarcar produto](#q17-falta-embarcar-muito-pessego)
   - [Q18: Sobra de estoque](#q18-quanto-vai-sobrar-de-pessego-no-estoque)
   - [Q20: Previsao de falta](#q20-o-que-vai-dar-falta-essa-semana)
5. [calculando_prazo.py](#script-calculando_prazopy)
   - [Q7: Quando chega no cliente](#q7-se-embarcar-o-pedido-vcd123-amanha-quando-chega-no-cliente)
6. [analisando_programacao.py](#script-analisando_programacaopy)
   - [Q15: Alterar programacao](#q15-o-que-da-pra-alterar-na-programacao-pra-matar-a-ruptura)

---

## Scripts Consolidados

| Script | Queries | Dominio |
|--------|---------|---------|
| `analisando_disponibilidade.py` | 1, 2, 3, 4, 5, 6, 9, 11, 12 | Disponibilidade e impacto |
| `consultando_pedidos.py` | 8, 10, 14, 16, 19 | Consulta de pedidos |
| `consultando_estoque.py` | 13, 17, 18, 20 | Estoque e projecoes |
| `calculando_prazo.py` | 7 | Lead time e entrega |
| `analisando_programacao.py` | 15 | Producao |

---

## Script: analisando_disponibilidade.py

### Q1: "Quando o pedido VCD123 estara disponivel?"

**Comando:** `analisando_disponibilidade.py --pedido VCD123`

**Logica:**
1. Buscar itens: CarteiraPrincipal WHERE num_pedido = 'VCD123' AND qtd_saldo > 0
2. Para cada item: calcular projecao de estoque (28 dias)
3. Encontrar primeiro dia onde saldo >= quantidade necessaria
4. Resposta = MAX(data) de todos os itens

**Output esperado:**
```
O pedido VCD123 estara 100% disponivel em DD/MM/YYYY.
Itens limitantes:
- Produto X: disponivel em DD/MM
- Produto Y: disponivel em DD/MM
```

---

### Q2: "O que vai ter de ruptura se eu enviar o pedido VCD123 amanha?"

**Comando:** `analisando_disponibilidade.py --pedido VCD123 --data amanha`

**Logica:**
1. Buscar itens do VCD123
2. Para cada item: verificar estoque projetado para amanha
3. Se estoque < quantidade necessaria -> RUPTURA
4. Calcular data de disponibilidade do item

**Output esperado:**
```
Se enviar VCD123 amanha, faltarao os produtos:
- Azeitona Verde 200g: Precisa 500, tem 300 -> Disponivel em 05/12
- Palmito Inteiro: Precisa 200, tem 0 -> Disponivel em 08/12
```

---

### Q3: "Qual pedido eu precisaria alterar a data para enviar o VCD123 amanha?"

**Comando:** `analisando_disponibilidade.py --pedido VCD123 --data amanha --sugerir-adiamento`

**Logica:**
1. Identificar produtos do VCD123 com estoque insuficiente
2. Buscar Separacao onde esses produtos estao (expedicao <= amanha, sincronizado_nf=False)
3. Calcular concentracao: valor_item / valor_total_pedido
4. Ordenar: concentracao DESC, expedicao DESC

**Output esperado:**
```
Para enviar VCD123 amanha, voce poderia adiar:
1. Pedido VCD456 (Atacadao) - 45% do pedido eh Azeitona - Exp: 30/11
   -> Libera 500 un de Azeitona
```

---

### Q4: "O que esta impactando para enviar os pedidos do Assai de SP completo?"

**Comando:** `analisando_disponibilidade.py --grupo assai --uf SP`

**Logica:**
1. Buscar pedidos: cnpj_cpf LIKE '06057223%' AND estado = 'SP'
2. Para cada pedido: verificar disponibilidade de cada item
3. Consolidar gargalos (produtos que mais aparecem como falta)

**Output esperado:**
```
Gargalos para enviar Assai SP completo:
1. Azeitona Verde 200g: Falta em 5 pedidos, total 2.500 un faltantes
2. Palmito Inteiro: Falta em 3 pedidos, total 800 un faltantes
```

---

### Q5: "Esses itens sao por conta de outros pedidos ou falta mesmo?"

**Comando:** `analisando_disponibilidade.py --grupo assai --diagnosticar-origem`

**Logica:**
1. Para cada produto em ruptura:
   - estoque_atual vs demanda_assai vs demanda_outros
   - Se estoque >= demanda_assai -> FALTA RELATIVA
   - Se estoque < demanda_assai -> FALTA ABSOLUTA

**Output esperado:**
```
Azeitona Verde 200g:
- Estoque: 1.000 | Demanda Assai: 2.500 | Demanda outros: 800
-> FALTA ABSOLUTA: Mesmo sem outros pedidos, faltariam 1.500 un

Palmito Inteiro:
- Estoque: 1.500 | Demanda Assai: 800 | Demanda outros: 900
-> FALTA RELATIVA: Se adiar outros pedidos, consegue atender
```

---

### Q6: "Quais pedidos sem agendamento posso enviar amanha?"

**Comando:** `analisando_disponibilidade.py --data amanha --sem-agendamento`

**Logica:**
1. Calcular pendentes: CarteiraPrincipal - Separacao.sincronizado_nf=False
2. Filtrar: cnpj NOT IN ContatoAgendamento OU forma = 'SEM AGENDAMENTO'
3. Verificar disponibilidade de todos itens
4. Se 100% disponivel -> incluir

**Output esperado:**
```
Pedidos disponiveis para envio amanha (sem agendamento):
1. VCD123 - Cliente ABC - R$ 45.000 - 100% disponivel
Total: 15 pedidos, R$ 450.000
```

---

### Q9: "Falta muito pra matar o pedido do Atacadao 183?"

**Comando:** `analisando_disponibilidade.py --grupo atacadao --loja 183 --completude`

**Logica:**
1. Buscar: grupo atacadao + raz_social_red ILIKE '%183%'
2. Calcular: valor_pendente / valor_original
3. Verificar disponibilidade de cada item pendente

**Output esperado:**
```
Pedido Atacadao 183 (VCD-2024-001234):
Completude: 75% ja faturado
- Valor original: R$ 60.000
- Valor pendente: R$ 15.000
Itens pendentes com falta: Azeitona, Palmito
```

---

### Q11: "Os pedidos atrasados sao por falta?"

**Comando:** `analisando_disponibilidade.py --atrasados --diagnosticar-causa`

**Logica:**
1. Pegar pedidos atrasados (expedicao < HOJE)
2. Para cada: verificar disponibilidade de cada item
3. Se algum item com falta -> "Por falta"
4. Retornar pedidos E produtos com falta

**Output esperado:**
```
POR FALTA DE ESTOQUE: 5 pedidos
1. VCD100 (Carrefour):
   - Azeitona: Precisa 500, tem 200 -> Falta 300
OUTRO MOTIVO: 3 pedidos
```

---

### Q12: "Quais pedidos mais estao travando a carteira?"

**Comando:** `analisando_disponibilidade.py --ranking-impacto`

**Logica:**
1. Identificar produtos em ruptura
2. Para cada: calcular impacto de cada pedido
3. Impacto = qtd_pedido / deficit_total
4. Rankear por impacto total

**Output esperado:**
```
1. VCD200 (Makro) - Trava 8 outros pedidos
   - Consome 1.000 un Azeitona (80% do deficit)
```

---

## Script: consultando_pedidos.py

### Q8: "Tem pedido pendente pro Atacadao?"

**Comando:** `consultando_pedidos.py --grupo atacadao`

**Logica:**
1. Buscar: cnpj_cpf LIKE '93209765%' OR '75315333%' OR '00063960%'
2. Filtrar: qtd_saldo_produto_pedido > 0
3. Agrupar por num_pedido

**Output esperado:**
```
Sim! 5 pedidos pendentes para Atacadao:
1. VCD123 - Atacadao lj 183 - R$ 45.000 - 15 itens
Total pendente: R$ 180.000
```

---

### Q10: "Tem pedido atrasado pra embarcar?"

**Comando:** `consultando_pedidos.py --atrasados`

**Logica:**
1. Buscar: Separacao WHERE expedicao < HOJE AND sincronizado_nf = False
2. Agrupar por num_pedido
3. Calcular dias de atraso

**Output esperado:**
```
Sim! 8 pedidos atrasados:
1. VCD100 - Carrefour - 5 dias de atraso - R$ 50.000
Total em atraso: R$ 250.000
```

---

### Q14: "Tem pedido faltando bonificacao?"

**Comando:** `consultando_pedidos.py --verificar-bonificacao`

**Logica:**
1. Identificar CNPJs com bonificacao (forma_pgto LIKE 'Sem Pagamento%')
2. Para cada: verificar se venda E bonificacao estao em Separacao
3. Alertar se apenas um esta separado

**Output esperado:**
```
FALTA BONIFICACAO NA SEPARACAO:
1. VCD500 (Atacadao lj 183)
   - Venda: Em separacao
   - Bonificacao: NAO esta em separacao
```

---

### Q16: "Pedido VCD123 ta em separacao?"

**Comando:** `consultando_pedidos.py --pedido VCD123 --status`

**Logica:**
1. Buscar CarteiraPrincipal: qtd_saldo_produto_pedido
2. Buscar Separacao: sincronizado_nf = False
3. Classificar: faturado | 100% separado | parcial | nao separado

**Output esperado:**
```
Pedido VCD123 - Atacadao lj 183:
Status: PARCIALMENTE SEPARADO
- Em separacao: 12 itens, R$ 35.000 (78%)
- Pendente na carteira: 3 itens, R$ 10.000 (22%)
```

---

### Q19: "Tem mais pedido pra mandar junto com o Assai lj 123?"

**Comando:** `consultando_pedidos.py --consolidar-com "assai 123"`

**Logica:**
1. Buscar dados do Assai lj 123: CEP, cidade, sub_rota
2. Buscar candidatos: sem separacao OU status='ABERTO'
3. Filtrar por proximidade: CEP > CIDADE > SUB_ROTA

**Output esperado:**
```
Pedidos para consolidar com Assai lj 123 (Sao Paulo/SP):
MESMO CEP: 1 pedido
MESMA CIDADE: 3 pedidos
MESMA SUB-ROTA: 2 pedidos
```

---

## Script: consultando_estoque.py

### Q13: "Chegou o palmito?" / "Saiu muito palmito?"

**Comando (entradas):** `consultando_estoque.py --produto palmito --entradas`
**Comando (saidas):** `consultando_estoque.py --produto palmito --saidas`

**Logica:**
1. Buscar codigos: CadastroPalletizacao WHERE nome ILIKE '%palmito%'
2. Buscar movimentacoes: MovimentacaoEstoque WHERE qtd > 0 (entradas) ou qtd < 0 (saidas)
3. Retornar tipo_movimentacao e local_movimentacao para enriquecer resposta
4. Incluir estoque atual

**Output esperado:**
```
Sim! Chegaram Palmitos recentemente:
28/11: Palmito Inteiro 300g: +500 un (PRODUCAO - Linha 1101-6)
Estoque atual: 1.200 un
```

---

### Q17: "Falta embarcar muito pessego?"

**Comando:** `consultando_estoque.py --produto pessego --pendente`

**Logica:**
1. Buscar codigos de pessego
2. carteira = SUM(CarteiraPrincipal.qtd_saldo) agrupado por pedido
3. separacao = SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False) agrupado por pedido
4. falta_separar = carteira - separacao

**Output esperado:**
```
Pessego pendente de embarque:
- Total na carteira: 2.500 un (5 pedidos)
- Em separacao: 1.500 un (3 pedidos)
- Falta separar: 1.000 un
Pedidos na carteira:
  - VCD123 (Cliente A): 1.000 un
  - VCD456 (Cliente B): 800 un
  - VCD789 (Cliente C): 700 un
```

---

### Q18: "Quanto vai sobrar de pessego no estoque?"

**Comando:** `consultando_estoque.py --produto pessego --sobra`

**Logica:**
1. estoque = estoque_atual
2. em_separacao = SUM(Separacao WHERE sincronizado_nf=False)
3. carteira_sem_separacao = carteira_total - em_separacao
4. sobra = estoque - carteira_total

**Output esperado:**
```
Pessego em Calda 400g:
- Estoque: 5.000 | Separacao: 1.500 | Carteira s/ sep: 1.000
- Sobra: 2.500 un
```

---

### Q20: "O que vai dar falta essa semana?"

**Comando:** `consultando_estoque.py --ruptura --dias 7`

**Logica:**
1. Para cada produto ativo: calcular projecao 7 dias
2. Filtrar produtos com dia_ruptura <= HOJE + 7
3. Ordenar por urgencia

**Output esperado:**
```
Previsao de ruptura (ate 06/12):
CRITICO (proximos 2 dias):
- Azeitona Verde 200g: Ruptura em 30/11 - Faltam 500 un
ALERTA (3-5 dias):
- Cogumelo Paris 200g: Ruptura em 03/12 - Faltam 150 un
```

---

## Script: calculando_prazo.py

### Q7: "Se embarcar o pedido VCD123 amanha quando chega no cliente?"

**Comando:** `calculando_prazo.py --pedido VCD123 --data-embarque amanha`

**Logica:**
1. Buscar dados do pedido: cidade, UF, codigo_ibge
2. Buscar CidadeAtendida: transportadoras + lead_time
3. data_entrega = embarque + lead_time
4. Ordenar por tempo (mais rapida primeiro)

**Output esperado:**
```
Embarque amanha (30/11) -> Chegada prevista:
Opcao 1: Transp. Fast - Lead time 2 dias -> Chega 02/12
Opcao 2: Transp. ABC - Lead time 3 dias -> Chega 03/12
```

---

## Script: analisando_programacao.py

### Q15: "O que da pra alterar na programacao pra matar a ruptura?"

**Comando:** `analisando_programacao.py --produto "VF pouch 150"`

**Logica:**
1. Identificar produto por nome/categoria/subcategoria
2. Identificar linha de producao
3. Buscar programacao da linha
4. Calcular ruptura e simular opcoes (trocar ou empurrar)

**Output esperado:**
```
Ruptura VF Pouch 150g prevista para 03/12
OPCAO 1: Trocar VF Pouch com Azeitona Fatiada
  03/12: VF Pouch 150g <- RESOLVE RUPTURA
  05/12: Azeitona Fatiada <- Adiada 2 dias
```

---

## Tabelas Utilizadas

| Tabela | Proposito |
|--------|-----------|
| CarteiraPrincipal | Pedidos com saldo pendente |
| Separacao | Itens reservados (sincronizado_nf=False) |
| MovimentacaoEstoque | Estoque atual e movimentos |
| ProgramacaoProducao | Producoes futuras |
| CadastroPalletizacao | Cadastro de produtos |
| ContatoAgendamento | Exigencia de agendamento |
| CidadeAtendida | Lead time por transportadora |
| CadastroSubRota | Sub-rotas por cidade |

---

## Grupos Empresariais

| Grupo | Prefixos CNPJ |
|-------|---------------|
| Atacadao | 93209765, 75315333, 00063960 |
| Assai | 06057223 |
| Tenda | 01157555 |
