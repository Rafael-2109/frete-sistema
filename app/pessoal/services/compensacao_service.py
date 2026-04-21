"""Compensacao Saida <-> Entrada Empresa (pessoal).

Contexto de negocio:
    Depósitos transitorios altos (ex: R$ 200k entra, R$ 200k sai no mesmo periodo)
    distorcem KPIs. Usuario marca categorias como "compensavel":
      - compensavel_tipo='S' -> Saida Empresa  (debito)
      - compensavel_tipo='E' -> Entrada Empresa (credito)
    Esta biblioteca pareia (saida, entrada) consumindo valor de uma contra a outra.

Conceitos:
    - valor_compensado (em PessoalTransacao): soma das compensacoes ATIVAS desta
      transacao (seja como saida ou entrada). Cache agregado, recalculado sempre
      apos aplicar/reverter.
    - valor_efetivo: valor - valor_compensado (nunca negativo). Propriedade do
      model; usado em relatorios.
    - Quando valor_compensado >= valor, a transacao recebe excluir_relatorio=True
      automaticamente (sai dos totais).

Observabilidade:
    - Todo pareamento gera linha em pessoal_compensacoes com snapshot de residuos,
      quem fez, quando, origem (auto/manual). Reversao mantem historico (status=REVERTIDA).
    - Logs estruturados em cada operacao.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, or_

from app import db
from app.pessoal.models import (
    PessoalCategoria, PessoalCompensacao, PessoalTransacao,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# =============================================================================
# TIPOS E HELPERS
# =============================================================================
@dataclass
class SugestaoPar:
    """Par candidato de compensacao (saida + entrada + valor a casar)."""
    saida: PessoalTransacao
    entrada: PessoalTransacao
    valor_a_compensar: float
    distancia_dias: int
    score: float  # menor distancia temporal + menor residuo = melhor score

    def to_dict(self):
        return {
            'saida': {
                'id': self.saida.id,
                'data': self.saida.data.isoformat() if self.saida.data else None,
                'historico': self.saida.historico,
                'descricao': self.saida.descricao,
                'valor': float(self.saida.valor),
                'valor_compensado': float(self.saida.valor_compensado or 0),
                'valor_restante': float(self.saida.valor) - float(self.saida.valor_compensado or 0),
                'categoria_id': self.saida.categoria_id,
            },
            'entrada': {
                'id': self.entrada.id,
                'data': self.entrada.data.isoformat() if self.entrada.data else None,
                'historico': self.entrada.historico,
                'descricao': self.entrada.descricao,
                'valor': float(self.entrada.valor),
                'valor_compensado': float(self.entrada.valor_compensado or 0),
                'valor_restante': float(self.entrada.valor) - float(self.entrada.valor_compensado or 0),
                'categoria_id': self.entrada.categoria_id,
            },
            'valor_a_compensar': self.valor_a_compensar,
            'distancia_dias': self.distancia_dias,
            'score': self.score,
        }


def _ids_categorias_compensaveis(tipo: str) -> set[int]:
    """IDs de categorias com compensavel_tipo = 'S' ou 'E' (ativas)."""
    assert tipo in ('S', 'E')
    return {
        c.id for c in PessoalCategoria.query.filter_by(
            compensavel_tipo=tipo, ativa=True,
        ).all()
    }


def _restante(t: PessoalTransacao) -> float:
    """Valor ainda nao compensado de uma transacao."""
    return float(t.valor or 0) - float(t.valor_compensado or 0)


# =============================================================================
# RECALCULO DE CACHE
# =============================================================================
def recalcular_valor_compensado(transacao_id: int) -> float:
    """Soma compensacoes ATIVAS onde a transacao aparece (como saida OU entrada).

    Atualiza PessoalTransacao.valor_compensado + excluir_relatorio quando aplicavel.
    Retorna o novo valor_compensado.
    """
    total = db.session.query(
        func.coalesce(func.sum(PessoalCompensacao.valor_compensado), 0)
    ).filter(
        PessoalCompensacao.status == 'ATIVA',
        or_(
            PessoalCompensacao.saida_id == transacao_id,
            PessoalCompensacao.entrada_id == transacao_id,
        ),
    ).scalar() or 0

    t = db.session.get(PessoalTransacao, transacao_id)
    if not t:
        return 0.0
    t.valor_compensado = Decimal(total)

    # Quando 100% compensado, tira do relatorio. Se residuo > 0, mantem visivel.
    valor_tot = float(t.valor or 0)
    compensado = float(total)
    if compensado >= valor_tot and valor_tot > 0:
        t.excluir_relatorio = True
    elif compensado == 0:
        # Se nao ha mais compensacao E nao tem outro motivo para excluir (categoria
        # Desconsiderar), restaurar para False.
        from app.pessoal.services.categorizacao_service import eh_categoria_desconsiderar
        if not eh_categoria_desconsiderar(t.categoria_id):
            t.excluir_relatorio = False
    return compensado


# =============================================================================
# SUGESTAO DE PARES (dry-run para preview)
# =============================================================================
def sugerir_pareamento(
    janela_dias: int = 7,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    max_sugestoes: int = 100,
) -> list[SugestaoPar]:
    """Gera pares (saida, entrada) candidatos a compensar.

    Algoritmo:
    1. Busca saidas com residuo > 0 em categorias compensavel_tipo='S'
    2. Para cada saida, busca entradas no intervalo [saida.data - janela_dias,
       saida.data + janela_dias] em categorias compensavel_tipo='E' com residuo > 0
    3. Prioriza: mesmo valor exato > valor proximo, menor distancia temporal primeiro
    4. Cada entrada so aparece em 1 par de sugestao por rodada (greedy)
    """
    ids_saida_cats = _ids_categorias_compensaveis('S')
    ids_entrada_cats = _ids_categorias_compensaveis('E')
    if not ids_saida_cats or not ids_entrada_cats:
        logger.info(
            'sugerir_pareamento: sem categorias compensaveis (saidas=%d, entradas=%d)',
            len(ids_saida_cats), len(ids_entrada_cats),
        )
        return []

    q_saidas = PessoalTransacao.query.filter(
        PessoalTransacao.tipo == 'debito',
        PessoalTransacao.categoria_id.in_(ids_saida_cats),
        PessoalTransacao.valor > PessoalTransacao.valor_compensado,
    )
    q_entradas = PessoalTransacao.query.filter(
        PessoalTransacao.tipo == 'credito',
        PessoalTransacao.categoria_id.in_(ids_entrada_cats),
        PessoalTransacao.valor > PessoalTransacao.valor_compensado,
    )
    if data_inicio:
        q_saidas = q_saidas.filter(PessoalTransacao.data >= data_inicio)
        q_entradas = q_entradas.filter(PessoalTransacao.data >= data_inicio - timedelta(days=janela_dias))
    if data_fim:
        q_saidas = q_saidas.filter(PessoalTransacao.data <= data_fim)
        q_entradas = q_entradas.filter(PessoalTransacao.data <= data_fim + timedelta(days=janela_dias))

    saidas = q_saidas.order_by(PessoalTransacao.data.asc()).all()
    entradas = q_entradas.order_by(PessoalTransacao.data.asc()).all()
    entradas_disponiveis = {e.id: _restante(e) for e in entradas}

    sugestoes: list[SugestaoPar] = []
    for s in saidas:
        if len(sugestoes) >= max_sugestoes:
            break
        resto_s = _restante(s)
        if resto_s <= 0:
            continue

        # Candidatas dentro da janela temporal
        cand = []
        for e in entradas:
            if entradas_disponiveis.get(e.id, 0) <= 0:
                continue
            dist = abs((s.data - e.data).days)
            if dist > janela_dias:
                continue
            resto_e = entradas_disponiveis[e.id]
            valor_match = min(resto_s, resto_e)
            # score: prioriza (match exato, menor distancia, maior valor_match)
            match_exato = 1.0 if abs(resto_s - resto_e) < 0.01 else 0.0
            score = match_exato * 1000 - dist * 10 + valor_match / 1_000_000
            cand.append((score, e, valor_match, dist))

        if not cand:
            continue
        cand.sort(key=lambda x: x[0], reverse=True)
        _, e_best, valor_match, dist = cand[0]
        sugestoes.append(SugestaoPar(
            saida=s, entrada=e_best,
            valor_a_compensar=valor_match,
            distancia_dias=dist, score=cand[0][0],
        ))
        entradas_disponiveis[e_best.id] -= valor_match
        # Nao decrementa resto_s porque cada saida so gera 1 sugestao por rodada
        # (usuario pode rodar de novo para pegar residuo)

    return sugestoes


# =============================================================================
# APLICAR COMPENSACAO
# =============================================================================
def aplicar_compensacao(
    saida_id: int,
    entrada_id: int,
    valor: float,
    origem: str = 'manual',
    criado_por: Optional[str] = None,
    observacao: Optional[str] = None,
    commit: bool = True,
) -> PessoalCompensacao:
    """Cria uma compensacao entre saida e entrada.

    Valida:
    - Transacoes existem, sao tipos corretos (debito/credito), categorias marcadas
    - valor <= residuo em ambas as pontas
    - saida != entrada
    """
    if saida_id == entrada_id:
        raise ValueError('saida_id e entrada_id devem ser diferentes.')
    if origem not in ('auto', 'manual'):
        raise ValueError(f'origem invalida: {origem!r}')
    if valor <= 0:
        raise ValueError('valor deve ser > 0.')

    saida = db.session.get(PessoalTransacao, saida_id)
    entrada = db.session.get(PessoalTransacao, entrada_id)
    if not saida or not entrada:
        raise ValueError('Transacao nao encontrada.')
    if saida.tipo != 'debito':
        raise ValueError(f'saida_id={saida_id} nao e debito (tipo={saida.tipo!r}).')
    if entrada.tipo != 'credito':
        raise ValueError(f'entrada_id={entrada_id} nao e credito (tipo={entrada.tipo!r}).')

    # Validar categorias compensaveis (aviso, nao bloqueio — permite compensacao manual livre)
    cat_saida = db.session.get(PessoalCategoria, saida.categoria_id) if saida.categoria_id else None
    cat_entrada = db.session.get(PessoalCategoria, entrada.categoria_id) if entrada.categoria_id else None
    if cat_saida and cat_saida.compensavel_tipo and cat_saida.compensavel_tipo != 'S':
        raise ValueError(
            f'Categoria da saida ({cat_saida.grupo}/{cat_saida.nome}) tem compensavel_tipo'
            f'={cat_saida.compensavel_tipo!r}, incompativel com SAIDA.'
        )
    if cat_entrada and cat_entrada.compensavel_tipo and cat_entrada.compensavel_tipo != 'E':
        raise ValueError(
            f'Categoria da entrada ({cat_entrada.grupo}/{cat_entrada.nome}) tem compensavel_tipo'
            f'={cat_entrada.compensavel_tipo!r}, incompativel com ENTRADA.'
        )

    resto_s = _restante(saida)
    resto_e = _restante(entrada)
    if valor > resto_s + 0.001:
        raise ValueError(f'valor ({valor}) excede residuo da saida ({resto_s}).')
    if valor > resto_e + 0.001:
        raise ValueError(f'valor ({valor}) excede residuo da entrada ({resto_e}).')

    valor_dec = Decimal(str(valor))
    compensacao = PessoalCompensacao(
        saida_id=saida_id,
        entrada_id=entrada_id,
        valor_compensado=valor_dec,
        residuo_saida=Decimal(str(resto_s - valor)),
        residuo_entrada=Decimal(str(resto_e - valor)),
        origem=origem,
        status='ATIVA',
        observacao=observacao,
        criado_por=criado_por,
        criado_em=agora_utc_naive(),
    )
    db.session.add(compensacao)
    db.session.flush()

    # Recalcula cache agregado em ambas as pontas
    recalcular_valor_compensado(saida_id)
    recalcular_valor_compensado(entrada_id)

    logger.info(
        'compensacao_aplicada id=%d saida=%d entrada=%d valor=%.2f origem=%s '
        'residuo_s=%.2f residuo_e=%.2f',
        compensacao.id, saida_id, entrada_id, float(valor_dec), origem,
        float(compensacao.residuo_saida), float(compensacao.residuo_entrada),
    )

    if commit:
        db.session.commit()
    return compensacao


# =============================================================================
# REVERTER
# =============================================================================
def reverter_compensacao(
    compensacao_id: int,
    revertido_por: Optional[str] = None,
    commit: bool = True,
) -> PessoalCompensacao:
    """Marca compensacao como REVERTIDA e recalcula caches."""
    comp = db.session.get(PessoalCompensacao, compensacao_id)
    if not comp:
        raise ValueError(f'Compensacao id={compensacao_id} nao encontrada.')
    if comp.status == 'REVERTIDA':
        raise ValueError(f'Compensacao id={compensacao_id} ja esta revertida.')

    comp.status = 'REVERTIDA'
    comp.revertido_em = agora_utc_naive()
    comp.revertido_por = revertido_por
    db.session.flush()

    recalcular_valor_compensado(comp.saida_id)
    recalcular_valor_compensado(comp.entrada_id)

    logger.info(
        'compensacao_revertida id=%d saida=%d entrada=%d valor=%.2f por=%s',
        comp.id, comp.saida_id, comp.entrada_id,
        float(comp.valor_compensado), revertido_por or '?',
    )

    if commit:
        db.session.commit()
    return comp


# =============================================================================
# COMPENSACAO AUTOMATICA EM LOTE
# =============================================================================
def compensar_automatico(
    janela_dias: int = 7,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    dry_run: bool = True,
    criado_por: Optional[str] = None,
) -> dict:
    """Aplica compensacoes em lote conforme sugestoes (greedy).

    Args:
        janela_dias: max dias entre saida e entrada para considerar par valido.
        data_inicio/data_fim: restringe as saidas processadas (entradas podem estar
            ate `janela_dias` fora).
        dry_run: se True, nao cria compensacoes — apenas retorna o que faria.
        criado_por: nome do usuario para auditoria.

    Returns:
        dict com 'sugestoes' (lista), 'aplicadas' (lista de ids), 'dry_run' (bool).
    """
    sugestoes = sugerir_pareamento(
        janela_dias=janela_dias, data_inicio=data_inicio, data_fim=data_fim,
        max_sugestoes=10_000,
    )

    aplicadas = []
    erros = []
    if not dry_run:
        for sug in sugestoes:
            try:
                comp = aplicar_compensacao(
                    saida_id=sug.saida.id,
                    entrada_id=sug.entrada.id,
                    valor=sug.valor_a_compensar,
                    origem='auto',
                    criado_por=criado_por,
                    observacao=f'Auto (janela={janela_dias}d, dist={sug.distancia_dias}d)',
                    commit=False,
                )
                aplicadas.append(comp.id)
            except Exception as e:
                logger.error(
                    'compensar_automatico falha saida=%d entrada=%d: %s',
                    sug.saida.id, sug.entrada.id, e,
                )
                erros.append({
                    'saida_id': sug.saida.id,
                    'entrada_id': sug.entrada.id,
                    'erro': str(e),
                })
        if aplicadas:
            db.session.commit()

    logger.info(
        'compensar_automatico dry=%s janela=%dd sugestoes=%d aplicadas=%d erros=%d',
        dry_run, janela_dias, len(sugestoes), len(aplicadas), len(erros),
    )
    return {
        'dry_run': dry_run,
        'janela_dias': janela_dias,
        'sugestoes_geradas': len(sugestoes),
        'sugestoes': [s.to_dict() for s in sugestoes],
        'aplicadas_ids': aplicadas,
        'erros': erros,
    }


# =============================================================================
# LISTAR COMPENSACOES (com joins para UI)
# =============================================================================
def listar_compensacoes(
    status: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = 500,
) -> list[dict]:
    """Lista compensacoes com dados das transacoes associadas."""
    q = PessoalCompensacao.query
    if status:
        q = q.filter(PessoalCompensacao.status == status)
    if data_inicio:
        q = q.filter(PessoalCompensacao.criado_em >= data_inicio)
    if data_fim:
        q = q.filter(PessoalCompensacao.criado_em <= data_fim)

    comps = q.order_by(PessoalCompensacao.criado_em.desc()).limit(limit).all()

    # Pre-carregar transacoes em 1 query
    ids = {c.saida_id for c in comps} | {c.entrada_id for c in comps}
    tx_map = {
        t.id: t for t in PessoalTransacao.query.filter(PessoalTransacao.id.in_(ids)).all()
    } if ids else {}

    out = []
    for c in comps:
        s = tx_map.get(c.saida_id)
        e = tx_map.get(c.entrada_id)
        d = c.to_dict()
        d['saida'] = {
            'id': c.saida_id,
            'data': s.data.isoformat() if s and s.data else None,
            'historico': s.historico if s else None,
            'valor': float(s.valor) if s else None,
            'valor_efetivo': s.valor_efetivo if s else None,
        } if s else None
        d['entrada'] = {
            'id': c.entrada_id,
            'data': e.data.isoformat() if e and e.data else None,
            'historico': e.historico if e else None,
            'valor': float(e.valor) if e else None,
            'valor_efetivo': e.valor_efetivo if e else None,
        } if e else None
        out.append(d)
    return out
