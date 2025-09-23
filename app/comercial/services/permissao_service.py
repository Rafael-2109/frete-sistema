"""
Service para gerenciamento de permissões comerciais
====================================================

Este serviço centraliza toda a lógica de permissões do módulo comercial,
incluindo verificação, aplicação de filtros e gerenciamento.

Autor: Sistema de Fretes
Data: 2025-01-21
"""

from typing import List, Dict
from sqlalchemy import or_, distinct
from flask import request
from flask_login import current_user
from app import db
from app.comercial.models import PermissaoComercial, LogPermissaoComercial
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
import logging

logger = logging.getLogger(__name__)


class PermissaoService:
    """Service para gerenciar permissões comerciais"""

    @staticmethod
    def usuario_tem_permissoes(usuario_id: int) -> bool:
        """
        Verifica se um usuário tem alguma permissão configurada.

        Args:
            usuario_id: ID do usuário

        Returns:
            bool: True se tem permissões, False caso contrário
        """
        return db.session.query(PermissaoComercial).filter_by(
            usuario_id=usuario_id
        ).first() is not None

    @staticmethod
    def obter_permissoes_usuario(usuario_id: int) -> Dict[str, List[str]]:
        """
        Obtém todas as permissões de um usuário organizadas por tipo.

        Args:
            usuario_id: ID do usuário

        Returns:
            Dict com listas de equipes e vendedores permitidos
        """
        permissoes = db.session.query(PermissaoComercial).filter_by(
            usuario_id=usuario_id
        ).all()

        return {
            'equipes': [p.valor for p in permissoes if p.tipo == 'equipe'],
            'vendedores': [p.valor for p in permissoes if p.tipo == 'vendedor']
        }

    @staticmethod
    def aplicar_filtro_permissoes(query, campo_equipe='equipe_vendas', campo_vendedor='vendedor'):
        """
        Aplica filtro de permissões em uma query se o usuário for vendedor.

        Args:
            query: Query SQLAlchemy a ser filtrada
            campo_equipe: Nome do campo de equipe na tabela
            campo_vendedor: Nome do campo de vendedor na tabela

        Returns:
            Query filtrada ou original se não for vendedor
        """
        # Se não for vendedor, retorna query sem filtro
        if not current_user.is_authenticated or current_user.perfil != 'vendedor':
            return query

        # Obter permissões do usuário
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

        # Se não tem permissões, retorna query vazia
        if not permissoes['equipes'] and not permissoes['vendedores']:
            # Retorna filtro que não retorna nada
            return query.filter(False)

        # Construir condições
        conditions = []

        # Adicionar condição para equipes
        if permissoes['equipes']:
            if '.' in campo_equipe:
                # Se for campo com tabela especificada
                conditions.append(eval(f"{campo_equipe}.in_({permissoes['equipes']})"))
            else:
                # Campo simples
                conditions.append(query.column_descriptions[0]['entity'].__table__.c[campo_equipe].in_(permissoes['equipes']))

        # Adicionar condição para vendedores
        if permissoes['vendedores']:
            if '.' in campo_vendedor:
                # Se for campo com tabela especificada
                conditions.append(eval(f"{campo_vendedor}.in_({permissoes['vendedores']})"))
            else:
                # Campo simples
                conditions.append(query.column_descriptions[0]['entity'].__table__.c[campo_vendedor].in_(permissoes['vendedores']))

        # Aplicar filtro com OR se houver condições
        if conditions:
            return query.filter(or_(*conditions))
        else:
            return query.filter(False)

    @staticmethod
    def obter_equipes_disponiveis() -> List[str]:
        """
        Obtém lista de todas as equipes disponíveis no sistema.

        Returns:
            Lista de nomes de equipes únicos
        """
        equipes_carteira = db.session.query(
            distinct(CarteiraPrincipal.equipe_vendas)
        ).filter(
            CarteiraPrincipal.equipe_vendas.isnot(None),
            CarteiraPrincipal.equipe_vendas != ''
        ).all()

        equipes_faturamento = db.session.query(
            distinct(FaturamentoProduto.equipe_vendas)
        ).filter(
            FaturamentoProduto.equipe_vendas.isnot(None),
            FaturamentoProduto.equipe_vendas != ''
        ).all()

        # Unir e fazer distinct
        equipes_set = set()
        for e in equipes_carteira:
            if e[0]:
                equipes_set.add(e[0])

        for e in equipes_faturamento:
            if e[0]:
                equipes_set.add(e[0])

        return sorted(list(equipes_set))

    @staticmethod
    def obter_vendedores_disponiveis() -> List[str]:
        """
        Obtém lista de todos os vendedores disponíveis no sistema.

        Returns:
            Lista de nomes de vendedores únicos
        """
        vendedores_carteira = db.session.query(
            distinct(CarteiraPrincipal.vendedor)
        ).filter(
            CarteiraPrincipal.vendedor.isnot(None),
            CarteiraPrincipal.vendedor != ''
        ).all()

        vendedores_faturamento = db.session.query(
            distinct(FaturamentoProduto.vendedor)
        ).filter(
            FaturamentoProduto.vendedor.isnot(None),
            FaturamentoProduto.vendedor != ''
        ).all()

        # Unir e fazer distinct
        vendedores_set = set()
        for v in vendedores_carteira:
            if v[0]:
                vendedores_set.add(v[0])

        for v in vendedores_faturamento:
            if v[0]:
                vendedores_set.add(v[0])

        return sorted(list(vendedores_set))

    @staticmethod
    def adicionar_permissao(usuario_id: int, tipo: str, valor: str, admin_email: str) -> bool:
        """
        Adiciona uma permissão para um usuário.

        Args:
            usuario_id: ID do usuário
            tipo: 'equipe' ou 'vendedor'
            valor: Nome da equipe ou vendedor
            admin_email: Email do administrador que está fazendo a alteração

        Returns:
            bool: True se adicionou com sucesso, False se já existia
        """
        try:
            # Verificar se já existe
            existe = db.session.query(PermissaoComercial).filter_by(
                usuario_id=usuario_id,
                tipo=tipo,
                valor=valor
            ).first()

            if existe:
                return False

            # Criar nova permissão
            permissao = PermissaoComercial(
                usuario_id=usuario_id,
                tipo=tipo,
                valor=valor,
                criado_por=admin_email
            )
            db.session.add(permissao)

            # Registrar no log
            log = LogPermissaoComercial(
                usuario_id=usuario_id,
                admin_id=current_user.id if current_user.is_authenticated else None,
                acao='adicionar',
                tipo=tipo,
                valor=valor,
                ip_address=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent', '')[:500] if request else None
            )
            db.session.add(log)

            db.session.commit()
            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar permissão: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def remover_permissao(usuario_id: int, tipo: str, valor: str) -> bool:
        """
        Remove uma permissão de um usuário.

        Args:
            usuario_id: ID do usuário
            tipo: 'equipe' ou 'vendedor'
            valor: Nome da equipe ou vendedor

        Returns:
            bool: True se removeu com sucesso, False se não existia
        """
        try:
            # Buscar permissão
            permissao = db.session.query(PermissaoComercial).filter_by(
                usuario_id=usuario_id,
                tipo=tipo,
                valor=valor
            ).first()

            if not permissao:
                return False

            # Remover permissão
            db.session.delete(permissao)

            # Registrar no log
            log = LogPermissaoComercial(
                usuario_id=usuario_id,
                admin_id=current_user.id if current_user.is_authenticated else None,
                acao='remover',
                tipo=tipo,
                valor=valor,
                ip_address=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent', '')[:500] if request else None
            )
            db.session.add(log)

            db.session.commit()
            return True

        except Exception as e:
            logger.error(f"Erro ao remover permissão: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def limpar_permissoes_usuario(usuario_id: int) -> int:
        """
        Remove todas as permissões de um usuário.

        Args:
            usuario_id: ID do usuário

        Returns:
            int: Quantidade de permissões removidas
        """
        try:
            # Contar permissões
            count = db.session.query(PermissaoComercial).filter_by(
                usuario_id=usuario_id
            ).count()

            # Remover todas
            db.session.query(PermissaoComercial).filter_by(
                usuario_id=usuario_id
            ).delete()

            # Registrar no log
            if count > 0:
                log = LogPermissaoComercial(
                    usuario_id=usuario_id,
                    admin_id=current_user.id if current_user.is_authenticated else None,
                    acao='limpar_todas',
                    tipo=None,
                    valor=None,
                    ip_address=request.remote_addr if request else None,
                    user_agent=request.headers.get('User-Agent', '')[:500] if request else None,
                    observacao=f"Removidas {count} permissões"
                )
                db.session.add(log)

            db.session.commit()
            return count

        except Exception as e:
            logger.error(f"Erro ao limpar permissões: {e}")
            db.session.rollback()
            return 0

    @staticmethod
    def obter_logs_usuario(usuario_id: int, limite: int = 50) -> List[LogPermissaoComercial]:
        """
        Obtém logs de alterações de permissão de um usuário.

        Args:
            usuario_id: ID do usuário
            limite: Quantidade máxima de logs a retornar

        Returns:
            Lista de logs ordenados por data (mais recente primeiro)
        """
        return db.session.query(LogPermissaoComercial).filter_by(
            usuario_id=usuario_id
        ).order_by(LogPermissaoComercial.data_hora.desc()).limit(limite).all()

    @staticmethod
    def filtrar_equipes_por_permissao(equipes: List[str]) -> List[str]:
        """
        Filtra lista de equipes baseado nas permissões do usuário atual.

        Args:
            equipes: Lista de equipes para filtrar

        Returns:
            Lista filtrada de equipes se for vendedor, lista original caso contrário
        """
        # Se não for vendedor, retorna todas
        if not current_user.is_authenticated or current_user.perfil != 'vendedor':
            return equipes

        # Obter permissões
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

        # Se não tem permissões, retorna lista vazia
        if not permissoes['equipes'] and not permissoes['vendedores']:
            return []

        # Se tem permissões de equipes, filtrar
        if permissoes['equipes']:
            return [e for e in equipes if e in permissoes['equipes']]

        # Se só tem vendedores específicos, precisa verificar quais equipes eles pertencem
        # Isso é mais complexo e pode requerer query adicional
        # Por ora, retorna lista vazia se só tem vendedores específicos
        return []

    @staticmethod
    def vendedor_tem_acesso_equipe(equipe: str) -> bool:
        """
        Verifica se o vendedor atual tem acesso a uma equipe.

        Args:
            equipe: Nome da equipe

        Returns:
            bool: True se tem acesso, False caso contrário
        """
        # Se não for vendedor, tem acesso
        if not current_user.is_authenticated or current_user.perfil != 'vendedor':
            return True

        # Obter permissões
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

        # Verificar se tem permissão para a equipe
        return equipe in permissoes['equipes']

    @staticmethod
    def vendedor_tem_acesso_vendedor(vendedor: str) -> bool:
        """
        Verifica se o vendedor atual tem acesso a visualizar dados de outro vendedor.

        Args:
            vendedor: Nome do vendedor

        Returns:
            bool: True se tem acesso, False caso contrário
        """
        # Se não for vendedor, tem acesso
        if not current_user.is_authenticated or current_user.perfil != 'vendedor':
            return True

        # Obter permissões
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

        # Verificar se tem permissão direta para o vendedor
        if vendedor in permissoes['vendedores']:
            return True

        # Verificar se o vendedor pertence a alguma equipe permitida
        # Isso requer buscar a equipe do vendedor
        vendedor_equipe = db.session.query(CarteiraPrincipal.equipe_vendas).filter(
            CarteiraPrincipal.vendedor == vendedor
        ).first()

        if vendedor_equipe and vendedor_equipe[0] in permissoes['equipes']:
            return True

        return False