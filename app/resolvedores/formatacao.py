"""Formatadores de mensagem de sugestao (puros, sem banco).

Port de resolver_entidades.py: formatar_sugestao_pedido (:1356), formatar_sugestao_produto (:1389).
CORRECAO (Rafael 2026-06-01): a branch 'multiplos_encontrados' do monolito quebrava com
TypeError (', '.join sobre pedidos_candidatos, que sao dicts). Aqui juntamos os num_pedido.
"""
from app.resolvedores.grupo import listar_grupos_disponiveis


def _num_pedido_candidato(c) -> str:
    """Extrai num_pedido de um candidato (dict {num_pedido, cliente}) ou aceita string crua."""
    if isinstance(c, dict):
        return str(c.get('num_pedido', ''))
    return str(c)


def formatar_sugestao_pedido(info: dict) -> str:
    """Formata mensagem de sugestao baseada no resultado de resolver_pedido."""
    if info['estrategia'] == 'NAO_ENCONTRADO':
        grupos = ', '.join(listar_grupos_disponiveis())
        return (
            f"Pedido '{info['termo_original']}' nao encontrado. "
            f"Tente:\n"
            f"- Numero do pedido (ex: VCD123)\n"
            f"- Parte do numero (ex: 123)\n"
            f"- Grupo + loja (ex: {grupos.split(',')[0]} 183)\n"
            f"- Nome do cliente (ex: Barueri)\n"
            f"Grupos disponiveis: {grupos}"
        )

    if info.get('multiplos_encontrados'):
        candidatos = info.get('pedidos_candidatos', [])
        primeiro = _num_pedido_candidato(candidatos[0]) if candidatos else 'N/A'
        outros = ', '.join(_num_pedido_candidato(c) for c in candidatos[1:10])
        return (
            f"Multiplos pedidos encontrados para '{info['termo_original']}'. "
            f"Usando o primeiro: {primeiro}. "
            f"Outros candidatos: {outros}"
        )

    return None  # type: ignore


def formatar_sugestao_produto(info: dict) -> str:
    """Formata mensagem de sugestao baseada no resultado de resolver_produto_unico."""
    if not info['encontrado'] and not info['multiplos']:
        return (
            f"Produto '{info['termo_original']}' nao encontrado. "
            f"Tente usar:\n"
            f"- Codigo do produto (ex: AZ001)\n"
            f"- Nome parcial (ex: azeitona preta)\n"
            f"- Tipo + embalagem (ex: balde industrial)\n"
            f"- Combinacao (ex: mezzani fatiada)"
        )

    if info['multiplos'] and not info['encontrado']:
        candidatos = info.get('candidatos', [])
        lista = '\n'.join([
            f"  - {c['cod_produto']}: {c['nome_produto']}"
            for c in candidatos
        ])
        return (
            f"Multiplos produtos encontrados para '{info['termo_original']}':\n{lista}\n"
            f"Especifique melhor o termo."
        )

    return None  # type: ignore
