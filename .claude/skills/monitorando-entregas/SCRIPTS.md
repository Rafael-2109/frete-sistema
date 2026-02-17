# Scripts — Monitorando Entregas (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. consultando_status_entrega.py

**Proposito:** Consulta status de entregas monitoradas (tabela `monitoramento_entregas`). Suporta filtros por NF, cliente, CNPJ, transportadora, status e periodo.

```bash
source .venv/bin/activate && \
python .claude/skills/monitorando-entregas/scripts/consultando_status_entrega.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--nf` | Numero da NF (busca parcial ILIKE) | `--nf 12345` |
| `--cliente` | Nome do cliente (busca parcial ILIKE) | `--cliente "Atacadao"` |
| `--cnpj` | CNPJ do cliente (formatado ou nao) | `--cnpj "45.543.915"` |
| `--transportadora` | Nome da transportadora (busca parcial ILIKE) | `--transportadora "Braspress"` |
| `--pendentes` | Apenas pendentes (status_finalizacao IS NULL) | flag |
| `--entregues` | Apenas entregues (status_finalizacao = 'Entregue') | flag |
| `--no-cd` | Apenas NFs no CD (nf_cd = true) | flag |
| `--reagendadas` | Apenas reagendadas (reagendar = true) | flag |
| `--problemas` | Com problema (nf_cd = true OR reagendar = true) | flag |
| `--de` | Data inicial do periodo (YYYY-MM-DD) | `--de 2025-01-01` |
| `--ate` | Data final do periodo (YYYY-MM-DD) | `--ate 2025-01-31` |
| `--limite` | Maximo de registros (default: 50) | `--limite 20` |
| `--formato` | Formato de saida: `json` ou `tabela` (default: json) | `--formato tabela` |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "total": 150,
  "exibindo": 50,
  "filtros_aplicados": {"pendentes": true},
  "entregas": [{"numero_nf": "12345", "cliente": "...", "status_finalizacao": null}]
}
```

---

## 2. consultando_devolucoes.py

**Proposito:** Consulta devolucoes (tabela `nf_devolucao`) com ocorrencias relacionadas (LEFT JOIN `ocorrencia_devolucao`).

```bash
source .venv/bin/activate && \
python .claude/skills/monitorando-entregas/scripts/consultando_devolucoes.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--nf` | Numero da NF original (busca parcial ILIKE) | `--nf 12345` |
| `--nfd` | Numero da NFD (busca parcial ILIKE) | `--nfd 67890` |
| `--cliente` | Nome do cliente/emitente (busca parcial ILIKE) | `--cliente "Atacadao"` |
| `--abertas` | Apenas ocorrencias abertas (status IN ABERTA, EM_ANALISE, AGUARDANDO_RETORNO) | flag |
| `--de` | Data inicial (YYYY-MM-DD) | `--de 2025-01-01` |
| `--ate` | Data final (YYYY-MM-DD) | `--ate 2025-12-31` |
| `--limite` | Maximo de registros (default: 50) | `--limite 20` |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "total": 30,
  "exibindo": 30,
  "devolucoes": [{"numero_nfd": "...", "status_nfd": "...", "status_ocorrencia": "ABERTA"}]
}
```

---

## 3. consultando_devolucoes_detalhadas.py

**Proposito:** Consulta devolucoes com entity resolution detalhada. 4 modos mutuamente exclusivos: por cliente, por produto, ranking de produtos e custo total.

```bash
source .venv/bin/activate && \
python .claude/skills/monitorando-entregas/scripts/consultando_devolucoes_detalhadas.py [parametros]
```

**Parametros de modo (mutuamente exclusivos, um obrigatorio):**

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--cliente` | Historico de devolucoes por cliente (ILIKE no nome) | `--cliente "Sendas"` |
| `--produto` | Produtos devolvidos (ILIKE no nome do produto) | `--produto "palmito"` |
| `--ranking` | Top N produtos mais devolvidos | flag |
| `--custo` | Custo total de devolucoes (via despesas_extras) | flag |

**Parametros gerais:**

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--de` | Data inicio (YYYY-MM-DD) | `--de 2025-01-01` |
| `--ate` | Data fim (YYYY-MM-DD) | `--ate 2025-12-31` |
| `--limite` | Max resultados (default: 50) | `--limite 10` |
| `--incluir-custo` | Incluir custo de devolucao (apenas com --cliente) | flag |
| `--ordenar-por` | Criterio de ordenacao do ranking: `ocorrencias` ou `quantidade` (default: ocorrencias) | `--ordenar-por quantidade` |

**Modos de operacao:**

| Modo | Parametro | Retorno principal |
|------|-----------|-------------------|
| Cliente | `--cliente` | Lista de NFDs do cliente + resumo (total, valor) + custo opcional |
| Produto | `--produto` | Linhas de devolucao com produto + resumo (ocorrencias, clientes) |
| Ranking | `--ranking` | Top N produtos por ocorrencias ou quantidade |
| Custo | `--custo` | Custo total + breakdown mensal via despesas_extras (tipo=DEVOLUCAO) |

**Retorno JSON (varia por modo):**
```json
{
  "sucesso": true,
  "modo": "ranking",
  "resumo": {"mensagem": "Top 10 produtos...", "criterio": "ocorrencias"},
  "ranking": [{"produto_referencia": "...", "total_ocorrencias": 15}]
}
```
