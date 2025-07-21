#!/usr/bin/env python3
"""
ANÁLISE DE PRÉ-SEPARAÇÕES EXISTENTES
Verifica dados atuais antes da implementação das mudanças
"""

import os
import sys
from datetime import datetime

def analisar_pre_separacoes_existentes():
    """Analisa estado atual das pré-separações"""
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import create_app, db
        from app.carteira.models import PreSeparacaoItem, CarteiraPrincipal
        
        try:
            from app.separacao.models import Separacao
        except ImportError:
            Separacao = None
        
        app = create_app()
        
        with app.app_context():
            # Import sqlalchemy functions inside app context
            from sqlalchemy import text, func
            
            print("🔍 ANÁLISE DE PRÉ-SEPARAÇÕES EXISTENTES")
            print("=" * 60)
            print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print()
            
            # 1. Análise geral de pré-separações
            total_pre_sep = PreSeparacaoItem.query.count()
            print(f"📊 Total de pré-separações: {total_pre_sep}")
            
            if total_pre_sep == 0:
                print("✅ Nenhuma pré-separação existente - implementação limpa")
                return True
            
            # 2. Análise do campo data_expedicao_editada
            sem_data_expedicao = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.data_expedicao_editada.is_(None)
            ).count()
            
            com_data_expedicao = total_pre_sep - sem_data_expedicao
            
            print(f"📋 Pré-separações COM data expedição: {com_data_expedicao}")
            print(f"⚠️  Pré-separações SEM data expedição: {sem_data_expedicao}")
            
            if sem_data_expedicao > 0:
                print("\n🔍 REGISTROS SEM DATA DE EXPEDIÇÃO:")
                registros_sem_data = PreSeparacaoItem.query.filter(
                    PreSeparacaoItem.data_expedicao_editada.is_(None)
                ).limit(10).all()
                
                for registro in registros_sem_data:
                    print(f"  ID: {registro.id} | Pedido: {registro.num_pedido} | "
                          f"Produto: {registro.cod_produto} | Status: {registro.status}")
            
            # 3. Análise de possíveis duplicatas na nova constraint
            print(f"\n🔍 ANÁLISE DE CONSTRAINT ÚNICA FUTURA:")
            print("Verificando possíveis conflitos...")
            
            # Query para detectar duplicatas na constraint futura
            duplicatas = db.session.query(
                PreSeparacaoItem.num_pedido,
                PreSeparacaoItem.cod_produto,
                func.coalesce(PreSeparacaoItem.data_expedicao_editada, '1900-01-01'),
                func.coalesce(PreSeparacaoItem.data_agendamento_editada, '1900-01-01'), 
                func.coalesce(PreSeparacaoItem.protocolo_editado, 'SEM_PROTOCOLO'),
                func.count(PreSeparacaoItem.id).label('total')
            ).group_by(
                PreSeparacaoItem.num_pedido,
                PreSeparacaoItem.cod_produto,
                func.coalesce(PreSeparacaoItem.data_expedicao_editada, '1900-01-01'),
                func.coalesce(PreSeparacaoItem.data_agendamento_editada, '1900-01-01'),
                func.coalesce(PreSeparacaoItem.protocolo_editado, 'SEM_PROTOCOLO')
            ).having(func.count(PreSeparacaoItem.id) > 1).all()
            
            if duplicatas:
                print(f"⚠️  Encontradas {len(duplicatas)} combinações duplicadas:")
                for dup in duplicatas[:5]:  # Mostrar apenas 5 primeiras
                    print(f"  Pedido: {dup[0]} | Produto: {dup[1]} | Duplicatas: {dup[5]}")
            else:
                print("✅ Nenhuma duplicata encontrada para constraint única")
            
            # 4. Análise de status
            print(f"\n📊 ANÁLISE POR STATUS:")
            status_count = db.session.query(
                PreSeparacaoItem.status,
                func.count(PreSeparacaoItem.id).label('total')
            ).group_by(PreSeparacaoItem.status).all()
            
            for status, count in status_count:
                print(f"  {status}: {count}")
            
            # 5. Análise de tipo_envio
            print(f"\n📦 ANÁLISE POR TIPO_ENVIO:")
            tipo_count = db.session.query(
                PreSeparacaoItem.tipo_envio,
                func.count(PreSeparacaoItem.id).label('total')
            ).group_by(PreSeparacaoItem.tipo_envio).all()
            
            for tipo, count in tipo_count:
                print(f"  {tipo or 'NULL'}: {count}")
            
            # 6. Análise de pedidos com múltiplas pré-separações
            print(f"\n🔍 ANÁLISE DE PEDIDOS COM MÚLTIPLAS PRÉ-SEPARAÇÕES:")
            pedidos_multiplos = db.session.query(
                PreSeparacaoItem.num_pedido,
                func.count(PreSeparacaoItem.id).label('total')
            ).group_by(PreSeparacaoItem.num_pedido).having(
                func.count(PreSeparacaoItem.id) > 1
            ).limit(10).all()
            
            if pedidos_multiplos:
                print(f"  Encontrados {len(pedidos_multiplos)} pedidos com múltiplas pré-separações:")
                for pedido, count in pedidos_multiplos:
                    print(f"    Pedido: {pedido} - {count} pré-separações")
            else:
                print("  Nenhum pedido com múltiplas pré-separações")
            
            # 7. Recomendações
            print(f"\n💡 RECOMENDAÇÕES PARA IMPLEMENTAÇÃO:")
            
            if sem_data_expedicao > 0:
                print(f"  ⚠️  AÇÃO NECESSÁRIA: {sem_data_expedicao} registros precisam de data_expedicao")
                print(f"     Opções: 1) Definir data padrão, 2) Remover registros incompletos")
            
            if duplicatas:
                print(f"  ⚠️  AÇÃO NECESSÁRIA: Consolidar {len(duplicatas)} grupos duplicados")
            
            if not duplicatas and sem_data_expedicao == 0:
                print(f"  ✅ DADOS PRONTOS: Pode prosseguir com implementação")
            
            print(f"\n📋 RESUMO:")
            print(f"  Total de registros: {total_pre_sep}")
            print(f"  Registros válidos: {com_data_expedicao}")
            print(f"  Necessitam correção: {sem_data_expedicao}")
            print(f"  Duplicatas encontradas: {len(duplicatas) if duplicatas else 0}")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analisar_pre_separacoes_existentes()