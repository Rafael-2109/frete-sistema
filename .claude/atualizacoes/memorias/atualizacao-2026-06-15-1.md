# Atualizacao Memorias — 2026-06-15-1

**Data**: 2026-06-15
**Memorias auditadas**: 154/154 (estado inicial) → 153 (estado final)
**Removidas**: 2 | **Consolidadas (merges no indice)**: ~22 entradas em ~11 linhas | **Atualizadas**: 1 (indexada novo orfao)

## Resumo

Decima-segunda auditoria. Sistema estruturalmente saudavel: frontmatter 153/153 OK, 0 links quebrados, 0 orfaos no estado final. Problema central era MEMORY.md **estourando os DOIS limites** — 175 linhas (> teto 150 do procedimento) e 27.7KB (> ~24.4KB do harness, TRUNCANDO o load e perdendo a secao final Historico, conforme warning do proprio harness). Acao: removidos 2 stubs 100% redundantes ja marcados `PROMOVIDA` (conteudo versionado em CLAUDE.md/references, auto-carregado) + condensacao do indice via merges tematicos. MEMORY.md baixou para **149 linhas** (abaixo do teto do procedimento). Byte count em 26.3KB: nao perseguido alem disso por Guideline #2 ("nao perseguir o byte nem remover fato valido") — o excesso reflete crescimento legitimo para 153 memorias (+40 desde a auditoria que cabia em 19.7KB com 113 files), e cortar mais exigiria destruir recall valido.

## Acoes Realizadas

### Remocoes (2) — APOSENTADORIA OBRIGATORIA (Guideline #6)
- Removido `feedback_carvia_anexar_semantica.md` — stub PROMOVIDA cujo conteudo esta integral em `app/carvia/CLAUDE.md` R20 (verificado, linha 221). Redundante com CLAUDE.md auto-carregado (Guideline #3).
- Removido `gotcha_cd_company_id_odoo.md` — stub PROMOVIDA cujo conteudo esta integral em `.claude/references/odoo/IDS_FIXOS.md` (verificado, nota ARMADILHA linha 54, que ate cita a propria promocao). Redundante.

### Mantidas com ponteiro (stubs PROMOVIDA/APOSENTADA que ainda agregam)
- `regra_direcao_migracao_diff_qtd.md` — promovida a estoque/CLAUDE.md §8.1, MAS o stub carrega aviso de que a description antiga estava INVERTIDA (previne re-confiar em dado ruim). Pointer mantido.
- `gotcha_mo_mark_done_picked_xmlrpc.md` — APOSENTADA (G-MO-05 em concluir_mo), MAS tem corolario AINDA NAO codificado (limpeza de producao fantasma via quant custo-zero). Pointer mantido.

### Condensacao do indice (sem perda de fato)
- ~22 entradas de link unico mescladas em ~11 linhas compartilhadas (separador ` · `, gancho compartilhado), tecnica documentada das auditorias anteriores. Removeu apenas overhead de linha/link; todos os fatos preservados.
- Trim de filler (palavras conectivas redundantes) em ~6 ganchos longos.

### Indexacao de orfao novo
- `feedback_limpeza_nao_tocar_modulo_ativo.md` (criado concorrentemente nesta sessao, sessao 383df84a) — memoria de feedback substantiva e valida, sem ponteiro. Indexada na secao User & Feedback junto a `feedback_rastrear_acesso_ui_completo` (que ela reforca).

## Estado Final
- Total memorias (topic files): **153** (era 154; -2 removidas, +1 orfao novo ja existente)
- MEMORY.md: **149 linhas** / 26.3KB
- Frontmatter: 153/153 OK (`name`/`description`/`type`)
- Links: 153 referenciados, 153 existem, 0 quebrados
- Orfaos: 0
- Backup: `~/backups_memoria_dev_2026-06-15.tar.gz`

## Nota sobre o byte limit
26.3KB segue acima do ~24.4KB do harness. Decisao consciente de NAO cortar mais: (a) procedimento exige <150 linhas (cumprido); (b) Guideline #2 veta perseguir o byte ou remover fato valido; (c) preferencia registrada do usuario "completude > tamanho". Caminho futuro para o byte (se virar dor real): consolidar topic files de casos de inventario ja totalmente resolvidos+revertidos em 1 arquivo "casos-inventario-historico", reduzindo a contagem de paths longos no indice — porem requer confirmacao de que os casos estao mesmo encerrados (varios ainda tem PENDENTE).
