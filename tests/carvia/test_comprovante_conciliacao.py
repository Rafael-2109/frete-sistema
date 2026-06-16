"""Testes — conciliacao invertida (Frente 3d).

Cobre o DESTINO da feature de comprovantes: listar faturas cliente com
comprovante e saldo em aberto + extrair o CNPJ de quem realmente pagou
(que pode != CNPJ da fatura — caso central do recurso).
"""

from __future__ import annotations

from decimal import Decimal
from datetime import date


def _criar_fatura(db, num='FAT-C1', valor='1000.00'):
    from app.carvia.models import CarviaFaturaCliente
    f = CarviaFaturaCliente(
        cnpj_cliente='22222222000122', nome_cliente='Cliente Teste',
        numero_fatura=num, data_emissao=date(2026, 6, 1),
        valor_total=Decimal(valor), status='PENDENTE', criado_por='test',
    )
    db.session.add(f)
    db.session.flush()
    return f


def _comp_na_fatura(db, fat_id, cnpj_pagador='33333333000133', valor='1000.00'):
    from app.carvia.models import CarviaComprovantePagamento, CarviaComprovanteVinculo
    comp = CarviaComprovantePagamento(
        nome_original='pix.pdf', nome_arquivo='s.pdf',
        caminho_s3='carvia/comprovantes/p.pdf',
        valor=Decimal(valor), data_pagamento=date(2026, 6, 2),
        cnpj_pagador=cnpj_pagador, criado_por='test',
    )
    db.session.add(comp)
    db.session.flush()
    db.session.add(CarviaComprovanteVinculo(
        comprovante_id=comp.id, entidade_tipo='fatura_cliente', entidade_id=fat_id,
        origem='MANUAL', criado_por='test',
    ))
    db.session.flush()
    return comp


class TestConciliacaoInvertida:

    def test_cnpjs_pagadores_ignora_vazio(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        f = _criar_fatura(db)
        _comp_na_fatura(db, f.id, cnpj_pagador='33333333000133')
        _comp_na_fatura(db, f.id, cnpj_pagador=None)  # sem cnpj -> ignorado

        cnpjs = CarviaComprovanteService.cnpjs_pagadores('fatura_cliente', f.id)
        assert '33333333000133' in cnpjs
        assert None not in cnpjs
        assert '' not in cnpjs

    def test_faturas_com_comprovante_lista_com_saldo(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        f = _criar_fatura(db, num='FAT-S1', valor='1000.00')
        _comp_na_fatura(db, f.id, cnpj_pagador='33333333000133')

        flist = CarviaComprovanteService.faturas_cliente_com_comprovante()
        item = next((x for x in flist if x['id'] == f.id), None)
        assert item is not None
        assert item['saldo'] == 1000.00
        assert len(item['comprovantes']) == 1
        assert item['comprovantes'][0]['cnpj_pagador'] == '33333333000133'

    def test_fatura_sem_comprovante_nao_aparece(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        f = _criar_fatura(db, num='FAT-NO')
        flist = CarviaComprovanteService.faturas_cliente_com_comprovante()
        assert f.id not in {x['id'] for x in flist}

    def test_fatura_comprovante_inativo_nao_aparece(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        f = _criar_fatura(db, num='FAT-INA')
        comp = _comp_na_fatura(db, f.id)
        comp.ativo = False
        db.session.flush()

        flist = CarviaComprovanteService.faturas_cliente_com_comprovante()
        assert f.id not in {x['id'] for x in flist}
