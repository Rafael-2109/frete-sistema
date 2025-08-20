#!/usr/bin/env python
"""
Script para verificar emails anexados no banco de dados
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.email_models import EmailAnexado
from app.fretes.models import DespesaExtra, Frete

app = create_app()

with app.app_context():
    print("="*60)
    print("VERIFICANDO EMAILS ANEXADOS NO SISTEMA")
    print("="*60)
    
    # 1. Contar total de emails
    total_emails = EmailAnexado.query.count()
    print(f"\n✅ Total de emails no banco: {total_emails}")
    
    if total_emails > 0:
        # 2. Listar emails com suas despesas
        print("\n📧 EMAILS CADASTRADOS:")
        print("-"*60)
        emails = EmailAnexado.query.all()
        for email in emails[:5]:  # Mostra apenas os 5 primeiros
            print(f"\nEmail ID: {email.id}")
            print(f"  Arquivo: {email.nome_arquivo}")
            print(f"  Assunto: {email.assunto}")
            print(f"  Despesa ID: {email.despesa_extra_id}")
            if email.despesa_extra:
                print(f"  Frete ID: {email.despesa_extra.frete_id}")
                print(f"  Tipo Despesa: {email.despesa_extra.tipo_despesa}")
    
    # 3. Verificar fretes com emails
    print("\n🚚 FRETES COM EMAILS:")
    print("-"*60)
    
    # Query para buscar fretes que têm emails
    fretes_com_emails = db.session.query(Frete.id, Frete.numero_cte, db.func.count(EmailAnexado.id).label('qtd_emails'))\
        .join(DespesaExtra, Frete.id == DespesaExtra.frete_id)\
        .join(EmailAnexado, DespesaExtra.id == EmailAnexado.despesa_extra_id)\
        .group_by(Frete.id, Frete.numero_cte)\
        .all()
    
    if fretes_com_emails:
        for frete in fretes_com_emails:
            print(f"Frete ID: {frete.id} | CTe: {frete.numero_cte} | Emails: {frete.qtd_emails}")
            print(f"  URL para visualizar: /fretes/{frete.id}")
    else:
        print("Nenhum frete com emails encontrado")
    
    # 4. Verificar despesas extras
    print("\n💰 DESPESAS COM EMAILS:")
    print("-"*60)
    
    despesas_com_emails = db.session.query(DespesaExtra.id, DespesaExtra.tipo_despesa, DespesaExtra.frete_id, db.func.count(EmailAnexado.id).label('qtd_emails'))\
        .join(EmailAnexado, DespesaExtra.id == EmailAnexado.despesa_extra_id)\
        .group_by(DespesaExtra.id, DespesaExtra.tipo_despesa, DespesaExtra.frete_id)\
        .all()
    
    if despesas_com_emails:
        for despesa in despesas_com_emails:
            print(f"Despesa ID: {despesa.id} | Tipo: {despesa.tipo_despesa} | Frete: {despesa.frete_id} | Emails: {despesa.qtd_emails}")
    else:
        print("Nenhuma despesa com emails encontrada")
    
    # 5. Verificar se a tabela existe
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    if 'emails_anexados' in inspector.get_table_names():
        print("\n✅ Tabela 'emails_anexados' existe no banco")
    else:
        print("\n❌ Tabela 'emails_anexados' NÃO existe! Execute: python create_email_tables.py")
    
    print("\n" + "="*60)
    print("VERIFICAÇÃO CONCLUÍDA")
    print("="*60)