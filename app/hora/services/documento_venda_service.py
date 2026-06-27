"""Geração de documentos imprimíveis do Pedido de Venda (HORA).

Documentos (todos via WeasyPrint, mesmo padrão de `recibo_service`):
  - PDV (Pedido/Orçamento): título dinâmico por status
        COTACAO/INCOMPLETO -> "Cotação"; CONFIRMADO/FATURADO -> "Pedido de Venda".
  - Termo de Responsabilidade, Garantia e Compra ("Santana").
  - Termo de Checagem para Entrega 0km (check list).
  - Termo de Ciência e Responsabilidade — Emplacamento Ciclomotor.

Critérios de impressão:
  - PDV: sempre.
  - Termo Garantia + Termo Checagem: status CONFIRMADO ou FATURADO.
  - Termo Ciclomotor: quando houver ao menos 1 item cuja moto seja ciclomotor
        (`HoraModelo.autopropelido is False` — campo canônico, o mesmo que
        classifica a NF-e em `cadastro.py`).

Multi-moto: 1 jogo de termos por moto (cada moto tem seu chassi/garantia),
concatenados no PDF. O "pacote" faz merge de tudo conforme o status.

Fronteira do módulo: reusa apenas utilitários compartilhados (render_template,
weasyprint, pypdf) — nenhuma lógica de módulo vizinho.
"""
from __future__ import annotations

import base64
import os
from decimal import Decimal
from io import BytesIO
from typing import Optional

from flask import current_app, render_template

from app.hora.models.venda import (
    HoraVenda,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_FATURADO,
)

# Meses por extenso para a data dos termos ("São Paulo, DD de MÊS de AAAA").
_MESES_PT = (
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
)

# Status que liberam os termos de compra (Garantia/Checagem).
STATUS_TERMOS = (VENDA_STATUS_CONFIRMADO, VENDA_STATUS_FATURADO)

# Cabeçalho dos documentos: a holding HORA é SEMPRE o emitente (razão social,
# CNPJ e e-mail FIXOS da matriz — regra fiscal: a NF-e sai sempre da matriz). A loja
# física da venda entra apenas como "Vendido por: <nome>" (sem CNPJ/endereço/telefone).
EMITENTE_MATRIZ = {
    'razao_social': 'HORA COMÉRCIO DE MOTOCICLETAS LTDA',
    'cnpj': '62.634.044/0001-20',
    'email': 'financeiro@motochefesp.com.br',
}


class DocumentoVendaError(Exception):
    """Erro de negócio na geração de documento (mensagem amigável p/ o operador)."""


# ---------------------------------------------------------------------------
# Logo (data URI base64) — embutido para não depender de base_url/servidor.
# ---------------------------------------------------------------------------
_LOGO_CACHE: Optional[str] = None


def _logo_data_uri() -> str:
    global _LOGO_CACHE
    if _LOGO_CACHE is None:
        path = os.path.join(
            current_app.root_path, 'static', 'hora', 'img', 'motochefe_logo.png'
        )
        try:
            with open(path, 'rb') as fh:
                b64 = base64.b64encode(fh.read()).decode('ascii')
            _LOGO_CACHE = f'data:image/png;base64,{b64}'
        except OSError:
            _LOGO_CACHE = ''  # sem logo: cabeçalho cai para o texto
    return _LOGO_CACHE


# ---------------------------------------------------------------------------
# Classificação de ciclomotor (critério canônico: modelo.autopropelido is False)
# ---------------------------------------------------------------------------
def itens_ciclomotor(venda: HoraVenda) -> list:
    """Itens (motos) cuja classificação é ciclomotor (não-autopropelido)."""
    out = []
    for it in (venda.itens or []):
        modelo = it.moto.modelo if it.moto else None
        if modelo is not None and modelo.autopropelido is False:
            out.append(it)
    return out


def tem_ciclomotor(venda: HoraVenda) -> bool:
    return bool(itens_ciclomotor(venda))


def titulo_pdv(venda: HoraVenda) -> str:
    """COTACAO/INCOMPLETO -> 'Cotação'; CONFIRMADO/FATURADO -> 'Pedido de Venda'."""
    return 'Pedido de Venda' if venda.status in STATUS_TERMOS else 'Cotação'


# ---------------------------------------------------------------------------
# Montagem de contexto
# ---------------------------------------------------------------------------
def _emitente(venda: HoraVenda) -> dict:
    """Cabeçalho dos documentos: razão/CNPJ/e-mail FIXOS da matriz +
    `vendido_por` = nome da loja física da venda (rótulo amigável, sem CNPJ)."""
    loja = venda.loja
    return {
        **EMITENTE_MATRIZ,
        'vendido_por': loja.rotulo_display if loja else None,
    }


def _destinatario(venda: HoraVenda) -> dict:
    cid = ' / '.join(p for p in (venda.endereco_cidade, venda.endereco_uf) if p)
    end_partes = [p for p in (venda.endereco_logradouro, venda.endereco_numero) if p]
    if venda.endereco_complemento:
        end_partes.append(venda.endereco_complemento)
    logradouro = ', '.join(end_partes)  # só logradouro/nº/compl (termos têm cidade/UF separados)
    endereco = logradouro
    if cid:
        endereco = f'{endereco} - {cid}' if endereco else cid  # completo (PDV: campo único)
    return {
        'nome': venda.nome_cliente,
        'cpf': venda.cpf_cliente,
        'email': venda.email_cliente,
        'telefone': venda.telefone_cliente,
        'inscricao_estadual': venda.inscricao_estadual,
        'endereco': endereco,
        'logradouro': logradouro,
        'bairro': venda.endereco_bairro,
        'cep': venda.cep,
        'cidade': venda.endereco_cidade,
        'uf': venda.endereco_uf,
    }


def _linhas_produto(venda: HoraVenda) -> list:
    """Linhas da tabela de produtos do PDV (motos + peças)."""
    linhas = []
    for it in (venda.itens or []):
        moto = it.moto
        modelo = moto.modelo if moto else None
        nome = modelo.nome_modelo if modelo else '—'
        potencia = (modelo.potencia_motor if modelo else None) or ''
        detalhes = [f'Chassi: {moto.numero_chassi}'] if moto else []
        if moto and moto.cor:
            detalhes.append(f'Cor: {moto.cor}')
        if moto and moto.numero_motor:
            detalhes.append(f'Motor: {moto.numero_motor}')
        linhas.append({
            'codigo': (nome or '').upper().replace(' ', '-'),
            'descricao': f'{nome} {potencia}'.strip(),
            'detalhe': ' · '.join(detalhes),
            'unid': 'UN',
            'qtd': Decimal('1'),
            'valor_unitario': it.preco_tabela_referencia or Decimal('0'),
            'desconto_pct': it.desconto_percentual or Decimal('0'),
            'desconto_valor': it.desconto_aplicado or Decimal('0'),
            'subtotal': it.preco_final or Decimal('0'),
        })
    for ip in (getattr(venda, 'itens_peca', None) or []):
        peca = getattr(ip, 'peca', None)
        linhas.append({
            'codigo': (peca.codigo_interno if peca and peca.codigo_interno else 'PEÇA'),
            'descricao': (peca.descricao if peca else 'Peça'),
            'detalhe': '',
            'unid': (peca.unidade if peca and getattr(peca, 'unidade', None) else 'UN'),
            'qtd': ip.qtd or Decimal('1'),
            'valor_unitario': ip.preco_unitario_referencia or Decimal('0'),
            'desconto_pct': Decimal('0'),
            'desconto_valor': ip.desconto_aplicado or Decimal('0'),
            'subtotal': ip.preco_final or Decimal('0'),
        })
    return linhas


def _pagamentos(venda: HoraVenda) -> list:
    """Blocos de pagamento (forma + parcelas) para o PDV.

    Usa `venda.pagamentos` (multi-forma). Fallback: 1 bloco a partir do header
    (forma_pagamento + numero_parcelas) quando não há pagamentos registrados.
    """
    from datetime import timedelta

    data_base = venda.data_venda
    intervalo = venda.intervalo_parcelas_dias or 30

    def _parcelas(valor_total: Decimal, n_parc: int) -> list:
        n_parc = max(1, int(n_parc or 1))
        bruto = (Decimal(str(valor_total or 0)) / n_parc).quantize(Decimal('0.01'))
        parcelas = []
        acumulado = Decimal('0')
        for k in range(1, n_parc + 1):
            valor = bruto if k < n_parc else (Decimal(str(valor_total or 0)) - acumulado)
            acumulado += valor
            venc = None
            if data_base:
                venc = data_base + timedelta(days=intervalo * k)
            parcelas.append({'numero': k, 'vencimento': venc, 'valor': valor})
        return parcelas

    blocos = []
    pags = list(venda.pagamentos or [])
    if pags:
        for p in pags:
            fmap = p.forma_map
            label = (fmap.descricao if fmap and fmap.descricao else p.forma_pagamento_hora)
            blocos.append({
                'forma': (label or '').replace('_', ' ').strip(),
                'aut_id': p.aut_id,
                'parcelas': _parcelas(p.valor, p.numero_parcelas),
                'total': Decimal(str(p.valor or 0)),
            })
    else:
        label = (venda.forma_pagamento or 'NÃO INFORMADO').replace('_', ' ')
        blocos.append({
            'forma': label.strip(),
            'aut_id': None,
            'parcelas': _parcelas(venda.valor_total, venda.numero_parcelas or 1),
            'total': Decimal(str(venda.valor_total or 0)),
        })
    return blocos


def _data_extenso(venda: HoraVenda) -> dict:
    """Dia / mês-por-extenso / ano da venda, para os termos."""
    d = venda.data_venda or venda.criado_em
    if not d:
        return {'dia': '', 'mes': '', 'ano': ''}
    return {'dia': f'{d.day:02d}', 'mes': _MESES_PT[d.month - 1], 'ano': d.year}


def _item_moto_ctx(it) -> dict:
    moto = it.moto
    modelo = moto.modelo if moto else None
    potencia = (modelo.potencia_motor if modelo else None) or ''
    # Potência normalizada para marcar o check-list (1000/2000/3000).
    digitos = ''.join(c for c in potencia if c.isdigit())
    potencia_classe = None
    for alvo in ('1000', '2000', '3000'):
        if alvo in digitos:
            potencia_classe = alvo
            break
    return {
        'chassi': moto.numero_chassi if moto else '',
        'modelo': modelo.nome_modelo if modelo else '',
        'cor': moto.cor if moto else '',
        'motor': moto.numero_motor if moto else '',
        'potencia': potencia,
        'potencia_classe': potencia_classe,
        'autopropelido': bool(modelo.autopropelido) if modelo else True,
        'eh_ciclomotor': (modelo.autopropelido is False) if modelo else False,
    }


def _contexto_base(venda: HoraVenda) -> dict:
    from app.utils.timezone import agora_utc_naive
    return {
        'venda': venda,
        'logo_uri': _logo_data_uri(),
        'emitente': _emitente(venda),
        'destinatario': _destinatario(venda),
        'data_extenso': _data_extenso(venda),
        'numero_pdv': str(venda.id),
        'gerado_em': agora_utc_naive(),
    }


# ---------------------------------------------------------------------------
# Render / merge
# ---------------------------------------------------------------------------
def _render_pdf(template: str, **ctx) -> bytes:
    from weasyprint import HTML  # lazy import (custo de boot)
    html_str = render_template(template, **ctx)
    return HTML(string=html_str).write_pdf()


def _merge(pdfs: list) -> bytes:
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    for blob in pdfs:
        reader = PdfReader(BytesIO(blob))
        for page in reader.pages:
            writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Geradores públicos (cada um retorna bytes de PDF)
# ---------------------------------------------------------------------------
def gerar_pdv_pdf(venda: HoraVenda) -> bytes:
    ctx = _contexto_base(venda)
    ctx.update({
        'titulo': titulo_pdv(venda),
        'linhas_produto': _linhas_produto(venda),
        'blocos_pagamento': _pagamentos(venda),
    })
    return _render_pdf('hora/documentos/pdv.html', **ctx)


def gerar_termo_garantia_pdf(venda: HoraVenda) -> bytes:
    # Defesa em profundidade: o dropdown desabilita o link fora de CONFIRMADO/FATURADO,
    # mas a URL é acessível direto — o termo só vale a partir da confirmação.
    if venda.status not in STATUS_TERMOS:
        raise DocumentoVendaError(
            'Termo de garantia só está disponível para pedidos Confirmados ou Faturados.'
        )
    base = _contexto_base(venda)
    if not venda.itens:
        raise DocumentoVendaError('Pedido sem motos — termo de garantia não se aplica.')
    pdfs = [
        _render_pdf('hora/documentos/termo_garantia.html', item=_item_moto_ctx(it), **base)
        for it in venda.itens
    ]
    return _merge(pdfs)


def gerar_termo_checagem_pdf(venda: HoraVenda) -> bytes:
    if venda.status not in STATUS_TERMOS:
        raise DocumentoVendaError(
            'Termo de checagem só está disponível para pedidos Confirmados ou Faturados.'
        )
    base = _contexto_base(venda)
    if not venda.itens:
        raise DocumentoVendaError('Pedido sem motos — checagem não se aplica.')
    pdfs = [
        _render_pdf('hora/documentos/termo_checagem.html', item=_item_moto_ctx(it), **base)
        for it in venda.itens
    ]
    return _merge(pdfs)


def gerar_termo_ciclomotor_pdf(venda: HoraVenda) -> bytes:
    base = _contexto_base(venda)
    itens = itens_ciclomotor(venda)
    if not itens:
        raise DocumentoVendaError('Nenhuma moto deste pedido é ciclomotor.')
    pdfs = [
        _render_pdf('hora/documentos/termo_ciclomotor.html', item=_item_moto_ctx(it), **base)
        for it in itens
    ]
    return _merge(pdfs)


def gerar_pacote_pdf(venda: HoraVenda) -> bytes:
    """PDF único: PDV + (termos quando CONFIRMADO/FATURADO) + (ciclomotor se houver)."""
    partes = [gerar_pdv_pdf(venda)]
    if venda.status in STATUS_TERMOS:
        if venda.itens:
            partes.append(gerar_termo_garantia_pdf(venda))
            partes.append(gerar_termo_checagem_pdf(venda))
        if tem_ciclomotor(venda):
            partes.append(gerar_termo_ciclomotor_pdf(venda))
    return _merge(partes)
