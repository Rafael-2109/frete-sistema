"""
Loader de Saldo de Pedido - Compara quantidades original vs separado vs restante.
Max 200 linhas.
"""

from typing import Dict, Any, List
from decimal import Decimal
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class SaldoPedidoLoader(BaseLoader):
    """Analisa saldo de pedido: original, separado, restante."""

    DOMINIO = "carteira"

    CAMPOS_BUSCA = [
        "num_pedido",
        "cnpj_cpf",
        "raz_social_red",
    ]

    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        """Busca saldo de pedido comparando carteira vs separacao."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from sqlalchemy import or_

        resultado = {
            "sucesso": True,
            "valor_buscado": valor,
            "campo_busca": campo,
            "total_encontrado": 0,
            "dados": [],
            "resumo": {}
        }

        if not self.validar_campo(campo):
            resultado["sucesso"] = False
            resultado["erro"] = f"Campo invalido: {campo}"
            return resultado

        try:
            # Busca na carteira
            q_cart = CarteiraPrincipal.query
            if campo == "num_pedido":
                q_cart = q_cart.filter(CarteiraPrincipal.num_pedido.like(f"%{valor}%"))
            elif campo == "cnpj_cpf":
                valor_limpo = "".join(c for c in valor if c.isdigit())
                q_cart = q_cart.filter(or_(
                    CarteiraPrincipal.cnpj_cpf.like(f"%{valor}%"),
                    CarteiraPrincipal.cnpj_cpf.like(f"%{valor_limpo}%")
                ))
            elif campo == "raz_social_red":
                q_cart = q_cart.filter(CarteiraPrincipal.raz_social_red.ilike(f"%{valor}%"))

            itens_carteira = q_cart.all()

            if not itens_carteira:
                resultado["mensagem"] = f"Pedido '{valor}' nao encontrado na carteira."
                return resultado

            # Agrupa por pedido
            pedidos = {}
            for item in itens_carteira:
                key = item.num_pedido
                if key not in pedidos:
                    pedidos[key] = {
                        "num_pedido": item.num_pedido,
                        "cliente": item.raz_social_red,
                        "cnpj": item.cnpj_cpf,
                        "pedido_cliente": item.pedido_cliente,
                        "expedicao": item.expedicao.strftime("%d/%m/%Y") if item.expedicao else None,
                        "itens": {}
                    }

                cod = item.cod_produto
                if cod not in pedidos[key]["itens"]:
                    pedidos[key]["itens"][cod] = {
                        "cod_produto": cod,
                        "nome_produto": item.nome_produto,
                        "qtd_original": 0,
                        "qtd_separada": 0,
                        "qtd_faturada": 0,
                        "qtd_restante": 0,
                        "valor_unitario": float(item.preco_produto_pedido or 0),
                        "status": "PENDENTE"
                    }

                # Quantidade na carteira = quantidade original do pedido
                pedidos[key]["itens"][cod]["qtd_original"] += float(item.qtd_saldo_produto_pedido or 0)

            # Busca separacoes para os pedidos encontrados
            nums_pedidos = list(pedidos.keys())
            separacoes = Separacao.query.filter(
                Separacao.num_pedido.in_(nums_pedidos)
            ).all()

            for sep in separacoes:
                ped = pedidos.get(sep.num_pedido)
                if not ped:
                    continue

                cod = sep.cod_produto
                if cod not in ped["itens"]:
                    # Item separado que nao esta na carteira (totalmente atendido anteriormente)
                    ped["itens"][cod] = {
                        "cod_produto": cod,
                        "nome_produto": sep.nome_produto,
                        "qtd_original": 0,
                        "qtd_separada": 0,
                        "qtd_faturada": 0,
                        "qtd_restante": 0,
                        "valor_unitario": 0,
                        "status": "PENDENTE"
                    }

                qtd = float(sep.qtd_saldo or 0)
                if sep.sincronizado_nf:
                    ped["itens"][cod]["qtd_faturada"] += qtd
                else:
                    ped["itens"][cod]["qtd_separada"] += qtd

            # Calcula restante e status de cada item
            for ped in pedidos.values():
                for item in ped["itens"].values():
                    # Restante = Original - Separada - Faturada
                    # Mas na carteira so mostra o saldo, entao:
                    item["qtd_restante"] = item["qtd_original"] - item["qtd_separada"]

                    # Calcula status
                    if item["qtd_faturada"] > 0:
                        if item["qtd_restante"] <= 0 and item["qtd_separada"] <= 0:
                            item["status"] = "FATURADO"
                        else:
                            item["status"] = "PARCIAL_FATURADO"
                    elif item["qtd_separada"] > 0:
                        if item["qtd_restante"] <= 0:
                            item["status"] = "TOTALMENTE_SEPARADO"
                        else:
                            item["status"] = "PARCIAL_SEPARADO"
                    else:
                        item["status"] = "PENDENTE"

            # Converte itens de dict para lista
            for ped in pedidos.values():
                ped["itens"] = list(ped["itens"].values())

            resultado["dados"] = list(pedidos.values())
            resultado["total_encontrado"] = len(pedidos)

            # Resumo geral
            total_original = sum(sum(i["qtd_original"] for i in p["itens"]) for p in pedidos.values())
            total_separado = sum(sum(i["qtd_separada"] for i in p["itens"]) for p in pedidos.values())
            total_faturado = sum(sum(i["qtd_faturada"] for i in p["itens"]) for p in pedidos.values())
            total_restante = sum(sum(i["qtd_restante"] for i in p["itens"]) for p in pedidos.values())

            resultado["resumo"] = {
                "total_pedidos": len(pedidos),
                "qtd_original": total_original,
                "qtd_separada": total_separado,
                "qtd_faturada": total_faturado,
                "qtd_restante": total_restante,
                "percentual_atendido": round((total_separado + total_faturado) / total_original * 100, 1) if total_original > 0 else 0
            }

        except Exception as e:
            logger.error(f"Erro ao buscar saldo: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Nenhum pedido encontrado.")

        r = dados["resumo"]
        linhas = [
            "=== ANALISE DE SALDO DE PEDIDO ===",
            "",
            "RESUMO GERAL:",
            f"  Quantidade Original: {r['qtd_original']:,.0f}un",
            f"  Quantidade Separada: {r['qtd_separada']:,.0f}un",
            f"  Quantidade Faturada: {r['qtd_faturada']:,.0f}un",
            f"  Quantidade Restante: {r['qtd_restante']:,.0f}un",
            f"  Atendimento: {r['percentual_atendido']:.1f}%",
            ""
        ]

        for ped in dados["dados"]:
            linhas.append(f"=== PEDIDO: {ped['num_pedido']} ===")
            linhas.append(f"  Cliente: {ped['cliente']}")
            if ped.get("pedido_cliente"):
                linhas.append(f"  Pedido Cliente: {ped['pedido_cliente']}")
            linhas.append(f"  Expedicao: {ped.get('expedicao') or 'Nao definida'}")
            linhas.append("")
            linhas.append("  ITENS:")
            linhas.append("  " + "-" * 70)
            linhas.append("  Produto                        | Original | Separado | Restante | Status")
            linhas.append("  " + "-" * 70)

            for item in ped["itens"]:
                nome = item["nome_produto"][:30] if item["nome_produto"] else item["cod_produto"]
                linhas.append(
                    f"  {nome:30} | {item['qtd_original']:>8.0f} | {item['qtd_separada']:>8.0f} | "
                    f"{item['qtd_restante']:>8.0f} | {item['status']}"
                )

            linhas.append("")

        return "\n".join(linhas)
