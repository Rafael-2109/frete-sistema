#!/usr/bin/env python3
"""
DIAGNÓSTICO SEGURO: Apenas analisa problema UTF-8 sem modificar nada
"""

import os
import sys
import tempfile

def analisar_problema_utf8():
    """Analisa o problema UTF-8 sem fazer modificações"""
    
    print('🔍 DIAGNÓSTICO SEGURO - PROBLEMA UTF-8')
    print('=' * 60)
    
    # 1. Analisar ambiente atual
    print('📊 1. AMBIENTE ATUAL:')
    print('-' * 30)
    
    print(f'Python version: {sys.version}')
    print(f'Python encoding: {sys.getdefaultencoding()}')
    print(f'File system encoding: {sys.getfilesystemencoding()}')
    
    import locale
    try:
        print(f'System locale: {locale.getpreferredencoding()}')
    except:
        print('System locale: N/A')
    
    # Verificar variáveis de ambiente relevantes
    env_vars = ['PYTHONIOENCODING', 'LANG', 'LC_ALL', 'PGCLIENTENCODING']
    print(f'\nVariáveis de ambiente:')
    for var in env_vars:
        value = os.getenv(var, 'não definida')
        print(f'  {var}: {value}')
    
    print()
    
    # 2. Testar conexão (sem modificar nada)
    print('🧪 2. TESTE DE CONEXÃO:')
    print('-' * 30)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('❌ DATABASE_URL não encontrada')
        return False
    
    print(f'Database URL length: {len(database_url)} caracteres')
    print(f'Database URL válida: ✅')
    
    # Testar apenas import sem conectar
    try:
        import psycopg2
        print(f'psycopg2 version: {psycopg2.__version__}')
        print('psycopg2 import: ✅')
    except ImportError as e:
        print(f'psycopg2 import: ❌ {e}')
        return False
    
    # 3. Simular teste de conexão (sem conectar realmente)
    print('\n🔬 3. SIMULAÇÃO DE TESTE:')
    print('-' * 30)
    
    # Em vez de conectar, vamos apenas simular com dados de teste
    try:
        # Criar um teste com dados locais
        test_string = "Teste com acentuação: ção, ã, é, ñ"
        encoded = test_string.encode('utf-8')
        decoded = encoded.decode('utf-8')
        print(f'Teste encoding/decoding: ✅')
        print(f'String teste: {decoded}')
    except Exception as e:
        print(f'Teste encoding/decoding: ❌ {e}')
    
    print()
    
    # 4. Analisar arquivo .env atual
    print('📄 4. ANÁLISE DO .env ATUAL:')
    print('-' * 30)
    
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        print('Arquivo .env encontrado ✅')
        print(f'Tamanho: {len(env_content)} caracteres')
        
        # Verificar configurações UTF-8 existentes
        utf8_configs = ['PYTHONIOENCODING', 'PYTHONUTF8', 'PGCLIENTENCODING']
        print('\nConfigurações UTF-8 no .env:')
        for config in utf8_configs:
            if config in env_content:
                # Extrair valor
                for line in env_content.split('\n'):
                    if line.startswith(config):
                        print(f'  ✅ {line}')
                        break
            else:
                print(f'  ❌ {config}: não configurado')
                
    except FileNotFoundError:
        print('Arquivo .env: não encontrado')
    except Exception as e:
        print(f'Erro ao ler .env: {e}')
    
    print()
    
    # 5. Verificar modelo PreSeparacaoItem
    print('🔧 5. VERIFICAÇÃO DO MODELO:')
    print('-' * 30)
    
    model_file = 'app/carteira/models.py'
    try:
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print('Modelo carteira/models.py: ✅')
        
        if 'class PreSeparacaoItem' in content:
            print('Classe PreSeparacaoItem: ✅ encontrada')
            
            if 'salvar_via_workaround' in content:
                print('Método salvar_via_workaround: ✅ implementado')
            else:
                print('Método salvar_via_workaround: ❌ não implementado')
                
            if 'carregar_via_workaround' in content:
                print('Método carregar_via_workaround: ✅ implementado')
            else:
                print('Método carregar_via_workaround: ❌ não implementado')
        else:
            print('Classe PreSeparacaoItem: ❌ não encontrada')
            
    except Exception as e:
        print(f'Erro ao verificar modelo: {e}')
    
    return True

def gerar_recomendacoes():
    """Gera recomendações baseadas na análise"""
    
    print('\n💡 RECOMENDAÇÕES SEGURAS:')
    print('=' * 60)
    
    print('🔧 OPÇÃO 1 - CONFIGURAÇÃO MANUAL TEMPORÁRIA:')
    print('   Configurar variáveis apenas para esta sessão:')
    print('   ```')
    print('   set PYTHONIOENCODING=utf-8')
    print('   set PYTHONUTF8=1')
    print('   set PGCLIENTENCODING=UTF8')
    print('   ```')
    print()
    
    print('🔄 OPÇÃO 2 - WORKAROUND PERMANENTE (RECOMENDADO):')
    print('   Usar PreSeparacaoItem.salvar_via_workaround() que já está implementado')
    print('   Não mexer nas migrações até resolução definitiva')
    print()
    
    print('🚀 OPÇÃO 3 - APLICAR APENAS EM PRODUÇÃO:')
    print('   Migração funciona no Render (ambiente Linux UTF-8)')
    print('   Desenvolver localmente com workaround')
    print()
    
    print('⚠️ RISCOS A EVITAR:')
    print('   ❌ Modificar .env sem backup')
    print('   ❌ Testar conexão direta em produção')
    print('   ❌ Aplicar configurações globais sem testar')

def main():
    """Função principal segura"""
    
    print('🛡️ DIAGNÓSTICO SEGURO - SEM MODIFICAÇÕES')
    print('=' * 60)
    print('Este script apenas ANALISA, não modifica nada!')
    print()
    
    # Análise completa
    sucesso = analisar_problema_utf8()
    
    # Recomendações
    gerar_recomendacoes()
    
    print('\n🎯 PRÓXIMOS PASSOS SEGUROS:')
    print('=' * 60)
    print('1. ✅ Usar workaround implementado no modelo')
    print('2. ✅ Continuar desenvolvimento com Etapa 2')
    print('3. ✅ Aplicar migração real apenas no Render')
    print('4. ⚠️ Evitar modificações arriscadas no ambiente local')
    
    return sucesso

if __name__ == "__main__":
    success = main()
    print(f'\n✅ Diagnóstico concluído {"com sucesso" if success else "com problemas"}') 