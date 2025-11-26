"""
Servico de Opcoes de Envio - Analisa e gera opcoes A/B/C para envio de pedido.

Opcoes:
A - Envio total (aguardar todos os itens)
B - Envio sem 1 item gargalo
C - Envio sem 2 itens gargalo
"""

from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ItemPedido:
    """Representa um item do pedido com analise de disponibilidade."""
    cod_produto: str
    nome_produto: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    estoque_atual: float
    data_disponivel: Optional[date]
    dias_para_disponivel: Optional[int]
    disponivel_hoje: bool
    pallets: float = 0.0  # Calculado via CadastroPalletizacao
    peso_total: float = 0.0  # Calculado via CadastroPalletizacao


@dataclass
class OpcaoEnvio:
    """Representa uma opcao de envio."""
    codigo: str  # A, B, C
    descricao: str
    data_envio: Optional[date]
    itens_incluidos: List[ItemPedido]
    itens_excluidos: List[ItemPedido]
    valor_total: float
    valor_original: float
    percentual_valor: float
    qtd_itens: int
    qtd_itens_total: int


class OpcoesEnvioService:
    """Analisa pedido e gera opcoes de envio baseadas em disponibilidade."""

    HORIZONTE_DIAS = 30

    @classmethod
    def analisar_pedido(cls, num_pedido: str) -> Dict[str, Any]:
        """
        Analisa pedido e retorna ate 3 opcoes de envio.

        Returns:
            Dict com sucesso, opcoes e dados do pedido
        """
        from app.carteira.models import CarteiraPrincipal
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        from app.producao.models import CadastroPalletizacao

        resultado = {
            "sucesso": True,
            "num_pedido": num_pedido,
            "opcoes": [],
            "cliente": None,
            "valor_total_pedido": 0,
            "itens_analisados": []
        }

        try:
            # Buscar itens do pedido na carteira
            itens_carteira = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido.like(f"%{num_pedido}%"),
                CarteiraPrincipal.ativo == True
            ).all()

            if not itens_carteira:
                resultado["sucesso"] = False
                resultado["erro"] = f"Pedido {num_pedido} nao encontrado na carteira"
                return resultado

            # Dados do cliente (primeiro item)
            primeiro = itens_carteira[0]
            resultado["cliente"] = {
                "cnpj": primeiro.cnpj_cpf,
                "razao_social": primeiro.raz_social_red,
                "cidade": primeiro.nome_cidade,
                "uf": primeiro.cod_uf
            }
            resultado["num_pedido"] = primeiro.num_pedido

            # Analisar cada item
            hoje = date.today()
            itens_analisados = []

            for item in itens_carteira:
                quantidade = float(item.qtd_saldo_produto_pedido or 0)
                if quantidade <= 0:
                    continue

                valor_unitario = float(item.preco_produto_pedido or 0)
                valor_total = quantidade * valor_unitario

                # Buscar projecao de estoque
                projecao = ServicoEstoqueSimples.calcular_projecao(
                    item.cod_produto, dias=cls.HORIZONTE_DIAS
                )
                estoque_atual = projecao.get("estoque_atual", 0)

                # Encontrar data de disponibilidade
                data_disponivel = cls._encontrar_data_disponivel(
                    projecao, quantidade, hoje
                )

                dias_para = (data_disponivel - hoje).days if data_disponivel else None

                # Buscar palletizacao do produto
                pallets = 0.0
                peso_total = 0.0
                try:
                    cadastro = CadastroPalletizacao.query.filter_by(
                        cod_produto=item.cod_produto,
                        ativo=True
                    ).first()
                    if cadastro:
                        pallets = cadastro.calcular_pallets(quantidade)
                        peso_total = cadastro.calcular_peso_total(quantidade)
                except Exception as e:
                    logger.warning(f"Erro ao buscar palletizacao de {item.cod_produto}: {e}")

                item_analisado = ItemPedido(
                    cod_produto=item.cod_produto,
                    nome_produto=item.nome_produto,
                    quantidade=quantidade,
                    valor_unitario=valor_unitario,
                    valor_total=valor_total,
                    estoque_atual=estoque_atual,
                    data_disponivel=data_disponivel,
                    dias_para_disponivel=dias_para,
                    disponivel_hoje=estoque_atual >= quantidade,
                    pallets=pallets,
                    peso_total=peso_total
                )
                itens_analisados.append(item_analisado)

            if not itens_analisados:
                resultado["sucesso"] = False
                resultado["erro"] = "Nenhum item com quantidade para analisar"
                return resultado

            resultado["itens_analisados"] = itens_analisados
            resultado["valor_total_pedido"] = sum(i.valor_total for i in itens_analisados)

            # Ordenar por dias para disponibilidade (gargalos primeiro)
            itens_ordenados = sorted(
                itens_analisados,
                key=lambda x: (x.dias_para_disponivel or 999, -x.valor_total),
                reverse=True
            )

            # Gerar opcoes
            opcoes = cls._gerar_opcoes(itens_ordenados, resultado["valor_total_pedido"])
            resultado["opcoes"] = opcoes

        except Exception as e:
            logger.error(f"Erro ao analisar opcoes de envio: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    @classmethod
    def _encontrar_data_disponivel(cls, projecao: Dict, qtd: float, hoje: date) -> Optional[date]:
        """Encontra primeira data com estoque suficiente."""
        lista_projecao = projecao.get("projecao", [])

        for dia_proj in lista_projecao:
            estoque_dia = dia_proj.get("saldo_final", 0)
            if estoque_dia >= qtd:
                data_str = dia_proj.get("data")
                if data_str:
                    return date.fromisoformat(data_str)

        return None

    @classmethod
    def _gerar_opcoes(cls, itens_ordenados: List[ItemPedido], valor_total: float) -> List[Dict]:
        """
        Gera ate 3 opcoes de envio.

        A - Envio total
        B - Sem 1 gargalo
        C - Sem 2 gargalos
        """
        opcoes = []
        hoje = date.today()

        # Opcao A: Envio total
        data_envio_total = cls._calcular_data_envio(itens_ordenados)
        opcao_a = {
            "codigo": "A",
            "titulo": "Envio Total",
            "descricao": f"Aguardar todos os {len(itens_ordenados)} itens",
            "data_envio": data_envio_total.strftime("%d/%m/%Y") if data_envio_total else None,
            "data_envio_iso": data_envio_total.isoformat() if data_envio_total else None,
            "dias_para_envio": (data_envio_total - hoje).days if data_envio_total else None,
            "itens": [cls._item_to_dict(i) for i in itens_ordenados],
            "itens_excluidos": [],
            "valor": valor_total,
            "valor_original": valor_total,
            "percentual": 100.0,
            "qtd_itens": len(itens_ordenados),
            "disponivel_hoje": all(i.disponivel_hoje for i in itens_ordenados)
        }
        opcoes.append(opcao_a)

        # Identificar gargalos (itens que atrasam mais)
        gargalos = [i for i in itens_ordenados if not i.disponivel_hoje]
        gargalos_ordenados = sorted(
            gargalos,
            key=lambda x: (x.dias_para_disponivel or 999),
            reverse=True
        )

        # Opcao B: Sem 1 gargalo (se houver gargalo)
        if len(gargalos_ordenados) >= 1:
            gargalo_1 = gargalos_ordenados[0]
            itens_b = [i for i in itens_ordenados if i.cod_produto != gargalo_1.cod_produto]

            if itens_b:
                data_envio_b = cls._calcular_data_envio(itens_b)
                valor_b = sum(i.valor_total for i in itens_b)

                opcao_b = {
                    "codigo": "B",
                    "titulo": "Envio Parcial (-1 item)",
                    "descricao": f"Sem {gargalo_1.nome_produto[:30]}",
                    "data_envio": data_envio_b.strftime("%d/%m/%Y") if data_envio_b else hoje.strftime("%d/%m/%Y"),
                    "data_envio_iso": data_envio_b.isoformat() if data_envio_b else hoje.isoformat(),
                    "dias_para_envio": (data_envio_b - hoje).days if data_envio_b else 0,
                    "itens": [cls._item_to_dict(i) for i in itens_b],
                    "itens_excluidos": [cls._item_to_dict(gargalo_1)],
                    "valor": valor_b,
                    "valor_original": valor_total,
                    "percentual": round((valor_b / valor_total) * 100, 1) if valor_total > 0 else 0,
                    "qtd_itens": len(itens_b),
                    "disponivel_hoje": all(i.disponivel_hoje for i in itens_b)
                }
                opcoes.append(opcao_b)

        # Opcao C: Sem 2 gargalos (se houver 2+ gargalos)
        if len(gargalos_ordenados) >= 2:
            gargalo_1 = gargalos_ordenados[0]
            gargalo_2 = gargalos_ordenados[1]
            excluidos = {gargalo_1.cod_produto, gargalo_2.cod_produto}
            itens_c = [i for i in itens_ordenados if i.cod_produto not in excluidos]

            if itens_c:
                data_envio_c = cls._calcular_data_envio(itens_c)
                valor_c = sum(i.valor_total for i in itens_c)

                opcao_c = {
                    "codigo": "C",
                    "titulo": "Envio Parcial (-2 itens)",
                    "descricao": f"Sem {gargalo_1.nome_produto[:20]} e {gargalo_2.nome_produto[:20]}",
                    "data_envio": data_envio_c.strftime("%d/%m/%Y") if data_envio_c else hoje.strftime("%d/%m/%Y"),
                    "data_envio_iso": data_envio_c.isoformat() if data_envio_c else hoje.isoformat(),
                    "dias_para_envio": (data_envio_c - hoje).days if data_envio_c else 0,
                    "itens": [cls._item_to_dict(i) for i in itens_c],
                    "itens_excluidos": [cls._item_to_dict(gargalo_1), cls._item_to_dict(gargalo_2)],
                    "valor": valor_c,
                    "valor_original": valor_total,
                    "percentual": round((valor_c / valor_total) * 100, 1) if valor_total > 0 else 0,
                    "qtd_itens": len(itens_c),
                    "disponivel_hoje": all(i.disponivel_hoje for i in itens_c)
                }
                opcoes.append(opcao_c)

        return opcoes

    @classmethod
    def _calcular_data_envio(cls, itens: List[ItemPedido]) -> Optional[date]:
        """Calcula data de envio (data do item que demora mais)."""
        datas = [i.data_disponivel for i in itens if i.data_disponivel]
        if not datas:
            # Se todos disponiveis hoje
            if all(i.disponivel_hoje for i in itens):
                return date.today()
            return None
        return max(datas)

    @classmethod
    def _item_to_dict(cls, item: ItemPedido) -> Dict:
        """Converte ItemPedido para dict."""
        return {
            "cod_produto": item.cod_produto,
            "nome_produto": item.nome_produto,
            "quantidade": item.quantidade,
            "valor_unitario": item.valor_unitario,
            "valor_total": item.valor_total,
            "estoque_atual": item.estoque_atual,
            "data_disponivel": item.data_disponivel.strftime("%d/%m/%Y") if item.data_disponivel else None,
            "dias_para_disponivel": item.dias_para_disponivel,
            "disponivel_hoje": item.disponivel_hoje
        }
