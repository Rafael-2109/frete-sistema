"""
Serviço Unificado de Ajuste de Sincronização Odoo - VERSÃO ATUALIZADA
======================================================================

Versão simplificada sem PreSeparacaoItem, usando apenas Separacao.
Trabalha com saldos calculados e hierarquia correta.

Segue fielmente a ESPECIFICACAO_SINCRONIZACAO_ODOO.md
"""

import logging
from typing import Dict, List, Any
from app import db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.separacao.models import Separacao

logger = logging.getLogger(__name__)


class AjusteSincronizacaoService:
    """
    Serviço unificado para ajustar separações conforme alterações do Odoo.

    Regras principais:
    1. Separação TOTAL: Substituição completa (espelho do pedido)
    2. Separação PARCIAL: Segue hierarquia de ajuste
    3. Sempre filtrar por sincronizado_nf=False
    4. Usar saldos calculados (qtd_produto - qtd_cancelada - qtd_faturada)
    """

    @classmethod
    def processar_pedido_alterado(cls, num_pedido: str, itens_odoo: List[Dict]) -> Dict[str, Any]:
        """
        Processa um pedido que foi alterado no Odoo.

        Args:
            num_pedido: Número do pedido alterado
            itens_odoo: Lista com os itens atualizados do Odoo (já com saldo calculado)

        Returns:
            Dict com resultado do processamento
        """
        # Garantir sessão limpa
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao commitar sessão: {e}")
            db.session.rollback()

        try:
            logger.info(f"🔄 Processando pedido alterado: {num_pedido}")

            resultado = {
                "sucesso": True,
                "num_pedido": num_pedido,
                "tipo_processamento": None,
                "alteracoes_aplicadas": [],
                "alertas_gerados": [],
                "erros": [],
            }

            # 1. Identificar todos os lotes relacionados ao pedido
            lotes_afetados = cls._identificar_lotes_afetados(num_pedido)

            if not lotes_afetados:
                logger.info(f"Pedido {num_pedido} não tem separações alteráveis")
                resultado["tipo_processamento"] = "SEM_SEPARACAO"
                return resultado

            logger.info(f"📋 Processando pedido {num_pedido} com {len(lotes_afetados)} lotes:")
            for lote_info in lotes_afetados:
                logger.info(f"   - Lote {lote_info['lote_id']} status {lote_info['status']}")

            # 2. Processar cada lote
            for info_lote in lotes_afetados:
                lote_id = info_lote["lote_id"]
                status_lote = info_lote["status"]

                logger.info(f"Processando lote {lote_id} (status: {status_lote})")

                # Detectar se é TOTAL ou PARCIAL baseado no tipo_envio
                primeira_sep = Separacao.query.filter_by(
                    separacao_lote_id=lote_id, num_pedido=num_pedido, sincronizado_nf=False
                ).first()

                tipo_separacao = "TOTAL" if primeira_sep and primeira_sep.tipo_envio == "total" else "PARCIAL"

                if tipo_separacao == "TOTAL":
                    # Caso 1: Separação TOTAL - Substituir completamente
                    logger.info(f"Processando SUBSTITUIÇÃO TOTAL do lote {lote_id}")
                    resultado_lote = cls._processar_separacao_total(num_pedido, lote_id, status_lote, itens_odoo)
                else:
                    # Caso 2: Separação PARCIAL - Aplicar hierarquia
                    logger.info(f"Processando ajuste PARCIAL do lote {lote_id}")
                    resultado_lote = cls._processar_separacao_parcial(num_pedido, lote_id, status_lote, itens_odoo)

                # Acumular resultados
                resultado["alteracoes_aplicadas"].extend(resultado_lote.get("alteracoes", []))
                resultado["alertas_gerados"].extend(resultado_lote.get("alertas", []))
                resultado["erros"].extend(resultado_lote.get("erros", []))

            # Definir tipo de processamento baseado no que foi feito
            if resultado["alteracoes_aplicadas"]:
                resultado["tipo_processamento"] = "ALTERACOES_APLICADAS"
            else:
                resultado["tipo_processamento"] = "SEM_ALTERACOES"

            # Commitar todas as alterações
            try:
                db.session.commit()
                logger.info(f"✅ Alterações commitadas para pedido {num_pedido}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ Erro ao commitar alterações: {e}")
                resultado["sucesso"] = False
                resultado["erros"].append(f"Erro ao salvar: {str(e)}")

            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao processar pedido {num_pedido}: {e}")
            db.session.rollback()
            return {
                "sucesso": False,
                "num_pedido": num_pedido,
                "erro": str(e),
                "alteracoes_aplicadas": [],
                "alertas_gerados": [],
                "erros": [str(e)],
            }

    @classmethod
    def _identificar_lotes_afetados(cls, num_pedido: str) -> List[Dict]:
        """
        Identifica todos os lotes de Separacao afetados pelo pedido.

        IMPORTANTE:
        - Processa apenas Separacao com sincronizado_nf=False
        - Apenas status alteráveis: PREVISAO, ABERTO, COTADO

        Returns:
            Lista de dicts com {lote_id, tipo, status}
        """
        # 🔴 PROTEÇÃO: Verificar se pedido tem NF processada sem lote (não deve ser alterado)
        from app.faturamento.models import FaturamentoProduto
        
        nf_sem_lote = FaturamentoProduto.query.filter_by(
            origem=num_pedido,
            status_nf='SEM_LOTE'
        ).first()
        
        if nf_sem_lote:
            logger.warning(f"⚠️ PROTEÇÃO: Pedido {num_pedido} tem NF {nf_sem_lote.numero_nf} processada sem lote (status_nf='SEM_LOTE') - NÃO será alterado para evitar redução indevida")
            return []  # Retorna vazio para não processar alterações
        
        lotes = []

        # Buscar separações não sincronizadas e com status alterável
        seps = (
            db.session.query(Separacao.separacao_lote_id, Separacao.status, Separacao.numero_nf)
            .filter(
                Separacao.num_pedido == num_pedido,
                Separacao.separacao_lote_id.isnot(None),
                Separacao.sincronizado_nf == False,  # CRÍTICO: Não alterar NFs processadas
            )
            .distinct()
            .all()
        )

        for lote_id, status, numero_nf in seps:
            lotes.append({"lote_id": lote_id, "tipo": "SEPARACAO", "status": status})
            logger.info(f"Encontrada Separacao com lote {lote_id} (status: {status}, sincronizado_nf: False)")

        # Log das separações ignoradas
        seps_ignoradas = (
            db.session.query(Separacao.separacao_lote_id, Separacao.status, Separacao.numero_nf)
            .filter(
                Separacao.num_pedido == num_pedido,
                Separacao.separacao_lote_id.isnot(None),
                db.or_(Separacao.sincronizado_nf == True, Separacao.status.in_(["FATURADO", "NF no CD", "EMBARCADO"])),
            )
            .distinct()
            .all()
        )

        for lote_id, status, numero_nf in seps_ignoradas:
            logger.warning(
                f"🛡️ PROTEÇÃO: Ignorando lote {lote_id} - Status '{status}' ou já sincronizado (NF: {numero_nf})"
            )

        if not lotes:
            logger.info(f"Pedido {num_pedido} não tem separações alteráveis")
        else:
            logger.info(f"Total de {len(lotes)} lotes para processar")

        return lotes

    @classmethod
    def _processar_separacao_total(
        cls, num_pedido: str, lote_id: str, status_lote: str, itens_odoo: List[Dict]
    ) -> Dict:
        """
        Processa separação TOTAL - atualização completa SEM DELETAR.

        REGRAS:
        1. NUNCA deletar todas as separações
        2. Atualizar quantidades dos produtos existentes
        3. Adicionar produtos novos preservando dados do lote
        4. Remover apenas produtos que zeraram (não vieram do Odoo)
        """
        resultado = {"alteracoes": [], "alertas": [], "erros": []}

        try:
            # Buscar todas as separações existentes do lote
            separacoes_existentes = Separacao.query.filter_by(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                sincronizado_nf=False
            ).all()

            # Criar índice por cod_produto para acesso rápido
            separacoes_por_produto = {sep.cod_produto: sep for sep in separacoes_existentes}

            # Dados para preservar de uma separação exemplo (para novos produtos)
            dados_lote_preservar = None
            if separacoes_existentes:
                primeira_sep = separacoes_existentes[0]
                dados_lote_preservar = {
                    'cnpj_cpf': primeira_sep.cnpj_cpf,
                    'raz_social_red': primeira_sep.raz_social_red,
                    'nome_cidade': primeira_sep.nome_cidade,
                    'cod_uf': primeira_sep.cod_uf,
                    'data_pedido': primeira_sep.data_pedido,
                    'expedicao': primeira_sep.expedicao,
                    'agendamento': primeira_sep.agendamento,
                    'protocolo': primeira_sep.protocolo,
                    'observ_ped_1': primeira_sep.observ_ped_1,
                    'rota': primeira_sep.rota,
                    'sub_rota': primeira_sep.sub_rota,
                    'roteirizacao': primeira_sep.roteirizacao
                }

            # IMPORTANTE: Se COTADO, capturar dados ANTES de atualizar
            itens_antigos = {}
            if status_lote == "COTADO":
                for sep in separacoes_existentes:
                    itens_antigos[sep.cod_produto] = {
                        "qtd": float(sep.qtd_saldo or 0),
                        "nome": sep.nome_produto
                    }
                logger.info(f"📸 Capturados {len(itens_antigos)} itens ANTES da atualização TOTAL (COTADO)")

            # Buscar dados de palletização uma vez só
            from app.producao.models import CadastroPalletizacao
            produtos_unicos = {item["cod_produto"] for item in itens_odoo}
            palletizacoes = {p.cod_produto: p for p in CadastroPalletizacao.query.filter(
                CadastroPalletizacao.cod_produto.in_(list(produtos_unicos))
            ).all()}

            # Controlar produtos processados do Odoo
            produtos_processados = set()

            # Processar cada item do Odoo
            for item_odoo in itens_odoo:
                cod_produto = item_odoo["cod_produto"]
                produtos_processados.add(cod_produto)
                qtd_saldo = float(item_odoo["qtd_saldo_produto_pedido"])

                # Calcular peso e pallet
                palletizacao = palletizacoes.get(cod_produto)
                peso_calculado = 0
                pallet_calculado = 0

                if palletizacao:
                    peso_calculado = qtd_saldo * float(palletizacao.peso_bruto or 1.0)
                    if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                        pallet_calculado = qtd_saldo / float(palletizacao.palletizacao)
                else:
                    peso_calculado = qtd_saldo  # Assumir peso 1:1
                    logger.debug(f"⚠️ Palletização não encontrada para {cod_produto}")

                # Verificar se produto já existe na separação
                if cod_produto in separacoes_por_produto:
                    # ATUALIZAR separação existente
                    sep_existente = separacoes_por_produto[cod_produto]

                    # Atualizar apenas campos que mudam com a quantidade
                    sep_existente.qtd_saldo = qtd_saldo
                    sep_existente.valor_saldo = item_odoo.get("preco_produto_pedido", 0) * qtd_saldo
                    sep_existente.peso = peso_calculado
                    sep_existente.pallet = pallet_calculado

                    # Atualizar datas se vieram do Odoo (mas preservar se não vieram)
                    if item_odoo.get("expedicao"):
                        sep_existente.expedicao = item_odoo["expedicao"]
                    if item_odoo.get("agendamento"):
                        sep_existente.agendamento = item_odoo["agendamento"]
                    if item_odoo.get("protocolo"):
                        sep_existente.protocolo = item_odoo["protocolo"]

                    logger.info(f"✏️ Atualizado {cod_produto}: qtd {qtd_saldo:.2f}, peso {peso_calculado:.2f}, pallet {pallet_calculado:.2f}")

                else:
                    # ADICIONAR novo produto à separação
                    # Usar dados preservados do lote ou do item_odoo
                    if dados_lote_preservar:
                        # Preferir dados do lote existente
                        cnpj_cpf = dados_lote_preservar['cnpj_cpf']
                        raz_social_red = dados_lote_preservar['raz_social_red']
                        nome_cidade = dados_lote_preservar['nome_cidade']
                        cod_uf = dados_lote_preservar['cod_uf']
                        data_pedido = dados_lote_preservar['data_pedido']
                        expedicao = item_odoo.get("expedicao") or dados_lote_preservar['expedicao']
                        agendamento = item_odoo.get("agendamento") or dados_lote_preservar['agendamento']
                        protocolo = item_odoo.get("protocolo") or dados_lote_preservar['protocolo']
                        observ_ped_1 = item_odoo.get("observ_ped_1") or dados_lote_preservar['observ_ped_1']
                        rota = dados_lote_preservar['rota']
                        sub_rota = dados_lote_preservar['sub_rota']
                        roteirizacao = dados_lote_preservar['roteirizacao']
                    else:
                        # Fallback se não há dados para preservar
                        cnpj_cpf = item_odoo.get("cnpj_cpf", "")
                        raz_social_red = item_odoo.get("raz_social_red", "")
                        nome_cidade = item_odoo.get("municipio") or item_odoo.get("nome_cidade") or "São Paulo"
                        cod_uf = item_odoo.get("estado") or item_odoo.get("cod_uf") or "SP"
                        data_pedido = item_odoo.get("data_pedido")
                        expedicao = item_odoo.get("expedicao")
                        agendamento = item_odoo.get("agendamento")
                        protocolo = item_odoo.get("protocolo")
                        observ_ped_1 = item_odoo.get("observ_ped_1")
                        rota = None
                        sub_rota = None
                        roteirizacao = None

                    nova_sep = Separacao(
                        separacao_lote_id=lote_id,
                        num_pedido=num_pedido,
                        cod_produto=cod_produto,
                        nome_produto=item_odoo.get("nome_produto", ""),
                        qtd_saldo=qtd_saldo,
                        valor_saldo=item_odoo.get("preco_produto_pedido", 0) * qtd_saldo,
                        peso=peso_calculado,
                        pallet=pallet_calculado,
                        cnpj_cpf=cnpj_cpf,
                        raz_social_red=raz_social_red,
                        nome_cidade=nome_cidade,
                        cod_uf=cod_uf,
                        data_pedido=data_pedido,
                        expedicao=expedicao,
                        agendamento=agendamento,
                        protocolo=protocolo,
                        observ_ped_1=observ_ped_1,
                        rota=rota,
                        sub_rota=sub_rota,
                        roteirizacao=roteirizacao,
                        status=status_lote,
                        sincronizado_nf=False,
                        tipo_envio="total",
                    )
                    db.session.add(nova_sep)
                    logger.info(f"➕ Adicionado novo produto {cod_produto} com qtd {qtd_saldo:.2f}, peso {peso_calculado:.2f}, pallet {pallet_calculado:.2f}")

            # REMOVER produtos que não vieram do Odoo (qtd zerou)
            for cod_produto, sep_existente in separacoes_por_produto.items():
                if cod_produto not in produtos_processados:
                    db.session.delete(sep_existente)
                    logger.info(f"🗑️ Removido produto {cod_produto} (não está mais no pedido)")

            resultado["alteracoes"].append({"tipo": "SUBSTITUICAO_TOTAL", "lote_id": lote_id, "itens": len(itens_odoo)})

            # Se não era PREVISAO nem ABERTO, gerar alerta sobre a alteração
            if status_lote not in ["PREVISAO", "ABERTO"] and itens_antigos:
                cls._gerar_alerta_cotado(
                    lote_id, num_pedido, "SUBSTITUICAO_TOTAL", itens_antigos, itens_odoo, resultado
                )

            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao processar separação TOTAL: {e}")
            resultado["erros"].append(str(e))
            return resultado

    @classmethod
    def _processar_separacao_parcial(
        cls, num_pedido: str, lote_id: str, status_lote: str, itens_odoo: List[Dict]
    ) -> Dict:
        """
        Processa separação PARCIAL - segue hierarquia de ajuste.
        """
        resultado = {"alteracoes": [], "alertas": [], "erros": []}

        try:
            # Se COTADO, capturar estado antes das mudanças
            itens_antigos = {}
            if status_lote == "COTADO":
                separacoes_antigas = Separacao.query.filter_by(
                    separacao_lote_id=lote_id, num_pedido=num_pedido, sincronizado_nf=False
                ).all()

                for sep in separacoes_antigas:
                    itens_antigos[sep.cod_produto] = {"qtd": float(sep.qtd_saldo or 0), "nome": sep.nome_produto}
                logger.info(f"📸 Capturados {len(itens_antigos)} itens ANTES do ajuste PARCIAL (COTADO)")

            # Calcular diferenças entre Odoo e sistema atual
            diferencas = cls._calcular_diferencas_com_saldo(num_pedido, lote_id, itens_odoo)

            # Processar reduções seguindo hierarquia
            for reducao in diferencas["reducoes"]:
                resultado_red = cls._aplicar_reducao_hierarquia(
                    num_pedido, lote_id, reducao["cod_produto"], reducao["qtd_reduzir"]
                )
                resultado["alteracoes"].append(resultado_red)

            # Processar aumentos seguindo critérios de status
            for aumento in diferencas["aumentos"]:
                # Verificar status do lote e tipo_envio
                primeira_sep = Separacao.query.filter_by(separacao_lote_id=lote_id, sincronizado_nf=False).first()

                tipo_envio = primeira_sep.tipo_envio if primeira_sep else "parcial"

                # Se tipo_envio='total' E status permite alteração sem alerta
                if tipo_envio == "total" and status_lote in ["PREVISAO", "ABERTO"]:
                    # Aplicar aumento diretamente
                    cls._aplicar_aumento(num_pedido, lote_id, aumento)
                    resultado["alteracoes"].append(
                        {
                            "tipo": "AUMENTO",
                            "cod_produto": aumento["cod_produto"],
                            "quantidade": aumento["qtd_aumentar"],
                        }
                    )

                # Se tipo_envio='total' mas status requer alerta
                elif tipo_envio == "total" and status_lote not in ["PREVISAO", "ABERTO"]:
                    resultado["alertas"].append(
                        {
                            "tipo": f"AUMENTO_{status_lote}",
                            "cod_produto": aumento["cod_produto"],
                            "quantidade_necessaria": aumento["qtd_aumentar"],
                            "mensagem": f"Aumento necessário em item {status_lote}: {aumento['cod_produto']} (envio total)",
                        }
                    )

                # Se tipo_envio='parcial', sempre gerar alerta
                else:
                    resultado["alertas"].append(
                        {
                            "tipo": "AUMENTO_PARCIAL",
                            "cod_produto": aumento["cod_produto"],
                            "quantidade": aumento["qtd_aumentar"],
                            "mensagem": f"Aumento detectado em envio parcial: {aumento['cod_produto']}",
                        }
                    )

            # Processar novos itens
            # 🔧 CORREÇÃO: Apenas adicionar novos produtos em separações TOTAL, não PARCIAL
            primeira_sep = Separacao.query.filter_by(separacao_lote_id=lote_id, sincronizado_nf=False).first()
            tipo_envio = primeira_sep.tipo_envio if primeira_sep else "parcial"

            for novo in diferencas["novos"]:
                if tipo_envio == "total":
                    # Separação TOTAL: adicionar produto novo do Odoo
                    cls._adicionar_novo_item(num_pedido, lote_id, novo)
                    resultado["alteracoes"].append(
                        {"tipo": "NOVO_ITEM", "cod_produto": novo["cod_produto"], "quantidade": novo["quantidade"]}
                    )
                else:
                    # Separação PARCIAL: NÃO adicionar, apenas alertar
                    resultado["alertas"].append(
                        {
                            "tipo": "PRODUTO_NOVO_ODOO_IGNORADO",
                            "cod_produto": novo["cod_produto"],
                            "quantidade": novo["quantidade"],
                            "mensagem": f"Produto {novo['cod_produto']} novo no Odoo não foi adicionado (separação parcial)"
                        }
                    )

            # Se COTADO, gerar alertas para alterações
            if status_lote == "COTADO" and resultado["alteracoes"]:
                cls._gerar_alerta_cotado(lote_id, num_pedido, "AJUSTE_PARCIAL", itens_antigos, itens_odoo, resultado)

            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao processar separação PARCIAL: {e}")
            resultado["erros"].append(str(e))
            return resultado

    @classmethod
    def _calcular_diferencas_com_saldo(cls, num_pedido: str, lote_id: str, itens_odoo: List[Dict]) -> Dict:
        """
        Calcula diferenças entre Odoo e sistema atual usando saldos calculados.
        """
        diferencas = {"reducoes": [], "aumentos": [], "novos": [], "removidos": []}

        # Mapear itens do Odoo por produto
        odoo_por_produto = {}
        for item in itens_odoo:
            cod_produto = item["cod_produto"]
            qtd = float(item["qtd_saldo_produto_pedido"])  # Já calculado
            odoo_por_produto[cod_produto] = qtd

        # Buscar itens atuais da separação
        separacoes_atuais = Separacao.query.filter_by(
            separacao_lote_id=lote_id, num_pedido=num_pedido, sincronizado_nf=False
        ).all()

        produtos_processados = set()

        # Comparar cada item atual com Odoo
        for sep in separacoes_atuais:
            cod_produto = sep.cod_produto
            qtd_atual = float(sep.qtd_saldo or 0)
            qtd_odoo = odoo_por_produto.get(cod_produto, 0)

            produtos_processados.add(cod_produto)

            if abs(qtd_odoo - qtd_atual) > 0.01:  # Diferença significativa
                if qtd_odoo < qtd_atual:
                    # Redução
                    diferencas["reducoes"].append(
                        {
                            "cod_produto": cod_produto,
                            "qtd_atual": qtd_atual,
                            "qtd_nova": qtd_odoo,
                            "qtd_reduzir": qtd_atual - qtd_odoo,
                        }
                    )
                else:
                    # Aumento
                    diferencas["aumentos"].append(
                        {
                            "cod_produto": cod_produto,
                            "qtd_atual": qtd_atual,
                            "qtd_nova": qtd_odoo,
                            "qtd_aumentar": qtd_odoo - qtd_atual,
                        }
                    )

        # Identificar produtos novos (no Odoo mas não na separação)
        for cod_produto, qtd_odoo in odoo_por_produto.items():
            if cod_produto not in produtos_processados and qtd_odoo > 0:
                # Buscar dados completos do item
                item_completo = next((i for i in itens_odoo if i["cod_produto"] == cod_produto), None)
                if item_completo:
                    diferencas["novos"].append(
                        {"cod_produto": cod_produto, "quantidade": qtd_odoo, "dados_completos": item_completo}
                    )

        logger.info(
            f"📊 Diferenças calculadas: {len(diferencas['reducoes'])} reduções, "
            f"{len(diferencas['aumentos'])} aumentos, {len(diferencas['novos'])} novos"
        )

        return diferencas

    @classmethod
    def _aplicar_reducao_hierarquia(cls, num_pedido: str, lote_id: str, cod_produto: str, qtd_reduzir: float) -> Dict:
        """
        Aplica redução seguindo hierarquia: PREVISAO → ABERTO → COTADO
        """
        resultado = {"tipo": "REDUCAO", "cod_produto": cod_produto, "qtd_reduzida": 0, "alteracoes_por_status": []}

        qtd_restante = qtd_reduzir

        # Hierarquia de status para redução
        hierarquia = ["PREVISAO", "ABERTO", "COTADO", "FATURADO", "EMBARCADO", "NF no CD"]

        for status in hierarquia:
            if qtd_restante <= 0:
                break

            # Buscar separações deste status
            separacoes = Separacao.query.filter_by(
                num_pedido=num_pedido, cod_produto=cod_produto, status=status, sincronizado_nf=False
            ).all()

            for sep in separacoes:
                if qtd_restante <= 0:
                    break

                qtd_atual = float(sep.qtd_saldo or 0)

                if qtd_atual > 0:
                    qtd_a_reduzir = min(qtd_atual, qtd_restante)
                    nova_qtd = qtd_atual - qtd_a_reduzir

                    sep.qtd_saldo = nova_qtd
                    qtd_restante -= qtd_a_reduzir
                    resultado["qtd_reduzida"] += qtd_a_reduzir

                    resultado["alteracoes_por_status"].append(
                        {
                            "status": status,
                            "lote_id": sep.separacao_lote_id,
                            "qtd_reduzida": qtd_a_reduzir,
                            "nova_qtd": nova_qtd,
                        }
                    )

                    logger.info(
                        f"📉 Reduzido {qtd_a_reduzir} de {cod_produto} em {status} " f"(lote: {sep.separacao_lote_id})"
                    )

                    # Se alterou status que não seja PREVISAO ou ABERTO, marcar para gerar alerta
                    if status not in ["PREVISAO", "ABERTO"]:
                        resultado["alerta_gerado"] = True
                        resultado["status_alterado"] = status

        return resultado

    @classmethod
    def _aplicar_aumento(cls, num_pedido: str, lote_id: str, aumento: Dict):
        """
        Aplica aumento preservando dados e recalculando peso/pallet.
        """
        cod_produto = aumento["cod_produto"]
        qtd_aumentar = aumento["qtd_aumentar"]

        # Verificar se já existe separação ABERTO para este produto
        sep_existente = Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido,
            cod_produto=cod_produto,
            status="ABERTO",
            sincronizado_nf=False,
        ).first()

        # Buscar palletização para recalcular
        from app.producao.models import CadastroPalletizacao
        palletizacao = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto
        ).first()

        if sep_existente:
            # Aumentar quantidade existente e recalcular peso/pallet
            nova_qtd = float(sep_existente.qtd_saldo or 0) + qtd_aumentar
            sep_existente.qtd_saldo = nova_qtd

            # Recalcular peso e pallet com nova quantidade
            if palletizacao:
                sep_existente.peso = nova_qtd * float(palletizacao.peso_bruto or 1.0)
                if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                    sep_existente.pallet = nova_qtd / float(palletizacao.palletizacao)
            else:
                sep_existente.peso = nova_qtd

            logger.info(f"📈 Aumentado {qtd_aumentar} em separação existente para {cod_produto} (nova qtd: {nova_qtd:.2f})")
        else:
            # Criar nova separação preservando dados do lote
            sep_exemplo = Separacao.query.filter_by(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                sincronizado_nf=False
            ).first()

            # Calcular peso e pallet
            peso_calculado = 0
            pallet_calculado = 0
            if palletizacao:
                peso_calculado = qtd_aumentar * float(palletizacao.peso_bruto or 1.0)
                if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                    pallet_calculado = qtd_aumentar / float(palletizacao.palletizacao)
            else:
                peso_calculado = qtd_aumentar

            if sep_exemplo:
                # Copiar dados do lote
                nova_sep = Separacao(
                    separacao_lote_id=lote_id,
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    qtd_saldo=qtd_aumentar,
                    peso=peso_calculado,
                    pallet=pallet_calculado,
                    # Copiar todos os dados do exemplo
                    nome_produto=sep_exemplo.nome_produto,
                    valor_saldo=(sep_exemplo.valor_saldo / sep_exemplo.qtd_saldo * qtd_aumentar) if sep_exemplo.qtd_saldo else 0,
                    cnpj_cpf=sep_exemplo.cnpj_cpf,
                    raz_social_red=sep_exemplo.raz_social_red,
                    nome_cidade=sep_exemplo.nome_cidade,
                    cod_uf=sep_exemplo.cod_uf,
                    data_pedido=sep_exemplo.data_pedido,
                    expedicao=sep_exemplo.expedicao,
                    agendamento=sep_exemplo.agendamento,
                    protocolo=sep_exemplo.protocolo,
                    observ_ped_1=sep_exemplo.observ_ped_1,
                    rota=sep_exemplo.rota,
                    sub_rota=sep_exemplo.sub_rota,
                    roteirizacao=sep_exemplo.roteirizacao,
                    status="ABERTO",
                    sincronizado_nf=False,
                    tipo_envio="parcial",
                )
            else:
                # Fallback mínimo se não há exemplo
                item_odoo = next((i for i in aumento.get("itens_odoo", []) if i["cod_produto"] == cod_produto), {})
                nome_cidade = item_odoo.get("municipio", "") or item_odoo.get("nome_cidade", "") or "São Paulo"
                cod_uf = item_odoo.get("estado", "") or item_odoo.get("cod_uf", "") or "SP"

                nova_sep = Separacao(
                    separacao_lote_id=lote_id,
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    qtd_saldo=qtd_aumentar,
                    peso=peso_calculado,
                    pallet=pallet_calculado,
                    nome_cidade=nome_cidade,
                    cod_uf=cod_uf,
                    status="ABERTO",
                    sincronizado_nf=False,
                    tipo_envio="parcial",
                )

            db.session.add(nova_sep)
            logger.info(f"📈 Criada nova separação com {qtd_aumentar:.2f} para {cod_produto} (peso: {peso_calculado:.2f}, pallet: {pallet_calculado:.2f})")

    @classmethod
    def _adicionar_novo_item(cls, num_pedido: str, lote_id: str, novo_item: Dict):
        """
        Adiciona novo item preservando dados do lote existente.
        """
        dados = novo_item.get("dados_completos", {})
        cod_produto = novo_item["cod_produto"]
        quantidade = novo_item["quantidade"]

        # Buscar uma separação existente do mesmo lote para copiar dados
        sep_exemplo = Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido,
            sincronizado_nf=False
        ).first()

        # Buscar palletização para calcular peso e pallet
        from app.producao.models import CadastroPalletizacao
        palletizacao = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto
        ).first()

        peso_calculado = 0
        pallet_calculado = 0

        if palletizacao:
            peso_calculado = float(quantidade) * float(palletizacao.peso_bruto or 1.0)
            if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                pallet_calculado = float(quantidade) / float(palletizacao.palletizacao)
        else:
            peso_calculado = float(quantidade)  # Assumir peso 1:1

        # Preservar dados do lote se existir separação exemplo
        if sep_exemplo:
            nova_sep = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                nome_produto=dados.get("nome_produto", ""),
                qtd_saldo=quantidade,
                valor_saldo=dados.get("preco_produto_pedido", 0) * quantidade,
                peso=peso_calculado,
                pallet=pallet_calculado,
                # Copiar dados do lote
                cnpj_cpf=sep_exemplo.cnpj_cpf,
                raz_social_red=sep_exemplo.raz_social_red,
                nome_cidade=sep_exemplo.nome_cidade,
                cod_uf=sep_exemplo.cod_uf,
                data_pedido=sep_exemplo.data_pedido,
                expedicao=dados.get("expedicao") or sep_exemplo.expedicao,
                agendamento=dados.get("agendamento") or sep_exemplo.agendamento,
                protocolo=dados.get("protocolo") or sep_exemplo.protocolo,
                observ_ped_1=sep_exemplo.observ_ped_1,
                rota=sep_exemplo.rota,
                sub_rota=sep_exemplo.sub_rota,
                roteirizacao=sep_exemplo.roteirizacao,
                status="ABERTO",
                sincronizado_nf=False,
                tipo_envio="parcial",
            )
        else:
            # Fallback se não houver exemplo
            cod_uf = dados.get("estado", "") or dados.get("cod_uf", "") or "SP"
            nome_cidade = dados.get("municipio", "") or dados.get("nome_cidade", "") or "São Paulo"

            nova_sep = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                nome_produto=dados.get("nome_produto", ""),
                qtd_saldo=quantidade,
                valor_saldo=dados.get("preco_produto_pedido", 0) * quantidade,
                peso=peso_calculado,
                pallet=pallet_calculado,
                cnpj_cpf=dados.get("cnpj_cpf", ""),
                raz_social_red=dados.get("raz_social_red", ""),
                nome_cidade=nome_cidade,
                cod_uf=cod_uf,
                data_pedido=dados.get("data_pedido"),
                expedicao=dados.get("expedicao"),
                agendamento=dados.get("agendamento"),
                protocolo=dados.get("protocolo"),
                observ_ped_1=dados.get("observ_ped_1"),
                status="ABERTO",
                sincronizado_nf=False,
                tipo_envio="parcial",
            )

        db.session.add(nova_sep)
        logger.info(f"➕ Novo item {cod_produto} adicionado com peso {peso_calculado:.2f} e pallet {pallet_calculado:.2f}")

    @classmethod
    def _gerar_alerta_cotado(
        cls,
        lote_id: str,
        num_pedido: str,
        tipo_alteracao: str,
        itens_antigos: Dict,
        itens_novos: List[Dict],
        resultado: Dict,
    ):
        """
        Gera alerta quando separação COTADA é alterada.
        """
        try:
            # Criar descrição detalhada da alteração
            descricao = f"Separação COTADA alterada - Tipo: {tipo_alteracao}\n"

            # Comparar itens
            for cod_produto, dados_antigos in itens_antigos.items():
                item_novo = next((i for i in itens_novos if i["cod_produto"] == cod_produto), None)
                if item_novo:
                    qtd_nova = float(item_novo["qtd_saldo_produto_pedido"])
                    qtd_antiga = dados_antigos["qtd"]
                    if abs(qtd_nova - qtd_antiga) > 0.01:
                        descricao += f"- {cod_produto}: {qtd_antiga} → {qtd_nova}\n"
                else:
                    descricao += f"- {cod_produto}: REMOVIDO (era {dados_antigos['qtd']})\n"

            # Verificar novos itens
            for item_novo in itens_novos:
                if item_novo["cod_produto"] not in itens_antigos:
                    descricao += f"- {item_novo['cod_produto']}: NOVO ({item_novo['qtd_saldo_produto_pedido']})\n"

            # Criar alerta
            alerta = AlertaSeparacaoCotada(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                tipo_alerta="ALTERACAO_QUANTIDADE_COTADO",
                nivel="CRITICO",
                descricao=descricao,
                fonte="SINCRONIZACAO_ODOO",
                resolvido=False,
            )
            db.session.add(alerta)

            resultado["alertas"].append(
                {"tipo": "COTADO_ALTERADO", "lote_id": lote_id, "num_pedido": num_pedido, "descricao": descricao}
            )

            logger.warning(f"🚨 ALERTA GERADO: Separação COTADA {lote_id} foi alterada")

        except Exception as e:
            logger.error(f"Erro ao gerar alerta: {e}")

    @classmethod
    def _verificar_se_cotado(cls, lote_id: str) -> bool:
        """
        Verifica se um lote está com status COTADO.
        """
        separacao = Separacao.query.filter_by(separacao_lote_id=lote_id, status="COTADO", sincronizado_nf=False).first()

        return separacao is not None

    @classmethod
    def _verificar_se_faturado(cls, lote_id: str) -> bool:
        """
        Verifica se um lote está faturado (sincronizado_nf=True ou status FATURADO).
        """
        separacao = (
            Separacao.query.filter_by(separacao_lote_id=lote_id)
            .filter(db.or_(Separacao.sincronizado_nf == True, Separacao.status == "FATURADO"))
            .first()
        )

        return separacao is not None
