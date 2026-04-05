"""
Briefing Inter-Sessão MVP (Memory System v2 — Fase 3A).

Gera bloco XML compacto (~400 chars) com eventos ocorridos entre sessões:
- Erros de sync Odoo (últimas 6h)
- Falhas de importação de pedidos
- Estado de memórias (conflitos, cold candidates)
- Commits recentes no repositório (git log)

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


def build_intersession_briefing(user_id: int) -> Optional[str]:
    """
    Gera briefing inter-sessão: o que mudou desde a última sessão do usuário.

    Queries leves em tabelas existentes. Retorna XML compacto ou None.

    Args:
        user_id: ID do usuário no banco

    Returns:
        XML string (~400 chars) ou None se não houver eventos relevantes.
    """
    try:
        parts = []

        # 1. Última sessão do usuário (para saber "desde quando" informar)
        last_session_at = _get_last_session_time(user_id)

        # 1b. Último intent/tarefa da sessão anterior (continuidade)
        last_intent = _check_last_session_intent(user_id)
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
        memory_alerts = _check_memory_alerts(user_id)
        if memory_alerts:
            parts.append(memory_alerts)

        # 5. Commits recentes no repo (desde última sessão)
        use_commits = os.getenv('USE_COMMIT_BRIEFING', 'true').lower() == 'true'
        if use_commits:
            recent_commits = _check_recent_commits(last_session_at)
            if recent_commits:
                parts.append(recent_commits)

        # 6. Memórias empresa sem revisão há 60+ dias
        stale_alert = _check_stale_empresa_memories()
        if stale_alert:
            parts.append(stale_alert)

        # 7. Relatorio de inteligencia D7 (recomendacoes do cron semanal)
        intelligence_alert = _check_intelligence_report()
        if intelligence_alert:
            parts.append(intelligence_alert)

        # 8. Respostas do Claude Code ao dialogo de melhoria (D8)
        use_improvement = os.getenv('AGENT_IMPROVEMENT_DIALOGUE', 'false').lower() == 'true'
        if use_improvement:
            improvement_responses = _check_improvement_responses()
            if improvement_responses:
                parts.append(improvement_responses)

        if not parts:
            return None

        since = last_session_at.strftime('%d/%m %H:%M') if last_session_at else '?'
        header = f'<intersession_briefing since="{since}">'
        footer = '</intersession_briefing>'
        return header + '\n' + '\n'.join(parts) + '\n' + footer

    except Exception as e:
        logger.debug(f"[BRIEFING] Erro ao gerar briefing (ignorado): {e}")
        return None


def _get_last_session_time(user_id: int):
    """Retorna timestamp da última sessão do usuário ou None."""
    try:
        from ..models import AgentSession

        last = AgentSession.query.filter_by(
            user_id=user_id,
        ).order_by(
            AgentSession.updated_at.desc()
        ).first()

        return last.updated_at if last else None
    except Exception:
        return None


def _check_last_session_intent(user_id: int) -> Optional[str]:
    """
    Extrai intent/tarefa da última sessão do usuário para continuidade.

    Busca summary JSONB da última sessão e extrai:
    - tarefas_pendentes[0] (prioridade: é o que o usuário precisa continuar)
    - resumo_geral (fallback: o que foi feito na sessão anterior)

    Returns:
        XML tag com último intent ou None se não houver sessão/summary.
    """
    try:
        from ..models import AgentSession

        last = AgentSession.query.filter_by(
            user_id=user_id,
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
            f'<odoo_sync_errors total="{total_errors}" since="{cutoff.strftime("%d/%m %H:%M")}">'
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

        return f'<import_failures count="{count}" since="{cutoff.strftime("%d/%m %H:%M")}"/>'

    except Exception as e:
        logger.debug(f"[BRIEFING] Import check falhou (ignorado): {e}")
        return None


def _check_memory_alerts(user_id: int) -> Optional[str]:
    """
    Verifica alertas de memória: conflitos pendentes, cold candidates.

    Alertas:
    - Memórias com has_potential_conflict=True
    - Memórias candidatas a tier frio (usage_count >= 20, effectiveness_score < 0.1)
    """
    try:
        from ..models import AgentMemory

        alerts = []

        # Conflitos pendentes (pessoais + empresa)
        try:
            conflict_memories = AgentMemory.query.filter(
                AgentMemory.user_id.in_([user_id, 0]),
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

        since_fmt = since.strftime('%d/%m %H:%M') if since else '?'
        return (
            f'<recent_commits since="{since_fmt}" count="{len(commits_xml)}">\n'
            + '\n'.join(commits_xml)
            + '\n</recent_commits>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Git commits check falhou (ignorado): {e}")
        return None


def _check_stale_empresa_memories() -> Optional[str]:
    """
    Verifica memorias empresa sem revisao ha 60+ dias.

    Memorias com reviewed_at=NULL e criadas ha mais de 60 dias
    sao candidatas a revisao. Retorna alerta se count > 5.
    """
    try:
        from ..models import AgentMemory
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = now - timedelta(days=60)

        stale = AgentMemory.query.filter(
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.reviewed_at.is_(None),
            AgentMemory.created_at < cutoff,
        ).count()

        if stale > 5:
            return f'<stale_empresa count="{stale}">Memorias empresa sem revisao ha 60+ dias.</stale_empresa>'
        return None
    except Exception as e:
        logger.debug(f"[BRIEFING] Stale empresa check falhou (ignorado): {e}")
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


def _check_intelligence_report() -> Optional[str]:
    """
    Verifica se ha relatorio de inteligencia D7 recente (< 14 dias).

    Extrai top 3 recomendacoes prescritivas do report_json e injeta
    como XML no briefing. Zero custo LLM — query SQL direta.

    Returns:
        XML tag com recomendacoes ou None se nao houver relatorio recente.
    """
    try:
        from ..models import AgentIntelligenceReport

        report = AgentIntelligenceReport.get_latest()
        if not report or not report.report_date:
            return None

        now = agora_utc_naive()
        report_age = (now.date() - report.report_date).days
        if report_age > 14:
            return None

        report_data = report.report_json
        if not isinstance(report_data, dict):
            return None

        recs = report_data.get('recommendations', [])
        if not recs or not isinstance(recs, list):
            return None

        # Top 3 recomendacoes, priorizando critical > warning > info
        severity_order = {'critical': 0, 'warning': 1, 'info': 2, 'success': 3}
        sorted_recs = sorted(
            recs,
            key=lambda r: severity_order.get(r.get('severity', 'info'), 99)
        )
        top_recs = sorted_recs[:3]

        # Formatar como XML compacto
        def _xml_esc(text: str) -> str:
            """Escapa texto para XML (& < > ")."""
            return (
                text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )

        rec_parts = []
        for rec in top_recs:
            severity = _xml_esc(str(rec.get('severity', 'info')))
            safe_title = _xml_esc(str(rec.get('title', '?')))
            action = rec.get('suggested_action', '')
            safe_action = _xml_esc(str(action)) if action else ''
            rec_parts.append(
                f'<rec severity="{severity}">{safe_title}'
                f'{" — " + safe_action if safe_action else ""}</rec>'
            )

        score = float(report.health_score or 0)
        return (
            f'<intelligence_report date="{report.report_date}" '
            f'score="{score:.0f}" age_days="{report_age}">'
            + ''.join(rec_parts)
            + '</intelligence_report>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Intelligence report check falhou (ignorado): {e}")
        return None


def _check_improvement_responses() -> Optional[str]:
    """
    Verifica respostas do Claude Code ao dialogo de melhoria (D8).

    Busca respostas nao verificadas (status='responded', ultimos 14 dias)
    e formata como XML para injecao no briefing do agente.

    Zero custo LLM — query SQL direta.

    Returns:
        XML tag com respostas ou None se nao houver pendentes.
    """
    try:
        from ..models import AgentImprovementDialogue

        responses = AgentImprovementDialogue.get_unverified_responses()
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
            f'note="Respostas do Claude Code ao dialogo de melhoria. '
            f'Avalie se as mudancas resolveram os problemas reportados.">'
            + ''.join(parts)
            + '</improvement_responses>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Improvement responses check falhou (ignorado): {e}")
        return None
