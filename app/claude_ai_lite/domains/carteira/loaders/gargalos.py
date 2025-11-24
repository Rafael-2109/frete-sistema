"""
Loader de Gargalos - Identifica produtos que travam pedidos por falta de estoque.
Complexo: cruza carteira + estoque + projecao para identificar bottlenecks.
Max 200 linhas.
"""

from typing import Dict, Any, List, Tuple
from datetime import date, timedelta
from collections import defaultdict
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class GargalosLoader(BaseLoader):
    """Identifica produtos gargalo que impedem envio de pedidos."""

    DOMINIO = "carteira"

    CAMPOS_BUSCA = [
        "num_pedido",  # Analisa gargalos de um pedido especifico
        "geral",       # Analisa gargalos gerais da carteira
        "cod_produto", # Analisa impacto de um produto especifico
    ]

    def buscar(self, valor: str, campo: str, contexto: Dict = None) -> Dict[str, Any]:
        """Identifica gargalos de estoque."""
        self._contexto = contexto  # Guarda para uso nos métodos internos

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
            if campo == "num_pedido":
                return self._gargalos_pedido(valor, resultado)
            elif campo == "geral":
                return self._gargalos_gerais(resultado)
            elif campo == "cod_produto":
                return self._impacto_produto(valor, resultado)

        except Exception as e:
            logger.error(f"Erro ao analisar gargalos: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _gargalos_pedido(self, num_pedido: str, resultado: Dict) -> Dict:
        """Analisa quais produtos travam um pedido especifico."""
        from app.carteira.models import CarteiraPrincipal
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        # Busca itens do pedido na carteira
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido.like(f"%{num_pedido}%"),
            CarteiraPrincipal.ativo == True
        ).all()

        if not itens:
            resultado["mensagem"] = f"Pedido '{num_pedido}' nao encontrado na carteira."
            return resultado

        # Analisa cada item
        gargalos = []
        itens_ok = []
        hoje = date.today()

        for item in itens:
            qtd_necessaria = float(item.qtd_saldo_produto_pedido or 0)
            if qtd_necessaria <= 0:
                continue

            projecao = ServicoEstoqueSimples.calcular_projecao(item.cod_produto, dias=30)
            estoque_atual = projecao.get("estoque_atual", 0)

            # Verifica se tem estoque suficiente
            if estoque_atual >= qtd_necessaria:
                itens_ok.append({
                    "cod_produto": item.cod_produto,
                    "nome_produto": item.nome_produto,
                    "qtd_necessaria": qtd_necessaria,
                    "estoque_atual": estoque_atual,
                    "status": "DISPONIVEL"
                })
            else:
                # Encontra quando tera estoque
                data_disponivel = self._encontrar_data_estoque(projecao, qtd_necessaria, hoje)
                dias_espera = (data_disponivel - hoje).days if data_disponivel else None

                gargalos.append({
                    "cod_produto": item.cod_produto,
                    "nome_produto": item.nome_produto,
                    "qtd_necessaria": qtd_necessaria,
                    "estoque_atual": estoque_atual,
                    "falta": qtd_necessaria - estoque_atual,
                    "data_disponivel": data_disponivel.strftime("%d/%m/%Y") if data_disponivel else None,
                    "dias_espera": dias_espera,
                    "impacto_valor": float(item.preco_produto_pedido or 0) * qtd_necessaria,
                    "status": "GARGALO"
                })

        # Ordena gargalos por dias de espera (maior primeiro)
        gargalos.sort(key=lambda x: (x["dias_espera"] or 999), reverse=True)

        resultado["dados"] = {
            "num_pedido": itens[0].num_pedido,
            "cliente": itens[0].raz_social_red,
            "gargalos": gargalos,
            "itens_ok": itens_ok
        }
        resultado["total_encontrado"] = len(gargalos)
        resultado["resumo"] = {
            "total_itens": len(gargalos) + len(itens_ok),
            "itens_gargalo": len(gargalos),
            "itens_disponiveis": len(itens_ok),
            "maior_espera_dias": max((g["dias_espera"] or 0) for g in gargalos) if gargalos else 0,
            "pode_enviar_parcial": len(itens_ok) > 0
        }

        return resultado

    def _gargalos_gerais(self, resultado: Dict) -> Dict:
        """Analisa produtos que mais travam pedidos na carteira toda."""
        from app.carteira.models import CarteiraPrincipal
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        from sqlalchemy import func

        # Agrupa demanda por produto na carteira
        demanda = CarteiraPrincipal.query.with_entities(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total_demanda'),
            func.count(CarteiraPrincipal.num_pedido.distinct()).label('qtd_pedidos')
        ).filter(
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto
        ).all()

        # Analisa cada produto
        gargalos = []
        for prod in demanda:
            total_demanda = float(prod.total_demanda or 0)
            if total_demanda <= 0:
                continue

            projecao = ServicoEstoqueSimples.calcular_projecao(prod.cod_produto, dias=14)
            estoque_atual = projecao.get("estoque_atual", 0)

            if estoque_atual < total_demanda:
                falta = total_demanda - estoque_atual
                cobertura = (estoque_atual / total_demanda * 100) if total_demanda > 0 else 0

                gargalos.append({
                    "cod_produto": prod.cod_produto,
                    "nome_produto": prod.nome_produto,
                    "demanda_total": total_demanda,
                    "estoque_atual": estoque_atual,
                    "falta": falta,
                    "cobertura_pct": round(cobertura, 1),
                    "pedidos_afetados": prod.qtd_pedidos,
                    "ruptura_prevista": projecao.get("dia_ruptura"),
                    "severidade": self._calcular_severidade(cobertura, prod.qtd_pedidos)
                })

        # Ordena por severidade (maior primeiro)
        gargalos.sort(key=lambda x: x["severidade"], reverse=True)

        resultado["dados"] = gargalos[:20]  # Top 20
        resultado["total_encontrado"] = len(gargalos)
        resultado["resumo"] = {
            "total_produtos_gargalo": len(gargalos),
            "produtos_criticos": len([g for g in gargalos if g["severidade"] >= 8]),
            "produtos_alerta": len([g for g in gargalos if 5 <= g["severidade"] < 8]),
        }

        return resultado

    def _impacto_produto(self, cod_produto: str, resultado: Dict) -> Dict:
        """Analisa impacto de um produto especifico nos pedidos."""
        from app.carteira.models import CarteiraPrincipal
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        # Busca pedidos que usam esse produto
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto.ilike(f"%{cod_produto}%"),
            CarteiraPrincipal.ativo == True
        ).all()

        if not itens:
            resultado["mensagem"] = f"Produto '{cod_produto}' nao encontrado na carteira."
            return resultado

        projecao = ServicoEstoqueSimples.calcular_projecao(itens[0].cod_produto, dias=14)
        estoque_atual = projecao.get("estoque_atual", 0)

        pedidos_afetados = []
        for item in itens:
            qtd = float(item.qtd_saldo_produto_pedido or 0)
            pedidos_afetados.append({
                "num_pedido": item.num_pedido,
                "cliente": item.raz_social_red,
                "qtd_necessaria": qtd,
                "pode_atender": estoque_atual >= qtd,
                "expedicao": item.expedicao.strftime("%d/%m/%Y") if item.expedicao else None
            })

        resultado["dados"] = {
            "cod_produto": itens[0].cod_produto,
            "nome_produto": itens[0].nome_produto,
            "estoque_atual": estoque_atual,
            "demanda_total": sum(p["qtd_necessaria"] for p in pedidos_afetados),
            "pedidos_afetados": pedidos_afetados
        }
        resultado["total_encontrado"] = len(pedidos_afetados)
        resultado["resumo"] = {
            "total_pedidos": len(pedidos_afetados),
            "pedidos_atendidos": len([p for p in pedidos_afetados if p["pode_atender"]]),
            "pedidos_bloqueados": len([p for p in pedidos_afetados if not p["pode_atender"]])
        }

        return resultado

    def _encontrar_data_estoque(self, projecao: Dict, qtd: float, hoje: date) -> date:
        """Encontra primeira data com estoque suficiente."""
        for dia in projecao.get("projecao", []):
            if dia.get("saldo_final", 0) >= qtd:
                return date.fromisoformat(dia["data"])
        return None

    def _calcular_severidade(self, cobertura: float, qtd_pedidos: int) -> int:
        """Calcula severidade do gargalo (1-10)."""
        score = 0
        if cobertura < 20:
            score += 5
        elif cobertura < 50:
            score += 3
        elif cobertura < 80:
            score += 1

        if qtd_pedidos >= 10:
            score += 5
        elif qtd_pedidos >= 5:
            score += 3
        elif qtd_pedidos >= 2:
            score += 1

        return min(score, 10)

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Nenhum gargalo identificado.")

        campo = dados["campo_busca"]

        if campo == "num_pedido":
            return self._formatar_gargalo_pedido(dados)
        elif campo == "geral":
            return self._formatar_gargalos_gerais(dados)
        elif campo == "cod_produto":
            return self._formatar_impacto_produto(dados)

        return "Formato nao implementado"

    def _formatar_gargalo_pedido(self, dados: Dict) -> str:
        """Formata gargalos de pedido especifico."""
        d = dados["dados"]
        r = dados["resumo"]

        linhas = [
            f"=== ANALISE DE GARGALOS - Pedido {d['num_pedido']} ===",
            f"Cliente: {d['cliente']}",
            "",
            f"Resumo: {r['itens_gargalo']} gargalo(s) de {r['total_itens']} item(ns)",
            f"Maior espera: {r['maior_espera_dias']} dia(s)",
            ""
        ]

        if d["gargalos"]:
            linhas.append("ITENS COM PROBLEMA DE ESTOQUE:")
            for g in d["gargalos"]:
                disp = f"Disponivel em {g['data_disponivel']}" if g["data_disponivel"] else "Sem previsao"
                linhas.append(f"  - {g['nome_produto'][:40]}")
                linhas.append(f"    Necessario: {g['qtd_necessaria']:.0f} | Estoque: {g['estoque_atual']:.0f} | Falta: {g['falta']:.0f}")
                linhas.append(f"    {disp}")
            linhas.append("")

        if d["itens_ok"]:
            linhas.append(f"ITENS DISPONIVEIS ({len(d['itens_ok'])}):")
            for item in d["itens_ok"][:5]:
                linhas.append(f"  - {item['nome_produto'][:40]}: {item['qtd_necessaria']:.0f}un OK")

        if r["pode_enviar_parcial"]:
            linhas.append("")
            linhas.append("SUGESTAO: Envio parcial possivel com os itens disponiveis.")

        return "\n".join(linhas)

    def _formatar_gargalos_gerais(self, dados: Dict) -> str:
        """Formata analise geral de gargalos."""
        r = dados["resumo"]

        linhas = [
            "=== PRODUTOS GARGALO NA CARTEIRA ===",
            "",
            f"Total de Produtos com Problema: {r['total_produtos_gargalo']}",
            f"  Criticos (severidade 8-10): {r['produtos_criticos']}",
            f"  Alerta (severidade 5-7): {r['produtos_alerta']}",
            "",
            "TOP GARGALOS (ordenado por severidade):",
            ""
        ]

        for g in dados["dados"][:10]:
            sev_emoji = "CRITICO" if g["severidade"] >= 8 else ("ALERTA" if g["severidade"] >= 5 else "ATENCAO")
            linhas.append(f"[{sev_emoji}] {g['nome_produto'][:35]} ({g['cod_produto']})")
            linhas.append(f"    Demanda: {g['demanda_total']:.0f} | Estoque: {g['estoque_atual']:.0f} | Cobertura: {g['cobertura_pct']:.0f}%")
            linhas.append(f"    Pedidos afetados: {g['pedidos_afetados']}")
            linhas.append("")

        return "\n".join(linhas)

    def _formatar_impacto_produto(self, dados: Dict) -> str:
        """Formata impacto de produto especifico."""
        d = dados["dados"]
        r = dados["resumo"]

        linhas = [
            f"=== IMPACTO DO PRODUTO: {d['nome_produto']} ===",
            f"Codigo: {d['cod_produto']}",
            "",
            f"Estoque Atual: {d['estoque_atual']:,.0f}un",
            f"Demanda Total: {d['demanda_total']:,.0f}un",
            "",
            f"Pedidos Afetados: {r['total_pedidos']}",
            f"  Podem ser atendidos: {r['pedidos_atendidos']}",
            f"  Bloqueados por falta: {r['pedidos_bloqueados']}",
            "",
            "PEDIDOS:"
        ]

        for ped in d["pedidos_afetados"][:10]:
            status = "OK" if ped["pode_atender"] else "BLOQUEADO"
            linhas.append(f"  - {ped['num_pedido']} | {ped['cliente'][:20]} | {ped['qtd_necessaria']:.0f}un | {status}")

        return "\n".join(linhas)
