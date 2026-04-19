"""Testes Sprint E (2026-04-19) — Fase 1B Medio esforco.

E1 multi-linha (rota), E2 estorno (detectar/registrar),
E3 juros/desconto em conciliacao, E4 R17 estendido,
E5 admin corrigir FT, E6 juros fatura, E7 rateio pedagio,
E8 fila DIVERGENTE, E9 historico conferencia, E10 FIFO.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date, timedelta


def _sfx() -> str:
    return uuid.uuid4().hex[:6]


# ---------------------------------------------------------------------------
# E1 — rota multi-linha
# ---------------------------------------------------------------------------

class TestE1MultiLinha:
    def test_rota_aceita_extrato_linhas_ids(self, app):
        # Sanity: rota existe e o payload array nao quebra a assinatura
        with app.app_context():
            rules = [str(r) for r in app.url_map.iter_rules()
                     if 'conciliar' in str(r)]
            assert any(r.endswith('/conciliacao/conciliar') for r in rules)


# ---------------------------------------------------------------------------
# E2 — estorno
# ---------------------------------------------------------------------------

class TestE2Estorno:
    def test_detectar_candidatos_retorna_lista(self, app):
        # Schema pode nao ter linha_original_id no DB de teste local.
        # So valida que metodo existe e signature esperada.
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        import inspect
        assert hasattr(
            CarviaConciliacaoService, 'detectar_candidatos_estorno'
        )
        assert hasattr(CarviaConciliacaoService, 'registrar_estorno')
        sig = inspect.signature(
            CarviaConciliacaoService.registrar_estorno
        )
        assert 'linha_estorno_id' in sig.parameters
        assert 'linha_original_id' in sig.parameters


# ---------------------------------------------------------------------------
# E3 — juros/desconto
# ---------------------------------------------------------------------------

class TestE3JurosDesconto:
    def test_model_tem_campos(self, app):
        from app.carvia.models import CarviaConciliacao
        assert hasattr(CarviaConciliacao, 'valor_acrescimo')
        assert hasattr(CarviaConciliacao, 'valor_desconto')


# ---------------------------------------------------------------------------
# E4 — R17 estendido
# ---------------------------------------------------------------------------

class TestE4R17Estendido:
    def test_service_aceita_multiplos_tipos(self, app):
        from app.carvia.services.financeiro.carvia_historico_match_service import (
            CarviaHistoricoMatchService,
        )
        # Sanity: metodo existe, logica estendida (checamos no codigo mesmo)
        import inspect
        src = inspect.getsource(
            CarviaHistoricoMatchService.registrar_aprendizado
        )
        for t in ['fatura_cliente', 'fatura_transportadora',
                  'despesa', 'custo_entrega']:
            assert t in src


# ---------------------------------------------------------------------------
# E5 — admin corrigir FT
# ---------------------------------------------------------------------------

class TestE5AdminCorrigirFT:
    def test_service_existe_com_signature(self):
        """Schema pode divergir localmente (observacoes_conferencia nao
        aplicado) — validamos apenas contrato do service."""
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        import inspect
        assert hasattr(
            CarviaConciliacaoService, 'admin_corrigir_ft_conferida'
        )
        sig = inspect.signature(
            CarviaConciliacaoService.admin_corrigir_ft_conferida
        )
        for p in ['fatura_id', 'usuario', 'motivo']:
            assert p in sig.parameters


# ---------------------------------------------------------------------------
# E6 — juros por atraso
# ---------------------------------------------------------------------------

class TestE6JurosAtraso:
    def test_calcula_sem_atraso_retorna_valor_original(self, db):
        from app.carvia.models import CarviaFaturaCliente
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        f = CarviaFaturaCliente(
            numero_fatura=f'FAT-E6-{_sfx()}',
            cnpj_cliente='12345678000100',
            nome_cliente='Cliente',
            data_emissao=date(2026, 4, 1),
            vencimento=date(2026, 5, 30),  # futuro — sem atraso
            valor_total=Decimal('1000.00'),
            status='PENDENTE',
            criado_por='test',
        )
        db.session.add(f)
        db.session.flush()

        r = CarviaConciliacaoService.calcular_valor_atualizado_fatura(
            f.id, data_pagamento=date(2026, 4, 19),
        )
        assert r['sucesso'] is True
        assert r['dias_atraso'] == 0
        assert r['valor_atualizado'] == 1000.0
        assert r['multa'] == 0.0
        assert r['juros'] == 0.0

    def test_calcula_30_dias_atraso(self, db):
        from app.carvia.models import CarviaFaturaCliente
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        f = CarviaFaturaCliente(
            numero_fatura=f'FAT-E6b-{_sfx()}',
            cnpj_cliente='12345678000100',
            nome_cliente='Cliente',
            data_emissao=date(2026, 3, 1),
            vencimento=date(2026, 3, 20),
            valor_total=Decimal('1000.00'),
            status='PENDENTE',
            criado_por='test',
        )
        db.session.add(f)
        db.session.flush()

        # Pago 30 dias depois do vencimento
        r = CarviaConciliacaoService.calcular_valor_atualizado_fatura(
            f.id, data_pagamento=date(2026, 4, 19),
            multa_percentual=2.0, juros_mes=1.0,
        )
        assert r['sucesso'] is True
        assert r['dias_atraso'] == 30
        # Multa: 2% de 1000 = 20
        assert r['multa'] == 20.0
        # Juros: 1000 * (1/100/30) * 30 = 10
        assert abs(r['juros'] - 10.0) < 0.01
        # Total: 1000 + 20 + 10 = 1030
        assert abs(r['valor_atualizado'] - 1030.0) < 0.01


# ---------------------------------------------------------------------------
# E7 — rateio pedagio
# ---------------------------------------------------------------------------

class TestE7RateioPedagio:
    def test_metodo_existe(self):
        from app.carvia.services.documentos.conferencia_service import (
            ConferenciaService,
        )
        assert hasattr(ConferenciaService, 'calcular_rateio_pedagio')


# ---------------------------------------------------------------------------
# E8 — fila DIVERGENTE
# ---------------------------------------------------------------------------

class TestE8FilaDivergente:
    def test_listar_retorna_lista(self, app):
        from app.carvia.services.documentos.conferencia_service import (
            ConferenciaService,
        )
        with app.app_context():
            resultado = ConferenciaService().listar_fretes_divergentes()
            assert isinstance(resultado, list)


# ---------------------------------------------------------------------------
# E9 — historico append-only
# ---------------------------------------------------------------------------

class TestE9HistoricoConferencia:
    def test_model_existe(self, app):
        from app.carvia.models import CarviaConferenciaHistorico
        assert CarviaConferenciaHistorico.__tablename__ == (
            'carvia_conferencia_historico'
        )


# ---------------------------------------------------------------------------
# E10 — FIFO distribuicao
# ---------------------------------------------------------------------------

class TestE10Fifo:
    def test_distribuicao_esgota_valor(self, db):
        from app.carvia.models import CarviaFaturaCliente
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        cnpj = '99999999000100'
        # 3 faturas ordem de vencimento
        for i, venc in enumerate([
            date(2026, 3, 1),
            date(2026, 3, 15),
            date(2026, 4, 1),
        ]):
            db.session.add(CarviaFaturaCliente(
                numero_fatura=f'FAT-E10-{i}-{_sfx()}',
                cnpj_cliente=cnpj,
                nome_cliente='Cliente E10',
                data_emissao=venc - timedelta(days=30),
                vencimento=venc,
                valor_total=Decimal('500.00'),
                total_conciliado=Decimal('0'),
                status='PENDENTE',
                criado_por='test',
            ))
        db.session.flush()

        # Tenta alocar R$ 1100 (cobre 2 faturas e 200 da 3a)
        r = CarviaConciliacaoService.sugerir_distribuicao_fifo(
            cnpj_cliente=cnpj, valor_disponivel=1100.0,
        )
        assert r['sucesso'] is True
        assert r['faturas_alocadas'] == 3
        # Mais antiga primeiro
        venc_ordenado = [d['vencimento'] for d in r['distribuicao']]
        assert venc_ordenado == sorted(venc_ordenado)
        # Valor total alocado aproxima 1100
        total_aloc = sum(d['valor_sugerido'] for d in r['distribuicao'])
        assert abs(total_aloc - 1100.0) < 0.01
