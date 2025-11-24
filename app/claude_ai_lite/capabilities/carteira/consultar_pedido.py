"""
Capacidade: Consultar Pedido

Consultas por pedido, cliente, CNPJ ou pedido do cliente.
"""

from typing import Dict, Any, List
from sqlalchemy import or_
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class ConsultarPedidoCapability(BaseCapability):
    """Consulta pedidos na carteira."""

    NOME = "consultar_pedido"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["consultar_status", "buscar_pedido"]
    CAMPOS_BUSCA = ["num_pedido", "cnpj_cpf", "raz_social_red", "pedido_cliente"]
    DESCRICAO = "Consulta status e detalhes de pedidos"
    EXEMPLOS = [
        "Pedido VCD123 tem separação?",
        "Status do pedido VCD456",
        "Pedidos do cliente Atacadão",
        "Pedido do CNPJ 12345678000199"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for intenção de consulta ou tiver num_pedido."""
        if intencao in self.INTENCOES:
            return True
        # Também processa se tiver num_pedido e não for análise
        if entidades.get("num_pedido") and intencao not in ("analisar_disponibilidade", "analisar_gargalo"):
            return True
        return False

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Busca pedidos e suas separações."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao

        campo, valor = self.extrair_valor_busca(entidades)

        resultado = {
            "sucesso": True,
            "valor_buscado": valor,
            "campo_busca": campo,
            "total_encontrado": 0,
            "dados": []
        }

        if not campo or not valor:
            resultado["sucesso"] = False
            resultado["erro"] = "Campo ou valor de busca não informado"
            return resultado

        try:
            # Filtro base: apenas itens ativos com saldo > 0
            query = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            )

            if campo == "raz_social_red":
                # Busca inteligente: divide em palavras e busca todas (AND)
                # Ex: "Assai 308" -> raz_social_red ILIKE '%Assai%' AND raz_social_red ILIKE '%308%'
                palavras = valor.split()
                for palavra in palavras:
                    if len(palavra) >= 2:  # Ignora palavras muito curtas
                        query = query.filter(CarteiraPrincipal.raz_social_red.ilike(f"%{palavra}%"))
            elif campo == "cnpj_cpf":
                valor_limpo = "".join(c for c in valor if c.isdigit())
                query = query.filter(or_(
                    CarteiraPrincipal.cnpj_cpf.like(f"%{valor}%"),
                    CarteiraPrincipal.cnpj_cpf.like(f"%{valor_limpo}%")
                ))
            elif campo == "pedido_cliente":
                query = query.filter(CarteiraPrincipal.pedido_cliente.ilike(f"%{valor}%"))
            elif campo == "num_pedido":
                query = query.filter(CarteiraPrincipal.num_pedido.like(f"%{valor}%"))

            # Aplica filtros aprendidos pelo IA Trainer
            query = self.aplicar_filtros_aprendidos(query, contexto, CarteiraPrincipal)

            itens = query.all()

            if not itens:
                resultado["mensagem"] = f"Nenhum pedido encontrado para {campo}={valor}"
                return resultado

            # Agrupa por pedido
            pedidos = {}
            for item in itens:
                key = item.num_pedido
                if key not in pedidos:
                    separacoes = Separacao.query.filter_by(num_pedido=item.num_pedido).all()

                    # NOTA: expedicao e agendamento estão em Separacao, não em CarteiraPrincipal
                    # Pegamos da primeira separação encontrada, se existir
                    primeira_sep = separacoes[0] if separacoes else None

                    pedidos[key] = {
                        "num_pedido": item.num_pedido,
                        "cliente": item.raz_social_red,
                        "cnpj": item.cnpj_cpf,
                        "pedido_cliente": item.pedido_cliente,
                        "data_pedido": item.data_pedido.strftime("%d/%m/%Y") if item.data_pedido else None,
                        "expedicao": primeira_sep.expedicao.strftime("%d/%m/%Y") if primeira_sep and primeira_sep.expedicao else None,
                        "agendamento": primeira_sep.agendamento.strftime("%d/%m/%Y") if primeira_sep and primeira_sep.agendamento else None,
                        "agendamento_confirmado": primeira_sep.agendamento_confirmado if primeira_sep else False,
                        "tem_separacao": len(separacoes) > 0,
                        "produtos": [],
                        "separacoes": [self._formatar_separacao(s) for s in separacoes]
                    }

                pedidos[key]["produtos"].append({
                    "cod_produto": item.cod_produto,
                    "nome_produto": item.nome_produto,
                    "qtd": float(item.qtd_saldo_produto_pedido or 0),
                    "valor": float(item.preco_produto_pedido or 0) * float(item.qtd_saldo_produto_pedido or 0)
                })

            resultado["dados"] = list(pedidos.values())
            resultado["total_encontrado"] = len(pedidos)

        except Exception as e:
            logger.error(f"Erro ao buscar pedidos: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _formatar_separacao(self, sep) -> Dict:
        """Formata dados de uma separação."""
        return {
            "lote_id": sep.separacao_lote_id,
            "status": sep.status_calculado,
            "expedicao": sep.expedicao.strftime("%d/%m/%Y") if sep.expedicao else None,
            "agendamento": sep.agendamento.strftime("%d/%m/%Y") if sep.agendamento else None,
            "numero_nf": sep.numero_nf,
            "cod_produto": sep.cod_produto,
            "nome_produto": sep.nome_produto,
            "qtd_saldo": float(sep.qtd_saldo or 0)
        }

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not resultado.get("sucesso"):
            return f"Erro: {resultado.get('erro')}"

        if resultado["total_encontrado"] == 0:
            return resultado.get("mensagem", "Nenhum pedido encontrado.")

        linhas = [f"Encontrados {resultado['total_encontrado']} pedido(s):\n"]

        for p in resultado["dados"]:
            linhas.append(f"--- Pedido: {p['num_pedido']} ---")
            linhas.append(f"  Cliente: {p['cliente']} | CNPJ: {p['cnpj']}")
            if p.get("pedido_cliente"):
                linhas.append(f"  Pedido Cliente: {p['pedido_cliente']}")
            linhas.append(f"  Expedicao: {p.get('expedicao') or 'Nao definida'}")
            if p.get("agendamento"):
                conf = " (CONFIRMADO)" if p.get("agendamento_confirmado") else ""
                linhas.append(f"  Agendamento: {p['agendamento']}{conf}")

            if p.get("produtos"):
                linhas.append(f"  Produtos ({len(p['produtos'])}):")
                for prod in p["produtos"]:
                    linhas.append(f"    - {prod['nome_produto']}: {prod['qtd']:.0f}un")

            if p.get("tem_separacao"):
                linhas.append(f"  Separacoes ({len(p['separacoes'])}):")
                for sep in p["separacoes"]:
                    linhas.append(f"    - {sep['nome_produto']}: {sep['qtd_saldo']:.0f}un | {sep['status']}")
            else:
                linhas.append("  TEM SEPARACAO: NAO")
            linhas.append("")

        return "\n".join(linhas)
