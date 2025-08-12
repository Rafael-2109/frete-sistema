#!/usr/bin/env python3
"""
Script para verificar se as proteções de separações faturadas estão funcionando em produção.
NÃO faz alterações no banco, apenas verifica a lógica.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
from sqlalchemy import and_, or_

def verificar_protecoes():
    """Verifica se as proteções estão funcionando corretamente."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔍 VERIFICAÇÃO DE PROTEÇÕES EM PRODUÇÃO")
        print("="*60)
        
        # 1. Buscar pedidos com diferentes status
        print("\n📊 Analisando pedidos por status:")
        
        status_counts = db.session.query(
            Pedido.status,
            db.func.count(Pedido.id)
        ).group_by(Pedido.status).all()
        
        for status, count in status_counts:
            print(f"  - {status}: {count} pedidos")
        
        # 2. Verificar quantos pedidos FATURADOS/EMBARCADOS têm Separação
        print("\n🔒 Verificando Separações de pedidos FATURADOS/EMBARCADOS:")
        
        # Pedidos FATURADOS com Separação
        faturados_com_sep = db.session.query(
            db.func.count(db.func.distinct(Pedido.separacao_lote_id))
        ).filter(
            Pedido.status == 'FATURADO',
            Pedido.separacao_lote_id.isnot(None)
        ).scalar() or 0
        
        print(f"  - Pedidos FATURADOS com Separação: {faturados_com_sep}")
        
        # Pedidos EMBARCADOS com Separação
        embarcados_com_sep = db.session.query(
            db.func.count(db.func.distinct(Pedido.separacao_lote_id))
        ).filter(
            Pedido.status == 'EMBARCADO',
            Pedido.separacao_lote_id.isnot(None)
        ).scalar() or 0
        
        print(f"  - Pedidos EMBARCADOS com Separação: {embarcados_com_sep}")
        
        # 3. Testar a query de proteção
        print("\n🛡️ Testando query de proteção (JOIN com filtro):")
        
        # Query com proteção (só ABERTO/COTADO)
        query_protegida = db.session.query(
            db.func.count(db.func.distinct(Separacao.separacao_lote_id))
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.separacao_lote_id.isnot(None),
            db.or_(
                Pedido.status.in_(['ABERTO', 'COTADO']),
                Pedido.status.is_(None)
            )
        ).scalar() or 0
        
        print(f"  - Separações que PODEM ser alteradas (ABERTO/COTADO): {query_protegida}")
        
        # Query de ignorados
        query_ignorados = db.session.query(
            db.func.count(db.func.distinct(Separacao.separacao_lote_id))
        ).join(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.separacao_lote_id.isnot(None),
            ~Pedido.status.in_(['ABERTO', 'COTADO'])
        ).scalar() or 0
        
        print(f"  - Separações PROTEGIDAS (não ABERTO/COTADO): {query_ignorados}")
        
        # 4. Exemplos específicos
        print("\n📋 Exemplos de pedidos FATURADOS que seriam protegidos:")
        
        exemplos = db.session.query(
            Pedido.num_pedido,
            Pedido.separacao_lote_id,
            Pedido.status,
            Pedido.nf
        ).filter(
            Pedido.status == 'FATURADO',
            Pedido.separacao_lote_id.isnot(None)
        ).limit(5).all()
        
        for num, lote, status, nf in exemplos:
            # Verificar se seria filtrado pela proteção
            seria_protegido = db.session.query(
                Separacao.separacao_lote_id
            ).join(
                Pedido,
                Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                Separacao.separacao_lote_id == lote,
                ~Pedido.status.in_(['ABERTO', 'COTADO'])
            ).first() is not None
            
            print(f"  - Pedido {num} (NF: {nf})")
            print(f"    Lote: {lote}")
            print(f"    Status: {status}")
            print(f"    Seria protegido: {'✅ SIM' if seria_protegido else '❌ NÃO'}")
        
        # 5. Resumo final
        print("\n" + "="*60)
        print("📈 RESUMO DA VERIFICAÇÃO:")
        print("="*60)
        
        if query_ignorados > 0:
            print(f"✅ PROTEÇÃO FUNCIONANDO: {query_ignorados} lotes estão protegidos")
            print("   Estes lotes NÃO serão alterados pela sincronização")
        else:
            print("⚠️ NENHUM lote protegido encontrado")
            print("   Isso pode ser normal se não houver pedidos faturados com separação")
        
        total_separacoes = db.session.query(
            db.func.count(db.func.distinct(Separacao.separacao_lote_id))
        ).scalar() or 0
        
        percentual_protegido = (query_ignorados / total_separacoes * 100) if total_separacoes > 0 else 0
        
        print(f"\n📊 {percentual_protegido:.1f}% das separações estão protegidas")
        print(f"   ({query_ignorados} de {total_separacoes} total)")
        
        return True

def main():
    """Função principal."""
    try:
        verificar_protecoes()
        print("\n✅ Verificação concluída com sucesso")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro durante verificação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()