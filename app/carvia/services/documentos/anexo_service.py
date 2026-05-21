# -*- coding: utf-8 -*-
"""
Service de Anexos polimorficos CarVia (CarviaAnexo)
====================================================

Centraliza upload/listagem/exclusao/download de anexos comprovatorios para
CarviaFrete e CarviaSubcontrato. Espelha a logica que estava inline em
custo_entrega_routes.py::upload_anexo_custo_entrega, mas generica por entidade.

Validacao de entidade: o service confirma que a entidade existe antes de
inserir (garante integridade referencial mesmo sem FK fisica polimorfica).

Transacao: os metodos de escrita fazem `add` + `flush` mas NAO commitam — o
caller (rota) commita (padrao do modulo, igual CustoEntregaFaturaService).
"""

import logging
import os

from app import db
from app.carvia.models.anexos import CarviaAnexo
from app.carvia.utils.upload_policies import (
    ALLOWED_EXT_ANEXO,
    MAX_BYTES_ANEXO,
    UPLOAD_MAX_MB_ANEXO,
    is_extensao_permitida,
    mensagem_erro_extensao,
    mensagem_erro_tamanho,
)

logger = logging.getLogger(__name__)


def _resolver_modelo(entidade_tipo):
    """Retorna a classe do model para o entidade_tipo (lazy import), ou None."""
    if entidade_tipo == CarviaAnexo.ENTIDADE_FRETE:
        from app.carvia.models import CarviaFrete
        return CarviaFrete
    if entidade_tipo == CarviaAnexo.ENTIDADE_SUBCONTRATO:
        from app.carvia.models import CarviaSubcontrato
        return CarviaSubcontrato
    return None


class CarviaAnexoService:
    """Servico de anexos polimorficos (frete, subcontrato)."""

    @staticmethod
    def validar_entidade(entidade_tipo, entidade_id):
        """Valida tipo suportado + existencia da entidade.

        Returns:
            objeto da entidade.
        Raises:
            ValueError: tipo invalido ou entidade inexistente.
        """
        if entidade_tipo not in CarviaAnexo.ENTIDADES_VALIDAS:
            raise ValueError(
                f"Tipo de entidade invalido: '{entidade_tipo}'. "
                f"Validos: {', '.join(sorted(CarviaAnexo.ENTIDADES_VALIDAS))}."
            )
        modelo = _resolver_modelo(entidade_tipo)
        obj = db.session.get(modelo, entidade_id)
        if not obj:
            raise ValueError(
                f"{entidade_tipo.capitalize()} #{entidade_id} nao encontrado."
            )
        return obj

    @staticmethod
    def listar(entidade_tipo, entidade_id):
        """Lista anexos ATIVOS de uma entidade, mais recentes primeiro."""
        return CarviaAnexo.query.filter(
            CarviaAnexo.entidade_tipo == entidade_tipo,
            CarviaAnexo.entidade_id == entidade_id,
            CarviaAnexo.ativo.is_(True),
        ).order_by(CarviaAnexo.criado_em.desc()).all()

    @staticmethod
    def criar(entidade_tipo, entidade_id, file, usuario, descricao=None):
        """Faz upload de um anexo para a entidade.

        NAO commita — o caller deve commitar.

        Args:
            entidade_tipo: 'frete' | 'subcontrato'
            entidade_id: id da entidade
            file: werkzeug FileStorage (request.files['arquivo'])
            usuario: email/identificacao do usuario
            descricao: texto opcional

        Returns:
            CarviaAnexo criado (apos flush, com id).

        Raises:
            ValueError: falha de validacao (tipo, entidade, arquivo, tamanho).
        """
        # 1. Entidade valida e existente
        CarviaAnexoService.validar_entidade(entidade_tipo, entidade_id)

        # 2. Arquivo presente + extensao
        if not file or not file.filename:
            raise ValueError('Nenhum arquivo enviado.')
        if not is_extensao_permitida(file.filename, ALLOWED_EXT_ANEXO):
            raise ValueError(mensagem_erro_extensao(ALLOWED_EXT_ANEXO))

        # 3. Tamanho
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_BYTES_ANEXO:
            raise ValueError(mensagem_erro_tamanho(UPLOAD_MAX_MB_ANEXO))

        # 4. Salvar no S3/local
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        caminho = storage.save_file(file, folder='carvia/anexos')
        if not caminho:
            raise ValueError('Falha ao salvar arquivo no storage.')

        # 5. Metadados de email (.msg/.eml)
        email_metadata = {}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext in ('msg', 'eml'):
            try:
                from app.utils.email_handler import EmailHandler
                handler = EmailHandler()
                file.seek(0)
                if ext == 'msg':
                    email_metadata = handler.processar_email_msg(file) or {}
                else:
                    email_metadata = handler.processar_email_eml(file) or {}
            except Exception as e_email:  # noqa: BLE001 — metadado e best-effort
                logger.warning(
                    "Nao foi possivel extrair metadados do email %s: %s",
                    file.filename, e_email,
                )

        preview = email_metadata.get('conteudo_preview', '')
        anexo = CarviaAnexo(
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            nome_original=file.filename,
            nome_arquivo=os.path.basename(caminho),
            caminho_s3=caminho,
            tamanho_bytes=size,
            content_type=file.content_type,
            descricao=(descricao or '').strip() or None,
            criado_por=usuario,
            email_remetente=email_metadata.get('remetente') or None,
            email_assunto=email_metadata.get('assunto') or None,
            email_data_envio=email_metadata.get('data_envio'),
            email_conteudo_preview=preview[:500] if preview else None,
        )
        db.session.add(anexo)
        db.session.flush()
        logger.info(
            "CarviaAnexo #%s criado para %s#%s por %s",
            anexo.id, entidade_tipo, entidade_id, usuario,
        )
        return anexo

    @staticmethod
    def soft_delete(anexo_id):
        """Soft-delete (ativo=False). NAO commita. Retorna o anexo ou None."""
        anexo = db.session.get(CarviaAnexo, anexo_id)
        if not anexo:
            return None
        anexo.ativo = False
        db.session.flush()
        return anexo

    @staticmethod
    def download_url(anexo):
        """Gera URL de download (presigned S3, com fallback get_file_url)."""
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        return (
            storage.get_download_url(anexo.caminho_s3, anexo.nome_original)
            or storage.get_file_url(anexo.caminho_s3)
        )
