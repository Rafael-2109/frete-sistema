---
name: resolvendo-entidades
description: >-
  Esta skill deve ser usada SEMPRE ANTES de invocar skills que aceitam
  parametro de cliente, produto, pedido, cidade ou transportadora quando o
  usuario fornece nome generico em vez de identificador exato. Resolve
  "Atacadao" para CNPJs, "palmito" para cod_produto, "VCD123" para num_pedido,
  "Manaus" para codigo IBGE e UF, "TAC" ou "Transmerc" para transportadora_id.
  Nao usar quando o usuario fornece identificador exato (CNPJ completo,
  cod_produto numerico, num_pedido com prefixo VCD/VFB, transportadora_id).

  NAO USAR quando usuario fornece ID exato (CNPJ completo, cod_produto, num_pedido, transportadora_id).
allowed-tools: Read, Bash, Glob, Grep
---

# Resolvendo Entidades

Skill dedicada a resolver termos humanos para identificadores do sistema.

---

## Indice

1. [CRITICO: Quando Usar Esta Skill](#critico-quando-usar-esta-skill)
2. [Regras de Fidelidade ao Output](#regras-de-fidelidade-ao-output)
3. [Fluxo Obrigatorio](#fluxo-obrigatorio)
4. [Mapeamento: Qual Script Usar?](#mapeamento-qual-script-usar)
5. [Scripts Disponiveis](#scripts-disponiveis)
6. [Regras de Negocio](#regras-de-negocio)
7. [Tratamento de Resultados Vazios e Ambiguidade](#tratamento-de-resultados-vazios-e-ambiguidade)
8. [Referencias Cruzadas](#referencias-cruzadas)
9. [References](#references)

---

## CRITICO: Quando Usar Esta Skill

**OBRIGATORIO usar ANTES de qualquer skill que aceite entidades do dominio.**

As entidades transitam por MULTIPLAS tabelas do sistema:

| Entidade | Tabelas onde existe |
|----------|---------------------|
| **CLIENTE (CNPJ)** | CarteiraPrincipal, Separacao, EmbarqueItem, Frete, EntregasMonitoradas, NFDevolucao, FaturamentoProduto |
| **PRODUTO** | CadastroPalletizacao, CarteiraPrincipal, Separacao, MovimentacaoEstoque, UnificacaoCodigos |
| **PEDIDO** | CarteiraPrincipal, Separacao, EmbarqueItem |
| **TRANSPORTADORA** | transportadoras, fretes, carvia_subcontratos |

Sem resolver primeiro, o agente alucina ou falha em consultas.

---

## Regras de Fidelidade ao Output

### OBRIGATORIO — Anti-Alucinacao

```
REGRA F1: NUNCA inventar dados que nao estejam no JSON de retorno do script.
         Se o script retornou 3 CNPJs, apresentar EXATAMENTE 3 — nao 4, nao 2.

REGRA F2: NUNCA completar numeros parciais por conta propria.
         Se o script retornou "VCD2565291", apresentar "VCD2565291" — nao "VCD256529100".

REGRA F3: NUNCA inferir relacoes nao retornadas pelo script.
         Se resolver_grupo retornou CNPJs, NAO assumir quais lojas pertencem a cada CNPJ
         sem ter os dados do campo "clientes" no output.

REGRA F4: Quando sucesso=false, reportar HONESTAMENTE.
         Dizer "nao encontrado" e repetir a sugestao do campo "sugestao" do JSON.
         NAO especular motivos ou inventar dados alternativos.

REGRA F5: Valores numericos (total, score, similaridade) devem ser citados
         EXATAMENTE como retornados pelo script. NAO arredondar ou estimar.
```

### Fidelidade na Apresentacao

- **Sempre citar a fonte**: "Segundo o script resolver_grupo.py, o grupo Atacadao tem X CNPJs em SP"
- **Sempre informar total vs exibindo**: Se total=50 mas exibindo=20, dizer "Mostrando 20 de 50 resultados"
- **Sempre informar estrategia usada**: Se estrategia=NOME_PARCIAL, mencionar que foi busca por nome

---

## Fluxo Obrigatorio

```
1. Usuario: "entregas do Assai de SP"
            ↓
2. RESOLVER PRIMEIRO:
   resolver_grupo.py --grupo assai --uf SP
   → {"sucesso": true, "prefixos_cnpj": ["06.057.22"], "total": 15}
            ↓
3. ENTAO CONSULTAR:
   consultando_status_entrega.py --cnpj "06.057.22"
```

### Quando NAO Resolver

**NAO usar esta skill se usuario ja forneceu:**
- CNPJ completo: `06.057.22/0001-XX`
- cod_produto exato: `AZ001`
- num_pedido exato: `VCD2565291`
- transportadora_id numerico: `42`

---

## Mapeamento: Qual Script Usar?

### Tabela de Decisao Rapida

| Se o usuario menciona... | Script | Exemplo de Uso |
|--------------------------|--------|----------------|
| "Atacadao", "Assai", "Tenda" | `resolver_grupo.py --grupo X` | `--grupo atacadao` |
| "Atacadao de SP" | `resolver_grupo.py --grupo X --uf Y` | `--grupo atacadao --uf SP` |
| "Atacadao loja 183" | `resolver_grupo.py --grupo X --loja Y` | `--grupo atacadao --loja 183` |
| "Carrefour", cliente nao-grupo | `resolver_cliente.py --termo X` | `--termo Carrefour` |
| "CNPJ 45.543.915" | `resolver_cliente.py --termo X` | `--termo 45.543.915` |
| "palmito", "azeitona" | `resolver_produto.py --termo X` | `--termo palmito` |
| "CI", "AZ VF" (abreviacao) | `resolver_produto.py --termo X` | `--termo "AZ VF"` |
| "palmito balde mezzani" (composto) | `resolver_produto.py --termo X` | `--termo "palmito balde mezzani"` |
| "VCD123", parte de pedido | `resolver_pedido.py --termo X` | `--termo VCD123` |
| "Sao Paulo", cidade | `resolver_cidade.py --cidade X` | `--cidade "Sao Paulo"` |
| "SP", "RJ" (UF) | `resolver_uf.py --uf X` | `--uf SP` |
| "TAC", "Transmerc" (transportadora) | `resolver_transportadora.py --termo X` | `--termo TAC` |

### Regras de Decisao

1. **Se menciona grupo empresarial conhecido (Atacadao, Assai, Tenda):**
   → `resolver_grupo.py`

2. **Se menciona cliente desconhecido ou CNPJ parcial:**
   → `resolver_cliente.py`

3. **Se menciona produto por nome/abreviacao:**
   → `resolver_produto.py`

4. **Se menciona pedido por numero parcial:**
   → `resolver_pedido.py`

5. **Se menciona cidade ou UF:**
   → `resolver_cidade.py` ou `resolver_uf.py`

6. **Se menciona transportadora por nome ou CNPJ parcial:**
   → `resolver_transportadora.py`

---

## Scripts Disponiveis

### 1. resolver_grupo.py

Resolve grupos empresariais para lista de CNPJs.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_grupo.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--grupo` | Sim | Nome do grupo (atacadao, assai, tenda) |
| `--uf` | Nao | Filtrar por UF (SP, RJ, etc.) |
| `--loja` | Nao | Filtrar por identificador de loja (183, CENTRO) |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) |

**Retorno:**
```json
{
  "sucesso": true,
  "grupo": "assai",
  "prefixos_cnpj": ["06.057.22"],
  "filtros_aplicados": {"uf": "SP"},
  "cnpjs": ["06.057.22/0001-XX", "06.057.22/0002-YY"],
  "clientes": [{"cnpj": "...", "nome": "...", "cidade": "...", "uf": "..."}],
  "total": 15,
  "exibindo": 15
}
```

**Erro quando grupo desconhecido:**
```json
{
  "sucesso": false,
  "erro": "Grupo 'xyz' nao encontrado",
  "grupos_disponiveis": ["atacadao", "assai", "tenda"]
}
```

### 2. resolver_cliente.py

Resolve cliente nao-grupo por CNPJ parcial ou nome.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_cliente.py --termo "Carrefour"
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--termo` | Sim | CNPJ parcial ou nome do cliente |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) |
| `--limite` | Nao | Maximo de resultados (default: 50) |

**Retorno:**
```json
{
  "sucesso": true,
  "termo_original": "Carrefour",
  "estrategia": "NOME_PARCIAL",
  "clientes": [
    {"cnpj": "45.543.915/0001-XX", "nome": "CARREFOUR CENTRO", "cidade": "SAO PAULO", "uf": "SP"}
  ],
  "total": 3,
  "fonte": "entregas"
}
```

**NOTA**: Para grupos (Atacadao, Assai, Tenda), use `resolver_grupo.py` — NAO `resolver_cliente.py`.

### 3. resolver_produto.py

Resolve produto por termo, abreviacao ou combinacao de termos.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_produto.py --termo "palmito" [--modo hibrida]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--termo` | Sim | Nome, abreviacao ou caracteristica do produto |
| `--limite` | Nao | Maximo de resultados (default: 50) |
| `--modo` | Nao | `texto` (ILIKE), `semantica` (embeddings), `hibrida` (ambos, default) |

**Busca composta**: Termos sao tokenizados. "AZ VF mezzani balde" → detecta abreviacao AZ VF + filtra por mezzani + tipo_embalagem balde.

**Retorno:**
```json
{
  "sucesso": true,
  "termo_original": "palmito",
  "modo": "hibrida",
  "abreviacoes_detectadas": ["Azeitona Verde Fatiada"],
  "produtos": [
    {
      "cod_produto": "PAL001",
      "nome_produto": "PALMITO PUPUNHA 300G",
      "tipo_embalagem": "VIDRO",
      "tipo_materia_prima": "PP",
      "categoria_produto": "CAMPO BELO",
      "score": 8,
      "source": "texto"
    }
  ],
  "total": 15
}
```

### 4. resolver_pedido.py

Resolve pedido por numero parcial ou termo. Busca em 5 estrategias automaticas.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_pedido.py --termo "VCD123"
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--termo` | Sim | Numero parcial, CNPJ, grupo+loja, ou nome cliente |
| `--fonte` | Nao | carteira, separacao, ambos (default: ambos) |

**Estrategias (em ordem de prioridade):**
1. `NUMERO_EXATO` — Num pedido exato
2. `NUMERO_PARCIAL` — Num pedido LIKE
3. `CNPJ_DIRETO` — CNPJ do cliente
4. `GRUPO_LOJA` — Grupo empresarial + loja (ex: "atacadao 183")
5. `CLIENTE_PARCIAL` — Nome parcial do cliente

**Retorno:**
```json
{
  "sucesso": true,
  "termo_original": "VCD123",
  "estrategia": "NUMERO_PARCIAL",
  "pedidos": [
    {"num_pedido": "VCD1234567", "cnpj": "93.209.76/0001-XX", "cliente": "ATACADAO 183", "cidade": "SP", "uf": "SP", "fonte": "carteira"}
  ],
  "multiplos": true,
  "total": 5
}
```

**IMPORTANTE**: Quando `multiplos=true`, SEMPRE apresentar opcoes ao usuario para escolha.

### 5. resolver_cidade.py

Resolve cidade com normalizacao de acentos.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_cidade.py --cidade "itanhaem"
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--cidade` | Sim | Nome da cidade (com ou sem acentos) |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) |

**Retorno:**
```json
{
  "sucesso": true,
  "cidade_original": "itanhaem",
  "termo_normalizado": "itanhaem",
  "cidades_encontradas": [{"cidade": "ITANHAEM", "uf": "SP"}],
  "clientes": [{"cnpj": "...", "nome": "...", "cidade": "ITANHAEM", "uf": "SP"}],
  "total": 5,
  "fonte": "entregas"
}
```

### 6. resolver_uf.py

Resolve UF para lista de CNPJs/pedidos.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_uf.py --uf SP
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--uf` | Sim | Sigla da UF (SP, RJ, etc.) — valida contra lista de 27 UFs |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) |

**Retorno:**
```json
{
  "sucesso": true,
  "uf": "SP",
  "clientes": [{"cnpj": "...", "nome": "...", "cidade": "...", "uf": "SP"}],
  "cidades": ["CAMPINAS", "SAO PAULO", "SOROCABA"],
  "total": 150,
  "exibindo": 100,
  "fonte": "entregas"
}
```

### 7. resolver_transportadora.py

Resolve transportadora por nome parcial ou CNPJ.

```bash
source .venv/bin/activate && python .claude/skills/resolvendo-entidades/scripts/resolver_transportadora.py --termo "TAC"
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--termo` | Sim | Nome parcial ou CNPJ (minimo 2 caracteres) |
| `--limite` | Nao | Maximo de resultados (default: 10) |

**Estrategias (em ordem de prioridade):**
1. `CNPJ` — Se termo tem 8+ digitos, busca por CNPJ
2. `SEMANTICO` — Busca via embeddings Voyage AI (se disponivel)
3. `ILIKE` — Busca textual por razao_social (fallback)

**Retorno:**
```json
{
  "sucesso": true,
  "termo_original": "TAC",
  "estrategia": "ILIKE",
  "transportadoras": [
    {"id": 42, "cnpj": "12.345.678/0001-00", "razao_social": "TAC TRANSPORTES", "cidade": "SP", "uf": "SP", "ativo": true}
  ],
  "total": 1
}
```

**NOTA**: Campo da tabela e `razao_social` (NAO `nome`). Tabela e `transportadoras` (com s).

---

## Regras de Negocio

### Grupos Empresariais Mapeados

| Grupo | Prefixos CNPJ | Aliases |
|-------|---------------|---------|
| `atacadao` | 93.209.76, 75.315.33, 00.063.96 | Carrefour Atacadao |
| `assai` | 06.057.22 | Assai Atacadista |
| `tenda` | 01.157.55 | Tenda Atacado |

### Abreviacoes de Produto

| Abreviacao | Campo | Valor | Descricao |
|------------|-------|-------|-----------|
| CI | tipo_materia_prima | CI | Cogumelo Inteiro |
| CF | tipo_materia_prima | CF | Cogumelo Fatiado |
| AZ VF | tipo_materia_prima | AZ VF | Azeitona Verde Fatiada |
| AZ PF | tipo_materia_prima | AZ PF | Azeitona Preta Fatiada |
| AZ VI | tipo_materia_prima | AZ VI | Azeitona Verde Inteira |
| AZ PI | tipo_materia_prima | AZ PI | Azeitona Preta Inteira |
| AZ VR | tipo_materia_prima | AZ VR | Azeitona Verde Recheada |
| AZ VSC | tipo_materia_prima | AZ VSC | Azeitona Verde Sem Caroco |
| BD | tipo_embalagem | BD% | Balde |
| VD | tipo_embalagem | VIDRO% | Vidro |
| BR | tipo_embalagem | BARRICA | Barrica |
| GL | tipo_embalagem | GALAO% | Galao |
| POUCH | tipo_embalagem | POUCH% | Pouch |
| SACHET | tipo_embalagem | SACHET% | Sachet |
| MEZZANI | categoria_produto | MEZZANI | Marca Mezzani |
| CAMPO BELO | categoria_produto | CAMPO BELO | Marca Campo Belo |
| BENASSI | categoria_produto | BENASSI | Marca Benassi |
| IMPERIAL | categoria_produto | IMPERIAL | Marca Imperial |
| IND | categoria_produto | INDUSTRIA | Destinado a industria |

### O Agente PODE Afirmar

- CNPJs de um grupo empresarial **retornados pelo script**
- Produtos que casam com termo de busca **retornados pelo script**
- Pedidos que casam com numero parcial **retornados pelo script**
- Clientes encontrados por nome/CNPJ **retornados pelo script**
- Transportadoras encontradas **retornadas pelo script**

### O Agente NAO PODE Inventar

- CNPJs de grupos nao mapeados
- Produtos sem match no CadastroPalletizacao
- Pedidos inexistentes
- Abreviacoes nao documentadas
- Transportadoras nao retornadas pelo script
- Relacoes entre entidades nao retornadas (ex: "esse CNPJ e da loja 183")

---

## Tratamento de Resultados Vazios e Ambiguidade

### Resultado Vazio (sucesso=false)

Quando o script retorna `sucesso: false`:

1. **Reportar honestamente**: "Nao encontrei [entidade] com o termo '[termo]'"
2. **Mostrar sugestao do script**: campo `sugestao` do JSON, se existir
3. **Mostrar alternativas do script**: campo `grupos_disponiveis` ou `ufs_validas`, se existir
4. **NAO especular**: Nao dizer "talvez o nome esteja errado" — apenas reportar o fato
5. **NAO tentar fallback criativo**: Nao rodar outro script tentando adivinhar o que o usuario quis

### Resultado Ambiguo (multiplos=true ou total > 1)

Quando o script retorna multiplos resultados:

1. **Sempre apresentar opcoes ao usuario**: Listar os resultados para o usuario escolher
2. **Maximo de 10 opcoes visualmente**: Se total > 10, mostrar top 10 e informar "mais X resultados"
3. **Formato da opcao**: `num_pedido (cliente, cidade/UF)` ou `nome_produto (cod_produto, tipo_embalagem)`
4. **Perguntar**: "Qual destes voce quer?" ou "Qual opcao?"
5. **NAO escolher pelo usuario**: Mesmo que 1 resultado pareca "obvio", apresentar para confirmacao
   - Excecao: se total=1, pode prosseguir diretamente

### Resultado Parcial (exibindo < total)

Quando `exibindo < total`:
1. Informar: "Mostrando X de Y resultados"
2. Se usuario precisa de mais: sugerir filtro adicional (--uf, --loja, etc.)

---

## Referencias Cruzadas

### Skills que PRECISAM de Resolucao

| Skill | Parametros que precisam resolver |
|-------|----------------------------------|
| `gerindo-expedicao` | --grupo, --cliente, --produto, --pedido |
| `monitorando-entregas` | --cliente, --cnpj |
| `consultando-sql` | Qualquer filtro de entidade na query |
| `rastreando-odoo` | --partner (nome de parceiro) |
| `cotando-frete` | --cidade (destino da cotacao) |
| `gerindo-carvia` | --transportadora (nome da transportadora) |

### Quando Delegar para Outra Skill

| Situacao | Skill a usar |
|----------|--------------|
| Apos resolver, consultar pedidos/estoque | `gerindo-expedicao` |
| Apos resolver, consultar entregas | `monitorando-entregas` |
| Apos resolver, consultar SQL | `consultando-sql` |
| Apos resolver, rastrear no Odoo | `rastreando-odoo` |
| Apos resolver, cotar frete | `cotando-frete` |
| Apos resolver, consultar subcontratos | `gerindo-carvia` |

---

## References

| Gatilho na Pergunta | Reference a Ler | Motivo |
|---------------------|-----------------|--------|
| "quais grupos existem?" | `references/grupos_empresariais.md` | Lista completa de grupos e CNPJs |
| "abreviacoes de produto" | `references/abreviacoes_produto.md` | Mapeamento completo |
| "onde esta a entidade X?" | `references/entidades_por_tabela.md` | Tabelas que contem cada entidade |

---

## Exemplos de Uso

### Cenario 1: Resolver grupo antes de consultar entregas

```
Pergunta: "entregas pendentes do Assai de SP"

Passo 1 - Resolver:
   resolver_grupo.py --grupo assai --uf SP --fonte entregas
   → {"prefixos_cnpj": ["06.057.22"], "total": 15}

Passo 2 - Consultar:
   consultando_status_entrega.py --cnpj "06.057.22" --pendentes
   → {"total": 8, "entregas": [...]}

Resposta: "Segundo o script, o Assai tem 15 CNPJs em SP (prefixo 06.057.22).
           Encontrei 8 entregas pendentes."
```

### Cenario 2: Resolver produto por abreviacao composta

```
Pergunta: "tem AZ VF em balde na carteira do Atacadao?"

Passo 1 - Resolver produto:
   resolver_produto.py --termo "AZ VF balde"
   → {"abreviacoes_detectadas": ["Azeitona Verde Fatiada", "Balde"],
      "produtos": [{"cod_produto": "AZ001", "nome_produto": "AZEITONA VERDE FATIADA BD 2KG"}]}

Passo 2 - Resolver grupo:
   resolver_grupo.py --grupo atacadao
   → {"prefixos_cnpj": ["93.209.76", "75.315.33", "00.063.96"]}

Passo 3 - Consultar:
   (usar gerindo-expedicao com filtros resolvidos)
```

### Cenario 3: Multiplos resultados — PERGUNTAR ao usuario

```
Pergunta: "pedido 123"

Passo 1 - Resolver:
   resolver_pedido.py --termo 123
   → {"multiplos": true, "pedidos": [
       {"num_pedido": "VCD1234", "cliente": "ATACADAO 183"},
       {"num_pedido": "VCD5123", "cliente": "ASSAI GUARULHOS"},
       {"num_pedido": "VFB123", "cliente": "TENDA CENTRO"}
     ], "total": 3}

Resposta: "Encontrei 3 pedidos com '123'. Qual voce quer?
   1. VCD1234 (Atacadao 183)
   2. VCD5123 (Assai Guarulhos)
   3. VFB123 (Tenda Centro)"
```

### Cenario 4: Resultado vazio — reportar honestamente

```
Pergunta: "CNPJs do grupo Walmart"

Passo 1 - Resolver:
   resolver_grupo.py --grupo walmart
   → {"sucesso": false, "erro": "Grupo 'walmart' nao encontrado",
      "grupos_disponiveis": ["atacadao", "assai", "tenda"]}

Resposta: "O grupo 'Walmart' nao esta mapeado no sistema.
           Grupos disponiveis: Atacadao, Assai, Tenda.
           Para buscar por nome de cliente, use resolver_cliente.py."
```

### Cenario 5: Resolver transportadora

```
Pergunta: "qual o CNPJ da transportadora TAC?"

Passo 1 - Resolver:
   resolver_transportadora.py --termo TAC
   → {"sucesso": true, "estrategia": "ILIKE",
      "transportadoras": [{"id": 42, "cnpj": "12.345.678/0001-00",
                           "razao_social": "TAC TRANSPORTES", "ativo": true}]}

Resposta: "Encontrei 1 transportadora: TAC TRANSPORTES (CNPJ: 12.345.678/0001-00, ativa)."
```
