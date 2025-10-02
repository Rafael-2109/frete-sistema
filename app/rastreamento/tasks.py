"""
🧹 WORKER DE LIMPEZA LGPD - RASTREAMENTO GPS
Expurgo automático de dados de rastreamento após 90 dias
Conformidade com LGPD (Lei 13.709/2018)
"""

from app import db
from app.rastreamento.models import RastreamentoEmbarque, PingGPS, LogRastreamento
from datetime import datetime
from flask import current_app


def limpar_dados_expirados_lgpd():
    """
    Job agendado para rodar diariamente às 2h da manhã
    Remove dados de rastreamento GPS com mais de 90 dias

    Conformidade LGPD:
    - Princípio da minimização de dados (Art. 6º, III)
    - Prazo de retenção limitado (Art. 15, II)
    - Eliminação automática após finalidade atingida

    Returns:
        tuple: (total_expurgado, total_erros)
    """
    try:
        data_limite = datetime.utcnow()

        # Buscar rastreamentos expirados (data_expurgo_lgpd <= hoje)
        rastreamentos_expirados = RastreamentoEmbarque.query.filter(
            RastreamentoEmbarque.data_expurgo_lgpd <= data_limite
        ).all()

        total_expurgado = 0
        total_erros = 0

        for rastreamento in rastreamentos_expirados:
            try:
                embarque_id = rastreamento.embarque_id
                rastreamento_id = rastreamento.id

                # Conta pings antes de deletar (para log)
                total_pings = rastreamento.pings.count()

                # Deletar rastreamento (cascade vai deletar pings e logs automaticamente)
                db.session.delete(rastreamento)
                db.session.commit()

                total_expurgado += 1

                current_app.logger.info(
                    f"✅ LGPD: Rastreamento #{rastreamento_id} expurgado "
                    f"(Embarque #{embarque_id}, {total_pings} pings removidos)"
                )

            except Exception as e:
                db.session.rollback()
                total_erros += 1
                current_app.logger.error(
                    f"❌ Erro ao expurgar rastreamento #{rastreamento.id}: {str(e)}"
                )
                continue

        # Log final
        if total_expurgado > 0:
            current_app.logger.info(
                f"🧹 Limpeza LGPD concluída: {total_expurgado} rastreamentos expurgados, "
                f"{total_erros} erros"
            )
        else:
            current_app.logger.info("✅ Limpeza LGPD: Nenhum rastreamento expirado encontrado")

        return (total_expurgado, total_erros)

    except Exception as e:
        current_app.logger.error(f"❌ Erro crítico na limpeza LGPD: {str(e)}")
        db.session.rollback()
        return (0, 1)


def verificar_rastreamentos_inativos():
    """
    Verifica rastreamentos que estão há mais de 24h sem enviar ping
    Envia alerta para equipe de monitoramento

    Útil para identificar problemas de rastreamento
    """
    from datetime import timedelta

    try:
        limite_inatividade = datetime.utcnow() - timedelta(hours=24)

        # Buscar rastreamentos ativos mas sem pings há 24h
        rastreamentos_inativos = RastreamentoEmbarque.query.filter(
            RastreamentoEmbarque.status.in_(['ATIVO', 'CHEGOU_DESTINO']),
            RastreamentoEmbarque.ultimo_ping_em < limite_inatividade
        ).all()

        if rastreamentos_inativos:
            current_app.logger.warning(
                f"⚠️ {len(rastreamentos_inativos)} rastreamentos inativos há mais de 24h"
            )

            for rastr in rastreamentos_inativos:
                current_app.logger.warning(
                    f"   - Embarque #{rastr.embarque_id}: último ping em "
                    f"{rastr.ultimo_ping_em.strftime('%d/%m/%Y %H:%M')}"
                )

            # TODO: Enviar notificação para equipe (email, Slack, etc.)

        return len(rastreamentos_inativos)

    except Exception as e:
        current_app.logger.error(f"❌ Erro ao verificar rastreamentos inativos: {str(e)}")
        return 0


def gerar_relatorio_rastreamento():
    """
    Gera relatório diário de rastreamentos
    Estatísticas para análise de uso
    """
    try:
        from sqlalchemy import func

        # Contar por status
        stats = db.session.query(
            RastreamentoEmbarque.status,
            func.count(RastreamentoEmbarque.id)
        ).group_by(RastreamentoEmbarque.status).all()

        current_app.logger.info("📊 RELATÓRIO DIÁRIO DE RASTREAMENTO:")
        for status, count in stats:
            current_app.logger.info(f"   - {status}: {count}")

        # Total de pings nas últimas 24h
        from datetime import timedelta
        ontem = datetime.utcnow() - timedelta(days=1)

        total_pings_24h = PingGPS.query.filter(
            PingGPS.criado_em >= ontem
        ).count()

        current_app.logger.info(f"   - Pings nas últimas 24h: {total_pings_24h}")

        # Rastreamentos que chegaram ao destino hoje
        hoje_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        chegaram_hoje = RastreamentoEmbarque.query.filter(
            RastreamentoEmbarque.chegou_destino_em >= hoje_inicio
        ).count()

        current_app.logger.info(f"   - Chegaram ao destino hoje: {chegaram_hoje}")

        # Entregas concluídas hoje
        entregas_hoje = RastreamentoEmbarque.query.filter(
            RastreamentoEmbarque.canhoto_enviado_em >= hoje_inicio
        ).count()

        current_app.logger.info(f"   - Entregas concluídas hoje: {entregas_hoje}")

        return True

    except Exception as e:
        current_app.logger.error(f"❌ Erro ao gerar relatório: {str(e)}")
        return False
