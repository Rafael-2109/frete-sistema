"""
Script para testar filtros invertidos nas separações
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.localidades.models import CadastroRota, CadastroSubRota
from sqlalchemy import func, and_, or_, not_

app = create_app()

with app.app_context():
    print("="*80)
    print("DEBUG: Filtros Invertidos")
    print("="*80)

    # PASSO 1: Buscar algumas separações
    print("\n[PASSO 1] Total de separações com expedicao...")

    total_com_expedicao = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None)
    ).scalar()

    print(f"   Total: {total_com_expedicao}")

    # PASSO 2: Simular filtro - vamos filtrar por UF="SP"
    print("\n[PASSO 2] Separações COM filtro UF='SP'...")

    total_sp = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None),
        Separacao.cod_uf == 'SP'
    ).scalar()

    print(f"   Separações em SP: {total_sp}")

    # PASSO 3: Aplicar NOT (deveria retornar as que NÃO são de SP)
    print("\n[PASSO 3] Separações SEM filtro UF='SP' (invertido)...")

    total_nao_sp = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None),
        not_(Separacao.cod_uf == 'SP')
    ).scalar()

    print(f"   Separações NÃO em SP: {total_nao_sp}")
    print(f"   Validação: {total_sp} + {total_nao_sp} = {total_sp + total_nao_sp} (deve ser {total_com_expedicao})")

    # PASSO 4: Testar com AND de múltiplas condições
    print("\n[PASSO 4] Teste com múltiplas condições...")

    # Com filtros: UF=SP E rota=CIF-SP
    query_com_filtros = db.session.query(func.count(Separacao.id)).outerjoin(
        CadastroRota,
        Separacao.cod_uf == CadastroRota.cod_uf
    ).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None),
        Separacao.cod_uf == 'SP',
        CadastroRota.rota == 'CIF-SP'
    ).scalar()

    print(f"   Com filtros (UF=SP AND Rota=CIF-SP): {query_com_filtros}")

    # SEM filtros (invertido) - deveria retornar: NÃO (UF=SP AND Rota=CIF-SP)
    query_sem_filtros = db.session.query(func.count(Separacao.id)).outerjoin(
        CadastroRota,
        Separacao.cod_uf == CadastroRota.cod_uf
    ).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None),
        not_(and_(
            Separacao.cod_uf == 'SP',
            CadastroRota.rota == 'CIF-SP'
        ))
    ).scalar()

    print(f"   SEM filtros (invertido): {query_sem_filtros}")
    print(f"   Validação: {query_com_filtros} + {query_sem_filtros} = {query_com_filtros + query_sem_filtros}")

    # PASSO 5: Testar se alguma separação está em SP mas sem rota
    print("\n[PASSO 5] Investigar separações em SP sem rota definida...")

    sp_sem_rota = db.session.query(func.count(Separacao.id)).outerjoin(
        CadastroRota,
        Separacao.cod_uf == CadastroRota.cod_uf
    ).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None),
        Separacao.cod_uf == 'SP',
        CadastroRota.rota.is_(None)
    ).scalar()

    print(f"   Separações em SP SEM rota definida: {sp_sem_rota}")

    print("\n" + "="*80)
    print("✅ DEBUG CONCLUÍDO!")
    print("="*80)
