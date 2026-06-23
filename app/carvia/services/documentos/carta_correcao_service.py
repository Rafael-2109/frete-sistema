"""Service de Carta de Correção (CCe) CarVia.

Upload/listagem/exclusão/download + propagação pela cadeia cotacao <-> nf.
Espelha CarviaComprovanteService, porém ENXUTO (sem campos financeiros) e
restrito às entidades {cotacao, nf}. Métodos de escrita fazem flush, NÃO commitam.
"""
import logging
import os

from app import db
from app.carvia.utils.upload_policies import (
    ALLOWED_EXT_CCE, MAX_BYTES_ANEXO, UPLOAD_MAX_MB_ANEXO,
    is_extensao_permitida, mensagem_erro_extensao, mensagem_erro_tamanho,
)

logger = logging.getLogger(__name__)


def _resolver_modelo(entidade_tipo):
    if entidade_tipo == 'cotacao':
        from app.carvia.models import CarviaCotacao
        return CarviaCotacao
    if entidade_tipo == 'nf':
        from app.carvia.models import CarviaNf
        return CarviaNf
    return None


class CarviaCartaCorrecaoService:

    @staticmethod
    def validar_entidade(entidade_tipo, entidade_id):
        from app.carvia.models import CarviaCartaCorrecaoVinculo
        if entidade_tipo not in CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS:
            raise ValueError(
                f"Tipo de entidade invalido: '{entidade_tipo}'. "
                f"Validos: {', '.join(sorted(CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS))}."
            )
        modelo = _resolver_modelo(entidade_tipo)
        obj = db.session.get(modelo, entidade_id)
        if not obj:
            raise ValueError(f"{entidade_tipo} #{entidade_id} nao encontrado.")
        return obj

    @staticmethod
    def sincronizar_cadeia(entidade_tipo, entidade_id, criado_por='sistema'):
        """Vincula toda CCe ativa do fecho da cadeia a TODAS as entidades
        cotacao/nf do fecho. Idempotente. NÃO commita. Retorna nº de vínculos criados."""
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
        from app.carvia.services.documentos._cadeia_nf import resolver_cadeia_nf

        rel = resolver_cadeia_nf(entidade_tipo, entidade_id)
        pairs = [(t, i) for (t, i) in rel if t in ('cotacao', 'nf')]
        if not pairs:
            return 0

        cond = db.or_(*[
            db.and_(
                CarviaCartaCorrecaoVinculo.entidade_tipo == t,
                CarviaCartaCorrecaoVinculo.entidade_id == i,
            ) for (t, i) in pairs
        ])
        existentes = CarviaCartaCorrecaoVinculo.query.filter(cond).all()
        existentes_set = {(v.carta_id, v.entidade_tipo, v.entidade_id) for v in existentes}
        carta_ids = {v.carta_id for v in existentes}
        if not carta_ids:
            return 0

        ativos = {
            c.id for c in CarviaCartaCorrecao.query.filter(
                CarviaCartaCorrecao.id.in_(carta_ids),
                CarviaCartaCorrecao.ativo.is_(True),
            ).all()
        }
        criados = 0
        for carta_id in ativos:
            for (t, i) in pairs:
                if (carta_id, t, i) not in existentes_set:
                    db.session.add(CarviaCartaCorrecaoVinculo(
                        carta_id=carta_id, entidade_tipo=t, entidade_id=i,
                        origem=CarviaCartaCorrecaoVinculo.ORIGEM_PROPAGADO,
                        criado_por=criado_por,
                    ))
                    criados += 1
        if criados:
            db.session.flush()
        return criados

    @staticmethod
    def criar(entidade_tipo, entidade_id, file, usuario, descricao=None):
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo

        CarviaCartaCorrecaoService.validar_entidade(entidade_tipo, entidade_id)

        if not file or not file.filename:
            raise ValueError('Nenhum arquivo enviado.')
        if not is_extensao_permitida(file.filename, ALLOWED_EXT_CCE):
            raise ValueError(mensagem_erro_extensao(ALLOWED_EXT_CCE))

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_BYTES_ANEXO:
            raise ValueError(mensagem_erro_tamanho(UPLOAD_MAX_MB_ANEXO))

        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        caminho = storage.save_file(file, folder='carvia/cartas_correcao')
        if not caminho:
            raise ValueError('Falha ao salvar arquivo no storage.')

        carta = CarviaCartaCorrecao(
            nome_original=file.filename,
            nome_arquivo=os.path.basename(caminho),
            caminho_s3=caminho,
            tamanho_bytes=size,
            content_type=file.content_type,
            descricao=(descricao or '').strip() or None,
            criado_por=usuario,
        )
        db.session.add(carta)
        db.session.flush()

        db.session.add(CarviaCartaCorrecaoVinculo(
            carta_id=carta.id, entidade_tipo=entidade_tipo, entidade_id=entidade_id,
            origem=CarviaCartaCorrecaoVinculo.ORIGEM_MANUAL, criado_por=usuario,
        ))
        db.session.flush()

        CarviaCartaCorrecaoService.sincronizar_cadeia(
            entidade_tipo, entidade_id, criado_por=usuario)
        logger.info("CarviaCartaCorrecao #%s criada para %s#%s por %s",
                    carta.id, entidade_tipo, entidade_id, usuario)
        return carta

    @staticmethod
    def listar(entidade_tipo, entidade_id):
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
        return db.session.query(
            CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo,
        ).join(
            CarviaCartaCorrecaoVinculo,
            CarviaCartaCorrecaoVinculo.carta_id == CarviaCartaCorrecao.id,
        ).filter(
            CarviaCartaCorrecaoVinculo.entidade_tipo == entidade_tipo,
            CarviaCartaCorrecaoVinculo.entidade_id == entidade_id,
            CarviaCartaCorrecao.ativo.is_(True),
        ).order_by(CarviaCartaCorrecao.criado_em.desc()).all()

    @staticmethod
    def tem_cce_batch(entidade_tipo, entidade_ids):
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
        ids = [i for i in (entidade_ids or []) if i is not None]
        if not ids:
            return {}
        rows = db.session.query(CarviaCartaCorrecaoVinculo.entidade_id).join(
            CarviaCartaCorrecao,
            CarviaCartaCorrecao.id == CarviaCartaCorrecaoVinculo.carta_id,
        ).filter(
            CarviaCartaCorrecaoVinculo.entidade_tipo == entidade_tipo,
            CarviaCartaCorrecaoVinculo.entidade_id.in_(ids),
            CarviaCartaCorrecao.ativo.is_(True),
        ).distinct().all()
        com = {r[0] for r in rows}
        return {i: (i in com) for i in ids}

    @staticmethod
    def soft_delete(carta_id):
        from app.carvia.models import CarviaCartaCorrecao
        carta = db.session.get(CarviaCartaCorrecao, carta_id)
        if not carta:
            return None
        carta.ativo = False
        db.session.flush()
        return carta

    @staticmethod
    def download_url(carta):
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        return (storage.get_download_url(carta.caminho_s3, carta.nome_original)
                or storage.get_file_url(carta.caminho_s3))
