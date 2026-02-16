# Scripts — Resolvendo Entidades (Detalhes)

Referencia detalhada de parametros, retornos e estrategias de resolucao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. resolver_grupo.py

**Proposito:** Resolve grupos empresariais para lista de CNPJs.

```bash
source .venv/bin/activate && \
python .claude/skills/resolvendo-entidades/scripts/resolver_grupo.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--grupo` | Sim | Nome do grupo (atacadao, assai, tenda) | `--grupo atacadao` |
| `--uf` | Nao | Filtrar por UF | `--uf SP` |
| `--loja` | Nao | Filtrar por identificador de loja | `--loja 183` |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) | `--fonte carteira` |

**Retorno:**
```json
{
  "sucesso": true,
  "grupo": "assai",
  "prefixos_cnpj": ["06.057.22"],
  "filtros": {"uf": "SP"},
  "cnpjs": ["06.057.22/0001-XX", "06.057.22/0002-YY"],
  "total": 15
}
```

**Grupos mapeados:**

| Grupo | Prefixos CNPJ | Aliases |
|-------|---------------|---------|
| `atacadao` | 93.209.76, 75.315.33, 00.063.96 | Carrefour Atacadao |
| `assai` | 06.057.22 | Assai Atacadista |
| `tenda` | 01.157.55 | Tenda Atacado |

---

## 2. resolver_cliente.py

**Proposito:** Resolve cliente nao-grupo por CNPJ parcial ou nome.

```bash
source .venv/bin/activate && \
python .claude/skills/resolvendo-entidades/scripts/resolver_cliente.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--termo` | Sim | CNPJ parcial ou nome do cliente | `--termo Carrefour`, `--termo "45.543.915"` |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) | `--fonte carteira` |
| `--limite` | Nao | Maximo de resultados (default: 50) | `--limite 20` |

**Retorno:**
```json
{
  "sucesso": true,
  "termo": "Carrefour",
  "estrategia": "NOME_PARCIAL",
  "clientes": [
    {"cnpj": "45.543.915/0001-XX", "nome": "CARREFOUR CENTRO", "cidade": "SAO PAULO", "uf": "SP"}
  ],
  "total": 3
}
```

---

## 3. resolver_produto.py

**Proposito:** Resolve produto por termo ou abreviacao.

```bash
source .venv/bin/activate && \
python .claude/skills/resolvendo-entidades/scripts/resolver_produto.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--termo` | Sim | Nome, abreviacao ou caracteristica do produto | `--termo palmito`, `--termo "AZ VF"` |
| `--limite` | Nao | Maximo de resultados (default: 50) | `--limite 20` |

**Retorno:**
```json
{
  "sucesso": true,
  "termo": "palmito",
  "produtos": [
    {"cod_produto": "PAL001", "nome_produto": "PALMITO PUPUNHA 300G", "score": 8}
  ],
  "total": 15
}
```

**Abreviacoes conhecidas:**

| Abreviacao | Campo | Valor | Descricao |
|------------|-------|-------|-----------|
| CI | tipo_materia_prima | CI | Cogumelo Inteiro |
| CF | tipo_materia_prima | CF | Cogumelo Fatiado |
| AZ VF | tipo_materia_prima | AZ VF | Azeitona Verde Fatiada |
| AZ PF | tipo_materia_prima | AZ PF | Azeitona Preta Fatiada |
| AZ VI | tipo_materia_prima | AZ VI | Azeitona Verde Inteira |
| AZ PI | tipo_materia_prima | AZ PI | Azeitona Preta Inteira |
| BD | tipo_embalagem | BD% | Balde |
| VD | tipo_embalagem | VIDRO% | Vidro |
| BR | tipo_embalagem | BARRICA | Barrica |
| GL | tipo_embalagem | GALAO% | Galao |
| MEZZANI | categoria_produto | MEZZANI | Marca Mezzani |
| CAMPO BELO | categoria_produto | CAMPO BELO | Marca Campo Belo |
| IND | categoria_produto | INDUSTRIA | Destinado a industria |

---

## 4. resolver_pedido.py

**Proposito:** Resolve pedido por numero parcial ou termo.

```bash
source .venv/bin/activate && \
python .claude/skills/resolvendo-entidades/scripts/resolver_pedido.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--termo` | Sim | Numero parcial ou termo de busca | `--termo VCD123` |
| `--fonte` | Nao | carteira, separacao, ambos (default: ambos) | `--fonte carteira` |

**Retorno:**
```json
{
  "sucesso": true,
  "termo": "VCD123",
  "estrategia": "NUMERO_PARCIAL",
  "pedidos": [
    {"num_pedido": "VCD1234567", "cliente": "ATACADAO 183", "cnpj": "93.209.76/0001-XX"}
  ],
  "multiplos": true,
  "total": 5
}
```

**Se `multiplos: true`**: Apresentar opcoes ao usuario via AskUserQuestion.

---

## 5. resolver_cidade.py

**Proposito:** Resolve cidade com normalizacao de acentos.

```bash
source .venv/bin/activate && \
python .claude/skills/resolvendo-entidades/scripts/resolver_cidade.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--cidade` | Sim | Nome da cidade (com ou sem acentos) | `--cidade itanhaem` |
| `--fonte` | Nao | carteira, separacao, entregas (default: entregas) | `--fonte carteira` |

**Nota:** CarteiraPrincipal NAO tem `codigo_ibge`. Usa `nome_cidade` + `cod_uf` para resolver.

---

## 6. resolver_uf.py

**Proposito:** Resolve UF para lista de CNPJs/pedidos.

```bash
source .venv/bin/activate && \
python .claude/skills/resolvendo-entidades/scripts/resolver_uf.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--uf` | Sim | Sigla do estado (2 letras) | `--uf SP` |

---

## Exemplos de Uso

### Cenario 1: Resolver grupo antes de consultar entregas
```
Pergunta: "entregas pendentes do Assai de SP"
Passo 1: resolver_grupo.py --grupo assai --uf SP --fonte entregas
  → {"prefixos_cnpj": ["06.057.22"], "total": 15}
Passo 2: monitorando-entregas → --cnpj "06.057.22" --pendentes
```

### Cenario 2: Resolver produto por abreviacao
```
Pergunta: "tem AZ VF na carteira do Atacadao?"
Passo 1: resolver_produto.py --termo "AZ VF"
  → {"produtos": [{"cod_produto": "AZ001", "nome": "AZEITONA VERDE FATIADA"}]}
Passo 2: resolver_grupo.py --grupo atacadao
  → {"prefixos_cnpj": ["93.209.76", "75.315.33", "00.063.96"]}
Passo 3: gerindo-expedicao com filtros resolvidos
```

### Cenario 3: Multiplos pedidos
```
Pergunta: "pedido 123"
Passo 1: resolver_pedido.py --termo 123
  → {"multiplos": true, "pedidos": ["VCD1234", "VCD5123", "VFB123"]}
Acao: Perguntar ao usuario qual pedido deseja.
```
