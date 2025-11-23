"""
Loader de Rotas - Consultas por rota, sub-rota e UF.
Max 200 linhas.
"""

from typing import Dict, Any, List
from sqlalchemy import func
import logging

from ...base import BaseLoader

logger = logging.getLogger(__name__)


class RotasLoader(BaseLoader):
    """Consultas por rota, sub-rota e UF na carteira/separacao."""

    DOMINIO = "carteira"

    CAMPOS_BUSCA = [
        "rota",
        "sub_rota",
        "cod_uf",
    ]

    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        """Busca pedidos/separacoes por rota, sub-rota ou UF."""
        from app.separacao.models import Separacao
        from app.localidades.models import CadastroRota, CadastroSubRota

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
            # Query base: apenas separacoes nao faturadas
            query = Separacao.query.filter(Separacao.sincronizado_nf == False)

            # Aplica filtro conforme campo
            if campo == "rota":
                query = query.filter(Separacao.rota.ilike(f"%{valor}%"))
            elif campo == "sub_rota":
                query = query.filter(Separacao.sub_rota.ilike(f"%{valor}%"))
            elif campo == "cod_uf":
                # UF aceita valor exato (2 caracteres) ou parcial
                valor_uf = valor.upper().strip()
                if len(valor_uf) == 2:
                    query = query.filter(Separacao.cod_uf == valor_uf)
                else:
                    query = query.filter(Separacao.cod_uf.ilike(f"%{valor_uf}%"))

            separacoes = query.all()

            if not separacoes:
                # Tenta buscar info da rota/sub-rota para dar contexto
                if campo == "rota":
                    rota_info = CadastroRota.query.filter(CadastroRota.rota.ilike(f"%{valor}%")).first()
                    if rota_info:
                        resultado["mensagem"] = f"Rota '{rota_info.rota}' (UF: {rota_info.cod_uf}) existe, mas nao ha pedidos pendentes nela."
                    else:
                        resultado["mensagem"] = f"Rota '{valor}' nao encontrada no cadastro."
                elif campo == "sub_rota":
                    sub_info = CadastroSubRota.query.filter(CadastroSubRota.sub_rota.ilike(f"%{valor}%")).first()
                    if sub_info:
                        resultado["mensagem"] = f"Sub-rota '{sub_info.sub_rota}' ({sub_info.nome_cidade}/{sub_info.cod_uf}) existe, mas nao ha pedidos pendentes nela."
                    else:
                        resultado["mensagem"] = f"Sub-rota '{valor}' nao encontrada no cadastro."
                else:
                    resultado["mensagem"] = f"Nenhum pedido encontrado para UF '{valor}'."
                return resultado

            # Agrupa por pedido (separacao_lote_id + num_pedido)
            pedidos = {}
            for sep in separacoes:
                key = f"{sep.separacao_lote_id}:{sep.num_pedido}"
                if key not in pedidos:
                    pedidos[key] = {
                        "separacao_lote_id": sep.separacao_lote_id,
                        "num_pedido": sep.num_pedido,
                        "cliente": sep.raz_social_red,
                        "cidade": sep.nome_cidade,
                        "uf": sep.cod_uf,
                        "rota": sep.rota,
                        "sub_rota": sep.sub_rota,
                        "roteirizacao": sep.roteirizacao,
                        "expedicao": sep.expedicao.strftime("%d/%m/%Y") if sep.expedicao else None,
                        "agendamento": sep.agendamento.strftime("%d/%m/%Y") if sep.agendamento else None,
                        "status": sep.status_calculado,
                        "valor_total": 0,
                        "peso_total": 0,
                        "pallet_total": 0,
                        "qtd_itens": 0,
                        "produtos": []
                    }
                pedidos[key]["valor_total"] += float(sep.valor_saldo or 0)
                pedidos[key]["peso_total"] += float(sep.peso or 0)
                pedidos[key]["pallet_total"] += float(sep.pallet or 0)
                pedidos[key]["qtd_itens"] += 1
                pedidos[key]["produtos"].append({
                    "cod": sep.cod_produto,
                    "nome": sep.nome_produto,
                    "qtd": float(sep.qtd_saldo or 0)
                })

            resultado["dados"] = list(pedidos.values())
            resultado["total_encontrado"] = len(pedidos)

            # Resumo agregado
            resultado["resumo"] = {
                "total_pedidos": len(pedidos),
                "total_valor": sum(p["valor_total"] for p in pedidos.values()),
                "total_peso": sum(p["peso_total"] for p in pedidos.values()),
                "total_pallets": sum(p["pallet_total"] for p in pedidos.values()),
                "total_itens": sum(p["qtd_itens"] for p in pedidos.values()),
                "por_status": self._agrupar_por_status(pedidos.values()),
                "por_uf": self._agrupar_por_uf(pedidos.values()) if campo != "cod_uf" else None,
            }

        except Exception as e:
            logger.error(f"Erro ao buscar por {campo}: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _agrupar_por_status(self, pedidos) -> Dict[str, int]:
        """Agrupa pedidos por status."""
        por_status = {}
        for p in pedidos:
            st = p["status"]
            por_status[st] = por_status.get(st, 0) + 1
        return por_status

    def _agrupar_por_uf(self, pedidos) -> Dict[str, Dict]:
        """Agrupa pedidos por UF com totais."""
        por_uf = {}
        for p in pedidos:
            uf = p["uf"] or "N/A"
            if uf not in por_uf:
                por_uf[uf] = {"qtd": 0, "valor": 0}
            por_uf[uf]["qtd"] += 1
            por_uf[uf]["valor"] += p["valor_total"]
        return por_uf

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not dados.get("sucesso"):
            return f"Erro: {dados.get('erro')}"
        if dados["total_encontrado"] == 0:
            return dados.get("mensagem", "Nenhum pedido encontrado.")

        r = dados["resumo"]
        campo = dados["campo_busca"]
        valor = dados["valor_buscado"]

        linhas = [
            f"=== PEDIDOS POR {campo.upper()}: {valor.upper()} ===",
            "",
            "RESUMO:",
            f"  Total de Pedidos: {r['total_pedidos']}",
            f"  Valor Total: R$ {r['total_valor']:,.2f}",
            f"  Peso Total: {r['total_peso']:,.0f} kg",
            f"  Pallets: {r['total_pallets']:,.1f}",
            f"  Itens: {r['total_itens']}",
            ""
        ]

        # Agrupa por status
        if r.get("por_status"):
            linhas.append("Por Status:")
            for st, qtd in r["por_status"].items():
                linhas.append(f"  - {st}: {qtd} pedido(s)")
            linhas.append("")

        # Agrupa por UF (se nao foi busca por UF)
        if r.get("por_uf"):
            linhas.append("Por UF:")
            for uf, info in sorted(r["por_uf"].items(), key=lambda x: -x[1]["valor"]):
                linhas.append(f"  - {uf}: {info['qtd']} pedido(s) | R$ {info['valor']:,.2f}")
            linhas.append("")

        # Lista pedidos (max 10)
        linhas.append("PEDIDOS:")
        for p in dados["dados"][:10]:
            linhas.append(f"--- {p['num_pedido']} ---")
            linhas.append(f"  Cliente: {p['cliente']}")
            linhas.append(f"  Destino: {p['cidade']}/{p['uf']}")
            if p.get("rota"):
                linhas.append(f"  Rota: {p['rota']} | Sub-rota: {p.get('sub_rota', 'N/A')}")
            if p.get("roteirizacao"):
                linhas.append(f"  Transportadora: {p['roteirizacao']}")
            linhas.append(f"  Status: {p['status']} | Valor: R$ {p['valor_total']:,.2f}")
            exp = p.get("expedicao") or "Nao definida"
            linhas.append(f"  Expedicao: {exp}")
            linhas.append("")

        if len(dados["dados"]) > 10:
            linhas.append(f"... e mais {len(dados['dados']) - 10} pedido(s)")

        return "\n".join(linhas)
