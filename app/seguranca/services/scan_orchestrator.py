"""
Scan Orchestrator
=================

Coordena varreduras de seguranca:
- Cria registro de varredura
- Executa checks (email, dominio)
- Cria vulnerabilidades (upsert via unique constraint)
- Calcula scores
- Dispara notificacoes
"""

from typing import Dict, Any, Optional, List

from app import db
from app.utils.timezone import agora_utc_naive
from app.utils.logging_config import logger


def executar_varredura(
    tipo: str = 'FULL_SCAN',
    disparado_por: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executa varredura de seguranca.

    Args:
        tipo: FULL_SCAN, EMAIL_BREACH, DOMAIN_EXPOSURE
        disparado_por: Email do admin que disparou (null=automatica)

    Returns:
        dict com resultado da varredura
    """
    from app.seguranca.models import (
        SegurancaVarredura, SegurancaVulnerabilidade, SegurancaConfig
    )
    from app.auth.models import Usuario

    # Criar registro de varredura
    varredura = SegurancaVarredura(
        tipo=tipo,
        status='EM_EXECUCAO',
        disparado_por=disparado_por,
    )
    db.session.add(varredura)
    db.session.flush()

    total_verificados = 0
    total_vulnerabilidades = 0
    detalhes = {'erros': []}

    try:
        usuarios = Usuario.query.filter_by(status='ativo').all()
        total_verificados = len(usuarios)

        # ── 1. Verificacao de Email Breaches ──
        if tipo in ('FULL_SCAN', 'EMAIL_BREACH'):
            api_key = SegurancaConfig.get_valor('hibp_api_key')
            count = _verificar_emails(usuarios, varredura.id, api_key, detalhes)
            total_vulnerabilidades += count

        # ── 2. Verificacao de Dominios ──
        if tipo in ('FULL_SCAN', 'DOMAIN_EXPOSURE'):
            count = _verificar_dominios(usuarios, varredura.id, detalhes)
            total_vulnerabilidades += count

        # ── 3. Calcular scores ──
        _recalcular_scores(usuarios)

        # Atualizar varredura
        varredura.status = 'CONCLUIDA'
        varredura.concluido_em = agora_utc_naive()
        varredura.total_verificados = total_verificados
        varredura.total_vulnerabilidades = total_vulnerabilidades
        varredura.detalhes = detalhes

        db.session.commit()

        # ── 4. Notificar ──
        _notificar_novas_vulnerabilidades(varredura.id)

        logger.info(
            f"Varredura {varredura.id} concluida: "
            f"{total_verificados} verificados, "
            f"{total_vulnerabilidades} vulnerabilidades"
        )

        return {
            'sucesso': True,
            'varredura_id': varredura.id,
            'total_verificados': total_verificados,
            'total_vulnerabilidades': total_vulnerabilidades,
        }

    except Exception as e:
        logger.error(f"Erro na varredura {varredura.id}: {e}")
        varredura.status = 'FALHOU'
        varredura.concluido_em = agora_utc_naive()
        varredura.detalhes = {
            'erros': detalhes.get('erros', []) + [str(e)]
        }
        db.session.commit()

        return {
            'sucesso': False,
            'varredura_id': varredura.id,
            'erro': str(e),
        }


def _verificar_emails(
    usuarios: list,
    varredura_id: int,
    api_key: Optional[str],
    detalhes: dict,
) -> int:
    """Verifica emails de usuarios contra HIBP"""
    from app.seguranca.services.hibp_service import (
        verificar_email_breaches, obter_breaches_resumo
    )
    from app.seguranca.models import SegurancaVulnerabilidade

    count = 0

    if not api_key:
        detalhes['email_breach'] = {
            'verificado': False,
            'motivo': 'API key HIBP nao configurada',
        }
        return 0

    detalhes['email_breach'] = {'verificado': True, 'resultados': []}

    for usuario in usuarios:
        if not usuario.email:
            continue

        resultado = verificar_email_breaches(usuario.email, api_key)

        if not resultado['sucesso']:
            detalhes['erros'].append(
                f"Erro HIBP para {usuario.email}: {resultado.get('erro')}"
            )
            continue

        if resultado['total'] > 0:
            breaches = obter_breaches_resumo(resultado['breaches'])

            # Upsert vulnerabilidade (unique constraint previne duplicata)
            for breach in breaches:
                titulo = f"Email exposto em vazamento: {breach['nome']}"
                existente = SegurancaVulnerabilidade.query.filter_by(
                    user_id=usuario.id,
                    categoria='EMAIL_BREACH',
                    titulo=titulo,
                ).first()

                if not existente:
                    vuln = SegurancaVulnerabilidade(
                        user_id=usuario.id,
                        varredura_id=varredura_id,
                        categoria='EMAIL_BREACH',
                        severidade=_severidade_breach(breach),
                        titulo=titulo,
                        descricao=(
                            f"O email {usuario.email} foi encontrado no "
                            f"vazamento '{breach['nome']}' "
                            f"(data: {breach['data_breach']}). "
                            f"Dados comprometidos: "
                            f"{', '.join(breach['dados_comprometidos'])}"
                        ),
                        dados=breach,
                    )
                    db.session.add(vuln)
                    count += 1

            detalhes['email_breach']['resultados'].append({
                'email': usuario.email,
                'breaches': len(breaches),
            })

    db.session.flush()
    return count


def _verificar_dominios(
    usuarios: list,
    varredura_id: int,
    detalhes: dict,
) -> int:
    """Verifica seguranca DNS dos dominios dos usuarios"""
    from app.seguranca.services.domain_service import (
        verificar_dominio, extrair_dominios_usuarios
    )
    from app.seguranca.models import SegurancaVulnerabilidade

    dominios = extrair_dominios_usuarios()
    count = 0

    detalhes['domain'] = {
        'verificado': True,
        'dominios_total': len(dominios),
        'resultados': [],
    }

    for dominio in dominios:
        try:
            resultado = verificar_dominio(dominio)

            for vuln_data in resultado.get('vulnerabilidades', []):
                # Atribuir a TODOS os usuarios daquele dominio
                usuarios_dominio = [
                    u for u in usuarios
                    if u.email and u.email.split('@')[1].lower() == dominio
                ]

                for usuario in usuarios_dominio:
                    existente = SegurancaVulnerabilidade.query.filter_by(
                        user_id=usuario.id,
                        categoria=vuln_data['categoria'],
                        titulo=vuln_data['titulo'],
                    ).first()

                    if not existente:
                        vuln = SegurancaVulnerabilidade(
                            user_id=usuario.id,
                            varredura_id=varredura_id,
                            categoria=vuln_data['categoria'],
                            severidade=vuln_data['severidade'],
                            titulo=vuln_data['titulo'],
                            descricao=vuln_data['descricao'],
                            dados={'dominio': dominio},
                        )
                        db.session.add(vuln)
                        count += 1

            detalhes['domain']['resultados'].append({
                'dominio': dominio,
                'score': resultado['score_parcial'],
                'vulnerabilidades': len(resultado['vulnerabilidades']),
            })

        except Exception as e:
            detalhes['erros'].append(
                f"Erro ao verificar dominio {dominio}: {e}"
            )
            logger.error(f"Erro ao verificar dominio {dominio}: {e}")

    db.session.flush()
    return count


def _recalcular_scores(usuarios: list) -> None:
    """Recalcula scores de todos os usuarios e empresa"""
    from app.seguranca.services.score_service import (
        calcular_score_usuario, calcular_score_empresa
    )

    for usuario in usuarios:
        try:
            calcular_score_usuario(usuario.id)
        except Exception as e:
            logger.error(f"Erro ao calcular score usuario {usuario.id}: {e}")

    try:
        calcular_score_empresa()
    except Exception as e:
        logger.error(f"Erro ao calcular score empresa: {e}")


def _notificar_novas_vulnerabilidades(varredura_id: int) -> None:
    """Notifica sobre novas vulnerabilidades da varredura"""
    from app.seguranca.models import SegurancaVulnerabilidade

    novas = SegurancaVulnerabilidade.query.filter_by(
        varredura_id=varredura_id,
        notificado=False,
    ).filter(
        SegurancaVulnerabilidade.severidade.in_(['CRITICA', 'ALTA'])
    ).all()

    if not novas:
        return

    try:
        from app.notificacoes.services import NotificationDispatcher
        dispatcher = NotificationDispatcher()

        for vuln in novas:
            tipo_notif = {
                'EMAIL_BREACH': 'SEGURANCA_BREACH_DETECTADO',
                'SENHA_FRACA': 'SEGURANCA_SENHA_FRACA',
                'SENHA_VAZADA': 'SEGURANCA_SENHA_FRACA',
            }.get(vuln.categoria, 'SEGURANCA_DOMINIO_VULNERAVEL')

            dispatcher.enviar_alerta(
                tipo=tipo_notif,
                nivel='CRITICO' if vuln.severidade == 'CRITICA' else 'ALTO',
                titulo=vuln.titulo,
                mensagem=vuln.descricao or vuln.titulo,
                dados={
                    'vulnerabilidade_id': vuln.id,
                    'categoria': vuln.categoria,
                    'severidade': vuln.severidade,
                    'user_id': vuln.user_id,
                },
                user_id=vuln.user_id,
                canais=['in_app'],
            )

            vuln.notificado = True
            vuln.notificado_em = agora_utc_naive()

        db.session.flush()

    except Exception as e:
        logger.error(f"Erro ao notificar vulnerabilidades: {e}")


def _severidade_breach(breach: dict) -> str:
    """Determina severidade de um breach baseado nos dados comprometidos"""
    dados_criticos = {'Passwords', 'Credit cards', 'Bank account numbers'}
    dados_altos = {'Phone numbers', 'Physical addresses', 'IP addresses'}

    dados = set(breach.get('dados_comprometidos', []))

    if dados & dados_criticos:
        return 'CRITICA'
    elif dados & dados_altos:
        return 'ALTA'
    elif breach.get('verificado'):
        return 'MEDIA'
    else:
        return 'BAIXA'
