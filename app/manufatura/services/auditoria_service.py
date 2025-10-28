"""
Serviço de Auditoria para Lista de Materiais
Registra todas as alterações (CRIAR, EDITAR, INATIVAR, REATIVAR) no histórico
"""
from app import db
from app.manufatura.models import ListaMateriais, ListaMateriaisHistorico
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ServicoAuditoria:
    """
    Serviço para gerenciar auditoria de alterações em Lista de Materiais
    """

    @staticmethod
    def registrar_criacao(componente: ListaMateriais, usuario: str, motivo: str = None):
        """
        Registra criação de um novo componente no histórico

        Args:
            componente: Objeto ListaMateriais recém-criado
            usuario: Nome do usuário que criou
            motivo: Motivo da criação (opcional)

        Returns:
            ListaMateriaisHistorico: Registro de histórico criado
        """
        try:
            historico = ListaMateriaisHistorico(
                lista_materiais_id=componente.id,
                operacao='CRIAR',
                cod_produto_produzido=componente.cod_produto_produzido,
                nome_produto_produzido=componente.nome_produto_produzido,
                cod_produto_componente=componente.cod_produto_componente,
                nome_produto_componente=componente.nome_produto_componente,
                versao=componente.versao,
                # ANTES: null (não existia)
                qtd_utilizada_antes=None,
                status_antes=None,
                # DEPOIS: valores atuais
                qtd_utilizada_depois=componente.qtd_utilizada,
                status_depois=componente.status,
                # Metadados
                alterado_em=datetime.utcnow(),
                alterado_por=usuario,
                motivo=motivo
            )

            db.session.add(historico)
            db.session.commit()

            logger.info(
                f"✅ Auditoria CRIAR: {componente.cod_produto_componente} "
                f"na estrutura de {componente.cod_produto_produzido} por {usuario}"
            )

            return historico

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao registrar criação no histórico: {e}")
            raise

    @staticmethod
    def registrar_edicao(
        componente: ListaMateriais,
        usuario: str,
        qtd_anterior: float,
        motivo: str = None
    ):
        """
        Registra edição de um componente existente

        Args:
            componente: Objeto ListaMateriais após edição
            usuario: Nome do usuário que editou
            qtd_anterior: Quantidade utilizada ANTES da edição
            motivo: Motivo da edição (opcional)

        Returns:
            ListaMateriaisHistorico: Registro de histórico criado
        """
        try:
            historico = ListaMateriaisHistorico(
                lista_materiais_id=componente.id,
                operacao='EDITAR',
                cod_produto_produzido=componente.cod_produto_produzido,
                nome_produto_produzido=componente.nome_produto_produzido,
                cod_produto_componente=componente.cod_produto_componente,
                nome_produto_componente=componente.nome_produto_componente,
                versao=componente.versao,
                # ANTES
                qtd_utilizada_antes=qtd_anterior,
                status_antes=componente.status,  # Status geralmente não muda na edição
                # DEPOIS
                qtd_utilizada_depois=componente.qtd_utilizada,
                status_depois=componente.status,
                # Metadados
                alterado_em=datetime.utcnow(),
                alterado_por=usuario,
                motivo=motivo
            )

            db.session.add(historico)
            db.session.commit()

            logger.info(
                f"✅ Auditoria EDITAR: {componente.cod_produto_componente} "
                f"({qtd_anterior} → {componente.qtd_utilizada}) por {usuario}"
            )

            return historico

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao registrar edição no histórico: {e}")
            raise

    @staticmethod
    def registrar_inativacao(
        componente: ListaMateriais,
        usuario: str,
        motivo: str = None
    ):
        """
        Registra inativação (remoção) de um componente

        Args:
            componente: Objeto ListaMateriais após inativação
            usuario: Nome do usuário que inativou
            motivo: Motivo da inativação (opcional, mas recomendado)

        Returns:
            ListaMateriaisHistorico: Registro de histórico criado
        """
        try:
            historico = ListaMateriaisHistorico(
                lista_materiais_id=componente.id,
                operacao='INATIVAR',
                cod_produto_produzido=componente.cod_produto_produzido,
                nome_produto_produzido=componente.nome_produto_produzido,
                cod_produto_componente=componente.cod_produto_componente,
                nome_produto_componente=componente.nome_produto_componente,
                versao=componente.versao,
                # ANTES
                qtd_utilizada_antes=componente.qtd_utilizada,
                status_antes='ativo',
                # DEPOIS
                qtd_utilizada_depois=componente.qtd_utilizada,
                status_depois='inativo',
                # Metadados
                alterado_em=datetime.utcnow(),
                alterado_por=usuario,
                motivo=motivo or 'Componente removido da estrutura'
            )

            db.session.add(historico)

            # Atualizar campos de auditoria no componente
            componente.inativado_em = datetime.utcnow()
            componente.inativado_por = usuario
            componente.motivo_inativacao = motivo

            db.session.commit()

            logger.info(
                f"✅ Auditoria INATIVAR: {componente.cod_produto_componente} "
                f"removido de {componente.cod_produto_produzido} por {usuario}"
            )

            return historico

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao registrar inativação no histórico: {e}")
            raise

    @staticmethod
    def registrar_reativacao(
        componente: ListaMateriais,
        usuario: str,
        motivo: str = None
    ):
        """
        Registra reativação de um componente previamente inativo

        Args:
            componente: Objeto ListaMateriais após reativação
            usuario: Nome do usuário que reativou
            motivo: Motivo da reativação (opcional)

        Returns:
            ListaMateriaisHistorico: Registro de histórico criado
        """
        try:
            historico = ListaMateriaisHistorico(
                lista_materiais_id=componente.id,
                operacao='REATIVAR',
                cod_produto_produzido=componente.cod_produto_produzido,
                nome_produto_produzido=componente.nome_produto_produzido,
                cod_produto_componente=componente.cod_produto_componente,
                nome_produto_componente=componente.nome_produto_componente,
                versao=componente.versao,
                # ANTES
                qtd_utilizada_antes=componente.qtd_utilizada,
                status_antes='inativo',
                # DEPOIS
                qtd_utilizada_depois=componente.qtd_utilizada,
                status_depois='ativo',
                # Metadados
                alterado_em=datetime.utcnow(),
                alterado_por=usuario,
                motivo=motivo or 'Componente reativado na estrutura'
            )

            db.session.add(historico)
            db.session.commit()

            logger.info(
                f"✅ Auditoria REATIVAR: {componente.cod_produto_componente} "
                f"reativado em {componente.cod_produto_produzido} por {usuario}"
            )

            return historico

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao registrar reativação no histórico: {e}")
            raise

    @staticmethod
    def buscar_historico_componente(lista_materiais_id: int, limit: int = 50):
        """
        Busca histórico de um componente específico

        Args:
            lista_materiais_id: ID do registro em lista_materiais
            limit: Número máximo de registros a retornar

        Returns:
            List[ListaMateriaisHistorico]: Lista de registros de histórico
        """
        try:
            historico = ListaMateriaisHistorico.query.filter_by(
                lista_materiais_id=lista_materiais_id
            ).order_by(
                ListaMateriaisHistorico.alterado_em.desc()
            ).limit(limit).all()

            return historico

        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico do componente {lista_materiais_id}: {e}")
            return []

    @staticmethod
    def buscar_historico_produto(cod_produto: str, limit: int = 100):
        """
        Busca histórico de todas as alterações em um produto

        Args:
            cod_produto: Código do produto produzido
            limit: Número máximo de registros a retornar

        Returns:
            List[ListaMateriaisHistorico]: Lista de registros de histórico
        """
        try:
            historico = ListaMateriaisHistorico.query.filter_by(
                cod_produto_produzido=cod_produto
            ).order_by(
                ListaMateriaisHistorico.alterado_em.desc()
            ).limit(limit).all()

            return historico

        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico do produto {cod_produto}: {e}")
            return []

    @staticmethod
    def buscar_historico_usuario(usuario: str, limit: int = 100):
        """
        Busca histórico de todas as alterações feitas por um usuário

        Args:
            usuario: Nome do usuário
            limit: Número máximo de registros a retornar

        Returns:
            List[ListaMateriaisHistorico]: Lista de registros de histórico
        """
        try:
            historico = ListaMateriaisHistorico.query.filter_by(
                alterado_por=usuario
            ).order_by(
                ListaMateriaisHistorico.alterado_em.desc()
            ).limit(limit).all()

            return historico

        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico do usuário {usuario}: {e}")
            return []

    @staticmethod
    def buscar_historico_periodo(data_inicio, data_fim, limit: int = 500):
        """
        Busca histórico em um período específico

        Args:
            data_inicio: Data inicial (datetime ou date)
            data_fim: Data final (datetime ou date)
            limit: Número máximo de registros a retornar

        Returns:
            List[ListaMateriaisHistorico]: Lista de registros de histórico
        """
        try:
            historico = ListaMateriaisHistorico.query.filter(
                ListaMateriaisHistorico.alterado_em >= data_inicio,
                ListaMateriaisHistorico.alterado_em <= data_fim
            ).order_by(
                ListaMateriaisHistorico.alterado_em.desc()
            ).limit(limit).all()

            return historico

        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico do período: {e}")
            return []

    @staticmethod
    def estatisticas_historico():
        """
        Retorna estatísticas gerais do histórico

        Returns:
            dict: Estatísticas de uso
        """
        try:
            total = ListaMateriaisHistorico.query.count()

            # Contar por operação
            from sqlalchemy import func
            operacoes = db.session.query(
                ListaMateriaisHistorico.operacao,
                func.count(ListaMateriaisHistorico.id)
            ).group_by(ListaMateriaisHistorico.operacao).all()

            # Usuários mais ativos
            usuarios = db.session.query(
                ListaMateriaisHistorico.alterado_por,
                func.count(ListaMateriaisHistorico.id)
            ).group_by(
                ListaMateriaisHistorico.alterado_por
            ).order_by(
                func.count(ListaMateriaisHistorico.id).desc()
            ).limit(10).all()

            return {
                'total_registros': total,
                'por_operacao': dict(operacoes),
                'usuarios_mais_ativos': [
                    {'usuario': u[0], 'alteracoes': u[1]}
                    for u in usuarios
                ]
            }

        except Exception as e:
            logger.error(f"❌ Erro ao buscar estatísticas: {e}")
            return {
                'total_registros': 0,
                'por_operacao': {},
                'usuarios_mais_ativos': []
            }
