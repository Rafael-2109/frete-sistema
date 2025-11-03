"""
Serviço para sincronizar items de Separacao com FaturamentoProduto

Busca dados reais de quantidade, valor, peso e pallets do FaturamentoProduto
e atualiza a Separacao para refletir o que foi realmente faturado.
"""

import logging
from typing import Dict, Any
from app import db
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao

logger = logging.getLogger(__name__)


class SincronizadorItemsService:
    """
    Serviço para sincronizar items de Separacao com dados de FaturamentoProduto
    """

    def sincronizar_items_faturamento(
        self,
        separacao_lote_id: str,
        usuario: str = 'Sistema'
    ) -> Dict[str, Any]:
        """
        Sincroniza items de Separacao com FaturamentoProduto

        LÓGICA COMPLETA:
        1. Buscar Separacao com separacao_lote_id e sincronizado_nf=True
        2. Extrair numero_nf da primeira Separacao encontrada
        3. Buscar TODOS os produtos da NF em FaturamentoProduto
        4. Para cada produto em Separacao:
           a. Se existe em FaturamentoProduto: ATUALIZAR quantidades
           b. Se NÃO existe em FaturamentoProduto: ZERAR quantidades
        5. Para cada produto em FaturamentoProduto que NÃO está em Separacao:
           a. CRIAR nova Separacao copiando dados do lote

        Args:
            separacao_lote_id: ID do lote de separação
            usuario: Nome do usuário que solicitou

        Returns:
            Dict com resultado da operação
        """
        try:
            logger.info(f"🔄 Iniciando sincronização COMPLETA de items para lote {separacao_lote_id}")

            # 1. Buscar Separacoes do lote com sincronizado_nf=True
            separacoes = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                sincronizado_nf=True
            ).all()

            if not separacoes:
                logger.warning(f"  ⚠️ Nenhuma Separacao com sincronizado_nf=True para lote {separacao_lote_id}")
                return {
                    'success': False,
                    'erro': 'Nenhuma separação sincronizada encontrada neste lote'
                }

            # 2. Extrair numero_nf (deve ser igual para todos do lote)
            numero_nf = separacoes[0].numero_nf

            if not numero_nf:
                logger.warning(f"  ⚠️ Separação não possui numero_nf")
                return {
                    'success': False,
                    'erro': 'Separação não possui número de NF'
                }

            logger.info(f"  📋 NF encontrada: {numero_nf}")
            logger.info(f"  📦 Separacoes existentes no lote: {len(separacoes)}")

            # 3. Buscar TODOS os produtos desta NF em FaturamentoProduto
            itens_faturamento = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf
            ).all()

            if not itens_faturamento:
                logger.warning(f"  ⚠️ Nenhum item encontrado em FaturamentoProduto para NF {numero_nf}")
                return {
                    'success': False,
                    'erro': f'Nenhum item encontrado no faturamento para NF {numero_nf}'
                }

            logger.info(f"  📋 Itens na NF (FaturamentoProduto): {len(itens_faturamento)}")

            # Criar índice de produtos do faturamento para acesso rápido
            produtos_faturamento = {item.cod_produto: item for item in itens_faturamento}

            # Criar índice de separacoes existentes por cod_produto
            separacoes_por_produto = {sep.cod_produto: sep for sep in separacoes}

            # Usar primeira separação como exemplo para novos produtos
            separacao_exemplo = separacoes[0]

            # Contadores
            atualizados = 0
            zerados = 0
            adicionados = 0
            erros = 0
            detalhes = []

            # 4. PROCESSAR SEPARACOES EXISTENTES
            logger.info(f"  🔄 Processando separações existentes...")
            for separacao in separacoes:
                try:
                    cod_produto = separacao.cod_produto

                    if cod_produto in produtos_faturamento:
                        # 4a. Produto existe na NF: ATUALIZAR
                        resultado_item = self._sincronizar_item(
                            separacao=separacao,
                            numero_nf=numero_nf,
                            usuario=usuario
                        )

                        detalhes.append(resultado_item)

                        if resultado_item['status'] == 'atualizado':
                            atualizados += 1
                        else:
                            erros += 1

                    else:
                        # 4b. Produto NÃO existe na NF: ZERAR
                        logger.warning(f"    ⚠️ Produto {cod_produto} está na Separacao mas NÃO na NF - ZERANDO quantidades")

                        separacao.qtd_saldo = 0
                        separacao.valor_saldo = 0
                        separacao.peso = 0
                        separacao.pallet = 0
                        # Mantém sincronizado_nf=True conforme solicitado

                        zerados += 1
                        detalhes.append({
                            'cod_produto': cod_produto,
                            'status': 'zerado',
                            'motivo': 'Produto não encontrado na NF'
                        })

                except Exception as e:
                    logger.error(f"  ❌ Erro ao processar item {separacao.cod_produto}: {e}")
                    detalhes.append({
                        'cod_produto': separacao.cod_produto,
                        'status': 'erro',
                        'erro': str(e)
                    })
                    erros += 1

            # 5. ADICIONAR PRODUTOS NOVOS (que estão na NF mas não em Separacao)
            logger.info(f"  ➕ Verificando produtos novos para adicionar...")
            for cod_produto, item_faturamento in produtos_faturamento.items():
                if cod_produto not in separacoes_por_produto:
                    try:
                        logger.info(f"    ➕ Adicionando produto novo: {cod_produto}")

                        # Criar nova Separacao baseada no exemplo
                        nova_separacao = self._criar_separacao_de_faturamento(
                            separacao_exemplo=separacao_exemplo,
                            item_faturamento=item_faturamento,
                            separacao_lote_id=separacao_lote_id,
                            numero_nf=numero_nf
                        )

                        db.session.add(nova_separacao)
                        adicionados += 1

                        detalhes.append({
                            'cod_produto': cod_produto,
                            'status': 'adicionado',
                            'dados': {
                                'qtd_saldo': float(nova_separacao.qtd_saldo),
                                'valor_saldo': float(nova_separacao.valor_saldo),
                                'peso': float(nova_separacao.peso),
                                'pallet': float(nova_separacao.pallet)
                            }
                        })

                    except Exception as e:
                        logger.error(f"  ❌ Erro ao adicionar produto {cod_produto}: {e}")
                        detalhes.append({
                            'cod_produto': cod_produto,
                            'status': 'erro',
                            'erro': str(e)
                        })
                        erros += 1

            # Commit
            db.session.commit()

            logger.info(f"  ✅ Sincronização COMPLETA concluída:")
            logger.info(f"     - {atualizados} itens atualizados")
            logger.info(f"     - {zerados} itens zerados")
            logger.info(f"     - {adicionados} itens adicionados")
            logger.info(f"     - {erros} erros")

            return {
                'success': True,
                'separacao_lote_id': separacao_lote_id,
                'numero_nf': numero_nf,
                'atualizados': atualizados,
                'zerados': zerados,
                'adicionados': adicionados,
                'erros': erros,
                'detalhes': detalhes
            }

        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar items do lote {separacao_lote_id}: {e}")
            db.session.rollback()
            return {
                'success': False,
                'separacao_lote_id': separacao_lote_id,
                'erro': str(e)
            }

    def _sincronizar_item(
        self,
        separacao: Separacao,
        numero_nf: str,
        usuario: str
    ) -> Dict[str, Any]:
        """
        Sincroniza um item de Separacao com FaturamentoProduto

        Args:
            separacao: Objeto Separacao a atualizar
            numero_nf: Número da NF para buscar em FaturamentoProduto
            usuario: Usuário que solicitou

        Returns:
            Dict com resultado da sincronização do item
        """
        cod_produto = separacao.cod_produto

        # Buscar item em FaturamentoProduto
        faturamento_item = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            cod_produto=cod_produto
        ).first()

        if not faturamento_item:
            logger.warning(f"    ⚠️ Produto {cod_produto} não encontrado em FaturamentoProduto para NF {numero_nf}")
            return {
                'cod_produto': cod_produto,
                'status': 'nao_encontrado',
                'motivo': 'Produto não encontrado no faturamento'
            }

        # Extrair dados de FaturamentoProduto
        qtd_faturada = float(faturamento_item.qtd_produto_faturado or 0)
        valor_faturado = float(faturamento_item.valor_produto_faturado or 0)
        peso_total = float(faturamento_item.peso_total or 0)

        # Calcular pallets usando CadastroPalletizacao
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()

        pallets = 0
        if cadastro and cadastro.palletizacao > 0:
            pallets = round(qtd_faturada / float(cadastro.palletizacao), 2)

        # Atualizar Separacao
        separacao.qtd_saldo = qtd_faturada
        separacao.valor_saldo = valor_faturado
        separacao.peso = peso_total
        separacao.pallet = pallets

        logger.info(f"    ✅ {cod_produto}: qtd={qtd_faturada}, valor=R${valor_faturado:.2f}, peso={peso_total}kg, pallets={pallets}")

        return {
            'cod_produto': cod_produto,
            'status': 'atualizado',
            'dados_anteriores': {
                'qtd_saldo': float(separacao.qtd_saldo or 0),
                'valor_saldo': float(separacao.valor_saldo or 0),
                'peso': float(separacao.peso or 0),
                'pallet': float(separacao.pallet or 0)
            },
            'dados_novos': {
                'qtd_saldo': qtd_faturada,
                'valor_saldo': valor_faturado,
                'peso': peso_total,
                'pallet': pallets
            }
        }

    def _criar_separacao_de_faturamento(
        self,
        separacao_exemplo: Separacao,
        item_faturamento: FaturamentoProduto,
        separacao_lote_id: str,
        numero_nf: str
    ) -> Separacao:
        """
        Cria nova Separacao baseada em item de FaturamentoProduto

        Copia TODOS os campos da separacao_exemplo EXCETO:
        - cod_produto (vem de FaturamentoProduto)
        - nome_produto (vem de FaturamentoProduto)
        - qtd_saldo (vem de FaturamentoProduto)
        - valor_saldo (vem de FaturamentoProduto)
        - peso (vem de FaturamentoProduto)
        - pallet (calculado via CadastroPalletizacao)

        Args:
            separacao_exemplo: Separacao usada como modelo
            item_faturamento: Item de FaturamentoProduto com dados do produto
            separacao_lote_id: ID do lote
            numero_nf: Número da NF

        Returns:
            Nova instância de Separacao
        """
        # Extrair dados de FaturamentoProduto
        cod_produto = item_faturamento.cod_produto
        nome_produto = item_faturamento.nome_produto
        qtd_faturada = float(item_faturamento.qtd_produto_faturado or 0)
        valor_faturado = float(item_faturamento.valor_produto_faturado or 0)
        peso_total = float(item_faturamento.peso_total or 0)

        # Calcular pallets usando CadastroPalletizacao
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()

        pallets = 0
        if cadastro and cadastro.palletizacao and cadastro.palletizacao > 0:
            pallets = round(qtd_faturada / float(cadastro.palletizacao), 2)
        else:
            logger.warning(f"      ⚠️ CadastroPalletizacao não encontrado ou zerado para {cod_produto}")

        # Criar nova Separacao copiando TODOS os campos da exemplo
        nova_separacao = Separacao(
            # IDs e identificadores
            separacao_lote_id=separacao_lote_id,
            num_pedido=separacao_exemplo.num_pedido,
            numero_nf=numero_nf,

            # Dados do produto (vêm de FaturamentoProduto)
            cod_produto=cod_produto,
            nome_produto=nome_produto,
            qtd_saldo=qtd_faturada,
            valor_saldo=valor_faturado,
            peso=peso_total,
            pallet=pallets,

            # Cliente (copiado do exemplo)
            cnpj_cpf=separacao_exemplo.cnpj_cpf,
            raz_social_red=separacao_exemplo.raz_social_red,
            pedido_cliente=separacao_exemplo.pedido_cliente,

            # Localização (copiado do exemplo)
            nome_cidade=separacao_exemplo.nome_cidade,
            cod_uf=separacao_exemplo.cod_uf,
            cnpj_endereco_ent=separacao_exemplo.cnpj_endereco_ent,
            empresa_endereco_ent=separacao_exemplo.empresa_endereco_ent,
            cep_endereco_ent=separacao_exemplo.cep_endereco_ent,
            bairro_endereco_ent=separacao_exemplo.bairro_endereco_ent,
            rua_endereco_ent=separacao_exemplo.rua_endereco_ent,
            endereco_ent=separacao_exemplo.endereco_ent,
            telefone_endereco_ent=separacao_exemplo.telefone_endereco_ent,

            # Datas (copiado do exemplo)
            data_pedido=separacao_exemplo.data_pedido,
            expedicao=separacao_exemplo.expedicao,
            agendamento=separacao_exemplo.agendamento,
            protocolo=separacao_exemplo.protocolo,

            # Observações e roteamento (copiado do exemplo)
            observ_ped_1=separacao_exemplo.observ_ped_1,
            rota=separacao_exemplo.rota,
            sub_rota=separacao_exemplo.sub_rota,
            roteirizacao=separacao_exemplo.roteirizacao,

            # Status e controle (copiado do exemplo)
            status=separacao_exemplo.status,
            tipo_envio=separacao_exemplo.tipo_envio,
            sincronizado_nf=True,  # Mantém True conforme solicitado
            nf_cd=separacao_exemplo.nf_cd,
        )

        logger.info(f"      ✅ Criada Separacao para {cod_produto}: qtd={qtd_faturada}, valor=R${valor_faturado:.2f}, peso={peso_total}kg, pallets={pallets}")

        return nova_separacao
