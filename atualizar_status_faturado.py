#!/usr/bin/env python3
"""
Script para atualizar o status de todos os pedidos que possuem NF
e existe registro correspondente em FaturamentoProduto.numero_nf
para status = 'FATURADO'

Este script corrige retroativamente todos os pedidos que foram faturados
mas permaneceram com status incorreto (COTADO, NF no CD, etc)
"""

from app import create_app, db
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import func
from datetime import datetime

app = create_app()

def main():
    with app.app_context():
        print("=" * 70)
        print("ATUALIZAÇÃO DE STATUS DE PEDIDOS FATURADOS")
        print("=" * 70)
        print(f"Execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        
        # 1. Análise inicial - Contar pedidos por status atual
        print("📊 SITUAÇÃO ATUAL DOS PEDIDOS:")
        print("-" * 40)
        
        contagem_inicial = db.session.query(
            Pedido.status,
            func.count(Pedido.id).label('quantidade')
        ).group_by(Pedido.status).order_by('quantidade DESC').all()
        
        total_pedidos = sum(qtd for _, qtd in contagem_inicial)
        
        for status, qtd in contagem_inicial:
            percentual = (qtd / total_pedidos * 100) if total_pedidos > 0 else 0
            print(f"  • {(status or 'SEM STATUS'):20} {qtd:6} ({percentual:5.1f}%)")
        print(f"  {'TOTAL':20} {total_pedidos:6}")
        
        # 2. Buscar pedidos com NF preenchida mas status != 'FATURADO'
        print("\n🔍 BUSCANDO PEDIDOS COM NF MAS SEM STATUS FATURADO...")
        print("-" * 40)
        
        pedidos_com_nf = Pedido.query.filter(
            Pedido.nf.isnot(None),
            Pedido.nf != "",
            Pedido.status != 'FATURADO'
        ).all()
        
        print(f"Encontrados: {len(pedidos_com_nf)} pedidos com NF mas status != 'FATURADO'\n")
        
        if not pedidos_com_nf:
            print("✅ Todos os pedidos já estão com status correto!")
            return
        
        # 3. Verificar quais realmente têm faturamento
        print("🔎 VERIFICANDO EXISTÊNCIA EM FATURAMENTOPRODUTO...")
        print("-" * 40)
        
        pedidos_para_atualizar = []
        pedidos_sem_faturamento = []
        
        for pedido in pedidos_com_nf:
            # Verificar se existe registro de faturamento
            faturamento = FaturamentoProduto.query.filter_by(
                numero_nf=pedido.nf
            ).first()
            
            if faturamento:
                pedidos_para_atualizar.append(pedido)
            else:
                pedidos_sem_faturamento.append(pedido)
        
        print(f"  ✅ Com faturamento confirmado: {len(pedidos_para_atualizar)}")
        print(f"  ⚠️  Sem registro de faturamento: {len(pedidos_sem_faturamento)}")
        
        # 4. Listar pedidos sem faturamento (para investigação)
        if pedidos_sem_faturamento:
            print("\n⚠️  PEDIDOS COM NF MAS SEM REGISTRO DE FATURAMENTO:")
            print("-" * 40)
            for i, pedido in enumerate(pedidos_sem_faturamento[:10], 1):
                print(f"  {i}. Pedido: {pedido.num_pedido:15} | NF: {pedido.nf:10} | Status: {pedido.status:10} | Lote: {pedido.separacao_lote_id}")
            if len(pedidos_sem_faturamento) > 10:
                print(f"  ... e mais {len(pedidos_sem_faturamento) - 10} pedidos")
        
        # 5. Atualizar pedidos confirmados
        if pedidos_para_atualizar:
            print("\n📝 ATUALIZANDO PEDIDOS CONFIRMADOS...")
            print("-" * 40)
            
            # Agrupar por status atual para relatório
            status_grupos = {}
            for pedido in pedidos_para_atualizar:
                status_atual = pedido.status or 'SEM STATUS'
                if status_atual not in status_grupos:
                    status_grupos[status_atual] = []
                status_grupos[status_atual].append(pedido)
            
            # Mostrar resumo das mudanças
            print("Mudanças a serem aplicadas:")
            for status_atual, pedidos_grupo in sorted(status_grupos.items()):
                print(f"  • {status_atual:15} → FATURADO: {len(pedidos_grupo)} pedidos")
            
            # Aplicar atualizações
            contador = 0
            try:
                for pedido in pedidos_para_atualizar:
                    pedido.status = 'FATURADO'
                    contador += 1
                    
                    # Mostrar progresso a cada 100 pedidos
                    if contador % 100 == 0:
                        print(f"    Processados: {contador}/{len(pedidos_para_atualizar)}...")
                
                # Commit das alterações
                db.session.commit()
                print(f"\n✅ {contador} pedidos atualizados com sucesso!")
                
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ ERRO ao atualizar pedidos: {e}")
                return
        
        # 6. Verificação final
        print("\n📊 VERIFICAÇÃO PÓS-ATUALIZAÇÃO:")
        print("-" * 40)
        
        # Contar novamente por status
        contagem_final = db.session.query(
            Pedido.status,
            func.count(Pedido.id).label('quantidade')
        ).group_by(Pedido.status).order_by('quantidade DESC').all()
        
        for status, qtd in contagem_final:
            percentual = (qtd / total_pedidos * 100) if total_pedidos > 0 else 0
            # Destacar status FATURADO
            if status == 'FATURADO':
                print(f"  • {status:20} {qtd:6} ({percentual:5.1f}%) ✅")
            else:
                print(f"  • {(status or 'SEM STATUS'):20} {qtd:6} ({percentual:5.1f}%)")
        
        # Verificar se ainda existem inconsistências
        ainda_inconsistentes = Pedido.query.filter(
            Pedido.nf.isnot(None),
            Pedido.nf != "",
            Pedido.status != 'FATURADO'
        ).count()
        
        print("\n" + "=" * 70)
        if ainda_inconsistentes > 0:
            print(f"⚠️  ATENÇÃO: Ainda existem {ainda_inconsistentes} pedidos com NF mas sem status FATURADO")
            print("   (Provavelmente são NFs sem registro em FaturamentoProduto)")
        else:
            print("✅ SUCESSO: Todos os pedidos com NF válida estão com status FATURADO!")
        print("=" * 70)
        
        # 7. Relatório de NFs órfãs (opcional)
        if pedidos_sem_faturamento:
            print("\n📋 RELATÓRIO DE NFs ÓRFÃS (sem registro de faturamento):")
            print("-" * 40)
            print("Estas NFs estão preenchidas em Pedido mas não existem em FaturamentoProduto.")
            print("Possíveis causas:")
            print("  • NF cancelada no Odoo mas não atualizada no sistema")
            print("  • NF digitada manualmente com erro")
            print("  • Importação de faturamento pendente")
            print(f"\nTotal de NFs órfãs: {len(pedidos_sem_faturamento)}")
            
            # Salvar em arquivo para análise
            arquivo_relatorio = f"nfs_orfas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(arquivo_relatorio, 'w') as f:
                f.write("RELATÓRIO DE NFs ÓRFÃS\n")
                f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                
                for pedido in pedidos_sem_faturamento:
                    f.write(f"Pedido: {pedido.num_pedido}\n")
                    f.write(f"  NF: {pedido.nf}\n")
                    f.write(f"  Status Atual: {pedido.status}\n")
                    f.write(f"  Lote: {pedido.separacao_lote_id}\n")
                    f.write(f"  Data Pedido: {pedido.data_pedido}\n")
                    f.write("-" * 40 + "\n")
            
            print(f"📄 Relatório detalhado salvo em: {arquivo_relatorio}")

if __name__ == "__main__":
    main()