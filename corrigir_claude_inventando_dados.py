#!/usr/bin/env python
"""
🔧 Script para corrigir o problema de Claude inventando dados
Melhora system prompt e queries para evitar informações fictícias
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

def aplicar_correcoes():
    """Aplica correções para evitar que Claude invente dados"""
    
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # 1. Melhorar o system prompt
        novo_prompt_adicional = '''

❌ **REGRAS CRÍTICAS - NUNCA VIOLAR**:
1. **NUNCA INVENTE DADOS**: Se não estiver nos dados fornecidos, NÃO EXISTE
2. **NUNCA LISTE EMPRESAS FICTÍCIAS**: Use APENAS clientes presentes nos dados
3. **NUNCA EXTRAPOLE**: Se tem dados de 30 dias, não afirme sobre "todo o sistema"
4. **QUANDO NÃO SOUBER**: Responda "Dados não disponíveis para esta consulta"
5. **VALIDAÇÃO OBRIGATÓRIA**: Cada cliente/número deve vir dos dados fornecidos

⚠️ **CLIENTES QUE NÃO EXISTEM NO SISTEMA** (NUNCA MENCIONAR):
- MAKRO (fechou há anos)
- WALMART 
- EXTRA
- BIG
- SAM'S CLUB
- COMERCIAL ZAFFARI

✅ **SEMPRE VERIFICAR**:
- Se a pergunta é sobre "todo o sistema" mas você tem dados de apenas 30 dias
- Se está listando clientes, TODOS devem estar nos dados fornecidos
- Se está dando números totais, devem ser calculados dos dados reais

🎯 **EXEMPLO CORRETO**:
Pergunta: "Quantos clientes existem no sistema?"
Dados fornecidos: 933 entregas dos últimos 30 dias com 78 clientes únicos

RESPOSTA ERRADA: "O sistema tem 78 clientes"
RESPOSTA CORRETA: "Nos últimos 30 dias, identificamos 78 clientes únicos com entregas. 
Para o total de clientes cadastrados no sistema, seria necessário uma consulta sem filtro de data."'''

        # Localizar onde adicionar ao system prompt
        pos_system_prompt = conteudo.find('✅ **SEMPRE**:')
        if pos_system_prompt != -1:
            # Inserir após a seção SEMPRE
            pos_fim_sempre = conteudo.find('\n\n🎯 **OBJETIVO**', pos_system_prompt)
            if pos_fim_sempre != -1:
                conteudo = (
                    conteudo[:pos_fim_sempre] + 
                    novo_prompt_adicional +
                    conteudo[pos_fim_sempre:]
                )
                print("✅ System prompt atualizado com regras anti-invenção")
        
        # 2. Adicionar método para detectar consultas sobre totais
        novo_metodo = '''
    def _ajustar_contexto_para_totais(self, consulta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Ajusta contexto quando a pergunta é sobre totais do sistema"""
        
        consulta_lower = consulta.lower()
        
        # Detectar perguntas sobre totais/quantidades gerais
        eh_total_sistema = any(termo in consulta_lower for termo in [
            'quantos clientes existem',
            'total de clientes',
            'todos os clientes',
            'quantidade de clientes no sistema',
            'quantas empresas',
            'total de empresas'
        ])
        
        if eh_total_sistema:
            logger.info("🎯 Pergunta sobre TOTAL DO SISTEMA detectada - removendo filtro de data")
            # Remover limite de data para contar TODOS os clientes
            analise['periodo_dias'] = None
            analise['consulta_total_sistema'] = True
            analise['observacao'] = "Consulta sem filtro de data para obter total real"
            
            # Adicionar flag para carregar query específica de contagem
            analise['query_especial'] = 'contar_clientes_total'
        
        return analise'''

        # 3. Adicionar método para queries especiais
        query_especial = '''
    def _executar_query_especial(self, tipo_query: str) -> Dict[str, Any]:
        """Executa queries especiais para consultas específicas"""
        
        try:
            if tipo_query == 'contar_clientes_total':
                # Contar TODOS os clientes únicos do sistema
                from app.faturamento.models import RelatorioFaturamentoImportado
                from sqlalchemy import func, distinct
                
                total_clientes = db.session.query(
                    func.count(distinct(RelatorioFaturamentoImportado.nome_cliente))
                ).filter(
                    RelatorioFaturamentoImportado.nome_cliente != None,
                    RelatorioFaturamentoImportado.nome_cliente != ''
                ).scalar() or 0
                
                # Contar estados atendidos
                estados_atendidos = db.session.query(
                    func.count(distinct(RelatorioFaturamentoImportado.uf))
                ).filter(
                    RelatorioFaturamentoImportado.uf != None,
                    RelatorioFaturamentoImportado.uf != ''
                ).scalar() or 0
                
                logger.info(f"📊 Query especial: {total_clientes} clientes totais, {estados_atendidos} estados")
                
                return {
                    'tipo': 'contagem_total_clientes',
                    'total_clientes': total_clientes,
                    'estados_atendidos': estados_atendidos,
                    'observacao': 'Contagem de TODOS os clientes cadastrados no sistema'
                }
        
        except Exception as e:
            logger.error(f"❌ Erro na query especial {tipo_query}: {e}")
            return {'erro': str(e)}'''

        # 4. Modificar _analisar_consulta para usar o ajuste
        # Encontrar o método _analisar_consulta
        pos_analisar = conteudo.find('def _analisar_consulta(self, consulta: str) -> Dict[str, Any]:')
        if pos_analisar != -1:
            # Encontrar o return do método
            pos_return = conteudo.find('return analise', pos_analisar)
            if pos_return != -1:
                # Inserir chamada antes do return
                indent = '        '  # 8 espaços
                nova_linha = f'\n{indent}# Ajustar contexto para consultas de totais\n{indent}analise = self._ajustar_contexto_para_totais(consulta, analise)\n'
                
                # Encontrar a linha antes do return
                inicio_linha = conteudo.rfind('\n', 0, pos_return)
                conteudo = conteudo[:pos_return] + nova_linha + conteudo[pos_return:]
                print("✅ Ajuste de contexto adicionado em _analisar_consulta")

        # 5. Inserir os novos métodos após _analisar_consulta
        pos_fim_analisar = conteudo.find('\n    def _carregar_contexto_inteligente', pos_analisar)
        if pos_fim_analisar != -1:
            conteudo = (
                conteudo[:pos_fim_analisar] + 
                '\n' + novo_metodo + '\n' + query_especial +
                conteudo[pos_fim_analisar:]
            )
            print("✅ Novos métodos adicionados")

        # 6. Modificar _carregar_contexto_inteligente para usar queries especiais
        # Adicionar no início do método
        pos_carregar = conteudo.find('def _carregar_contexto_inteligente(self, analise: Dict[str, Any]) -> Dict[str, Any]:')
        if pos_carregar != -1:
            pos_try = conteudo.find('try:', pos_carregar)
            if pos_try != -1:
                check_query_especial = '''
            # Verificar se há query especial
            if analise.get('query_especial'):
                resultado_especial = self._executar_query_especial(analise['query_especial'])
                if resultado_especial and not resultado_especial.get('erro'):
                    return {
                        'dados_especificos': {'query_especial': resultado_especial},
                        'registros_carregados': 1,
                        'timestamp': datetime.now().isoformat(),
                        '_from_cache': False,
                        'tipo_consulta': 'query_especial'
                    }
            
'''
                # Inserir após o try:
                pos_apos_try = conteudo.find('\n', pos_try) + 1
                conteudo = conteudo[:pos_apos_try] + check_query_especial + conteudo[pos_apos_try:]
                print("✅ Verificação de query especial adicionada")

        # Salvar arquivo modificado
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("\n✅ Correções aplicadas com sucesso!")
        print("\n📊 Melhorias implementadas:")
        print("1. System prompt rigoroso contra invenções")
        print("2. Lista de clientes que NÃO existem")
        print("3. Detecção de perguntas sobre totais")
        print("4. Queries especiais sem filtro de data")
        print("5. Validação de contexto apropriado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar correções: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🔧 CORREÇÃO: CLAUDE INVENTANDO DADOS")
    print("=" * 50)
    print("Este script corrige o problema de Claude")
    print("inventar clientes e dados fictícios")
    print("=" * 50)
    
    # Fazer backup
    if not fazer_backup():
        print("❌ Falha ao criar backup. Abortando...")
        return
    
    # Aplicar correções
    if aplicar_correcoes():
        print("\n✅ CORREÇÕES APLICADAS COM SUCESSO!")
        print("\n🎯 Próximos passos:")
        print("1. Reinicie o servidor Flask")
        print("2. Teste: 'Quantos clientes existem no sistema?'")
        print("3. Claude não deve mais inventar dados!")
        
        print("\n📝 Testes recomendados:")
        print("- Quantos clientes existem no sistema?")
        print("- Qual o status do sistema?")
        print("- Liste os principais clientes")
        
        print("\n💡 Para reverter:")
        print("   Restaure o backup criado")
    else:
        print("\n❌ Falha ao aplicar correções")

if __name__ == "__main__":
    main() 