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
    INTENCOES = [
        "analisar_disponibilidade",
        "quando_posso_enviar",
        "verificar_disponibilidade",
        "consultar_prazo",
        "consultar prazo de envio",
        "prazo_envio"
    ]
    CAMPOS_BUSCA = ["num_pedido", "raz_social_red", "cliente"]  # Aceita pedido OU cliente
    DESCRICAO = "Analisa quando um pedido/cliente pode ser enviado baseado no estoque"
    EXEMPLOS = [
        "Quando posso enviar o pedido VCD123?",
        "Quando embarcar VCD456?",
        "Quando dá pra enviar 28 pallets pro Atacadão 183?",
        "Posso despachar o VCD111 hoje?"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for análise de disponibilidade."""
        # Verifica se a intenção é de análise de disponibilidade
        if intencao in self.INTENCOES:
            return True

        # Verifica palavras-chave na intenção
        intencao_lower = intencao.lower()
        palavras_chave = ['quando', 'prazo', 'disponib', 'enviar', 'embarcar', 'despachar']
        if any(p in intencao_lower for p in palavras_chave):
            # Aceita num_pedido OU cliente
            if entidades.get('num_pedido') or entidades.get('raz_social_red') or entidades.get('cliente'):
                return True

        return False

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Analisa pedido ou cliente e retorna opções de envio com pallets calculados."""
        from app.separacao.models import Separacao
        from app.carteira.models import CarteiraPrincipal
        from app.producao.models import CadastroPalletizacao
        # Import do serviço existente
        from app.claude_ai_lite.domains.carteira.services.opcoes_envio import OpcoesEnvioService

        campo, valor = self.extrair_valor_busca(entidades)

        # Quantidade desejada de pallets (se informada)
        qtd_pallets_desejada = entidades.get('quantidade') or entidades.get('qtd_saldo')
        status_sep = str(entidades.get('status_separacao', '')).lower()
        filtro_add = str(entidades.get('filtro_adicional', '')).lower()
        excluir_separados = 'separad' in status_sep or 'separad' in filtro_add

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
            resultado["erro"] = "Número do pedido ou cliente não informado"
            return resultado

        try:
            # CASO 1: Busca por CLIENTE (não por num_pedido)
            if campo in ['raz_social_red', 'cliente']:
                return self._analisar_por_cliente(
                    valor, qtd_pallets_desejada, excluir_separados, resultado, entidades
                )

            # CASO 2: Busca por NUM_PEDIDO (comportamento original)
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

    def _analisar_por_cliente(
        self, cliente: str, qtd_pallets_desejada, excluir_separados: bool,
        resultado: Dict, entidades: Dict
    ) -> Dict[str, Any]:
        """
        Analisa disponibilidade por CLIENTE (não por pedido).

        Responde perguntas como: "Quando dá pra enviar 28 pallets pro Atacadão 183?"
        """
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from app.producao.models import CadastroPalletizacao
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        from datetime import date

        logger.info(f"[ANALISAR_DISP] Buscando por cliente: {cliente}, pallets desejados: {qtd_pallets_desejada}")

        # 1. Buscar itens do cliente na carteira
        query = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.raz_social_red.ilike(f"%{cliente}%"),
            CarteiraPrincipal.ativo == True
        )

        # 2. Excluir itens já separados se solicitado
        if excluir_separados:
            # Pegar num_pedidos já separados desse cliente
            pedidos_separados = Separacao.query.filter(
                Separacao.raz_social_red.ilike(f"%{cliente}%"),
                Separacao.sincronizado_nf == False
            ).with_entities(Separacao.num_pedido, Separacao.cod_produto).all()

            # Criar set de (num_pedido, cod_produto) já separados
            separados_set = {(s.num_pedido, s.cod_produto) for s in pedidos_separados}
            logger.info(f"[ANALISAR_DISP] {len(separados_set)} itens já separados excluídos")

        itens_carteira = query.all()

        if not itens_carteira:
            resultado["sucesso"] = False
            resultado["erro"] = f"Cliente '{cliente}' não encontrado na carteira"
            return resultado

        # 3. Carregar cache de palletização
        cache_pallet = {}
        produtos = CadastroPalletizacao.query.filter_by(ativo=True).all()
        for p in produtos:
            cache_pallet[p.cod_produto] = {
                'palletizacao': float(p.palletizacao or 0),
                'peso_bruto': float(p.peso_bruto or 0)
            }

        # 4. Calcular pallets para cada item
        hoje = date.today()
        itens_analisados = []
        total_pallets_disponiveis = 0.0
        total_peso = 0.0

        for item in itens_carteira:
            # Excluir se já separado
            if excluir_separados and (item.num_pedido, item.cod_produto) in separados_set:
                continue

            quantidade = float(item.qtd_saldo_produto_pedido or 0)
            if quantidade <= 0:
                continue

            # Calcular pallets REAL via CadastroPalletizacao
            pallet_info = cache_pallet.get(item.cod_produto, {})
            palletizacao = pallet_info.get('palletizacao', 0)
            peso_bruto = pallet_info.get('peso_bruto', 0)

            if palletizacao > 0:
                pallets = round(quantidade / palletizacao, 2)
                peso = round(quantidade * peso_bruto, 2)
            else:
                pallets = 0
                peso = 0

            # Buscar disponibilidade de estoque
            try:
                projecao = ServicoEstoqueSimples.calcular_projecao(item.cod_produto, dias=30)
                estoque_atual = projecao.get("estoque_atual", 0)
                disponivel_hoje = estoque_atual >= quantidade
            except Exception:
                estoque_atual = 0
                disponivel_hoje = False

            itens_analisados.append({
                "num_pedido": item.num_pedido,
                "cod_produto": item.cod_produto,
                "nome_produto": item.nome_produto,
                "quantidade": quantidade,
                "pallets": pallets,
                "peso": peso,
                "estoque_atual": estoque_atual,
                "disponivel_hoje": disponivel_hoje,
                "valor": float(item.preco_produto_pedido or 0) * quantidade
            })

            total_pallets_disponiveis += pallets
            total_peso += peso

        if not itens_analisados:
            resultado["sucesso"] = False
            resultado["erro"] = f"Nenhum item disponível para o cliente '{cliente}'"
            return resultado

        # 5. Ordenar por disponibilidade (disponíveis primeiro)
        itens_analisados.sort(key=lambda x: (not x['disponivel_hoje'], -x['pallets']))

        # 6. Montar resultado
        resultado["sucesso"] = True
        resultado["cliente"] = cliente
        resultado["total_pallets"] = round(total_pallets_disponiveis, 2)
        resultado["total_peso"] = round(total_peso, 2)
        resultado["total_itens"] = len(itens_analisados)
        resultado["total_encontrado"] = len(itens_analisados)
        resultado["dados"] = itens_analisados

        # Quantos itens disponíveis hoje
        itens_disponiveis_hoje = [i for i in itens_analisados if i['disponivel_hoje']]
        pallets_disponiveis_hoje = sum(i['pallets'] for i in itens_disponiveis_hoje)

        resultado["analise"] = {
            "cliente": cliente,
            "total_pallets": round(total_pallets_disponiveis, 2),
            "total_peso": round(total_peso, 2),
            "pallets_disponiveis_hoje": round(pallets_disponiveis_hoje, 2),
            "itens_disponiveis_hoje": len(itens_disponiveis_hoje),
            "itens_total": len(itens_analisados),
            "excluiu_separados": excluir_separados
        }

        # Se pediu quantidade específica de pallets, monta carga sugerida
        if qtd_pallets_desejada:
            qtd_pallets_desejada = float(qtd_pallets_desejada)

            # Monta carga sugerida selecionando itens até atingir a quantidade
            carga_sugerida = self._montar_carga_sugerida(
                itens_analisados, qtd_pallets_desejada
            )
            resultado["carga_sugerida"] = carga_sugerida

            if carga_sugerida["pode_montar"]:
                if carga_sugerida["todos_disponiveis_hoje"]:
                    resultado["analise"]["pode_enviar_hoje"] = True
                    resultado["analise"]["mensagem"] = (
                        f"✅ Pode enviar {qtd_pallets_desejada} pallets HOJE! "
                        f"Montei uma carga com {carga_sugerida['total_pallets']:.1f} pallets "
                        f"usando {len(carga_sugerida['itens'])} itens."
                    )
                else:
                    resultado["analise"]["pode_enviar_hoje"] = False
                    resultado["analise"]["mensagem"] = (
                        f"⏳ Montei uma carga com {carga_sugerida['total_pallets']:.1f} pallets, "
                        f"mas {carga_sugerida['itens_aguardar']} item(ns) não tem estoque hoje."
                    )
            else:
                resultado["analise"]["pode_enviar_hoje"] = False
                resultado["analise"]["mensagem"] = (
                    f"❌ Não foi possível montar carga de {qtd_pallets_desejada} pallets. "
                    f"Total disponível na carteira: {total_pallets_disponiveis:.1f} pallets"
                )

        logger.info(f"[ANALISAR_DISP] Cliente {cliente}: {total_pallets_disponiveis:.1f} pallets, {len(itens_analisados)} itens")
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

        # Caso: análise por CLIENTE (tem total_pallets)
        if resultado.get("total_pallets") is not None:
            return self._formatar_analise_cliente(resultado)

        # Caso normal: opções de envio por pedido
        return self._formatar_opcoes(resultado)

    def _formatar_analise_cliente(self, dados: Dict) -> str:
        """Formata análise de disponibilidade por CLIENTE com pallets calculados."""
        a = dados.get("analise", {})
        itens = dados.get("dados", [])

        linhas = [
            f"=== ANÁLISE DE DISPONIBILIDADE - Cliente: {a.get('cliente', 'N/A')} ===",
            "",
            f"📦 RESUMO DE PALLETS:",
            f"   Total na carteira: {a.get('total_pallets', 0):.1f} pallets",
            f"   Disponível HOJE: {a.get('pallets_disponiveis_hoje', 0):.1f} pallets",
            f"   Total de itens: {a.get('itens_total', 0)}",
            f"   Itens disponíveis hoje: {a.get('itens_disponiveis_hoje', 0)}",
            f"   Peso total: {a.get('total_peso', 0):,.0f} kg",
        ]

        if a.get('excluiu_separados'):
            linhas.append(f"   (Excluídos itens já separados)")

        # Mensagem principal se pediu quantidade específica
        if a.get('mensagem'):
            linhas.append("")
            linhas.append(f"🎯 {a['mensagem']}")

        # Lista dos itens
        linhas.append("")
        linhas.append("--- ITENS DETALHADOS ---")

        for i, item in enumerate(itens[:15], 1):
            status = "✅ OK" if item.get('disponivel_hoje') else "⏳ Aguardar"
            linhas.append(
                f"{i}. {item['nome_produto'][:35]} | "
                f"Pedido: {item['num_pedido']} | "
                f"{item['quantidade']:.0f} un = {item['pallets']:.2f} pallets | "
                f"[{status}]"
            )

        if len(itens) > 15:
            linhas.append(f"... e mais {len(itens) - 15} itens")

        return "\n".join(linhas)

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
