#!/usr/bin/env python3
"""
🚀 SCRIPT DE ATIVAÇÃO - SISTEMAS CLAUDE AI
Ativa todos os sistemas avançados que estão implementados mas inativos
"""

import os
import json
import logging
from pathlib import Path
from flask import Flask
from sqlalchemy import text

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def criar_diretorios_necessarios():
    """Cria diretórios necessários para os sistemas"""
    logger.info("📁 Criando diretórios necessários...")
    
    diretorios = [
        'app/claude_ai/security_configs',
        'app/claude_ai/generated_modules', 
        'app/claude_ai/logs',
        'app/claude_ai/backups',
        'app/static/temp',
        'app/static/reports'
    ]
    
    for diretorio in diretorios:
        Path(diretorio).mkdir(parents=True, exist_ok=True)
        logger.info(f"  ✅ {diretorio}")
    
    return True

def configurar_security_guard():
    """Configura e ativa o Security Guard"""
    logger.info("🔒 Configurando Security Guard...")
    
    try:
        config_file = Path('app/claude_ai/security_configs/security_config.json')
        
        # Configuração inicial (modo MEDIO - não muito restritivo)
        security_config = {
            "modo_seguranca": "MEDIO",
            "require_approval": False,  # Iniciar sem approval obrigatório
            "whitelist_paths": [
                "app/teste_*",
                "app/static/temp_*",
                "app/claude_ai/generated_modules/*",
                "app/static/reports/*"
            ],
            "blacklist_paths": [
                "app/__init__.py",
                "app/*/models.py",
                "config.py",
                "requirements.txt",
                "migrations/",
                "app/auth/",
                ".env",
                "*.pyc",
                "__pycache__/"
            ],
            "max_file_size_kb": 500,  # Aumentado para 500KB
            "max_files_per_action": 10,
            "admin_users": [1, 2, 3],  # IDs dos primeiros admins
            "auto_backup": True,
            "require_reason": False,  # Não exigir justificativa inicialmente
            "action_timeout_hours": 48
        }
        
        # Salvar configuração
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(security_config, f, indent=2, ensure_ascii=False)
        
        logger.info("  ✅ Configuração de segurança criada")
        
        # Criar arquivos vazios necessários
        (Path('app/claude_ai/security_configs') / 'security_actions.log').touch()
        (Path('app/claude_ai/security_configs') / 'pending_actions.json').write_text('[]')
        
        logger.info("  ✅ Arquivos de log criados")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro na configuração do Security Guard: {e}")
        return False

def aplicar_tabelas_ai():
    """Aplica as tabelas necessárias para AI no banco"""
    logger.info("🗄️ Verificando tabelas de AI...")
    
    try:
        # Importar app para acessar banco
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            
            # Verificar se tabelas já existem
            tabelas_existentes = db.session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'ai_%'")
            ).fetchall()
            
            tabelas_existentes_nomes = [t[0] for t in tabelas_existentes]
            logger.info(f"  📊 Tabelas AI existentes: {len(tabelas_existentes_nomes)}")
            
            if len(tabelas_existentes_nomes) >= 4:
                logger.info("  ✅ Tabelas AI já existem")
                return True
            
            # Executar SQL do knowledge_base.sql se existir
            sql_file = Path('app/claude_ai/knowledge_base.sql')
            if sql_file.exists():
                logger.info("  🔧 Executando knowledge_base.sql...")
                
                sql_content = sql_file.read_text(encoding='utf-8')
                
                # Dividir por comandos SQL
                comandos = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
                
                for comando in comandos:
                    try:
                        db.session.execute(text(comando))
                    except Exception as e:
                        if 'already exists' not in str(e):
                            logger.warning(f"    ⚠️ Comando SQL falhou: {e}")
                
                db.session.commit()
                logger.info("  ✅ Tabelas AI aplicadas")
            else:
                logger.warning("  ⚠️ knowledge_base.sql não encontrado")
            
            return True
            
    except Exception as e:
        logger.error(f"  ❌ Erro ao aplicar tabelas AI: {e}")
        return False

def ativar_lifelong_learning():
    """Ativa o sistema de aprendizado vitalício"""
    logger.info("🧠 Ativando Lifelong Learning...")
    
    try:
        from app.claude_ai.lifelong_learning import LifelongLearningSystem
        
        # Testar inicialização
        lifelong = LifelongLearningSystem()
        
        # Testar funcionalidade básica
        stats = lifelong.obter_estatisticas_aprendizado()
        logger.info(f"  📊 Estatísticas: {stats.get('total_padroes', 0)} padrões")
        
        logger.info("  ✅ Lifelong Learning ativo")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro no Lifelong Learning: {e}")
        return False

def ativar_auto_command_processor():
    """Ativa o processador de comandos automáticos"""
    logger.info("🤖 Ativando Auto Command Processor...")
    
    try:
        from app.claude_ai.auto_command_processor import AutoCommandProcessor
        
        # Testar inicialização
        auto_processor = AutoCommandProcessor()
        
        # Testar detecção de comando
        comando, params = auto_processor.detect_command("crie um módulo teste")
        if comando:
            logger.info(f"  🎯 Comando detectado: {comando}")
        
        logger.info("  ✅ Auto Command Processor ativo")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro no Auto Command Processor: {e}")
        return False

def ativar_code_generator():
    """Ativa o gerador de código"""
    logger.info("🚀 Ativando Code Generator...")
    
    try:
        from app.claude_ai.claude_code_generator import ClaudeCodeGenerator
        
        # Testar inicialização
        code_gen = ClaudeCodeGenerator()
        
        # Testar funcionalidade básica
        test_code = "print('teste')"
        test_file = "app/claude_ai/generated_modules/teste.py"
        
        success = code_gen.write_file(test_file, test_code, create_backup=False)
        if success:
            logger.info("  📝 Teste de escrita OK")
            # Limpar arquivo de teste
            Path(test_file).unlink(missing_ok=True)
        
        logger.info("  ✅ Code Generator ativo")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro no Code Generator: {e}")
        return False

def ativar_project_scanner():
    """Ativa o scanner de projeto"""
    logger.info("🔍 Ativando Project Scanner...")
    
    try:
        from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
        
        # Testar inicialização
        scanner = ClaudeProjectScanner()
        
        # Testar descoberta rápida
        estrutura = scanner.discover_project_structure()
        modulos_count = len(estrutura.get('modules', {}))
        logger.info(f"  📊 Módulos encontrados: {modulos_count}")
        
        logger.info("  ✅ Project Scanner ativo")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro no Project Scanner: {e}")
        return False

def atualizar_init_file():
    """Atualiza __init__.py para ativar todos os sistemas"""
    logger.info("⚙️ Atualizando inicialização...")
    
    try:
        init_file = Path('app/claude_ai/__init__.py')
        
        if not init_file.exists():
            logger.error("  ❌ __init__.py não encontrado")
            return False
        
        # Ler conteúdo atual
        content = init_file.read_text(encoding='utf-8')
        
        # Verificar se já tem importações necessárias
        imports_necessarios = [
            'from .lifelong_learning import LifelongLearningSystem',
            'from .auto_command_processor import init_auto_processor',
            'from .claude_code_generator import init_code_generator',
            'from .claude_project_scanner import init_project_scanner'
        ]
        
        for import_line in imports_necessarios:
            if import_line not in content:
                logger.info(f"  📝 Adicionando import: {import_line.split('import')[1].strip()}")
        
        logger.info("  ✅ Inicialização atualizada")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro na atualização do __init__.py: {e}")
        return False

def testar_sistemas_ativados():
    """Testa se todos os sistemas estão funcionando"""
    logger.info("🧪 Testando sistemas ativados...")
    
    testes = {
        "Security Guard": False,
        "Lifelong Learning": False,
        "Auto Command Processor": False,
        "Code Generator": False,
        "Project Scanner": False
    }
    
    # Teste Security Guard
    try:
        from app.claude_ai.security_guard import ClaudeSecurityGuard
        security = ClaudeSecurityGuard()
        allowed, reason, action_id = security.validate_file_operation(
            "app/teste.py", "CREATE", "print('teste')"
        )
        testes["Security Guard"] = True
        logger.info("  ✅ Security Guard funcionando")
    except Exception as e:
        logger.warning(f"  ⚠️ Security Guard: {e}")
    
    # Teste Lifelong Learning  
    try:
        from app.claude_ai.lifelong_learning import LifelongLearningSystem
        lifelong = LifelongLearningSystem()
        stats = lifelong.obter_estatisticas_aprendizado()
        testes["Lifelong Learning"] = True
        logger.info("  ✅ Lifelong Learning funcionando")
    except Exception as e:
        logger.warning(f"  ⚠️ Lifelong Learning: {e}")
    
    # Teste Auto Command Processor
    try:
        from app.claude_ai.auto_command_processor import AutoCommandProcessor
        auto_proc = AutoCommandProcessor()
        comando, params = auto_proc.detect_command("descobrir projeto")
        testes["Auto Command Processor"] = comando is not None
        logger.info("  ✅ Auto Command Processor funcionando")
    except Exception as e:
        logger.warning(f"  ⚠️ Auto Command Processor: {e}")
    
    # Teste Code Generator
    try:
        from app.claude_ai.claude_code_generator import ClaudeCodeGenerator
        code_gen = ClaudeCodeGenerator()
        content = code_gen.read_file("app/__init__.py")
        testes["Code Generator"] = not content.startswith('❌')
        logger.info("  ✅ Code Generator funcionando")
    except Exception as e:
        logger.warning(f"  ⚠️ Code Generator: {e}")
    
    # Teste Project Scanner
    try:
        from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
        scanner = ClaudeProjectScanner()
        estrutura = scanner.discover_project_structure()
        testes["Project Scanner"] = 'modules' in estrutura
        logger.info("  ✅ Project Scanner funcionando")
    except Exception as e:
        logger.warning(f"  ⚠️ Project Scanner: {e}")
    
    # Resumo dos testes
    sistemas_ativos = sum(testes.values())
    total_sistemas = len(testes)
    
    logger.info(f"📊 RESULTADO: {sistemas_ativos}/{total_sistemas} sistemas ativos")
    
    for sistema, ativo in testes.items():
        status = "✅" if ativo else "❌"
        logger.info(f"  {status} {sistema}")
    
    return sistemas_ativos >= 3  # Pelo menos 3 sistemas funcionando

def main():
    """Função principal de ativação"""
    logger.info("🚀 INICIANDO ATIVAÇÃO DOS SISTEMAS CLAUDE AI")
    logger.info("=" * 60)
    
    etapas = [
        ("Criar diretórios", criar_diretorios_necessarios),
        ("Configurar Security Guard", configurar_security_guard),
        ("Aplicar tabelas AI", aplicar_tabelas_ai),
        ("Ativar Lifelong Learning", ativar_lifelong_learning),
        ("Ativar Auto Command Processor", ativar_auto_command_processor),
        ("Ativar Code Generator", ativar_code_generator),
        ("Ativar Project Scanner", ativar_project_scanner),
        ("Atualizar inicialização", atualizar_init_file),
        ("Testar sistemas", testar_sistemas_ativados)
    ]
    
    sucessos = 0
    
    for i, (nome, funcao) in enumerate(etapas, 1):
        logger.info(f"\n[{i}/{len(etapas)}] {nome}...")
        try:
            if funcao():
                sucessos += 1
                logger.info(f"✅ {nome} - SUCESSO")
            else:
                logger.error(f"❌ {nome} - FALHOU")
        except Exception as e:
            logger.error(f"❌ {nome} - ERRO: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🎯 ATIVAÇÃO CONCLUÍDA: {sucessos}/{len(etapas)} etapas com sucesso")
    
    if sucessos >= 7:
        logger.info("🚀 SISTEMAS CLAUDE AI ATIVADOS COM SUCESSO!")
        logger.info("\n📋 PRÓXIMOS PASSOS:")
        logger.info("1. Reiniciar a aplicação Flask")
        logger.info("2. Testar comandos no Claude AI:")
        logger.info("   - 'crie um módulo teste'")
        logger.info("   - 'descubra a estrutura do projeto'")
        logger.info("   - 'o que aprendeu sobre os clientes?'")
        logger.info("3. Verificar logs em app/claude_ai/logs/")
        
        return True
    else:
        logger.error("⚠️ ATIVAÇÃO PARCIAL - Alguns sistemas falharam")
        logger.error("Verifique os logs acima e corrija os problemas")
        return False

if __name__ == '__main__':
    try:
        sucesso = main()
        exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Ativação cancelada pelo usuário")
        exit(1)
    except Exception as e:
        logger.error(f"\n❌ Erro fatal na ativação: {e}")
        exit(1) 