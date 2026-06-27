"""Comissao de vendas — roadmap #28 (Fatia 1: cadastro de configuracao).

Cadastro de:
  - comissao base por moto (config singleton);
  - faixas de desconto (R$) -> reducao da comissao (R$);
  - comissao por peca (hora_peca.valor_comissao);
  - teto de desconto por modelo (hora_modelo.desconto_maximo).

Helper `reducao_comissao_para_desconto` ja disponivel (sera usado no calculo
da Fatia 3). Calculo de comissao da venda e fila de aprovacao de desconto
(Fatia 2) NAO estao aqui.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app import db
from app.hora.models import (
    HoraComissaoConfig, HoraComissaoFaixaDesconto, HoraModelo, HoraPeca,
    HoraVenda, VENDA_STATUS_FATURADO,
)
from app.utils.timezone import agora_utc_naive

ZERO = Decimal('0')


def _to_dec(valor) -> Decimal:
    """Converte str BR ('1.234,56') ou US / numero -> Decimal (>=0). None->0."""
    if valor is None:
        return ZERO
    s = str(valor).strip()
    if not s:
        return ZERO
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        d = Decimal(s)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f'Valor invalido: {valor!r}') from exc
    if d < 0:
        raise ValueError('Valor nao pode ser negativo.')
    return d


def get_config() -> HoraComissaoConfig:
    """Retorna a config singleton (cria id=1 se nao existir)."""
    cfg = HoraComissaoConfig.query.get(1)
    if cfg is None:
        cfg = HoraComissaoConfig(id=1, comissao_base_moto=ZERO,
                                 atualizado_em=agora_utc_naive())
        db.session.add(cfg)
        db.session.commit()
    return cfg


def set_comissao_base_moto(valor, usuario: Optional[str] = None) -> HoraComissaoConfig:
    cfg = get_config()
    cfg.comissao_base_moto = _to_dec(valor)
    cfg.atualizado_por = (usuario or '').strip()[:100] or None
    cfg.atualizado_em = agora_utc_naive()
    db.session.commit()
    return cfg


def listar_faixas(apenas_ativas: bool = False) -> List[HoraComissaoFaixaDesconto]:
    q = HoraComissaoFaixaDesconto.query
    if apenas_ativas:
        q = q.filter_by(ativo=True)
    return q.order_by(HoraComissaoFaixaDesconto.desconto_min).all()


def criar_faixa(desconto_min, desconto_max, reducao_comissao) -> HoraComissaoFaixaDesconto:
    """Cria uma faixa de desconto->reducao. desconto_max vazio = sem limite superior."""
    dmin = _to_dec(desconto_min)
    dmax = None if (desconto_max is None or str(desconto_max).strip() == '') else _to_dec(desconto_max)
    if dmax is not None and dmax <= dmin:
        raise ValueError('Desconto maximo da faixa deve ser maior que o minimo.')
    faixa = HoraComissaoFaixaDesconto(
        desconto_min=dmin, desconto_max=dmax,
        reducao_comissao=_to_dec(reducao_comissao), ativo=True,
        criado_em=agora_utc_naive(),
    )
    db.session.add(faixa)
    db.session.commit()
    return faixa


def remover_faixa(faixa_id: int) -> None:
    faixa = HoraComissaoFaixaDesconto.query.get(faixa_id)
    if not faixa:
        raise ValueError('Faixa nao encontrada.')
    db.session.delete(faixa)
    db.session.commit()


def set_comissao_peca(peca_id: int, valor) -> HoraPeca:
    peca = HoraPeca.query.get(peca_id)
    if not peca:
        raise ValueError('Peca nao encontrada.')
    peca.valor_comissao = _to_dec(valor)
    db.session.commit()
    return peca


def set_teto_modelo(modelo_id: int, desconto_maximo) -> HoraModelo:
    """Define o teto de desconto (R$) por modelo. Vazio = sem teto (NULL)."""
    modelo = HoraModelo.query.get(modelo_id)
    if not modelo:
        raise ValueError('Modelo nao encontrado.')
    if desconto_maximo is None or str(desconto_maximo).strip() == '':
        modelo.desconto_maximo = None
    else:
        modelo.desconto_maximo = _to_dec(desconto_maximo)
    db.session.commit()
    return modelo


def calcular_comissao_venda(venda, faixas=None, base=None) -> dict:
    """Calcula a comissao de uma venda (#28, Fatia 3).

    - Motos: por item, comissao_base_moto - reducao da faixa do desconto do item
      (clamp >= 0). Soma de todos os itens-moto.
    - Pecas: soma de peca.valor_comissao * qtd dos itens_peca.

    Retorna {comissao_motos, comissao_pecas, total}. Brindes nao geram comissao.

    `faixas`/`base` opcionais: pre-carregados pelo caller (ex.: relatorio
    gerencial que agrega N vendas) para evitar 1 SELECT de faixas + get_config
    POR ITEM/VENDA (N+1). Default mantem o comportamento historico.
    """
    if base is None:
        base = Decimal(str(get_config().comissao_base_moto or 0))
    if faixas is None:
        faixas = listar_faixas(apenas_ativas=True)
    comissao_motos = ZERO
    for item in (venda.itens or []):
        desconto = Decimal(str(item.desconto_aplicado or 0))
        c = base - reducao_comissao_para_desconto(desconto, faixas)
        comissao_motos += c if c > ZERO else ZERO
    comissao_pecas = ZERO
    for ip in (getattr(venda, 'itens_peca', None) or []):
        peca = getattr(ip, 'peca', None)
        if peca:
            comissao_pecas += (
                Decimal(str(peca.valor_comissao or 0)) * Decimal(str(ip.qtd or 0))
            )
    return {
        'comissao_motos': comissao_motos,
        'comissao_pecas': comissao_pecas,
        'total': comissao_motos + comissao_pecas,
    }


def relatorio_comissao(data_inicio=None, data_fim=None) -> List[dict]:
    """Relatorio de comissao por vendedor de vendas FATURADAS no periodo.

    `data_inicio`/`data_fim` sao `date` (inclusivos). Comissao conta quando a
    venda esta FATURADA (decisao do dono). Agrupa por HoraVenda.vendedor.
    Retorna lista de dicts {vendedor, qtd_vendas, total} ordenada por total desc.
    """
    from datetime import datetime, time, timedelta
    q = HoraVenda.query.filter(HoraVenda.status == VENDA_STATUS_FATURADO)
    if data_inicio:
        q = q.filter(HoraVenda.faturado_em >= datetime.combine(data_inicio, time.min))
    if data_fim:
        # inclusivo: < (data_fim + 1 dia)
        q = q.filter(HoraVenda.faturado_em < datetime.combine(data_fim + timedelta(days=1), time.min))

    por_vendedor: dict = {}
    for v in q.all():
        c = calcular_comissao_venda(v)
        vend = (v.vendedor or '(sem vendedor)')
        agg = por_vendedor.setdefault(vend, {'vendedor': vend, 'qtd_vendas': 0, 'total': ZERO})
        agg['qtd_vendas'] += 1
        agg['total'] += c['total']
    return sorted(por_vendedor.values(), key=lambda x: x['total'], reverse=True)


def reducao_comissao_para_desconto(desconto_rs, faixas=None) -> Decimal:
    """Retorna a reducao de comissao (R$) para um dado valor de desconto (R$).

    Aplica a faixa ativa cujo intervalo [desconto_min, desconto_max) contem o
    desconto. desconto_max NULL = aberto superiormente. Se nenhuma faixa casa,
    reducao = 0. (Usado no calculo de comissao — Fatia 3.)
    """
    d = _to_dec(desconto_rs)
    faixas = listar_faixas(apenas_ativas=True) if faixas is None else faixas
    for faixa in faixas:
        dmin = Decimal(str(faixa.desconto_min or 0))
        dmax = faixa.desconto_max
        if d >= dmin and (dmax is None or d < Decimal(str(dmax))):
            return Decimal(str(faixa.reducao_comissao or 0))
    return ZERO
