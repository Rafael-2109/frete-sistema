"""
Job RQ para inserção sequencial de pedidos no Odoo.

Processa filiais UMA A UMA: criar pedido → calcular impostos → próxima.
Garante que nunca há >1 cálculo de impostos rodando no Odoo simultaneamente.

Sem este controle, N jobs de impostos rodam em paralelo, acumulam RAM
e derrubam o Odoo.

Padrão: Fire-and-Poll (P2 do Odoo CLAUDE.md)
- Criar pedido: fire com timeout 90s, poll por (partner_id + pedido_compra)
- Calcular impostos: fire com timeout 90s, poll verificando l10n_br_total_tributos > 0
- Progresso: atualiza Redis a cada etapa, frontend polla via AJAX

Fonte do padrão: app/recebimento/workers/recebimento_lf_jobs.py
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Chave Redis para progresso
REDIS_KEY_PREFIX = 'pedido_insercao_progresso'
REDIS_TTL = 3600  # 1 hora


def inserir_pedidos_lote_job(session_key: str, filiais_dados: list,
                              rede: str, tipo_doc: str, numero_doc: str,
                              s3_path: str, usuario: str):
    """
    Job RQ: insere pedidos filial a filial com cálculo de impostos serializado.

    Para cada filial:
    1. Cria sale.order no Odoo (fire_and_poll se timeout)
    2. Calcula impostos (fire_and_poll — espera terminar antes da próxima)
    3. Registra resultado no banco
    4. Atualiza progresso no Redis

    Args:
        session_key: Chave do PedidoImportacaoTemp
        filiais_dados: Lista de dicts com dados das filiais a inserir
            Cada dict: {cnpj, itens_odoo, nome_cliente, uf, tem_divergencia,
                        divergencias, justificativa, numero_pedido_cliente}
        rede: Nome da rede (ATACADAO, ASSAI)
        tipo_doc: Tipo do documento (PROPOSTA, PEDIDO)
        numero_doc: Número do documento
        s3_path: Path do PDF no S3
        usuario: Nome do usuário

    Returns:
        dict com resultados por filial
    """
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.pedidos.integracao_odoo import get_odoo_service
        from app.pedidos.integracao_odoo.models import PedidoImportacaoTemp
        from app.pedidos.workers.impostos_jobs import calcular_impostos_odoo
        from app import db

        total = len(filiais_dados)
        resultados = []
        redis_conn = _get_redis()

        logger.info(
            f"[Inserir Lote] Iniciando {total} filial(is) para {rede} "
            f"session={session_key}"
        )

        _atualizar_progresso(redis_conn, session_key, {
            'status': 'processando',
            'total': total,
            'atual': 0,
            'percentual': 0,
            'mensagem': 'Iniciando inserção...',
            'resultados': [],
        })

        service = get_odoo_service()

        for i, filial in enumerate(filiais_dados):
            cnpj = filial['cnpj']
            nome_cliente = filial.get('nome_cliente', '')
            itens_odoo = filial['itens_odoo']
            numero_pedido_cliente = filial.get('numero_pedido_cliente')

            percentual = int(((i) / total) * 100)
            _atualizar_progresso(redis_conn, session_key, {
                'status': 'processando',
                'total': total,
                'atual': i + 1,
                'percentual': percentual,
                'mensagem': f'Criando pedido {i + 1}/{total}: {nome_cliente}',
                'etapa': 'criando_pedido',
                'cnpj_atual': cnpj,
                'resultados': resultados,
            })

            # --- Etapa A: Criar pedido no Odoo ---
            try:
                picking_policy = 'direct' if rede.upper() == 'ATACADAO' else None

                resultado = service.criar_pedido(
                    cnpj_cliente=cnpj,
                    itens=itens_odoo,
                    numero_pedido_cliente=numero_pedido_cliente,
                    payment_provider_id=30,
                    picking_policy=picking_policy,
                    calcular_impostos=False,  # Feito manualmente abaixo
                )

                if not resultado.sucesso:
                    logger.warning(
                        f"[Inserir Lote] Filial {i + 1}/{total} ({cnpj}): "
                        f"ERRO ao criar pedido — {resultado.mensagem}"
                    )
                    res = {
                        'cnpj': cnpj,
                        'nome_cliente': nome_cliente,
                        'sucesso': False,
                        'order_id': None,
                        'order_name': None,
                        'mensagem': resultado.mensagem,
                        'erros': resultado.erros,
                    }
                    resultados.append(res)
                    _registrar_auditoria(
                        db, cnpj, itens_odoo, rede, tipo_doc,
                        numero_doc, s3_path, usuario, filial, resultado
                    )
                    continue

                order_id = resultado.order_id
                order_name = resultado.order_name

                # Registra auditoria
                _registrar_auditoria(
                    db, cnpj, itens_odoo, rede, tipo_doc,
                    numero_doc, s3_path, usuario, filial, resultado
                )

            except Exception as e:
                logger.error(f"[Inserir Lote] Filial {i + 1}/{total} ({cnpj}): EXCEÇÃO — {e}")
                resultados.append({
                    'cnpj': cnpj,
                    'nome_cliente': nome_cliente,
                    'sucesso': False,
                    'order_id': None,
                    'order_name': None,
                    'mensagem': f'Erro: {str(e)}',
                    'erros': [str(e)],
                })
                continue

            # --- Etapa B: Calcular impostos (serializado — 1 por vez) ---
            _atualizar_progresso(redis_conn, session_key, {
                'status': 'processando',
                'total': total,
                'atual': i + 1,
                'percentual': percentual,
                'mensagem': f'Calculando impostos {i + 1}/{total}: {order_name}',
                'etapa': 'calculando_impostos',
                'cnpj_atual': cnpj,
                'resultados': resultados,
            })

            impostos_msg = ""
            try:
                impostos_result = calcular_impostos_odoo(order_id, order_name)
                if impostos_result.get('success'):
                    tempo_imp = impostos_result.get('tempo_segundos', 0)
                    impostos_msg = f" | Impostos OK ({tempo_imp:.0f}s)"
                else:
                    impostos_msg = f" | Impostos: {impostos_result.get('message', 'falha')}"
            except Exception as e:
                logger.warning(f"[Inserir Lote] Impostos {order_name}: {e}")
                impostos_msg = f" | Impostos: erro ({e})"

            logger.info(
                f"[Inserir Lote] Filial {i + 1}/{total} ({cnpj}): "
                f"{order_name}{impostos_msg}"
            )

            resultados.append({
                'cnpj': cnpj,
                'nome_cliente': nome_cliente,
                'sucesso': True,
                'order_id': order_id,
                'order_name': order_name,
                'mensagem': f'{order_name} criado{impostos_msg}',
                'erros': resultado.erros if resultado.erros else [],
            })

        # --- Finalização ---
        todos_sucesso = all(r.get('sucesso') for r in resultados)
        algum_sucesso = any(r.get('sucesso') for r in resultados)

        _atualizar_progresso(redis_conn, session_key, {
            'status': 'concluido' if algum_sucesso else 'erro',
            'total': total,
            'atual': total,
            'percentual': 100,
            'mensagem': (
                f'Concluído: {sum(1 for r in resultados if r.get("sucesso"))}/{total} com sucesso'
            ),
            'etapa': 'finalizado',
            'resultados': resultados,
        })

        # Atualiza PedidoImportacaoTemp
        try:
            registro_temp = PedidoImportacaoTemp.buscar_por_chave(session_key)
            if registro_temp:
                if todos_sucesso:
                    registro_temp.marcar_lancado(resultados)
                elif algum_sucesso:
                    registro_temp.status = 'PARCIAL'
                    registro_temp.resultados_lancamento = resultados
                else:
                    registro_temp.marcar_erro(resultados)
                db.session.commit()
        except Exception as e:
            logger.error(f"[Inserir Lote] Erro ao atualizar registro temp: {e}")
            db.session.rollback()

        logger.info(
            f"[Inserir Lote] Finalizado: {sum(1 for r in resultados if r.get('sucesso'))}/{total} "
            f"sucesso para session={session_key}"
        )

        return {'resultados': resultados, 'total': total}


def _registrar_auditoria(db, cnpj, itens_odoo, rede, tipo_doc,
                          numero_doc, s3_path, usuario, filial, resultado):
    """Registra resultado no RegistroPedidoOdoo para auditoria."""
    from app.pedidos.integracao_odoo.models import RegistroPedidoOdoo

    try:
        registro = RegistroPedidoOdoo(
            rede=rede.upper(),
            tipo_documento=tipo_doc.upper(),
            numero_documento=numero_doc,
            arquivo_pdf_s3=s3_path,
            cnpj_cliente=cnpj,
            nome_cliente=filial.get('nome_cliente'),
            uf_cliente=filial.get('uf'),
            status_odoo='PENDENTE',
            dados_documento=itens_odoo,
            divergente=filial.get('tem_divergencia', False),
            divergencias=filial.get('divergencias'),
            justificativa_aprovacao=filial.get('justificativa'),
            inserido_por=usuario,
            aprovado_por=usuario if filial.get('tem_divergencia') else None,
        )

        if resultado.sucesso:
            registro.marcar_sucesso(resultado.order_id, resultado.order_name)
        else:
            registro.marcar_erro(resultado.mensagem)

        db.session.add(registro)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"[Inserir Lote] Erro ao registrar auditoria: {e}")


def _get_redis():
    """Retorna conexão Redis."""
    try:
        from redis import Redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        return Redis.from_url(redis_url)
    except Exception:
        return None


def _atualizar_progresso(redis_conn, session_key, dados):
    """Atualiza progresso no Redis para polling do frontend."""
    if not redis_conn:
        return
    try:
        chave = f'{REDIS_KEY_PREFIX}:{session_key}'
        redis_conn.setex(chave, REDIS_TTL, json.dumps(dados, default=str))
    except Exception as e:
        logger.debug(f"[Inserir Lote] Erro ao atualizar Redis: {e}")
