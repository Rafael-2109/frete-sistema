"""
Capacidade: Analisar Disponibilidade

Analisa quando um pedido pode ser enviado e gera opções A/B/C.
"""

from typing import Dict, Any, List
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class AnalisarDisponibilidadeCapability(BaseCapability):
    """Analisa disponibilidade e gera opções de envio."""

    NOME = "analisar_disponibilidade"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["analisar_disponibilidade"]
    CAMPOS_BUSCA = ["num_pedido"]
    DESCRICAO = "Analisa quando um pedido pode ser enviado baseado no estoque"
    EXEMPLOS = [
        "Quando posso enviar o pedido VCD123?",
        "Quando embarcar VCD456?",
        "Tem estoque para enviar o pedido VCD789?",
        "Posso despachar o VCD111 hoje?"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for análise de disponibilidade."""
        return intencao == "analisar_disponibilidade"

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Analisa pedido e retorna opções de envio A/B/C."""
        from app.separacao.models import Separacao
        # Import do serviço existente
        from app.claude_ai_lite.domains.carteira.services.opcoes_envio import OpcoesEnvioService

        campo, valor = self.extrair_valor_busca(entidades)

        resultado = {
            "sucesso": True,
            "valor_buscado": valor,
            "campo_busca": campo,
            "total_encontrado": 0,
            "dados": [],
            "analise": {},
            "opcoes": []
        }

        if not valor:
            resultado["sucesso"] = False
            resultado["erro"] = "Número do pedido não informado"
            return resultado

        try:
            # Verifica se já está separado
            itens_sep = Separacao.query.filter(
                Separacao.num_pedido.like(f"%{valor}%"),
                Separacao.sincronizado_nf == False
            ).all()

            # Usa o serviço de opções existente
            analise = OpcoesEnvioService.analisar_pedido(valor)

            if not analise["sucesso"]:
                # Se não encontrou na carteira, verifica se está separado
                if itens_sep:
                    return self._responder_pedido_ja_separado(valor, itens_sep, resultado)
                resultado["sucesso"] = False
                resultado["erro"] = analise.get("erro", "Pedido não encontrado")
                return resultado

            # Preenche resultado
            resultado["num_pedido"] = analise["num_pedido"]
            resultado["cliente"] = analise["cliente"]
            resultado["valor_total_pedido"] = analise["valor_total_pedido"]
            resultado["opcoes"] = analise["opcoes"]
            resultado["total_encontrado"] = len(analise["opcoes"])

            # Análise resumida
            resultado["analise"] = {
                "num_pedido": analise["num_pedido"],
                "cliente": analise["cliente"]["razao_social"] if analise["cliente"] else None,
                "valor_total": analise["valor_total_pedido"],
                "qtd_opcoes": len(analise["opcoes"]),
                "todos_disponiveis_hoje": analise["opcoes"][0]["disponivel_hoje"] if analise["opcoes"] else False
            }

            # Adiciona dados para memória/follow-up
            resultado["dados"] = analise.get("itens", [])

        except Exception as e:
            logger.error(f"Erro na análise de disponibilidade: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _responder_pedido_ja_separado(self, num_pedido: str, separacoes: List, resultado: Dict) -> Dict:
        """Responde quando pedido já está separado."""
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

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude com opções."""
        if not resultado.get("sucesso"):
            return f"Erro: {resultado.get('erro')}"

        if resultado["total_encontrado"] == 0:
            return resultado.get("mensagem", "Pedido não encontrado.")

        # Caso especial: pedido já separado
        if resultado.get("ja_separado"):
            return self._formatar_ja_separado(resultado)

        # Caso normal: opções de envio
        return self._formatar_opcoes(resultado)

    def _formatar_ja_separado(self, dados: Dict) -> str:
        """Formata resposta para pedido já separado."""
        a = dados["analise"]
        linhas = [
            f"=== PEDIDO {a['num_pedido']} - JÁ SEPARADO ===\n",
            f"O pedido já foi separado e possui {a['total_lotes']} lote(s).\n"
        ]
        for lote in dados["dados"]:
            exp = lote["expedicao"].strftime("%d/%m/%Y") if lote.get("expedicao") else "Não definida"
            agend = lote["agendamento"].strftime("%d/%m/%Y") if lote.get("agendamento") else "Não definido"
            linhas.append(f"  Status: {lote['status']}")
            linhas.append(f"  Expedição: {exp}")
            linhas.append(f"  Agendamento: {agend}")
            for p in lote["produtos"][:3]:
                linhas.append(f"    - {p['nome']}: {p['qtd']:.0f}un")
        return "\n".join(linhas)

    def _formatar_opcoes(self, dados: Dict) -> str:
        """Formata opções de envio A/B/C."""
        a = dados["analise"]
        opcoes = dados.get("opcoes", [])

        linhas = [
            f"=== ANÁLISE DE DISPONIBILIDADE - Pedido {a['num_pedido']} ===",
            f"Cliente: {a.get('cliente', 'N/A')}",
            f"Valor Total do Pedido: R$ {a.get('valor_total', 0):,.2f}",
            "",
            "=== OPÇÕES DE ENVIO ===",
            ""
        ]

        for opcao in opcoes:
            codigo = opcao["codigo"]
            linhas.append(f"--- OPÇÃO {codigo}: {opcao['titulo']} ---")
            linhas.append(f"  Data de Envio: {opcao['data_envio'] or 'Sem previsão'}")

            if opcao.get("dias_para_envio") is not None:
                if opcao["dias_para_envio"] == 0:
                    linhas.append(f"  Disponível: HOJE")
                else:
                    linhas.append(f"  Aguardar: {opcao['dias_para_envio']} dia(s)")

            linhas.append(f"  Valor: R$ {opcao['valor']:,.2f} ({opcao['percentual']:.1f}% do pedido)")
            linhas.append(f"  Itens: {opcao['qtd_itens']}")

            # Lista itens incluídos (resumido)
            if opcao.get("itens"):
                for item in opcao["itens"][:3]:
                    if item["disponivel_hoje"]:
                        status_item = "OK"
                    elif item.get("dias_para_disponivel"):
                        status_item = f"Aguardar {item['dias_para_disponivel']}d"
                    else:
                        status_item = "Sem previsão"
                    linhas.append(f"    - {item['nome_produto'][:35]}: {item['quantidade']:.0f}un [{status_item}]")
                if len(opcao["itens"]) > 3:
                    linhas.append(f"    ... e mais {len(opcao['itens']) - 3} itens")

            # Lista itens excluídos
            if opcao.get("itens_excluidos"):
                linhas.append(f"  ITENS NÃO INCLUÍDOS:")
                for item in opcao["itens_excluidos"]:
                    linhas.append(f"    X {item['nome_produto'][:35]}: {item['quantidade']:.0f}un (R$ {item['valor_total']:,.2f})")

            linhas.append("")

        linhas.append("Para criar separação, responda com a opção desejada (A, B ou C).")

        return "\n".join(linhas)
