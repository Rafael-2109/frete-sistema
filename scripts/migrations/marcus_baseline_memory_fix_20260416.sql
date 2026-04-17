-- Migration: Fix baseline de conciliacoes do Marcus (user_id=18)
--
-- Problema: Marcus precisa "esquentar" o agente todo dia - agente entrega baseline
-- com formato errado (colunas, abas, fonte) mesmo com memorias ja salvas.
--
-- Causa raiz:
-- 1. preferences.xml do Marcus so documenta 2 de 4 abas
-- 2. Memoria 536 (protocolo baseline) importance 0.5 + nivel 3 + /protocolos/ -
--    NAO entra em <operational_directives>
-- 3. Memoria 534 (consolidated.xml) sem embedding + escopo errado
--
-- Ref: docs/superpowers/plans/o-usuario-marcus-me-calm-parrot.md
-- Data: 2026-04-16
--
-- NOTA: este SQL e idempotente mas NAO gera embeddings. Apos executar,
-- rodar: python .claude/skills/gerindo-agente/scripts/manutencao.py reindex-memories --user-id 0 --reindex
--       python .claude/skills/gerindo-agente/scripts/manutencao.py reindex-memories --user-id 18 --reindex

BEGIN;

-- ============================================================================
-- Passo 1: Backup dos conteudos atuais em agent_memory_versions
-- Schema real: (memory_id, content, version, changed_at, changed_by)
-- UNIQUE constraint: (memory_id, version) — calcular proximo version dinamicamente.
-- ============================================================================

-- Backup preferences.xml user_id=18
INSERT INTO agent_memory_versions (memory_id, content, version, changed_by)
SELECT m.id,
       m.content,
       COALESCE((SELECT MAX(v.version) FROM agent_memory_versions v WHERE v.memory_id = m.id), 0) + 1,
       'migration:marcus_baseline_fix_20260416'
FROM agent_memories m
WHERE m.user_id = 18 AND m.path = '/memories/preferences.xml';

-- Backup user.xml user_id=18
INSERT INTO agent_memory_versions (memory_id, content, version, changed_by)
SELECT m.id,
       m.content,
       COALESCE((SELECT MAX(v.version) FROM agent_memory_versions v WHERE v.memory_id = m.id), 0) + 1,
       'migration:marcus_baseline_fix_20260416'
FROM agent_memories m
WHERE m.user_id = 18 AND m.path = '/memories/user.xml';

-- Backup memoria 536
INSERT INTO agent_memory_versions (memory_id, content, version, changed_by)
SELECT m.id,
       m.content,
       COALESCE((SELECT MAX(v.version) FROM agent_memory_versions v WHERE v.memory_id = m.id), 0) + 1,
       'migration:marcus_baseline_fix_20260416'
FROM agent_memories m
WHERE m.id = 536;

-- ============================================================================
-- Passo 2: Atualizar preferences.xml do Marcus (user_id=18)
-- ============================================================================

UPDATE agent_memories
SET
  content = $MARCUSPREF$<preferences updated="2026-04-17" source="baseline-completion-plan" priority="mandatory">
  <preference name="PRESCRITIVO" priority="mandatory">
    <value>Preferencias abaixo sao REGRAS, nao sugestoes. Violar formato = erro grave. NUNCA gerar variacao sem autorizacao explicita.</value>
  </preference>

  <preference name="export_format">
    <value>Excel (.xlsx) sempre. Rejeitar HTML/CSV salvo pedido explicito.</value>
    <detail>QUANDO entregar resultados de levantamento, conciliacao, baseline ou relatorio, gerar automaticamente Excel sem aguardar solicitacao. QUANDO mostrar tabela no chat relevante ao arquivo, incluir automaticamente no Excel.</detail>
  </preference>

  <preference name="conciliacao_em_lote">
    <value>Apresentar tabela DATA|JOURNAL|DESCRICAO|VALOR antes de executar lote. NUNCA executar sem confirmacao do escopo.</value>
  </preference>

  <preference name="ritmo_processamento">
    <value>Processar um mes por vez. Aguardar confirmacao explicita antes de avancar para o proximo mes/lote.</value>
  </preference>

  <preference name="baseline_conciliacoes" priority="mandatory">
    <value>Relatorio de extratos pendentes de conciliacao - FORMATO TRAVADO, 4 abas fixas.</value>
    <trigger>Gatilhos exatos: "atualizar baseline", "atualizar a baseline", "baseline de conciliacao", "foto das conciliacoes", "foto atual das conciliacoes", "extratos pendentes por mes", "gerar baseline", "relatorio de extratos pendentes".</trigger>

    <skill_preferida>gerando-baseline-conciliacao</skill_preferida>

    <fonte>
      SEMPRE consultar Odoo: modelo account.bank.statement.line com is_reconciled=False.
      NUNCA usar tabela local extrato_item (acumula linhas ja conciliadas - 18.158 local vs 6.985 Odoo em 16/04/2026).
      Journals monitorados: SICOOB, GRAFENO, BRADESCO, AGIS GARANTIDA, VORTX GRAFENO.
      Para conciliacoes D-1: unir TRES fontes (extrato_item + lancamento_comprovante + carvia_conciliacoes).
    </fonte>

    <arquivo>extratos_pendentes_mes_journal_&lt;DDmmmYYYY&gt;.xlsx</arquivo>

    <abas>
      <aba nome="Pendentes Mes x Journal" posicao="1">
        Fonte: Odoo, is_reconciled=False.
        Colunas EXATAS e nessa ordem: Mes | Journal | Linhas | PGTOS | Valor Debitos | RECEB. | Valor Creditos.
        PGTOS = COUNT(linhas com amount &lt; 0).
        RECEB. = COUNT(linhas com amount &gt; 0).
        Valor Debitos = soma negativa (NAO abs).
        Valor Creditos = soma positiva.
        Rodape: linha TOTAL + secao "Evolucao Baseline" com historico (ex: 09/Abr=8.684, 16/Abr=6.985, delta).
      </aba>

      <aba nome="Pendentes" posicao="2">
        Linhas detalhadas (top N por valor absoluto).
        Schema da aba 1 explodido por linha individual do extrato.
        Incluir colunas adicionais: Data, Descricao, Partner, payment_id (se houver).
      </aba>

      <aba nome="Conciliacoes Dia Anterior" posicao="3">
        Conciliacoes feitas em D-1 (dia anterior) agrupadas por usuario.
        Colunas EXATAS: Usuario | Linhas | Pgtos | Valor Debitos | Rec | Valor Creditos.
        Usuario = NOME REAL do Odoo via write_uid (ex: Martha, Allanda, Vanderleia, Marcus) - NUNCA SYNC_ODOO_WRITE_DATE.
        FONTES obrigatorias (armadilha documentada): unir extrato_item + lancamento_comprovante + carvia_conciliacoes. Omitir fonte produz contagem/valores/usuarios incorretos sem sinalizacao de erro.
      </aba>

      <aba nome="Resumo" posicao="4">
        Tabela pivot hierarquica: Mes como grupo (com subtotal, fundo verde claro), Journals como sub-itens indentados.
        Colunas: Rotulos de Linha | Soma de PGTOS | Soma de RECEB.
        Ultima linha: "Total Geral".
      </aba>
    </abas>

    <validacao>
      ANTES de responder com arquivo, confirmar mentalmente:
      (1) fonte = Odoo account.bank.statement.line is_reconciled=False (NAO tabela local);
      (2) valores Debito = negativo (NAO abs);
      (3) usuarios D-1 = nomes reais write_uid (NAO SYNC_*);
      (4) 4 abas com nomes EXATOS (Pendentes Mes x Journal, Pendentes, Conciliacoes Dia Anterior, Resumo);
      (5) PGTOS = count(amount&lt;0), RECEB = count(amount&gt;0) - NUNCA usar payment_id IS NOT NULL.
    </validacao>

    <armadilhas_documentadas>
      - Usar tabela local extrato_item em vez de Odoo = contagem 2-3x maior por defasagem sync.
      - Nomear aba "Baseline" em vez de "Pendentes Mes x Journal" ou "Extratos Pendentes".
      - Valor Debitos positivo (deve ser negativo).
      - Omitir secao "Evolucao Baseline" no rodape da aba 1.
      - Exibir SYNC_ODOO_WRITE_DATE em vez do nome real do usuario.
      - Omitir aba D-1 (Conciliacoes Dia Anterior).
      - Calcular PGTOS/RECEB por payment_id IS NOT NULL (retorna zero - pendentes nao tem payment_id preenchido).
      - Gerar apenas 2 abas em vez de 4.
    </armadilhas_documentadas>
  </preference>
</preferences>
$MARCUSPREF$,
  importance_score = 0.9,
  category = 'permanent',
  updated_at = NOW()
WHERE user_id=18 AND path='/memories/preferences.xml';

-- ============================================================================
-- Passo 3: Adicionar item 7 em user.xml do Marcus se nao existir
-- ============================================================================

UPDATE agent_memories
SET
  content = REPLACE(
    content,
    '</contextualizacao>',
    ' (7) Para qualquer gatilho de baseline de conciliacao (atualizar baseline, foto das conciliacoes, extratos pendentes por mes): consultar /memories/preferences.xml secao baseline_conciliacoes como FONTE UNICA do formato. Preferencia: invocar skill gerando-baseline-conciliacao antes de escrever qualquer SQL ou gerar planilha. O formato tem 4 abas fixas (Pendentes Mes x Journal, Pendentes, Conciliacoes Dia Anterior, Resumo) - NUNCA gerar variacao sem autorizacao explicita do Marcus.</contextualizacao>'
  ),
  updated_at = NOW()
WHERE user_id=18
  AND path='/memories/user.xml'
  AND content NOT LIKE '%(7) Para qualquer gatilho de baseline%'
  AND content LIKE '%</contextualizacao>%';

-- ============================================================================
-- Passo 4: Promover memoria 536 (protocolo -> heuristica nivel 5)
-- ============================================================================

UPDATE agent_memories
SET
  path = '/memories/empresa/heuristicas/financeiro/baseline-de-extratos-formato-fixo.xml',
  content = $MEM536$<heuristica id="financeiro_baseline_extratos_formato_travado" updated_at="16/04/2026">
  <tag>[heuristica:financeiro] baseline de extratos exige formato fixo de colunas e 4 abas</tag>
  <meta nivel="5" criterios="1,2,3,4" protected_from_consolidation="true"/>
  <fonte_autoritativa>/memories/preferences.xml secao &lt;preference name="baseline_conciliacoes"&gt;</fonte_autoritativa>

  <when>
    O arquivo de baseline de extratos pendentes tem formato canonico definido pelo usuario Marcus (user_id=18, Controller Financeiro). Gatilhos textuais: "atualizar baseline", "atualizar a baseline", "baseline de conciliacao", "foto das conciliacoes", "extratos pendentes por mes", "gerar baseline". O agente ja gerou formato incorreto 7+ vezes em sessao unica exigindo correcao interativa. Formato travado e 4 abas EXATAS:
    (1) "Pendentes Mes x Journal" - Mes|Journal|Linhas|PGTOS|Valor Debitos|RECEB.|Valor Creditos + rodape Evolucao Baseline;
    (2) "Pendentes" - linhas detalhadas top N por valor absoluto;
    (3) "Conciliacoes Dia Anterior" - Usuario|Linhas|Pgtos|Valor Debitos|Rec|Valor Creditos usando nomes reais do write_uid;
    (4) "Resumo" - pivot hierarquica Mes&gt;Journal com Soma de PGTOS e Soma de RECEB.
    Fonte obrigatoria: Odoo account.bank.statement.line is_reconciled=False - NUNCA tabela local extrato_item. Valores debito sao negativos (nao abs). Pgtos=count(amount&lt;0), Rec=count(amount&gt;0) - NUNCA payment_id IS NOT NULL.
  </when>

  <do>
    1. Ao detectar gatilho de baseline, INVOCAR a skill gerando-baseline-conciliacao (preferencia) ou, se indisponivel, seguir preferences.xml do usuario a risca.
    2. ANTES de responder com arquivo, validar 5 checkpoints:
       (a) fonte=Odoo is_reconciled=False (nao local);
       (b) Valor Debitos negativo;
       (c) usuarios D-1=nomes reais write_uid (nao SYNC_*);
       (d) 4 abas com nomes EXATOS listados acima;
       (e) Pgtos/Rec via sinal do amount, nao payment_id.
    3. Se o usuario pedir variacao (aba diferente, coluna extra, fonte diferente): RECUSAR e perguntar autorizacao explicita ("O formato esta travado em preferences.xml. Autoriza mudanca?"). NUNCA gerar layout alternativo sem confirmacao.
    4. Se a fonte Odoo divergir mais de 50% da tabela local ou expectativa previa, re-consultar Odoo antes de responder - cache de sessao pode estar defasado por conciliacoes paralelas.
  </do>

  <fontes_dados>
    Odoo account.bank.statement.line (is_reconciled=False) - fonte primaria para abas 1, 2, 4.
    Aba 3 (D-1) exige UNIAO de tres fontes: extrato_item + lancamento_comprovante + carvia_conciliacoes - omitir produz contagem/valores/usuarios errados sem sinalizacao.
    Nomes reais via write_uid do Odoo (Martha, Allanda, Vanderleia, Marcus) - NUNCA SYNC_ODOO_WRITE_DATE.
  </fontes_dados>

  <historico_baseline>
    09/04/2026: 8.684 linhas (SICOOB 55,8%, GRAFENO 29,6%, BRADESCO 8,8%, AGIS 4,4%).
    16/04/2026: 6.985 linhas (-1.699, Pgtos=6.115, Rec=870). Tabela local nesse dia: 18.158 (NAO usar).
  </historico_baseline>
</heuristica>
$MEM536$,
  importance_score = 0.95,
  category = 'structural',
  updated_at = NOW()
WHERE id = 536;

-- ============================================================================
-- Passo 5: Corrigir memoria 534 (escopo pessoal -> empresa)
-- ============================================================================

UPDATE agent_memories
SET
  escopo = 'empresa',
  updated_at = NOW()
WHERE id = 534 AND escopo <> 'empresa';

-- ============================================================================
-- Passo 6: Registrar pitfall estrutural (user_id=0, empresa)
-- ============================================================================

INSERT INTO agent_memories (
  user_id, path, content, is_directory,
  created_at, updated_at,
  importance_score, category, is_cold, usage_count, effective_count, correction_count,
  has_potential_conflict, escopo, created_by
)
SELECT
  0,
  '/memories/empresa/pitfalls/agente/memory-injection-protocolo-vs-heuristica.xml',
  $PITFALL$[pitfall:agente_memory_injection] Memorias de protocolo com importance<0.7 ou path /protocolos/ nao entram em <operational_directives>

WHEN: Ao salvar um protocolo operacional criado pelo usuario via sessao de correcao (ex: baseline de extratos, formato de planilha travado), o protocolo costuma ser categorizado como 'structural' com importance~0.5 e path /memories/empresa/protocolos/{dominio}/. Esse conteudo eh lido como memoria passiva em Tier 2 semantica, mas NAO entra no bloco <operational_directives> que o system_prompt instrui o agente a obedecer como regra.

Evidencia: baseline do Marcus (memory_id=536) ficou orfao entre 05/04 e 16/04. Agente errou formato 7 vezes em sessao unica por ler preferences.xml mas nao tratar como regra ativa. Filtro _build_operational_directives (memory_injection.py:360-368) exige: user_id=0, path LIKE /memories/empresa/heuristicas/%, importance_score >= 0.7 (MANDATORY_IMPORTANCE_THRESHOLD), e _is_nivel_5() retornando True.

DO:
1. Ao salvar protocolo critico com valor prescritivo (regras de formato, checklists de validacao), CATEGORIZAR como heuristica em vez de protocolo e adicionar <meta nivel="5">.
2. Subir importance_score manualmente para >= 0.7 (ate 0.95 para itens mandatorios).
3. Considerar tambem alterar filtro do _build_operational_directives para aceitar /protocolos/ alem de /heuristicas/ (rever feature_flags.py USE_OPERATIONAL_DIRECTIVES e memory_injection.py linha 364).
4. Criar bloco <preference name="nome_regra" priority="mandatory"> em /memories/preferences.xml do usuario dono do protocolo como camada de backup - Tier 1 sempre injetado.

META: area=agente:memory_injection nivel=5 criterios=1,2,3,4
$PITFALL$,
  false,
  NOW(), NOW(),
  0.9, 'structural', false, 0, 0, 0,
  false, 'empresa', NULL
WHERE NOT EXISTS (
  SELECT 1 FROM agent_memories
  WHERE user_id=0 AND path='/memories/empresa/pitfalls/agente/memory-injection-protocolo-vs-heuristica.xml'
);

-- ============================================================================
-- Verificacao pos-migration
-- ============================================================================

-- Deve retornar 1 linha com len > 5000
SELECT 'preferences_marcus' AS item, length(content) AS valor
FROM agent_memories WHERE user_id=18 AND path='/memories/preferences.xml';

-- Deve retornar 1 linha com score=0.95
SELECT 'memoria_baseline_promovida' AS item,
       id, importance_score, path
FROM agent_memories WHERE id=536;

-- Deve retornar 1 linha com escopo='empresa'
SELECT 'memoria_534_escopo' AS item, id, escopo
FROM agent_memories WHERE id=534;

-- Deve retornar 1 linha (pitfall)
SELECT 'pitfall_registrado' AS item, COUNT(*) AS total
FROM agent_memories WHERE path LIKE '/memories/empresa/pitfalls/agente/%';

COMMIT;
