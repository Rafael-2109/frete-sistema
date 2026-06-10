<!-- doc:meta
tipo: relatorio
camada: L3
sot_de: —
hub: docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md
superseded_by: —
atualizado: 2026-06-10
-->
# Dry-run — consolidacao de memorias quase-duplicadas (curadoria F6)

> **Papel:** relatorio do dry-run de consolidacao dos pares quase-duplicados
> residentes no estore de memorias do Agente Web (curadoria F6 autorizada pelo
> Rafael — aplicar SOMENTE apos revisao deste relatorio). Anexo do plano
> `2026-06-09-arquitetura-contexto-boot-agente.md`.

## Metodo

- **Pares**: regenerados FRESCOS de PROD (read-only) em 2026-06-10 ~19:00Z com o
  MESMO metodo do A/B do dedup (`_canonicalize_for_dedup` + voyage-4-lite
  doc-doc, visibilidade do dedup): 482 memorias ativas → **94 pares >= 0.85**
  (eram 78 no corpus do A/B da manha — o estore cresceu).
- **Analise**: workflow `dryrun-consolidacao-duplicatas` (94 agentes Sonnet,
  1/par, conteudo INTEGRAL dos dois lados + metadados de uso). Regras
  conservadoras: perfil/contexto vivo nunca consolida; na duvida nao consolida;
  canonico = mais completo/usado; absorvida vira FRIA com ponteiro (nunca delete).
- **Zero escrita** — propostas apenas. Payload de aplicacao (com conteudo_merge
  integral por par): `~/.claude/projects/-home-rafaelnascimento-projetos-frete-sistema/535e1290-91e9-4fa0-8a23-5cfe063a43a1/f6_consolidacao_apply.json`.

## Resultado

| Veredito | Pares | Detalhe |
|---|---:|---|
| **consolidar** | **27** | canonico absorve delta; perdedora vira fria + meta consolidada_em |
| nao_consolidar — perfil/contexto vivo | 17 | user.xml/context/*/usuarios/* (falso-duplicata estrutural: perfil RESUME conhecimento) |
| nao_consolidar — complementares | 50 | mesma area, ensinam coisas DISTINTAS (consolidar destruiria conhecimento) |

Leitura: so ~29% dos pares >=0.85 sao duplicatas REAIS — confirma o achado do
A/B (gate binario por cosine nao separa duplicata de complementar; a fronteira
0.81-0.85 se sobrepoe). A consolidacao certa e semantica (LLM lendo os dois
lados), nao por threshold.

## As 27 propostas de consolidacao

| sim | canonico (fica) | absorvida (vira fria) | merge? | justificativa (resumo) |
|---|---|---|---|---|
| 0.921 | 496 `empresa/heuristicas/financeiro/pagamentos-receita-federal-tratados-como-faturas-de.xml` | 488 `empresa/heuristicas/financeiro/tributos-federais-recorrentes-formam-cluster-mensal-uniforme.xml` | sim | Ambas ensinam o mesmo fato central: débitos BRADESCO 'RECEITA FEDERAL/SP' formam cluster de 7 tributos no último dia útil, devem ser process… |
| 0.912 | 219 `empresa/regras/antes-de-realizar-operacoes-em-massa-em.xml` | 225 `empresa/regras/pedidos-de-venda-com-status-locked-dev.xml` | sim | Ambas ensinam regras de cancelamento de pedidos de venda no Odoo (empresa/regras). A (id=219) é mais completa: cobre draft (lote direto OK, … |
| 0.909 | 462 `empresa/armadilhas/recebimento/vinculacao-nf-po-exige-update-em-dois-sistemas.xml` | 265 `empresa/causas/financeiro/nfs-de-entrada-frequentemente-fazem-match-automati.xml` | sim | Ambas sao conhecimento empresa (user_id=0) sobre o mesmo processo — vinculacao NF-PO no recebimento, armadilhas e protocolos. Ensinam a MESM… |
| 0.907 | 511 `empresa/protocolos/financeiro/migracao-cnab-entre-bancos-exige-mais-que-troca-de-codigo.xml` | 513 `empresa/protocolos/remessa_cnab400_vortx_310.md` | sim | Ambas sao empresa/protocolos de conhecimento sobre migracao CNAB400 BMP/274->Vortx/310 e ensinam as mesmas armadilhas (campo multa pos 066, … |
| 0.907 | 512 `empresa/armadilhas/financeiro/nosso-numero-cnab-exige-unicidade-e-dac-por-algoritmo-do.xml` | 571 `empresa/armadilhas/financeiro/nosso-numero-dac-zero-grava-caracter-invalido.xml` | sim | Ambas as memorias ensinam a mesma armadilha: DAC módulo 11 em CNAB 400, casos de borda (resto=0/1 ou >=10 grava caractere inválido) e algori… |
| 0.905 | 369 `empresa/protocolos/financeiro/transferencias-internas-com-defasagem-entre-bancos.xml` | 373 `empresa/protocolos/financeiro/conciliacao-transferencias-set2025-pendencias.xml` | sim | Ambos são empresa/protocolos sobre conciliação de transferências internas (mesmo domínio, mesma área de conhecimento). O canônico (369) tem … |
| 0.898 | 311 `empresa/heuristicas/comercial/duplicacao-de-pedido-atacadao-por-reinsercao.xml` | 449 `empresa/heuristicas/comercial/duplicacao-de-pedido-assai-por-reimportacao-pdf.xml` | sim | Ambas sao heuristicas de conhecimento empresarial (empresa/heuristicas/comercial) sobre o mesmo dominio: deteccao e correcao de duplicacoes … |
| 0.897 | 451 `empresa/armadilhas/integracao/exclusao-em-massa-odoo-exige-lotes-pequenos-com-pausa.xml` | 447 `corrections/o-usuario-corrigiu-o-agente-ao-perceber-que-a-operacao-em-lo.xml` | nao | As duas memorias ensinam a mesma coisa: operacoes em massa no Odoo (unlink/cancel) exigem lotes pequenos para evitar 502 Bad Gateway por tim… |
| 0.892 | 306 `empresa/protocolos/recebimento/desvinculacao-nf-po-requer-limpeza-em-tres-tabelas.xml` | 462 `empresa/armadilhas/recebimento/vinculacao-nf-po-exige-update-em-dois-sistemas.xml` | sim | Ambas as memorias ensinam o mesmo dominio: vinculacao/desvinculacao NF-PO no recebimento, com atualizacao obrigatoria em Odoo+sistema local.… |
| 0.892 | 769 `empresa/armadilhas/carvia/frete-fracionada-zerado-sem-tabela-nem-cte-vinculado.xml` | 255 `empresa/regras/ao-alterar-o-campo-tabela-frete-minimo-v.xml` | sim | Ambas as memorias sao conhecimento empresa (user_id=0) sobre calculo e atualizacao de valores de frete CarVia. Ensinam a mesma area: multipl… |
| 0.891 | 344 `empresa/protocolos/recebimento/validacao-de-picking-bloqueada-por-qty-done-zero-e-qc-fail.xml` | 669 `empresa/armadilhas/expedicao/lot-id-disponivel-exige-query-em-stock-quant-nao-em-stock.xml` | sim | Ambos sao CONHECIMENTO x CONHECIMENTO (empresa, sem paths de perfil/sistema). O protocolo:estoque de b (reserva orfã + ML de lote esgotado b… |
| 0.889 | 715 `learned/patterns.xml` | 887 `corrections/agente-calculou-pedagio-por-faixas-do-peso-cubado-341kg-4-f.xml` | sim | Ambas as memorias ensinam a mesma regra central: calcular pedagio CarVia usa peso bruto, nao peso cubado. O canonico (715) e mais completo: … |
| 0.885 | 337 `empresa/heuristicas/integracao/pedido-criado-durante-janela-de-sync-nao-e-capturado.xml` | 339 `empresa/armadilhas/integracao/servico-atualizar-carteira-nao-faz-insert-de-pedido-novo.xml` | sim | Ambas ensinam o mesmo nucleo: o servico de sync de carteira nao faz INSERT de pedido novo, so UPDATE. A (id=337) e o canonico por ser mais a… |
| 0.881 | 511 `empresa/protocolos/financeiro/migracao-cnab-entre-bancos-exige-mais-que-troca-de-codigo.xml` | 512 `empresa/armadilhas/financeiro/nosso-numero-cnab-exige-unicidade-e-dac-por-algoritmo-do.xml` | sim | Ambas são memorias empresa/conhecimento sobre CNAB400 e migração entre bancos (Vórtx/310 em comum), com overlap substancial (0.88). A (id=51… |
| 0.880 | 265 `empresa/causas/financeiro/nfs-de-entrada-frequentemente-fazem-match-automati.xml` | 903 `learned/patterns.xml` | sim | Ambas as memorias ensinam armadilhas e protocolos do fluxo NF-PO (vinculacao, cache, bloqueios, De-Para). A memoria A (empresa, id=265) e ni… |
| 0.874 | 369 `empresa/protocolos/financeiro/transferencias-internas-com-defasagem-entre-bancos.xml` | 473 `empresa/heuristicas/financeiro/transferencias-internas-agis-garantida-e-vortx-agis-sao.xml` | sim | Ambas ensinam o mesmo domínio (conciliação de transferências internas entre journals do grupo Nacom Goya) com sobreposição central clara: pa… |
| 0.873 | 460 `empresa/heuristicas/operacional/respeitar-instrucoes-negativas-usuario.xml` | 476 `corrections/o-usuario-pediu-explicitamente-para-nao-fazer-o-padrao-juro.xml` | nao | Par EMPRESA (id=460, user_id=0, heuristicas/operacional) x PESSOAL (id=476, user_id=18, corrections/). Regra 4 se aplica: mesmo ensinamento … |
| 0.870 | 536 `empresa/heuristicas/financeiro/baseline-de-extratos-formato-fixo.xml` | 439 `corrections/o-usuario-teve-que-corrigir-o-agente-multiplas-vezes-sobre-o.xml` | nao | Ambas ensinam o mesmo conhecimento: o formato obrigatorio para o baseline de conciliacao de extratos. Regra 4 se aplica diretamente: memoria… |
| 0.868 | 255 `empresa/regras/ao-alterar-o-campo-tabela-frete-minimo-v.xml` | 715 `learned/patterns.xml` | sim | Par EMPRESA×PESSOAL (user_id=0 vs user_id=17) sobre operações CarVia. Pela regra 4, canônico = empresa (id=255). Os dois compartilham o domí… |
| 0.867 | 715 `learned/patterns.xml` | 740 `corrections/usuario-corrigiu-frete-subcontratado-nao-gera-credito-de-ic.xml` | sim | Ambas as memorias sao CONHECIMENTO x CONHECIMENTO do mesmo usuario (user_id=17) e ensinam parcialmente a mesma regra: frete subcontratado de… |
| 0.867 | 804 `empresa/heuristicas/producao/estoque-virtual-producao-indica-apontamentos-pendentes-nao.xml` | 820 `empresa/heuristicas/producao/salmoura-produzida-em-localizacao-errada-trava-op-filha.xml` | sim | Ambas são heurísticas de produção (empresa x empresa, mesma área) que ensinam causas e correções de saldo incorreto/bloqueio de MP em ordens… |
| 0.862 | 638 `empresa/armadilhas/carvia/update-frete-cotacao-bloqueado-ui-mas-seguro-sem-cte.xml` | 255 `empresa/regras/ao-alterar-o-campo-tabela-frete-minimo-v.xml` | sim | Ambas ensinam sobre atualização de valores de frete CarVia e a ausência de sincronização automática entre entidades (carvia_fretes, carvia_s… |
| 0.862 | 897 `empresa/armadilhas/financeiro/periodo-travado-bloqueia-reclassificacao-de-lancamentos.xml` | 901 `empresa/armadilhas/financeiro/reclassificacao-de-ativo-para-cpv-impacta-balanco-e-dre.xml` | sim | Ambas são armadilhas empresa/financeiro sobre reclassificação contábil no Odoo com período travado. Ensinam o mesmo núcleo (dry-run, ciclo d… |
| 0.859 | 625 `empresa/heuristicas/carvia/tde-automatica-dago-deve-entrar-como-despesa-extra.xml` | 740 `corrections/usuario-corrigiu-frete-subcontratado-nao-gera-credito-de-ic.xml` | sim | Ambas as memórias ensinam a mesma regra: frete subcontratado deve ser gravado como valor líquido sem ICMS. Memory A (empresa, id=625) é mais… |
| 0.856 | 366 `empresa/protocolos/estoque/diagnostico-de-estoque-inflado-por-cancelamento-assimetrico.xml` | 902 `empresa/heuristicas/estoque/pickings-antigos-pendentes-inflam-posicao-de-item.xml` | sim | Ambas as memorias ensinam sobre estoque inflado/reservas distorcidas no mesmo domínio (empresa/estoque), mas cobrem causas distintas: 'a' co… |
| 0.854 | 866 `learned/consolidated.xml` | 903 `learned/patterns.xml` | sim | Ambas são memórias pessoais (user_id=69) sob /memories/learned/ ensinando padrões operacionais do mesmo domínio (vinculação NF-PO, cache, de… |
| 0.852 | 489 `empresa/heuristicas/financeiro/tarifas-bancarias-pendentes-acumulam-por-meses-sem.xml` | 435 `empresa/armadilhas/financeiro/iof-usa-conta-especifica-22771-nao-despesas-bancarias.xml` | sim | Ambas ensinam a mesma coisa: roteamento de contas no Odoo para tarifas bancárias (conta TRANSITÓRIA 22199 → 22767/22771). B (id=489) é canôn… |

## Plano de aplicacao (apos OK do Rafael)

Para cada par aprovado, em transacao unica (PROD via psql, verificacao
before/after):
1. Se ha `conteudo_merge`: UPDATE do content do CANONICO (backup do conteudo
   anterior via memory_versions/historico padrao).
2. Absorvida: `is_cold=true` + `meta.consolidada_em = <id canonico>` (NUNCA
   delete — search_cold_memories continua achando).
3. DELETE da linha de `agent_memory_embeddings` do canonico alterado (reindex
   diario re-embeda) e da absorvida.
4. Invalidacao: cache de injecao expira por TTL 30min (sem acao).

Opcoes de execucao: (a) aplicar as 27; (b) aplicar so as sem-merge (absorvida
e' subconjunto puro — risco minimo); (c) revisar par-a-par as com-merge (24 das 27
tem conteudo_merge redigido no payload; 3 sao absorcao pura).
