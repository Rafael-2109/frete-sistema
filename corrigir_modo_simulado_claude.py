#!/usr/bin/env python
"""
🔧 Script para corrigir o modo simulado do Claude AI
Permite consultas de dados reais mesmo sem API key da Anthropic
"""

import os
import sys
import shutil
from datetime import datetime

def fazer_backup():
    """Faz backup do arquivo original"""
    arquivo_original = "app/claude_ai/claude_real_integration.py"
    arquivo_backup = f"app/claude_ai/claude_real_integration.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if os.path.exists(arquivo_original):
        shutil.copy2(arquivo_original, arquivo_backup)
        print(f"✅ Backup criado: {arquivo_backup}")
        return True
    else:
        print(f"❌ Arquivo não encontrado: {arquivo_original}")
        return False

def aplicar_correcao():
    """Aplica correção para permitir dados reais sem API key"""
    
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # 1. Modificar _fallback_simulado para ser mais transparente
        novo_fallback = '''    def _fallback_simulado(self, consulta: str) -> str:
        """Fallback quando Claude real não está disponível - MELHORADO COM DADOS REAIS"""
        
        # 🎯 PROCESSAR CONSULTAS BÁSICAS COM DADOS REAIS
        consulta_lower = consulta.lower()
        
        # Detectar tipo de consulta
        eh_status = any(termo in consulta_lower for termo in ['status', 'sistema', 'estatística'])
        eh_faturamento = any(termo in consulta_lower for termo in ['faturamento', 'faturou', 'quanto', 'valor'])
        eh_cliente = any(termo in consulta_lower for termo in ['cliente', 'clientes', 'empresa'])
        eh_entrega = any(termo in consulta_lower for termo in ['entrega', 'entregas', 'pendente'])
        
        if eh_status or eh_faturamento or eh_cliente or eh_entrega:
            try:
                # Analisar consulta
                contexto_analisado = self._analisar_consulta(consulta)
                
                # Carregar dados reais
                dados_reais = self._carregar_contexto_inteligente(contexto_analisado)
                
                # Formatar resposta baseada em dados reais
                return self._formatar_resposta_dados_reais_simulado(consulta, contexto_analisado, dados_reais)
                
            except Exception as e:
                logger.error(f"Erro ao processar dados reais no modo simulado: {e}")
        
        # Fallback genérico melhorado
        return f"""⚠️ **MODO SIMULADO - DADOS LIMITADOS**

Sua consulta: "{consulta}"

⚠️ **ATENÇÃO**: O sistema está operando sem conexão com Claude AI real.
Algumas funcionalidades avançadas estão limitadas.

💡 **Para ativar o modo completo**:
1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente
2. Entre em contato com o administrador

🔧 **Funcionalidades disponíveis no modo simulado**:
- Consultas de status do sistema
- Dados de faturamento básico
- Listagem de clientes e entregas
- Estatísticas gerais

📊 **Para consultas específicas**, tente:
- "Qual o status do sistema?"
- "Quanto faturou hoje?"
- "Quantos clientes existem?"
- "Mostre entregas pendentes"

---
⚡ Modo: Simulado com Dados Reais Básicos"""'''

        # 2. Adicionar método para formatar resposta com dados reais
        novo_metodo = '''
    def _formatar_resposta_dados_reais_simulado(self, consulta: str, contexto: Dict[str, Any], dados: Dict[str, Any]) -> str:
        """Formata resposta com dados reais no modo simulado"""
        
        resposta = f"""🤖 **SISTEMA DE FRETES - MODO DADOS REAIS**

📊 **RESPOSTA PARA**: "{consulta}"

"""
        
        # Status do sistema
        if "status" in consulta.lower():
            total_registros = dados.get('registros_carregados', 0)
            dados_especificos = dados.get('dados_especificos', {})
            
            resposta += f"""🔧 **STATUS DO SISTEMA**

📊 **ESTATÍSTICAS GERAIS** (Últimos {contexto.get('periodo_dias', 30)} dias):
• Total de registros processados: {total_registros}
• Módulos ativos: {len(dados_especificos)} domínios
• Última atualização: {dados.get('timestamp', 'N/A')}
"""
            
            # Dados de entregas se disponível
            if 'entregas' in dados_especificos:
                entregas_data = dados_especificos['entregas']
                total_entregas = entregas_data.get('total_registros', 0)
                
                if entregas_data.get('metricas'):
                    metricas = entregas_data['metricas']
                    resposta += f"""
📦 **ENTREGAS**:
• Total de entregas: {total_entregas}
• Entregas realizadas: {metricas.get('entregas_realizadas', 0)}
• Entregas pendentes: {total_entregas - metricas.get('entregas_realizadas', 0)}
• Performance no prazo: {metricas.get('percentual_no_prazo', 0)}%
"""
            
            # Dados de faturamento se disponível
            if 'faturamento' in dados_especificos:
                faturamento_data = dados_especificos['faturamento']
                if 'faturamento' in faturamento_data:
                    stats = faturamento_data['faturamento'].get('estatisticas', {})
                    resposta += f"""
💰 **FATURAMENTO**:
• Total de faturas: {stats.get('total_faturas', 0)}
• Valor total: R$ {stats.get('valor_total', 0):,.2f}
• Valor hoje: R$ {stats.get('valor_hoje', 0):,.2f}
"""
        
        # Faturamento específico
        elif "faturamento" in consulta.lower() or "faturou" in consulta.lower():
            if 'faturamento' in dados.get('dados_especificos', {}):
                faturamento_data = dados['dados_especificos']['faturamento']
                if 'faturamento' in faturamento_data:
                    stats = faturamento_data['faturamento'].get('estatisticas', {})
                    
                    if "hoje" in consulta.lower():
                        resposta += f"""💰 **FATURAMENTO HOJE**:
• Total de NFs: {stats.get('faturas_hoje', 0)}
• Valor total: R$ {stats.get('valor_hoje', 0):,.2f}
"""
                    else:
                        resposta += f"""💰 **FATURAMENTO** (Últimos {contexto.get('periodo_dias', 30)} dias):
• Total de faturas: {stats.get('total_faturas', 0)}
• Valor total: R$ {stats.get('valor_total', 0):,.2f}
• Média diária: R$ {stats.get('valor_total', 0) / contexto.get('periodo_dias', 30):,.2f}
"""
        
        # Clientes
        elif "cliente" in consulta.lower():
            # Buscar lista real de clientes dos dados
            clientes_unicos = set()
            
            for dominio, dados_dominio in dados.get('dados_especificos', {}).items():
                if isinstance(dados_dominio, dict) and 'registros' in dados_dominio:
                    for registro in dados_dominio['registros']:
                        if isinstance(registro, dict):
                            cliente = registro.get('cliente') or registro.get('nome_cliente')
                            if cliente:
                                clientes_unicos.add(cliente)
            
            resposta += f"""🏢 **CLIENTES DO SISTEMA**:
• Total de clientes únicos: {len(clientes_unicos)}

**Alguns clientes encontrados**:
"""
            for i, cliente in enumerate(list(clientes_unicos)[:10], 1):
                resposta += f"{i}. {cliente}\\n"
            
            if len(clientes_unicos) > 10:
                resposta += f"\\n... e mais {len(clientes_unicos) - 10} clientes"
        
        resposta += f"""

---
⚠️ **Modo**: Dados Reais (Simulado - sem IA avançada)
📊 **Fonte**: Banco de dados PostgreSQL
🕒 **Processado**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
💡 **Dica**: Configure ANTHROPIC_API_KEY para análises avançadas com IA"""
        
        return resposta'''

        # Localizar onde inserir o novo método (após _fallback_simulado)
        pos_fallback = conteudo.find('def _fallback_simulado(self, consulta: str) -> str:')
        if pos_fallback == -1:
            print("❌ Não encontrou método _fallback_simulado")
            return False
        
        # Encontrar o final do método _fallback_simulado
        pos_fim_fallback = conteudo.find('\n\n    def ', pos_fallback + 1)
        if pos_fim_fallback == -1:
            # Se não encontrar outro método, procurar pelo final da classe
            pos_fim_fallback = len(conteudo)
        
        # Substituir o método _fallback_simulado
        inicio_metodo = pos_fallback
        fim_metodo = conteudo.find('🔄 **Por enquanto, usando sistema básico...**"""', pos_fallback)
        if fim_metodo != -1:
            fim_metodo = conteudo.find('\n', fim_metodo) + 1
            
            # Substituir método antigo pelo novo
            conteudo_novo = (
                conteudo[:inicio_metodo] + 
                novo_fallback + 
                novo_metodo +
                conteudo[fim_metodo:]
            )
        else:
            print("❌ Não conseguiu identificar final do método _fallback_simulado")
            return False
        
        # Salvar arquivo modificado
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo_novo)
        
        print("✅ Correção aplicada com sucesso!")
        print("📊 Agora o sistema consultará dados reais mesmo sem API key para:")
        print("   - Status do sistema")
        print("   - Faturamento")
        print("   - Listagem de clientes")
        print("   - Entregas pendentes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar correção: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🔧 CORREÇÃO DO MODO SIMULADO DO CLAUDE AI")
    print("=" * 50)
    print("Este script permite consultas de dados reais")
    print("mesmo quando a API key da Anthropic não está configurada")
    print("=" * 50)
    
    # Fazer backup
    if not fazer_backup():
        print("❌ Falha ao criar backup. Abortando...")
        return
    
    # Aplicar correção
    if aplicar_correcao():
        print("\n✅ CORREÇÃO APLICADA COM SUCESSO!")
        print("\n🎯 Próximos passos:")
        print("1. Reinicie o servidor Flask")
        print("2. Teste com: 'Qual o status do sistema?'")
        print("3. O sistema agora mostrará dados reais!")
        
        print("\n💡 Para reverter:")
        print("   Restaure o backup criado")
    else:
        print("\n❌ Falha ao aplicar correção")

if __name__ == "__main__":
    main() 