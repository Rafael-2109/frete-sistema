"""
Service de NF de Remessa de Pallet - Dominio B

Este service gerencia todas as operacoes relacionadas a NFs de remessa de pallet:
- Importacao de NF do Odoo
- Consultas e listagens
- Cancelamento
- Registro de solucoes (devolucoes, retornos)
- Atualizacao de status

Regras de Negocio:
- REGRA 004: Devolucao 1:N - 1 NF devolucao pode fechar N NFs remessa
- REGRA 004: Retorno 1:1 - 1 NF retorno fecha apenas 1 NF remessa
- REGRA 005: Cancelamento - Nunca deletar, apenas marcar flags

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from app import db
from app.pallet.models.nf_remessa import PalletNFRemessa
from app.pallet.models.nf_solucao import PalletNFSolucao
from app.pallet.services.credito_service import CreditoService
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class NFService:
    """
    Service para gerenciamento de NFs de remessa de pallet (Dominio B).

    Responsabilidades:
    - Importar NF de remessa do Odoo
    - Consultar NFs por diferentes criterios
    - Cancelar NFs (nunca deletar)
    - Registrar solucoes documentais (devolucao, retorno, cancelamento)
    - Atualizar status baseado em resolucoes
    - Confirmar/rejeitar sugestoes de vinculacao
    """

    # =========================================================================
    # IMPORTACAO DE NF
    # =========================================================================

    @staticmethod
    def importar_nf_remessa_odoo(dados_odoo: dict, usuario: str = None) -> PalletNFRemessa:
        """
        Cria registro de NF de remessa a partir de dados importados do Odoo.

        Ao criar a NF de remessa, automaticamente cria o credito associado
        atraves do CreditoService.

        Args:
            dados_odoo: Dicionario com dados da NF do Odoo. Campos esperados:
                - numero_nf (str): Numero da NF (obrigatorio)
                - serie (str): Serie da NF (opcional)
                - chave_nfe (str): Chave da NF-e (opcional, unique)
                - data_emissao (datetime): Data de emissao (obrigatorio)
                - quantidade (int): Quantidade de pallets (obrigatorio)
                - empresa (str): CD, FB ou SC (obrigatorio)
                - tipo_destinatario (str): TRANSPORTADORA ou CLIENTE (obrigatorio)
                - cnpj_destinatario (str): CNPJ do destinatario (obrigatorio)
                - nome_destinatario (str): Nome do destinatario (opcional)
                - cnpj_transportadora (str): CNPJ da transportadora (opcional)
                - nome_transportadora (str): Nome da transportadora (opcional)
                - valor_unitario (Decimal): Valor unitario do pallet (opcional, default 35.00)
                - valor_total (Decimal): Valor total da NF (opcional)
                - odoo_account_move_id (int): ID do account.move no Odoo (opcional)
                - odoo_picking_id (int): ID do picking no Odoo (opcional)
                - embarque_id (int): ID do embarque local (opcional)
                - embarque_item_id (int): ID do embarque item local (opcional)
                - observacao (str): Observacoes (opcional)
            usuario: Usuario que esta realizando a importacao

        Returns:
            PalletNFRemessa: NF de remessa criada

        Raises:
            ValueError: Se campos obrigatorios estiverem faltando
            ValueError: Se NF com mesma chave_nfe ja existir
        """
        # Validar campos obrigatorios
        campos_obrigatorios = ['numero_nf', 'data_emissao', 'quantidade',
                               'empresa', 'tipo_destinatario', 'cnpj_destinatario']

        for campo in campos_obrigatorios:
            if campo not in dados_odoo or dados_odoo[campo] is None:
                raise ValueError(f"Campo obrigatorio ausente: {campo}")

        # Validar tipo_destinatario
        tipo_dest = dados_odoo['tipo_destinatario']
        if tipo_dest not in ('TRANSPORTADORA', 'CLIENTE'):
            raise ValueError(
                f"Tipo de destinatario invalido: {tipo_dest}. "
                "Use 'TRANSPORTADORA' ou 'CLIENTE'"
            )

        # Validar empresa
        empresa = dados_odoo['empresa']
        if empresa not in ('CD', 'FB', 'SC'):
            raise ValueError(
                f"Empresa invalida: {empresa}. "
                "Use 'CD', 'FB' ou 'SC'"
            )

        # Verificar duplicidade por chave_nfe (se fornecida)
        chave_nfe = dados_odoo.get('chave_nfe')
        if chave_nfe:
            existente = PalletNFRemessa.query.filter(
                PalletNFRemessa.chave_nfe == chave_nfe,
                PalletNFRemessa.ativo == True
            ).first()

            if existente:
                logger.warning(
                    f"NF com chave {chave_nfe} ja existe (#{existente.id})"
                )
                return existente

        # Criar NF de remessa
        nf_remessa = PalletNFRemessa(
            numero_nf=dados_odoo['numero_nf'],
            serie=dados_odoo.get('serie'),
            chave_nfe=chave_nfe,
            data_emissao=dados_odoo['data_emissao'],
            empresa=empresa,
            tipo_destinatario=tipo_dest,
            cnpj_destinatario=dados_odoo['cnpj_destinatario'],
            nome_destinatario=dados_odoo.get('nome_destinatario'),
            cnpj_transportadora=dados_odoo.get('cnpj_transportadora'),
            nome_transportadora=dados_odoo.get('nome_transportadora'),
            quantidade=dados_odoo['quantidade'],
            valor_unitario=dados_odoo.get('valor_unitario', Decimal('35.00')),
            valor_total=dados_odoo.get('valor_total'),
            odoo_account_move_id=dados_odoo.get('odoo_account_move_id'),
            odoo_picking_id=dados_odoo.get('odoo_picking_id'),
            embarque_id=dados_odoo.get('embarque_id'),
            embarque_item_id=dados_odoo.get('embarque_item_id'),
            movimentacao_estoque_id=dados_odoo.get('movimentacao_estoque_id'),
            observacao=dados_odoo.get('observacao'),
            status='ATIVA',
            criado_por=usuario or 'SISTEMA'
        )

        # Calcular valor_total se nao fornecido
        if not nf_remessa.valor_total and nf_remessa.valor_unitario:
            nf_remessa.valor_total = nf_remessa.valor_unitario * nf_remessa.quantidade

        try:
            db.session.add(nf_remessa)
            db.session.flush()  # Obter ID antes de criar credito

            # Criar credito automaticamente (REGRA 001)
            CreditoService.criar_credito_ao_importar_nf(
                nf_remessa_id=nf_remessa.id,
                usuario=usuario
            )

            db.session.commit()

            logger.info(
                f"NF de remessa #{nf_remessa.id} importada do Odoo "
                f"(NF {nf_remessa.numero_nf}, {nf_remessa.quantidade} pallets -> "
                f"{nf_remessa.tipo_destinatario}: {nf_remessa.nome_destinatario})"
            )

            return nf_remessa

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar NF de remessa: {e}")
            raise

    # =========================================================================
    # CONSULTAS
    # =========================================================================

    @staticmethod
    def obter_nf_por_id(nf_id: int) -> Optional[PalletNFRemessa]:
        """
        Busca NF de remessa por ID.

        Args:
            nf_id: ID da NF de remessa

        Returns:
            PalletNFRemessa ou None se nao encontrada

        Raises:
            ValueError: Se nf_id for None ou invalido
        """
        if not nf_id:
            raise ValueError("ID da NF e obrigatorio")

        return PalletNFRemessa.query.filter(
            PalletNFRemessa.id == nf_id,
            PalletNFRemessa.ativo == True
        ).first()

    @staticmethod
    def obter_nf_por_numero(numero_nf: str, serie: str = None) -> Optional[PalletNFRemessa]:
        """
        Busca NF de remessa por numero (e opcionalmente serie).

        Se houver multiplas NFs com o mesmo numero (series diferentes),
        retorna a mais recente.

        Args:
            numero_nf: Numero da NF
            serie: Serie da NF (opcional)

        Returns:
            PalletNFRemessa ou None se nao encontrada

        Raises:
            ValueError: Se numero_nf for vazio
        """
        if not numero_nf:
            raise ValueError("Numero da NF e obrigatorio")

        query = PalletNFRemessa.query.filter(
            PalletNFRemessa.numero_nf == numero_nf,
            PalletNFRemessa.ativo == True
        )

        if serie:
            query = query.filter(PalletNFRemessa.serie == serie)

        return query.order_by(PalletNFRemessa.criado_em.desc()).first()

    @staticmethod
    def obter_nf_por_chave(chave_nfe: str) -> Optional[PalletNFRemessa]:
        """
        Busca NF de remessa pela chave da NF-e.

        A chave NFe e unica, entao retorna no maximo 1 registro.

        Args:
            chave_nfe: Chave da NF-e (44 caracteres)

        Returns:
            PalletNFRemessa ou None se nao encontrada

        Raises:
            ValueError: Se chave_nfe for vazia ou invalida
        """
        if not chave_nfe:
            raise ValueError("Chave da NF-e e obrigatoria")

        if len(chave_nfe) != 44:
            logger.warning(f"Chave NFe com tamanho invalido: {len(chave_nfe)} chars")

        return PalletNFRemessa.query.filter(
            PalletNFRemessa.chave_nfe == chave_nfe,
            PalletNFRemessa.ativo == True
        ).first()

    @staticmethod
    def listar_nfs_ativas(
        cnpj_destinatario: str = None,
        tipo_destinatario: str = None,
        empresa: str = None,
        limite: int = 100
    ) -> List[PalletNFRemessa]:
        """
        Lista NFs de remessa ativas (nao canceladas).

        Args:
            cnpj_destinatario: Filtrar por CNPJ do destinatario (opcional)
            tipo_destinatario: Filtrar por tipo - TRANSPORTADORA ou CLIENTE (opcional)
            empresa: Filtrar por empresa emissora - CD, FB ou SC (opcional)
            limite: Quantidade maxima de registros (default 100)

        Returns:
            List[PalletNFRemessa]: Lista de NFs encontradas, ordenadas por data_emissao desc
        """
        query = PalletNFRemessa.query.filter(
            PalletNFRemessa.status.in_(['ATIVA', 'RESOLVIDA']),
            PalletNFRemessa.cancelada == False,
            PalletNFRemessa.ativo == True
        )

        if cnpj_destinatario:
            query = query.filter(
                PalletNFRemessa.cnpj_destinatario == cnpj_destinatario
            )

        if tipo_destinatario:
            if tipo_destinatario not in ('TRANSPORTADORA', 'CLIENTE'):
                raise ValueError(
                    f"Tipo de destinatario invalido: {tipo_destinatario}"
                )
            query = query.filter(
                PalletNFRemessa.tipo_destinatario == tipo_destinatario
            )

        if empresa:
            if empresa not in ('CD', 'FB', 'SC'):
                raise ValueError(f"Empresa invalida: {empresa}")
            query = query.filter(PalletNFRemessa.empresa == empresa)

        return query.order_by(
            PalletNFRemessa.data_emissao.desc()
        ).limit(limite).all()

    @staticmethod
    def listar_nfs_pendentes_vinculacao() -> List[PalletNFRemessa]:
        """
        Lista NFs ativas que possuem sugestoes de vinculacao pendentes de confirmacao.

        Retorna NFs que:
        - Estao com status ATIVA
        - Possuem pelo menos uma PalletNFSolucao com vinculacao='SUGESTAO'
          e confirmado=False e rejeitado=False

        Returns:
            List[PalletNFRemessa]: Lista de NFs com sugestoes pendentes
        """
        # Subquery para encontrar nf_remessa_ids com sugestoes pendentes
        subquery = db.session.query(PalletNFSolucao.nf_remessa_id).filter(
            PalletNFSolucao.vinculacao == 'SUGESTAO',
            PalletNFSolucao.confirmado == False,
            PalletNFSolucao.rejeitado == False,
            PalletNFSolucao.ativo == True
        ).distinct()

        return PalletNFRemessa.query.filter(
            PalletNFRemessa.status == 'ATIVA',
            PalletNFRemessa.cancelada == False,
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.id.in_(subquery)
        ).order_by(
            PalletNFRemessa.data_emissao.asc()
        ).all()

    # =========================================================================
    # CANCELAMENTO
    # =========================================================================

    @staticmethod
    def cancelar_nf(
        nf_remessa_id: int,
        motivo: str,
        usuario: str
    ) -> PalletNFRemessa:
        """
        Cancela uma NF de remessa.

        REGRA 005: Nunca deletar - sempre marcar flags de cancelamento.

        Args:
            nf_remessa_id: ID da NF de remessa
            motivo: Motivo do cancelamento
            usuario: Usuario que esta cancelando

        Returns:
            PalletNFRemessa: NF cancelada

        Raises:
            ValueError: Se NF nao encontrada ou ja cancelada
            ValueError: Se motivo ou usuario vazios
        """
        if not motivo:
            raise ValueError("Motivo do cancelamento e obrigatorio")

        if not usuario:
            raise ValueError("Usuario e obrigatorio")

        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        if not nf_remessa:
            raise ValueError(f"NF de remessa #{nf_remessa_id} nao encontrada")

        if nf_remessa.cancelada:
            logger.warning(
                f"NF #{nf_remessa_id} ja esta cancelada "
                f"(cancelada em {nf_remessa.cancelada_em} por {nf_remessa.cancelada_por})"
            )
            return nf_remessa

        if not nf_remessa.ativo:
            raise ValueError(f"NF de remessa #{nf_remessa_id} esta inativa")

        try:
            # Usar metodo do modelo que ja seta todos os campos
            nf_remessa.cancelar(motivo=motivo, usuario=usuario)

            db.session.commit()

            logger.info(
                f"NF de remessa #{nf_remessa_id} cancelada por {usuario}. "
                f"Motivo: {motivo}"
            )

            return nf_remessa

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cancelar NF #{nf_remessa_id}: {e}")
            raise

    # =========================================================================
    # ATUALIZACAO DE STATUS
    # =========================================================================

    @staticmethod
    def atualizar_status_nf(nf_remessa_id: int) -> PalletNFRemessa:
        """
        Atualiza o status da NF baseado nas solucoes registradas.

        Regras:
        - Se cancelada -> status='CANCELADA'
        - Se qtd_resolvida >= quantidade -> status='RESOLVIDA'
        - Caso contrario -> status='ATIVA' (mesmo parcialmente resolvida)

        Args:
            nf_remessa_id: ID da NF de remessa

        Returns:
            PalletNFRemessa: NF com status atualizado

        Raises:
            ValueError: Se NF nao encontrada
        """
        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        if not nf_remessa:
            raise ValueError(f"NF de remessa #{nf_remessa_id} nao encontrada")

        try:
            # Recalcular qtd_resolvida baseado nas solucoes confirmadas
            total_resolvido = db.session.query(
                db.func.sum(PalletNFSolucao.quantidade)
            ).filter(
                PalletNFSolucao.nf_remessa_id == nf_remessa_id,
                PalletNFSolucao.confirmado == True,
                PalletNFSolucao.rejeitado == False,
                PalletNFSolucao.ativo == True
            ).scalar() or 0

            nf_remessa.qtd_resolvida = total_resolvido

            # Usar metodo do modelo para atualizar status
            nf_remessa.atualizar_status()
            nf_remessa.atualizado_em = agora_utc_naive()

            db.session.commit()

            logger.info(
                f"Status da NF #{nf_remessa_id} atualizado: {nf_remessa.status} "
                f"(resolvido: {nf_remessa.qtd_resolvida}/{nf_remessa.quantidade})"
            )

            return nf_remessa

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar status da NF #{nf_remessa_id}: {e}")
            raise

    # =========================================================================
    # REGISTRO DE SOLUCOES
    # =========================================================================

    @staticmethod
    def registrar_solucao_nf(
        nf_remessa_id: int,
        tipo: str,
        quantidade: int,
        dados: dict,
        usuario: str
    ) -> PalletNFSolucao:
        """
        Registra uma solucao documental para a NF de remessa.

        Tipos de solucao:
        - DEVOLUCAO: NF de devolucao emitida pelo destinatario (1:N com remessas)
        - RECUSA: NF recusada pelo destinatario (sem NF, registro manual)
        - CANCELAMENTO: NF foi cancelada (importado do Odoo)
        - NOTA_CREDITO: NC vinculada automaticamente via reversed_entry_id

        Args:
            nf_remessa_id: ID da NF de remessa
            tipo: Tipo da solucao - DEVOLUCAO, RECUSA, CANCELAMENTO ou NOTA_CREDITO
            quantidade: Quantidade de pallets resolvidos nesta solucao
            dados: Dados adicionais da solucao. Campos esperados:
                Para DEVOLUCAO e NOTA_CREDITO:
                - numero_nf_solucao (str): Numero da NF de devolucao/retorno
                - serie_nf_solucao (str): Serie da NF (opcional)
                - chave_nfe_solucao (str): Chave da NF-e (opcional)
                - data_nf_solucao (datetime): Data da NF
                - cnpj_emitente (str): CNPJ do emitente
                - nome_emitente (str): Nome do emitente
                - info_complementar (str): Info complementar para match (opcional)
                - vinculacao (str): AUTOMATICO, MANUAL ou SUGESTAO (default MANUAL)
                - odoo_account_move_id (int): ID do account.move no Odoo (opcional)
                - odoo_dfe_id (int): ID do DFe no Odoo (opcional)
                - observacao (str): Observacoes (opcional)
                Para CANCELAMENTO:
                - observacao (str): Observacoes/motivo
            usuario: Usuario que esta registrando

        Returns:
            PalletNFSolucao: Solucao criada

        Raises:
            ValueError: Se NF nao encontrada ou dados invalidos
        """
        # Validar NF de remessa
        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        if not nf_remessa:
            raise ValueError(f"NF de remessa #{nf_remessa_id} nao encontrada")

        if nf_remessa.cancelada:
            raise ValueError(f"NF de remessa #{nf_remessa_id} esta cancelada")

        if not nf_remessa.ativo:
            raise ValueError(f"NF de remessa #{nf_remessa_id} esta inativa")

        # Validar tipo
        tipos_validos = ('DEVOLUCAO', 'RECUSA', 'CANCELAMENTO', 'NOTA_CREDITO')
        if tipo not in tipos_validos:
            raise ValueError(
                f"Tipo de solucao invalido: {tipo}. "
                f"Use: {', '.join(tipos_validos)}"
            )

        # Validar quantidade
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        # Verificar se quantidade nao excede o pendente
        if quantidade > nf_remessa.qtd_pendente:
            raise ValueError(
                f"Quantidade ({quantidade}) maior que pendente ({nf_remessa.qtd_pendente})"
            )

        # Validar usuario
        if not usuario:
            raise ValueError("Usuario e obrigatorio")

        dados = dados or {}
        vinculacao = dados.get('vinculacao', 'MANUAL')

        try:
            # Criar solucao usando factory methods do modelo
            if tipo == 'DEVOLUCAO':
                # Verificar duplicidade
                if PalletNFSolucao.verificar_duplicidade(
                    numero_nf=dados.get('numero_nf_solucao', ''),
                    cnpj_emitente=dados.get('cnpj_emitente', ''),
                    nf_remessa_id=nf_remessa_id
                ):
                    raise ValueError(
                        f"Ja existe solucao para NF {dados.get('numero_nf_solucao')} "
                        f"do emitente {dados.get('cnpj_emitente')}"
                    )

                solucao = PalletNFSolucao.criar_devolucao(
                    nf_remessa_id=nf_remessa_id,
                    quantidade=quantidade,
                    numero_nf=dados.get('numero_nf_solucao', ''),
                    data_nf=dados.get('data_nf_solucao'),
                    cnpj_emitente=dados.get('cnpj_emitente', ''),
                    nome_emitente=dados.get('nome_emitente', ''),
                    usuario=usuario,
                    vinculacao=vinculacao,
                    chave_nfe=dados.get('chave_nfe_solucao'),
                    serie=dados.get('serie_nf_solucao'),
                    observacao=dados.get('observacao')
                )

            elif tipo == 'RECUSA':
                # RECUSA: NF recusada pelo cliente (sem NF, registro manual)
                solucao = PalletNFSolucao.criar_recusa(
                    nf_remessa_id=nf_remessa_id,
                    quantidade=quantidade,
                    usuario=usuario,
                    motivo_recusa=dados.get('info_complementar', dados.get('motivo_recusa', '')),
                    observacao=dados.get('observacao')
                )

            elif tipo == 'NOTA_CREDITO':
                # NOTA_CREDITO: vinculado automaticamente via reversed_entry_id
                solucao = PalletNFSolucao.criar_nota_credito(
                    nf_remessa_id=nf_remessa_id,
                    quantidade=quantidade,
                    numero_nf=dados.get('numero_nf_solucao', ''),
                    data_nf=dados.get('data_nf_solucao'),
                    cnpj_destinatario=dados.get('cnpj_emitente', ''),
                    nome_destinatario=dados.get('nome_emitente', ''),
                    odoo_account_move_id=dados.get('odoo_account_move_id', 0),
                    usuario=usuario,
                    chave_nfe=dados.get('chave_nfe_solucao'),
                    observacao=dados.get('observacao')
                )

            elif tipo == 'CANCELAMENTO':
                solucao = PalletNFSolucao.criar_cancelamento(
                    nf_remessa_id=nf_remessa_id,
                    quantidade=quantidade,
                    usuario=usuario,
                    observacao=dados.get('observacao')
                )

            # Adicionar campos extras do Odoo se fornecidos
            if dados.get('odoo_account_move_id'):
                solucao.odoo_account_move_id = dados['odoo_account_move_id']
            if dados.get('odoo_dfe_id'):
                solucao.odoo_dfe_id = dados['odoo_dfe_id']

            db.session.add(solucao)
            db.session.flush()

            # Atualizar qtd_resolvida e status da NF (apenas se confirmada)
            if solucao.confirmado:
                nf_remessa.qtd_resolvida = (nf_remessa.qtd_resolvida or 0) + quantidade
                nf_remessa.atualizar_status()

            db.session.commit()

            logger.info(
                f"Solucao {tipo} #{solucao.id} registrada para NF #{nf_remessa_id} "
                f"({quantidade} pallets, vinculacao: {vinculacao})"
            )

            return solucao

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Erro ao registrar solucao {tipo} para NF #{nf_remessa_id}: {e}"
            )
            raise

    # =========================================================================
    # CONFIRMACAO/REJEICAO DE SUGESTOES
    # =========================================================================

    @staticmethod
    def confirmar_sugestao(nf_solucao_id: int, usuario: str) -> PalletNFSolucao:
        """
        Confirma uma sugestao de vinculacao.

        Quando confirmada:
        - Define confirmado=True
        - Atualiza qtd_resolvida da NF de remessa
        - Atualiza status da NF de remessa

        Args:
            nf_solucao_id: ID da solucao (sugestao)
            usuario: Usuario que esta confirmando

        Returns:
            PalletNFSolucao: Solucao confirmada

        Raises:
            ValueError: Se solucao nao encontrada ou nao e uma sugestao
        """
        if not usuario:
            raise ValueError("Usuario e obrigatorio")

        solucao = PalletNFSolucao.query.get(nf_solucao_id)
        if not solucao:
            raise ValueError(f"Solucao #{nf_solucao_id} nao encontrada")

        if not solucao.ativo:
            raise ValueError(f"Solucao #{nf_solucao_id} esta inativa")

        if solucao.vinculacao != 'SUGESTAO':
            raise ValueError(
                f"Solucao #{nf_solucao_id} nao e uma sugestao "
                f"(vinculacao atual: {solucao.vinculacao})"
            )

        if solucao.confirmado:
            logger.warning(f"Solucao #{nf_solucao_id} ja esta confirmada")
            return solucao

        if solucao.rejeitado:
            raise ValueError(f"Solucao #{nf_solucao_id} ja foi rejeitada")

        try:
            # Usar metodo do modelo
            solucao.confirmar(usuario)

            # Atualizar NF de remessa
            nf_remessa = solucao.nf_remessa
            nf_remessa.qtd_resolvida = (nf_remessa.qtd_resolvida or 0) + solucao.quantidade
            nf_remessa.atualizar_status()

            db.session.commit()

            logger.info(
                f"Sugestao #{nf_solucao_id} confirmada por {usuario} "
                f"(NF remessa #{nf_remessa.id}: {nf_remessa.status})"
            )

            return solucao

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao confirmar sugestao #{nf_solucao_id}: {e}")
            raise

    @staticmethod
    def rejeitar_sugestao(
        nf_solucao_id: int,
        motivo: str,
        usuario: str
    ) -> PalletNFSolucao:
        """
        Rejeita uma sugestao de vinculacao.

        A sugestao rejeitada permanece no banco para auditoria,
        mas nao afeta o saldo da NF de remessa.

        Args:
            nf_solucao_id: ID da solucao (sugestao)
            motivo: Motivo da rejeicao
            usuario: Usuario que esta rejeitando

        Returns:
            PalletNFSolucao: Solucao rejeitada

        Raises:
            ValueError: Se solucao nao encontrada ou nao e uma sugestao
        """
        if not motivo:
            raise ValueError("Motivo da rejeicao e obrigatorio")

        if not usuario:
            raise ValueError("Usuario e obrigatorio")

        solucao = PalletNFSolucao.query.get(nf_solucao_id)
        if not solucao:
            raise ValueError(f"Solucao #{nf_solucao_id} nao encontrada")

        if not solucao.ativo:
            raise ValueError(f"Solucao #{nf_solucao_id} esta inativa")

        if solucao.vinculacao != 'SUGESTAO':
            raise ValueError(
                f"Solucao #{nf_solucao_id} nao e uma sugestao "
                f"(vinculacao atual: {solucao.vinculacao})"
            )

        if solucao.rejeitado:
            logger.warning(f"Solucao #{nf_solucao_id} ja esta rejeitada")
            return solucao

        if solucao.confirmado:
            raise ValueError(
                f"Solucao #{nf_solucao_id} ja foi confirmada - "
                "nao pode ser rejeitada"
            )

        try:
            # Usar metodo do modelo
            solucao.rejeitar(usuario, motivo)

            db.session.commit()

            logger.info(
                f"Sugestao #{nf_solucao_id} rejeitada por {usuario}. "
                f"Motivo: {motivo}"
            )

            return solucao

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao rejeitar sugestao #{nf_solucao_id}: {e}")
            raise

    # =========================================================================
    # RESUMO
    # =========================================================================

    @staticmethod
    def obter_resumo_nf(nf_remessa_id: int) -> Dict:
        """
        Retorna resumo completo de uma NF de remessa.

        Inclui:
        - Dados da NF
        - Quantidades (original, resolvida, pendente)
        - Status
        - Lista de solucoes

        Args:
            nf_remessa_id: ID da NF de remessa

        Returns:
            Dict com resumo completo:
            {
                'nf_remessa_id': int,
                'numero_nf': str,
                'serie': str,
                'chave_nfe': str,
                'data_emissao': datetime,
                'empresa': str,
                'tipo_destinatario': str,
                'cnpj_destinatario': str,
                'nome_destinatario': str,
                'qtd_original': int,
                'qtd_resolvida': int,
                'qtd_pendente': int,
                'percentual_resolvido': float,
                'status': str,
                'cancelada': bool,
                'solucoes': [
                    {
                        'id': int,
                        'tipo': str,
                        'quantidade': int,
                        'numero_nf_solucao': str,
                        'vinculacao': str,
                        'status_display': str,
                        'criado_em': datetime,
                        'criado_por': str
                    },
                    ...
                ],
                'sugestoes_pendentes': int
            }

        Raises:
            ValueError: Se NF nao encontrada
        """
        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        if not nf_remessa:
            raise ValueError(f"NF de remessa #{nf_remessa_id} nao encontrada")

        # Buscar solucoes
        solucoes = PalletNFSolucao.listar_por_nf_remessa(
            nf_remessa_id=nf_remessa_id,
            apenas_confirmadas=False
        ).all()

        # Contar sugestoes pendentes
        sugestoes_pendentes = sum(
            1 for s in solucoes
            if s.vinculacao == 'SUGESTAO' and not s.confirmado and not s.rejeitado
        )

        # Calcular percentual
        percentual = 0.0
        if nf_remessa.quantidade > 0:
            percentual = (
                (nf_remessa.qtd_resolvida or 0) / nf_remessa.quantidade
            ) * 100

        return {
            'nf_remessa_id': nf_remessa.id,
            'numero_nf': nf_remessa.numero_nf,
            'serie': nf_remessa.serie,
            'chave_nfe': nf_remessa.chave_nfe,
            'data_emissao': nf_remessa.data_emissao,
            'empresa': nf_remessa.empresa,
            'tipo_destinatario': nf_remessa.tipo_destinatario,
            'cnpj_destinatario': nf_remessa.cnpj_destinatario,
            'nome_destinatario': nf_remessa.nome_destinatario,
            'qtd_original': nf_remessa.quantidade,
            'qtd_resolvida': nf_remessa.qtd_resolvida or 0,
            'qtd_pendente': nf_remessa.qtd_pendente,
            'percentual_resolvido': round(percentual, 2),
            'status': nf_remessa.status,
            'cancelada': nf_remessa.cancelada,
            'motivo_cancelamento': nf_remessa.motivo_cancelamento,
            'solucoes': [
                {
                    'id': s.id,
                    'tipo': s.tipo,
                    'tipo_display': s.tipo_display,
                    'quantidade': s.quantidade,
                    'numero_nf_solucao': s.numero_nf_solucao,
                    'data_nf_solucao': s.data_nf_solucao,
                    'cnpj_emitente': s.cnpj_emitente,
                    'nome_emitente': s.nome_emitente,
                    'vinculacao': s.vinculacao,
                    'vinculacao_display': s.vinculacao_display,
                    'status_display': s.status_display,
                    'confirmado': s.confirmado,
                    'rejeitado': s.rejeitado,
                    'criado_em': s.criado_em,
                    'criado_por': s.criado_por
                }
                for s in solucoes
            ],
            'sugestoes_pendentes': sugestoes_pendentes
        }
