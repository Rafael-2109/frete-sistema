"""
Loader de Disponibilidade - Analise de quando embarcar pedido.
Usa OpcoesEnvioService para gerar opcoes A/B/C.
"""

from typing import Dict, Any, List
from datetime import date
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class DisponibilidadeLoader(BaseLoader):
    """Analisa disponibilidade e gera opcoes de envio."""

    DOMINIO = "carteira"

    CAMPOS_BUSCA = [
        "num_pedido",
    ]

    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        """Analisa pedido e retorna opcoes de envio A/B/C."""
        from app.separacao.models import Separacao
        from ..services.opcoes_envio import OpcoesEnvioService

        resultado = {
            "sucesso": True,
            "valor_buscado": valor,
            "campo_busca": campo,
            "total_encontrado": 0,
            "dados": [],
            "analise": {},
            "opcoes": []
        }

        if campo != "num_pedido":
            resultado["sucesso"] = False
            resultado["erro"] = "Analise de disponibilidade apenas por num_pedido"
            return resultado

        try:
            # Verifica se ja esta separado
            itens_sep = Separacao.query.filter(
                Separacao.num_pedido.like(f"%{valor}%"),
                Separacao.sincronizado_nf == False
            ).all()

            # Usa o servico de opcoes
            analise = OpcoesEnvioService.analisar_pedido(valor)

            if not analise["sucesso"]:
                # Se nao encontrou na carteira, verifica se esta separado
                if itens_sep:
                    return self._responder_pedido_ja_separado(valor, itens_sep, resultado)
                resultado["sucesso"] = False
                resultado["erro"] = analise.get("erro", "Pedido nao encontrado")
                return resultado

            # Preenche resultado
            resultado["num_pedido"] = analise["num_pedido"]
            resultado["cliente"] = analise["cliente"]
            resultado["valor_total_pedido"] = analise["valor_total_pedido"]
            resultado["opcoes"] = analise["opcoes"]
            resultado["total_encontrado"] = len(analise["opcoes"])

            # Analise resumida
            resultado["analise"] = {
                "num_pedido": analise["num_pedido"],
                "cliente": analise["cliente"]["razao_social"] if analise["cliente"] else None,
                "valor_total": analise["valor_total_pedido"],
                "qtd_opcoes": len(analise["opcoes"]),
                "todos_disponiveis_hoje": analise["opcoes"][0]["disponivel_hoje"] if analise["opcoes"] else False
            }

        except Exception as e:
            logger.error(f"Erro na analise de disponibilidade: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _responder_pedido_ja_separado(self, num_pedido: str, separacoes: List, resultado: Dict) -> Dict:
        """Responde quando pedido ja esta separado."""
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
        """Formata dados para contexto do Claude com opcoes."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Pedido nao encontrado.")

        # Caso especial: pedido ja separado
        if dados.get("ja_separado"):
            return self._formatar_ja_separado(dados)

        # Caso normal: opcoes de envio
        return self._formatar_opcoes(dados)

    def _formatar_ja_separado(self, dados: Dict) -> str:
        """Formata resposta para pedido ja separado."""
        a = dados["analise"]
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
            for p in lote["produtos"][:3]:
                linhas.append(f"    - {p['nome']}: {p['qtd']:.0f}un")
        return "\n".join(linhas)

    def _formatar_opcoes(self, dados: Dict) -> str:
        """Formata opcoes de envio A/B/C."""
        a = dados["analise"]
        opcoes = dados.get("opcoes", [])

        linhas = [
            f"=== ANALISE DE DISPONIBILIDADE - Pedido {a['num_pedido']} ===",
            f"Cliente: {a.get('cliente', 'N/A')}",
            f"Valor Total do Pedido: R$ {a.get('valor_total', 0):,.2f}",
            "",
            "=== OPCOES DE ENVIO ===",
            ""
        ]

        for opcao in opcoes:
            codigo = opcao["codigo"]
            linhas.append(f"--- OPCAO {codigo}: {opcao['titulo']} ---")
            linhas.append(f"  Data de Envio: {opcao['data_envio'] or 'Sem previsao'}")

            if opcao.get("dias_para_envio") is not None:
                if opcao["dias_para_envio"] == 0:
                    linhas.append(f"  Disponivel: HOJE")
                else:
                    linhas.append(f"  Aguardar: {opcao['dias_para_envio']} dia(s)")

            linhas.append(f"  Valor: R$ {opcao['valor']:,.2f} ({opcao['percentual']:.1f}% do pedido)")
            linhas.append(f"  Itens: {opcao['qtd_itens']}")

            # Lista itens incluidos (resumido)
            if opcao.get("itens"):
                for item in opcao["itens"][:3]:
                    if item["disponivel_hoje"]:
                        status_item = "OK"
                    elif item.get("dias_para_disponivel"):
                        status_item = f"Aguardar {item['dias_para_disponivel']}d"
                    else:
                        status_item = "Sem previsao"
                    linhas.append(f"    - {item['nome_produto'][:35]}: {item['quantidade']:.0f}un [{status_item}]")
                if len(opcao["itens"]) > 3:
                    linhas.append(f"    ... e mais {len(opcao['itens']) - 3} itens")

            # Lista itens excluidos
            if opcao.get("itens_excluidos"):
                linhas.append(f"  ITENS NAO INCLUIDOS:")
                for item in opcao["itens_excluidos"]:
                    linhas.append(f"    X {item['nome_produto'][:35]}: {item['quantidade']:.0f}un (R$ {item['valor_total']:,.2f})")

            linhas.append("")

        # Gera texto dinâmico baseado nas opções disponíveis
        if opcoes:
            letras = [op.get('codigo', chr(65 + i)) for i, op in enumerate(opcoes)]
            opcoes_str = ", ".join(letras[:-1]) + f" ou {letras[-1]}" if len(letras) > 1 else letras[0]
            linhas.append(f"Para criar separacao, responda com a opcao desejada ({opcoes_str}).")

        return "\n".join(linhas)
