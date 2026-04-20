"""
CarviaNfTransferenciaService — Vinculo NF Triangular
=====================================================

Servico responsavel por criar e gerir vinculos 1:N entre NF de
Transferencia (intercompany, mesma raiz CNPJ) e NF de Venda ao cliente
final. Uma NF so vira "transferencia efetiva" ao ganhar pelo menos 1
vinculo; sem vinculo, e frete comum.

Regras:
- Candidatura: `cnpj_emitente[:8] == cnpj_destinatario[:8]` (raiz CNPJ)
- Match: `nf_venda.cnpj_emitente == nf_transf.cnpj_destinatario`
  (a filial que recebeu a transferencia e quem emite a venda)
- Peso: soma(`peso_bruto` NFs venda vinculadas) <= `peso_bruto` NF transf
- Retroatividade: vinculo com NF venda em frete CONFERIDO/FATURADO ou em
  fatura e PERMITIDO, mas registra alerta no audit trail
- Desvinculo: bloqueado se NF venda tem frete CONFERIDO/FATURADO ou
  esta em item de fatura (simetrico a criacao)
"""

import json
import logging
import re
from decimal import Decimal
from typing import Iterable, List, Optional

from app import db
from app.carvia.models.documentos import (
    CarviaNf,
    CarviaNfVinculoTransferencia,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# Status de CarviaFrete que disparam alerta retroativo (nao bloqueiam).
STATUS_FRETE_RETROATIVO = {'CONFERIDO', 'FATURADO'}
# Status de CarviaFrete que impedem desvinculo (simetrico).
STATUS_FRETE_BLOQUEIA_DESVINCULO = {'CONFERIDO', 'FATURADO'}


class CarviaNfTransferenciaService:
    """Service stateless — todos metodos sao staticmethods."""

    # ------------------------------------------------------------------ #
    #  Helpers internos
    # ------------------------------------------------------------------ #

    @staticmethod
    def _apenas_digitos(valor: Optional[str]) -> str:
        if not valor:
            return ''
        return re.sub(r'\D', '', valor)

    @staticmethod
    def _raiz_cnpj(cnpj: Optional[str], n: int = 8) -> str:
        d = CarviaNfTransferenciaService._apenas_digitos(cnpj)
        return d[:n] if len(d) >= n else ''

    # ------------------------------------------------------------------ #
    #  Classificacao (candidatura e efetividade)
    # ------------------------------------------------------------------ #

    @staticmethod
    def eh_candidata_transferencia(nf: CarviaNf) -> bool:
        """True se CNPJ emit e dest tem mesma raiz (8 digitos)."""
        if nf is None:
            return False
        raiz_e = CarviaNfTransferenciaService._raiz_cnpj(nf.cnpj_emitente)
        raiz_d = CarviaNfTransferenciaService._raiz_cnpj(nf.cnpj_destinatario)
        return bool(raiz_e) and raiz_e == raiz_d

    @staticmethod
    def eh_transferencia_efetiva(nf_id: int) -> bool:
        """True se existe algum vinculo onde a NF e a transferencia."""
        if not nf_id:
            return False
        return db.session.query(
            db.exists().where(
                CarviaNfVinculoTransferencia.nf_transferencia_id == nf_id
            )
        ).scalar()

    @staticmethod
    def get_ids_transferencias_efetivas() -> set:
        """Retorna set de nf_ids que sao transferencia efetiva (cacheavel)."""
        rows = db.session.query(
            CarviaNfVinculoTransferencia.nf_transferencia_id
        ).distinct().all()
        return {r[0] for r in rows}

    @staticmethod
    def get_nums_transferencia_efetiva() -> set:
        """Retorna set de numero_nf que sao transferencia efetiva."""
        rows = db.session.query(
            CarviaNf.numero_nf
        ).join(
            CarviaNfVinculoTransferencia,
            CarviaNfVinculoTransferencia.nf_transferencia_id == CarviaNf.id,
        ).distinct().all()
        return {r[0] for r in rows if r[0]}

    # ------------------------------------------------------------------ #
    #  Consultas de vinculo
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_transferencia_de(nf_venda_id: int) -> Optional[CarviaNf]:
        """Retorna a NF transferencia vinculada a uma NF venda (ou None)."""
        vinc = CarviaNfVinculoTransferencia.query.filter_by(
            nf_venda_id=nf_venda_id
        ).first()
        if not vinc:
            return None
        return db.session.get(CarviaNf, vinc.nf_transferencia_id)

    @staticmethod
    def get_vendas_de(nf_transf_id: int) -> List[CarviaNf]:
        """Lista NFs venda vinculadas a uma NF transferencia."""
        vinculos = CarviaNfVinculoTransferencia.query.filter_by(
            nf_transferencia_id=nf_transf_id
        ).all()
        if not vinculos:
            return []
        ids = [v.nf_venda_id for v in vinculos]
        return CarviaNf.query.filter(CarviaNf.id.in_(ids)).all()

    @staticmethod
    def get_vinculo_por_venda(nf_venda_id: int) -> Optional[CarviaNfVinculoTransferencia]:
        return CarviaNfVinculoTransferencia.query.filter_by(
            nf_venda_id=nf_venda_id
        ).first()

    # ------------------------------------------------------------------ #
    #  Listagem de candidatas para a UI
    # ------------------------------------------------------------------ #

    @staticmethod
    def listar_candidatas_venda(
        nf_transf_id: int,
        incluir_venda_alvo_id: Optional[int] = None,
    ) -> List[CarviaNf]:
        """NFs venda candidatas para 1-N (alem da venda alvo atual).

        Criterios (todos obrigatorios):
        - Nao esta CANCELADA
        - cnpj_emitente == nf_transf.cnpj_destinatario
        - cnpj_emitente[:8] != cnpj_destinatario[:8] (nao e tambem transferencia)
        - Nao tem vinculo existente (ou e a venda alvo, se passada)

        A venda alvo (incluir_venda_alvo_id) e incluida mesmo se ja tiver
        vinculo — representa a NF atual do contexto.
        """
        nf_transf = db.session.get(CarviaNf, nf_transf_id)
        if not nf_transf:
            return []

        cnpj_dest_transf = CarviaNfTransferenciaService._apenas_digitos(
            nf_transf.cnpj_destinatario
        )
        if not cnpj_dest_transf:
            return []

        # NFs venda sem vinculo (exceto venda alvo)
        sub_vinculadas = db.session.query(
            CarviaNfVinculoTransferencia.nf_venda_id
        ).subquery()

        query = CarviaNf.query.filter(
            CarviaNf.status != 'CANCELADA',
            CarviaNf.cnpj_emitente == nf_transf.cnpj_destinatario,
            # NAO e candidata a transferencia ela mesma
            db.or_(
                CarviaNf.cnpj_destinatario.is_(None),
                db.func.substr(
                    db.func.regexp_replace(CarviaNf.cnpj_emitente, r'\D', '', 'g'),
                    1, 8,
                ) != db.func.substr(
                    db.func.regexp_replace(CarviaNf.cnpj_destinatario, r'\D', '', 'g'),
                    1, 8,
                ),
            ),
        )

        if incluir_venda_alvo_id:
            query = query.filter(
                db.or_(
                    CarviaNf.id == incluir_venda_alvo_id,
                    ~CarviaNf.id.in_(sub_vinculadas),
                )
            )
        else:
            query = query.filter(~CarviaNf.id.in_(sub_vinculadas))

        return query.order_by(CarviaNf.data_emissao.desc(), CarviaNf.id.desc()).all()

    @staticmethod
    def listar_transferencias_candidatas_existentes(
        nf_venda_id: int,
    ) -> List[CarviaNf]:
        """NFs transferencia ja importadas candidatas para esta NF venda.

        Criterios:
        - eh_candidata_transferencia (raiz CNPJ emit==dest)
        - cnpj_destinatario == nf_venda.cnpj_emitente
        - Nao esta CANCELADA
        """
        nf_venda = db.session.get(CarviaNf, nf_venda_id)
        if not nf_venda or not nf_venda.cnpj_emitente:
            return []

        query = CarviaNf.query.filter(
            CarviaNf.status != 'CANCELADA',
            CarviaNf.id != nf_venda_id,
            CarviaNf.cnpj_destinatario == nf_venda.cnpj_emitente,
            # Raiz CNPJ emit == dest (candidata)
            db.func.substr(
                db.func.regexp_replace(CarviaNf.cnpj_emitente, r'\D', '', 'g'),
                1, 8,
            ) == db.func.substr(
                db.func.regexp_replace(CarviaNf.cnpj_destinatario, r'\D', '', 'g'),
                1, 8,
            ),
        )
        return query.order_by(CarviaNf.data_emissao.desc(), CarviaNf.id.desc()).all()

    # ------------------------------------------------------------------ #
    #  Parsing XML (reuso do NFeXMLParser)
    # ------------------------------------------------------------------ #

    @staticmethod
    def parsear_xml_transferencia(
        xml_bytes: bytes,
        arquivo_nome: Optional[str] = None,
    ) -> dict:
        """Parseia XML NF-e retornando dados + metadados de candidatura.

        Nao persiste — apenas retorna preview. A persistencia acontece
        em `upsert_nf_transferencia_a_partir_do_preview`.
        """
        from app.carvia.services.parsers.nfe_xml_parser import NFeXMLParser

        parser = NFeXMLParser(xml_bytes)
        if not parser.is_valid():
            return {'ok': False, 'erro': 'XML invalido ou nao reconhecido'}
        if not parser.is_nfe():
            return {'ok': False, 'erro': 'Documento nao e NF-e (modelo 55)'}

        info = parser.get_todas_informacoes()

        raiz_e = CarviaNfTransferenciaService._raiz_cnpj(info.get('cnpj_emitente'))
        raiz_d = CarviaNfTransferenciaService._raiz_cnpj(info.get('cnpj_destinatario'))
        candidata = bool(raiz_e) and raiz_e == raiz_d

        # Ja existe no banco (por chave)?
        existente = None
        chave = info.get('chave_acesso_nf')
        if chave:
            existente = CarviaNf.query.filter_by(chave_acesso_nf=chave).first()

        return {
            'ok': True,
            'info': info,
            'arquivo_nome': arquivo_nome,
            'candidata': candidata,
            'existente_id': existente.id if existente else None,
            'existente_status': existente.status if existente else None,
        }

    @staticmethod
    def upsert_nf_transferencia_a_partir_do_preview(
        info: dict,
        criado_por: str,
    ) -> CarviaNf:
        """Cria CarviaNf a partir do parse, ou retorna existente (por chave)."""
        chave = info.get('chave_acesso_nf')
        if chave:
            nf = CarviaNf.query.filter_by(chave_acesso_nf=chave).first()
            if nf:
                return nf

        nf = CarviaNf(
            numero_nf=info.get('numero_nf') or '',
            serie_nf=info.get('serie_nf'),
            chave_acesso_nf=chave,
            data_emissao=(
                info['data_emissao'].date()
                if info.get('data_emissao') and hasattr(info['data_emissao'], 'date')
                else info.get('data_emissao')
            ),
            cnpj_emitente=CarviaNfTransferenciaService._apenas_digitos(
                info.get('cnpj_emitente') or ''
            ),
            nome_emitente=info.get('nome_emitente'),
            uf_emitente=info.get('uf_emitente'),
            cidade_emitente=info.get('cidade_emitente'),
            cnpj_destinatario=CarviaNfTransferenciaService._apenas_digitos(
                info.get('cnpj_destinatario') or ''
            ),
            nome_destinatario=info.get('nome_destinatario'),
            uf_destinatario=info.get('uf_destinatario'),
            cidade_destinatario=info.get('cidade_destinatario'),
            valor_total=info.get('valor_total'),
            peso_bruto=info.get('peso_bruto'),
            peso_liquido=info.get('peso_liquido'),
            quantidade_volumes=info.get('quantidade_volumes'),
            tipo_fonte='XML_NFE',
            status='ATIVA',
            criado_por=criado_por or 'sistema',
        )
        db.session.add(nf)
        db.session.flush()  # precisa do id
        return nf

    # ------------------------------------------------------------------ #
    #  Validacao de peso
    # ------------------------------------------------------------------ #

    @staticmethod
    def comparar_pesos(
        nf_transf_id: int,
        nf_venda_ids: Iterable[int],
    ) -> dict:
        """Compara peso_bruto NF transf vs soma das NFs venda."""
        nf_transf = db.session.get(CarviaNf, nf_transf_id)
        if not nf_transf:
            return {'ok': False, 'erro': 'NF transferencia nao encontrada'}

        ids = list(nf_venda_ids or [])
        vendas = CarviaNf.query.filter(CarviaNf.id.in_(ids)).all() if ids else []

        peso_transf = Decimal(str(nf_transf.peso_bruto or 0))
        soma = Decimal('0')
        detalhes = []
        for v in vendas:
            p = Decimal(str(v.peso_bruto or 0))
            soma += p
            detalhes.append({
                'nf_venda_id': v.id,
                'numero_nf': v.numero_nf,
                'peso_bruto': float(p),
            })

        excede = soma > peso_transf
        return {
            'ok': True,
            'peso_transf': float(peso_transf),
            'peso_vendas_soma': float(soma),
            'delta': float(peso_transf - soma),
            'excede': excede,
            'detalhes_vendas': detalhes,
        }

    # ------------------------------------------------------------------ #
    #  Contexto retroativo (alerta nao bloqueante)
    # ------------------------------------------------------------------ #

    @staticmethod
    def detectar_contexto_retroativo(nf_venda_id: int) -> dict:
        """Retorna info de fretes/faturas que disparam alerta retroativo."""
        from app.carvia.models.frete import CarviaFrete

        nf = db.session.get(CarviaNf, nf_venda_id)
        if not nf:
            return {'tem_retroativo': False}

        # Fretes com status CONFERIDO/FATURADO que referenciam a NF via CSV
        fretes_hit = []
        if nf.numero_nf:
            fretes = CarviaFrete.query.filter(
                CarviaFrete.status.in_(STATUS_FRETE_RETROATIVO),
                CarviaFrete.numeros_nfs.isnot(None),
                db.or_(
                    CarviaFrete.numeros_nfs == nf.numero_nf,
                    CarviaFrete.numeros_nfs.like(f"{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf}"),
                ),
            ).all()
            fretes_hit = [{'frete_id': f.id, 'status': f.status} for f in fretes]

        # Faturas que referenciam a NF
        faturas_c = [
            {'id': f.id, 'numero_fatura': f.numero_fatura}
            for f in nf.get_faturas_cliente()
        ]
        faturas_t = [
            {'id': f.id, 'numero_fatura': f.numero_fatura}
            for f in nf.get_faturas_transportadora()
        ]

        tem = bool(fretes_hit or faturas_c or faturas_t)
        return {
            'tem_retroativo': tem,
            'fretes': fretes_hit,
            'faturas_cliente': faturas_c,
            'faturas_transp': faturas_t,
        }

    # ------------------------------------------------------------------ #
    #  Validacao de vinculo (agrega todas as checagens)
    # ------------------------------------------------------------------ #

    @staticmethod
    def validar_vinculo(
        nf_transf_id: int,
        nf_venda_ids: Iterable[int],
    ) -> tuple:
        """Valida sem persistir. Retorna (ok, motivo_se_falha, dados)."""
        nf_transf = db.session.get(CarviaNf, nf_transf_id)
        if not nf_transf:
            return False, 'NF transferencia nao encontrada', {}
        if nf_transf.status == 'CANCELADA':
            return False, 'NF transferencia esta CANCELADA', {}
        if not CarviaNfTransferenciaService.eh_candidata_transferencia(nf_transf):
            return (
                False,
                'NF nao e candidata a transferencia (CNPJ emit e dest devem '
                'ter mesma raiz de 8 digitos)',
                {},
            )

        ids = list(nf_venda_ids or [])
        if not ids:
            return False, 'Nenhuma NF venda selecionada', {}

        vendas = CarviaNf.query.filter(CarviaNf.id.in_(ids)).all()
        if len(vendas) != len(set(ids)):
            return False, 'Uma ou mais NFs venda nao encontradas', {}

        cnpj_dest_transf = CarviaNfTransferenciaService._apenas_digitos(
            nf_transf.cnpj_destinatario
        )
        for v in vendas:
            if v.id == nf_transf.id:
                return False, 'NF nao pode ser vinculada a si mesma', {}
            if v.status == 'CANCELADA':
                return False, f'NF venda {v.numero_nf} esta CANCELADA', {}
            cnpj_emit_venda = CarviaNfTransferenciaService._apenas_digitos(
                v.cnpj_emitente
            )
            if cnpj_emit_venda != cnpj_dest_transf:
                return (
                    False,
                    f'NF venda {v.numero_nf} tem emitente {cnpj_emit_venda} '
                    f'!= destinatario da transf {cnpj_dest_transf}',
                    {},
                )

            ja_vinc = CarviaNfVinculoTransferencia.query.filter_by(
                nf_venda_id=v.id
            ).first()
            if ja_vinc and ja_vinc.nf_transferencia_id != nf_transf_id:
                return (
                    False,
                    f'NF venda {v.numero_nf} ja esta vinculada a outra '
                    f'transferencia (#{ja_vinc.nf_transferencia_id})',
                    {},
                )

        peso = CarviaNfTransferenciaService.comparar_pesos(nf_transf_id, ids)
        if peso.get('excede'):
            return (
                False,
                f"Soma dos pesos das vendas ({peso['peso_vendas_soma']:.3f}) "
                f"excede peso da transferencia ({peso['peso_transf']:.3f})",
                {'peso': peso},
            )

        return True, '', {'peso': peso, 'vendas': vendas, 'transf': nf_transf}

    # ------------------------------------------------------------------ #
    #  Criacao / Remocao (atomic)
    # ------------------------------------------------------------------ #

    @staticmethod
    def criar_vinculos(
        nf_transf_id: int,
        nf_venda_ids: Iterable[int],
        criado_por: str,
        confirma_retroativo: bool = False,
    ) -> tuple:
        """Cria N vinculos atomicamente. Rollback se qualquer validacao falha.

        Retorna (ok, mensagem, vinculos_criados_list).
        """
        ok, motivo, dados = CarviaNfTransferenciaService.validar_vinculo(
            nf_transf_id, nf_venda_ids
        )
        if not ok:
            return False, motivo, []

        vendas = dados['vendas']
        transf = dados['transf']

        # Detecta retroatividade para cada venda
        retroativos = {}
        qualquer_retroativo = False
        for v in vendas:
            ctx = CarviaNfTransferenciaService.detectar_contexto_retroativo(v.id)
            retroativos[v.id] = ctx
            if ctx.get('tem_retroativo'):
                qualquer_retroativo = True

        if qualquer_retroativo and not confirma_retroativo:
            return (
                False,
                'Vinculo retroativo detectado — confirmacao explicita necessaria',
                [{'nf_venda_id': vid, 'contexto': ctx}
                 for vid, ctx in retroativos.items() if ctx.get('tem_retroativo')],
            )

        criados = []
        try:
            for v in vendas:
                ctx = retroativos[v.id]
                vinculo = CarviaNfVinculoTransferencia(
                    nf_transferencia_id=transf.id,
                    nf_venda_id=v.id,
                    peso_bruto_venda_snapshot=v.peso_bruto,
                    peso_bruto_transf_snapshot=transf.peso_bruto,
                    vinculado_retroativamente=bool(ctx.get('tem_retroativo')),
                    contexto_retroativo=(
                        json.dumps(ctx, default=str)
                        if ctx.get('tem_retroativo') else None
                    ),
                    criado_por=criado_por or 'sistema',
                    criado_em=agora_utc_naive(),
                )
                db.session.add(vinculo)
                criados.append(vinculo)
            db.session.flush()
            db.session.commit()
            logger.info(
                f'Vinculos de transferencia criados: transf={transf.id} '
                f'vendas={[v.id for v in vendas]} por={criado_por}'
            )
            return True, 'Vinculos criados com sucesso', criados
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao criar vinculos de transferencia: {e}')
            return False, f'Erro ao persistir vinculos: {e}', []

    @staticmethod
    def remover_vinculo(nf_venda_id: int, removido_por: str) -> tuple:
        """Remove vinculo de uma NF venda especifica.

        Bloqueia se NF venda tem frete CONFERIDO/FATURADO ou item de fatura.
        Retorna (ok, mensagem).
        """
        from app.carvia.models.frete import CarviaFrete

        vinc = CarviaNfVinculoTransferencia.query.filter_by(
            nf_venda_id=nf_venda_id
        ).first()
        if not vinc:
            return False, 'Vinculo nao encontrado'

        nf = db.session.get(CarviaNf, nf_venda_id)
        if not nf:
            return False, 'NF venda nao encontrada'

        # Bloqueios simetricos
        if nf.numero_nf:
            fretes_bloq = CarviaFrete.query.filter(
                CarviaFrete.status.in_(STATUS_FRETE_BLOQUEIA_DESVINCULO),
                CarviaFrete.numeros_nfs.isnot(None),
                db.or_(
                    CarviaFrete.numeros_nfs == nf.numero_nf,
                    CarviaFrete.numeros_nfs.like(f"{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf}"),
                ),
            ).all()
            if fretes_bloq:
                ids = ', '.join(f'#{f.id} ({f.status})' for f in fretes_bloq[:3])
                return (
                    False,
                    f'NF venda esta em frete(s) {ids} — desvinculo bloqueado',
                )

        if nf.get_faturas_cliente():
            return (
                False,
                'NF venda esta em item de Fatura Cliente — desvinculo bloqueado',
            )
        if nf.get_faturas_transportadora():
            return (
                False,
                'NF venda esta em item de Fatura Transportadora — desvinculo bloqueado',
            )

        try:
            db.session.delete(vinc)
            db.session.commit()
            logger.info(
                f'Vinculo de transferencia removido: venda={nf_venda_id} '
                f'por={removido_por}'
            )
            return True, 'Vinculo removido com sucesso'
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao remover vinculo: {e}')
            return False, f'Erro ao persistir: {e}'

    # ------------------------------------------------------------------ #
    #  Busca expandida (para fretes/CTes)
    # ------------------------------------------------------------------ #

    @staticmethod
    def expandir_nfs_relacionadas(
        numeros_nfs: Iterable[str],
    ) -> set:
        """Dado conjunto de numeros de NF, retorna numeros + parceiros
        vinculados (transf <-> vendas).

        Exemplo: NF venda `001` vinculada a NF transf `TX1`. expandir(['001'])
        retorna {'001', 'TX1'}. expandir(['TX1']) retorna {'TX1', '001',
        ..outras vendas do mesmo vinculo}.
        """
        nums_input = {n.strip() for n in (numeros_nfs or []) if n and n.strip()}
        if not nums_input:
            return set()

        # 1) Resolve nums -> ids
        rows_ids = db.session.query(CarviaNf.id, CarviaNf.numero_nf).filter(
            CarviaNf.numero_nf.in_(nums_input)
        ).all()
        if not rows_ids:
            return nums_input  # nenhum match no banco — retorna so o original
        nf_ids_input = {r[0] for r in rows_ids}

        # 2) Procura vinculos onde qualquer lado bate com nf_ids_input
        vincs = CarviaNfVinculoTransferencia.query.filter(
            db.or_(
                CarviaNfVinculoTransferencia.nf_transferencia_id.in_(nf_ids_input),
                CarviaNfVinculoTransferencia.nf_venda_id.in_(nf_ids_input),
            )
        ).all()
        if not vincs:
            return nums_input

        # 3) Coleta TODOS os ids envolvidos nesses vinculos (grupo completo).
        #    Para cada vinculo tocado, incluir transf + todas as vendas da transf.
        transf_ids = {v.nf_transferencia_id for v in vincs}
        relacionados_ids = set(transf_ids)
        # Adicionar TODAS as vendas das transf tocadas
        vendas_rows = db.session.query(
            CarviaNfVinculoTransferencia.nf_venda_id
        ).filter(
            CarviaNfVinculoTransferencia.nf_transferencia_id.in_(transf_ids)
        ).all()
        for (vid,) in vendas_rows:
            relacionados_ids.add(vid)
        relacionados_ids |= nf_ids_input

        # 4) Ids -> numeros_nf
        nums_rows = db.session.query(CarviaNf.numero_nf).filter(
            CarviaNf.id.in_(relacionados_ids)
        ).all()
        nums_expandidos = {r[0] for r in nums_rows if r[0]}
        return nums_expandidos | nums_input
