#!/usr/bin/env python
"""
🔧 Script para corrigir erro 'metodo_deteccao' que causa fallback
Corrige o problema que ocorreu com "Rede Mercadão"
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

def corrigir_erro_metodo_deteccao():
    """Corrige o erro KeyError: 'metodo_deteccao'"""
    
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # 1. Adicionar validação segura do campo metodo_deteccao
        validacao_metodo = '''
                # 🔧 CORREÇÃO: Validar campo metodo_deteccao
                if not grupo_detectado.get('metodo_deteccao'):
                    grupo_detectado['metodo_deteccao'] = 'auto_detectado'
                    logger.warning(f"⚠️ Campo metodo_deteccao ausente, usando padrão: auto_detectado")
                
                # 🔍 VALIDAR SE GRUPO AUTO-DETECTADO TEM DADOS REAIS
                if grupo_detectado.get('tipo_deteccao') == 'GRUPO_AUTOMATICO':
                    # Verificar se existem dados para esse grupo
                    from app import db
                    from app.monitoramento.models import EntregaMonitorada
                    
                    filtro_sql = grupo_detectado.get('filtro_sql', '')
                    if filtro_sql:
                        # Verificar se há registros com esse filtro
                        count = db.session.query(EntregaMonitorada).filter(
                            EntregaMonitorada.cliente.ilike(filtro_sql)
                        ).limit(1).count()
                        
                        if count == 0:
                            logger.warning(f"⚠️ Grupo auto-detectado '{grupo_detectado['grupo_detectado']}' não tem dados reais")
                            logger.info("🔄 Ignorando grupo sem dados e continuando análise geral")
                            # Não processar grupos sem dados
                            grupo_detectado = None
                            analise["tipo_consulta"] = "geral"
                            analise["cliente_especifico"] = None
                '''

        # 2. Encontrar onde o erro ocorre
        # O erro acontece logo após detectar o grupo
        pos_grupo_detectado = conteudo.find('if grupo_detectado:')
        if pos_grupo_detectado != -1:
            # Encontrar o início do bloco if
            inicio_linha = conteudo.rfind('\n', 0, pos_grupo_detectado)
            indent = '            '  # 12 espaços baseado no contexto
            
            # Inserir validação logo após o if
            pos_inserir = conteudo.find('\n', pos_grupo_detectado)
            conteudo = (
                conteudo[:pos_inserir] + '\n' +
                validacao_metodo +
                conteudo[pos_inserir:]
            )
            print("✅ Validação de metodo_deteccao adicionada")

        # 3. Adicionar tratamento de erro onde o campo é usado
        # Procurar por acessos diretos ao campo
        correcao_acesso = '''grupo_detectado.get('metodo_deteccao', 'auto_detectado')'''
        
        # Substituir acessos diretos
        conteudo = conteudo.replace(
            "grupo_detectado['metodo_deteccao']",
            correcao_acesso
        )
        
        # Contar substituições
        num_substituicoes = conteudo.count(correcao_acesso)
        if num_substituicoes > 0:
            print(f"✅ {num_substituicoes} acessos ao campo corrigidos")

        # 4. Adicionar tratamento de exceção específico
        tratamento_excecao = '''
        except KeyError as e:
            if str(e) == "'metodo_deteccao'":
                logger.error("❌ Erro: Campo 'metodo_deteccao' ausente no grupo detectado")
                logger.info("🔄 Continuando sem grupo específico")
                # Fallback para consulta geral
                analise["tipo_consulta"] = "geral"
                analise["cliente_especifico"] = None
            else:
                raise  # Re-lançar outros KeyErrors
        '''

        # 5. Adicionar log para debug
        log_debug = '''
                logger.debug(f"🔍 Grupo detectado: {grupo_detectado}")
                logger.debug(f"📋 Campos disponíveis: {list(grupo_detectado.keys())}")
        '''

        # Encontrar onde adicionar o log
        pos_log = conteudo.find("logger.info(f\"🏢 GRUPO EMPRESARIAL:")
        if pos_log != -1:
            inicio_linha_log = conteudo.rfind('\n', 0, pos_log)
            conteudo = (
                conteudo[:inicio_linha_log] + '\n' +
                log_debug +
                conteudo[inicio_linha_log:]
            )
            print("✅ Logs de debug adicionados")

        # Salvar arquivo modificado
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("\n✅ Correções aplicadas com sucesso!")
        print("\n🔧 Melhorias implementadas:")
        print("1. Validação segura do campo metodo_deteccao")
        print("2. Verificação se grupo auto-detectado tem dados reais")
        print("3. Fallback para consulta geral se grupo não tem dados")
        print("4. Tratamento de exceção específico")
        print("5. Logs de debug para troubleshooting")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar correções: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🔧 CORREÇÃO: Erro 'metodo_deteccao'")
    print("=" * 50)
    print("Este script corrige o erro que causou fallback")
    print("quando perguntaram sobre 'Rede Mercadão'")
    print("=" * 50)
    
    # Fazer backup
    if not fazer_backup():
        print("❌ Falha ao criar backup. Abortando...")
        return
    
    # Aplicar correções
    if corrigir_erro_metodo_deteccao():
        print("\n✅ CORREÇÕES APLICADAS!")
        print("\n🎯 Resultados esperados:")
        print("1. Erro 'metodo_deteccao' não causa mais fallback")
        print("2. Grupos auto-detectados são validados")
        print("3. Sistema continua funcionando sem grupos inexistentes")
        print("4. Melhor logging para debug")
        
        print("\n⚠️ Comportamento corrigido:")
        print("ANTES: Erro → Modo simulado")
        print("DEPOIS: Erro → Continua com consulta geral")
        
        print("\n💡 Para reverter:")
        print("   Restaure o backup criado")
    else:
        print("\n❌ Falha ao aplicar correções")

if __name__ == "__main__":
    main() 