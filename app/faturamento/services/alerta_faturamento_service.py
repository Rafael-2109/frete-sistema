"""Alertas de faturamento por CNPJ (e-mail + Teams).

Ao faturar (NF nova via sync Odoo) para um CNPJ cadastrado e ativo, dispara UM
aviso por cliente (agrupando as NFs novas) por e-mail (lista do CNPJ, todos em
cópia) e no Teams (canal fixo via webhook). Idempotente por (numero_nf, canal).

`processar_alertas_faturamento` NUNCA levanta exceção (garantia p/ o hook da
sync Odoo — nunca derruba o faturamento).
"""
import re
import logging

import requests

from app import db
from app.utils.timezone import agora_utc_naive
from app.faturamento.models import (
    RelatorioFaturamentoImportado,
    AlertaFaturamentoCnpj,
    AlertaFaturamentoConfig,
    AlertaFaturamentoEnviado,
)
from app.notificacoes.email_sender import email_sender, EmailTemplates, EmailConfig

logger = logging.getLogger(__name__)

TEAMS_TIMEOUT = 15


def normalizar_cnpj(cnpj):
    return re.sub(r'\D', '', cnpj or '')


def _fmt_moeda(valor):
    v = float(valor or 0)
    return ('R$ ' + f'{v:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_data(d):
    return d.strftime('%d/%m/%Y') if d else '-'


def agrupar_por_cnpj(cabecalhos):
    grupos = {}
    for nf in cabecalhos:
        grupos.setdefault(normalizar_cnpj(nf.cnpj_cliente), []).append(nf)
    return grupos


def filtrar_nao_enviadas(cabecalhos, canal):
    numeros = [n.numero_nf for n in cabecalhos]
    if not numeros:
        return []
    ja_ok = {
        r.numero_nf for r in AlertaFaturamentoEnviado.query.filter(
            AlertaFaturamentoEnviado.canal == canal,
            AlertaFaturamentoEnviado.status == 'ok',
            AlertaFaturamentoEnviado.numero_nf.in_(numeros),
        ).all()
    }
    return [n for n in cabecalhos if n.numero_nf not in ja_ok]


def montar_linhas(cabecalhos):
    linhas, total = [], 0.0
    for nf in sorted(cabecalhos, key=lambda n: n.numero_nf):
        total += float(nf.valor_total or 0)
        cidade = f"{nf.municipio}/{nf.estado}" if nf.municipio else (nf.estado or '')
        linhas.append({
            'numero_nf': nf.numero_nf,
            'data': _fmt_data(nf.data_fatura),
            'valor': _fmt_moeda(nf.valor_total),
            'cidade': cidade,
        })
    return linhas, _fmt_moeda(total)


def montar_dados_email(linhas, total):
    dados = {f"NF {l['numero_nf']}": f"{l['data']} · {l['valor']} · {l['cidade']}" for l in linhas}
    dados['Total'] = total
    return dados


def montar_texto_teams(nome, cnpj, linhas, total):
    corpo = "\n".join(
        f"- NF {l['numero_nf']} · {l['data']} · {l['valor']} · {l['cidade']}" for l in linhas
    )
    return f"**Faturamento — {nome or cnpj}** (CNPJ {cnpj})\n{corpo}\n**Total: {total}**"


def registrar_envio(numero_nf, cnpj, canal, ok, detalhe=None):
    """Upsert por (numero_nf, canal): evita violar o UNIQUE ao reprocessar erro."""
    reg = AlertaFaturamentoEnviado.query.filter_by(numero_nf=numero_nf, canal=canal).first()
    if reg is None:
        reg = AlertaFaturamentoEnviado(numero_nf=numero_nf, canal=canal)
        db.session.add(reg)
    reg.cnpj = cnpj
    reg.status = 'ok' if ok else 'erro'
    reg.detalhe = (detalhe or '')[:2000]
    reg.enviado_em = agora_utc_naive()


def enviar_email(cnpj_cfg, nome, cnpj, linhas, total):
    if not EmailConfig.is_configured():
        return {'success': False, 'error': 'E-mail não configurado (EMAIL_*)'}
    emails = cnpj_cfg.lista_emails()
    if not emails:
        return {'success': False, 'error': 'CNPJ sem e-mails cadastrados'}
    return email_sender.send(
        to=emails[0],
        cc=emails[1:] or None,
        subject=f"Faturamento — {nome or cnpj}",
        body_html=EmailTemplates.info(
            titulo=f"Faturamento — {nome or cnpj} (CNPJ {cnpj})",
            mensagem="Foram faturadas as seguintes notas para este cliente:",
            dados=montar_dados_email(linhas, total),
        ),
    )


def enviar_teams(config, texto):
    if not (config.teams_ativo and config.teams_webhook_url):
        return {'success': False, 'error': 'Teams desativado ou sem URL'}
    try:
        resp = requests.post(config.teams_webhook_url, json={'text': texto}, timeout=TEAMS_TIMEOUT)
        if 200 <= resp.status_code < 300:
            return {'success': True}
        return {'success': False, 'error': f'HTTP {resp.status_code}'}
    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}


def _processar_canal(nfs, cnpj, nome, canal, envia_fn):
    """Filtra pendentes do canal, envia 1x agrupado, registra por NF. Retorna (ok, erro)."""
    pend = filtrar_nao_enviadas(nfs, canal)
    if not pend:
        return None, None
    linhas, total = montar_linhas(pend)
    if canal == 'email':
        r = envia_fn(nome, cnpj, linhas, total)
    else:
        r = envia_fn(montar_texto_teams(nome, cnpj, linhas, total))
    ok = bool(r.get('success'))
    for nf in pend:
        registrar_envio(nf.numero_nf, cnpj, canal, ok, r.get('error') or r.get('message_id'))
    return ok, (None if ok else r.get('error'))


def processar_alertas_faturamento(nfs_novas):
    """Entrypoint do hook. NUNCA levanta exceção."""
    resumo = {'cnpjs': 0, 'emails_ok': 0, 'teams_ok': 0, 'erros': []}
    try:
        if not nfs_novas:
            return resumo
        cabecalhos = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.numero_nf.in_(list(nfs_novas)),
            RelatorioFaturamentoImportado.ativo.is_(True),
        ).all()
        if not cabecalhos:
            return resumo
        config = AlertaFaturamentoConfig.get_config()
        for cnpj, nfs in agrupar_por_cnpj(cabecalhos).items():
            try:
                cnpj_cfg = AlertaFaturamentoCnpj.query.filter_by(cnpj=cnpj, ativo=True).first()
                if not cnpj_cfg:
                    continue
                resumo['cnpjs'] += 1
                nome = cnpj_cfg.nome_cliente or (nfs[0].nome_cliente if nfs else None)
                if config.email_ativo:
                    ok, erro = _processar_canal(
                        nfs, cnpj, nome, 'email',
                        lambda n, c, l, t: enviar_email(cnpj_cfg, n, c, l, t))
                    if ok:
                        resumo['emails_ok'] += 1
                    elif erro:
                        resumo['erros'].append(f"email {cnpj}: {erro}")
                if config.teams_ativo:
                    ok, erro = _processar_canal(
                        nfs, cnpj, nome, 'teams',
                        lambda texto: enviar_teams(config, texto))
                    if ok:
                        resumo['teams_ok'] += 1
                    elif erro:
                        resumo['erros'].append(f"teams {cnpj}: {erro}")
                db.session.commit()
            except Exception as e:  # isola por CNPJ
                db.session.rollback()
                logger.error(f"Alerta faturamento CNPJ {cnpj} falhou: {e}", exc_info=True)
                resumo['erros'].append(f"{cnpj}: {e}")
        return resumo
    except Exception as e:  # nunca propaga p/ a sync
        logger.error(f"processar_alertas_faturamento falhou: {e}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        resumo['erros'].append(str(e))
        return resumo


def enviar_teste(cnpj_cfg, config):
    """Dispara um aviso de TESTE (linha fictícia) para o CNPJ. NÃO grava log."""
    linhas = [{'numero_nf': 'TESTE', 'data': _fmt_data(agora_utc_naive().date()),
               'valor': _fmt_moeda(0), 'cidade': ''}]
    total = _fmt_moeda(0)
    nome = cnpj_cfg.nome_cliente or cnpj_cfg.cnpj
    r_email = enviar_email(cnpj_cfg, nome, cnpj_cfg.cnpj, linhas, total) if config.email_ativo else {'success': None}
    r_teams = enviar_teams(config, montar_texto_teams(nome, cnpj_cfg.cnpj, linhas, total)) if config.teams_ativo else {'success': None}
    return {'email': r_email, 'teams': r_teams}
