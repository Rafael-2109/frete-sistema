#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔧 SCRIPT DE CORREÇÃO PARA CLAUDE AI
Corrige os erros identificados que causam "Resposta não disponível"
"""

import os
import sys
import re

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def corrigir_nlp_analyzer_method():
    """Corrige o método errado no claude_real_integration.py"""
    print("\n1. Corrigindo método NLP Analyzer...")
    
    arquivo = 'app/claude_ai/claude_real_integration.py'
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Encontrar e corrigir a linha errada
        if 'analyze_advanced_query' in conteudo:
            conteudo_corrigido = conteudo.replace(
                'nlp_analysis = self.nlp_analyzer.analyze_advanced_query(consulta, dados_contexto)',
                'nlp_analysis = self.nlp_analyzer.analisar_com_nlp(consulta, dados_contexto)'
            )
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(conteudo_corrigido)
            
            print("   ✅ Método corrigido: analyze_advanced_query → analisar_com_nlp")
        else:
            print("   ⚠️ Método já corrigido ou não encontrado")
            
    except Exception as e:
        print(f"   ❌ Erro ao corrigir: {e}")

def adicionar_tratamento_campo_ligacao():
    """Adiciona tratamento para erro campo_ligacao no advanced_integration.py"""
    print("\n2. Corrigindo erro campo_ligacao...")
    
    arquivo = 'app/claude_ai/advanced_integration.py'
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Encontrar a função _analyze_semantics
        if 'mapping_result = mapeamento.mapear_consulta_completa(query)' in conteudo:
            # Adicionar tratamento de erro mais robusto
            novo_conteudo = conteudo.replace(
                """            # Mapear consulta completa
            mapping_result = mapeamento.mapear_consulta_completa(query)
            
            return {
                'mapped_terms': mapping_result.get('termos_mapeados', []),
                'confidence': mapping_result.get('confianca_geral', 0.5),
                'domain_detected': mapping_result.get('dominio_detectado', 'geral'),
                'semantic_complexity': len(query.split()) / 20.0  # Normalizado
            }""",
                """            # Mapear consulta completa
            try:
                mapping_result = mapeamento.mapear_consulta_completa(query)
                
                return {
                    'mapped_terms': mapping_result.get('termos_mapeados', []),
                    'confidence': mapping_result.get('confianca_geral', 0.5),
                    'domain_detected': mapping_result.get('dominio_detectado', 'geral'),
                    'semantic_complexity': len(query.split()) / 20.0  # Normalizado
                }
            except (AttributeError, KeyError) as e:
                logger.warning(f"Erro no mapeamento semântico: {e}")
                # Retornar análise básica sem mapeamento
                return {
                    'mapped_terms': [],
                    'confidence': 0.5,
                    'domain_detected': 'geral',
                    'semantic_complexity': len(query.split()) / 20.0
                }"""
            )
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(novo_conteudo)
            
            print("   ✅ Tratamento de erro campo_ligacao adicionado")
        else:
            print("   ⚠️ Código já corrigido ou estrutura diferente")
            
    except Exception as e:
        print(f"   ❌ Erro ao corrigir: {e}")

def melhorar_resposta_padrao():
    """Melhora a resposta padrão quando há erros"""
    print("\n3. Melhorando respostas padrão...")
    
    arquivo = 'app/claude_ai/claude_real_integration.py'
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Procurar resposta padrão
        if '"Resposta não disponível"' in conteudo:
            # Melhorar mensagem de erro
            conteudo = conteudo.replace(
                '"Resposta não disponível"',
                '"Desculpe, encontrei um problema ao processar sua consulta. Por favor, tente reformular ou seja mais específico."'
            )
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(conteudo)
            
            print("   ✅ Resposta padrão melhorada")
        else:
            print("   ⚠️ Resposta padrão não encontrada")
            
    except Exception as e:
        print(f"   ❌ Erro ao melhorar resposta: {e}")

def corrigir_analyze_com_nlp():
    """Corrige o uso correto do método analisar_com_nlp"""
    print("\n4. Ajustando integração com NLP...")
    
    arquivo = 'app/claude_ai/claude_real_integration.py'
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
        
        modificado = False
        for i, linha in enumerate(linhas):
            if 'nlp_analysis = self.nlp_analyzer.analisar_com_nlp(consulta)' in linha:
                # Adicionar tratamento do resultado
                espacos = len(linha) - len(linha.lstrip())
                indent = ' ' * espacos
                
                # Substituir com código completo
                novas_linhas = [
                    f"{indent}# Aplicar análise NLP\n",
                    f"{indent}nlp_result = self.nlp_analyzer.analisar_com_nlp(consulta)\n",
                    f"{indent}# Usar os resultados da análise\n",
                    f"{indent}if nlp_result and nlp_result.tokens_limpos:\n",
                    f"{indent}    logger.info(f'🔬 NLP: {{len(nlp_result.tokens_limpos)}} tokens, {{len(nlp_result.palavras_chave)}} palavras-chave')\n",
                    f"{indent}    # Aplicar correções sugeridas\n",
                    f"{indent}    if nlp_result.correcoes_sugeridas:\n",
                    f"{indent}        for erro, correcao in nlp_result.correcoes_sugeridas.items():\n",
                    f"{indent}            consulta = consulta.replace(erro, correcao)\n",
                    f"{indent}        logger.info(f'📝 NLP aplicou {{len(nlp_result.correcoes_sugeridas)}} correções')\n"
                ]
                
                # Substituir linha
                linhas[i:i+1] = novas_linhas
                modificado = True
                break
        
        if modificado:
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.writelines(linhas)
            print("   ✅ Integração NLP corrigida com tratamento completo")
        else:
            print("   ⚠️ Linha de integração NLP não encontrada")
            
    except Exception as e:
        print(f"   ❌ Erro ao corrigir integração: {e}")

def adicionar_logs_debug():
    """Adiciona mais logs para debug"""
    print("\n5. Adicionando logs de debug...")
    
    arquivo = 'app/claude_ai/claude_real_integration.py'
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Adicionar log antes do processamento avançado
        if 'logger.info("🚀 Iniciando processamento IA AVANÇADA...")' in conteudo:
            conteudo = conteudo.replace(
                'logger.info("🚀 Iniciando processamento IA AVANÇADA...")',
                '''logger.info("🚀 Iniciando processamento IA AVANÇADA...")
        logger.debug(f"📊 Contexto: domínio={dados_contexto.get('dominio', 'N/A')}, cliente={dados_contexto.get('cliente_especifico', 'N/A')}")
        logger.debug(f"📊 Dados: {len(dados_contexto.get('dados', []))} registros carregados")'''
            )
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(conteudo)
            
            print("   ✅ Logs de debug adicionados")
        else:
            print("   ⚠️ Ponto de inserção de logs não encontrado")
            
    except Exception as e:
        print(f"   ❌ Erro ao adicionar logs: {e}")

def main():
    """Executa todas as correções"""
    print("🔧 INICIANDO CORREÇÕES DO CLAUDE AI...")
    
    # Executar correções
    corrigir_nlp_analyzer_method()
    adicionar_tratamento_campo_ligacao()
    melhorar_resposta_padrao()
    corrigir_analyze_com_nlp()
    adicionar_logs_debug()
    
    print("\n✅ CORREÇÕES CONCLUÍDAS!")
    print("\n📝 PRÓXIMOS PASSOS:")
    print("1. Faça commit das alterações")
    print("2. Faça push para o GitHub")
    print("3. O Render fará deploy automático")
    print("4. Teste o Claude AI novamente")
    
    print("\n💡 TESTE COM:")
    print('   - "Quais entregas estão atrasadas?"')
    print('   - "Mostre os pedidos do Assai"')
    print('   - "Relatório de fretes pendentes"')

if __name__ == "__main__":
    main() 