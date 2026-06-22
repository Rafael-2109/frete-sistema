<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/skills/gerindo-expedicao/SKILL.md
superseded_by: —
atualizado: 2026-06-22
-->
# Scripts — Gerindo Expedicao (Detalhes)

> **Papel:** Scripts — Gerindo Expedicao (Detalhes).

## Indice

- [Ambiente Virtual](#ambiente-virtual)
- [1. analisando_disponibilidade_estoque.py](#1-analisando_disponibilidade_estoquepy)
- [2. consultando_situacao_pedidos.py](#2-consultando_situacao_pedidospy)
- [3. consultando_produtos_estoque.py](#3-consultando_produtos_estoquepy)
- [4. calculando_leadtime_entrega.py](#4-calculando_leadtime_entregapy)
- [5. criando_separacao_pedidos.py](#5-criando_separacao_pedidospy)
- [6. consultando_programacao_producao.py](#6-consultando_programacao_producaopy)
- [7. resolver_entidades.py](#7-resolver_entidadespy)
- [8. analisando_carteira_completa.py](#8-analisando_carteira_completapy)
- [9. gerar_embarque.py](#9-gerar_embarquepy)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. analisando_disponibilidade_estoque.py

**Proposito:** Analisa disponibilidade de estoque para pedidos ou grupos de clientes.

**Queries cobertas:** Q1, Q2, Q3, Q4, Q5, Q6, Q9, Q11, Q12

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou "grupo termo" | `--pedido VCD123` ou `--pedido "atacadao 183"` |
| `--grupo` | Grupo empresarial | `--grupo atacadao`, `--grupo assai`, `--grupo tenda` |
| `--loja` | Identificador da loja (em raz_social_red) | `--loja 183` |
| `--uf` | Filtrar por UF | `--uf SP` |
| `--data` | Data para analise (hoje, amanha, dd/mm, YYYY-MM-DD) | `--data amanha` |
| `--sem-agendamento` | Apenas pedidos sem exigencia de agendamento | flag |
| `--sugerir-adiamento` | Sugerir pedidos para adiar (liberar estoque) | flag |
| `--diagnosticar-origem` | Distinguir falta absoluta vs relativa | flag |
| `--completude` | Calcular % faturado vs pendente | flag |
| `--atrasados` | Analisar pedidos com expedicao vencida | flag |
| `--diagnosticar-causa` | Detalhar causa do atraso | flag |
| `--ranking-impacto` | Ranking de pedidos que mais travam carteira | flag |
| `--limit` | Limite de resultados (default: 100) | `--limit 20` |

---

## 2. consultando_situacao_pedidos.py

**Proposito:** Consulta pedidos por diversos filtros e perspectivas.

**Queries cobertas:** Q8, Q10, Q14, Q16, Q19

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou termo de busca | `--pedido VCD123` |
| `--grupo` | Grupo empresarial (atacadao, assai, tenda) | `--grupo atacadao` |
| `--cliente` | CNPJ ou nome parcial do cliente | `--cliente Carrefour`, `--cliente "45.543.915"` |
| `--produto` | Filtrar por produto (combina com --grupo ou --cliente) | `--produto palmito` |
| `--atrasados` | Listar pedidos atrasados | flag |
| `--verificar-bonificacao` | Verificar bonificacoes faltando | flag |
| `--status` | Mostrar status detalhado | flag |
| `--consolidar-com` | Buscar pedidos para consolidar | `--consolidar-com "assai 123"` |
| `--ate-data` | Data limite de expedicao | `--ate-data amanha`, `--ate-data 15/12` |
| `--em-separacao` | Buscar em Separacao (nao CarteiraPrincipal) | flag |
| `--co-passageiros-embarque` | Lista todos clientes/pedidos/NFs no mesmo embarque | `--co-passageiros-embarque 1234` |
| `--limit` | Limite de resultados (default: 100) | `--limit 20` |

**Combinacoes suportadas:**
- `--grupo atacadao --produto ketchup` → Pedidos do Atacadao com ketchup
- `--cliente Carrefour --produto palmito` → Pedidos do Carrefour com palmito
- `--cliente "45.543.915"` → Busca por CNPJ
- `--co-passageiros-embarque 1234` → Quem embarcou junto no embarque 1234

**Modo `--status` (consulta de UM pedido) retorna:**
- `pedido.peso_total_kg` — peso bruto total (kg)
- `pedido.volume_total_m3` — volume cubico total (m3, calculado de altura*largura*comprimento)
- `pedido.pallets_total` — qtd total de pallets (qtd / palletizacao)
- `pedido.cliente`, `cnpj`, `cidade`, `uf`, `cep`, `data_entrega_pedido`
- `detalhes.status_descricao`, `valor_total_pedido`, `percentual_separado`
- `detalhes.em_separacao`, `pendente_separar`, `faturado` (com itens e valores)
- `pedido.lotes_separacao` — detalhamento dos lotes existentes
- `pedido.incoterm`, `eh_fob`, `eh_bonificacao` — flags de regra de negocio

---

## 3. consultando_produtos_estoque.py

**Proposito:** Consulta estoque atual, movimentacoes, pendencias, projecoes e SITUACAO COMPLETA.

**Queries cobertas:** Q13, Q17, Q18, Q20 + SITUACAO COMPLETA

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou termo do produto | `--produto palmito`, `--produto "az verde"` |
| `--completo` | SITUACAO COMPLETA (estoque, separacoes, demanda, producao, projecao) | flag |
| `--entradas` | Mostrar entradas recentes (qtd > 0) | flag |
| `--saidas` | Mostrar saidas recentes (qtd < 0) | flag |
| `--pendente` | Quantidade pendente de embarque + lista pedidos | flag |
| `--sobra` | Calcular sobra de estoque apos demanda | flag |
| `--scan-ruptura-global` | Scan proativo: analisa APENAS produtos com separacoes ativas | flag |
| `--ruptura` | Previsao de rupturas (todos produtos com movimentacao) | flag |
| `--dias` | Horizonte de projecao em dias (default: 7) | `--dias 14` |
| `--limit` | Limite de resultados (default: 100) | `--limit 50` |
| `--limit-entradas` | Limite de movimentacoes por produto (default: 100) | `--limit-entradas 20` |

**Opcao --completo retorna:**
- Estoque atual e menor estoque nos proximos 7 dias
- Separacoes por data de expedicao (detalhado com pedidos)
- Demanda total (Carteira bruta/liquida + Separacoes)
- Programacao de producao (proximos 14 dias)
- Projecao dia a dia (estoque projetado)
- Indicadores: sobra, cobertura em dias, % disponivel, previsao de ruptura

---

## 4. calculando_leadtime_entrega.py

**Proposito:** Calcula data de entrega OU data de expedicao sugerida (calculo reverso).

**Queries cobertas:** Q7 + CALCULO REVERSO

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/calculando_leadtime_entrega.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou termo de busca | `--pedido VCD123`, `--pedido "atacadao 183"` |
| `--cidade` | Cidade de destino (alternativa ao pedido) | `--cidade "Sao Paulo"` |
| `--uf` | UF de destino (requerido se usar --cidade) | `--uf SP` |
| `--data-embarque` | Data de embarque (calcula data de entrega) | `--data-embarque amanha` |
| `--data-entrega` | Data de entrega desejada (calcula data de embarque) | `--data-entrega 25/12` |
| `--limit` | Limite de opcoes de transportadora (default: 10) | `--limit 3` |

**Modos de operacao:**

| Modo | Parametro | Descricao |
|------|-----------|-----------|
| Previsao de entrega | `--data-embarque` | Se embarcar dia X, quando chega? |
| Sugestao de embarque | `--data-entrega` | Para chegar dia Y, quando embarcar? |
| Auto (usa pedido) | Apenas `--pedido` | Usa data_entrega_pedido para calculo reverso |

---

## 5. criando_separacao_pedidos.py

**Proposito:** Cria separacoes de pedidos via linguagem natural.

**IMPORTANTE:** Sempre executar primeiro SEM `--executar` para simular!

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido (OBRIGATORIO) | `--pedido VCD123` |
| `--expedicao` | Data de expedicao (OBRIGATORIO) | `--expedicao amanha`, `--expedicao 20/12` |
| `--tipo` | Tipo de separacao | `--tipo completa`, `--tipo parcial` |
| `--pallets` | Quantidade de pallets desejada | `--pallets 28` |
| `--pallets-inteiros` | Forcar pallets inteiros por item | flag |
| `--apenas-estoque` | Separar apenas o que tem em estoque | flag |
| `--excluir-produtos` | JSON array de produtos a excluir | `--excluir-produtos '["KETCHUP","MOSTARDA"]'` |
| `--agendamento` | Data de agendamento | `--agendamento 22/12` |
| `--protocolo` | Protocolo de agendamento | `--protocolo AG12345` |
| `--agendamento-confirmado` | Marcar agendamento como confirmado | flag |
| `--executar` | Efetivamente criar (sem isso, apenas simula) | flag |

**Tipos de separacao:**

| Tipo | Parametros | Descricao |
|------|------------|-----------|
| Completa | `--tipo completa` | Todos os itens com qtd total |
| Parcial | `--tipo parcial` | N itens com qtds especificas |
| Por pallets | `--pallets N` | Distribuir N pallets proporcionalmente |
| Pallets inteiros | `--pallets N --pallets-inteiros` | Cada item = pallets inteiros |
| Apenas estoque | `--apenas-estoque` | So o que tem disponivel |
| Excluindo produtos | `--excluir-produtos '[...]'` | Tudo exceto lista |

---

## 6. consultando_programacao_producao.py

**Proposito:** Lista programacao de producao e simula alteracoes para resolver ruptura.

**Queries cobertas:** Q15 + LISTAGEM COMPLETA

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_programacao_producao.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--listar` | Lista TODA a programacao de producao | flag |
| `--dias` | Horizonte em dias (default: 14) | `--dias 7` |
| `--por-dia` | Mostrar detalhes agrupados por dia | flag |
| `--por-linha` | Mostrar detalhes agrupados por linha | flag |
| `--linha` | Filtrar por linha de producao | `--linha "Linha A"` |
| `--produto` | Produto em ruptura (para reprogramacao) | `--produto "VF pouch 150"` |

**Modos de operacao:**

| Modo | Parametro | Descricao |
|------|-----------|-----------|
| Listagem | `--listar` | Toda a programacao dos proximos N dias |
| Reprogramacao | `--produto` | Opcoes para resolver ruptura |

---

## 7. resolver_entidades.py

**Proposito:** Modulo utilitario para resolver entidades do dominio. Uso interno pelos outros scripts.
Resolve: pedidos, produtos, grupos empresariais, cidades.

---

## 8. analisando_carteira_completa.py

**Proposito:** Analise COMPLETA da carteira seguindo algoritmo P1-P7 do Rafael. Script principal da skill — implementa priorizacao, regras de parcial, comunicacoes PCP/Comercial e sugestoes de separacao.

**IMPORTANTE:** Este e o script mais complexo (1.300+ linhas). Para analises simples, prefira os scripts 1-6. Use este para analise completa da carteira com decisoes.

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/analisando_carteira_completa.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--resumo` | Apenas resumo executivo (sem detalhes por pedido) | flag |
| `--prioridade` | Filtrar por prioridade especifica (1-7) | `--prioridade 1`, `--prioridade 4` |
| `--limit` | Limite de pedidos a analisar | `--limit 20` |
| `--acoes` | Mostrar apenas acoes recomendadas | flag |

**Prioridades disponiveis:**

| Prioridade | Descricao |
|------------|-----------|
| 1 | Pedidos com data_entrega_pedido (cliente negociou) |
| 2 | FOB (cliente coleta) — SEMPRE COMPLETO |
| 3 | Cargas diretas fora de SP (>=26 pallets ou >=20.000kg) |
| 4 | Atacadao (exceto loja 183) |
| 5 | Assai |
| 6 | Demais clientes (ordenado por data_pedido) |
| 7 | Atacadao 183 (ultimo — evitar ruptura em outros) |

**Retorno inclui:**
- Resumo executivo: total pedidos, valor, peso, pallets por prioridade
- Por pedido: disponibilidade, decisao (embarcar/parcial/aguardar), motivo
- Comunicacoes PCP: agrupadas por produto em falta
- Comunicacoes Comercial: agrupadas por gestor
- Comandos de separacao prontos para execucao

---

## 9. gerar_embarque.py

**Proposito:** Gera um EMBARQUE PRONTO (Cotacao + Embarque + EmbarqueItem) a partir de
Separacoes JA escolhidas, propagando `cotacao_id` na Separacao (status -> COTADO via
event listener). Replica a sequencia oficial do `fechar_frete` (ramo Nacom) DENTRO de
app_context, reusando as funcoes oficiais (TabelaFreteManager, obter_proximo_numero_embarque,
LocalizacaoService, Separacao.atualizar_cotacao). NAO reimplementa nada.

**NAO LANCA FRETE.** O embarque nasce SEM `data_embarque`. O frete nasce DEPOIS, no fluxo
normal de portaria/faturamento. Este script NUNCA chama lancamento de frete.

**IMPORTANTE:** Sempre executar primeiro SEM `--confirmar` (dry-run) para ver o plano!

**v1 SO ramo Nacom** — RECUSA lotes com prefixo `CARVIA-`/`ASSAI-` com erro claro.

```bash
source .venv/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/gerar_embarque.py [parametros]
```

### Dois modos

| Modo | Como acionar | O que faz com a tabela de frete |
|------|--------------|----------------------------------|
| **A) ESPELHO** | `--embarque-origem <id>` | Copia o snapshot `tabela_*` congelado do Embarque origem (DIRETA) ou de um EmbarqueItem origem (FRACIONADA). NAO re-busca TabelaFrete. Lotes vem dos itens Nacom ativos do origem (restrinja com `--lotes`). |
| **B) SOLTAS** | `--lotes '[...]' --transportadora-id T --tabela "NOME"` | Monta `dados_tabela` a partir da TabelaFrete oficial (uf_origem=SP, uf_destino derivado dos pedidos, tipo_carga=`--tipo`, modalidade=`--modalidade`). |

### Parametros

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--user-id` | ID do usuario, validado contra tabela `usuarios` (OBRIGATORIO; vira `Cotacao.usuario_id` e `Embarque.criado_por`) | `--user-id 74` |
| `--embarque-origem` | Modo ESPELHO: id do Embarque a espelhar | `--embarque-origem 5807` |
| `--lotes` | Modo SOLTAS: JSON array de `separacao_lote_id` (no ESPELHO restringe o subset) | `--lotes '["LOTE_20251004_1","LOTE_20251004_2"]'` |
| `--transportadora-id` | Modo SOLTAS: id da transportadora | `--transportadora-id 12` |
| `--tabela` | Modo SOLTAS: nome da TabelaFrete (uf_origem=SP) | `--tabela "TABELA AM"` |
| `--tipo` | `DIRETA` ou `FRACIONADA` (default FRACIONADA; no ESPELHO herda do origem) | `--tipo DIRETA` |
| `--modalidade` | Modalidade da tabela (modo SOLTAS) | `--modalidade "FRETE PESO"` |
| `--confirmar` | Efetiva a criacao. Sem isso, apenas simula (dry-run). | flag |

### Guard-rails

- **`--dry-run` e o DEFAULT** — sem `--confirmar` so simula e imprime o plano (totais
  recalculados do banco, numero de embarque previsto, itens que criaria, aviso de frete).
- **`--user-id` OBRIGATORIO** e validado contra `usuarios` (inexistente -> exit 1).
- **DIRETA exige UF normalizado unico** (`LocalizacaoService.normalizar_uf_com_regras`).
  UF misto -> erro (use FRACIONADA ou separe por UF).
- **Idempotencia**: se algum lote ja pertence a embarque ativo, o dry-run ALERTA e o
  `--confirmar` ABORTA (evita Cotacao/Embarque duplicados).
- **Totais recalculados do banco** (`Pedido` por `separacao_lote_id`), nunca da entrada.
- **NUNCA INSERT raw** — so ORM via funcoes oficiais. Frete jamais com tabela zerada.

### Exit codes

| Code | Significado |
|------|-------------|
| `0` | Efetivado (`--confirmar` com sucesso) |
| `4` | Dry-run OK (simulacao bem-sucedida; default sem `--confirmar`) |
| `1` | Falha (erro de execucao / validacao de negocio / user-id inexistente) |
| `2` | Uso (parametros invalidos: sem modo, `--lotes` nao-JSON, `--user-id` ausente) |

### Exemplos

```bash
# ESPELHO (dry-run -> exit 4)
python .claude/skills/gerindo-expedicao/scripts/gerar_embarque.py --user-id 74 --embarque-origem 5807

# ESPELHO efetivo (-> exit 0)
python .claude/skills/gerindo-expedicao/scripts/gerar_embarque.py --user-id 74 --embarque-origem 5807 --confirmar

# SOLTAS (dry-run -> exit 4)
python .claude/skills/gerindo-expedicao/scripts/gerar_embarque.py --user-id 74 \
  --lotes '["LOTE_20251004_1","LOTE_20251004_2"]' \
  --transportadora-id 12 --tabela "TABELA AM" --tipo DIRETA --modalidade "FRETE PESO"

# SOLTAS efetivo FRACIONADA (-> exit 0)
python .claude/skills/gerindo-expedicao/scripts/gerar_embarque.py --user-id 74 \
  --lotes '["LOTE_A"]' --transportadora-id 12 --tabela "TABELA AM" --tipo FRACIONADA --confirmar
```

### Retorno (dry-run) inclui

- `usuario` (id, nome) validado
- `plano`: `modo`, `tipo_carga`, `transportadora_id`, `lotes`, `dados_tabela` (snapshot),
  `totais` (valor/peso/pallet recalculados), `icms_destino`, `numero_embarque_previsto`,
  `itens_previstos` (1 por lote: cnpj, cliente, pedido, peso, valor, pallets, cidade/uf),
  `ja_em_embarque_ativo`, `aviso_frete`.
- `alerta_idempotencia` quando algum lote ja esta em embarque ativo.

### Retorno (efetivado) inclui

- `cotacao_id`, `embarque_id`, `numero_embarque`, `tipo_carga`, `itens_criados`, `totais`,
  `aviso_frete` ("Embarque criado SEM data_embarque. Frete nascera no fluxo normal...").
