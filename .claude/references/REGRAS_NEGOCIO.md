# Regras de Negocio - Sistema de Fretes

**Ultima Atualizacao**: 07/12/2025
**Uso**: Consultar quando precisar de logica de dominio detalhada

> **NOTA**: As regras CRITICAS de `sincronizado_nf` e `status` estao no `CLAUDE.md` principal.
> Este arquivo contem regras de negocio detalhadas e especificas.

Este documento descreve as regras de negocio especificas do sistema logistico.

---

## Indice

0. [A Empresa: Nacom Goya](#0-a-empresa-nacom-goya)
1. [Grupos Empresariais (por CNPJ)](#1-grupos-empresariais-por-cnpj)
2. [Bonificacao](#2-bonificacao)
3. [Roteirizacao](#3-roteirizacao)
4. [Estoque e Projecao](#4-estoque-e-projecao)
5. [Status de Separacao](#5-status-de-separacao)
6. [Pedidos Pendentes vs Separados](#6-pedidos-pendentes-vs-separados)
7. [Completude de Pedido ("Matar")](#7-completude-de-pedido-matar)
8. [Atraso de Pedido](#8-atraso-de-pedido)
9. [Agendamento](#9-agendamento)
10. [Lead Time (Prazo de Entrega)](#10-lead-time-prazo-de-entrega)
11. [Concentracao de Item no Pedido](#11-concentracao-de-item-no-pedido)
12. [Termos Comuns (Glossario)](#12-termos-comuns-glossario)
13. [Criacao de Separacao](#13-criacao-de-separacao)
14. [Agendamento para Criacao de Separacao](#14-agendamento-para-criacao-de-separacao)

---

## 0. A Empresa: Nacom Goya

### Estrutura do Grupo

```
NACOM GOYA (Empresa Principal)
├── Planta Fabril (Conservas) - Fracionamento
├── CD/Armazem (4.000 pallets) - 2km das fabricas
└── LA FAMIGLIA (Subcontratada)
    ├── Galpao Molhos (6 tanques + 6 envasadoras)
    └── Galpao Oleos
```

### Escala de Operacao

| Metrica | Valor |
|---------|-------|
| Faturamento mensal | ~R$ 16.000.000 |
| Volume mensal | ~1.000.000 kg |
| Pedidos/mes | ~500 |
| Capacidade CD | 4.000 pallets |
| Expedicao maxima/dia | 500 pallets |

### Produtos

| Categoria | Origem | Marcas Proprias |
|-----------|--------|-----------------|
| Conservas | Importadas em bombonas, fracionadas | Campo Belo, La Famiglia, St Isabel, Casablanca, Dom Gameiro |
| Molhos | Produzidos (La Famiglia) | La Famiglia |
| Oleos | Produzidos (La Famiglia) | La Famiglia |

### Top Clientes (75% do faturamento)

| # | Cliente | Tipo | Fat/Mes | % Total | Gestor |
|---|---------|------|---------|---------|--------|
| 1 | **Atacadao** | Atacarejo | R$ 8MM | **50%** | Junior |
| 2 | **Assai** | Atacarejo | R$ 2.1MM | 13% | Junior (SP) / Miler (outros) |
| 3 | Gomes da Costa | Industria | R$ 700K | 4% | Fernando |
| 4 | Mateus | Atacarejo | R$ 500K | 3% | Miler |
| 5 | Dia a Dia | Atacarejo | R$ 350K | 2% | Miler |
| 6 | Tenda | Atacarejo | R$ 350K | 2% | Junior |

**REGRA CRITICA:** Atacadao = 50% do faturamento. Se Atacadao atrasa, a empresa SENTE.

### Estrutura Comercial

```
GESTORES:
├── JUNIOR (~4-5 vendedores) - KEY ACCOUNTS
│   ├── Atacadao (Brasil inteiro)
│   ├── Assai SP (40% do Assai)
│   ├── Tenda (so SP)
│   └── Spani (SP e RJ)
│   └── Contato: WhatsApp
│
├── MILER (~50 vendedores)
│   ├── Brasil EXCETO SP
│   ├── Assai (fora SP), Mateus, Dia a Dia
│   └── Contato: WhatsApp
│
├── FERNANDO (~4-5 vendedores)
│   ├── Industrias (Gomes da Costa, Camil, Seara, Heinz)
│   └── Contato: WhatsApp
│
└── DENISE (2 vendedoras)
    ├── Vendas internas
    └── Contato: Microsoft Teams

PCP:
└── Contato: Microsoft Teams (ou ramal)
└── SLA de resposta: 30 minutos
```

### Gargalos (Ordem de Frequencia)

1. **AGENDAS** (Gargalo #1) - Cliente DEMORA para aprovar agenda
2. **MATERIA-PRIMA** (Gargalo #2) - MP importada com lead time longo
3. **PRODUCAO** (Gargalo #3) - Capacidade de linhas

---

## 1. Grupos Empresariais (por CNPJ)

→ Ver [business.md#grupos-empresariais](../skills/gerindo-expedicao/references/business.md#grupos-empresariais) para prefixos CNPJ e queries SQL.

**Resumo rápido:** Atacadão, Assaí, Tenda - identificados por prefixo CNPJ.

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

→ Ver [glossary.md](../skills/gerindo-expedicao/references/glossary.md) para glossário completo de termos do domínio.

---

## 13. Criacao de Separacao

### 13.1 Prerequisitos Obrigatorios

| Campo | Obrigatorio | Fonte |
|-------|-------------|-------|
| num_pedido | SIM | Usuario informa |
| expedicao | SIM | Usuario informa |
| Tipo (completa/parcial) | SIM | Usuario informa ou deduzir |
| agendamento | CONDICIONAL | Se cliente exige (contatos_agendamento) |
| protocolo | CONDICIONAL | Se cliente exige agendamento |
| agendamento_confirmado | CONDICIONAL | Se cliente exige agendamento |

### 13.2 Validacoes Antes de Criar

**OBRIGATORIO validar:**
1. Pedido existe na CarteiraPrincipal com qtd_saldo > 0
2. Pedido NAO possui separacao existente (sincronizado_nf=False)
3. Estoque disponivel para cada produto

**Se pedido ja tem separacao:**
- Retornar erro com lote_id existente
- Sugerir: "Este pedido ja possui separacao no lote [X]. Deseja adicionar mais itens?"

### 13.3 Calculo de Pallets

**Formula:**
```
pallets = quantidade / palletizacao
```

Onde `palletizacao` vem de CadastroPalletizacao.

**Modos de distribuicao:**

| Modo | Descricao | Calculo |
|------|-----------|---------|
| Proporcional | Distribuir pallets proporcionalmente | `pallets_item = pallets_total * (valor_item / valor_total)` |
| Inteiros | Cada item = numero inteiro de pallets | `qtd = floor(pallets) * palletizacao` |
| Fracionado | Permite pallets fracionados | `qtd = pallets * palletizacao` |

**Priorizacao para pallets inteiros:**
1. Ordenar itens por palletizacao (maior primeiro)
2. Alocar pallets inteiros ate esgotar meta
3. Arredondar ultimo item se necessario

### 13.4 Rota e Incoterm

**Regra de Rota:**
```
Se incoterm IN ('RED', 'FOB'):
    rota = incoterm  # RED ou FOB
Senao:
    rota = buscar_rota_por_uf(cod_uf)
```

**Sub-rota:** Sempre calculada por UF + cidade via CadastroSubRota.

### 13.5 Tipo de Envio

| Tipo | Quando Usar |
|------|-------------|
| `total` | Separando TODOS os itens com TODAS as quantidades |
| `parcial` | Separando alguns itens OU quantidades parciais |

**Calculo automatico:**
```python
Se (produtos_separando == todos_produtos_pedido)
   E (qtds_separando == qtds_totais):
    tipo_envio = 'total'
Senao:
    tipo_envio = 'parcial'
```

### 13.6 Status Inicial

| Situacao | Status Inicial |
|----------|----------------|
| Separacao via agente | ABERTO |
| Pre-separacao (workspace) | PREVISAO |

**Importante:** Separacoes criadas pelo agente vao SEMPRE com status='ABERTO'.

### 13.7 Campos Criados Automaticamente

| Campo | Fonte/Calculo |
|-------|---------------|
| separacao_lote_id | app/utils/lote_utils.py gerar_lote_id() |
| peso | qtd * peso_bruto (CadastroPalletizacao) |
| pallet | qtd / palletizacao (CadastroPalletizacao) |
| valor_saldo | qtd * preco_produto_pedido (CarteiraPrincipal) |
| rota | buscar_rota_por_uf(cod_uf) ou incoterm |
| sub_rota | buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade) |
| sincronizado_nf | False (SEMPRE) |
| criado_em | agora_brasil() |

### 13.8 Validacao de Estoque

**Antes de criar, verificar para cada produto:**
```python
estoque_disponivel = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
                   - SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)

Se estoque_disponivel < quantidade_solicitada:
    ALERTAR usuario
    Sugerir: --apenas-estoque ou excluir produto
```

### 13.9 Modo Apenas Estoque

Quando `--apenas-estoque`:
```python
Para cada produto:
    estoque = calcular_estoque_atual(cod_produto)
    qtd_final = min(qtd_solicitada, estoque)
    Se qtd_final <= 0:
        IGNORAR produto
```

### 13.10 Exclusao de Produtos

Quando `--excluir-produtos '[...]'`:
```python
produtos_excluir = json.loads(excluir_produtos)
Para cada item_carteira:
    Se cod_produto IN produtos_excluir
       OU nome_produto ILIKE qualquer termo em produtos_excluir:
        IGNORAR produto
```

**Match por nome:** Usar sempre resolver_produto localizado em .claude/skills/gerindo-expedicao/scripts/resolver_entidades.py.


---

## 14. Agendamento para Criacao de Separacao

### 14.1 Verificacao Automatica

**SEMPRE verificar antes de criar separacao:**
```sql
SELECT forma, contato, observacao
FROM contatos_agendamento
WHERE cnpj = [cnpj_do_pedido]
```

### 14.2 Resultados Possiveis

| Resultado | Acao |
|-----------|------|
| Nao encontrado | Informar: "Cliente nao precisa de agendamento" |
| forma = 'SEM AGENDAMENTO' | Informar: "Cliente nao precisa de agendamento" |
| forma != 'SEM AGENDAMENTO' | SOLICITAR: agendamento, protocolo, confirmado |

### 14.3 Formas de Agendamento

| Forma | Descricao |
|-------|-----------|
| Portal | Agendamento via portal web do cliente |
| Telefone | Agendamento por ligacao |
| E-mail | Agendamento por e-mail |
| WhatsApp | Agendamento por WhatsApp |

### 14.4 Campos Opcionais

Se usuario NAO informar agendamento/protocolo quando exigido:
- AVISAR que faltam informacoes
- PERMITIR continuar (campos ficam NULL)
- NAO bloquear criacao

Se usuario INFORMAR mesmo quando nao exigido:
- REGISTRAR normalmente (campos serao preenchidos)
