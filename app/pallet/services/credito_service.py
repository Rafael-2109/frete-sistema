"""
Service de Crédito de Pallet - Domínio A

Este service gerencia todas as operações relacionadas a créditos de pallet:
- Criação automática de crédito ao importar NF de remessa
- Registro de documentos (canhotos, vales)
- Registro de soluções (baixa, venda, recebimento, substituição)
- Cálculo e atualização de saldos

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app import db
from app.pallet.models.nf_remessa import PalletNFRemessa
from app.pallet.models.credito import PalletCredito
from app.pallet.models.documento import PalletDocumento
from app.pallet.models.solucao import PalletSolucao

logger = logging.getLogger(__name__)


class CreditoService:
    """
    Service para gerenciamento de créditos de pallet (Domínio A).

    Responsabilidades:
    - Criar crédito automaticamente ao importar NF de remessa
    - Registrar documentos que enriquecem o crédito
    - Registrar soluções que decrementam o saldo
    - Calcular e atualizar status do crédito
    """

    # =========================================================================
    # CRIAÇÃO DE CRÉDITO
    # =========================================================================

    @staticmethod
    def criar_credito_ao_importar_nf(
        nf_remessa_id: int,
        usuario: str = None
    ) -> PalletCredito:
        """
        Cria um crédito automaticamente ao importar uma NF de remessa.

        REGRA 001 (PRD): Ao IMPORTAR NF de remessa do Odoo:
        - CRIAR registro em pallet_creditos vinculado automaticamente
        - qtd_saldo inicial = quantidade da NF importada

        Args:
            nf_remessa_id: ID da NF de remessa recém-criada
            usuario: Usuário que está realizando a operação

        Returns:
            PalletCredito: Crédito criado

        Raises:
            ValueError: Se NF não existe ou já tem crédito
        """
        # Buscar NF de remessa
        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        if not nf_remessa:
            raise ValueError(f"NF de remessa #{nf_remessa_id} não encontrada")

        # Verificar se já existe crédito para esta NF
        credito_existente = PalletCredito.query.filter(
            PalletCredito.nf_remessa_id == nf_remessa_id,
            PalletCredito.ativo == True
        ).first()

        if credito_existente:
            logger.warning(
                f"NF #{nf_remessa_id} já possui crédito #{credito_existente.id}"
            )
            return credito_existente

        # Criar crédito
        credito = PalletCredito(
            nf_remessa_id=nf_remessa_id,
            qtd_original=nf_remessa.quantidade,
            qtd_saldo=nf_remessa.quantidade,  # Saldo inicial = quantidade total
            tipo_responsavel=nf_remessa.tipo_destinatario,
            cnpj_responsavel=nf_remessa.cnpj_destinatario,
            nome_responsavel=nf_remessa.nome_destinatario,
            status='PENDENTE',
            criado_por=usuario or 'SISTEMA'
        )

        # Calcular prazo de cobrança
        credito.calcular_prazo()

        db.session.add(credito)
        db.session.commit()

        logger.info(
            f"✅ Crédito #{credito.id} criado para NF #{nf_remessa_id} "
            f"({nf_remessa.quantidade} pallets)"
        )

        return credito

    @staticmethod
    def criar_credito_manual(
        nf_remessa_id: int,
        quantidade: int,
        tipo_responsavel: str,
        cnpj_responsavel: str,
        nome_responsavel: str,
        usuario: str,
        uf_responsavel: str = None,
        cidade_responsavel: str = None,
        observacao: str = None
    ) -> PalletCredito:
        """
        Cria um crédito manualmente (para casos especiais ou correções).

        Args:
            nf_remessa_id: ID da NF de remessa
            quantidade: Quantidade de pallets
            tipo_responsavel: 'TRANSPORTADORA' ou 'CLIENTE'
            cnpj_responsavel: CNPJ do responsável
            nome_responsavel: Nome do responsável
            usuario: Usuário que está criando
            uf_responsavel: UF do responsável (opcional)
            cidade_responsavel: Cidade do responsável (opcional)
            observacao: Observações (opcional)

        Returns:
            PalletCredito: Crédito criado
        """
        # Validar NF de remessa
        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        if not nf_remessa:
            raise ValueError(f"NF de remessa #{nf_remessa_id} não encontrada")

        # Validar tipo de responsável
        if tipo_responsavel not in ('TRANSPORTADORA', 'CLIENTE'):
            raise ValueError(
                f"Tipo de responsável inválido: {tipo_responsavel}. "
                "Use 'TRANSPORTADORA' ou 'CLIENTE'"
            )

        # Criar crédito
        credito = PalletCredito(
            nf_remessa_id=nf_remessa_id,
            qtd_original=quantidade,
            qtd_saldo=quantidade,
            tipo_responsavel=tipo_responsavel,
            cnpj_responsavel=cnpj_responsavel,
            nome_responsavel=nome_responsavel,
            uf_responsavel=uf_responsavel,
            cidade_responsavel=cidade_responsavel,
            status='PENDENTE',
            observacao=observacao,
            criado_por=usuario
        )

        # Calcular prazo
        credito.calcular_prazo(uf=uf_responsavel)

        db.session.add(credito)
        db.session.commit()

        logger.info(
            f"✅ Crédito manual #{credito.id} criado para NF #{nf_remessa_id} "
            f"({quantidade} pallets -> {nome_responsavel})"
        )

        return credito

    # =========================================================================
    # REGISTRO DE DOCUMENTOS
    # =========================================================================

    @staticmethod
    def registrar_documento(
        credito_id: int,
        tipo: str,
        quantidade: int,
        usuario: str,
        numero_documento: str = None,
        data_emissao: date = None,
        data_validade: date = None,
        cnpj_emissor: str = None,
        nome_emissor: str = None,
        arquivo_path: str = None,
        arquivo_nome: str = None,
        arquivo_tipo: str = None,
        observacao: str = None
    ) -> PalletDocumento:
        """
        Registra um documento que enriquece o crédito (canhoto ou vale pallet).

        Args:
            credito_id: ID do crédito
            tipo: 'CANHOTO' ou 'VALE_PALLET'
            quantidade: Quantidade de pallets no documento
            usuario: Usuário que está registrando
            numero_documento: Número do documento (para vale pallet)
            data_emissao: Data de emissão
            data_validade: Data de validade
            cnpj_emissor: CNPJ de quem emitiu
            nome_emissor: Nome de quem emitiu
            arquivo_path: Caminho do arquivo anexo
            arquivo_nome: Nome original do arquivo
            arquivo_tipo: MIME type do arquivo
            observacao: Observações

        Returns:
            PalletDocumento: Documento registrado
        """
        # Buscar crédito
        credito = PalletCredito.query.get(credito_id)
        if not credito:
            raise ValueError(f"Crédito #{credito_id} não encontrado")

        if not credito.ativo:
            raise ValueError(f"Crédito #{credito_id} está inativo")

        # Validar tipo
        if tipo not in ('CANHOTO', 'VALE_PALLET'):
            raise ValueError(
                f"Tipo de documento inválido: {tipo}. "
                "Use 'CANHOTO' ou 'VALE_PALLET'"
            )

        # Validar quantidade
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        # Criar documento
        documento = PalletDocumento(
            credito_id=credito_id,
            tipo=tipo,
            quantidade=quantidade,
            numero_documento=numero_documento,
            data_emissao=data_emissao,
            data_validade=data_validade,
            cnpj_emissor=cnpj_emissor,
            nome_emissor=nome_emissor,
            arquivo_path=arquivo_path,
            arquivo_nome=arquivo_nome,
            arquivo_tipo=arquivo_tipo,
            observacao=observacao,
            criado_por=usuario
        )

        db.session.add(documento)
        db.session.commit()

        logger.info(
            f"✅ Documento {tipo} #{documento.id} registrado para crédito #{credito_id} "
            f"({quantidade} pallets)"
        )

        return documento

    @staticmethod
    def registrar_recebimento_documento(
        documento_id: int,
        usuario: str,
        pasta_arquivo: str = None,
        aba_arquivo: str = None
    ) -> PalletDocumento:
        """
        Registra o recebimento físico de um documento pela Nacom.

        Args:
            documento_id: ID do documento
            usuario: Usuário que recebeu
            pasta_arquivo: Pasta onde foi arquivado
            aba_arquivo: Aba/divisória onde foi arquivado

        Returns:
            PalletDocumento: Documento atualizado
        """
        documento = PalletDocumento.query.get(documento_id)
        if not documento:
            raise ValueError(f"Documento #{documento_id} não encontrado")

        if documento.recebido:
            logger.warning(f"Documento #{documento_id} já foi recebido anteriormente")
            return documento

        documento.registrar_recebimento(usuario)
        documento.pasta_arquivo = pasta_arquivo
        documento.aba_arquivo = aba_arquivo

        db.session.commit()

        logger.info(f"✅ Documento #{documento_id} marcado como recebido por {usuario}")

        return documento

    # =========================================================================
    # REGISTRO DE SOLUÇÕES
    # =========================================================================

    @staticmethod
    def registrar_solucao(
        credito_id: int,
        tipo_solucao: str,
        quantidade: int,
        usuario: str,
        dados_adicionais: dict = None
    ) -> Tuple[PalletSolucao, PalletCredito]:
        """
        Registra uma solução genérica para o crédito.

        REGRA 002 (PRD): Qualquer solução de pallet:
        - DECREMENTA pallet_credito.qtd_saldo
        - CRIA registro em pallet_solucao
        - Se qtd_saldo = 0, status = 'RESOLVIDO'
        - Se qtd_saldo > 0 e < original, status = 'PARCIAL'

        Args:
            credito_id: ID do crédito
            tipo_solucao: 'BAIXA', 'VENDA', 'RECEBIMENTO', 'SUBSTITUICAO'
            quantidade: Quantidade sendo resolvida
            usuario: Usuário que está registrando
            dados_adicionais: Dados específicos do tipo de solução

        Returns:
            Tuple[PalletSolucao, PalletCredito]: Solução criada e crédito atualizado
        """
        # Buscar crédito
        credito = PalletCredito.query.get(credito_id)
        if not credito:
            raise ValueError(f"Crédito #{credito_id} não encontrado")

        if not credito.ativo:
            raise ValueError(f"Crédito #{credito_id} está inativo")

        if credito.status == 'RESOLVIDO':
            raise ValueError(f"Crédito #{credito_id} já está totalmente resolvido")

        # Validar quantidade
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        if quantidade > credito.qtd_saldo:
            raise ValueError(
                f"Quantidade ({quantidade}) maior que saldo disponível ({credito.qtd_saldo})"
            )

        # Validar tipo
        tipos_validos = ('BAIXA', 'VENDA', 'RECEBIMENTO', 'SUBSTITUICAO')
        if tipo_solucao not in tipos_validos:
            raise ValueError(
                f"Tipo de solução inválido: {tipo_solucao}. "
                f"Use: {', '.join(tipos_validos)}"
            )

        dados = dados_adicionais or {}

        # Criar solução usando factory methods
        if tipo_solucao == 'BAIXA':
            solucao = PalletSolucao.criar_baixa(
                credito_id=credito_id,
                quantidade=quantidade,
                motivo=dados.get('motivo', ''),
                confirmado=dados.get('confirmado', False),
                usuario=usuario,
                observacao=dados.get('observacao')
            )
        elif tipo_solucao == 'VENDA':
            solucao = PalletSolucao.criar_venda(
                credito_id=credito_id,
                quantidade=quantidade,
                nf_venda=dados.get('nf_venda', ''),
                data_venda=dados.get('data_venda'),
                valor_unitario=dados.get('valor_unitario', 0),
                cnpj_comprador=dados.get('cnpj_comprador', ''),
                nome_comprador=dados.get('nome_comprador', ''),
                usuario=usuario,
                observacao=dados.get('observacao'),
                chave_nfe=dados.get('chave_nfe')
            )
        elif tipo_solucao == 'RECEBIMENTO':
            solucao = PalletSolucao.criar_recebimento(
                credito_id=credito_id,
                quantidade=quantidade,
                data_recebimento=dados.get('data_recebimento'),
                local=dados.get('local', ''),
                recebido_de=dados.get('recebido_de', ''),
                cnpj_entregador=dados.get('cnpj_entregador', ''),
                usuario=usuario,
                observacao=dados.get('observacao')
            )
        elif tipo_solucao == 'SUBSTITUICAO':
            solucao = PalletSolucao.criar_substituicao(
                credito_id=credito_id,
                credito_destino_id=dados.get('credito_destino_id'),
                quantidade=quantidade,
                nf_destino=dados.get('nf_destino', ''),
                motivo=dados.get('motivo', ''),
                usuario=usuario,
                observacao=dados.get('observacao')
            )

        # Decrementar saldo do crédito
        credito.registrar_solucao(quantidade)

        db.session.add(solucao)
        db.session.commit()

        logger.info(
            f"✅ Solução {tipo_solucao} #{solucao.id} registrada para crédito #{credito_id} "
            f"({quantidade} pallets, saldo: {credito.qtd_saldo})"
        )

        return solucao, credito

    @staticmethod
    def registrar_baixa(
        credito_id: int,
        quantidade: int,
        motivo: str,
        confirmado_cliente: bool,
        usuario: str,
        observacao: str = None
    ) -> Tuple[PalletSolucao, PalletCredito]:
        """
        Registra uma baixa (descarte) de pallets.

        Baixa é usado quando o cliente confirma que não devolverá os pallets
        (descartáveis, perdidos, etc.).

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade sendo baixada
            motivo: Motivo da baixa
            confirmado_cliente: Se cliente confirmou a baixa
            usuario: Usuário que está registrando
            observacao: Observações

        Returns:
            Tuple[PalletSolucao, PalletCredito]: Solução criada e crédito atualizado
        """
        return CreditoService.registrar_solucao(
            credito_id=credito_id,
            tipo_solucao='BAIXA',
            quantidade=quantidade,
            usuario=usuario,
            dados_adicionais={
                'motivo': motivo,
                'confirmado': confirmado_cliente,
                'observacao': observacao
            }
        )

    @staticmethod
    def registrar_venda(
        creditos_quantidades: List[Dict],
        nf_venda: str,
        data_venda: date,
        valor_unitario: float,
        cnpj_comprador: str,
        nome_comprador: str,
        usuario: str,
        chave_nfe: str = None,
        observacao: str = None
    ) -> List[Tuple[PalletSolucao, PalletCredito]]:
        """
        Registra uma venda de pallets (N NFs remessa → 1 NF venda).

        Permite vincular múltiplos créditos a uma única NF de venda.

        Args:
            creditos_quantidades: Lista de dicts {'credito_id': int, 'quantidade': int}
            nf_venda: Número da NF de venda
            data_venda: Data da venda
            valor_unitario: Valor unitário do pallet
            cnpj_comprador: CNPJ do comprador
            nome_comprador: Nome do comprador
            usuario: Usuário que está registrando
            chave_nfe: Chave da NF-e (opcional)
            observacao: Observações

        Returns:
            List[Tuple]: Lista de (solução, crédito) para cada crédito processado
        """
        resultados = []

        for item in creditos_quantidades:
            credito_id = item['credito_id']
            quantidade = item['quantidade']

            solucao, credito = CreditoService.registrar_solucao(
                credito_id=credito_id,
                tipo_solucao='VENDA',
                quantidade=quantidade,
                usuario=usuario,
                dados_adicionais={
                    'nf_venda': nf_venda,
                    'data_venda': data_venda,
                    'valor_unitario': valor_unitario,
                    'cnpj_comprador': cnpj_comprador,
                    'nome_comprador': nome_comprador,
                    'chave_nfe': chave_nfe,
                    'observacao': observacao
                }
            )
            resultados.append((solucao, credito))

        logger.info(
            f"✅ Venda NF {nf_venda} registrada para {len(resultados)} créditos"
        )

        return resultados

    @staticmethod
    def registrar_recebimento(
        credito_id: int,
        quantidade: int,
        data_recebimento: date,
        local: str,
        recebido_de: str,
        cnpj_entregador: str,
        usuario: str,
        observacao: str = None
    ) -> Tuple[PalletSolucao, PalletCredito]:
        """
        Registra o recebimento físico de pallets (coleta).

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade recebida
            data_recebimento: Data do recebimento
            local: Local onde foi recebido
            recebido_de: Nome de quem entregou
            cnpj_entregador: CNPJ de quem entregou
            usuario: Usuário que está registrando
            observacao: Observações

        Returns:
            Tuple[PalletSolucao, PalletCredito]: Solução criada e crédito atualizado
        """
        return CreditoService.registrar_solucao(
            credito_id=credito_id,
            tipo_solucao='RECEBIMENTO',
            quantidade=quantidade,
            usuario=usuario,
            dados_adicionais={
                'data_recebimento': data_recebimento,
                'local': local,
                'recebido_de': recebido_de,
                'cnpj_entregador': cnpj_entregador,
                'observacao': observacao
            }
        )

    @staticmethod
    def registrar_substituicao(
        credito_origem_id: int,
        credito_destino_id: int,
        quantidade: int,
        usuario: str,
        motivo: str,
        nf_destino: str = None,
        observacao: str = None
    ) -> Tuple[PalletSolucao, PalletCredito, PalletCredito]:
        """
        Registra uma substituição de responsabilidade.

        REGRA 003 (PRD): Substituição de responsabilidade:
        - DECREMENTA saldo do crédito origem
        - INCREMENTA saldo do crédito destino (ou cria novo)
        - Mantém rastreabilidade via pallet_solucao.credito_destino_id

        Args:
            credito_origem_id: ID do crédito de origem
            credito_destino_id: ID do crédito de destino
            quantidade: Quantidade sendo transferida
            usuario: Usuário que está registrando
            motivo: Motivo da substituição
            nf_destino: NF da nova remessa (opcional)
            observacao: Observações

        Returns:
            Tuple: (solução, crédito_origem, crédito_destino)
        """
        # Validar crédito destino
        credito_destino = PalletCredito.query.get(credito_destino_id)
        if not credito_destino:
            raise ValueError(f"Crédito destino #{credito_destino_id} não encontrado")

        if not credito_destino.ativo:
            raise ValueError(f"Crédito destino #{credito_destino_id} está inativo")

        # Registrar solução de substituição no crédito origem
        solucao, credito_origem = CreditoService.registrar_solucao(
            credito_id=credito_origem_id,
            tipo_solucao='SUBSTITUICAO',
            quantidade=quantidade,
            usuario=usuario,
            dados_adicionais={
                'credito_destino_id': credito_destino_id,
                'nf_destino': nf_destino,
                'motivo': motivo,
                'observacao': observacao
            }
        )

        # Incrementar saldo do crédito destino
        credito_destino.qtd_saldo += quantidade
        credito_destino.qtd_original += quantidade
        credito_destino.atualizar_status()
        credito_destino.atualizado_por = usuario

        db.session.commit()

        logger.info(
            f"✅ Substituição: {quantidade} pallets transferidos de crédito "
            f"#{credito_origem_id} para #{credito_destino_id}"
        )

        return solucao, credito_origem, credito_destino

    # =========================================================================
    # CÁLCULOS E CONSULTAS
    # =========================================================================

    @staticmethod
    def calcular_saldo_credito(credito_id: int) -> Dict:
        """
        Calcula o saldo atual de um crédito considerando todas as soluções.

        Args:
            credito_id: ID do crédito

        Returns:
            Dict com informações do saldo
        """
        credito = PalletCredito.query.get(credito_id)
        if not credito:
            raise ValueError(f"Crédito #{credito_id} não encontrado")

        # Calcular totais por tipo de solução
        totais_solucao = PalletSolucao.total_por_tipo(credito_id)

        return {
            'credito_id': credito_id,
            'qtd_original': credito.qtd_original,
            'qtd_saldo': credito.qtd_saldo,
            'qtd_resolvida': credito.qtd_resolvida,
            'percentual_resolvido': credito.percentual_resolvido,
            'status': credito.status,
            'totais_por_solucao': totais_solucao,
            'documentos_count': len([d for d in credito.documentos if d.ativo]),
            'solucoes_count': len([s for s in credito.solucoes if s.ativo])
        }

    @staticmethod
    def atualizar_status_credito(credito_id: int) -> PalletCredito:
        """
        Recalcula e atualiza o status de um crédito.

        Útil para correções ou após migrações de dados.

        Args:
            credito_id: ID do crédito

        Returns:
            PalletCredito: Crédito atualizado
        """
        credito = PalletCredito.query.get(credito_id)
        if not credito:
            raise ValueError(f"Crédito #{credito_id} não encontrado")

        # Recalcular saldo baseado nas soluções
        total_solucionado = db.session.query(
            db.func.sum(PalletSolucao.quantidade)
        ).filter(
            PalletSolucao.credito_id == credito_id,
            PalletSolucao.ativo == True
        ).scalar() or 0

        credito.qtd_saldo = credito.qtd_original - total_solucionado
        credito.atualizar_status()

        db.session.commit()

        logger.info(
            f"✅ Status do crédito #{credito_id} atualizado: "
            f"{credito.status} (saldo: {credito.qtd_saldo})"
        )

        return credito

    @staticmethod
    def listar_creditos_pendentes(
        cnpj_responsavel: str = None,
        tipo_responsavel: str = None,
        vencidos: bool = None,
        limite: int = 100,
        status: str = None
    ) -> List[PalletCredito]:
        """
        Lista créditos pendentes de resolução.

        Args:
            cnpj_responsavel: Filtrar por CNPJ do responsável
            tipo_responsavel: Filtrar por tipo ('TRANSPORTADORA' ou 'CLIENTE')
            vencidos: Se True, apenas vencidos; Se False, apenas não vencidos
            limite: Quantidade máxima de registros
            status: Filtrar por status específico(s) separados por vírgula
                    (ex: 'PENDENTE,PARCIAL'). Default: ['PENDENTE', 'PARCIAL']

        Returns:
            List[PalletCredito]: Créditos encontrados
        """
        # Determinar lista de status a filtrar
        if status:
            status_list = [s.strip().upper() for s in status.split(',') if s.strip()]
            # Validar status
            valid_status = ['PENDENTE', 'PARCIAL', 'RESOLVIDO']
            status_list = [s for s in status_list if s in valid_status]
            if not status_list:
                status_list = ['PENDENTE', 'PARCIAL']
        else:
            status_list = ['PENDENTE', 'PARCIAL']

        query = PalletCredito.query.filter(
            PalletCredito.status.in_(status_list),
            PalletCredito.ativo == True
        )

        if cnpj_responsavel:
            query = query.filter(PalletCredito.cnpj_responsavel == cnpj_responsavel)

        if tipo_responsavel:
            query = query.filter(PalletCredito.tipo_responsavel == tipo_responsavel)

        if vencidos is not None:
            hoje = date.today()
            if vencidos:
                query = query.filter(PalletCredito.data_vencimento < hoje)
            else:
                query = query.filter(
                    db.or_(
                        PalletCredito.data_vencimento >= hoje,
                        PalletCredito.data_vencimento.is_(None)
                    )
                )

        return query.order_by(
            PalletCredito.data_vencimento.asc()
        ).limit(limite).all()

    @staticmethod
    def obter_resumo_por_responsavel(cnpj_responsavel: str) -> Dict:
        """
        Obtém resumo de créditos por responsável.

        Args:
            cnpj_responsavel: CNPJ do responsável

        Returns:
            Dict com resumo
        """
        creditos = PalletCredito.query.filter(
            PalletCredito.cnpj_responsavel == cnpj_responsavel,
            PalletCredito.ativo == True
        ).all()

        saldo_total = sum(c.qtd_saldo for c in creditos if c.status != 'RESOLVIDO')
        qtd_original_total = sum(c.qtd_original for c in creditos)

        vencidos = [c for c in creditos if c.data_vencimento and c.data_vencimento < date.today() and c.status != 'RESOLVIDO']

        return {
            'cnpj_responsavel': cnpj_responsavel,
            'nome_responsavel': creditos[0].nome_responsavel if creditos else None,
            'total_creditos': len(creditos),
            'creditos_pendentes': len([c for c in creditos if c.status in ('PENDENTE', 'PARCIAL')]),
            'creditos_resolvidos': len([c for c in creditos if c.status == 'RESOLVIDO']),
            'qtd_original_total': qtd_original_total,
            'saldo_total': saldo_total,
            'creditos_vencidos': len(vencidos),
            'saldo_vencido': sum(c.qtd_saldo for c in vencidos)
        }

    @staticmethod
    def listar_vencimentos_proximos(dias: int = 7) -> List[PalletCredito]:
        """
        Lista créditos que vencem nos próximos N dias.

        Args:
            dias: Quantidade de dias para considerar

        Returns:
            List[PalletCredito]: Créditos próximos do vencimento
        """
        hoje = date.today()
        limite = hoje + timedelta(days=dias)

        return PalletCredito.query.filter(
            PalletCredito.data_vencimento.isnot(None),
            PalletCredito.data_vencimento >= hoje,
            PalletCredito.data_vencimento <= limite,
            PalletCredito.status.in_(['PENDENTE', 'PARCIAL']),
            PalletCredito.ativo == True
        ).order_by(
            PalletCredito.data_vencimento.asc()
        ).all()
