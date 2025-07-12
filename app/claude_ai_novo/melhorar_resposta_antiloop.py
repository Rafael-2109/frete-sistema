#!/usr/bin/env python3
"""
🔧 MELHORAR RESPOSTA ANTI-LOOP
==============================

Melhora a resposta quando o sistema detecta e previne um loop,
fornecendo respostas mais úteis baseadas na análise da query.
"""

import os
import shutil
from datetime import datetime

def melhorar_resposta_antiloop():
    """Melhora a resposta quando o loop é detectado"""
    
    print("🔧 Melhorando resposta anti-loop...")
    
    # Melhorar integration_manager.py
    integration_file = "app/claude_ai_novo/integration/integration_manager.py"
    
    if os.path.exists(integration_file):
        # Backup
        backup_file = f"{integration_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(integration_file, backup_file)
        print(f"✅ Backup criado: {backup_file}")
        
        with open(integration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substituir a resposta genérica por uma mais inteligente
        old_response = '''logger.warning("⚠️ Detectado possível loop - retornando resposta direta")
            return {
                "success": True,
                "response": f"Processamento direto: {query}",
                "query": query,
                "source": "integration_direct",
                "loop_prevented": True
            }'''
        
        new_response = '''logger.warning("⚠️ Detectado possível loop - retornando resposta direta")
            
            # Analisar a query para fornecer resposta mais útil
            query_lower = query.lower() if query else ""
            
            # Respostas específicas baseadas no tipo de consulta
            if "entregas" in query_lower and "atacadão" in query_lower:
                response = """📦 Status das Entregas - Atacadão:
                
Para obter informações detalhadas sobre as entregas do Atacadão, você pode:
1. Acessar o relatório de entregas no menu principal
2. Filtrar por data, status ou número do pedido
3. Visualizar o tracking em tempo real

💡 Dica: Use comandos como "listar entregas atacadão hoje" ou "status entrega 12345" para consultas específicas."""
            
            elif "entregas" in query_lower:
                response = """📦 Informações sobre Entregas:
                
Para consultar entregas, especifique:
- Cliente: "entregas do [nome do cliente]"
- Data: "entregas de hoje/ontem/esta semana"
- Status: "entregas pendentes/em rota/entregues"

💡 Exemplo: "mostrar entregas pendentes de hoje" """
            
            elif "frete" in query_lower or "fretes" in query_lower:
                response = """🚚 Informações sobre Fretes:
                
Comandos disponíveis para fretes:
- "calcular frete para [destino]"
- "listar fretes do mês"
- "status frete [número]"
- "fretes pendentes"

💡 Use filtros para refinar sua busca!"""
            
            elif "pedido" in query_lower or "pedidos" in query_lower:
                response = """📋 Informações sobre Pedidos:
                
Para consultar pedidos:
- "pedidos de hoje"
- "pedido número [12345]"
- "pedidos pendentes"
- "pedidos do cliente [nome]"

💡 Você também pode exportar relatórios!"""
            
            elif "relatorio" in query_lower or "relatório" in query_lower:
                response = """📊 Geração de Relatórios:
                
Relatórios disponíveis:
- Relatório de entregas
- Relatório de faturamento
- Relatório de performance
- Relatório customizado

💡 Especifique o período: "relatório de entregas desta semana" """
            
            elif "ajuda" in query_lower or "help" in query_lower or "comando" in query_lower:
                response = """❓ Central de Ajuda - Comandos Disponíveis:
                
📦 Entregas: "listar entregas", "status entrega [id]"
🚚 Fretes: "calcular frete", "fretes pendentes"
📋 Pedidos: "pedidos hoje", "pedido [número]"
📊 Relatórios: "relatório entregas", "exportar dados"
👥 Clientes: "dados cliente [nome]", "histórico [cliente]"

💡 Seja específico para melhores resultados!"""
            
            else:
                response = f"""🤖 Processando: '{query}'
                
Não consegui identificar exatamente o que você precisa. Tente ser mais específico:

📦 Para entregas: "listar entregas de hoje"
🚚 Para fretes: "calcular frete para São Paulo"
📋 Para pedidos: "mostrar pedido 12345"
📊 Para relatórios: "relatório de faturamento"

💡 Digite "ajuda" para ver todos os comandos disponíveis."""
            
            return {
                "success": True,
                "response": response,
                "query": query,
                "source": "integration_antiloop",
                "loop_prevented": True,
                "response_type": "intelligent_fallback"
            }'''
        
        # Substituir no arquivo
        content = content.replace(old_response, new_response)
        
        # Salvar arquivo
        with open(integration_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Arquivo {integration_file} atualizado com respostas inteligentes")
    
    print("\n🎉 Resposta anti-loop melhorada!")
    print("\nAgora quando o sistema detectar um loop, fornecerá:")
    print("- Respostas específicas baseadas no contexto")
    print("- Sugestões de comandos úteis")
    print("- Orientações para o usuário")

if __name__ == "__main__":
    melhorar_resposta_antiloop() 