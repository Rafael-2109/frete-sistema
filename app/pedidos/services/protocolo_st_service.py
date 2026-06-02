"""
ProtocoloStService — split de NF por protocolo ST (Atacadão RJ).

Quando a UF de uma filial exige separação (`RegiaoTabelaRede.separar_protocolo_st`)
e o pedido tem produtos sujeitos a ST (`ProdutoDeParaAtacadao.protocolo_st`) E demais,
o pedido é quebrado em 2 sale.orders no Odoo.

Responsabilidades (separa I/O de lógica pura):
- `enriquecer_itens_raw`     — I/O: marca cada item raw com `protocolo_st` (De-Para).
- `enriquecer_separar_flag`  — I/O: marca cada filial com `separar_protocolo_st` (RegiaoTabelaRede).
- `gerar_grupos_lancamento`  — PURA: dado uma filial já enriquecida, retorna 1 ou 2 grupos
                                de lançamento (itens_odoo + divergências por grupo).

Os flags são resolvidos no UPLOAD e persistidos em `dados_filiais`; o LANÇAMENTO
(síncrono e assíncrono) consome `gerar_grupos_lancamento` sobre os dados já enriquecidos.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ===================== Utilitários =====================

_TRUTHY_PLANILHA = {'1', '1.0', 'true', 'sim', 's', 'x', 'yes', 'y', 'verdadeiro'}


def parse_bool_planilha(valor: Any) -> bool:
    """Interpreta uma célula de planilha (Excel/CSV) como booleano.

    True para 'Sim', '1', 'True', 'X', 'S', 'Yes', etc. (case-insensitive);
    False para vazio/NaN/'Não'/0.
    """
    if valor is None:
        return False
    return str(valor).strip().lower() in _TRUTHY_PLANILHA


# ===================== Lógica pura (sem DB) =====================

def _build_itens_odoo(itens: List[Dict[str, Any]], uf: str, nome_cliente: str) -> List[Dict[str, Any]]:
    """Monta a lista de itens no formato esperado por `OdooIntegrationService.criar_pedido`.

    Itens sem `nosso_codigo` (sem De-Para) são ignorados — o lançamento já é bloqueado
    a montante quando há itens sem De-Para.
    """
    out: List[Dict[str, Any]] = []
    for item in itens:
        nosso_codigo = item.get('nosso_codigo')
        if not nosso_codigo:
            continue
        out.append({
            'nosso_codigo': nosso_codigo,
            'quantidade': item.get('quantidade', 0),
            'preco': item.get('preco_final', item.get('preco_documento', 0)),
            'uf': uf,
            'nome_cliente': nome_cliente,
        })
    return out


def _build_divergencias(itens: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Lista de divergências de preço dos itens do grupo (ou None se nenhuma)."""
    divs = [
        {
            'codigo': item.get('nosso_codigo'),
            'preco_doc': item.get('preco_documento'),
            'preco_tabela': item.get('preco_tabela'),
            'preco_final': item.get('preco_final'),
            'diferenca': item.get('diferenca_percentual'),
        }
        for item in itens if item.get('divergente')
    ]
    return divs or None


def gerar_grupos_lancamento(filial: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Retorna os grupos de lançamento (1 ou 2) de uma filial já enriquecida.

    Split em 2 grupos (ST primeiro, depois Demais) ocorre apenas quando:
      filial['separar_protocolo_st'] == True  E  há itens ST e itens não-ST.
    Caso contrário, 1 único grupo (rotulo_st=None) com todos os itens.

    Cada grupo:
        {'rotulo_st': 'ST'|'NORMAL'|None,
         'itens_odoo': [...],
         'tem_divergencia': bool,
         'divergencias': [...] | None}

    Função PURA — depende apenas dos flags já presentes em `filial` e seus itens
    (`filial['separar_protocolo_st']`, `item['protocolo_st']`).
    """
    itens = filial.get('itens', []) or []
    uf = filial.get('uf', '') or ''
    nome_cliente = filial.get('nome_cliente', '') or ''
    separar = bool(filial.get('separar_protocolo_st', False))

    com_st = [i for i in itens if i.get('protocolo_st')]
    sem_st = [i for i in itens if not i.get('protocolo_st')]

    if separar and com_st and sem_st:
        particoes = [('ST', com_st), ('NORMAL', sem_st)]
    else:
        particoes = [(None, itens)]

    grupos: List[Dict[str, Any]] = []
    for rotulo, subset in particoes:
        itens_odoo = _build_itens_odoo(subset, uf, nome_cliente)
        if not itens_odoo:
            continue
        grupos.append({
            'rotulo_st': rotulo,
            'itens_odoo': itens_odoo,
            'tem_divergencia': any(i.get('divergente') for i in subset),
            'divergencias': _build_divergencias(subset),
        })
    return grupos


# ===================== Enriquecimento (I/O — DB) =====================

def enriquecer_itens_raw(itens: List[Dict[str, Any]], rede: str) -> None:
    """Marca cada item raw com `protocolo_st` (default False), mutação in-place.

    Apenas ATACADAO possui De-Para com `protocolo_st`. O status é resolvido por
    `codigo_nosso` agregando `any(protocolo_st)` entre as linhas do De-Para daquele
    código — interpretação "atributo fixo do produto" (decisão do usuário), evitando
    fragilidade de match por CNPJ. 1 query batch.
    """
    for it in itens:
        it.setdefault('protocolo_st', False)

    if (rede or '').upper() != 'ATACADAO':
        return

    nossos = {it.get('nosso_codigo') for it in itens if it.get('nosso_codigo')}
    if not nossos:
        return

    from app.portal.atacadao.models import ProdutoDeParaAtacadao

    rows = ProdutoDeParaAtacadao.query.filter(
        ProdutoDeParaAtacadao.ativo.is_(True),
        ProdutoDeParaAtacadao.codigo_nosso.in_(nossos),
    ).all()

    idx: Dict[str, bool] = {}
    for d in rows:
        idx[d.codigo_nosso] = idx.get(d.codigo_nosso, False) or bool(d.protocolo_st)

    for it in itens:
        nc = it.get('nosso_codigo')
        if nc:
            it['protocolo_st'] = idx.get(nc, False)


def enriquecer_separar_flag(dados_filiais: List[Dict[str, Any]], rede: str) -> None:
    """Marca cada filial com `separar_protocolo_st` (default False), mutação in-place.

    Resolve por (rede, uf) via `RegiaoTabelaRede`. 1 query batch.
    """
    for f in dados_filiais:
        f.setdefault('separar_protocolo_st', False)

    if not dados_filiais:
        return

    ufs = {(f.get('uf') or '').upper() for f in dados_filiais if f.get('uf')}
    if not ufs:
        return

    from app.pedidos.validacao.models import RegiaoTabelaRede

    rows = RegiaoTabelaRede.query.filter(
        RegiaoTabelaRede.rede == (rede or '').upper(),
        RegiaoTabelaRede.ativo.is_(True),
        RegiaoTabelaRede.uf.in_(ufs),
    ).all()

    idx: Dict[str, bool] = {r.uf.upper(): bool(r.separar_protocolo_st) for r in rows}

    for f in dados_filiais:
        uf = (f.get('uf') or '').upper()
        f['separar_protocolo_st'] = idx.get(uf, False)
