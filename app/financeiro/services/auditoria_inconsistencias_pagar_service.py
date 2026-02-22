# -*- coding: utf-8 -*-
"""
Servico de Auditoria de Inconsistencias Local x Odoo — Contas a Pagar
======================================================================

Detecta divergencias entre o estado de pagamento em contas_a_pagar (local)
e o estado real no Odoo (account.move.line).

Casos detectados:
- PAGO_LOCAL_ABERTO_ODOO: parcela_paga=True mas Odoo mostra not_paid/partial
- VALOR_RESIDUAL_DIVERGENTE: valor_residual local != abs(amount_residual) Odoo
- SEM_MATCH_ODOO: odoo_line_id existe mas registro nao encontrado no Odoo

Diferencas vs Contas a Receber:
- Model: ContasAPagar (nao ContasAReceber)
- Odoo fields: SEM x_studio_status_de_pagamento (2 sinais, nao 3)
- amount_residual Odoo: NEGATIVO para contas a pagar → comparar abs()
- Campo local: `reconciliado` (Boolean) em vez de `status_pagamento_odoo` (String)

IMPORTANTE:
- Este servico e READ-ONLY no Odoo (nao altera dados no Odoo)
- So escreve o campo inconsistencia_odoo em contas_a_pagar (flag)
- NAO altera parcela_paga, valor_residual, reconciliado nem nenhum outro campo

Uso:
    from app.financeiro.services.auditoria_inconsistencias_pagar_service import AuditoriaInconsistenciasPagarService
    service = AuditoriaInconsistenciasPagarService()
    resultado = service.detectar_inconsistencias(empresa=3, dry_run=False)

Data: 2026-02-21
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app import db
from app.utils.timezone import agora_utc_naive
from app.financeiro.models import ContasAPagar

logger = logging.getLogger(__name__)

# Tamanho de batch para search_read Odoo
BATCH_SIZE = 500

# Tolerancia para comparacao de valor_residual (R$ 0,02)
TOLERANCIA_RESIDUAL = 0.02


class AuditoriaInconsistenciasPagarService:
    """
    Servico de deteccao de inconsistencias entre dados locais e Odoo (contas a pagar).

    Estrategia:
    1. Busca registros contas_a_pagar com odoo_line_id
    2. Em batches de 500, busca os account.move.line no Odoo
    3. Compara: parcela_paga local vs 2-sinais Odoo (l10n_br_paga, amount_residual, reconciled)
    4. Se divergente -> seta inconsistencia_odoo
    5. Se consistente e tinha flag -> limpa flag, seta inconsistencia_resolvida_em

    GOTCHA: NAO incluir move_id/partner_id no search_read (causa partner_imovel_id error
    em algumas configuracoes Odoo).

    GOTCHA O3: amount_residual NEGATIVO para contas a pagar. Sempre comparar abs().
    """

    def __init__(self, connection=None):
        """
        Args:
            connection: Conexao Odoo (opcional, sera criada se nao fornecida)
        """
        self._connection = connection
        self.estatisticas = {
            'total_verificados': 0,
            'inconsistencias_detectadas': 0,
            'inconsistencias_limpas': 0,
            'sem_match_odoo': 0,
            'erros_batch': 0,
            'detalhes_por_tipo': {},
            'inicio': None,
            'fim': None,
            'duracao_segundos': 0,
        }

    @property
    def connection(self):
        """Retorna a conexao Odoo, criando se necessario (lazy import)."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
        return self._connection

    def detectar_inconsistencias(
        self,
        empresa: int = None,
        dry_run: bool = True,
        apenas_pagos: bool = True,
    ) -> Dict:
        """
        Detecta inconsistencias sem alterar dados locais (exceto o flag).

        Args:
            empresa: Filtrar por empresa (1=FB, 2=SC, 3=CD). None = todas.
            dry_run: Se True, apenas lista sem atualizar flags.
            apenas_pagos: Se True, verifica apenas registros com parcela_paga=True.
                          Se False, verifica TODOS com odoo_line_id.

        Returns:
            Dict com estatisticas e lista de inconsistencias encontradas.
        """
        inicio = datetime.now()
        self.estatisticas['inicio'] = agora_utc_naive()

        logger.info(
            f"[AuditoriaPagar] Iniciando deteccao de inconsistencias "
            f"(empresa={empresa}, dry_run={dry_run}, apenas_pagos={apenas_pagos})"
        )

        # 1. Buscar registros locais para verificar
        registros = self._buscar_registros_locais(empresa, apenas_pagos)
        total = len(registros)
        logger.info(f"[AuditoriaPagar] {total} registros locais para verificar")

        if total == 0:
            self.estatisticas['fim'] = agora_utc_naive()
            return self._resultado(dry_run)

        # 2. Processar em batches
        inconsistencias = []
        for i in range(0, total, BATCH_SIZE):
            batch = registros[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"[AuditoriaPagar] Batch {batch_num}/{total_batches} ({len(batch)} registros)")

            try:
                batch_result = self._processar_batch(batch, dry_run)
                inconsistencias.extend(batch_result)
            except Exception as e:
                logger.error(f"[AuditoriaPagar] Erro no batch {batch_num}: {e}")
                self.estatisticas['erros_batch'] += 1

        # 3. Commit se nao e dry_run
        if not dry_run:
            try:
                db.session.commit()
                logger.info("[AuditoriaPagar] Flags atualizados no banco")
            except Exception as e:
                db.session.rollback()
                logger.error(f"[AuditoriaPagar] Erro ao gravar: {e}")
                raise

        duracao = (datetime.now() - inicio).total_seconds()
        self.estatisticas['fim'] = agora_utc_naive()
        self.estatisticas['duracao_segundos'] = round(duracao, 1)

        logger.info(
            f"[AuditoriaPagar] Concluida em {duracao:.1f}s — "
            f"{self.estatisticas['inconsistencias_detectadas']} inconsistencias detectadas, "
            f"{self.estatisticas['inconsistencias_limpas']} limpas"
        )

        resultado = self._resultado(dry_run)
        resultado['inconsistencias'] = inconsistencias
        return resultado

    def limpar_inconsistencias_resolvidas(self, empresa: int = None) -> Dict:
        """
        Re-verifica registros flagados e limpa se Odoo agora confirma pagamento.

        Util para execucao periodica: apos reconciliacao manual no Odoo,
        o flag e limpo automaticamente na proxima execucao.

        Returns:
            Dict com quantidade de flags limpos.
        """
        logger.info(f"[AuditoriaPagar] Limpando inconsistencias resolvidas (empresa={empresa})")

        query = ContasAPagar.query.filter(
            ContasAPagar.inconsistencia_odoo.isnot(None),
            ContasAPagar.odoo_line_id.isnot(None),
        )
        if empresa:
            query = query.filter(ContasAPagar.empresa == empresa)

        registros = query.all()
        logger.info(f"[AuditoriaPagar] {len(registros)} registros flagados para re-verificar")

        if not registros:
            return {'limpas': 0, 'mantidas': 0}

        # Reutiliza detectar_inconsistencias com dry_run=False
        resultado = self.detectar_inconsistencias(
            empresa=empresa,
            dry_run=False,
            apenas_pagos=False,
        )

        return {
            'limpas': resultado.get('inconsistencias_limpas', 0),
            'mantidas': resultado.get('inconsistencias_detectadas', 0),
        }

    def contar_inconsistencias(self, empresa: int = None) -> Dict:
        """
        Conta inconsistencias ativas sem consultar Odoo (leitura local).

        Returns:
            Dict com contagens por tipo de inconsistencia.
        """
        query = db.session.query(
            ContasAPagar.inconsistencia_odoo,
            db.func.count(ContasAPagar.id),
        ).filter(
            ContasAPagar.inconsistencia_odoo.isnot(None),
        ).group_by(
            ContasAPagar.inconsistencia_odoo,
        )

        if empresa:
            query = query.filter(ContasAPagar.empresa == empresa)

        resultados = query.all()

        contagens = {}
        total = 0
        for tipo, qtd in resultados:
            contagens[tipo] = qtd
            total += qtd

        return {
            'total': total,
            'por_tipo': contagens,
        }

    # =========================================================================
    # METODOS INTERNOS
    # =========================================================================

    def _buscar_registros_locais(
        self,
        empresa: int = None,
        apenas_pagos: bool = True,
    ) -> List[ContasAPagar]:
        """Busca registros locais para verificar contra Odoo."""
        query = ContasAPagar.query.filter(
            ContasAPagar.odoo_line_id.isnot(None),
        )

        if empresa:
            query = query.filter(ContasAPagar.empresa == empresa)

        if apenas_pagos:
            query = query.filter(ContasAPagar.parcela_paga == True)

        return query.all()

    def _processar_batch(
        self,
        registros: List[ContasAPagar],
        dry_run: bool,
    ) -> List[Dict]:
        """
        Processa um batch de registros: busca no Odoo e compara.

        Returns:
            Lista de dicts descrevendo cada inconsistencia encontrada.
        """
        # Mapear odoo_line_id -> registro local
        mapa_local = {r.odoo_line_id: r for r in registros}
        odoo_ids = list(mapa_local.keys())

        # Buscar no Odoo (apenas campos necessarios, SEM move_id/partner_id)
        # DIFERENCA vs Receber: SEM x_studio_status_de_pagamento (contas a pagar nao usa)
        try:
            linhas_odoo = self.connection.search_read(
                'account.move.line',
                [['id', 'in', odoo_ids]],
                fields=[
                    'id',
                    'l10n_br_paga',
                    'amount_residual',
                    'reconciled',
                    'balance',
                ],
                limit=BATCH_SIZE + 100,  # margem para seguranca
            )
        except Exception as e:
            logger.error(f"[AuditoriaPagar] Erro ao buscar Odoo batch: {e}")
            self.estatisticas['erros_batch'] += 1
            return []

        # Mapear odoo_id -> dados Odoo
        mapa_odoo = {linha['id']: linha for linha in linhas_odoo}

        inconsistencias = []

        for odoo_id, registro in mapa_local.items():
            self.estatisticas['total_verificados'] += 1

            linha_odoo = mapa_odoo.get(odoo_id)

            if linha_odoo is None:
                # Registro nao encontrado no Odoo
                inc = self._marcar_inconsistencia(
                    registro, 'SEM_MATCH_ODOO', dry_run,
                    detalhe=f"odoo_line_id={odoo_id} nao encontrado no Odoo",
                )
                if inc:
                    inconsistencias.append(inc)
                continue

            # Comparar estado local vs Odoo
            inc = self._comparar_estado(registro, linha_odoo, dry_run)
            if inc:
                inconsistencias.append(inc)

        return inconsistencias

    def _comparar_estado(
        self,
        registro: ContasAPagar,
        linha_odoo: Dict,
        dry_run: bool,
    ) -> Optional[Dict]:
        """
        Compara estado local vs Odoo para um registro especifico.

        Regra de 2 sinais Odoo (diferente de Receber que tem 3):
        - l10n_br_paga: flag booleano do Odoo
        - amount_residual: valor remanescente (0 = totalmente pago)
          GOTCHA O3: NEGATIVO para contas a pagar → usar abs()
        - reconciled: flag booleano de reconciliacao

        Returns:
            Dict descrevendo a inconsistencia, ou None se consistente.
        """
        # Dados locais
        paga_local = registro.parcela_paga
        residual_local = registro.valor_residual

        # Dados Odoo
        paga_odoo = bool(linha_odoo.get('l10n_br_paga'))
        amount_residual_odoo = float(linha_odoo.get('amount_residual', 0) or 0)
        # GOTCHA O3: amount_residual NEGATIVO para contas a pagar
        residual_odoo = abs(amount_residual_odoo)
        reconciled_odoo = bool(linha_odoo.get('reconciled'))

        # =====================================================================
        # CASO 1: parcela_paga=True local, mas Odoo NAO confirma pagamento
        # =====================================================================
        if paga_local:
            # Odoo considera pago se QUALQUER sinal confirma:
            # - l10n_br_paga=True OU amount_residual ~ 0 OU reconciled=True
            odoo_confirma_pago = (
                paga_odoo
                or residual_odoo < TOLERANCIA_RESIDUAL
                or reconciled_odoo
            )

            if not odoo_confirma_pago:
                return self._marcar_inconsistencia(
                    registro, 'PAGO_LOCAL_ABERTO_ODOO', dry_run,
                    detalhe=(
                        f"Local: paga=True, residual={residual_local} | "
                        f"Odoo: l10n_br_paga={paga_odoo}, "
                        f"amount_residual={amount_residual_odoo}, "
                        f"reconciled={reconciled_odoo}"
                    ),
                )

        # =====================================================================
        # CASO 2: valor_residual divergente (verificar se faz sentido)
        # =====================================================================
        if residual_local is not None and residual_odoo > TOLERANCIA_RESIDUAL:
            diff = abs((residual_local or 0) - residual_odoo)
            if diff > TOLERANCIA_RESIDUAL:
                # Divergencia de residual, mas so se for significativa
                # Nao marcar se ja tiver inconsistencia mais grave
                if not registro.inconsistencia_odoo or registro.inconsistencia_odoo == 'VALOR_RESIDUAL_DIVERGENTE':
                    return self._marcar_inconsistencia(
                        registro, 'VALOR_RESIDUAL_DIVERGENTE', dry_run,
                        detalhe=(
                            f"Local residual={residual_local} vs "
                            f"Odoo residual={residual_odoo} "
                            f"(diff={diff:.2f})"
                        ),
                    )

        # =====================================================================
        # SEM INCONSISTENCIA — limpar flag se existia
        # =====================================================================
        if registro.inconsistencia_odoo:
            return self._limpar_inconsistencia(registro, dry_run)

        return None

    def _marcar_inconsistencia(
        self,
        registro: ContasAPagar,
        tipo: str,
        dry_run: bool,
        detalhe: str = '',
    ) -> Optional[Dict]:
        """Marca ou atualiza flag de inconsistencia em um registro."""
        agora = agora_utc_naive()

        info = {
            'id': registro.id,
            'empresa': registro.empresa,
            'titulo_nf': registro.titulo_nf,
            'parcela': registro.parcela,
            'cnpj': registro.cnpj,
            'raz_social': registro.raz_social,
            'valor_residual': registro.valor_residual,
            'metodo_baixa': registro.metodo_baixa,
            'inconsistencia': tipo,
            'detalhe': detalhe,
            'acao': 'detectada' if not registro.inconsistencia_odoo else 'mantida',
        }

        if not dry_run:
            if registro.inconsistencia_odoo != tipo:
                registro.inconsistencia_odoo = tipo
                registro.inconsistencia_detectada_em = agora
                registro.inconsistencia_resolvida_em = None

        self.estatisticas['inconsistencias_detectadas'] += 1
        self.estatisticas['detalhes_por_tipo'][tipo] = \
            self.estatisticas['detalhes_por_tipo'].get(tipo, 0) + 1

        if tipo == 'SEM_MATCH_ODOO':
            self.estatisticas['sem_match_odoo'] += 1

        logger.debug(
            f"  [{tipo}] {registro.titulo_nf}-{registro.parcela} "
            f"(empresa={registro.empresa}): {detalhe}"
        )

        return info

    def _limpar_inconsistencia(
        self,
        registro: ContasAPagar,
        dry_run: bool,
    ) -> Optional[Dict]:
        """Limpa flag de inconsistencia quando Odoo confirma estado OK."""
        agora = agora_utc_naive()

        info = {
            'id': registro.id,
            'empresa': registro.empresa,
            'titulo_nf': registro.titulo_nf,
            'parcela': registro.parcela,
            'inconsistencia_anterior': registro.inconsistencia_odoo,
            'acao': 'resolvida',
        }

        if not dry_run:
            registro.inconsistencia_odoo = None
            registro.inconsistencia_resolvida_em = agora

        self.estatisticas['inconsistencias_limpas'] += 1

        logger.info(
            f"  [RESOLVIDA] {registro.titulo_nf}-{registro.parcela}: "
            f"inconsistencia {registro.inconsistencia_odoo} limpa"
        )

        return info

    def _resultado(self, dry_run: bool) -> Dict:
        """Monta dict de resultado final."""
        return {
            'sucesso': True,
            'dry_run': dry_run,
            **self.estatisticas,
        }
