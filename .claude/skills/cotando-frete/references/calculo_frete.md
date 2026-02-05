# Logica Completa de Calculo de Frete

FONTE: `app/utils/calculadora_frete.py` — `CalculadoraFrete.calcular_frete_unificado()`

## Visao Geral

O calculo de frete segue 10 passos sequenciais. Cada passo depende do anterior.
Componentes podem ser aplicados ANTES ou DEPOIS do frete minimo, conforme configuracao da transportadora.

---

## Passo 1: Determinar ICMS

PRIORIDADE (usa o primeiro que existir):
1. `icms_proprio` (campo da TabelaFrete) — ICMS fixo definido pela tabela
2. `icms` (campo da Cidade) — ICMS do municipio destino
3. `icms_destino` (campo da TabelaFrete) — fallback

EXEMPLO: Tabela com `icms_proprio=0.12` → usa 12%, ignora ICMS da cidade

FONTE: `calculadora_frete.py:218-236` (`_obter_icms_final`)

---

## Passo 2: Peso para Calculo

FORMULA: `peso_para_calculo = max(peso_real, frete_minimo_peso)`

**CONFUSAO COMUM**: `frete_minimo_peso` NAO e um valor em R$.
E um PESO MINIMO em kg. Se a carga pesa 50kg mas o minimo e 100kg, cobra-se por 100kg.

EXEMPLO: peso_real=50kg, frete_minimo_peso=100kg → peso_para_calculo=100kg

FONTE: `calculadora_frete.py:238-245` (`_determinar_peso_calculo`)

---

## Passo 3: Frete Base

FORMULA:
```
frete_peso  = peso_para_calculo × valor_kg
frete_valor = valor_mercadoria × (percentual_valor / 100)
frete_base  = frete_peso + frete_valor
```

**CONFUSAO COMUM**: E SOMA, NAO "o maior dos dois".
Ambos componentes sempre se somam.

EXEMPLO: 5.000kg × R$0,85/kg = R$4.250 + R$50.000 × 0,30% = R$150 → frete_base = R$4.400

FONTE: `calculadora_frete.py:247-261` (`_calcular_frete_base`)

---

## Passo 4: Componentes Adicionais

Cada componente pode ser ANTES ou DEPOIS do frete minimo.
A transportadora define isso via flags `aplica_X_pos_minimo` (default: False = ANTES).

### 4.1 GRIS (Gerenciamento de Risco)

FORMULA: `gris = max(valor_mercadoria × percentual_gris / 100, gris_minimo)`

Se o calculo percentual da menos que o minimo, usa o minimo.

EXEMPLO: R$50.000 × 0,30% = R$150. gris_minimo=R$25. → gris = R$150 (calculado > minimo)
EXEMPLO: R$5.000 × 0,30% = R$15. gris_minimo=R$25. → gris = R$25 (minimo > calculado)

FONTE: `calculadora_frete.py:288-301` (`_calcular_gris_com_minimo`)

### 4.2 ADV (Ad Valorem)

FORMULA: `adv = max(valor_mercadoria × percentual_adv / 100, adv_minimo)`

Mesma logica do GRIS, com seu proprio minimo.

FONTE: `calculadora_frete.py:303-316` (`_calcular_adv_com_minimo`)

### 4.3 RCA (Risco de Carga Aquaviaria)

FORMULA: `rca = valor_mercadoria × percentual_rca / 100`

NAO tem valor minimo. Usado para cargas que passam por balsa/navio.

FONTE: `calculadora_frete.py:318-326` (`_calcular_rca`)

### 4.4 Pedagio

DUAS FORMAS (configurada em `transportadora.pedagio_por_fracao`):

**A) POR FRACAO** (`pedagio_por_fracao=True`, default):
```
multiplos = ceil(peso / 100)   → arredonda PARA CIMA
pedagio  = multiplos × pedagio_por_100kg
```

EXEMPLO: 5.250kg → ceil(52,5) = 53 fracoes × R$5,50 = R$291,50

**B) EXATO** (`pedagio_por_fracao=False`):
```
multiplos = peso / 100   → valor EXATO
pedagio  = multiplos × pedagio_por_100kg
```

EXEMPLO: 5.250kg → 52,5 fracoes × R$5,50 = R$288,75

FONTE: `calculadora_frete.py:342-361` (`_calcular_pedagio_v2`)

### 4.5 Valores Fixos

- `valor_tas`: Taxa de Administracao de Servico (valor fixo por embarque)
- `valor_despacho`: Taxa de despacho (valor fixo por embarque)
- `valor_cte`: Taxa de emissao do CTe (valor fixo por embarque)

Cada um pode ser ANTES ou DEPOIS do frete minimo via flags da transportadora.

FONTE: `calculadora_frete.py:127-144`

---

## Passo 5: Separar Componentes ANTES e DEPOIS

Para cada componente (GRIS, ADV, RCA, pedagio, TAS, despacho, CTE):
- Se `transportadora.aplica_X_pos_minimo = False` → soma em `componentes_antes`
- Se `transportadora.aplica_X_pos_minimo = True` → soma em `componentes_depois`

DEFAULT: Todos ANTES (False)

EXEMPLO com GRIS pos-minimo:
- frete_base = R$200, GRIS = R$50, frete_minimo_valor = R$350
- Se GRIS ANTES: frete_liquido_antes = 200+50 = R$250 → aplica minimo → R$350
- Se GRIS DEPOIS: frete_liquido_antes = R$200 → aplica minimo → R$350 → + R$50 = R$400

FONTE: `calculadora_frete.py:90-144`

---

## Passo 6: Aplicar Frete Minimo VALOR

FORMULA: `frete_apos_minimo = max(frete_base + componentes_antes, frete_minimo_valor)`

**CONFUSAO COMUM**: `frete_minimo_valor` e um VALOR em R$, diferente de `frete_minimo_peso` que e PESO em kg.

EXEMPLO: frete_liquido_antes = R$250, frete_minimo_valor = R$350 → frete_apos_minimo = R$350

FONTE: `calculadora_frete.py:376-382` (`_aplicar_frete_minimo_valor`)

---

## Passo 7: Adicionar Componentes POS-MINIMO

FORMULA: `frete_final_liquido = frete_apos_minimo + componentes_depois`

FONTE: `calculadora_frete.py:152-153`

---

## Passo 8: Aplicar ICMS (se nao incluso)

CONDICAO: Se `icms_incluso = False` E `icms > 0`

FORMULA: `frete_com_icms = frete_final_liquido / (1 - icms)`

Se icms < 1 (decimal, ex: 0.07): divisor = 1 - 0.07 = 0.93
Se icms >= 1 (percentual, ex: 7): divisor = 1 - 7/100 = 0.93

EXEMPLO: R$3.250 / 0.93 = R$3.494,62

Se `icms_incluso = True`: frete_com_icms = frete_final_liquido (sem alteracao)

FONTE: `calculadora_frete.py:384-402` (`_aplicar_icms_final`)

---

## Passo 9: Calcular Valor Liquido

FORMULA:
- Se transportadora OPTANTE (Simples Nacional): `valor_liquido = frete_com_icms`
  (optante nao destaca ICMS, fica com o valor cheio)
- Se transportadora NAO OPTANTE: `valor_liquido = frete_com_icms × (1 - icms)`
  (desconta ICMS que sera recolhido ao estado)

FONTE: `calculadora_frete.py:404-417` (`_calcular_valor_liquido`)

---

## Passo 10: Resultado Final

O calculo retorna 3 valores:
- **valor_bruto**: frete SEM ICMS (para referencia)
- **valor_com_icms**: frete COM ICMS (valor da NF de frete)
- **valor_liquido**: valor que a transportadora efetivamente recebe

---

## Carga DIRETA vs FRACIONADA

### FRACIONADA (tipo_carga='FRACIONADA')
- Calculo DIRETO: cada CNPJ tem seu proprio calculo
- Usado quando: < 26 pallets E < 20.000 kg
- Modalidade geralmente: FRETE PESO

FONTE: `calculadora_frete.py:488-517` (`calcular_frete_carga_fracionada`)

### DIRETA (tipo_carga='DIRETA')
- Usa peso/valor TOTAL do embarque (nao do CNPJ individual)
- Modalidade: veiculo (VAN, TOCO, TRUCK, CARRETA, BITREM)
- Limite de peso: respeitado pela capacidade do veiculo (`Veiculo.peso_maximo`)
- **REGRA "TABELA MAIS CARA"**: quando ha multiplas tabelas para mesma
  (transportadora, UF, modalidade), escolhe a de maior valor_liquido
- **RATEIO**: frete e proporcional ao peso de cada CNPJ
  `frete_cnpj = frete_total × (peso_cnpj / peso_total)`

FONTE: `calculadora_frete.py:432-486` (`calcular_frete_carga_direta`)

---

## Campos que Alteram o Comportamento (Transportadora)

Estes campos ficam na Transportadora (NAO na TabelaFrete):

| Campo | Default | Efeito |
|-------|---------|--------|
| `aplica_gris_pos_minimo` | False | GRIS entra antes/depois do frete minimo |
| `aplica_adv_pos_minimo` | False | ADV entra antes/depois |
| `aplica_rca_pos_minimo` | False | RCA entra antes/depois |
| `aplica_pedagio_pos_minimo` | False | Pedagio entra antes/depois |
| `aplica_tas_pos_minimo` | False | TAS entra antes/depois |
| `aplica_despacho_pos_minimo` | False | Despacho entra antes/depois |
| `aplica_cte_pos_minimo` | False | CTE entra antes/depois |
| `pedagio_por_fracao` | True | Pedagio arredonda para cima ou exato |
| `optante` | False | Se Simples Nacional (afeta ICMS liquido) |

FONTE: `app/transportadoras/models.py:18-29`

---

## Campos da Tabela de Frete (TabelaFreteManager)

Lista centralizada de 18 campos em `app/utils/tabela_frete_manager.py:16-36`:

| Campo | Descricao | Unidade |
|-------|-----------|---------|
| `modalidade` | Tipo de veiculo ou FRETE PESO | texto |
| `nome_tabela` | Nome identificador da tabela | texto |
| `valor_kg` | Preco por kg | R$/kg |
| `percentual_valor` | % sobre valor da mercadoria | % |
| `frete_minimo_valor` | Piso do frete em R$ | R$ |
| `frete_minimo_peso` | Peso minimo para calculo | kg |
| `icms` | ICMS informativo | decimal |
| `percentual_gris` | % GRIS sobre valor | % |
| `gris_minimo` | Valor minimo do GRIS | R$ |
| `pedagio_por_100kg` | Pedagio por fracao de 100kg | R$ |
| `valor_tas` | Taxa fixa TAS | R$ |
| `percentual_adv` | % ADV sobre valor | % |
| `adv_minimo` | Valor minimo do ADV | R$ |
| `percentual_rca` | % RCA sobre valor | % |
| `valor_despacho` | Taxa fixa despacho | R$ |
| `valor_cte` | Taxa fixa CTe | R$ |
| `icms_incluso` | Se ICMS ja esta nos valores | boolean |
| `icms_proprio` | ICMS fixo da tabela | decimal |
