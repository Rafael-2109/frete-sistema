<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-25
-->
# Relatório Semanal de Estoque (comparativo segunda-a-segunda) — Design

> **Papel:** spec de design do relatório semanal de estoque entregue por e-mail (comparativo segunda-a-segunda). Plano par: `docs/superpowers/plans/2026-06-25-relatorio-estoque-semanal.md`.

> **Data:** 2026-06-25
> **Autor:** Marcus (via Claude Code)
> **Status:** Em revisão (aguardando aprovação da spec)

## Indice
- Objetivo
- Contexto
- Escopo
- Design (cálculo, serviço, job, e-mail)

## Contexto

Complementa (sem substituir) o relatório de **estoques** já existente em
`/manufatura/relatorios-semanais/` (snapshot do saldo atual) com a **dimensão
semanal** — o que entrou e saiu comparando uma segunda com a anterior — e entrega
automática por e-mail.

## 1. Objetivo

Marcus precisa receber, **toda segunda-feira de manhã (8h)**, um relatório de
estoque que mostre, para cada material, **o que entrou e o que saiu na última
semana** — comparando o saldo de uma segunda com o da segunda anterior.

Hoje o sistema já gera um relatório de **estoques** em
`/manufatura/relatorios-semanais/` (botão que baixa um `.zip` com 3 planilhas).
Esse relatório é um **retrato do saldo atual** (snapshot), sem dimensão de tempo.
O novo relatório **complementa** esse de estoques com a dimensão semanal e é
**entregue por e-mail automaticamente** — sem substituir nada do que já existe.

## 2. Escopo

### Faz parte
- Novo relatório `estoque_semanal.xlsx` com as colunas do comparativo semanal.
- Cálculo do saldo de estoque em **duas datas** (segunda anterior e segunda atual).
- Cálculo de **entradas** e **consumos/saídas** no período entre as duas segundas.
- Coluna **"Outros ajustes"** para garantir o fechamento da conta.
- Envio **automático por e-mail** toda segunda às 8h (anexo `.xlsx`).
- Função reutilizável com modo `dry_run` (gera sem enviar — para teste).

### NÃO faz parte (YAGNI)
- Não altera os 3 relatórios atuais do botão de download.
- Não cria tela/página nova (entrega é por e-mail; teste é via shell).
- Não cobre filtros por fornecedor, por ordem de produção, nem histórico de
  várias semanas (só o comparativo da semana corrente vs. anterior).

## 3. Decisões de produto (alinhadas com Marcus)

| Decisão | Escolha |
|---------|---------|
| Materiais cobertos | **3 grupos**: Insumos, Embalagens e Produto Acabado (PA com lógica adaptada) |
| Forma de entrega | **E-mail automático**, planilha anexada |
| Destinatário | **Configurável** por variável de ambiente (Rafael/Marcus definem na ativação) |
| Horário | **Segunda-feira, 8h** (timezone America/Sao_Paulo) |
| Fechamento da conta | Coluna **"Outros ajustes"** absorve o resto, garantindo o fechamento |

## 4. Modelo de dados (confirmado no código)

Tudo vem de **`MovimentacaoEstoque`** (`app/estoque/models.py`), que já tem a
dimensão temporal e a origem de cada movimento:

- `data_movimentacao` (date) — data do movimento.
- `qtd_movimentacao` (numeric, **com sinal**) — positivo entra, negativo sai.
- `tipo_movimentacao` — `ENTRADA`, `SAIDA`, `AJUSTE`, `PRODUÇÃO`, `CONSUMO`, `FATURAMENTO`.
- `local_movimentacao` — `COMPRA`, `VENDA`, `PRODUCAO`, `AJUSTE`, `DEVOLUCAO`, `REVERSAO`.
- `ativo` (bool) — `False` = movimento cancelado (sempre filtrar `ativo=True`).

Origens confirmadas:
- **Entrada por compra**: `recebimento_fisico_odoo_service.py` grava
  `tipo='ENTRADA'` + `local='COMPRA'` (positivo).
- **Consumo de produção (apontamento)**: `consumo_producao_service.py` grava
  `tipo='CONSUMO'` (negativo) e a contrapartida `tipo='PRODUÇÃO'` (positivo) para
  o produto produzido. **Atenção: `'PRODUÇÃO'` é gravado com acento.**
- **Saída de Produto Acabado (todo faturamento)**: `processar_faturamento.py` grava
  `tipo='FATURAMENTO'` + `local='VENDA'` + `qtd=-abs(...)` (negativo) para **toda
  NF de saída** — venda E **bonificação** (a importação Odoo inclui
  `l10n_br_tipo_pedido in (venda, bonificacao, industrializacao, exportacao,
  venda-industrializacao)`, `faturamento_service.py:1399`). No estoque, venda e
  bonificação são indistinguíveis (ambas baixam como FATURAMENTO+VENDA). **Não
  existe escritor `tipo='SAIDA'` para vendas de PA** — usar `FATURAMENTO` como
  sinal primário (código aceita `SAIDA` como fallback defensivo).
- **Entrada por devolução de venda (PA)**: `reversao_service.py` grava
  `tipo='ENTRADA'` + `local='REVERSAO'` + `qtd` positivo (produto devolvido volta
  ao estoque). É o único movimento de devolução que afeta o estoque hoje (a NFD do
  cliente, sozinha, não gera `MovimentacaoEstoque`). O código aceita também
  `local='DEVOLUCAO'` por robustez.

Classificação em Insumos / Embalagens / Produto Acabado: reusa a função
`classificar_aba` de `relatorios_semanais_calc.py` (mesma do relatório atual),
que usa `CadastroPalletizacao` (`tipo_materia_prima`, `categoria_produto`,
`tipo_embalagem`).

Unificação de códigos: consolida código origem→destino pelo mesmo mapa de
`UnificacaoCodigos` usado no relatório atual, para não duplicar linhas.

## 5. Régua de datas (convenção de "saldo de abertura")

`data_movimentacao` é uma DATA (sem hora). Convenção adotada:

- **seg_atual** = a segunda em que o relatório roda (hoje).
- **seg_anterior** = `seg_atual − 7 dias`.
- **Estoque "segunda 0"** = `SUM(qtd_movimentacao) WHERE data_movimentacao < seg_anterior`
  (saldo de abertura da segunda anterior).
- **Estoque "segunda do dia"** = `SUM(qtd_movimentacao) WHERE data_movimentacao < seg_atual`
  (saldo de abertura de hoje).
- **Período do meio** = `seg_anterior <= data_movimentacao < seg_atual`
  (segunda anterior, inclusive, até domingo, inclusive — 7 dias).

Consequência (intencional): movimentos com data da **segunda anterior** entram no
período; movimentos com data de **hoje** ainda não (são saldo de abertura de hoje).
Rodando 8h da segunda, captura tudo até o domingo à noite.

**Por construção:** `Estoque seg0 + Σ(movimentos do período) = Estoque hoje`.

> **Nota:** diferente do relatório de estoques atual, aqui o saldo **não** recebe
> piso 0 (estoque negativo é exibido como está). Aplicar piso quebraria o
> fechamento da conta. Este é um relatório de movimentação/auditoria: precisa fechar.

## 6. As 4 colunas de movimento mudam de sentido por grupo

Para todos os grupos a planilha mostra: **Estoque seg0 · Entradas · Consumos/Saídas
· Outros ajustes · Estoque hoje**. O que cada coluna soma depende do grupo:

| Grupo | "Entradas" soma | "Consumos/Saídas" soma |
|-------|-----------------|------------------------|
| **Insumos / Embalagens** | movimentos de **compra** (`tipo=ENTRADA` + `local=COMPRA`) | **consumo de produção** (`tipo=CONSUMO`) |
| **Produto Acabado** | **produção** (`tipo=PRODUÇÃO`) + **devolução de venda** (`local=REVERSAO`/`DEVOLUCAO`) | **todo faturamento** — venda e **bonificação** (`tipo=FATURAMENTO` + `local=VENDA`; aceita `SAIDA` como fallback) |

- "Entradas" e "Consumos/Saídas" são exibidos como **valores positivos** (quantidade).
- **"Outros ajustes"** = `(Estoque hoje − Estoque seg0) − Entradas + Consumos`.
  Absorve ajustes de inventário, devoluções, transferências e cruzamentos atípicos
  (ex.: PA consumido como componente, insumo vendido). Garante o fechamento.

Cabeçalho de cada aba é ajustado ao grupo (ex.: aba Insumos diz
"Entradas (compras)"/"Consumos (produção)"; aba Produto_Acabado diz
"Entradas (produção)"/"Saídas (vendas)").

### Universo de linhas
Aparecem os produtos que tenham estoque ≠ 0 em **alguma** das duas segundas **ou**
que tiveram **algum movimento** no período. Produtos zerados e sem movimento na
semana não poluem o relatório.

## 7. Arquitetura

```
app/manufatura/services/estoque_semanal_service.py   (NOVO)
  ├─ coleta (queries agregadas em MovimentacaoEstoque):
  │    saldo_ate(data) · movimentos_periodo_por_categoria(ini, fim)
  ├─ monta linhas por grupo (reusa classificar_aba + unificação)
  ├─ gera estoque_semanal.xlsx (pandas/openpyxl, mesmo padrão do service atual)
  └─ enviar_estoque_semanal_email(dry_run=False) → usa EmailSender (anexo .xlsx)

app/scheduler/sincronizacao_incremental_definitiva.py  (EDITA)
  └─ executar_estoque_semanal_email() + add_job cron
       day_of_week='mon', hour=ESTOQUE_SEMANAL_EMAIL_HOUR (default 8), ATRÁS da flag
```

- **E-mail**: usa o `EmailSender` existente (`app/notificacoes/email_sender.py`),
  que suporta anexo `(filename, bytes)` no backend SMTP. Assunto:
  "Relatório semanal de estoque — semana de DD/MM a DD/MM". Corpo HTML curto +
  planilha anexada.
- **Cálculo puro** (régua de datas, fechamento) isolado em funções testáveis,
  no padrão do `relatorios_semanais_calc.py`.

### Variáveis de ambiente (novas)
| Var | Default | Função |
|-----|---------|--------|
| `ESTOQUE_SEMANAL_EMAIL_ENABLED` | `false` | Liga/desliga o envio automático (Rafael ativa) |
| `ESTOQUE_SEMANAL_EMAIL_TO` | `""` | Destinatário(s), separados por vírgula |
| `ESTOQUE_SEMANAL_EMAIL_HOUR` | `8` | Hora do envio na segunda |

Reusa as `EMAIL_*` já existentes para o envio. Pré-requisito de ativação:
`EmailConfig.is_configured()` verdadeiro em produção (a confirmar com Rafael).

## 8. Tratamento de erros
- Falha ao explodir/agregar um produto não derruba o relatório (loga e segue),
  no mesmo espírito do service atual.
- Se o e-mail não estiver configurado (`is_configured()` falso) ou
  `ESTOQUE_SEMANAL_EMAIL_TO` vazio: loga aviso e **não** quebra o scheduler.
- Job protegido por flag (default OFF): nada dispara até o Rafael ativar.

## 9. Testes
- Régua de datas: saldo de abertura nas duas pontas; movimento na segunda
  anterior conta, movimento de hoje não conta.
- Fechamento: `seg0 + entradas − consumos + outros == hoje` em cada grupo,
  incluindo casos com ajuste/devolução/venda.
- Classificação por grupo e sentido das colunas (compra vs. produção; produção
  vs. venda no PA).
- Estoque negativo é exibido sem piso e a conta ainda fecha.
- `dry_run=True` gera bytes do `.xlsx` e **não** chama o envio.

## 10. Como testar/ativar (produção)
```python
from app.manufatura.services.estoque_semanal_service import enviar_estoque_semanal_email
enviar_estoque_semanal_email(dry_run=True)   # gera planilha, NÃO envia
enviar_estoque_semanal_email()               # envia por e-mail
```
Ativar: setar `ESTOQUE_SEMANAL_EMAIL_ENABLED=true` e `ESTOQUE_SEMANAL_EMAIL_TO`
no Render (depende do Rafael). `EMAIL_*` precisam estar configuradas.
