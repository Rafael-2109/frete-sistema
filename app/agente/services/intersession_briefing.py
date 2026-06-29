"""
Briefing Inter-Sessão MVP (Memory System v2 — Fase 3A).

Gera bloco XML compacto (~400 chars) com eventos ocorridos entre sessões:
- Erros de sync Odoo (últimas 6h)
- Falhas de importação de pedidos
- Estado de memórias (conflitos, cold candidates)
- Commits recentes no repositório (git log)

F4.1 PAD-CTX (2026-06-09): blocos NAO-operacionais relocados para consulta
on-demand — `stale_empresa` e `intelligence_report` sairam do boot (info
acessivel via tela admin /agente/memorias e rotas D7); `improvement_responses`
so entra com AGENT_IMPROVEMENT_INJECT_BOOT=true (default off — a flag
AGENT_IMPROVEMENT_DIALOGUE segue governando apenas o DIALOGO D8). Excecao
condicional F4.5: `get_skill_bug_responses_for_skill` devolve a response de
skill_bug ao contexto SOMENTE no turno que usa a skill afetada (consumida
pelo PreToolUse da Skill tool em sdk/hooks.py).

Sem nova tabela — queries diretas em tabelas existentes.
Best-effort: falhas são logadas silenciosamente.

Custo: zero (queries SQL leves + git log, sem chamada LLM).
Trigger: início de cada sessão, via Tier 0b em client.py.
"""

import logging
import os
import subprocess
from typing import Optional

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def build_intersession_briefing(user_id: int, agente_id: str = 'web') -> Optional[str]:
    """
    Gera briefing inter-sessão: o que mudou desde a última sessão do usuário.

    Queries leves em tabelas existentes. Retorna XML compacto ou None.

    M3 (F2 fatia 2): `agente_id` isola as fontes por-agente (sessoes anteriores,
    intent de continuidade, alertas de memoria) — a sessao 'lojas' nao recebe
    continuidade/alertas das sessoes Nacom 'web'. Default 'web' = aditivo.
    NOTA: _check_recurring_errors (AgentSkillEffectiveness) e GLOBAL e nao tem
    coluna agente — fica fora desta fatia (P2/defesa).

    Args:
        user_id: ID do usuário no banco
        agente_id: agente da sessao ('web' | 'lojas')

    Returns:
        XML string (~400 chars) ou None se não houver eventos relevantes.
    """
    try:
        parts = []

        # 1. Última sessão do usuário (para saber "desde quando" informar)
        last_session_at = _get_last_session_time(user_id, agente_id)

        # 1b. Último intent/tarefa da sessão anterior (continuidade)
        last_intent = _check_last_session_intent(user_id, agente_id)
        if last_intent:
            parts.append(last_intent)

        # 2. Erros de sync Odoo (últimas 6h ou desde última sessão)
        odoo_errors = _check_odoo_sync_errors(last_session_at)
        if odoo_errors:
            parts.append(odoo_errors)

        # 3. Falhas de importação de pedidos
        import_failures = _check_import_failures(last_session_at)
        if import_failures:
            parts.append(import_failures)

        # 4. Memórias com conflito pendente
        memory_alerts = _check_memory_alerts(user_id, agente_id)
        if memory_alerts:
            parts.append(memory_alerts)

        # 5. Commits recentes no repo (desde última sessão)
        use_commits = os.getenv('USE_COMMIT_BRIEFING', 'true').lower() == 'true'
        if use_commits:
            recent_commits = _check_recent_commits(last_session_at)
            if recent_commits:
                parts.append(recent_commits)

        # F4.1 PAD-CTX: stale_empresa (item 6) e intelligence_report (item 7)
        # RELOCADOS para consulta on-demand (tela admin /agente/memorias + rotas
        # D7) — fora do boot operacional.

        # 6. Respostas do Claude Code ao dialogo de melhoria (D8).
        # F4.1: a INJECAO no boot tem controle proprio (default OFF) — a flag
        # AGENT_IMPROVEMENT_DIALOGUE governa apenas o DIALOGO (batch D8 +
        # register_improvement). Excecao por skill (F4.5): ver
        # get_skill_bug_responses_for_skill (consumida no PreToolUse Skill).
        use_improvement = (
            os.getenv('AGENT_IMPROVEMENT_DIALOGUE', 'false').lower() == 'true'
            and os.getenv('AGENT_IMPROVEMENT_INJECT_BOOT', 'false').lower() == 'true'
        )
        if use_improvement:
            improvement_responses = _check_improvement_responses()
            if improvement_responses:
                parts.append(improvement_responses)

        # 7. F5.7 PAD-CTX: top-3 erros recorrentes de skill (gate interno de
        # >=30d de historico em agent_skill_effectiveness — dormante antes).
        use_recurring = os.getenv(
            'AGENT_RECURRING_ERRORS_BOOT', 'true'
        ).lower() == 'true'
        if use_recurring:
            recurring = _check_recurring_errors()
            if recurring:
                parts.append(recurring)

        if not parts:
            return None

        # Granularidade horaria (nao por minuto) para evitar invalidar cache de
        # messages a cada minuto. Ver analise: silent invalidator B5 (2026-05-09).
        since = last_session_at.strftime('%d/%m %Hh') if last_session_at else '?'
        header = f'<intersession_briefing since="{since}">'
        footer = '</intersession_briefing>'
        return header + '\n' + '\n'.join(parts) + '\n' + footer

    except Exception as e:
        logger.debug(f"[BRIEFING] Erro ao gerar briefing (ignorado): {e}")
        return None


def _get_last_session_time(user_id: int, agente_id: str = 'web'):
    """Retorna timestamp da última sessão do usuário (do agente) ou None."""
    try:
        from ..models import AgentSession

        last = AgentSession.query.filter_by(
            user_id=user_id, agente=agente_id,  # M3/B01: por agente
        ).order_by(
            AgentSession.updated_at.desc()
        ).first()

        return last.updated_at if last else None
    except Exception:
        return None


def _check_last_session_intent(user_id: int, agente_id: str = 'web') -> Optional[str]:
    """
    Extrai intent/tarefa da última sessão do usuário para continuidade.

    Busca summary JSONB da última sessão e extrai:
    - tarefas_pendentes[0] (prioridade: é o que o usuário precisa continuar)
    - resumo_geral (fallback: o que foi feito na sessão anterior)

    M3 (F2 fatia 2): `agente_id` isola por agente. Default 'web' = aditivo.

    Returns:
        XML tag com último intent ou None se não houver sessão/summary.
    """
    try:
        from ..models import AgentSession

        last = AgentSession.query.filter_by(
            user_id=user_id, agente=agente_id,  # M3/B01: por agente
        ).order_by(
            AgentSession.updated_at.desc()
        ).first()

        if not last or not last.summary or not isinstance(last.summary, dict):
            return None

        summary = last.summary

        # Prioridade: tarefa pendente (o que falta fazer)
        tarefas = summary.get('tarefas_pendentes', [])
        if tarefas and isinstance(tarefas, list) and len(tarefas) > 0:
            tarefa = str(tarefas[0]).strip()
            if tarefa:
                # Escapar para XML
                safe = (
                    tarefa.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                )
                remaining = f' remaining="{len(tarefas)}"' if len(tarefas) > 1 else ''
                return f'<last_session_intent type="tarefa_pendente"{remaining}>{safe}</last_session_intent>'

        # Fallback: resumo geral (o que foi feito)
        resumo = summary.get('resumo_geral', '')
        if resumo and isinstance(resumo, str) and resumo.strip():
            safe = (
                resumo.strip().replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            return f'<last_session_intent type="resumo">{safe}</last_session_intent>'

        return None

    except Exception as e:
        logger.debug(f"[BRIEFING] Last session intent check falhou (ignorado): {e}")
        return None


def _check_odoo_sync_errors(since) -> Optional[str]:
    """
    Verifica erros de sync Odoo desde a última sessão.

    Fonte: lancamento_frete_odoo_auditoria (status=ERRO).
    Fallback para últimas 6h se since=None.
    """
    try:
        from app import db
        from sqlalchemy import text as sql_text
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = since if since else (now - timedelta(hours=6))

        # Contar erros por etapa
        result = db.session.execute(sql_text("""
            SELECT etapa, etapa_descricao, count(*) as cnt
            FROM lancamento_frete_odoo_auditoria
            WHERE status = 'ERRO'
              AND executado_em >= :cutoff
            GROUP BY etapa, etapa_descricao
            ORDER BY cnt DESC
            LIMIT 3
        """), {"cutoff": cutoff})

        rows = result.fetchall()
        if not rows:
            return None

        total_errors = sum(r[2] for r in rows)
        top_etapa = rows[0][1] if rows else 'N/A'

        return (
            f'<odoo_sync_errors total="{total_errors}" since="{cutoff.strftime("%d/%m %Hh")}">'
            f'Top: {top_etapa} ({rows[0][2]}x)'
            f'</odoo_sync_errors>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Odoo sync check falhou (ignorado): {e}")
        return None


def _check_import_failures(since) -> Optional[str]:
    """
    Verifica falhas de importação de pedidos Odoo.

    Fonte: registro_pedido_odoo (status_odoo=ERRO).
    """
    try:
        from app import db
        from sqlalchemy import text as sql_text
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = since if since else (now - timedelta(hours=6))

        result = db.session.execute(sql_text("""
            SELECT count(*)
            FROM registro_pedido_odoo
            WHERE status_odoo = 'ERRO'
              AND processado_em >= :cutoff
        """), {"cutoff": cutoff})

        count = result.scalar() or 0
        if count == 0:
            return None

        return f'<import_failures count="{count}" since="{cutoff.strftime("%d/%m %Hh")}"/>'

    except Exception as e:
        logger.debug(f"[BRIEFING] Import check falhou (ignorado): {e}")
        return None


def _check_memory_alerts(user_id: int, agente_id: str = 'web') -> Optional[str]:
    """
    Verifica alertas de memória: conflitos pendentes, cold candidates.

    Alertas:
    - Memórias com has_potential_conflict=True
    - Memórias candidatas a tier frio (usage_count >= 20, effectiveness_score < 0.1)

    M3 (F2 fatia 2): `agente_id` isola por agente. Default 'web' = aditivo.
    """
    try:
        from ..models import AgentMemory

        alerts = []

        # Conflitos pendentes (pessoais + empresa)
        try:
            conflict_memories = AgentMemory.query.filter(
                AgentMemory.user_id.in_([user_id, 0]),
                AgentMemory.agente == agente_id,  # M3/B02: por agente
                AgentMemory.has_potential_conflict == True,  # noqa: E712
                AgentMemory.is_directory == False,  # noqa: E712
            ).with_entities(AgentMemory.path).limit(5).all()
            if conflict_memories:
                paths = '; '.join(m.path for m in conflict_memories)
                alerts.append(
                    f'conflitos={len(conflict_memories)} paths="{paths}"'
                )
        except Exception:
            pass

        # Cold candidates: usage_count >= 20 e nunca efetivo
        try:
            cold_candidates = AgentMemory.query.filter(
                AgentMemory.user_id == user_id,
                AgentMemory.agente == agente_id,  # M3/B03: por agente
                AgentMemory.is_directory == False,  # noqa: E712
                AgentMemory.is_cold == False,  # noqa: E712
                AgentMemory.usage_count >= 20,
                AgentMemory.effective_count == 0,
            ).count()
            if cold_candidates > 0:
                alerts.append(f'cold_candidates={cold_candidates}')
        except Exception:
            pass

        if not alerts:
            return None

        return f'<memory_alerts {" ".join(alerts)}/>'

    except Exception as e:
        logger.debug(f"[BRIEFING] Memory alerts check falhou (ignorado): {e}")
        return None


def _check_recent_commits(since) -> Optional[str]:
    """
    Verifica commits recentes no repositório git desde a última sessão.

    Roda `git log --oneline -5 --since=...` no diretório do projeto.
    Para cada commit, extrai módulos afetados (primeiro dir em app/).

    Custo: zero (subprocess local).

    Returns:
        XML com até 5 commits recentes ou None.
    """
    try:
        # Determinar diretório do projeto (raiz do repo)
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        # Formatar --since
        if since:
            since_str = since.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Fallback: últimas 24h
            from datetime import timedelta
            fallback = agora_utc_naive() - timedelta(hours=24)
            since_str = fallback.strftime('%Y-%m-%d %H:%M:%S')

        # git log --oneline -5 --since=...
        result = subprocess.run(
            ['git', 'log', '--oneline', '-5', f'--since={since_str}'],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        lines = result.stdout.strip().split('\n')
        if not lines:
            return None

        # Para cada commit, extrair módulos afetados
        commits_xml = []
        for line in lines:
            parts = line.split(' ', 1)
            if len(parts) < 2:
                continue
            commit_hash = parts[0]
            message = parts[1]

            # Extrair módulos via git diff-tree (arquivos alterados)
            modules = _extract_modules_from_commit(commit_hash, project_dir)
            modules_attr = f' modules="{modules}"' if modules else ''

            # Escapar mensagem para XML
            safe_msg = (
                message.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            commits_xml.append(f'<commit hash="{commit_hash}"{modules_attr}>{safe_msg}</commit>')

        if not commits_xml:
            return None

        since_fmt = since.strftime('%d/%m %Hh') if since else '?'
        return (
            f'<recent_commits since="{since_fmt}" count="{len(commits_xml)}">\n'
            + '\n'.join(commits_xml)
            + '\n</recent_commits>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Git commits check falhou (ignorado): {e}")
        return None


def _extract_modules_from_commit(commit_hash: str, project_dir: str) -> str:
    """
    Extrai módulos afetados por um commit (primeiro dir em app/).

    Ex: se commit tocou app/carvia/routes.py e app/agente/sdk/client.py,
    retorna "carvia,agente".

    Returns:
        String com módulos separados por vírgula, ou vazio.
    """
    try:
        result = subprocess.run(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_hash],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=3,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return ''

        modules = set()
        for file_path in result.stdout.strip().split('\n'):
            # Extrair módulo: app/MODULO/... → MODULO
            if file_path.startswith('app/'):
                parts = file_path.split('/')
                if len(parts) >= 2:
                    modules.add(parts[1])

        return ','.join(sorted(modules)) if modules else ''

    except Exception:
        return ''


def _format_improvement_responses(responses, note: str) -> Optional[str]:
    """Formata respostas do dialogo de melhoria como XML compacto (max 5)."""
    if not responses:
        return None

    def _xml_esc(text: str) -> str:
        """Escapa texto para XML."""
        return (
            text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )

    parts = []
    for r in responses[:5]:  # max 5 para nao poluir contexto
        safe_title = _xml_esc(str(r.title))
        notes = r.implementation_notes or r.description
        safe_notes = _xml_esc(str(notes)[:200])
        implemented = 'auto' if r.auto_implemented else 'manual'

        parts.append(
            f'<response key="{r.suggestion_key}" '
            f'category="{r.category}" impl="{implemented}">'
            f'{safe_title} — {safe_notes}</response>'
        )

    return (
        f'<improvement_responses count="{len(responses)}" '
        f'note="{note}">'
        + ''.join(parts)
        + '</improvement_responses>'
    )


def _check_recurring_errors() -> Optional[str]:
    """
    F5.7 PAD-CTX (item A3) — destila "top 3 erros recorrentes" de skills no boot.

    GATE DE VOLUME: so ativa quando agent_skill_effectiveness tiver >=30 dias
    de historico (MIN(created_at) <= now-30d). Antes disso o bloco fica
    DORMANTE (retorna None) — evita destilar ruido de amostra pequena.

    Quando ativo: top 3 skills por falhas (resolveu=false) nos ultimos 30 dias,
    exigindo recorrencia (>=2 falhas). Zero custo LLM — query SQL direta.

    Returns:
        XML <erros_recorrentes> compacto ou None (sem dados / gate fechado).
    """
    try:
        from datetime import timedelta

        from sqlalchemy import func

        from app import db
        from app.utils.timezone import agora_utc_naive
        from ..models import AgentSkillEffectiveness

        now = agora_utc_naive()
        primeiro = db.session.query(
            func.min(AgentSkillEffectiveness.created_at)
        ).scalar()
        if primeiro is None or primeiro > now - timedelta(days=30):
            return None  # gate fechado: <30d de historico

        janela = now - timedelta(days=30)
        rows = (
            db.session.query(
                AgentSkillEffectiveness.skill_name,
                func.count().label('falhas'),
            )
            .filter(
                AgentSkillEffectiveness.resolveu.is_(False),
                AgentSkillEffectiveness.created_at >= janela,
            )
            .group_by(AgentSkillEffectiveness.skill_name)
            .having(func.count() >= 2)  # recorrente = 2+ falhas
            .order_by(func.count().desc())
            .limit(3)
            .all()
        )
        if not rows:
            return None

        linhas = ''.join(
            f'\n  <skill name="{_xml_escape_attr(r.skill_name)}" falhas="{r.falhas}"/>'
            for r in rows
        )
        return (
            '<erros_recorrentes window="30d" '
            'note="Skills com falhas recorrentes — redobre validacao ao usa-las.">'
            f'{linhas}\n</erros_recorrentes>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Recurring errors check falhou (ignorado): {e}")
        return None


def _xml_escape_attr(text: str) -> str:
    """Escape minimo para valor de atributo XML."""
    return (
        str(text)
        .replace('&', '&amp;').replace('<', '&lt;')
        .replace('>', '&gt;').replace('"', '&quot;')
    )


def _check_improvement_responses() -> Optional[str]:
    """
    Verifica respostas do Claude Code ao dialogo de melhoria (D8).

    Busca respostas nao verificadas (status='responded', ultimos 14 dias)
    e formata como XML para injecao no briefing do agente.
    F4.1: so entra no boot com AGENT_IMPROVEMENT_INJECT_BOOT=true (caller).

    Zero custo LLM — query SQL direta.

    Returns:
        XML tag com respostas ou None se nao houver pendentes.
    """
    try:
        from ..models import AgentImprovementDialogue

        responses = AgentImprovementDialogue.get_unverified_responses()
        return _format_improvement_responses(
            responses,
            note=('Respostas do Claude Code ao dialogo de melhoria. '
                  'Avalie se as mudancas resolveram os problemas reportados.'),
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Improvement responses check falhou (ignorado): {e}")
        return None


def get_skill_bug_responses_for_skill(skill_name: str) -> Optional[str]:
    """
    F4.5 PAD-CTX — excecao condicional ao corte de improvement_responses do
    boot: response de skill_bug ATIVA (status='responded', <=14d) volta ao
    contexto SOMENTE no turno que USA a skill afetada.

    Consumida pelo PreToolUse da Skill tool (sdk/hooks.py:
    _build_skill_pretool_context). Match da skill: evidence_json['skill']
    (gravado pelo skill_effectiveness_service) OU mencao do nome da skill em
    title/description (register_improvement real-time nao grava o campo).

    Roda fora de request Flask (loop do SDK) — probe + create_app, mesmo
    pattern de get_skill_reminders_for_session.

    Returns:
        XML <improvement_responses> filtrado ou None.
    """
    if not skill_name:
        return None
    try:
        from contextlib import nullcontext
        try:
            from flask import current_app as _app_probe
            _ = _app_probe.name
            _ctx = nullcontext()
        except RuntimeError:
            from app import create_app as _ca
            _ctx = _ca().app_context()

        with _ctx:
            from ..models import AgentImprovementDialogue

            responses = AgentImprovementDialogue.get_unverified_responses()
            skill_lower = skill_name.lower()
            matched = []
            for r in responses or []:
                if r.category != 'skill_bug':
                    continue
                ev = r.evidence_json if isinstance(r.evidence_json, dict) else {}
                ev_skill = str(ev.get('skill') or '').lower()
                if ev_skill == skill_lower or skill_lower in f"{r.title}\n{r.description}".lower():
                    matched.append(r)

            return _format_improvement_responses(
                matched,
                note=(f'Respostas do Claude Code a bugs reportados na skill '
                      f'{skill_name}. Avalie nesta execucao se o problema foi '
                      f'resolvido.'),
            )

    except Exception as e:
        logger.debug(f"[BRIEFING] skill_bug responses check falhou (ignorado): {e}")
        return None
