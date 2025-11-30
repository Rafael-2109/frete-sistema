"""
Capacidade: Analisar Disponibilidade

Analisa quando um pedido pode ser enviado e gera opções A/B/C.

v3.0 (28/11/2025):
- NOVO: Suporte a consultas por DATA de disponibilidade
  "Quais produtos do Atacadão terão estoque no dia 01/12?"
- NOVO: Filtros combinados (cliente + UF + data + produto)
- NOVO: Integração com separacao_actions para confirmação de carga
- NOVO: Mais intenções e campos de busca
- Calcula saldo real: carteira - separações pendentes (sincronizado_nf=False)
- Agrupa resultado por pedido com detalhe de itens
- Ordena: disponíveis primeiro, depois por valor
- Suporta follow-ups: "qual valor?", "qual peso?", "quantos pallets?"

v2.0 (27/11/2025):
- Adicionado suporte a "pedidos em aberto que dá pra mandar"
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import date, datetime, timedelta
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class AnalisarDisponibilidadeCapability(BaseCapability):
    """Analisa disponibilidade e gera opções de envio."""

    NOME = "analisar_disponibilidade"
    DOMINIO = "carteira"
    TIPO = "consulta"

    # === INTENÇÕES EXPANDIDAS v3.0 ===
    INTENCOES = [
        # Intenções principais
        "analisar_disponibilidade",       # Geral: quando posso enviar?
        "consultar_pedidos_abertos",      # Do que tem em aberto, dá pra mandar?
        "quando_posso_enviar",            # Quando posso enviar pedido X?
        "verificar_disponibilidade",

        # v3.0: Intenções para DATA de disponibilidade
        "disponibilidade_por_data",       # O que terá estoque no dia X?
        "produtos_disponiveis_data",      # Quais produtos estarão disponíveis?
        "estoque_futuro",                 # Quando terá estoque?
        "previsao_estoque",               # Previsão de estoque
        "analisar_estoque_cliente",       # v3.0: Claude usa esta intenção frequentemente!

        # v3.0: Intenções para montagem de carga
        "montar_carga",                   # Quero montar uma carga
        "quero_montar_carga",             # Monta uma carga de X pallets
        "sugerir_carga",                  # Sugira uma carga

        # v3.0: Intenções por produto
        "disponibilidade_produto",        # Quando o produto X estará disponível?
        "quando_tera_estoque",            # Quando terá estoque de X?
        "consultar_estoque_produto",      # v3.0: Estoque de um produto específico

        # v3.0: Intenções por UF
        "disponibilidade_por_uf",         # O que tem pra mandar pro RS?
        "pedidos_por_estado",             # Pedidos disponíveis para MG

        # Intenções existentes
        "consultar_prazo",
        "prazo_envio",
        "analisar_pedidos_abertos",
        "pedidos_disponiveis",
        "o_que_da_pra_mandar",
        "quais_pedidos_posso_enviar",
        "maior_pedido_disponivel",        # Qual o maior pedido disponível?
        "valor_disponivel_cliente",       # Quanto tem disponível do cliente X?
    ]

    # === CAMPOS DE BUSCA EXPANDIDOS v3.0 ===
    CAMPOS_BUSCA = [
        "num_pedido",
        "raz_social_red",
        "cliente",
        # v3.0: Novos campos
        "cod_produto",
        "produto",
        "cod_uf",
        "estado",
        "uf",
        "vendedor",
        "rota",
        "data_disponibilidade",  # Para consultas "no dia X"
        "data",
        "expedicao",
    ]

    DESCRICAO = "Analisa quando pedidos/produtos podem ser enviados baseado no estoque e projeção"

    EXEMPLOS = [
        # Originais
        "Quando posso enviar o pedido VCD123?",
        "Quando embarcar VCD456?",
        "Quando dá pra enviar 28 pallets pro Atacadão 183?",
        "Posso despachar o VCD111 hoje?",
        "Do que tem em aberto, dá pra mandar algum?",
        "Quais pedidos do Atacadão dá pra enviar hoje?",
        "O que está disponível pra mandar?",
        "Qual o maior pedido que dá pra mandar?",
        # v3.0: Novos exemplos críticos
        "Quais produtos do Atacadão 183 terão estoque no dia 01/12?",
        "O que vai ter disponível pro Assaí na semana que vem?",
        "Quando a azeitona verde estará disponível?",
        "O que tem pra mandar pro RS?",
        "Pedidos do MG acima de R$ 10.000?",
        "Monta uma carga de 30 pallets pro Carrefour",
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """
        Verifica se deve processar - v3.0 mais abrangente.

        Aceita se:
        1. Intenção está na lista de INTENCOES
        2. Palavras-chave de disponibilidade + pelo menos uma entidade válida
        3. Consulta sobre data futura + cliente/produto
        """
        # 1. Intenção direta
        if intencao in self.INTENCOES:
            return True

        intencao_lower = intencao.lower()

        # 2. Palavras-chave expandidas
        palavras_disponibilidade = [
            'quando', 'prazo', 'disponib', 'enviar', 'embarcar', 'despachar',
            'mandar', 'maior', 'posso enviar', 'dá pra', 'da pra',
            # v3.0: Novas palavras
            'estoque', 'terá', 'tera', 'previsao', 'previsão',
            'montar carga', 'carga de', 'pallets pro', 'pallets para',
            'disponivel', 'disponível', 'aberto',
        ]

        tem_palavra_chave = any(p in intencao_lower for p in palavras_disponibilidade)

        if tem_palavra_chave:
            # Verifica se tem pelo menos uma entidade válida
            valores = self.extrair_todos_valores_busca(entidades)
            if valores:
                return True

            # v3.0: Aceita também se tem data/quantidade sem cliente específico
            # Ex: "O que terá estoque amanhã?" (consulta geral)
            if entidades.get('data') or entidades.get('data_disponibilidade') or entidades.get('quantidade'):
                return True

        return False

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """
        Executa análise de disponibilidade - v3.0 com roteamento inteligente.

        Detecta automaticamente o tipo de consulta:
        - Por num_pedido: Opções A/B/C para o pedido
        - Por cliente + data: Produtos disponíveis na data
        - Por cliente + pallets: Monta carga sugerida
        - Por cliente: Pedidos em aberto que podem ser enviados
        - Por produto: Quando o produto estará disponível
        - Por UF: Pedidos/produtos disponíveis para a UF
        """
        from app.separacao.models import Separacao
        from app.carteira.models import CarteiraPrincipal
        from app.producao.models import CadastroPalletizacao
        from app.claude_ai_lite.domains.carteira.services.opcoes_envio import OpcoesEnvioService

        # Extrai todos os valores de busca
        valores_busca = self.extrair_todos_valores_busca(entidades)

        # Resultado base
        resultado = {
            "sucesso": True,
            "valor_buscado": None,
            "campo_busca": None,
            "total_encontrado": 0,
            "dados": [],
            "analise": {},
            "opcoes": [],
            "tipo_consulta": None,
        }

        # Extrai parâmetros especiais
        qtd_pallets_desejada = entidades.get('quantidade') or entidades.get('qtd_saldo')
        data_alvo = self._extrair_data(entidades)
        intencao = str(entidades.get('_intencao', contexto.get('intencao', ''))).lower()
        consulta_original = str(contexto.get('consulta', '')).lower()

        # Extrai filtros de status
        status_sep = str(entidades.get('status_separacao', '')).lower()
        filtro_add = str(entidades.get('filtro_adicional', '')).lower()
        excluir_separados = 'separad' in status_sep or 'separad' in filtro_add

        # Detecta tipo de consulta
        quer_pedidos_abertos = self._detectar_pedidos_abertos(intencao, entidades, consulta_original)
        quer_por_data = data_alvo is not None and data_alvo > date.today()

        logger.info(
            f"[ANALISAR_DISP] valores={valores_busca}, pallets={qtd_pallets_desejada}, "
            f"data={data_alvo}, abertos={quer_pedidos_abertos}, por_data={quer_por_data}"
        )

        try:
            # === ROTEAMENTO INTELIGENTE ===

            # CASO 0: Consulta por DATA futura (v3.0 - NOVO!)
            # "Quais produtos do Atacadão terão estoque no dia 01/12?"
            if quer_por_data:
                cliente = valores_busca.get('raz_social_red') or valores_busca.get('cliente')
                if cliente:
                    resultado["tipo_consulta"] = "disponibilidade_por_data"
                    return self._analisar_disponibilidade_por_data(
                        cliente, data_alvo, valores_busca, resultado, entidades
                    )
                else:
                    # Data sem cliente - análise geral
                    resultado["tipo_consulta"] = "disponibilidade_geral_por_data"
                    return self._analisar_geral_por_data(data_alvo, valores_busca, resultado, entidades)

            # CASO 1: Consulta de pedidos em aberto do cliente
            cliente = valores_busca.get('raz_social_red') or valores_busca.get('cliente')
            if quer_pedidos_abertos and cliente:
                resultado["tipo_consulta"] = "pedidos_abertos_disponibilidade"
                return self._analisar_pedidos_em_aberto(cliente, resultado, entidades)

            # CASO 2: Busca por CLIENTE com quantidade específica de pallets
            if cliente and qtd_pallets_desejada:
                resultado["tipo_consulta"] = "carga_sugerida"
                return self._analisar_por_cliente(
                    cliente, float(qtd_pallets_desejada), excluir_separados, resultado, entidades
                )

            # CASO 3: Busca por CLIENTE (sem quantidade)
            if cliente and not valores_busca.get('num_pedido'):
                resultado["tipo_consulta"] = "analise_cliente"
                return self._analisar_por_cliente(
                    cliente, None, excluir_separados, resultado, entidades
                )

            # CASO 4: Busca por NUM_PEDIDO (comportamento original)
            num_pedido = valores_busca.get('num_pedido')
            if num_pedido:
                resultado["tipo_consulta"] = "opcoes_pedido"
                return self._analisar_por_pedido(num_pedido, resultado, entidades)

            # CASO 5: Busca por PRODUTO
            produto = valores_busca.get('cod_produto') or valores_busca.get('produto')
            if produto:
                resultado["tipo_consulta"] = "disponibilidade_produto"
                return self._analisar_por_produto(produto, valores_busca, resultado, entidades)

            # CASO 6: Busca por UF
            uf = valores_busca.get('cod_uf') or valores_busca.get('estado') or valores_busca.get('uf')
            if uf:
                resultado["tipo_consulta"] = "disponibilidade_uf"
                return self._analisar_por_uf(uf, valores_busca, resultado, entidades)

            # Fallback: Sem informações suficientes
            resultado["sucesso"] = False
            resultado["erro"] = "Informe um cliente, pedido, produto ou UF para análise"
            return resultado

        except Exception as e:
            logger.error(f"Erro na análise de disponibilidade: {e}", exc_info=True)
            resultado["sucesso"] = False
            resultado["erro"] = str(e)
            return resultado

    def _extrair_data(self, entidades: Dict) -> Optional[date]:
        """
        Extrai data das entidades - v3.0.

        Aceita formatos:
        - data_disponibilidade: "2025-12-01"
        - data: "01/12/2025" ou "2025-12-01"
        - expedicao: "2025-12-01"
        """
        for campo in ['data_disponibilidade', 'data', 'expedicao']:
            valor = entidades.get(campo)
            if not valor:
                continue

            if isinstance(valor, date):
                return valor

            if isinstance(valor, str):
                try:
                    # Formato ISO
                    if '-' in valor and len(valor) == 10:
                        return datetime.strptime(valor, '%Y-%m-%d').date()
                    # Formato BR
                    if '/' in valor:
                        return datetime.strptime(valor, '%d/%m/%Y').date()
                except ValueError:
                    pass

        return None

    def _detectar_pedidos_abertos(self, intencao: str, entidades: Dict, consulta: str) -> bool:
        """Detecta se a consulta é sobre pedidos em aberto."""
        # Intenções específicas
        intencoes_pedidos_abertos = [
            'consultar_pedidos_abertos',
            'analisar_pedidos_abertos',
            'pedidos_disponiveis',
            'o_que_da_pra_mandar',
            'quais_pedidos_posso_enviar',
        ]

        if intencao in intencoes_pedidos_abertos:
            return True

        # Flag explícita
        if entidades.get('analisar_disponibilidade_pedidos'):
            return True

        # Palavras-chave na consulta
        palavras = [
            'em aberto', 'pedidos abertos', 'dá pra mandar',
            'pode mandar', 'disponível pra', 'disponíveis pra',
            'o que tem', 'o que da', 'o que dá',
        ]
        return any(p in consulta for p in palavras)

    def _analisar_disponibilidade_por_data(
        self,
        cliente: str,
        data_alvo: date,
        valores_busca: Dict,
        resultado: Dict,
        entidades: Dict
    ) -> Dict[str, Any]:
        """
        v3.0: Analisa produtos que TERÃO estoque em uma data futura.

        Responde: "Quais produtos do Atacadão 183 terão estoque no dia 01/12?"

        Lógica:
        1. Busca itens da carteira do cliente
        2. Para cada item, verifica projeção de estoque até a data alvo
        3. Classifica: disponível hoje / disponível na data / sem previsão
        """
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from app.producao.models import CadastroPalletizacao
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        logger.info(f"[DISP_DATA] Analisando {cliente} para data {data_alvo}")

        # 1. Buscar itens da carteira do cliente
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.raz_social_red.ilike(f"%{cliente}%"),
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001
        ).all()

        if not itens_carteira:
            resultado["sucesso"] = False
            resultado["erro"] = f"Cliente '{cliente}' não encontrado na carteira"
            return resultado

        # 2. Buscar separações pendentes
        pedidos_cliente = list(set([i.num_pedido for i in itens_carteira]))
        separacoes_pendentes = Separacao.query.filter(
            Separacao.num_pedido.in_(pedidos_cliente),
            Separacao.sincronizado_nf == False,
            Separacao.status != 'PREVISAO'
        ).all()

        qtd_separada = {}
        for sep in separacoes_pendentes:
            key = (sep.num_pedido, sep.cod_produto)
            qtd_separada[key] = qtd_separada.get(key, 0) + float(sep.qtd_saldo or 0)

        # 3. Carregar cache de palletização
        cache_pallet = self._carregar_cache_palletizacao()

        # 4. Calcular dias até a data alvo
        dias_ate_data = (data_alvo - date.today()).days

        # 5. Analisar cada item
        itens_analisados = []
        produtos_unicos = set()

        for item in itens_carteira:
            key_sep = (item.num_pedido, item.cod_produto)
            qtd_carteira = float(item.qtd_saldo_produto_pedido or 0)
            qtd_ja_separada = qtd_separada.get(key_sep, 0)
            saldo_real = qtd_carteira - qtd_ja_separada

            if saldo_real < 0.001:
                continue

            produtos_unicos.add(item.cod_produto)

            # Calcula peso e pallets
            pall_data = cache_pallet.get(item.cod_produto, {})
            peso_item = saldo_real * pall_data.get('peso_bruto', 0)
            pallets_item = saldo_real / pall_data['palletizacao'] if pall_data.get('palletizacao', 0) > 0 else 0
            valor_item = saldo_real * float(item.preco_produto_pedido or 0)

            itens_analisados.append({
                "num_pedido": item.num_pedido,
                "cod_produto": item.cod_produto,
                "nome_produto": item.nome_produto,
                "saldo_real": saldo_real,
                "valor": valor_item,
                "peso": peso_item,
                "pallets": pallets_item,
                "_item": item,  # Para processamento posterior
            })

        # 6. Verificar disponibilidade na data alvo
        disponiveis_hoje = []
        disponiveis_na_data = []
        sem_previsao = []

        for item in itens_analisados:
            cod = item["cod_produto"]
            saldo = item["saldo_real"]

            try:
                # Verifica estoque atual
                estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod)
                item["estoque_atual"] = estoque_atual

                if estoque_atual >= saldo:
                    item["status"] = "disponivel_hoje"
                    item["data_disponivel"] = date.today().strftime("%d/%m/%Y")
                    disponiveis_hoje.append(item)
                else:
                    # Verifica projeção
                    projecao = ServicoEstoqueSimples.calcular_projecao(cod, dias=max(dias_ate_data + 5, 30))
                    data_disp = self._encontrar_data_disponivel(projecao, saldo)

                    if data_disp and data_disp <= data_alvo:
                        item["status"] = "disponivel_na_data"
                        item["data_disponivel"] = data_disp.strftime("%d/%m/%Y")
                        disponiveis_na_data.append(item)
                    elif data_disp:
                        item["status"] = "disponivel_apos_data"
                        item["data_disponivel"] = data_disp.strftime("%d/%m/%Y")
                        sem_previsao.append(item)
                    else:
                        item["status"] = "sem_previsao"
                        item["data_disponivel"] = "Sem previsão"
                        sem_previsao.append(item)

            except Exception as e:
                logger.warning(f"Erro ao verificar estoque de {cod}: {e}")
                item["status"] = "erro"
                item["data_disponivel"] = "Erro"
                item["estoque_atual"] = 0
                sem_previsao.append(item)

        # 7. Remove campo temporário
        for item in itens_analisados:
            item.pop('_item', None)

        # 8. Monta resultado ordenado
        todos_itens = disponiveis_hoje + disponiveis_na_data + sem_previsao

        resultado["sucesso"] = True
        resultado["cliente"] = cliente
        resultado["data_alvo"] = data_alvo.strftime("%d/%m/%Y")
        resultado["dados"] = todos_itens
        resultado["total_encontrado"] = len(todos_itens)

        # Totais por categoria
        valor_disp_hoje = sum(i["valor"] for i in disponiveis_hoje)
        valor_disp_data = sum(i["valor"] for i in disponiveis_na_data)
        pallets_disp_hoje = sum(i["pallets"] for i in disponiveis_hoje)
        pallets_disp_data = sum(i["pallets"] for i in disponiveis_na_data)

        resultado["analise"] = {
            "cliente": cliente,
            "data_alvo": data_alvo.strftime("%d/%m/%Y"),
            "dias_ate_data": dias_ate_data,
            "total_itens": len(todos_itens),
            "disponiveis_hoje": len(disponiveis_hoje),
            "disponiveis_na_data": len(disponiveis_na_data),
            "sem_previsao": len(sem_previsao),
            "valor_disponivel_hoje": round(valor_disp_hoje, 2),
            "valor_disponivel_na_data": round(valor_disp_hoje + valor_disp_data, 2),
            "pallets_disponiveis_hoje": round(pallets_disp_hoje, 2),
            "pallets_disponiveis_na_data": round(pallets_disp_hoje + pallets_disp_data, 2),
        }

        logger.info(
            f"[DISP_DATA] {cliente} para {data_alvo}: "
            f"{len(disponiveis_hoje)} hoje, {len(disponiveis_na_data)} na data, "
            f"{len(sem_previsao)} sem previsão"
        )

        return resultado

    def _analisar_geral_por_data(
        self,
        data_alvo: date,
        valores_busca: Dict,
        resultado: Dict,
        entidades: Dict
    ) -> Dict[str, Any]:
        """
        v3.0: Análise geral de disponibilidade por data (sem cliente específico).

        Para consultas como: "O que vai ter disponível amanhã?"
        """
        # Por enquanto, retorna erro pedindo cliente
        # TODO: Implementar análise geral se necessário
        resultado["sucesso"] = False
        resultado["erro"] = f"Para consultar disponibilidade no dia {data_alvo.strftime('%d/%m')}, informe o cliente."
        resultado["ambiguidade"] = {
            "existe": True,
            "tipo_faltante": "cliente",
            "pergunta": f"De qual cliente você quer verificar a disponibilidade para {data_alvo.strftime('%d/%m/%Y')}?",
        }
        return resultado

    def _analisar_por_produto(
        self,
        produto: str,
        valores_busca: Dict,
        resultado: Dict,
        entidades: Dict
    ) -> Dict[str, Any]:
        """
        v3.0: Analisa disponibilidade de um produto específico.

        Responde: "Quando a azeitona verde estará disponível?"
        """
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        from app.producao.models import CadastroPalletizacao
        from app.carteira.models import CarteiraPrincipal

        logger.info(f"[DISP_PRODUTO] Analisando produto: {produto}")

        # Busca produto no cadastro
        produto_info = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.cod_produto.ilike(f"%{produto}%") |
            CadastroPalletizacao.nome_produto.ilike(f"%{produto}%")
        ).first()

        if not produto_info:
            resultado["sucesso"] = False
            resultado["erro"] = f"Produto '{produto}' não encontrado no cadastro"
            return resultado

        cod_produto = produto_info.cod_produto

        try:
            # Estoque atual
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

            # Projeção 30 dias
            projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=30)

            # Demanda na carteira
            demanda_carteira = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).with_entities(
                CarteiraPrincipal.raz_social_red,
                CarteiraPrincipal.num_pedido,
                CarteiraPrincipal.qtd_saldo_produto_pedido
            ).all()

            total_demanda = sum(d.qtd_saldo_produto_pedido for d in demanda_carteira)

            resultado["sucesso"] = True
            resultado["cod_produto"] = cod_produto
            resultado["nome_produto"] = produto_info.nome_produto
            resultado["estoque_atual"] = estoque_atual
            resultado["total_demanda_carteira"] = float(total_demanda)
            resultado["projecao"] = projecao.get("projecao", [])[:10]
            resultado["total_encontrado"] = len(demanda_carteira)

            # Clientes que precisam desse produto
            resultado["dados"] = [
                {
                    "cliente": d.raz_social_red,
                    "num_pedido": d.num_pedido,
                    "quantidade": float(d.qtd_saldo_produto_pedido),
                    "pode_atender": estoque_atual >= float(d.qtd_saldo_produto_pedido),
                }
                for d in demanda_carteira[:20]
            ]

            # Análise resumida
            pode_atender_todos = estoque_atual >= total_demanda
            resultado["analise"] = {
                "produto": produto_info.nome_produto,
                "cod_produto": cod_produto,
                "estoque_atual": estoque_atual,
                "total_demanda": float(total_demanda),
                "saldo_livre": estoque_atual - float(total_demanda),
                "pode_atender_todos": pode_atender_todos,
                "clientes_aguardando": len(demanda_carteira),
            }

        except Exception as e:
            logger.error(f"Erro ao analisar produto {produto}: {e}")
            resultado["sucesso"] = False
            resultado["erro"] = str(e)

        return resultado

    def _analisar_por_uf(
        self,
        uf: str,
        valores_busca: Dict,
        resultado: Dict,
        entidades: Dict
    ) -> Dict[str, Any]:
        """
        v3.0: Analisa pedidos disponíveis para uma UF.

        Responde: "O que tem pra mandar pro RS?"
        """
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        uf = uf.upper()[:2]
        logger.info(f"[DISP_UF] Analisando UF: {uf}")

        # Busca itens da carteira para a UF
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_uf == uf,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001
        ).all()

        if not itens_carteira:
            resultado["sucesso"] = False
            resultado["erro"] = f"Nenhum item na carteira para UF '{uf}'"
            return resultado

        # Agrupa por pedido
        pedidos = {}
        for item in itens_carteira:
            if item.num_pedido not in pedidos:
                pedidos[item.num_pedido] = {
                    "num_pedido": item.num_pedido,
                    "cliente": item.raz_social_red,
                    "cidade": item.nome_cidade,
                    "uf": uf,
                    "itens": [],
                    "valor_total": 0,
                    "peso_total": 0,
                }

            pedidos[item.num_pedido]["itens"].append({
                "cod_produto": item.cod_produto,
                "nome_produto": item.nome_produto,
                "quantidade": float(item.qtd_saldo_produto_pedido),
            })
            pedidos[item.num_pedido]["valor_total"] += float(item.preco_produto_pedido or 0) * float(item.qtd_saldo_produto_pedido)

        # Verifica disponibilidade de cada pedido
        cache_pallet = self._carregar_cache_palletizacao()
        pedidos_disponiveis = []
        pedidos_parciais = []

        for num_pedido, dados in pedidos.items():
            todos_disponiveis = True
            itens_disponiveis = 0

            for item in dados["itens"]:
                try:
                    estoque = ServicoEstoqueSimples.calcular_estoque_atual(item["cod_produto"])
                    item["estoque"] = estoque
                    item["disponivel"] = estoque >= item["quantidade"]

                    if item["disponivel"]:
                        itens_disponiveis += 1
                    else:
                        todos_disponiveis = False
                except Exception:
                    item["estoque"] = 0
                    item["disponivel"] = False
                    todos_disponiveis = False

            dados["todos_disponiveis"] = todos_disponiveis
            dados["itens_disponiveis"] = itens_disponiveis
            dados["total_itens"] = len(dados["itens"])

            if todos_disponiveis:
                pedidos_disponiveis.append(dados)
            else:
                pedidos_parciais.append(dados)

        # Ordena por valor
        pedidos_disponiveis.sort(key=lambda p: -p["valor_total"])
        pedidos_parciais.sort(key=lambda p: -p["valor_total"])

        todos_pedidos = pedidos_disponiveis + pedidos_parciais

        resultado["sucesso"] = True
        resultado["uf"] = uf
        resultado["dados"] = todos_pedidos[:20]
        resultado["total_encontrado"] = len(todos_pedidos)

        resultado["analise"] = {
            "uf": uf,
            "total_pedidos": len(todos_pedidos),
            "pedidos_disponiveis": len(pedidos_disponiveis),
            "pedidos_parciais": len(pedidos_parciais),
            "valor_total": sum(p["valor_total"] for p in todos_pedidos),
            "valor_disponivel": sum(p["valor_total"] for p in pedidos_disponiveis),
        }

        return resultado

    def _analisar_por_pedido(
        self,
        num_pedido: str,
        resultado: Dict,
        entidades: Dict
    ) -> Dict[str, Any]:
        """Análise por número de pedido - gera opções A/B/C."""
        from app.separacao.models import Separacao
        from app.claude_ai_lite.domains.carteira.services.opcoes_envio import OpcoesEnvioService

        # Verifica se já está separado
        itens_sep = Separacao.query.filter(
            Separacao.num_pedido.like(f"%{num_pedido}%"),
            Separacao.sincronizado_nf == False
        ).all()

        # Usa o serviço de opções existente
        analise = OpcoesEnvioService.analisar_pedido(num_pedido)

        if not analise["sucesso"]:
            if itens_sep:
                return self._responder_pedido_ja_separado(num_pedido, itens_sep, resultado)
            resultado["sucesso"] = False
            resultado["erro"] = analise.get("erro", "Pedido não encontrado")
            return resultado

        resultado["num_pedido"] = analise["num_pedido"]
        resultado["cliente"] = analise["cliente"]
        resultado["valor_total_pedido"] = analise["valor_total_pedido"]
        resultado["opcoes"] = analise["opcoes"]
        resultado["total_encontrado"] = len(analise["opcoes"])

        resultado["analise"] = {
            "num_pedido": analise["num_pedido"],
            "cliente": analise["cliente"]["razao_social"] if analise["cliente"] else None,
            "valor_total": analise["valor_total_pedido"],
            "qtd_opcoes": len(analise["opcoes"]),
            "todos_disponiveis_hoje": analise["opcoes"][0]["disponivel_hoje"] if analise["opcoes"] else False
        }

        resultado["dados"] = analise.get("itens_analisados", analise.get("itens", []))

        return resultado

    def _analisar_por_cliente(
        self, cliente: str, qtd_pallets_desejada: Optional[float],
        excluir_separados: bool, resultado: Dict, entidades: Dict
    ) -> Dict[str, Any]:
        """Analisa disponibilidade por CLIENTE."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples

        logger.info(f"[ANALISAR_DISP] Buscando por cliente: {cliente}, pallets desejados: {qtd_pallets_desejada}")

        # 1. Buscar itens do cliente na carteira
        query = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.raz_social_red.ilike(f"%{cliente}%"),
            CarteiraPrincipal.ativo == True
        )

        # 2. Excluir itens já separados se solicitado
        separados_set = set()
        if excluir_separados:
            pedidos_separados = Separacao.query.filter(
                Separacao.raz_social_red.ilike(f"%{cliente}%"),
                Separacao.sincronizado_nf == False
            ).with_entities(Separacao.num_pedido, Separacao.cod_produto).all()
            separados_set = {(s.num_pedido, s.cod_produto) for s in pedidos_separados}
            logger.info(f"[ANALISAR_DISP] {len(separados_set)} itens já separados excluídos")

        itens_carteira = query.all()

        if not itens_carteira:
            resultado["sucesso"] = False
            resultado["erro"] = f"Cliente '{cliente}' não encontrado na carteira"
            return resultado

        # 3. Carregar cache de palletização
        cache_pallet = self._carregar_cache_palletizacao()

        # 4. Calcular pallets para cada item
        itens_analisados = []
        total_pallets_disponiveis = 0.0
        total_peso = 0.0

        for item in itens_carteira:
            if excluir_separados and (item.num_pedido, item.cod_produto) in separados_set:
                continue

            quantidade = float(item.qtd_saldo_produto_pedido or 0)
            if quantidade <= 0:
                continue

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

        # 5. Ordenar por disponibilidade
        itens_analisados.sort(key=lambda x: (not x['disponivel_hoje'], -x['pallets']))

        # 6. Montar resultado
        resultado["sucesso"] = True
        resultado["cliente"] = cliente
        resultado["total_pallets"] = round(total_pallets_disponiveis, 2)
        resultado["total_peso"] = round(total_peso, 2)
        resultado["total_itens"] = len(itens_analisados)
        resultado["total_encontrado"] = len(itens_analisados)
        resultado["dados"] = itens_analisados

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
            carga_sugerida = self._montar_carga_sugerida(itens_analisados, qtd_pallets_desejada)
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

    def _analisar_pedidos_em_aberto(
        self, cliente: str, resultado: Dict, entidades: Dict
    ) -> Dict[str, Any]:
        """Analisa pedidos EM ABERTO de um cliente."""
        from app.carteira.models import CarteiraPrincipal
        from app.separacao.models import Separacao
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        from sqlalchemy import func

        logger.info(f"[PEDIDOS_ABERTOS] Analisando pedidos em aberto do cliente: {cliente}")

        # 1. Buscar itens da carteira do cliente
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.raz_social_red.ilike(f"%{cliente}%"),
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001
        ).all()

        if not itens_carteira:
            resultado["sucesso"] = False
            resultado["erro"] = f"Cliente '{cliente}' não encontrado na carteira"
            return resultado

        # 2. Buscar separações pendentes
        pedidos_cliente = list(set([i.num_pedido for i in itens_carteira]))
        separacoes_pendentes = Separacao.query.filter(
            Separacao.num_pedido.in_(pedidos_cliente),
            Separacao.sincronizado_nf == False,
            Separacao.status != 'PREVISAO'
        ).all()

        qtd_separada = {}
        for sep in separacoes_pendentes:
            key = (sep.num_pedido, sep.cod_produto)
            qtd_separada[key] = qtd_separada.get(key, 0) + float(sep.qtd_saldo or 0)

        # 3. Cache de palletização
        cache_pallet = self._carregar_cache_palletizacao()

        # 4. Calcular saldo real e agrupar por pedido
        pedidos_abertos = {}
        produtos_unicos = set()

        for item in itens_carteira:
            key_sep = (item.num_pedido, item.cod_produto)
            qtd_carteira = float(item.qtd_saldo_produto_pedido or 0)
            qtd_ja_separada = qtd_separada.get(key_sep, 0)
            saldo_real = qtd_carteira - qtd_ja_separada

            if saldo_real < 0.001:
                continue

            produtos_unicos.add(item.cod_produto)

            if item.num_pedido not in pedidos_abertos:
                pedidos_abertos[item.num_pedido] = {
                    "num_pedido": item.num_pedido,
                    "raz_social_red": item.raz_social_red,
                    "cnpj_cpf": item.cnpj_cpf,
                    "data_pedido": item.data_pedido.strftime("%d/%m/%Y") if item.data_pedido else None,
                    "itens": [],
                    "valor_total": 0,
                    "peso_total": 0,
                    "pallets_total": 0,
                }

            preco = float(item.preco_produto_pedido or 0)
            valor_item = saldo_real * preco
            pall_data = cache_pallet.get(item.cod_produto, {})
            peso_item = saldo_real * pall_data.get('peso_bruto', 0)
            pallets_item = saldo_real / pall_data['palletizacao'] if pall_data.get('palletizacao', 0) > 0 else 0

            pedidos_abertos[item.num_pedido]["itens"].append({
                "cod_produto": item.cod_produto,
                "nome_produto": item.nome_produto,
                "qtd_carteira": qtd_carteira,
                "qtd_separada": qtd_ja_separada,
                "saldo_real": saldo_real,
                "preco_unitario": preco,
                "valor_item": valor_item,
                "peso": peso_item,
                "pallets": pallets_item,
            })
            pedidos_abertos[item.num_pedido]["valor_total"] += valor_item
            pedidos_abertos[item.num_pedido]["peso_total"] += peso_item
            pedidos_abertos[item.num_pedido]["pallets_total"] += pallets_item

        if not pedidos_abertos:
            resultado["sucesso"] = True
            resultado["total_encontrado"] = 0
            resultado["mensagem"] = f"Todos os pedidos de {cliente} já estão em separação ou faturados"
            return resultado

        # 5. Buscar estoque em batch
        estoque_por_produto = {}
        for cod_produto in produtos_unicos:
            try:
                estoque = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
                estoque_por_produto[cod_produto] = estoque
            except Exception as e:
                logger.warning(f"Erro ao buscar estoque de {cod_produto}: {e}")
                estoque_por_produto[cod_produto] = 0

        # 6. Analisar disponibilidade de cada pedido
        for num_pedido, pedido in pedidos_abertos.items():
            todos_disponiveis = True
            itens_disponiveis = 0
            itens_indisponiveis = 0
            gargalos = []
            data_disponibilidade_total = date.today()

            for item in pedido["itens"]:
                cod = item["cod_produto"]
                estoque = estoque_por_produto.get(cod, 0)
                saldo = item["saldo_real"]

                item["estoque_atual"] = estoque
                item["disponivel"] = estoque >= saldo

                if item["disponivel"]:
                    itens_disponiveis += 1
                    item["data_disponivel"] = date.today().strftime("%d/%m/%Y")
                else:
                    itens_indisponiveis += 1
                    todos_disponiveis = False

                    try:
                        projecao = ServicoEstoqueSimples.calcular_projecao(cod, dias=30)
                        data_disp = self._encontrar_data_disponivel(projecao, saldo)
                        item["data_disponivel"] = data_disp.strftime("%d/%m/%Y") if data_disp else "Sem previsão"

                        if data_disp and data_disp > data_disponibilidade_total: # type: ignore
                            data_disponibilidade_total = data_disp
                        elif not data_disp:
                            data_disponibilidade_total = None
                    except Exception:
                        item["data_disponivel"] = "Sem previsão"
                        data_disponibilidade_total = None

                    gargalos.append({
                        "cod_produto": cod,
                        "nome_produto": item["nome_produto"],
                        "falta": saldo - estoque,
                        "data_disponivel": item["data_disponivel"]
                    })

            pedido["todos_disponiveis"] = todos_disponiveis
            pedido["itens_disponiveis"] = itens_disponiveis
            pedido["itens_indisponiveis"] = itens_indisponiveis
            pedido["total_itens"] = len(pedido["itens"])
            pedido["percentual_disponivel"] = round(
                (itens_disponiveis / len(pedido["itens"]) * 100) if pedido["itens"] else 0
            )

            if not todos_disponiveis:
                pedido["gargalos"] = gargalos
                pedido["data_disponibilidade_total"] = (
                    data_disponibilidade_total.strftime("%d/%m/%Y")
                    if data_disponibilidade_total else "Sem previsão"
                )

        # 7. Ordenar: Disponíveis primeiro, depois por valor
        pedidos_lista = list(pedidos_abertos.values())
        pedidos_lista.sort(key=lambda p: (-int(p["todos_disponiveis"]), -p["valor_total"]))

        # 8. Montar resumo
        total_pedidos = len(pedidos_lista)
        pedidos_disponiveis = sum(1 for p in pedidos_lista if p["todos_disponiveis"])
        valor_total = sum(p["valor_total"] for p in pedidos_lista)
        valor_disponivel = sum(p["valor_total"] for p in pedidos_lista if p["todos_disponiveis"])
        peso_total = sum(p["peso_total"] for p in pedidos_lista)
        pallets_total = sum(p["pallets_total"] for p in pedidos_lista)

        resultado["sucesso"] = True
        resultado["dados"] = pedidos_lista
        resultado["total_encontrado"] = total_pedidos
        resultado["resumo"] = {
            "cliente": cliente,
            "total_pedidos_abertos": total_pedidos,
            "pedidos_disponiveis": pedidos_disponiveis,
            "pedidos_parciais": total_pedidos - pedidos_disponiveis,
            "valor_total_aberto": round(valor_total, 2),
            "valor_disponivel": round(valor_disponivel, 2),
            "peso_total": round(peso_total, 2),
            "pallets_total": round(pallets_total, 2),
        }
        resultado["analise"] = resultado["resumo"]

        logger.info(
            f"[PEDIDOS_ABERTOS] {cliente}: {total_pedidos} pedidos em aberto, "
            f"{pedidos_disponiveis} disponíveis (R$ {valor_disponivel:,.2f})"
        )

        return resultado

    def _carregar_cache_palletizacao(self) -> Dict[str, Dict]:
        """Carrega cache de palletização."""
        from app.producao.models import CadastroPalletizacao

        cache = {}
        produtos = CadastroPalletizacao.query.filter_by(ativo=True).all()
        for p in produtos:
            cache[p.cod_produto] = {
                'palletizacao': float(p.palletizacao or 0),
                'peso_bruto': float(p.peso_bruto or 0)
            }
        return cache

    def _encontrar_data_disponivel(self, projecao: Dict, qtd: float) -> Optional[date]:
        """Encontra primeira data com estoque suficiente."""
        lista_projecao = projecao.get("projecao", [])

        for dia_proj in lista_projecao:
            estoque_dia = dia_proj.get("saldo_final", 0)
            if estoque_dia >= qtd:
                data_str = dia_proj.get("data")
                if data_str:
                    return date.fromisoformat(data_str)

        return None

    def _montar_carga_sugerida(
        self, itens_analisados: List[Dict], qtd_pallets_desejada: float
    ) -> Dict[str, Any]:
        """Monta uma carga sugerida com a quantidade de pallets desejada."""
        carga = {
            "pode_montar": False,
            "total_pallets": 0.0,
            "total_peso": 0.0,
            "total_valor": 0.0,
            "itens": [],
            "todos_disponiveis_hoje": True,
            "itens_aguardar": 0
        }

        if not itens_analisados or qtd_pallets_desejada <= 0:
            return carga

        cache_pallet = self._carregar_cache_palletizacao()

        pallets_acumulados = 0.0
        peso_acumulado = 0.0
        valor_acumulado = 0.0
        itens_selecionados = []
        itens_sem_estoque = 0

        pallets_faltando = qtd_pallets_desejada

        for item in itens_analisados:
            if pallets_faltando <= 0:
                break

            pallets_item = item["pallets"]
            quantidade_item = item["quantidade"]

            pallet_info = cache_pallet.get(item["cod_produto"], {})
            palletizacao = pallet_info.get('palletizacao', 0)
            peso_bruto = pallet_info.get('peso_bruto', 0)

            if pallets_item > pallets_faltando and palletizacao > 0:
                # Fraciona item
                quantidade_necessaria = pallets_faltando * palletizacao
                pallets_usar = pallets_faltando
                peso_usar = quantidade_necessaria * peso_bruto
                valor_unitario = item["valor"] / quantidade_item if quantidade_item > 0 else 0
                valor_usar = quantidade_necessaria * valor_unitario

                itens_selecionados.append({
                    "num_pedido": item["num_pedido"],
                    "cod_produto": item["cod_produto"],
                    "nome_produto": item["nome_produto"],
                    "quantidade": round(quantidade_necessaria, 2),
                    "quantidade_original": quantidade_item,
                    "pallets": round(pallets_usar, 2),
                    "peso": round(peso_usar, 2),
                    "valor": round(valor_usar, 2),
                    "disponivel_hoje": item["disponivel_hoje"],
                    "estoque_atual": item.get("estoque_atual", 0),
                    "fracionado": True,
                    "percentual_usado": round((quantidade_necessaria / quantidade_item) * 100, 1)
                })

                pallets_acumulados += pallets_usar
                peso_acumulado += peso_usar
                valor_acumulado += valor_usar
                pallets_faltando = 0

                if not item["disponivel_hoje"]:
                    itens_sem_estoque += 1

            else:
                # Item inteiro
                itens_selecionados.append({
                    "num_pedido": item["num_pedido"],
                    "cod_produto": item["cod_produto"],
                    "nome_produto": item["nome_produto"],
                    "quantidade": quantidade_item,
                    "pallets": pallets_item,
                    "peso": item["peso"],
                    "valor": item["valor"],
                    "disponivel_hoje": item["disponivel_hoje"],
                    "estoque_atual": item.get("estoque_atual", 0),
                    "fracionado": False
                })

                pallets_acumulados += pallets_item
                peso_acumulado += item["peso"]
                valor_acumulado += item["valor"]
                pallets_faltando -= pallets_item

                if not item["disponivel_hoje"]:
                    itens_sem_estoque += 1

        atingiu_meta = pallets_acumulados >= qtd_pallets_desejada * 0.95
        usou_todos = len(itens_selecionados) == len(itens_analisados)

        if itens_selecionados and (atingiu_meta or usou_todos):
            carga["pode_montar"] = True
            carga["total_pallets"] = round(pallets_acumulados, 2)
            carga["total_peso"] = round(peso_acumulado, 2)
            carga["total_valor"] = round(valor_acumulado, 2)
            carga["itens"] = itens_selecionados
            carga["todos_disponiveis_hoje"] = itens_sem_estoque == 0
            carga["itens_aguardar"] = itens_sem_estoque
            carga["atingiu_meta_exata"] = atingiu_meta

        return carga

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

    # ==========================================================================
    # FORMATAÇÃO DE CONTEXTO
    # ==========================================================================

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Formata dados para contexto do Claude."""
        if not resultado.get("sucesso"):
            return f"Erro: {resultado.get('erro')}"

        if resultado["total_encontrado"] == 0:
            return resultado.get("mensagem", "Nenhum resultado encontrado.")

        tipo = resultado.get("tipo_consulta", "")

        # Roteamento de formatação
        if resultado.get("ja_separado"):
            return self._formatar_ja_separado(resultado)

        if tipo == "disponibilidade_por_data":
            return self._formatar_disponibilidade_por_data(resultado)

        if tipo == "pedidos_abertos_disponibilidade":
            return self._formatar_pedidos_abertos(resultado)

        if tipo == "disponibilidade_produto":
            return self._formatar_disponibilidade_produto(resultado)

        if tipo == "disponibilidade_uf":
            return self._formatar_disponibilidade_uf(resultado)

        if resultado.get("total_pallets") is not None:
            return self._formatar_analise_cliente(resultado)

        if resultado.get("opcoes"):
            return self._formatar_opcoes(resultado)

        # Fallback genérico
        return self._formatar_generico(resultado)

    def _formatar_disponibilidade_por_data(self, dados: Dict) -> str:
        """v3.0: Formata resultado de disponibilidade por data futura."""
        a = dados.get("analise", {})
        itens = dados.get("dados", [])

        linhas = [
            f"=== DISPONIBILIDADE PARA {a.get('data_alvo', 'N/A')} ===",
            f"Cliente: {a.get('cliente', 'N/A')}",
            f"Dias até a data: {a.get('dias_ate_data', 0)}",
            "",
            f"📊 RESUMO:",
            f"   Total de itens: {a.get('total_itens', 0)}",
            f"   ✅ Disponíveis HOJE: {a.get('disponiveis_hoje', 0)}",
            f"   📅 Disponíveis até {a.get('data_alvo', 'N/A')}: {a.get('disponiveis_na_data', 0)}",
            f"   ❌ Sem previsão: {a.get('sem_previsao', 0)}",
            "",
            f"💰 VALORES:",
            f"   Valor disponível hoje: R$ {a.get('valor_disponivel_hoje', 0):,.2f}",
            f"   Valor disponível na data: R$ {a.get('valor_disponivel_na_data', 0):,.2f}",
            f"   Pallets disponíveis hoje: {a.get('pallets_disponiveis_hoje', 0):.1f}",
            f"   Pallets disponíveis na data: {a.get('pallets_disponiveis_na_data', 0):.1f}",
            "",
            "=" * 60,
            ""
        ]

        # Agrupa por status
        disponiveis_hoje = [i for i in itens if i.get('status') == 'disponivel_hoje']
        disponiveis_na_data = [i for i in itens if i.get('status') == 'disponivel_na_data']
        outros = [i for i in itens if i.get('status') not in ('disponivel_hoje', 'disponivel_na_data')]

        if disponiveis_hoje:
            linhas.append("✅ DISPONÍVEIS HOJE:")
            for i, item in enumerate(disponiveis_hoje[:10], 1):
                linhas.append(
                    f"  {i}. {item['nome_produto'][:40]} | "
                    f"Pedido: {item['num_pedido']} | "
                    f"{item['saldo_real']:.0f}un = {item.get('pallets', 0):.2f} plt | "
                    f"R$ {item.get('valor', 0):,.2f}"
                )
            if len(disponiveis_hoje) > 10:
                linhas.append(f"  ... e mais {len(disponiveis_hoje) - 10} itens")
            linhas.append("")

        if disponiveis_na_data:
            linhas.append(f"📅 DISPONÍVEIS ATÉ {a.get('data_alvo', 'N/A')}:")
            for i, item in enumerate(disponiveis_na_data[:10], 1):
                linhas.append(
                    f"  {i}. {item['nome_produto'][:40]} | "
                    f"Pedido: {item['num_pedido']} | "
                    f"{item['saldo_real']:.0f}un | "
                    f"Previsão: {item.get('data_disponivel', 'N/A')}"
                )
            if len(disponiveis_na_data) > 10:
                linhas.append(f"  ... e mais {len(disponiveis_na_data) - 10} itens")
            linhas.append("")

        if outros:
            linhas.append("❌ SEM PREVISÃO ATÉ A DATA:")
            for i, item in enumerate(outros[:5], 1):
                linhas.append(
                    f"  {i}. {item['nome_produto'][:40]} | "
                    f"Pedido: {item['num_pedido']} | "
                    f"{item['saldo_real']:.0f}un | "
                    f"Previsão: {item.get('data_disponivel', 'N/A')}"
                )
            if len(outros) > 5:
                linhas.append(f"  ... e mais {len(outros) - 5} itens")

        return "\n".join(linhas)

    def _formatar_disponibilidade_produto(self, dados: Dict) -> str:
        """v3.0: Formata disponibilidade de um produto específico."""
        a = dados.get("analise", {})
        itens = dados.get("dados", [])

        linhas = [
            f"=== DISPONIBILIDADE DO PRODUTO ===",
            f"Produto: {a.get('produto', 'N/A')}",
            f"Código: {a.get('cod_produto', 'N/A')}",
            "",
            f"📦 ESTOQUE:",
            f"   Estoque atual: {a.get('estoque_atual', 0):,.0f} un",
            f"   Demanda na carteira: {a.get('total_demanda', 0):,.0f} un",
            f"   Saldo livre: {a.get('saldo_livre', 0):,.0f} un",
            "",
            f"📋 STATUS: {'✅ Pode atender toda demanda' if a.get('pode_atender_todos') else '⚠️ Não consegue atender toda demanda'}",
            f"   Clientes aguardando: {a.get('clientes_aguardando', 0)}",
            "",
            "--- CLIENTES QUE PRECISAM ---",
        ]

        for i, item in enumerate(itens[:15], 1):
            status = "✅" if item.get('pode_atender') else "❌"
            linhas.append(
                f"  {i}. [{status}] {item['cliente'][:30]} | "
                f"Pedido: {item['num_pedido']} | "
                f"{item['quantidade']:.0f}un"
            )

        if len(itens) > 15:
            linhas.append(f"  ... e mais {len(itens) - 15} clientes")

        return "\n".join(linhas)

    def _formatar_disponibilidade_uf(self, dados: Dict) -> str:
        """v3.0: Formata disponibilidade por UF."""
        a = dados.get("analise", {})
        pedidos = dados.get("dados", [])

        linhas = [
            f"=== PEDIDOS DISPONÍVEIS PARA {a.get('uf', 'N/A')} ===",
            "",
            f"📊 RESUMO:",
            f"   Total de pedidos: {a.get('total_pedidos', 0)}",
            f"   ✅ Disponíveis: {a.get('pedidos_disponiveis', 0)}",
            f"   ⚠️ Parciais: {a.get('pedidos_parciais', 0)}",
            "",
            f"💰 VALORES:",
            f"   Valor total: R$ {a.get('valor_total', 0):,.2f}",
            f"   Valor disponível: R$ {a.get('valor_disponivel', 0):,.2f}",
            "",
            "=" * 60,
            ""
        ]

        for i, p in enumerate(pedidos[:10], 1):
            status = "✅" if p.get("todos_disponiveis") else "⚠️"
            linhas.append(
                f"{i}. [{status}] Pedido: {p['num_pedido']} | "
                f"{p['cliente'][:25]} | "
                f"{p['cidade']}/{p['uf']} | "
                f"R$ {p['valor_total']:,.2f}"
            )

        if len(pedidos) > 10:
            linhas.append(f"... e mais {len(pedidos) - 10} pedidos")

        return "\n".join(linhas)

    def _formatar_analise_cliente(self, dados: Dict) -> str:
        """Formata análise de disponibilidade por CLIENTE."""
        a = dados.get("analise", {})
        itens = dados.get("dados", [])
        carga = dados.get("carga_sugerida", {})

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

        if a.get('mensagem'):
            linhas.append("")
            linhas.append(f"🎯 {a['mensagem']}")

        if carga.get("pode_montar") and carga.get("itens"):
            linhas.extend([
                "",
                "=" * 50,
                "📋 CARGA SUGERIDA",
                "=" * 50,
                f"   Total: {carga.get('total_pallets', 0):.1f} pallets",
                f"   Peso: {carga.get('total_peso', 0):,.0f} kg",
                f"   Valor: R$ {carga.get('total_valor', 0):,.2f}",
                f"   Itens: {len(carga.get('itens', []))}",
            ])

            if carga.get("todos_disponiveis_hoje"):
                linhas.append(f"   Status: ✅ TODOS DISPONÍVEIS HOJE")
            else:
                linhas.append(f"   Status: ⏳ {carga.get('itens_aguardar', 0)} item(ns) aguardando estoque")

            linhas.extend(["", "--- ITENS DA CARGA ---"])

            for i, item in enumerate(carga.get("itens", []), 1):
                status = "✅" if item.get('disponivel_hoje') else "⏳"
                fracionado = item.get('fracionado', False)

                if fracionado:
                    linhas.append(
                        f"  {i}. [{status}] {item['nome_produto'][:40]} ✂️ PARCIAL"
                    )
                    linhas.append(
                        f"      Pedido: {item['num_pedido']} | "
                        f"{item['quantidade']:.0f} de {item.get('quantidade_original', 0):.0f} un "
                        f"({item.get('percentual_usado', 0):.0f}%) = {item['pallets']:.2f} pallets | "
                        f"R$ {item['valor']:,.2f}"
                    )
                else:
                    linhas.append(
                        f"  {i}. [{status}] {item['nome_produto'][:40]}"
                    )
                    linhas.append(
                        f"      Pedido: {item['num_pedido']} | "
                        f"{item['quantidade']:.0f} un = {item['pallets']:.2f} pallets | "
                        f"R$ {item['valor']:,.2f}"
                    )

            linhas.extend([
                "",
                "💬 Para criar separação com estes itens, responda: 'CONFIRMAR CARGA'",
                "   ou ajuste a quantidade e pergunte novamente."
            ])

        else:
            linhas.extend(["", "--- ITENS DETALHADOS ---"])

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

            if opcao.get("itens_excluidos"):
                linhas.append(f"  ITENS NÃO INCLUÍDOS:")
                for item in opcao["itens_excluidos"]:
                    linhas.append(f"    X {item['nome_produto'][:35]}: {item['quantidade']:.0f}un (R$ {item['valor_total']:,.2f})")

            linhas.append("")

        linhas.append("Para criar separação, responda com a opção desejada (A, B ou C).")

        return "\n".join(linhas)

    def _formatar_pedidos_abertos(self, dados: Dict) -> str:
        """Formata resultado de pedidos em aberto."""
        resumo = dados.get("resumo", {})
        pedidos = dados.get("dados", [])

        linhas = [
            f"=== PEDIDOS EM ABERTO - {resumo.get('cliente', 'Cliente')} ===",
            "",
            f"📊 RESUMO:",
            f"   Total de pedidos em aberto: {resumo.get('total_pedidos_abertos', 0)}",
            f"   ✅ Disponíveis para envio TOTAL: {resumo.get('pedidos_disponiveis', 0)}",
            f"   ⚠️ Parcialmente disponíveis: {resumo.get('pedidos_parciais', 0)}",
            "",
            f"💰 VALORES:",
            f"   Valor total em aberto: R$ {resumo.get('valor_total_aberto', 0):,.2f}",
            f"   Valor disponível hoje: R$ {resumo.get('valor_disponivel', 0):,.2f}",
            f"   Peso total: {resumo.get('peso_total', 0):,.0f} kg",
            f"   Pallets total: {resumo.get('pallets_total', 0):.1f}",
            "",
            "=" * 60,
            ""
        ]

        for i, p in enumerate(pedidos[:10], 1):
            status = "✅ DISPONÍVEL" if p["todos_disponiveis"] else f"⚠️ PARCIAL ({p['percentual_disponivel']}%)"
            linhas.append(f"--- {i}. Pedido: {p['num_pedido']} | {status} ---")
            linhas.append(f"   Cliente: {p.get('raz_social_red', 'N/A')}")
            linhas.append(f"   Valor: R$ {p['valor_total']:,.2f}")
            linhas.append(f"   Peso: {p['peso_total']:,.0f}kg | Pallets: {p['pallets_total']:.2f}")
            linhas.append(f"   Itens: {p['itens_disponiveis']}/{p['total_itens']} disponíveis")

            for item in p["itens"][:3]:
                disp = "✅" if item.get("disponivel") else "❌"
                linhas.append(
                    f"      {disp} {item['nome_produto'][:35]}: "
                    f"{item['saldo_real']:.0f}un (estoque: {item.get('estoque_atual', 0):.0f})"
                )
            if len(p["itens"]) > 3:
                linhas.append(f"      ... e mais {len(p['itens']) - 3} itens")

            linhas.append("")

        if len(pedidos) > 10:
            linhas.append(f"... e mais {len(pedidos) - 10} pedidos")
            linhas.append("")

        linhas.extend([
            "=" * 60,
            "💡 AÇÕES DISPONÍVEIS:",
            "   - 'Qual o valor desses pedidos?' → Mostra valores",
            "   - 'Qual o maior?' → Mostra o pedido de maior valor disponível",
            "   - 'Programe o pedido X pro dia DD/MM' → Cria separação"
        ])

        return "\n".join(linhas)

    def _formatar_generico(self, dados: Dict) -> str:
        """Formatação genérica para casos não tratados."""
        linhas = [f"=== RESULTADO ({dados.get('total_encontrado', 0)} itens) ==="]

        for i, item in enumerate(dados.get("dados", [])[:20], 1):
            if isinstance(item, dict):
                partes = [f"{k}: {v}" for k, v in list(item.items())[:5] if v is not None]
                linhas.append(f"{i}. {' | '.join(partes)}")
            else:
                linhas.append(f"{i}. {item}")

        return "\n".join(linhas)
