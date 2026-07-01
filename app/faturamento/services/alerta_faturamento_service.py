"""Alertas de faturamento por CNPJ (e-mail).

Ao faturar (NF nova via sync Odoo) para um CNPJ cadastrado e ativo, dispara UM
aviso por cliente (agrupando as NFs novas) por e-mail — 1 e-mail com todos os
endereços do CNPJ em cópia. Idempotente por (numero_nf, canal='email').

`processar_alertas_faturamento` NUNCA levanta exceção (garantia p/ o hook da
sync Odoo — nunca derruba o faturamento).
"""
import re
import logging

from app import db
from app.utils.timezone import agora_utc_naive
from app.faturamento.models import (
    RelatorioFaturamentoImportado,
    AlertaFaturamentoCnpj,
    AlertaFaturamentoEnviado,
)
from app.notificacoes.email_sender import email_sender, EmailTemplates, EmailConfig

logger = logging.getLogger(__name__)

# Lista de e-mails padrao dos alertas (time Conservas Campo Belo que acompanha
# o faturamento do Atacadao RJ). Usada como valor inicial no cadastro de novos
# CNPJs (tela) e na carga inicial (seed). Editavel por CNPJ na tela.
EMAILS_PADRAO = (
    "stephanie.chaves@conservascampobelo.com.br;"
    "gislene.goes@conservascampobelo.com.br;"
    "elane.souza@conservascampobelo.com.br;"
    "sabrina.lima@conservascampobelo.com.br"
)


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


def filtrar_nao_enviadas(cabecalhos, canal='email'):
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


def registrar_envio(numero_nf, cnpj, ok, detalhe=None, canal='email'):
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


def processar_alertas_faturamento(nfs_novas):
    """Entrypoint do hook. NUNCA levanta exceção."""
    resumo = {'cnpjs': 0, 'emails_ok': 0, 'erros': []}
    try:
        if not nfs_novas:
            return resumo
        cabecalhos = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.numero_nf.in_(list(nfs_novas)),
            RelatorioFaturamentoImportado.ativo.is_(True),
        ).all()
        if not cabecalhos:
            return resumo
        for cnpj, nfs in agrupar_por_cnpj(cabecalhos).items():
            try:
                cnpj_cfg = AlertaFaturamentoCnpj.query.filter_by(cnpj=cnpj, ativo=True).first()
                if not cnpj_cfg:
                    continue
                resumo['cnpjs'] += 1
                nome = cnpj_cfg.nome_cliente or (nfs[0].nome_cliente if nfs else None)
                pend = filtrar_nao_enviadas(nfs, 'email')
                if not pend:
                    continue
                linhas, total = montar_linhas(pend)
                r = enviar_email(cnpj_cfg, nome, cnpj, linhas, total)
                ok = bool(r.get('success'))
                for nf in pend:
                    registrar_envio(nf.numero_nf, cnpj, ok, r.get('error') or r.get('message_id'))
                if ok:
                    resumo['emails_ok'] += 1
                else:
                    resumo['erros'].append(f"email {cnpj}: {r.get('error')}")
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


def enviar_teste(cnpj_cfg):
    """Dispara um e-mail de TESTE (linha fictícia) para o CNPJ. NÃO grava log."""
    linhas = [{'numero_nf': 'TESTE', 'data': _fmt_data(agora_utc_naive().date()),
               'valor': _fmt_moeda(0), 'cidade': ''}]
    total = _fmt_moeda(0)
    nome = cnpj_cfg.nome_cliente or cnpj_cfg.cnpj
    return {'email': enviar_email(cnpj_cfg, nome, cnpj_cfg.cnpj, linhas, total)}
