#!/usr/bin/env python3
"""
Script para criar todos os arquivos e diretórios necessários para o Claude AI
"""

import os
import json
import logging
import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def criar_diretorios_necessarios():
    """Cria todos os diretórios necessários"""
    
    diretorios = [
        "instance",
        "instance/claude_ai",
        "instance/claude_ai/backups",
        "instance/claude_ai/logs",
        "app/claude_ai/backups",
        "app/claude_ai/logs",
        "logs",
        "ml_models"
    ]
    
    logger.info("🏗️ Criando diretórios necessários...")
    
    for diretorio in diretorios:
        try:
            os.makedirs(diretorio, exist_ok=True)
            logger.info(f"✅ Diretório criado: {diretorio}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar {diretorio}: {e}")

def criar_security_config():
    """Cria arquivo de configuração de segurança"""
    
    config_path = "instance/claude_ai/security_config.json"
    
    config = {
        "security_level": "high",
        "max_file_size": 10485760,  # 10MB
        "allowed_extensions": [".py", ".txt", ".md", ".json", ".csv", ".xlsx"],
        "forbidden_patterns": [
            "password",
            "secret",
            "token",
            "key",
            "drop table",
            "delete from",
            "rm -rf",
            "format c:"
        ],
        "rate_limiting": {
            "max_requests_per_minute": 60,
            "max_requests_per_hour": 1000
        },
        "audit_logging": True,
        "encryption": {
            "enabled": True,
            "algorithm": "AES-256-GCM"
        },
        "access_control": {
            "require_authentication": True,
            "min_user_level": "user"
        }
    }
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Arquivo de configuração criado: {config_path}")
    except Exception as e:
        logger.error(f"❌ Erro ao criar config: {e}")

def criar_arquivos_log():
    """Cria arquivos de log vazios"""
    
    log_files = [
        "instance/claude_ai/logs/security.log",
        "instance/claude_ai/logs/operations.log",
        "app/claude_ai/logs/debug.log",
        "logs/claude_ai.log",
        "logs/multi_agent.log"
    ]
    
    logger.info("📋 Criando arquivos de log...")
    
    for log_file in log_files:
        try:
            # Criar diretório pai se não existir
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Criar arquivo vazio
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"# Log iniciado em {str(datetime.datetime.now())}\n")
            
            logger.info(f"✅ Arquivo de log criado: {log_file}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar {log_file}: {e}")

def criar_arquivos_backup():
    """Cria estrutura de backup"""
    
    backup_dirs = [
        "instance/claude_ai/backups/code",
        "instance/claude_ai/backups/config",
        "instance/claude_ai/backups/models",
        "app/claude_ai/backups/generated",
        "app/claude_ai/backups/projects"
    ]
    
    logger.info("💾 Criando estrutura de backup...")
    
    for backup_dir in backup_dirs:
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            # Criar arquivo .gitkeep para manter diretório no git
            gitkeep_file = os.path.join(backup_dir, ".gitkeep")
            with open(gitkeep_file, 'w') as f:
                f.write("")
            
            logger.info(f"✅ Backup dir criado: {backup_dir}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar backup dir: {e}")

def criar_pending_actions():
    """Cria arquivo de ações pendentes"""
    
    pending_actions = {
        "version": "1.0",
        "last_updated": "2024-07-04",
        "actions": [
            {
                "id": "init_001",
                "type": "system_init",
                "description": "Inicialização do sistema Claude AI",
                "status": "completed",
                "timestamp": "2024-07-04T18:00:00Z"
            }
        ]
    }
    
    try:
        with open("app/claude_ai/pending_actions.json", 'w', encoding='utf-8') as f:
            json.dump(pending_actions, f, indent=2, ensure_ascii=False)
        logger.info("✅ Arquivo pending_actions.json criado")
    except Exception as e:
        logger.error(f"❌ Erro ao criar pending_actions.json: {e}")

def main():
    """Função principal"""
    
    logger.info("🚀 Iniciando criação de arquivos necessários...")
    
    try:
        criar_diretorios_necessarios()
        criar_security_config()
        criar_arquivos_log()
        criar_arquivos_backup()
        criar_pending_actions()
        
        logger.info("✅ Todos os arquivos e diretórios necessários foram criados!")
        logger.info("🔥 Agora os sistemas devem funcionar sem erros de arquivo não encontrado")
        
    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 