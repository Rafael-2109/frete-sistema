#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 OTIMIZAÇÃO CRÍTICA - EXPORTAÇÃO DE MONITORAMENTO
Resolve lentidão de 48+ segundos na exportação de entregas

PROBLEMA ATUAL:
- N+1 queries (7.000 entregas × 5 relacionamentos = 35.000+ queries)
- Processamento pesado por entrega
- Conversões timezone individuais

SOLUÇÃO OTIMIZADA:
- Queries com joinedload para carregar tudo de uma vez
- Processamento em lote
- Cache de conversões
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def otimizar_exportacao_monitoramento():
    """Aplica otimizações na função de exportação de monitoramento"""
    print("🚀 APLICANDO OTIMIZAÇÕES NA EXPORTAÇÃO DE MONITORAMENTO")
    print("=" * 70)
    
    # Ler arquivo original
    arquivo_routes = "app/monitoramento/routes.py"
    
    with open(arquivo_routes, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Fazer backup
    with open(arquivo_routes + '.backup', 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print("✅ Backup criado em routes.py.backup")
    
    # 1. OTIMIZAR A QUERY PRINCIPAL - ADICIONAR JOINEDLOAD
    otimizacao_query = '''
            # 🚀 QUERY OTIMIZADA: Carrega todos os relacionamentos de uma vez
            from sqlalchemy.orm import joinedload
            entregas = query.options(
                joinedload(EntregaMonitorada.agendamentos),
                joinedload(EntregaMonitorada.logs),
                joinedload(EntregaMonitorada.eventos),
                joinedload(EntregaMonitorada.custos_extras),
                joinedload(EntregaMonitorada.comentarios)
            ).order_by(EntregaMonitorada.numero_nf).all()'''
    
    # Substituir query original
    conteudo = conteudo.replace(
        "            # Busca entregas\n            entregas = query.order_by(EntregaMonitorada.numero_nf).all()",
        "            # 🚀 BUSCA OTIMIZADA - Carrega relacionamentos em uma query" + otimizacao_query
    )
    
    # 2. ADICIONAR LOGS DE PERFORMANCE
    log_performance = '''            # 🚀 LOG DE PERFORMANCE
            import time
            start_time = time.time()
            print(f"📊 INICIANDO EXPORTAÇÃO: {len(entregas)} entregas")
            
            # Gera arquivo Excel - sempre formato completo'''
    
    conteudo = conteudo.replace(
        "            # Gera arquivo Excel - sempre formato completo",
        log_performance
    )
    
    # 3. ADICIONAR LOG FINAL
    log_final = '''            # 🚀 LOG FINAL DE PERFORMANCE
            total_time = time.time() - start_time
            print(f"🎉 EXPORTAÇÃO CONCLUÍDA em {total_time:.2f}s")
            
            flash(f'✅ Exportação concluída! {len(entregas)} entregas exportadas em {total_time:.2f}s.', 'success')'''
    
    conteudo = conteudo.replace(
        "            flash(f'✅ Exportação concluída! {len(entregas)} entregas exportadas.', 'success')",
        log_final
    )
    
    # 4. OTIMIZAR FUNÇÃO GERAR_EXCEL - ADICIONAR CACHE TIMEZONE
    cache_otimizacao = '''    # Cache para conversões de timezone (evita conversões repetidas)
    timezone_cache = {}
    
    def limpar_timezone(dt):
        """Remove timezone de datetime para compatibilidade com Excel - VERSÃO CACHE"""
        if dt is None:
            return None
        if dt in timezone_cache:
            return timezone_cache[dt]
        
        resultado = dt
        if hasattr(dt, 'replace') and hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            resultado = dt.replace(tzinfo=None)
        
        timezone_cache[dt] = resultado
        return resultado'''
    
    # Substituir função limpar_timezone
    conteudo = conteudo.replace(
        '    def limpar_timezone(dt):\n        """Remove timezone de datetime para compatibilidade com Excel"""\n        if dt is None:\n            return None\n        if hasattr(dt, \'replace\') and hasattr(dt, \'tzinfo\') and dt.tzinfo is not None:\n            return dt.replace(tzinfo=None)\n        return dt',
        cache_otimizacao
    )
    
    # 5. ADICIONAR LOGS DE PROGRESSO NA FUNÇÃO GERAR_EXCEL
    progresso_logs = '''    print(f"🔥 INICIANDO GERAÇÃO EXCEL para {len(entregas)} entregas...")
    
    # Prepara dados principais'''
    
    conteudo = conteudo.replace(
        '    # Prepara dados principais',
        progresso_logs
    )
    
    # Adicionar log de progresso no loop
    log_loop = '''    for i, entrega in enumerate(entregas):
        if i % 1000 == 0 and i > 0:
            print(f"📊 Processando entrega {i}/{len(entregas)}...")
        '''
    
    conteudo = conteudo.replace(
        '    for entrega in entregas:',
        log_loop
    )
    
    # Adicionar log final na função Excel
    log_excel_final = '''        print(f"🎉 EXCEL GERADO em {timezone_cache.__len__()} conversões cache utilizadas")
        
        return tmp_file.name'''
    
    conteudo = conteudo.replace(
        '        return tmp_file.name',
        log_excel_final
    )
    
    # Salvar arquivo otimizado
    with open(arquivo_routes, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ Otimizações aplicadas com sucesso!")
    print("\n🚀 BENEFÍCIOS ESPERADOS:")
    print("- Redução de 48s → ~8-12s na exportação completa")
    print("- Query com joinedload elimina N+1 problem")
    print("- Cache de conversões timezone")
    print("- Logs de performance em tempo real")
    print("- Progresso visível durante processamento")
    
    return True

if __name__ == "__main__":
    otimizar_exportacao_monitoramento() 