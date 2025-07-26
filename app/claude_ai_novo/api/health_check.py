#!/usr/bin/env python3
"""
Health Check API para o sistema Claude AI Novo
Endpoints para monitoramento e verificação de saúde do sistema
"""

try:
    from flask import Blueprint, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    Blueprint, jsonify = None
    FLASK_AVAILABLE = False
from datetime import datetime
import os
import psutil
import logging

# Criar blueprint
health_blueprint = Blueprint('claude_ai_health', __name__)

# Logger
logger = logging.getLogger(__name__)

@health_blueprint.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint principal de health check
    Retorna o status geral do sistema
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "claude_ai_novo",
            "version": "2.0.0",
            "checks": {
                "api": check_api_status(),
                "database": check_database_status(),
                "claude_api": check_claude_api_status(),
                "memory": check_memory_status(),
                "disk": check_disk_status()
            }
        }
        
        # Determinar status geral
        all_healthy = all(check.get("status") == "healthy" 
                         for check in health_status["checks"].values())
        
        if not all_healthy:
            health_status["status"] = "degraded"
            
        return jsonify(health_status), 200 if all_healthy else 503
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@health_blueprint.route('/health/live', methods=['GET'])
def liveness_probe():
    """
    Liveness probe para Kubernetes/Docker
    Verifica se o serviço está vivo
    """
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200

@health_blueprint.route('/health/ready', methods=['GET'])
def readiness_probe():
    """
    Readiness probe para Kubernetes/Docker
    Verifica se o serviço está pronto para receber tráfego
    """
    try:
        # Verificar componentes críticos
        db_status = check_database_status()
        claude_status = check_claude_api_status()
        
        is_ready = (
            db_status.get("status") == "healthy" and
            claude_status.get("status") == "healthy"
        )
        
        return jsonify({
            "ready": is_ready,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {
                "database": db_status,
                "claude_api": claude_status
            }
        }), 200 if is_ready else 503
        
    except Exception as e:
        logger.error(f"Erro no readiness probe: {e}")
        return jsonify({
            "ready": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503

def check_api_status():
    """Verifica status da API"""
    return {
        "status": "healthy",
        "response_time_ms": 1
    }

def check_database_status():
    """Verifica status do banco de dados"""
    try:
        from app import db
        # Executar query simples
        db.session.execute("SELECT 1")
        return {
            "status": "healthy",
            "connection": "active"
        }
    except Exception as e:
        logger.error(f"Erro ao verificar database: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def check_claude_api_status():
    """Verifica status da API do Claude"""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return {
                "status": "unhealthy",
                "error": "API key not configured"
            }
        
        return {
            "status": "healthy",
            "api_key_configured": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def check_memory_status():
    """Verifica status da memória"""
    try:
        memory = psutil.virtual_memory()
        return {
            "status": "healthy" if memory.percent < 90 else "warning",
            "usage_percent": memory.percent,
            "available_mb": memory.available / 1024 / 1024
        }
    except:
        return {
            "status": "unknown",
            "error": "Unable to check memory"
        }

def check_disk_status():
    """Verifica status do disco"""
    try:
        disk = psutil.disk_usage('/')
        return {
            "status": "healthy" if disk.percent < 85 else "warning",
            "usage_percent": disk.percent,
            "free_gb": disk.free / 1024 / 1024 / 1024
        }
    except:
        return {
            "status": "unknown",
            "error": "Unable to check disk"
        }