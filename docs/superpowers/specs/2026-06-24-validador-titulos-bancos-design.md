# Validador de Títulos x Bancos — Design

> Status: aprovado pelo Marcus em 24/06/2026 (design). Aguarda revisão do spec e plano de implementação.

## Contexto e problema

Hoje a conferência de títulos cedidos a bancos/securitizadoras é feita manualmente na
planilha `W:\VALIDADOR TITULOS BANCOS.xlsb` (9 abas). O operador (Marcus) baixa as bases
de cada ambiente externo, cola em abas, cria fórmulas para padronizar uma chave única e
faz três comparativos. O processo é trabalhoso, manual e propenso a erro.

Bancos/securitizadoras de boletos da Nacom Goya: **SRM, GRAFENO, AGIS, VORTX**.

### Como a planilha funciona hoje (engenharia reversa)

| Aba | Papel | Chave / observação |
|-----|-------|--------------------|
| `SRM` | base crua do banco SRM (~68 títulos) | identificador `Nro Documento` no formato `148466-001` |
| `GRAFENO` | base crua GRAFENO (~44) | identificador `Seu_Número` no formato `146299/003` |
| `AGIS` | base crua AGIS (~425) | identificador `Recebivel` no formato `146826/5` (às vezes `148576-2`) |
| `VORTX` | base crua VORTX (~289) | identificador `Seu_Número` no formato `148298/002` (às vezes `147443-003`) |
| `TODOS` | empilha os 4 bancos | `NF-PARC` + `BANCO` |
| `DINAN` / `FINAL` | tabela dinâmica NF-PARC × banco | soma por banco; `Total Geral > 1` = título em +1 banco |
| `FATURAMENTO` | notas faturadas (Odoo) | `Empresa, NF-e, Parcela, Vencimento, Saldo, Forma de Pagamento…` |
| `BOL x FAT` | cada nota faturada × bancos | `TOTAL = 0` = nota faturada sem boleto |

**Chave única `NF-PARC`**: `<número da NF>-<parcela sem zeros à esquerda>`. Ex.: `146299/003` → `146299-3`.

### Validação de recompra (regra de negócio do ponto 4)

Um mesmo título pode legitimamente estar em 2 bancos quando houve **recompra** — a Nacom
recompra o título de um banco. A recompra é validada contra a planilha
`W:\CONTAS A PAGAR - CP.xlsb`, aba **`CP - NACOM`** (~32 mil linhas): se o mesmo
título+parcela estiver lançado lá, o título em 2 bancos é **válido**.

## Objetivo

Substituir a planilha manual por uma **tela web** dentro do sistema de fretes, onde o
operador sobe as bases, clica em Processar, e recebe os 3 comparativos na tela e em Excel.

## Decisões de arquitetura (aprovadas pelo Marcus)

1. **Superfície: tela web** dentro do sistema (menu Financeiro). Decisão consciente, mesmo
   sabendo que o servidor (Render) não acessa o `W:\` local — logo, arquivos externos são
   enviados por upload.
2. **Faturamento: puxado do sistema** — tabela `contas_a_receber` (já sincronizada do Odoo).
   Não há upload nem chamada Odoo ao vivo.
3. **Contas a pagar (recompra): upload** da planilha `CONTAS A PAGAR - CP`, aba `CP - NACOM`.
   Fonte de verdade da recompra é a planilha manual do financeiro (ponto 4 do pedido),
   que pode conter lançamentos ausentes no Odoo. Por isso NÃO se usa a tabela
   `contas_a_pagar` do sistema.

### Entradas

- **5 uploads**: `SRM`, `GRAFENO`, `AGIS`, `VORTX`, `CONTAS A PAGAR - CP`.
- **1 fonte interna**: faturamento via `contas_a_receber`.

## Fluxo do usuário

1. Abre a tela "Validador de Títulos x Bancos" (menu Financeiro).
2. Sobe os 5 arquivos, cada um em seu campo identificado.
3. Clica em **Processar**.
4. Vê os 3 comparativos na tela + botão **Baixar Excel** com o resultado completo.

## Componentes

Tudo dentro de `app/financeiro/` (módulo existente), seguindo os padrões já usados ali.

```
app/financeiro/
  routes/validador_titulos.py        # rota(s) da tela + processamento (blueprint financeiro_bp)
  services/validador_titulos/
    __init__.py
    parsers_bancos.py                # 1 parser por banco -> lista de (NF-PARC, banco, valor, venc, ...)
    normalizador.py                  # NF-PARC canônico (usa parcela_utils.parcela_to_int)
    comparador.py                    # monta TODOS, duplicados, recompra, BOL x FAT, boletos sem nota
    exportador.py                    # gera o Excel de saída (reusa exportando-arquivos/openpyxl)
app/templates/financeiro/validador_titulos.html   # tela (upload + resultados)
```

### Unidades e responsabilidades

- **parsers_bancos.py** — um parser por banco. Cada parser lê o arquivo enviado (xlsx/xlsb/csv),
  localiza as colunas-chave **por nome de cabeçalho** (não por posição), e devolve uma lista
  normalizada de boletos: `{nf_parc, banco, valor, vencimento, identificador_original}`.
  Isola a bagunça de formato de cada banco atrás de uma interface única.
- **normalizador.py** — `montar_nf_parc(numero, separador?)`: separa NF e parcela e produz
  `"{nf}-{parcela_int}"`. Reusa `app/financeiro/parcela_utils.parcela_to_int` para a parcela
  (já trata `3.0`, `"003"`, `"P3"`, vazio, etc.). Trata os casos especiais conhecidos.
- **comparador.py** — recebe (boletos dos 4 bancos, faturamento, CP) e produz os resultados
  dos 3 comparativos. Lógica pura, testável sem Flask.
- **exportador.py** — Excel com abas: `TODOS`, `DUPLICADOS`, `BOL x FAT`,
  `BOLETOS SEM NOTA` e (auxiliar) as bases tratadas.
- **routes/validador_titulos.py** — GET (tela) + POST (recebe uploads, chama serviços,
  devolve resultados/Excel). Registrada no `financeiro_bp` (`app/__init__.py:998`).

## Regras dos comparativos

### Normalização NF-PARC (todas as fontes passam por aqui)

- Separador entre NF e parcela: `/` quando presente, senão último `-` (`rsplit("-", 1)`).
- Parcela → `parcela_to_int` (remove zeros à esquerda: `003` → `3`).
- Caso especial conhecido: `00103--2` (NF com hífen) → `rsplit` pelo último separador:
  NF=`00103-`, parcela=`2` → `00103--2`.

### Comparativo 1 — Títulos em mais de um banco (pontos 3 + 4)

1. Empilha os 4 bancos (aba `TODOS`).
2. Agrupa por `NF-PARC`; conta em quantos **bancos distintos** aparece.
3. `qtd_bancos >= 2` → entra na lista de duplicados, com a relação de bancos.
4. Cruza cada duplicado com o CP (`CP - NACOM`): existe lançamento com mesmo título+parcela?
   - 🟢 **Recompra OK** (achou no CP) → válido em 2 bancos.
   - 🔴 **Sem recompra — verificar** (não achou) → suspeito.

### Comparativo 2 — Notas faturadas SEM boleto (ponto 5)

1. Lista faturamento (`contas_a_receber`) como `NF-PARC` + dados (cliente, vencimento, valor).
2. Para cada NF-PARC faturado, verifica presença na lista `TODOS` (boletos dos bancos).
3. Não está em nenhum banco → entra na lista "faturado sem boleto".

### Comparativo 3 — Boletos sem nota (bônus, aprovado)

1. Para cada NF-PARC dos bancos, verifica se existe no faturamento.
2. Não existe → "boleto sem nota faturada" (costuma pegar erro de digitação de NF).

## Mapeamento de dados (a validar com arquivos crus na implementação)

| Fonte | Campo identificador (cru) | → NF-PARC |
|-------|---------------------------|-----------|
| SRM | `Nro Documento` (`148466-001`) | `rsplit("-")` → `148466-1` |
| GRAFENO | `Seu_Número` (`146299/003`) | split `/` → `146299-3` |
| AGIS | `Recebivel` (`146826/5` ou `148576-2`) | `/` ou `rsplit("-")` → `146826-5` |
| VORTX | `Seu_Número` (`148298/002` ou `147443-003`) | `/` ou `rsplit("-")` → `148298-2` |
| FATURAMENTO | `contas_a_receber.titulo_nf` + `parcela` | `titulo_nf-parcela_int` |
| CP - NACOM | `Titulo` (col `Titulo`) + `Parc` | `Titulo-Parc_int` |

**Filtro do faturamento (`contas_a_receber`) — a confirmar com Marcus na implementação:**
quais empresas (1=FB, 2=SC, 3=CD), qual recorte de período/vencimento, e se filtra por
`status_pagamento_odoo`/`parcela_paga`. A aba atual mostra `Situação = Emitido`, empresas
CD e FB.

## Reaproveitamento do que já existe

- `app/financeiro/parcela_utils.parcela_to_int` — normalização de parcela.
- Blueprint `financeiro_bp` (`app/__init__.py:998`) — registro de rotas.
- Padrões de upload/export já usados no módulo financeiro (parsers de extrato, exportação).
- Já existem `conversor_extrato_srm` e `remessa_vortx` no financeiro — verificar se há parser
  reaproveitável de layout SRM/VORTX antes de escrever do zero.

## Fora de escopo (YAGNI)

- Não persiste histórico de execuções em banco (processamento sob demanda; resultado vira Excel).
- Não automatiza o download das bases dos bancos.
- Não usa a tabela `contas_a_pagar` do sistema (fonte da recompra é a planilha manual).
- Não cria agendamento/rotina automática.

## Testes

- **Unitários (lógica pura, sem Flask):**
  - `normalizador`: casos `146299/003`→`146299-3`, `148466-001`→`148466-1`,
    `00103--2`→`00103--2`, vazio/ inválido.
  - `comparador`: duplicado em 2 bancos com e sem recompra; faturado sem boleto;
    boleto sem nota.
- **Parsers:** com amostras reais dos downloads crus de cada banco (pedir ao Marcus).
- **Validação ponta a ponta:** rodar com as bases reais e conferir que os números batem com
  a planilha atual (`FINAL` e `BOL x FAT`).

## Achados da validação do normalizador (24/06/2026)

Normalizador validado contra o gabarito real da planilha (coluna NF-PARC feita à mão):
**814/826 batem exatamente.** AGIS 425/425, SRM 67/68, e os não-vazios de GRAFENO/VORTX.
As 12 divergências reais são **dados sujos da planilha manual** (a decidir com Marcus):

- **6× `00NNN-00P`** (só VORTX, ex. `00106-003`): normalizador gera `00106-3`; a planilha
  gera `00106--3` (hífen duplo, artefato de fórmula). Decisão atual: **preservar zeros à
  esquerda** da NF (não casar `00106` com `106`). Confirmar com Marcus.
- **5× `NNN.0`** (só VORTX, ex. `147569.0`, `105.0`): a planilha "inventa" parcela = último
  dígito (`105-5`). É lixo → normalizador retorna `None` (sinaliza conferência). Confirmar.
- **1× SRM `147812`** sem parcela no documento: a parcela real está em coluna separada
  (`PARCELA`) — o parser SRM deve usá-la como fallback.

## Pontos abertos para a implementação

1. Amostra do **arquivo cru** baixado de cada banco (antes das fórmulas) — para os parsers.
2. Exemplo real de **recompra** na aba `CP - NACOM` — confirmar formato do título/parcela.
3. Filtro do **faturamento** em `contas_a_receber` (empresas, período, status).
4. Os 12 casos de borda acima (zeros à esquerda, `NNN.0`, SRM sem parcela).
