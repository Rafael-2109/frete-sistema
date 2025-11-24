"""
Loader de Estoque - Consultas de estoque atual, projecao e rupturas.
Usa ServicoEstoqueSimples para calculos.
Max 200 linhas.
"""

from typing import Dict, Any, List
from datetime import date
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class EstoqueLoader(BaseLoader):
    """Consultas de estoque: atual, projecao, rupturas."""

    DOMINIO = "estoque"

    CAMPOS_BUSCA = [
        "cod_produto",
        "nome_produto",
        "ruptura",  # Campo especial para listar produtos com ruptura
    ]

    def buscar(self, valor: str, campo: str, contexto: Dict = None) -> Dict[str, Any]:
        """Busca informacoes de estoque."""
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        from app.producao.models import CadastroPalletizacao

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
            # Caso especial: listar produtos com ruptura
            if campo == "ruptura":
                return self._buscar_rupturas(valor, resultado)

            # Busca produto pelo nome ou codigo
            if campo == "nome_produto":
                query = CadastroPalletizacao.query.filter(
                    CadastroPalletizacao.nome_produto.ilike(f"%{valor}%"),
                    CadastroPalletizacao.ativo == True
                )
            else:  # cod_produto
                query = CadastroPalletizacao.query.filter(
                    CadastroPalletizacao.cod_produto.ilike(f"%{valor}%"),
                    CadastroPalletizacao.ativo == True
                )

            # Aplica filtros aprendidos pelo IA Trainer
            query = self.aplicar_filtros_aprendidos(query, contexto, CadastroPalletizacao)

            produtos = query.limit(10).all()

            if not produtos:
                resultado["mensagem"] = f"Produto '{valor}' nao encontrado no cadastro."
                return resultado

            # Calcula projecao para cada produto
            dados_produtos = []
            for prod in produtos:
                projecao = ServicoEstoqueSimples.calcular_projecao(prod.cod_produto, dias=14)

                # Buscar proximas entradas (producao)
                entradas = ServicoEstoqueSimples.calcular_entradas_previstas(
                    prod.cod_produto,
                    date.today(),
                    date.today().replace(day=28) if date.today().month < 12 else date.today()
                )

                proxima_entrada = None
                for dt, qtd in sorted(entradas.items()):
                    if qtd > 0:
                        proxima_entrada = {"data": dt.strftime("%d/%m/%Y"), "qtd": qtd}
                        break

                dados_produtos.append({
                    "cod_produto": prod.cod_produto,
                    "nome_produto": prod.nome_produto,
                    "estoque_atual": projecao.get("estoque_atual", 0),
                    "menor_estoque_d7": projecao.get("menor_estoque_d7", 0),
                    "menor_estoque_d28": projecao.get("menor_estoque_d28", 0),
                    "dia_ruptura": projecao.get("dia_ruptura"),
                    "proxima_entrada": proxima_entrada,
                    "projecao_7dias": self._resumir_projecao(projecao.get("projecao", []), 7),
                    "status_estoque": self._classificar_estoque(projecao)
                })

            resultado["dados"] = dados_produtos
            resultado["total_encontrado"] = len(dados_produtos)

        except Exception as e:
            logger.error(f"Erro ao buscar estoque: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _buscar_rupturas(self, valor: str, resultado: Dict) -> Dict:
        """Busca produtos com ruptura prevista."""
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        try:
            # Valor pode ser numero de dias (default 7)
            dias = 7
            if valor and valor.isdigit():
                dias = min(int(valor), 30)

            rupturas = ServicoEstoqueSimples.get_produtos_ruptura(dias_limite=dias)

            if not rupturas:
                resultado["mensagem"] = f"Nenhum produto com ruptura prevista nos proximos {dias} dias."
                return resultado

            resultado["dados"] = rupturas
            resultado["total_encontrado"] = len(rupturas)
            resultado["resumo"] = {
                "horizonte_dias": dias,
                "total_produtos_ruptura": len(rupturas),
                "ruptura_hoje": len([r for r in rupturas if r["dias_ate_ruptura"] == 0]),
                "ruptura_3dias": len([r for r in rupturas if r["dias_ate_ruptura"] <= 3]),
            }

        except Exception as e:
            logger.error(f"Erro ao buscar rupturas: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _resumir_projecao(self, projecao: List[Dict], dias: int) -> List[Dict]:
        """Resume projecao para os proximos N dias."""
        resumo = []
        for dia in projecao[:dias + 1]:
            resumo.append({
                "dia": f"D{dia.get('dia', 0)}",
                "data": dia.get("data", ""),
                "saldo": dia.get("saldo_final", 0),
                "entrada": dia.get("entrada", 0),
                "saida": dia.get("saida", 0),
            })
        return resumo

    def _classificar_estoque(self, projecao: Dict) -> str:
        """Classifica status do estoque."""
        estoque = projecao.get("estoque_atual", 0)
        menor_d7 = projecao.get("menor_estoque_d7", 0)
        ruptura = projecao.get("dia_ruptura")

        if estoque <= 0:
            return "SEM_ESTOQUE"
        elif ruptura:
            return "RUPTURA_PREVISTA"
        elif menor_d7 < estoque * 0.2:
            return "ESTOQUE_BAIXO"
        else:
            return "ESTOQUE_OK"

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Nenhum produto encontrado.")

        campo = dados["campo_busca"]

        # Formato especial para rupturas
        if campo == "ruptura":
            return self._formatar_rupturas(dados)

        # Formato padrao para consulta de produto
        linhas = [f"=== ANALISE DE ESTOQUE ===", ""]

        for prod in dados["dados"]:
            status_emoji = {
                "SEM_ESTOQUE": "CRITICO",
                "RUPTURA_PREVISTA": "ALERTA",
                "ESTOQUE_BAIXO": "ATENCAO",
                "ESTOQUE_OK": "OK"
            }.get(prod["status_estoque"], "?")

            linhas.append(f"--- {prod['nome_produto']} ({prod['cod_produto']}) ---")
            linhas.append(f"  Status: [{status_emoji}]")
            linhas.append(f"  Estoque Atual: {prod['estoque_atual']:,.0f} unidades")
            linhas.append(f"  Menor Estoque D7: {prod['menor_estoque_d7']:,.0f} unidades")

            if prod["dia_ruptura"]:
                linhas.append(f"  ALERTA: Ruptura prevista em {prod['dia_ruptura']}")

            if prod["proxima_entrada"]:
                linhas.append(f"  Proxima Entrada: {prod['proxima_entrada']['qtd']:,.0f}un em {prod['proxima_entrada']['data']}")

            # Projecao resumida
            if prod["projecao_7dias"]:
                linhas.append("  Projecao (7 dias):")
                for dia in prod["projecao_7dias"][:4]:  # Mostra D0 a D3
                    mov = ""
                    if dia["entrada"] > 0:
                        mov += f"+{dia['entrada']:.0f}"
                    if dia["saida"] > 0:
                        mov += f" -{dia['saida']:.0f}"
                    linhas.append(f"    {dia['dia']}: {dia['saldo']:,.0f}un {mov}")

            linhas.append("")

        return "\n".join(linhas)

    def _formatar_rupturas(self, dados: Dict) -> str:
        """Formata lista de rupturas."""
        r = dados.get("resumo", {})
        linhas = [
            f"=== PRODUTOS COM RUPTURA PREVISTA ({r.get('horizonte_dias', 7)} dias) ===",
            "",
            f"Total: {r.get('total_produtos_ruptura', 0)} produto(s)",
            f"  Ruptura HOJE: {r.get('ruptura_hoje', 0)}",
            f"  Ruptura em 3 dias: {r.get('ruptura_3dias', 0)}",
            ""
        ]

        for prod in dados["dados"][:15]:
            dias = prod["dias_ate_ruptura"]
            urgencia = "HOJE!" if dias == 0 else f"em {dias}d"
            linhas.append(f"  - {prod['cod_produto']}: Estoque {prod['estoque_atual']:,.0f}un | Ruptura {urgencia}")

        if len(dados["dados"]) > 15:
            linhas.append(f"  ... e mais {len(dados['dados']) - 15} produto(s)")

        return "\n".join(linhas)
