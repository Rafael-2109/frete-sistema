"""
Loader de Produtos - Consultas por nome/codigo de produto.
Max 150 linhas.
"""

from typing import Dict, Any
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class ProdutosLoader(BaseLoader):
    """Consultas por produto na carteira."""

    DOMINIO = "carteira"

    CAMPOS_BUSCA = [
        "nome_produto",
        "cod_produto",
    ]

    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        """Busca produtos na carteira e separacao."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao

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
            # Busca na carteira (nao separados)
            if campo == "nome_produto":
                q_cart = CarteiraPrincipal.query.filter(CarteiraPrincipal.nome_produto.ilike(f"%{valor}%"))
                q_sep = Separacao.query.filter(Separacao.nome_produto.ilike(f"%{valor}%"), Separacao.sincronizado_nf == False)
            else:
                q_cart = CarteiraPrincipal.query.filter(CarteiraPrincipal.cod_produto.ilike(f"%{valor}%"))
                q_sep = Separacao.query.filter(Separacao.cod_produto.ilike(f"%{valor}%"), Separacao.sincronizado_nf == False)

            itens_cart = q_cart.all()
            itens_sep = q_sep.all()

            # Agrupa por produto
            produtos = {}

            for item in itens_cart:
                key = item.cod_produto
                if key not in produtos:
                    produtos[key] = self._criar_produto(item.cod_produto, item.nome_produto)
                produtos[key]["qtd_carteira"] += float(item.qtd_saldo_produto_pedido or 0)
                produtos[key]["valor_carteira"] += float(item.preco_produto_pedido or 0) * float(item.qtd_saldo_produto_pedido or 0)
                produtos[key]["pedidos_carteira"].append({
                    "num_pedido": item.num_pedido,
                    "cliente": item.raz_social_red,
                    "qtd": float(item.qtd_saldo_produto_pedido or 0),
                    "expedicao": item.expedicao.strftime("%d/%m/%Y") if item.expedicao else None,
                    "agendamento": item.agendamento.strftime("%d/%m/%Y") if item.agendamento else None,
                })

            for sep in itens_sep:
                key = sep.cod_produto
                if key not in produtos:
                    produtos[key] = self._criar_produto(sep.cod_produto, sep.nome_produto)
                produtos[key]["qtd_separada"] += float(sep.qtd_saldo or 0)
                if sep.expedicao:
                    produtos[key]["qtd_programada"] += float(sep.qtd_saldo or 0)
                produtos[key]["pedidos_separados"].append({
                    "num_pedido": sep.num_pedido,
                    "cliente": sep.raz_social_red,
                    "qtd": float(sep.qtd_saldo or 0),
                    "status": sep.status_calculado,
                    "expedicao": sep.expedicao.strftime("%d/%m/%Y") if sep.expedicao else None,
                })

            resultado["dados"] = list(produtos.values())
            resultado["total_encontrado"] = len(produtos)
            resultado["resumo"] = {
                "total_carteira": sum(p["qtd_carteira"] for p in produtos.values()),
                "total_separada": sum(p["qtd_separada"] for p in produtos.values()),
                "total_programada": sum(p["qtd_programada"] for p in produtos.values()),
                "total_valor": sum(p["valor_carteira"] for p in produtos.values()),
            }

        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _criar_produto(self, cod: str, nome: str) -> Dict:
        return {
            "cod_produto": cod, "nome_produto": nome,
            "qtd_carteira": 0, "valor_carteira": 0,
            "qtd_separada": 0, "qtd_programada": 0,
            "pedidos_carteira": [], "pedidos_separados": []
        }

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Nenhum produto encontrado.")

        r = dados["resumo"]
        linhas = [
            f"Encontrados {dados['total_encontrado']} produto(s):\n",
            "=== RESUMO ===",
            f"  Na Carteira: {r['total_carteira']:.0f}un",
            f"  Separada: {r['total_separada']:.0f}un",
            f"  Programada: {r['total_programada']:.0f}un",
            f"  Valor: R$ {r['total_valor']:,.2f}\n"
        ]

        for p in dados["dados"]:
            linhas.append(f"--- {p['nome_produto']} ({p['cod_produto']}) ---")
            linhas.append(f"  Carteira: {p['qtd_carteira']:.0f}un | Separada: {p['qtd_separada']:.0f}un | Programada: {p['qtd_programada']:.0f}un")
            if p["pedidos_carteira"]:
                linhas.append(f"  Pedidos Carteira ({len(p['pedidos_carteira'])}):")
                for ped in p["pedidos_carteira"][:3]:
                    exp = f"Exp:{ped['expedicao']}" if ped['expedicao'] else "Sem exp"
                    linhas.append(f"    - {ped['num_pedido']} | {ped['cliente'][:15]} | {ped['qtd']:.0f}un | {exp}")
            if p["pedidos_separados"]:
                linhas.append(f"  Pedidos Separados ({len(p['pedidos_separados'])}):")
                for ped in p["pedidos_separados"][:3]:
                    linhas.append(f"    - {ped['num_pedido']} | {ped['status']} | {ped['qtd']:.0f}un")
            linhas.append("")

        return "\n".join(linhas)
