"""
LinkingService — Vinculacao cross-documento CarVia
====================================================

Resolve FKs entre itens de fatura e entidades (operacoes, NFs, subcontratos).
Permite navegacao bidirecional entre os 5 tipos de documento CarVia:
NF, CTe CarVia (Operacao), CTe Subcontrato, Fatura Cliente, Fatura Transportadora.

Metodos:
- vincular_itens_fatura_cliente: resolve operacao_id e nf_id em itens existentes
- vincular_operacoes_da_fatura: backward binding operacao -> fatura via itens
- criar_itens_fatura_transportadora: gera itens a partir de subcontratos vinculados
- criar_itens_fatura_cliente_from_operacoes: gera itens a partir de operacoes (UI manual)
- resolver_operacao_por_cte: helper de matching cte_numero -> operacao_id
- resolver_nf_por_numero: helper de matching nf_numero -> nf_id
- backfill_todas_faturas: one-time para dados existentes
"""

import logging
import re

from app import db
from sqlalchemy import func, or_

logger = logging.getLogger(__name__)


class LinkingService:
    """Servico de vinculacao cross-documento CarVia."""

    # ------------------------------------------------------------------
    # Resolvers: cte_numero -> operacao_id, nf_numero -> nf_id
    # ------------------------------------------------------------------

    @staticmethod
    def resolver_operacao_por_cte(cte_numero):
        """Resolve cte_numero (string) -> CarviaOperacao.

        Normaliza zeros a esquerda: "00000001" == "1".
        Returns CarviaOperacao ou None.
        """
        if not cte_numero:
            return None

        from app.carvia.models import CarviaOperacao

        cte_norm = cte_numero.lstrip('0') or '0'
        operacao = CarviaOperacao.query.filter(
            func.ltrim(CarviaOperacao.cte_numero, '0') == cte_norm
        ).first()

        return operacao

    @staticmethod
    def resolver_nf_por_numero(nf_numero, contraparte_cnpj=None):
        """Resolve nf_numero (string) -> CarviaNf.

        Match por numero normalizado (sem zeros a esquerda).
        Se contraparte_cnpj fornecido, filtra por emitente OU destinatario.
        Returns CarviaNf ou None.
        """
        if not nf_numero:
            return None

        from app.carvia.models import CarviaNf

        nf_norm = nf_numero.lstrip('0') or '0'
        query = CarviaNf.query.filter(
            func.ltrim(CarviaNf.numero_nf, '0') == nf_norm,
            CarviaNf.status != 'CANCELADA',
        )

        if contraparte_cnpj:
            cnpj_digits = re.sub(r'\D', '', contraparte_cnpj)
            if len(cnpj_digits) >= 14:
                query = query.filter(
                    or_(
                        func.regexp_replace(
                            CarviaNf.cnpj_emitente, '[^0-9]', '', 'g'
                        ) == cnpj_digits,
                        func.regexp_replace(
                            CarviaNf.cnpj_destinatario, '[^0-9]', '', 'g'
                        ) == cnpj_digits,
                    )
                )

        return query.first()

    # ------------------------------------------------------------------
    # Criar NF referencia (stub) quando NF nao existe no banco
    # ------------------------------------------------------------------

    def _criar_nf_referencia(self, nf_numero, contraparte_cnpj,
                              contraparte_nome=None, valor_mercadoria=None,
                              peso_kg=None, criado_por='sistema'):
        """Cria CarviaNf minima (tipo_fonte=FATURA_REFERENCIA) quando NF nao existe.

        Usado como ultimo recurso quando:
        1. resolver_nf_por_numero() nao encontrou (NF nunca importada)
        2. Fallback via junction tambem falhou

        Idempotente: retorna NF existente se ja criada (por numero + cnpj normalizado).

        Args:
            nf_numero: Numero da NF (obrigatorio)
            contraparte_cnpj: CNPJ do emitente da NF (obrigatorio)
            contraparte_nome: Nome do emitente (opcional)
            valor_mercadoria: Valor da mercadoria (melhor dado disponivel)
            peso_kg: Peso em kg
            criado_por: Quem criou ('backfill' ou 'importacao')

        Returns:
            CarviaNf existente ou recem-criada
        """
        if not nf_numero or not contraparte_cnpj:
            logger.warning(
                f"_criar_nf_referencia: dados insuficientes "
                f"nf_numero={nf_numero} cnpj={contraparte_cnpj}"
            )
            return None

        from app.carvia.models import CarviaNf

        # Normalizar para busca de duplicata
        nf_norm = nf_numero.lstrip('0') or '0'
        cnpj_digits = re.sub(r'\D', '', contraparte_cnpj)

        # Verificar se ja existe (idempotencia)
        existente = CarviaNf.query.filter(
            func.ltrim(CarviaNf.numero_nf, '0') == nf_norm,
            func.regexp_replace(
                CarviaNf.cnpj_emitente, '[^0-9]', '', 'g'
            ) == cnpj_digits,
        ).first()

        if existente:
            logger.info(
                f"NF referencia ja existe: nf_id={existente.id} "
                f"numero={nf_numero} cnpj={contraparte_cnpj}"
            )
            return existente

        # Criar NF stub minima
        from app.utils.timezone import agora_utc_naive

        nf = CarviaNf(
            numero_nf=nf_numero,
            cnpj_emitente=contraparte_cnpj,
            nome_emitente=contraparte_nome,
            valor_total=valor_mercadoria,
            peso_bruto=peso_kg,
            tipo_fonte='FATURA_REFERENCIA',
            criado_em=agora_utc_naive(),
            criado_por=criado_por,
        )
        db.session.add(nf)
        db.session.flush()

        logger.info(
            f"NF referencia CRIADA: nf_id={nf.id} numero={nf_numero} "
            f"cnpj={contraparte_cnpj} tipo_fonte=FATURA_REFERENCIA"
        )
        return nf

    # ------------------------------------------------------------------
    # Fallback: buscar NF via junction (operacao -> nfs vinculadas)
    # ------------------------------------------------------------------

    def _resolver_nf_via_junction(self, nf_numero, operacao_id):
        """Busca NF via junction carvia_operacao_nfs quando match direto falha.

        Se o item tem operacao_id, busca NFs vinculadas a essa operacao
        e verifica se alguma tem numero_nf correspondente.

        Returns:
            CarviaNf ou None
        """
        if not nf_numero or not operacao_id:
            return None

        from app.carvia.models import CarviaNf, CarviaOperacaoNf

        nf_norm = nf_numero.lstrip('0') or '0'

        # Buscar NFs vinculadas a esta operacao cujo numero bate
        nf = CarviaNf.query.join(
            CarviaOperacaoNf,
            CarviaOperacaoNf.nf_id == CarviaNf.id
        ).filter(
            CarviaOperacaoNf.operacao_id == operacao_id,
            func.ltrim(CarviaNf.numero_nf, '0') == nf_norm,
        ).first()

        if nf:
            logger.info(
                f"NF resolvida via junction: nf_id={nf.id} "
                f"numero={nf_numero} operacao_id={operacao_id}"
            )

        return nf

    # ------------------------------------------------------------------
    # Criar junction operacao <-> NF (se nao existe)
    # ------------------------------------------------------------------

    def _criar_junction_se_necessario(self, operacao_id, nf_id):
        """Cria carvia_operacao_nfs se junction nao existe.

        Idempotente: verifica existencia antes de criar.

        Returns:
            True se criou, False se ja existia
        """
        if not operacao_id or not nf_id:
            return False

        from app.carvia.models import CarviaOperacaoNf

        existente = CarviaOperacaoNf.query.filter_by(
            operacao_id=operacao_id,
            nf_id=nf_id,
        ).first()

        if existente:
            return False

        junction = CarviaOperacaoNf(
            operacao_id=operacao_id,
            nf_id=nf_id,
        )
        db.session.add(junction)
        db.session.flush()

        logger.info(
            f"Junction CRIADA: operacao_id={operacao_id} nf_id={nf_id}"
        )
        return True

    # ------------------------------------------------------------------
    # vincular_nf_a_operacoes_orfas: re-linking retroativo CTe -> NF
    # ------------------------------------------------------------------

    def vincular_nf_a_operacoes_orfas(self, nf):
        """Busca operacoes que referenciam esta NF (via JSON) e cria junctions.

        Chamado apos importar NF quando CTe ja foi importado antes.
        Usa nfs_referenciadas_json para reverse-lookup.

        Estrategia de match (dentro do JSON):
        1. Match por chave (44 digitos) — mais confiavel
        2. Fallback: match por numero_nf + cnpj_emitente normalizados

        Args:
            nf: CarviaNf recem-criada (ja tem id)

        Returns:
            int — numero de junctions criadas
        """
        from app.carvia.models import CarviaOperacao

        if not nf or not nf.id:
            return 0

        junctions_criadas = 0

        # Preparar dados da NF para comparacao
        nf_chave = nf.chave_acesso_nf
        nf_numero = nf.numero_nf
        nf_cnpj = re.sub(r'\D', '', nf.cnpj_emitente or '')

        # GAP-34: Pre-filtrar operacoes via text search no JSON (evita full table scan)
        # Usa cast para text + LIKE para reduzir linhas carregadas em Python
        text_filters = []
        if nf_chave:
            text_filters.append(
                CarviaOperacao.nfs_referenciadas_json.cast(db.String).contains(nf_chave)
            )
        if nf_numero:
            nf_num_norm = nf_numero.lstrip('0') or '0'
            text_filters.append(
                CarviaOperacao.nfs_referenciadas_json.cast(db.String).contains(nf_num_norm)
            )

        base_filter = CarviaOperacao.nfs_referenciadas_json.isnot(None)
        if text_filters:
            operacoes = CarviaOperacao.query.filter(
                base_filter,
                or_(*text_filters),
            ).all()
        else:
            operacoes = CarviaOperacao.query.filter(base_filter).all()

        for operacao in operacoes:
            refs = operacao.nfs_referenciadas_json
            if not isinstance(refs, list):
                continue

            matched = False
            for ref in refs:
                if not isinstance(ref, dict):
                    continue

                # Match 1: por chave de acesso (44 digitos)
                if nf_chave and ref.get('chave') == nf_chave:
                    matched = True
                    break

                # Match 2: por numero_nf + cnpj_emitente normalizados
                ref_numero = ref.get('numero_nf')
                ref_cnpj = re.sub(r'\D', '', ref.get('cnpj_emitente') or '')

                if (ref_numero and nf_numero
                        and ref_numero.lstrip('0') == nf_numero.lstrip('0')
                        and ref_cnpj and nf_cnpj
                        and ref_cnpj == nf_cnpj):
                    matched = True
                    break

            if matched:
                if self._criar_junction_se_necessario(operacao.id, nf.id):
                    junctions_criadas += 1
                    logger.info(
                        f"Re-linking retroativo: op={operacao.id} "
                        f"(CTe {operacao.cte_numero}) -> nf={nf.id} "
                        f"(NF {nf.numero_nf})"
                    )

        return junctions_criadas

    # ------------------------------------------------------------------
    # vincular_operacao_a_itens_fatura_orfaos: quando CTe chega depois da Fatura
    # ------------------------------------------------------------------

    def vincular_operacao_a_itens_fatura_orfaos(self, operacao):
        """Busca itens de fatura cliente com cte_numero correspondente e operacao_id NULL.

        Chamado apos criar CarviaOperacao quando fatura ja foi importada antes.
        Atualiza operacao_id nos itens e cria junctions com NFs vinculadas.

        Cenarios cobertos:
        - Fat→NF→CTe (cenario 3): item tem nf_id, falta operacao_id
        - Fat→CTe→NF (cenario 4): item nao tem nf_id nem operacao_id
        - NF→Fat→CTe (cenario 5): item tem nf_id, falta operacao_id

        Args:
            operacao: CarviaOperacao recem-criada (ja tem id e cte_numero)

        Returns:
            int — numero de itens atualizados
        """
        if not operacao or not operacao.id or not operacao.cte_numero:
            return 0

        from app.carvia.models import CarviaFaturaClienteItem

        # Normalizar cte_numero (sem zeros a esquerda)
        cte_norm = operacao.cte_numero.lstrip('0') or '0'

        # Buscar itens com cte_numero matching e operacao_id NULL
        itens = CarviaFaturaClienteItem.query.filter(
            CarviaFaturaClienteItem.operacao_id.is_(None),
            CarviaFaturaClienteItem.cte_numero.isnot(None),
            func.ltrim(CarviaFaturaClienteItem.cte_numero, '0') == cte_norm,
        ).all()

        count = 0
        for item in itens:
            item.operacao_id = operacao.id
            count += 1
            logger.info(
                f"Re-linking fatura item (CTe): item={item.id} "
                f"cte={item.cte_numero} -> operacao={operacao.id}"
            )

            # Criar junction operacao <-> NF se item ja tem nf_id
            if item.nf_id:
                self._criar_junction_se_necessario(operacao.id, item.nf_id)

            # Backward binding: setar fatura_cliente_id na operacao
            # se ainda nao vinculada. Primeira fatura ganha quando
            # varios itens de faturas diferentes referenciam o mesmo CTe.
            if (item.fatura_cliente_id
                    and operacao.fatura_cliente_id is None):
                operacao.fatura_cliente_id = item.fatura_cliente_id
                operacao.status = 'FATURADO'
                logger.info(
                    f"Backward binding (re-link): operacao={operacao.id} "
                    f"-> fatura_cliente_id={item.fatura_cliente_id} "
                    f"status=FATURADO"
                )

        if count > 0:
            db.session.flush()

        return count

    # ------------------------------------------------------------------
    # vincular_nf_a_itens_fatura_orfaos: quando NF chega depois da Fatura
    # ------------------------------------------------------------------

    def vincular_nf_a_itens_fatura_orfaos(self, nf):
        """Busca itens de fatura cliente com nf_numero correspondente e nf_id pendente.

        Chamado apos criar CarviaNf quando fatura ja foi importada antes.
        Atualiza nf_id nos itens, incluindo os que apontam para FATURA_REFERENCIA stub.
        Cria junctions com operacoes vinculadas.

        Cenarios cobertos:
        - Fat→NF→CTe (cenario 3): item tem nf_id=NULL, falta nf_id
        - Fat→CTe→NF (cenario 4): item pode ter operacao_id, falta nf_id
        - CTe→Fat→NF (cenario 6): item tem operacao_id, falta nf_id

        Trata 2 casos:
        1. nf_id IS NULL (fatura importada antes da NF)
        2. nf_id aponta para FATURA_REFERENCIA stub (auto_criar_nf criou stub)

        Args:
            nf: CarviaNf recem-criada (ja tem id)

        Returns:
            int — numero de itens atualizados
        """
        if not nf or not nf.id or not nf.numero_nf:
            return 0

        from app.carvia.models import CarviaNf, CarviaFaturaClienteItem

        nf_norm = nf.numero_nf.lstrip('0') or '0'
        nf_cnpj_emit = re.sub(r'\D', '', nf.cnpj_emitente or '')
        nf_cnpj_dest = re.sub(r'\D', '', nf.cnpj_destinatario or '')

        count = 0

        # --- Caso 1: itens com nf_id IS NULL ---
        itens_null = CarviaFaturaClienteItem.query.filter(
            CarviaFaturaClienteItem.nf_id.is_(None),
            CarviaFaturaClienteItem.nf_numero.isnot(None),
            func.ltrim(CarviaFaturaClienteItem.nf_numero, '0') == nf_norm,
        ).all()

        for item in itens_null:
            # Filtrar por CNPJ contraparte (emitente OU destinatario da NF)
            if item.contraparte_cnpj:
                item_cnpj = re.sub(r'\D', '', item.contraparte_cnpj)
                if item_cnpj and item_cnpj not in (nf_cnpj_emit, nf_cnpj_dest):
                    continue

            item.nf_id = nf.id
            count += 1
            logger.info(
                f"Re-linking fatura item (NF): item={item.id} "
                f"nf_numero={item.nf_numero} -> nf={nf.id}"
            )

            # Criar junction operacao <-> NF se item ja tem operacao_id
            if item.operacao_id:
                self._criar_junction_se_necessario(item.operacao_id, nf.id)

        # --- Caso 2: itens apontando para FATURA_REFERENCIA stub ---
        if nf_cnpj_emit:
            stubs = CarviaNf.query.filter(
                CarviaNf.tipo_fonte == 'FATURA_REFERENCIA',
                CarviaNf.id != nf.id,  # Nao e a propria NF
                func.ltrim(CarviaNf.numero_nf, '0') == nf_norm,
                func.regexp_replace(
                    CarviaNf.cnpj_emitente, '[^0-9]', '', 'g'
                ) == nf_cnpj_emit,
            ).all()

            stub_ids = [s.id for s in stubs]
            if stub_ids:
                itens_stub = CarviaFaturaClienteItem.query.filter(
                    CarviaFaturaClienteItem.nf_id.in_(stub_ids),
                ).all()

                for item in itens_stub:
                    old_nf_id = item.nf_id
                    item.nf_id = nf.id
                    count += 1
                    logger.info(
                        f"Re-linking fatura item (NF stub->real): item={item.id} "
                        f"nf_numero={item.nf_numero} old_nf_id={old_nf_id} -> nf={nf.id}"
                    )

                    # Criar junction operacao <-> NF se item ja tem operacao_id
                    if item.operacao_id:
                        self._criar_junction_se_necessario(item.operacao_id, nf.id)

        if count > 0:
            db.session.flush()

        return count

    # ------------------------------------------------------------------
    # vincular_operacoes_da_fatura: backward binding operacao -> fatura
    # ------------------------------------------------------------------

    def vincular_operacoes_da_fatura(self, fatura_id):
        """Vincula operacoes a fatura via itens ja existentes (backward binding).

        Busca operacao_id nos CarviaFaturaClienteItem da fatura,
        e para cada operacao com fatura_cliente_id IS NULL,
        seta fatura_cliente_id e muda status para FATURADO.

        Regra de negocio: fatura PDF e evidencia documental de faturamento
        consumado, entao e correto promover status para FATURADO
        independente do status anterior (RASCUNHO/COTADO/CONFIRMADO).

        Returns:
            dict com: operacoes_vinculadas, operacoes_ja_vinculadas, total
        """
        from app.carvia.models import CarviaFaturaClienteItem, CarviaOperacao

        # Buscar operacao_ids distintos nos itens desta fatura
        itens = CarviaFaturaClienteItem.query.filter(
            CarviaFaturaClienteItem.fatura_cliente_id == fatura_id,
            CarviaFaturaClienteItem.operacao_id.isnot(None),
        ).all()

        operacao_ids = list(set(item.operacao_id for item in itens))

        stats = {
            'operacoes_vinculadas': 0,
            'operacoes_ja_vinculadas': 0,
            'total': len(operacao_ids),
        }

        if not operacao_ids:
            return stats

        operacoes = CarviaOperacao.query.filter(
            CarviaOperacao.id.in_(operacao_ids)
        ).all()

        for operacao in operacoes:
            if operacao.fatura_cliente_id is not None:
                stats['operacoes_ja_vinculadas'] += 1
                if operacao.fatura_cliente_id != fatura_id:
                    logger.warning(
                        f"Operacao {operacao.id} ja vinculada a fatura "
                        f"{operacao.fatura_cliente_id}, ignorando fatura {fatura_id}"
                    )
                continue

            operacao.fatura_cliente_id = fatura_id
            operacao.status = 'FATURADO'
            stats['operacoes_vinculadas'] += 1
            logger.info(
                f"Backward binding: operacao={operacao.id} "
                f"(CTe {operacao.cte_numero}) -> fatura_cliente_id={fatura_id} "
                f"status=FATURADO"
            )

        if stats['operacoes_vinculadas'] > 0:
            db.session.flush()

        return stats

    # ------------------------------------------------------------------
    # vincular_itens_fatura_cliente: resolve FKs em itens existentes
    # ------------------------------------------------------------------

    def vincular_itens_fatura_cliente(self, fatura_id, auto_criar_nf=False):
        """Resolve operacao_id e nf_id nos itens de uma fatura cliente existente.

        Itera sobre CarviaFaturaClienteItem onde operacao_id ou nf_id sao NULL
        e tenta resolver via cte_numero e nf_numero.

        Estrategia de resolucao de nf_id (3 niveis):
        1. Match direto via resolver_nf_por_numero() (numero + cnpj)
        2. Fallback via junction carvia_operacao_nfs (se item tem operacao_id)
        3. Ultimo recurso: criar NF referencia (se auto_criar_nf=True)

        Args:
            fatura_id: ID da CarviaFaturaCliente
            auto_criar_nf: Se True, cria CarviaNf stub (tipo_fonte=FATURA_REFERENCIA)
                          quando todos os fallbacks falham. Default False.

        Returns:
            dict com estatisticas
        """
        from app.carvia.models import CarviaFaturaClienteItem

        itens = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fatura_id
        ).all()

        stats = {
            'operacoes_resolvidas': 0,
            'nfs_resolvidas': 0,
            'nfs_via_junction': 0,
            'nfs_criadas_referencia': 0,
            'junctions_criadas': 0,
            'nfs_nao_resolvidas': 0,
            'total_itens': len(itens),
        }

        for item in itens:
            # Resolver operacao_id via cte_numero
            if item.operacao_id is None and item.cte_numero:
                operacao = self.resolver_operacao_por_cte(item.cte_numero)
                if operacao:
                    item.operacao_id = operacao.id
                    stats['operacoes_resolvidas'] += 1
                    logger.info(
                        f"Linking: fat_cli_item={item.id} cte={item.cte_numero} -> op={operacao.id}"
                    )

            # Resolver nf_id via nf_numero + contraparte_cnpj (3 niveis)
            if item.nf_id is None and item.nf_numero:
                nf = None
                metodo = None

                # Nivel 1: Match direto
                nf = self.resolver_nf_por_numero(
                    item.nf_numero, item.contraparte_cnpj
                )
                if nf:
                    metodo = 'direto'

                # Nivel 2: Fallback via junction (se item tem operacao_id)
                if nf is None and item.operacao_id:
                    nf = self._resolver_nf_via_junction(
                        item.nf_numero, item.operacao_id
                    )
                    if nf:
                        metodo = 'junction'
                        stats['nfs_via_junction'] += 1

                # Nivel 3: Criar NF referencia (ultimo recurso)
                if nf is None and auto_criar_nf:
                    nf = self._criar_nf_referencia(
                        nf_numero=item.nf_numero,
                        contraparte_cnpj=item.contraparte_cnpj,
                        contraparte_nome=item.contraparte_nome,
                        valor_mercadoria=item.valor_mercadoria,
                        peso_kg=item.peso_kg,
                        criado_por='importacao',
                    )
                    if nf:
                        metodo = 'referencia_criada'
                        stats['nfs_criadas_referencia'] += 1

                # Vincular NF ao item
                if nf:
                    item.nf_id = nf.id
                    stats['nfs_resolvidas'] += 1
                    logger.info(
                        f"Linking: fat_cli_item={item.id} nf_num={item.nf_numero} "
                        f"-> nf={nf.id} metodo={metodo}"
                    )

                    # Criar junction operacao <-> NF se necessario
                    if item.operacao_id:
                        if self._criar_junction_se_necessario(item.operacao_id, nf.id):
                            stats['junctions_criadas'] += 1
                else:
                    stats['nfs_nao_resolvidas'] += 1
                    logger.warning(
                        f"Linking FALHOU: item={item.id} nf_numero={item.nf_numero} "
                        f"contraparte_cnpj={item.contraparte_cnpj} -> nenhuma NF encontrada"
                    )

        db.session.flush()
        return stats

    # ------------------------------------------------------------------
    # criar_itens_fatura_transportadora: gera itens a partir de subcontratos
    # ------------------------------------------------------------------

    def criar_itens_fatura_transportadora(self, fatura_id):
        """Gera CarviaFaturaTransportadoraItem a partir dos subcontratos vinculados.

        Para cada subcontrato da fatura, cria 1 item com todas as FKs populadas.

        Returns:
            int — numero de itens criados
        """
        from app.carvia.models import (
            CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
            CarviaSubcontrato, CarviaOperacaoNf
        )

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            logger.warning(f"Fatura transportadora {fatura_id} nao encontrada")
            return 0

        # Buscar subcontratos vinculados a esta fatura
        subcontratos = CarviaSubcontrato.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).all()

        if not subcontratos:
            logger.info(f"Fatura transportadora {fatura_id}: nenhum subcontrato vinculado")
            return 0

        # Verificar se ja existem itens (evitar duplicatas)
        itens_existentes = CarviaFaturaTransportadoraItem.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).count()
        if itens_existentes > 0:
            logger.info(
                f"Fatura transportadora {fatura_id}: ja tem {itens_existentes} itens, pulando"
            )
            return 0

        count = 0
        for sub in subcontratos:
            operacao = sub.operacao if hasattr(sub, 'operacao') else None

            # Buscar primeira NF da operacao (para display)
            nf_id = None
            nf_numero = None
            if operacao:
                junction = CarviaOperacaoNf.query.filter_by(
                    operacao_id=operacao.id
                ).first()
                if junction:
                    from app.carvia.models import CarviaNf
                    nf = db.session.get(CarviaNf, junction.nf_id)
                    if nf:
                        nf_id = nf.id
                        nf_numero = nf.numero_nf

            item = CarviaFaturaTransportadoraItem(
                fatura_transportadora_id=fatura_id,
                subcontrato_id=sub.id,
                operacao_id=sub.operacao_id,
                nf_id=nf_id,
                cte_numero=sub.cte_numero,
                cte_data_emissao=sub.cte_data_emissao,
                contraparte_cnpj=operacao.cnpj_cliente if operacao else None,
                contraparte_nome=operacao.nome_cliente if operacao else None,
                nf_numero=nf_numero,
                valor_mercadoria=operacao.valor_mercadoria if operacao else None,
                peso_kg=float(operacao.peso_utilizado or 0) if operacao else None,
                valor_frete=float(sub.valor_final or 0) if sub.valor_final else None,
                valor_cotado=sub.valor_cotado,
                valor_acertado=sub.valor_acertado,
            )
            db.session.add(item)
            count += 1
            logger.info(
                f"Linking: fat_transp_item criado fatura={fatura_id} sub={sub.id} op={sub.operacao_id}"
            )

        db.session.flush()
        return count

    # ------------------------------------------------------------------
    # criar_itens_fatura_transportadora_incremental: apenas novos subs
    # ------------------------------------------------------------------

    def criar_itens_fatura_transportadora_incremental(self, fatura_id, subcontrato_ids):
        """Gera CarviaFaturaTransportadoraItem para subcontratos especificos.

        Similar a criar_itens_fatura_transportadora() mas NAO verifica existentes
        globalmente — cria apenas itens para os subcontratos informados.
        Usado ao anexar subcontratos a fatura existente.

        Args:
            fatura_id: ID da CarviaFaturaTransportadora
            subcontrato_ids: Lista de IDs de subcontratos a gerar itens

        Returns:
            int — numero de itens criados
        """
        from app.carvia.models import (
            CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
            CarviaSubcontrato, CarviaOperacaoNf
        )

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            logger.warning(f"Fatura transportadora {fatura_id} nao encontrada")
            return 0

        if not subcontrato_ids:
            return 0

        subcontratos = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.id.in_(subcontrato_ids),
            CarviaSubcontrato.fatura_transportadora_id == fatura_id,
        ).all()

        if not subcontratos:
            logger.info(
                f"Fatura transportadora {fatura_id}: nenhum subcontrato valido "
                f"entre {subcontrato_ids}"
            )
            return 0

        count = 0
        for sub in subcontratos:
            # Verificar se item ja existe para este subcontrato (idempotencia)
            existente = CarviaFaturaTransportadoraItem.query.filter_by(
                fatura_transportadora_id=fatura_id,
                subcontrato_id=sub.id,
            ).first()
            if existente:
                logger.info(
                    f"Item ja existe: fatura={fatura_id} sub={sub.id}, pulando"
                )
                continue

            operacao = sub.operacao if hasattr(sub, 'operacao') else None

            # Buscar primeira NF da operacao (para display)
            nf_id = None
            nf_numero = None
            if operacao:
                junction = CarviaOperacaoNf.query.filter_by(
                    operacao_id=operacao.id
                ).first()
                if junction:
                    from app.carvia.models import CarviaNf
                    nf = db.session.get(CarviaNf, junction.nf_id)
                    if nf:
                        nf_id = nf.id
                        nf_numero = nf.numero_nf

            item = CarviaFaturaTransportadoraItem(
                fatura_transportadora_id=fatura_id,
                subcontrato_id=sub.id,
                operacao_id=sub.operacao_id,
                nf_id=nf_id,
                cte_numero=sub.cte_numero,
                cte_data_emissao=sub.cte_data_emissao,
                contraparte_cnpj=operacao.cnpj_cliente if operacao else None,
                contraparte_nome=operacao.nome_cliente if operacao else None,
                nf_numero=nf_numero,
                valor_mercadoria=operacao.valor_mercadoria if operacao else None,
                peso_kg=float(operacao.peso_utilizado or 0) if operacao else None,
                valor_frete=float(sub.valor_final or 0) if sub.valor_final else None,
                valor_cotado=sub.valor_cotado,
                valor_acertado=sub.valor_acertado,
            )
            db.session.add(item)
            count += 1
            logger.info(
                f"Linking incremental: fat_transp_item criado "
                f"fatura={fatura_id} sub={sub.id} op={sub.operacao_id}"
            )

        db.session.flush()
        return count

    # ------------------------------------------------------------------
    # criar_itens_fatura_cliente_from_operacoes: gera itens (UI manual)
    # ------------------------------------------------------------------

    def criar_itens_fatura_cliente_from_operacoes(self, fatura_id):
        """Gera CarviaFaturaClienteItem a partir das operacoes vinculadas.

        Usado quando fatura e criada manualmente via UI (nao vem de PDF).
        Para cada operacao da fatura, cria 1 item com FKs populadas.

        Returns:
            int — numero de itens criados
        """
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaFaturaClienteItem,
            CarviaOperacao, CarviaOperacaoNf, CarviaNf
        )

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            logger.warning(f"Fatura cliente {fatura_id} nao encontrada")
            return 0

        # Buscar operacoes vinculadas a esta fatura
        operacoes = CarviaOperacao.query.filter_by(
            fatura_cliente_id=fatura_id
        ).all()

        if not operacoes:
            logger.info(f"Fatura cliente {fatura_id}: nenhuma operacao vinculada")
            return 0

        # Verificar se ja existem itens (evitar duplicatas)
        itens_existentes = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fatura_id
        ).count()
        if itens_existentes > 0:
            logger.info(
                f"Fatura cliente {fatura_id}: ja tem {itens_existentes} itens, pulando"
            )
            return 0

        count = 0
        for op in operacoes:
            # Buscar primeira NF da operacao (para display)
            nf_id = None
            nf_numero = None
            junction = CarviaOperacaoNf.query.filter_by(
                operacao_id=op.id
            ).first()
            if junction:
                nf = db.session.get(CarviaNf, junction.nf_id)
                if nf:
                    nf_id = nf.id
                    nf_numero = nf.numero_nf

            item = CarviaFaturaClienteItem(
                fatura_cliente_id=fatura_id,
                operacao_id=op.id,
                nf_id=nf_id,
                cte_numero=op.cte_numero,
                cte_data_emissao=op.cte_data_emissao,
                contraparte_cnpj=op.cnpj_cliente,
                contraparte_nome=op.nome_cliente,
                nf_numero=nf_numero,
                valor_mercadoria=op.valor_mercadoria,
                peso_kg=float(op.peso_utilizado or 0) if op.peso_utilizado else None,
                frete=op.cte_valor,
            )
            db.session.add(item)
            count += 1
            logger.info(
                f"Linking: fat_cli_item criado fatura={fatura_id} op={op.id} cte={op.cte_numero}"
            )

        db.session.flush()
        return count

    # ------------------------------------------------------------------
    # backfill_todas_faturas: one-time para dados existentes
    # ------------------------------------------------------------------

    def backfill_todas_faturas(self):
        """Backfill de FKs em todos os itens de faturas existentes.

        1. Para cada fatura_cliente: resolver operacao_id e nf_id nos itens
        2. Para cada fatura_transportadora: gerar itens a partir de subcontratos

        Returns:
            dict com estatisticas globais
        """
        from app.carvia.models import CarviaFaturaCliente, CarviaFaturaTransportadora

        stats = {
            'faturas_cliente': 0,
            'operacoes_resolvidas': 0,
            'nfs_resolvidas': 0,
            'faturas_transportadora': 0,
            'itens_transportadora_criados': 0,
        }

        # 1. Backfill faturas cliente
        faturas_cli = CarviaFaturaCliente.query.all()
        for fatura in faturas_cli:
            result = self.vincular_itens_fatura_cliente(fatura.id)
            stats['faturas_cliente'] += 1
            stats['operacoes_resolvidas'] += result['operacoes_resolvidas']
            stats['nfs_resolvidas'] += result['nfs_resolvidas']

        # 2. Gerar itens faturas transportadora
        faturas_transp = CarviaFaturaTransportadora.query.all()
        for fatura in faturas_transp:
            count = self.criar_itens_fatura_transportadora(fatura.id)
            stats['faturas_transportadora'] += 1
            stats['itens_transportadora_criados'] += count

        db.session.flush()
        logger.info(f"Backfill concluido: {stats}")
        return stats
