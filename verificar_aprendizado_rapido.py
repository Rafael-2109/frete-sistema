#!/usr/bin/env python3
"""
🔍 VERIFICAÇÃO RÁPIDA DO APRENDIZADO
Script simples para ver se precisa de manutenção
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime

def verificacao_rapida():
    """Verificação rápida de 1 minuto"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 VERIFICAÇÃO RÁPIDA DO APRENDIZADO")
        print("=" * 50)
        
        # 1. Taxa de erro recente
        erros = db.session.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN tipo_correcao IS NOT NULL THEN 1 ELSE 0 END) as erros
            FROM ai_learning_history
            WHERE created_at > CURRENT_DATE - INTERVAL '7 days'
        """)).first()
        
        if erros.total > 0:
            taxa_erro = (erros.erros / erros.total) * 100
            print(f"\n📊 Taxa de Erro (última semana): {taxa_erro:.1f}%")
            
            if taxa_erro > 30:
                print("   ⚠️  ALTA - Recomenda-se manutenção!")
            elif taxa_erro > 15:
                print("   🟡 MÉDIA - Monitorar")
            else:
                print("   ✅ BAIXA - Sistema saudável")
        
        # 2. Padrões problemáticos
        problemas = db.session.execute(text("""
            SELECT COUNT(*) as qtd
            FROM ai_knowledge_patterns
            WHERE confidence < 0.3 AND usage_count > 5
        """)).scalar()
        
        print(f"\n🚨 Padrões Problemáticos: {problemas}")
        if problemas > 10:
            print("   ⚠️  Executar: python manutencao_aprendizado.py limpar")
        
        # 3. Grupos não validados
        grupos = db.session.execute(text("""
            SELECT COUNT(*) as qtd
            FROM ai_grupos_empresariais
            WHERE confirmado_por IS NULL
        """)).scalar()
        
        if grupos > 0:
            print(f"\n🏢 Grupos Não Validados: {grupos}")
            print("   💡 Executar: python manutencao_aprendizado.py validar")
        
        # 4. Recomendação
        print("\n" + "=" * 50)
        if taxa_erro > 30 or problemas > 10 or grupos > 0:
            print("🔧 MANUTENÇÃO RECOMENDADA!")
            print("\nPróximos passos:")
            print("1. python manutencao_aprendizado.py saude")
            print("2. python manutencao_aprendizado.py limpar")
            print("3. python manutencao_aprendizado.py consolidar")
        else:
            print("✅ SISTEMA SAUDÁVEL - Sem ação necessária")
        
        print("\n💡 Dica: Execute semanalmente para melhores resultados!")

if __name__ == "__main__":
    verificacao_rapida() 