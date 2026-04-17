"""
Migration: Fix baseline de conciliacoes do Marcus (user_id=18)

Problema: Marcus precisa "esquentar" o agente todo dia de manha pois, mesmo
apos definir um baseline (formato canonico de planilha Excel para extratos
pendentes), o agente entrega arquivos com colunas erradas, abas erradas,
fonte de dados errada, exigindo 7+ correcoes por sessao.

Causa raiz mapeada:
1. preferences.xml do Marcus so documenta 2 de 4 abas (incompleto)
2. Memoria 536 (protocolo baseline) tem importance 0.5 + nivel 3 + path
   /protocolos/ - NAO entra em <operational_directives> (filtro requer
   /heuristicas/, importance>=0.7, nivel=5)
3. Memoria 534 (consolidated.xml) esta sem embedding e com escopo errado
   (pessoal em vez de empresa) - nao puxada pela busca semantica

Acoes:
1. Sobrescrever /memories/preferences.xml do user_id=18 com 4 abas canonicas
2. Atualizar /memories/user.xml do user_id=18 (item 7 apontando para skill)
3. Promover memoria 536 para nivel 5 + importance 0.95 + path /heuristicas/
4. Corrigir memoria 534: escopo empresa + gerar embedding
5. Registrar pitfall estrutural sobre filtro de operational_directives

Ref: docs/superpowers/plans/o-usuario-marcus-me-calm-parrot.md
Data: 2026-04-16
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


NEW_PREFERENCES_CONTENT = """<preferences updated="2026-04-17" source="baseline-completion-plan" priority="mandatory">
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
"""

USER_XML_ADDITIONAL_ITEM = """ (7) Para qualquer gatilho de baseline de conciliacao (atualizar baseline, foto das conciliacoes, extratos pendentes por mes): consultar /memories/preferences.xml secao baseline_conciliacoes como FONTE UNICA do formato. Preferencia: invocar skill gerando-baseline-conciliacao antes de escrever qualquer SQL ou gerar planilha. O formato tem 4 abas fixas (Pendentes Mes x Journal, Pendentes, Conciliacoes Dia Anterior, Resumo) - NUNCA gerar variacao sem autorizacao explicita do Marcus."""

PROMOTED_MEMORY_536_CONTENT = """<heuristica id="financeiro_baseline_extratos_formato_travado" updated_at="16/04/2026">
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
"""

PITFALL_CONTENT = """[pitfall:agente_memory_injection] Memorias de protocolo com importance<0.7 ou path /protocolos/ nao entram em <operational_directives>

WHEN: Ao salvar um protocolo operacional criado pelo usuario via sessao de correcao (ex: baseline de extratos, formato de planilha travado), o protocolo costuma ser categorizado como 'structural' com importance~0.5 e path /memories/empresa/protocolos/{dominio}/. Esse conteudo eh lido como memoria passiva em Tier 2 semantica, mas NAO entra no bloco <operational_directives> que o system_prompt instrui o agente a obedecer como regra.

Evidencia: baseline do Marcus (memory_id=536) ficou orfao entre 05/04 e 16/04. Agente errou formato 7 vezes em sessao unica por ler preferences.xml mas nao tratar como regra ativa. Filtro _build_operational_directives (memory_injection.py:360-368) exige: user_id=0, path LIKE /memories/empresa/heuristicas/%, importance_score >= 0.7 (MANDATORY_IMPORTANCE_THRESHOLD), e _is_nivel_5() retornando True.

DO:
1. Ao salvar protocolo critico com valor prescritivo (regras de formato, checklists de validacao), CATEGORIZAR como heuristica em vez de protocolo e adicionar <meta nivel=\"5\">.
2. Subir importance_score manualmente para >= 0.7 (ate 0.95 para itens mandatorios).
3. Considerar tambem alterar filtro do _build_operational_directives para aceitar /protocolos/ alem de /heuristicas/ (rever feature_flags.py USE_OPERATIONAL_DIRECTIVES e memory_injection.py linha 364).
4. Criar bloco <preference name=\"nome_regra\" priority=\"mandatory\"> em /memories/preferences.xml do usuario dono do protocolo como camada de backup - Tier 1 sempre injetado.

META: area=agente:memory_injection nivel=5 criterios=1,2,3,4
"""


def check_before(conn):
    print("=== BEFORE ===")
    result = conn.execute(text("SELECT id, length(content) AS len FROM agent_memories WHERE user_id=18 AND path='/memories/preferences.xml'"))
    row = result.fetchone()
    print(f"  preferences.xml user_id=18: {f'id={row[0]} len={row[1]}' if row else 'NAO EXISTE'}")

    result = conn.execute(text("SELECT id, length(content) AS len FROM agent_memories WHERE user_id=18 AND path='/memories/user.xml'"))
    row = result.fetchone()
    print(f"  user.xml user_id=18: {f'id={row[0]} len={row[1]}' if row else 'NAO EXISTE'}")

    result = conn.execute(text("SELECT id, importance_score, category, path FROM agent_memories WHERE id=536"))
    row = result.fetchone()
    print(f"  memoria id=536: {f'score={row[1]} cat={row[2]} path={row[3]}' if row else 'NAO EXISTE'}")

    result = conn.execute(text("SELECT id, escopo, path FROM agent_memories WHERE id=534"))
    row = result.fetchone()
    print(f"  memoria id=534: {f'escopo={row[1]} path={row[2]}' if row else 'NAO EXISTE'}")

    result = conn.execute(text("""
        SELECT m.id, CASE WHEN e.memory_id IS NULL THEN 'NO' ELSE 'YES' END AS has_emb
        FROM agent_memories m
        LEFT JOIN agent_memory_embeddings e ON e.memory_id = m.id
        WHERE m.id=534
    """))
    row = result.fetchone()
    print(f"  embedding id=534: {row[1] if row else 'NAO EXISTE'}")


def run_migration():
    from app.agente.models import AgentMemory, AgentMemoryVersion

    print("\n=== MIGRATION ===")

    # Passo 1: Atualizar preferences.xml do Marcus (user_id=18)
    print("\n[1/5] Atualizando preferences.xml (user_id=18)...")
    mem = AgentMemory.get_by_path(18, '/memories/preferences.xml')
    if not mem:
        print("  ERRO: preferences.xml do Marcus nao existe. Criar via MCP primeiro.")
        return False

    AgentMemoryVersion.save_version(mem.id, mem.content, changed_by='migration:marcus_baseline_fix')
    old_len = len(mem.content or '')
    mem.content = NEW_PREFERENCES_CONTENT
    mem.importance_score = 0.9
    mem.category = 'permanent'
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(mem, 'content')
    db.session.commit()
    print(f"  OK: preferences.xml atualizado (len {old_len} -> {len(NEW_PREFERENCES_CONTENT)}, 4 abas canonicas)")

    # Passo 2: Atualizar user.xml - adicionar item 7
    print("\n[2/5] Atualizando user.xml (user_id=18)...")
    mem_user = AgentMemory.get_by_path(18, '/memories/user.xml')
    if mem_user and mem_user.content:
        # Inserir item (7) antes do fechamento da tag contextualizacao
        content = mem_user.content
        if USER_XML_ADDITIONAL_ITEM.strip() in content:
            print("  SKIP: item 7 ja existe em user.xml")
        elif '</contextualizacao>' in content:
            AgentMemoryVersion.save_version(mem_user.id, mem_user.content, changed_by='migration:marcus_baseline_fix')
            new_content = content.replace(
                '</contextualizacao>',
                USER_XML_ADDITIONAL_ITEM + '</contextualizacao>'
            )
            mem_user.content = new_content
            flag_modified(mem_user, 'content')
            db.session.commit()
            print(f"  OK: item 7 adicionado em user.xml")
        else:
            print("  ERRO: tag </contextualizacao> nao encontrada - pular")
    else:
        print("  ERRO: user.xml do Marcus nao existe")

    # Passo 3: Promover memoria ID 536
    print("\n[3/5] Promovendo memoria ID 536 (protocolo baseline -> heuristica nivel 5)...")
    mem536 = AgentMemory.query.get(536)
    if mem536:
        AgentMemoryVersion.save_version(mem536.id, mem536.content, changed_by='migration:marcus_baseline_fix')
        mem536.content = PROMOTED_MEMORY_536_CONTENT
        mem536.importance_score = 0.95
        mem536.category = 'structural'
        # Mover path para /heuristicas/ para entrar em operational_directives
        mem536.path = '/memories/empresa/heuristicas/financeiro/baseline-de-extratos-formato-fixo.xml'
        flag_modified(mem536, 'content')
        db.session.commit()
        print(f"  OK: id=536 promovido (score=0.95, path=/heuristicas/, nivel=5)")
    else:
        print("  ERRO: memoria id=536 nao encontrada")

    # Passo 4: Corrigir memoria ID 534 (escopo + embedding)
    print("\n[4/5] Corrigindo memoria ID 534 (escopo pessoal->empresa + embedding)...")
    mem534 = AgentMemory.query.get(534)
    if mem534:
        if mem534.escopo != 'empresa':
            mem534.escopo = 'empresa'
            db.session.commit()
            print(f"  OK: escopo 534 alterado para 'empresa'")
        else:
            print(f"  SKIP: escopo 534 ja eh 'empresa'")

        # Gerar embedding best-effort
        try:
            from app.agente.tools.memory_mcp_tool import _embed_memory_best_effort
            _embed_memory_best_effort(mem534.user_id, mem534.path, mem534.content)
            print(f"  OK: embedding best-effort chamado para 534")
        except Exception as e:
            print(f"  WARN: embedding falhou (nao bloqueia): {e}")
    else:
        print("  ERRO: memoria id=534 nao encontrada")

    # Passo 5: Registrar pitfall
    print("\n[5/5] Registrando pitfall estrutural...")
    pitfall_path = '/memories/empresa/pitfalls/agente/memory-injection-protocolo-vs-heuristica.xml'
    existing_pitfall = AgentMemory.get_by_path(0, pitfall_path)
    if existing_pitfall:
        print(f"  SKIP: pitfall ja existe em {pitfall_path}")
    else:
        AgentMemory.create_file(0, pitfall_path, PITFALL_CONTENT)
        pitfall_mem = AgentMemory.get_by_path(0, pitfall_path)
        pitfall_mem.importance_score = 0.9
        pitfall_mem.category = 'structural'
        pitfall_mem.escopo = 'empresa'
        db.session.commit()
        print(f"  OK: pitfall registrado em {pitfall_path}")

    return True


def check_after(conn):
    print("\n=== AFTER ===")
    result = conn.execute(text("SELECT length(content) FROM agent_memories WHERE user_id=18 AND path='/memories/preferences.xml'"))
    row = result.fetchone()
    print(f"  preferences.xml user_id=18: len={row[0] if row else 'N/A'}")

    result = conn.execute(text("""
        SELECT id, importance_score, path FROM agent_memories
        WHERE path LIKE '/memories/empresa/heuristicas/financeiro/baseline%'
    """))
    for row in result:
        print(f"  heuristica baseline: id={row[0]} score={row[1]} path={row[2]}")

    result = conn.execute(text("SELECT id, escopo FROM agent_memories WHERE id=534"))
    row = result.fetchone()
    print(f"  id=534 escopo: {row[1] if row else 'N/A'}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE path LIKE '/memories/empresa/pitfalls/agente/%'"))
    print(f"  pitfalls agente registrados: {result.scalar()}")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            check_before(conn)

        ok = run_migration()
        if not ok:
            print("\n[FAIL] Migration interrompida. Verificar erros acima.")
            sys.exit(1)

        with db.engine.connect() as conn:
            check_after(conn)

        print("\n[OK] Migration concluida. Proximo passo: validar F4.")


if __name__ == '__main__':
    main()
