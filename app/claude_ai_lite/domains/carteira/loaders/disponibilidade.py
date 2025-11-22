"""
Loader de Disponibilidade - Analise de quando embarcar pedido.
Usa ServicoEstoqueSimples para projecao.
Max 150 linhas.
"""

from typing import Dict, Any, List
from datetime import date, timedelta
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class DisponibilidadeLoader(BaseLoader):
    """Analisa disponibilidade de estoque para embarque."""

    DOMINIO = "carteira"

    CAMPOS_BUSCA = [
        "num_pedido",  # Quando posso embarcar pedido X?
    ]

    HORIZONTE_DIAS = 30  # Analisa 30 dias
    DIAS_PROTECAO = 7    # Nao roubar de pedidos em 7 dias

    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        """Analisa quando pedido pode embarcar baseado no estoque projetado."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        resultado = {
            "sucesso": True,
            "valor_buscado": valor,
            "campo_busca": campo,
            "total_encontrado": 0,
            "dados": [],
            "analise": {}
        }

        if campo != "num_pedido":
            resultado["sucesso"] = False
            resultado["erro"] = "Analise de disponibilidade apenas por num_pedido"
            return resultado

        try:
            # Busca itens do pedido na CarteiraPrincipal (NAO separados)
            itens_cart = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido.like(f"%{valor}%")
            ).all()

            # Busca separacoes existentes (para informar status)
            itens_sep = Separacao.query.filter(
                Separacao.num_pedido.like(f"%{valor}%"),
                Separacao.sincronizado_nf == False
            ).all()

            if not itens_cart and not itens_sep:
                resultado["mensagem"] = f"Pedido {valor} nao encontrado"
                return resultado

            # Se pedido JA esta separado, informar a data existente
            if not itens_cart and itens_sep:
                return self._responder_pedido_ja_separado(valor, itens_sep, resultado)

            # Agrupa produtos da CARTEIRA (itens que precisam de estoque)
            produtos_pedido = {}
            for item in itens_cart:
                key = item.cod_produto
                if key not in produtos_pedido:
                    produtos_pedido[key] = {
                        "cod": key,
                        "nome": item.nome_produto,
                        "qtd_necessaria": 0
                    }
                produtos_pedido[key]["qtd_necessaria"] += float(item.qtd_saldo_produto_pedido or 0)

            # Analisa disponibilidade de cada produto
            hoje = date.today()
            analises = []

            for prod in produtos_pedido.values():
                if prod["qtd_necessaria"] <= 0:
                    continue

                projecao = ServicoEstoqueSimples.calcular_projecao(prod["cod"], dias=self.HORIZONTE_DIAS)
                data_possivel = self._encontrar_data_disponivel(
                    projecao, prod["qtd_necessaria"], hoje
                )

                analises.append({
                    "cod_produto": prod["cod"],
                    "nome_produto": prod["nome"],
                    "qtd_necessaria": prod["qtd_necessaria"],
                    "estoque_atual": projecao.get("estoque_atual", 0),
                    "data_possivel": data_possivel.strftime("%d/%m/%Y") if data_possivel else None,
                    "dias_para_embarque": (data_possivel - hoje).days if data_possivel else None,
                    "disponivel_hoje": projecao.get("estoque_atual", 0) >= prod["qtd_necessaria"]
                })

            # Determina data mais restritiva (produto que demora mais)
            datas_possiveis = [a["data_possivel"] for a in analises if a["data_possivel"]]
            if datas_possiveis:
                data_embarque = max(datas_possiveis)  # Data mais distante
            else:
                data_embarque = None

            resultado["dados"] = analises
            resultado["total_encontrado"] = len(analises)
            resultado["analise"] = {
                "num_pedido": valor,
                "total_produtos": len(analises),
                "data_embarque_sugerida": data_embarque,
                "todos_disponiveis_hoje": all(a["disponivel_hoje"] for a in analises),
            }

        except Exception as e:
            logger.error(f"Erro na analise de disponibilidade: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _encontrar_data_disponivel(self, projecao: Dict, qtd_necessaria: float, hoje: date) -> date:
        """Encontra primeira data com estoque disponivel."""
        lista_projecao = projecao.get("projecao", [])

        for dia_proj in lista_projecao:
            estoque_dia = dia_proj.get("saldo_final", 0)
            if estoque_dia >= qtd_necessaria:
                data_str = dia_proj.get("data")
                if data_str:
                    return date.fromisoformat(data_str)

        return None  # Nao encontrou no horizonte

    def _responder_pedido_ja_separado(self, num_pedido: str, separacoes: List, resultado: Dict) -> Dict:
        """Responde quando pedido ja esta totalmente separado."""
        # Agrupa por lote e pega datas
        lotes = {}
        for sep in separacoes:
            lote = sep.separacao_lote_id or "sem_lote"
            if lote not in lotes:
                lotes[lote] = {
                    "expedicao": sep.expedicao,
                    "agendamento": sep.agendamento,
                    "status": sep.status_calculado,
                    "produtos": []
                }
            lotes[lote]["produtos"].append({
                "cod": sep.cod_produto,
                "nome": sep.nome_produto,
                "qtd": float(sep.qtd_saldo or 0)
            })

        resultado["ja_separado"] = True
        resultado["total_encontrado"] = len(lotes)
        resultado["dados"] = list(lotes.values())
        resultado["analise"] = {
            "num_pedido": num_pedido,
            "status": "JA_SEPARADO",
            "total_lotes": len(lotes)
        }
        return resultado

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Pedido nao encontrado.")

        a = dados["analise"]

        # Caso especial: pedido ja separado
        if dados.get("ja_separado"):
            linhas = [
                f"=== PEDIDO {a['num_pedido']} - JA SEPARADO ===\n",
                f"O pedido ja foi separado e possui {a['total_lotes']} lote(s).\n"
            ]
            for lote in dados["dados"]:
                exp = lote["expedicao"].strftime("%d/%m/%Y") if lote["expedicao"] else "Nao definida"
                agend = lote["agendamento"].strftime("%d/%m/%Y") if lote["agendamento"] else "Nao definido"
                linhas.append(f"  Status: {lote['status']}")
                linhas.append(f"  Expedicao: {exp}")
                linhas.append(f"  Agendamento: {agend}")
                linhas.append(f"  Produtos: {len(lote['produtos'])}")
                for p in lote["produtos"][:3]:
                    linhas.append(f"    - {p['nome']}: {p['qtd']:.0f}un")
            return "\n".join(linhas)

        # Caso normal: analise de disponibilidade
        linhas = [
            f"=== ANALISE DE DISPONIBILIDADE - Pedido {a['num_pedido']} ===\n",
            f"Total de produtos: {a['total_produtos']}",
            f"Todos disponiveis hoje: {'SIM' if a['todos_disponiveis_hoje'] else 'NAO'}",
            f"Data sugerida embarque: {a['data_embarque_sugerida'] or 'Sem previsao em 30 dias'}\n",
            "--- Detalhes por Produto ---"
        ]

        for p in dados["dados"]:
            status = "DISPONIVEL" if p["disponivel_hoje"] else f"Aguardar {p['dias_para_embarque']} dias" if p["dias_para_embarque"] else "SEM PREVISAO"
            linhas.append(f"  {p['nome_produto']}")
            linhas.append(f"    Necessario: {p['qtd_necessaria']:.0f} | Estoque: {p['estoque_atual']:.0f} | {status}")

        return "\n".join(linhas)
