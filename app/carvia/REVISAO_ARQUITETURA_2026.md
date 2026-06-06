<!-- doc:meta
tipo: explanation
camada: L2
sot_de: Revisao de Arquitetura CarVia
hub: app/carvia/CLAUDE.md
superseded_by: —
atualizado: 2026-06-06
-->
# Revisao de Arquitetura CarVia

> **Papel:** avaliacao arquitetural do modulo CarVia (transportadora que VENDE frete e SUBCONTRATA terceiros) — modelo conceitual ideal de vinculos + mapa de gaps em macro processo, processo, vinculacoes, FK e exibicoes, com cada afirmacao classificada por nivel epistemico. **Abra quando:** for redesenhar vinculos/FK/conciliacao/fatura do CarVia, ou priorizar divida tecnica de confiabilidade de dados.

## Indice

- [Contexto e metodo](#contexto-e-metodo)
- [Legenda epistemica](#legenda-epistemica)
- [1. Modelo conceitual ideal](#1-modelo-conceitual-ideal)
- [2. As 5 falhas estruturais (raiz comum)](#2-as-5-falhas-estruturais-raiz-comum)
- [3. Veredito dos 6 pontos reportados + exemplo](#3-veredito-dos-6-pontos-reportados--exemplo)
- [4. Gaps adicionais por dimensao](#4-gaps-adicionais-por-dimensao)
- [5. Priorizacao sugerida](#5-priorizacao-sugerida)
- [6. Limites desta analise (risco de alucinacao)](#6-limites-desta-analise-risco-de-alucinacao)

## Contexto e metodo

Esta revisao foi produzida em 2026-06-06 sobre o modulo CarVia (~67K LOC, 107 arquivos Python, 115 templates, ~50 tabelas). Complementa — **nao substitui** — [REVISAO_GAPS.md](REVISAO_GAPS.md): aqueles 37 gaps (status/FK orfao/concorrencia) ja foram resolvidos e sao de outra natureza. Aqui o foco sao gaps **conceituais/arquiteturais** de nivel superior, partindo da pergunta: *como DEVERIA funcionar o vinculo de dados de uma transportadora que vende frete e subcontrata?*

**Metodo:** 6 mapas profundos do modulo (modelo/FK, ciclo do CTe, faturas, conciliacao, papeis, exibicoes) + verificacao direta de 6 pontos reportados pelo usuario + 1 exemplo + varredura de gaps em 5 dimensoes. O nucleo de fatos de maior carga foi **re-verificado pessoalmente** (leitura direta do codigo nesta sessao); o restante vem de subagentes com citacao `arquivo:linha` + trecho verbatim. O ponto I4 foi adicionalmente confirmado no **Postgres de producao**.

> **Por que a classificacao epistemica:** o pedido explicito foi separar o que e **fato verificado**, o que e **logica do sistema seguida e verificada**, e o que pode ser **alucinacao**. Cada afirmacao abaixo carrega uma etiqueta. A [Secao 6](#6-limites-desta-analise-risco-de-alucinacao) lista o que NAO foi verificado.

## Legenda epistemica

| Tag | Significado | Confianca |
|-----|-------------|-----------|
| **[F✓]** | **Fato verificado pelo autor** nesta sessao — arquivo lido diretamente, trecho confere | Maxima |
| **[F~]** | **Fato verificado por subagente** — citacao `arquivo:linha` + trecho verbatim no relatorio, **nao** re-lido pelo autor | Alta |
| **[F-DB]** | **Fato verificado no Postgres de producao** (consulta de constraint/contagem) | Alta |
| **[L]** | **Logica do sistema** — consequencia que decorre de fatos [F] seguindo o fluxo do codigo; **nao observada em runtime**, e inferencia logica | Media-Alta |
| **[?]** | **Nao verificado / julgamento / possivel alucinacao** — opiniao arquitetural (o "ideal"), premissa de dominio, severidade, ou comportamento de codigo nao lido | Baixa — tratar como hipotese |

Regra de leitura: **[F✓]/[F~]/[F-DB]** sao o que o codigo faz; **[L]** e o que decorre disso; **[?]** e opiniao/suposicao a confirmar com o negocio antes de agir.

---

## 1. Modelo conceitual ideal

> **Todo este bloco e [?]** — e raciocinio de dominio (como *deveria* ser), nao um fato sobre o codigo. Serve de regua para medir os gaps. Confirmar com a operacao antes de tratar como requisito.

Uma transportadora que **vende frete e subcontrata** tem, para **cada carga fisica**, **dois eventos economicos que sao dois lados do mesmo pivo**:

```
                          +--------------------------------------+
                          |   CARGA / FRETE  (1 movimento fisico)|  <- PIVO UNICO
                          |   origem->destino + N NFs (mercadoria)|
                          +---------------+----------------------+
              RECEITA <-------------------||-------------------> CUSTO
        +----------------------+          ||      +--------------------------+
        | CTe VENDA (emite p/   |         ||      | CTe COMPRA / subcontrato |
        | o TOMADOR contratual) |         ||      | (terceiro emite; CarVia  |
        | -> Fatura do PAGADOR  |         ||      |  e o tomador) -> Fatura   |
        |   (a receber)         |         ||      |  do terceiro (a pagar)    |
        +----------+------------+          ||     +------------+-------------+
                   |   MARGEM = Sreceita_real - Scusto_real    |
                   +------------- (ambos de CTe AUTORIZADO) ----+
```

Sete principios que o modelo ideal exige **[?]**:

1. **O frete e o pivo unico.** NF<->frete, CTe-venda<->frete e CTe-compra<->frete sao vinculos com **FK real e identidade nao-colidente** (chave de 44 digitos ou `numero+serie+emitente`), nao CSV de texto. A **margem real** sai do pivo: receita do CTe-venda autorizado menos custo do CTe-compra autorizado — nunca da cotacao.
2. **"Tomador" e uma ENTIDADE pagadora, nao um rotulo SEFAZ.** O CTe tem 6-7 participantes; o tomador (toma3/toma4) resolve para um CNPJ concreto que **e** quem a fatura cobra. O `toma4` (terceiro) carrega CNPJ proprio e precisa ser preservado. O pagador da fatura deriva de / e validado contra essa entidade-tomador.
3. **O CTe e um documento FISCAL com 3 dimensoes ortogonais:** (a) status de **workflow** (rascunho->faturado); (b) status **fiscal SEFAZ** (autorizado/cancelado/denegado, lido de `<protCTe>`/`<procEventoCTe>`); (c) **tipo** `tpCTe` (normal/complementar/anulacao/substituto). Anulacao/substituto referenciam e estornam/substituem o original — nunca sao receita nova. "Cancelado-interno" != "cancelado-SEFAZ".
4. **A fatura e um agregador imutavel-apos-emissao, com versionamento.** Valor reconciliado contra a soma dos componentes ativos (gate simetrico receita e custo), exclui cancelados da soma, suporta substituicao (fatura substituta que cancela a anterior preservando trilha), e a delecao desfaz simetricamente todos os vinculos criados.
5. **A conciliacao casa pela entidade-pagadora real** (tomador), considerando todas as identidades plausiveis da carga (tomador, destinatario, remetente, terceiro) e aprende por contraparte E direcao (receber<->cliente, pagar<->transportadora).
6. **Simetria venda<->compra:** todo conceito do lado venda tem espelho no custo (complementar de custo, conferencia de custo, re-link de subcontrato orfao, aprendizado de match para pagar).
7. **A espinha financeira tem integridade no BANCO** (FKs com ON DELETE correto), nao 100% na camada de service.

---

## 2. As 5 falhas estruturais (raiz comum)

Quase tudo que foi reportado e **sintoma de 5 decisoes arquiteturais** de fundo. A coluna "Fundamento" lista os fatos [F]; a coluna "Sintomas" e o mapeamento [L]/[?].

| # | Falha estrutural | Fundamento (fatos) | Sintomas |
|---|------------------|--------------------|----------|
| **A** | O frete (pivo) nao amarra receita-real x custo-real; o lado-custo nem e populado no eixo canonico | `frete.py:185-196` margem usa `valor_cotado` **[F~]**; import do sub seta so `operacao_id`, `frete_id=NULL` `importacao_service.py:2268-2286` **[F~]** | margem irreal, conferencia assimetrica **[L]** |
| **B** | "Tomador" e rotulo SEFAZ decorativo, nao entidade pagadora | `tomador.py:13-16,45-60` retorna `{codigo,label}` **sem CNPJ** **[F✓]**; `toma4` colapsa p/ `'TERCEIRO'` `importacao_service.py:2001-2002` **[F~]** | **I5, I6, I7 + exemplo** **[L]** |
| **C** | O CTe nao tem dimensao FISCAL (status SEFAZ + `tpCTe`); "CANCELADO" conflaciona interno x fiscal | so `tpCTe=='1'` reclassificado `importacao_service.py:307-312` **[F✓]**; `carvia_operacoes` sem `cstat/cancelado_em` (schema) **[F~]** | **I1, I3**, anulacao, receita fantasma **[L]** |
| **D** | Fatura e linha editavel, nao documento com ciclo de vida | gate "MANUAL puro" `fatura_routes.py:955` **[F✓]**; "Soma CTe" conta cancelados `detalhe.html:259` **[F✓]**; zero rota de substituicao **[F~]** | **I2** **[L]** |
| **E** | Integridade referencial mora no service, nao no banco | `frete.py:92-105` FKs sem `ondelete` **[F✓]**; `conta_corrente.py:54-56` idem **[F✓]**; conciliacao polimorfica sem FK `financeiro.py:281-283` **[F~]** | **I4** **[L]** |

> **[?]** Avaliacao do autor: a falha **B** sozinha explica metade da lista reportada (I5, I6, I7 + exemplo) e e pre-requisito conceitual para conciliacao confiavel — candidata a atacar primeiro.

---

## 3. Veredito dos 6 pontos reportados + exemplo

Todos os 7 pontos receberam veredito **CONFIRMADO**. Abaixo, o fato central de cada um com a etiqueta de verificacao, a consequencia logica e a correcao (opiniao).

### I1 — CTe complementar criado no SSW nao consegue ser inserido

- **[F~]** Existe caminho de import (tela `/carvia/importar` -> bloco 3.5 `importacao_service.py:876-1134`); nao ha endpoint dedicado fora desse pipeline de upload de XML.
- **[F✓]** A reclassificacao para complementar so ocorre se `tipo_cte == '1' and classificacao == 'CTE_CARVIA'` (`importacao_service.py:307-312`).
- **[F~]** O complementar e DESCARTADO via `continue` se faltar `<infCteComp>/<chCTe>` (`:919-927`) **ou** se a `CarviaOperacao` pai nao existir no banco por `cte_chave_acesso` (`:929-940`).
- **[L]** Como o operador criou o complementar (e tipicamente o CTe pai) direto no SSW, a operacao pai nunca foi importada -> o complementar nao tem ancora -> e silenciosamente descartado (vira `erros[]`; preview alerta mas nao bloqueia o botao confirmar — `importar_resultado.html:407-410` **[F~]**).
- **[L]** Nao ha re-link retroativo Comp->Operacao (existe so para NF<->CTe via `nfs_referenciadas_json`); reimportar depois do pai exige re-submissao manual.
- **Correcao [?]:** casar o pai tambem pelo lote em memoria do upload; persistir complementar "orfao/aguardando pai" com re-link retroativo; ofertar caminho de importar/criar o CTe pai externo; tornar a falha bloqueante/visivel. **Dimensao: PROCESSO · Severidade: ALTO [?].**

### I2 — Fatura nao valida valor x CTes; e nao e substituivel

- **[F✓]** `aprovar_fatura_cliente` tem docstring *"Gate: MANUAL puro — nao valida soma de CTes nem status das operacoes"* (`fatura_routes.py:955`) e o corpo so seta `status_conferencia='CONFERIDO'` + auditoria (`:987-1001`), zero comparacao com `valor_total`.
- **[F~]** A fatura TRANSPORTADORA, por contraste, tem gate de tolerancia R$1,00 (`fatura_routes.py:2313-2333`) — assimetria entre os dois lados da mesma entidade.
- **[F✓]** A "Soma CTe" exibida usa `operacoes|selectattr('cte_valor')|map(attribute='cte_valor')|sum` (`detalhe.html:259`) — `selectattr` filtra so valor falsy, **nao** status; um CTe CANCELADO com `cte_valor>0` entra na soma.
- **[F~]** Nao existe rota de substituicao (`grep def substituir` = 0); so edicao in-place ou hard-delete + recriar.
- **[L]** Como a quitacao (PAGA) e decidida por `total_conciliado >= valor_total` (`carvia_conciliacao_service.py` **[F~]**), uma fatura cobrada divergente dos CTes e dada como paga contra um total errado.
- **Correcao [?]:** gate de reconciliacao simetrico na aprovacao da fatura cliente; "Soma CTe" filtrando `status!='CANCELADO'`; modelar substituicao versionada. **Dimensao: EXIBICAO/PROCESSO · Severidade: ALTO [?].**

### I3 — CTe cancelado tratado como normal na tela das NF

- **[F~]** A Query 4 da listagem `/carvia/nfs` seleciona so `id, cte_numero, ctrc_numero` — **nao** o `status` (`nf_routes.py:215-232`).
- **[F~]** O template renderiza badge verde fixo `class="badge bg-success"` (`listar.html:201-213`); na mesma tela a coluna Fatura SABE diferenciar cancelada (`bg-danger`).
- **[F~]** O status so aparece ao abrir a NF (`detalhe.html:339`, badge `carvia-badge-cancelado` vermelho).
- **[F✓]** Nao ha campo distinguindo cancelado-SEFAZ de cancelado-interno: so `tpCTe=='1'` e tratado (`importacao_service.py:307-312`); `tpCTe` nao e persistido.
- **[L]** Um CTe cancelado parece receita viva na varredura; combinado com a "Soma CTe" do I2 (que inclui cancelados), gera **dupla contagem de receita** — enquanto o lado custo (FT) exclui cancelados (inconsistencia receita x custo).
- **Correcao [?]:** levar `status` a Query 4 + usar `carvia-badge-{{status}}`; persistir status fiscal SEFAZ separado do workflow; excluir CANCELADO das somas de receita. **Dimensao: EXIBICAO · Severidade: ALTO [?].**

### I4 — Excluir fatura em frete quebra o FK

> **Correcao de premissa [L]:** o mecanismo nao e "FK pendurada apontando para fatura inexistente" — e o **oposto**: `IntegrityError` que **bloqueia** o delete.

- **[F✓]** `carvia_fretes.fatura_cliente_id` e `fatura_transportadora_id` sao declarados **sem `ondelete=`** (`frete.py:92-105`); `conta_corrente.py:54-56` idem.
- **[F-DB]** No Postgres de producao, `pg_constraint.confdeltype` dessas FKs = `'a'` (NO ACTION); `carvia_custos_entrega.fatura_transportadora_id` = `'n'` (SET NULL). Contagens: **105 fretes** com `fatura_cliente_id`, **101** com `fatura_transportadora_id`, 0 em ContaCorrente (latente).
- **[F✓]** A fatura E setada no frete na criacao: `CarviaFrete.query.filter_by(operacao_id=op.id).update({'fatura_cliente_id': fatura.id})` (`fatura_routes.py:277-279`).
- **[F✓]** `admin_service.excluir_fatura_cliente` nullifica `CarviaOperacao` (`:214`) e `CarviaCteComplementar` (`:221`) mas **nunca** toca `CarviaFrete`; `excluir_fatura_transportadora` nullifica so `CarviaSubcontrato` (`:297`), esquecendo `CarviaFrete` e `ContaCorrente`.
- **[F~]** Nao ha `try/except/rollback` no `admin_service.py` em volta do `commit()` (`:249`); o route `admin_routes.py:94-105` so inspeciona `resultado['sucesso']`.
- **[L]** Como o frete segue apontando para a fatura e e NO ACTION, o `commit()` lanca `IntegrityError`, que sobe como **HTTP 500 cru** com sessao DB abortada -> excluir fatura com frete vinculado e impossivel pela UI.
- **[L]** Caso colateral: o CE (FK SET NULL) tem `fatura_transportadora_id` zerado pelo DB mas o service nao reverte `CE.status` -> CE orfao `VINCULADO_FT/PAGO` com FK NULL.
- **Correcao [?]:** nullificar `CarviaFrete`+`ContaCorrente` no service ANTES do delete **ou** migrar essas FKs para `ON DELETE SET NULL`; reverter `CE.status`; envolver o route em `try/except -> rollback` + flash. **Dimensao: FK · Severidade: ALTO [?].**

### I5 — Conciliacao nao filtra/usa destinatario

- **[F✓]** O motor `pontuar_documentos` calcula `score = sv*PESOS['valor'] + sd*PESOS['data'] + sn*PESOS['nome']` (`carvia_sugestao_service.py:99-103`); `sn = _score_nome(texto_extrato, doc.get('nome',''))` (`:97`).
- **[F~]** `doc['nome']` para fatura cliente = `f.nome_cliente or f.cnpj_cliente` = o **pagador** (`carvia_conciliacao_service.py:166`).
- **[F✓]** O override deterministico de CNPJ compara so `doc.get('cnpj_cliente') or doc.get('cnpj_transportadora')` (`sugestao_service.py:109`) — destinatario nao entra.
- **[F~]** O destinatario e carregado so para exibicao em `_enriquecer_fatura_cliente_para_conciliacao` (`conciliacao_service.py:1023-1026`), nunca lido por `pontuar_documentos`; o filtro de candidatos (`conciliacao_routes.py:294-301`) tambem ignora destinatario.
- **[L]** Linhas cujo pagador bancario e o destinatario recebem score de nome 0 e nao casam por CNPJ direto, mesmo com o CNPJ do destinatario na descricao.
- **Correcao [?]:** destinatario como sinal adicional (nao filtro duro); ampliar override e `_score_nome` para {pagador, remetente, destinatarios[]}; unificar os 2 motores de score; ancorar no `cte_tomador` real. **Dimensao: VINCULACAO · Severidade: MEDIO [?].**

### I6 — Conciliacao nao prioriza linhas historicas por tomador

- **[F✓]** O INSERT do aprendizado grava `tipo_documento='fatura_cliente'` **HARDCODED** (`carvia_historico_match_service.py:182`), apesar de o hook aceitar 4 tipos.
- **[F✓]** A consulta filtra `tipo_documento == 'fatura_cliente'` HARDCODED (`:242`; e `:303` no batch **[F~]**).
- **[F~]** O boost casa por `cnpj_doc = cnpj_cliente OR cnpj_transportadora` (`sugestao_service.py:109,133-151`); para FT so haveria boost por colisao de CNPJ com um pagador-de-cliente aprendido.
- **[L]** O aprendizado R17 so funciona de fato para **recebimento de cliente**; o lado pagar (subcontrato/transportadora) nao tem priorizacao por historico; `cte_tomador` nunca participa; o indice `(descricao_tokens, tipo_documento)` e morto (cardinalidade 1 na 2a coluna).
- **Correcao [?]:** gravar o tipo real; consultar particionando por direcao/tipo; ancorar a chave na contraparte de dominio (tomador/transportadora), nao no pagador agregado. **Dimensao: VINCULACAO · Severidade: MEDIO [?].**

### I7 (exemplo) — Fatura manual registra tomador = emitente

- **[F✓]** `fatura_cnpj = pagador_cnpj if pagador_cnpj else cnpj_cliente`, com comentario *"# Pagador: usar selecionado ou default (remetente)"* (`fatura_routes.py:251-252`).
- **[F~]** No import de CTe XML, `cnpj_cliente = rem.get('cnpj')` = o **remetente** (`importacao_service.py:2013`).
- **[F~]** A lista de candidatos a pagador inclui so Remetente + Destinatarios das NFs, **ignorando** `cte_tomador` (`fatura_routes.py:407-441`).
- **[F✓]** `cte_tomador` e puramente display: `resolver_tomador` retorna `{codigo,label_visual,label_completo}` sem CNPJ (`tomador.py:45-60`); `_LABEL_MAP` cobre so `REMETENTE->emitente`, `DESTINATARIO->destinatario` (`:13-16`).
- **[F~]** A emissao propria SSW hardcoda `cnpj_tomador = dest.cnpj` (destinatario) (`cotacao_v2_routes.py:3617-3733`), sem ramo para remetente/terceiro.
- **[L]** Em CIF/FOB com tomador != remetente, a fatura nasce com o CNPJ errado e nada avisa; no caso `toma4` (terceiro) o pagador real nem e candidato porque seu CNPJ foi descartado no import.
- **Correcao [?]:** reter a entidade-tomador no import; pre-selecionar o pagador pelo `cte_tomador`; alertar (sem bloquear, dado que a fatura agrupa N CTes) quando o pagador diverge do papel-tomador; unificar o tomador da emissao SSW com o SOT. **Dimensao: VINCULACAO · Severidade: MEDIO [?].**

---

## 4. Gaps adicionais por dimensao

Gaps NOVOS (alem dos 7 acima e dos 37 ja resolvidos). Toda linha tem `arquivo:linha` **[F~]** salvo onde marcado **[F✓]** (re-lido pelo autor). As colunas **Consequencia** sao **[L]** e as **Severidades** sao **[?]** (julgamento). Ha sobreposicao intencional entre dimensoes (o mesmo defeito de fundo aparece em varios lugares).

### 4.1 Macro processo

| ID | Gap | Evidencia | Sev. [?] |
|----|-----|-----------|----------|
| M1 | Margem real por carga nunca e computada (usa cotacao, nao CTe); properties de margem sao dead code | `frete.py:71-72,185-196`; `gerencial_service.py:136-156`; `margem_service.py:75-85` | ALTO |
| M2 | Conferencia assimetrica: custo gateado (R$5/R$1), venda sem gate de cobertura/margem (vender abaixo do custo passa) | `aprovacao_frete_service.py:79-100`; `fatura_routes.py:950-957` **[F✓ o gate]** | ALTO |
| M3 | Status fiscal SEFAZ ausente como dimensao; CANCELADO colapsa interno x fiscal | schema `carvia_operacoes.json`; `documentos.py:391-392` vs `:63-66` | ALTO |
| M4 | `tpCTe=2`(Anulacao)/`tpCTe=3`(Substituto) viram receita nova positiva (so `tpCTe=1` reclassificado) | `importacao_service.py:307-312` **[F✓]**; `cte_xml_parser.py:122-133` | ALTO |
| M5 | Complementar de CUSTO (subcontratado emite complementar) nao tem fluxo — vira sub solto | `importacao_service.py:2192-2246`; `cte_custos.py:11-106` | MEDIO |

### 4.2 Processo

| ID | Gap | Evidencia | Sev. [?] |
|----|-----|-----------|----------|
| P1 | CTe de venda entra como receita sem gate de autorizacao SEFAZ (`cStat`); nasce `RASCUNHO` hardcoded | `importacao_service.py:2004-2041`; `cte_complementar_persistencia.py:477-481` | ALTO |
| P2 | CTe cancelado na SEFAZ sem caminho de ENTRADA (parser nao trata `<procEventoCTe>`/`110111`) | `cte_xml_parser_carvia.py:473-483` | ALTO |
| P3 | Import de subcontrato orfao de operacao falha sem registro re-linkavel (XML ja foi ao S3) | `importacao_service.py:2207-2213`; `linking_service.py:268` | ALTO |
| P4 | Anexar item a FT ja PAGA cria item `FATURADO` que nunca sera pago (`pode_anexar_item` sempre True) | `faturas.py:437-457`; `fatura_routes.py:1570-1616` | ALTO |
| P5 | FT quitavel (PAGO) com `valor_total` digitado livre sem lastro de subcontratos; conferencia sobrescreve em vez de travar | `fatura_routes.py:1483,2470`; `carvia_conciliacao_service.py:202-232` | ALTO |
| P6 | Listagem de operacoes mostra CANCELADO por default (assimetria com export de NF) | `operacao_routes.py:61-62`; `exportacao_routes.py:178-183` | BAIXO |

### 4.3 Vinculacao

| ID | Gap | Evidencia | Sev. [?] |
|----|-----|-----------|----------|
| V1 | Subcontrato importado nunca e vinculado ao `CarviaFrete` (eixo) — so `operacao_id`, `frete_id=NULL` | `importacao_service.py:2268-2286`; `frete.py:138-144` | ALTO |
| V2 | Comp->Frete por `.first()` sobre `operacao_id` (relacao 1:N sem UNIQUE) — pode pendurar no frete errado | `importacao_service.py:1010-1014`; `frete.py:98-101,177-182` | ALTO |
| V3 | NF<->Frete e CSV de `numero_nf`, descarta `serie_nf`; `numero_nf` nao e UNIQUE -> colisao | `frete.py:49`; `documentos.py:16-17,155-160` | ALTO |
| V4 | `toma4` (terceiro com CNPJ proprio) perde o CNPJ na persistencia — vinculo tomador->entidade destruido | `cte_xml_parser_carvia.py:507-516`; `importacao_service.py:2001-2002` | MEDIO |
| V5 | Hard-delete de fatura nao desfaz `CarviaFrete.fatura_*_id` (vinculo bidirecional desfeito de um lado) | `fatura_routes.py:277-279` **[F✓]**; `admin_service.py:209-224,286-299` **[F✓]** | MEDIO |
| V6 | Conciliacao/Movimentacao polimorficas sem FK — doc removido deixa conciliacao orfa | `financeiro.py:281-283,100-102` | MEDIO |
| V7 | Pedido<->NF<->Cotacao por string `numero_nf` (cadeia R16 pre-pago) — colisao resolve cotacao errada | `previnculo_service.py:387-389,413-422`; `cotacao.py:548` | BAIXO |

### 4.4 Integridade de FK

> Caveat de metodo **[?]**: `ON DELETE` foi lido do ORM. So o I4/FK1 foi confirmado no Postgres de producao (**[F-DB]**). Os demais assumem que a constraint reflete o model.

| ID | Gap | Evidencia | Sev. [?] |
|----|-----|-----------|----------|
| FK1 | `carvia_fretes`+`conta_corrente` com FK NO ACTION; hard-delete de fatura bloqueia (I4) | `frete.py:92-105` **[F✓]**; `conta_corrente.py:54-56` **[F✓]**; prod **[F-DB]** | ALTO |
| FK2 | Conciliacao/Movimentacao polimorficas + limpeza assimetrica (CE filho fica com conciliacao orfa) | `financeiro.py:281-283`; `admin_service.py:113-130` | CRITICO |
| FK3 | Anexos polimorficos sem FK -> deletar frete/sub deixa anexos S3 orfaos | `anexos.py:31-37` | ALTO |
| FK4 | `numeros_nfs` CSV + match `ILIKE '%nf%'` inconsistente (NF "123" casa "1234") | `frete.py:49`; `frete_routes.py:761`; `custo_entrega_routes.py:1011`; `pedido_routes.py:534,700` | ALTO |
| FK5 | FK deprecated viva `CarviaFrete.subcontrato_id` (1:1) coexiste com `frete_id` (1:N), ambas escritas | `frete.py:81-91` **[F✓]**; `frete_routes.py:896,1060`; `fatura_routes.py:1614,1727` | ALTO |
| FK6 | Numero sequencial `MAX()+1` sem lock/sequence; colunas de numero sem UNIQUE isolado | `documentos.py:591-606`; `cte_custos.py:88-103`; `faturas.py:84-99` | MEDIO |
| FK7 | Assimetria cascade em junction + divergencia DB x ORM (delete-orphan sem `ondelete` no DB) | `documentos.py:617-626`; `cte_custos.py:81-86,151-156` | MEDIO |
| FK8 | `SET NULL` em `CustoEntrega.fatura_transportadora_id` nao reverte `status` (CE orfao VINCULADO_FT/PAGO) | `cte_custos.py:214-216`; `admin_service.py:294-308` | MEDIO |
| FK9 | `HistoricoMatch.conciliacao_id` ponteiro solto nao-FK (tolerable, append-only) | `financeiro.py:510-511` | BAIXO |

### 4.5 Exibicao / ligacoes de dados

| ID | Gap | Evidencia | Sev. [?] |
|----|-----|-----------|----------|
| E1 | "Soma CTe" da fatura cliente conta CANCELADO que a propria tabela exibe com badge vermelho (auto-contradicao) | `detalhe.html:259` **[F✓]**,`449-461`; `fatura_routes.py:2024-2030` | ALTO |
| E2 | `tpCTe=2/3` exibido como venda normal positiva (entra na soma do gerencial) | `listar_operacoes.html:242-243`; `gerencial_service.py:167,598` | ALTO |
| E3 | Cancelado-SEFAZ vs cancelado-interno: mesmo badge `CANCELADO` | `documentos.py:391-392` vs `:63-66`; `_carvia.css:57-60` | MEDIO |
| E4 | `valor_total` vs soma exibidos lado a lado sem badge de divergencia (cliente e FT) | `faturas_transportadora/visualizar.html:90,178,187-195`; `detalhe.html:117,259` | MEDIO |
| E5 | `toma4` exibe so "Tomador: Terceiro" sem CNPJ/nome (entidade perdida no import) | `_macros.html:208-216`; `tomador.py:13-24` **[F✓]** | MEDIO |
| E6 | Detalhe de conciliacao da FT sem Remetente/Destinatario (assimetria com fatura_cliente) | `conciliacao_routes.py:1116-1133`; `conciliacao.js:284-299` | BAIXO |
| E7 | Badges de CTe/NF/destinatario no painel de conciliacao incluem cancelados como ativos | `carvia_conciliacao_service.py:997-1021` | BAIXO |

---

## 5. Priorizacao sugerida

> **Todo este bloco e [?]** (julgamento de prioridade — confirmar com o negocio). Atacar a falha **B** primeiro resolve I5, I6, I7 e o exemplo de uma vez.

1. **B + FK1 + FK2** — entidade-tomador concreta (preservar `toma4`, derivar pagador do `cte_tomador`) + tampar a quebra de FK do I4 (`SET NULL` + nullificacao no service + `try/except`) + limpeza simetrica das conciliacoes polimorficas.
2. **C** — dimensao fiscal do CTe (`tpCTe` + status SEFAZ): resolve I3, M3, M4, P1, P2, E2, E3 (todos sintomas do mesmo buraco).
3. **D** — gate de soma simetrico (cliente) + excluir cancelados da soma (I2/E1) + conceito de substituicao.
4. **A** — popular `frete_id` no import do subcontrato (V1) + margem real por carga (M1) + gate de cobertura na venda (M2).

---

## 6. Limites desta analise (risco de alucinacao)

Itens **[?]** que NAO foram verificados no codigo e devem ser tratados como hipotese ate confirmacao:

1. **O "modelo conceitual ideal" (Secao 1) inteiro** — e raciocinio de dominio do autor, nao um fato sobre o codigo nem uma regra de negocio confirmada com a operacao da CarVia. Pode haver razao de negocio para decisoes atuais (ex.: a fatura agrupar N CTes com tomadores distintos justifica nao haver tomador unico — citado em R19).
2. **Todas as severidades e a priorizacao** — julgamento; nao medem frequencia real de ocorrencia em producao.
3. **Premissas de frequencia de dominio** — afirmacoes como "comum em frete FOB", "caso raro no B2B moto" sao suposicoes nao medidas.
4. **`ON DELETE` dos FKs (exceto I4/FK1)** — lido do ORM, nao confirmado no Postgres de producao. Onde se afirma "PG bloquearia/cascadearia", assume-se que a constraint reflete o model.
5. **Comportamento do parser DACTE PDF** (`DactePDFParser`) quanto a extrair `tpCTe` — **nao lido**. Se o complementar/anulacao chega so como PDF, a reclassificacao do pass 2 (que depende de `cte.get('tipo_cte')`) pode nao ocorrer — hipotese nao confirmada.
6. **Divergencia de 1 digito na extracao de `numero_nf` da chave** (`[25:34]` no parser estendido vs `[25:33]` na base) — notada por subagente, **nao re-verificada** pelo autor.
7. **Ausencia de `try/except` no `admin_service.py`** (parte do mecanismo do I4) — **[F~]** por subagente via grep; nao re-lido linha a linha pelo autor.
8. **Linhas `arquivo:linha` marcadas [F~]** podem ter sofrido drift se o codigo mudou apos a coleta (2026-06-05/06). Reconfirmar a linha antes de editar.

> Para corrigir qualquer item, **reconfirmar a `arquivo:linha`** no codigo vigente antes de agir — esta revisao e um mapa, nao um patch.

---

> **Hub:** [CarVia — Guia de Desenvolvimento](CLAUDE.md) · **Relacionado:** [REVISAO_GAPS.md](REVISAO_GAPS.md) (37 gaps anteriores, resolvidos).
