# Exemplos de Uso - Gerindo Expedicao

Mapeamento de perguntas frequentes para comandos dos scripts.

## Indice por Script

| Script | Perguntas Cobertas |
|--------|-------------------|
| consultando_situacao_pedidos | Pedidos pendentes, atrasados, status, consolidacao |
| consultando_produtos_estoque | Entradas, saidas, sobra, ruptura |
| analisando_disponibilidade_estoque | Disponibilidade, adiamento, gargalos |
| calculando_leadtime_entrega | Prazo de entrega |
| criando_separacao_pedidos | Criar separacoes |

---

## consultando_situacao_pedidos.py

### "Tem pedido pendente pro Atacadao?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py --grupo atacadao
```

**Resposta esperada:**
```
Sim! 5 pedidos pendentes para Atacadao:
1. VCD123 - Atacadao lj 183 - R$ 45.000 - 15 itens
Total pendente: R$ 180.000
```

---

### "Tem pedido atrasado pra embarcar?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py --atrasados
```

**Resposta esperada:**
```
Sim! 8 pedidos atrasados:
1. VCD100 - Carrefour - 5 dias de atraso - R$ 50.000
Total em atraso: R$ 250.000
```

---

### "Tem pedido faltando bonificacao?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py --verificar-bonificacao
```

**Resposta esperada:**
```
FALTA BONIFICACAO NA SEPARACAO:
1. VCD500 (Atacadao lj 183)
   - Venda: Em separacao
   - Bonificacao: NAO esta em separacao
```

---

### "Pedido VCD123 ta em separacao?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py --pedido VCD123 --status
```

**Resposta esperada:**
```
Pedido VCD123 - Atacadao lj 183:
Status: PARCIALMENTE SEPARADO
- Em separacao: 12 itens, R$ 35.000 (78%)
- Pendente na carteira: 3 itens, R$ 10.000 (22%)
```

---

### "Tem mais pedido pra mandar junto com o Assai lj 123?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py --consolidar-com "assai 123"
```

**Resposta esperada:**
```
Pedidos para consolidar com Assai lj 123 (Sao Paulo/SP):
MESMO CEP: 1 pedido
MESMA CIDADE: 3 pedidos
MESMA SUB-ROTA: 2 pedidos
```

---

## consultando_produtos_estoque.py

### "Chegou o palmito?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py --produto palmito --entradas
```

**Resposta esperada:**
```
Sim! Chegaram Palmitos recentemente:
28/11: Palmito Inteiro 300g: +500 un (PRODUCAO - Linha 1101-6)
Estoque atual: 1.200 un
```

---

### "Saiu muito cogumelo?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py --produto cogumelo --saidas
```

**Resposta esperada:**
```
Saidas de Cogumelo (ultimos 7 dias):
27/11: Cogumelo Fatiado 200g: -300 un (VENDA - NF 12345)
26/11: Cogumelo Inteiro 200g: -150 un (VENDA - NF 12340)
```

---

### "Falta embarcar muito pessego?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py --produto pessego --pendente
```

**Resposta esperada:**
```
Pessego pendente de embarque:
- Total na carteira: 2.500 un (5 pedidos)
- Em separacao: 1.500 un (3 pedidos)
- Falta separar: 1.000 un
Pedidos na carteira:
  - VCD123 (Cliente A): 1.000 un
  - VCD456 (Cliente B): 800 un
```

---

### "Quanto vai sobrar de pessego no estoque?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py --produto pessego --sobra
```

**Resposta esperada:**
```
Pessego em Calda 400g:
- Estoque: 5.000 | Separacao: 1.500 | Carteira s/ sep: 1.000
- Sobra: 2.500 un
```

---

### "O que vai dar falta essa semana?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py --ruptura --dias 7
```

**Resposta esperada:**
```
Previsao de ruptura (ate 06/12):
CRITICO (proximos 2 dias):
- Azeitona Verde 200g: Ruptura em 30/11 - Faltam 500 un
ALERTA (3-5 dias):
- Cogumelo Paris 200g: Ruptura em 03/12 - Faltam 150 un
```

---

## analisando_disponibilidade_estoque.py

### "Quando o pedido VCD123 estara disponivel?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --pedido VCD123
```

**Resposta esperada:**
```
O pedido VCD123 estara 100% disponivel em 05/12/2025.
Itens limitantes:
- Azeitona Verde 200g: disponivel em 03/12
- Palmito Inteiro: disponivel em 05/12
```

---

### "O que vai ter de ruptura se eu enviar o pedido VCD123 amanha?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --pedido VCD123 --data amanha
```

**Resposta esperada:**
```
Se enviar VCD123 amanha, faltarao os produtos:
- Azeitona Verde 200g: Precisa 500, tem 300 -> Disponivel em 05/12
- Palmito Inteiro: Precisa 200, tem 0 -> Disponivel em 08/12
```

---

### "Qual pedido eu precisaria alterar a data para enviar o VCD123 amanha?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --pedido VCD123 --data amanha --sugerir-adiamento
```

**Resposta esperada:**
```
Para enviar VCD123 amanha, voce poderia adiar:
1. Pedido VCD456 (Atacadao) - 45% do pedido eh Azeitona - Exp: 30/11
   -> Libera 500 un de Azeitona
```

---

### "O que esta impactando para enviar os pedidos do Assai de SP completo?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --grupo assai --uf SP
```

**Resposta esperada:**
```
Gargalos para enviar Assai SP completo:
1. Azeitona Verde 200g: Falta em 5 pedidos, total 2.500 un faltantes
2. Palmito Inteiro: Falta em 3 pedidos, total 800 un faltantes
```

---

### "Esses itens sao por conta de outros pedidos ou falta mesmo?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --grupo assai --diagnosticar-origem
```

**Resposta esperada:**
```
Azeitona Verde 200g:
- Estoque: 1.000 | Demanda Assai: 2.500 | Demanda outros: 800
-> FALTA ABSOLUTA: Mesmo sem outros pedidos, faltariam 1.500 un

Palmito Inteiro:
- Estoque: 1.500 | Demanda Assai: 800 | Demanda outros: 900
-> FALTA RELATIVA: Se adiar outros pedidos, consegue atender
```

---

### "Quais pedidos sem agendamento posso enviar amanha?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --data amanha --sem-agendamento
```

**Resposta esperada:**
```
Pedidos disponiveis para envio amanha (sem agendamento):
1. VCD123 - Cliente ABC - R$ 45.000 - 100% disponivel
Total: 15 pedidos, R$ 450.000
```

---

### "Falta muito pra matar o pedido do Atacadao 183?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --grupo atacadao --loja 183 --completude
```

**Resposta esperada:**
```
Pedido Atacadao 183 (VCD-2024-001234):
Completude: 75% ja faturado
- Valor original: R$ 60.000
- Valor pendente: R$ 15.000
Itens pendentes com falta: Azeitona, Palmito
```

---

### "Os pedidos atrasados sao por falta?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --atrasados --diagnosticar-causa
```

**Resposta esperada:**
```
POR FALTA DE ESTOQUE: 5 pedidos
1. VCD100 (Carrefour):
   - Azeitona: Precisa 500, tem 200 -> Falta 300
OUTRO MOTIVO: 3 pedidos
```

---

### "Quais pedidos mais estao travando a carteira?"

```bash
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py --ranking-impacto
```

**Resposta esperada:**
```
1. VCD200 (Makro) - Trava 8 outros pedidos
   - Consome 1.000 un Azeitona (80% do deficit)
```

---

## calculando_leadtime_entrega.py

### "Se embarcar o pedido VCD123 amanha quando chega no cliente?"

```bash
python .claude/skills/gerindo-expedicao/scripts/calculando_leadtime_entrega.py --pedido VCD123 --data-embarque amanha
```

**Resposta esperada:**
```
Embarque amanha (30/11) -> Chegada prevista:
Opcao 1: Transp. Fast - Lead time 2 dias -> Chega 02/12
Opcao 2: Transp. ABC - Lead time 3 dias -> Chega 03/12
```

---

## criando_separacao_pedidos.py

### "Crie separacao completa do VCD123 pra amanha"

**Passo 1 - Simular:**
```bash
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py --pedido VCD123 --expedicao amanha --tipo completa
```

**Passo 2 - Executar (apos confirmacao):**
```bash
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py --pedido VCD123 --expedicao amanha --tipo completa --executar
```

---

### "Separacao VCD456 com 28 pallets dia 20/12"

```bash
# Simular
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py --pedido VCD456 --expedicao 20/12 --pallets 28

# Executar
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py --pedido VCD456 --expedicao 20/12 --pallets 28 --executar
```

---

### "Enviar o que tem do VCD123"

```bash
# Simular
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py --pedido VCD123 --expedicao amanha --apenas-estoque

# Executar
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py --pedido VCD123 --expedicao amanha --apenas-estoque --executar
```

---

## consultando_programacao_producao.py

### "O que da pra alterar na programacao pra matar a ruptura?"

```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_programacao_producao.py --produto "VF pouch 150"
```

**Resposta esperada:**
```
Ruptura VF Pouch 150g prevista para 03/12
OPCAO 1: Trocar VF Pouch com Azeitona Fatiada
  03/12: VF Pouch 150g <- RESOLVE RUPTURA
  05/12: Azeitona Fatiada <- Adiada 2 dias
```
