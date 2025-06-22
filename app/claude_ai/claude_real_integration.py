#!/usr/bin/env python3
"""
Integração Claude REAL - API Anthropic
Sistema que usa o Claude verdadeiro ao invés de simulação
"""

import os
import anthropic
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ClaudeRealIntegration:
    """Integração com Claude REAL da Anthropic"""
    
    def __init__(self):
        """Inicializa integração com Claude real"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY não configurada - usando modo simulado")
            self.client = None
            self.modo_real = False
        else:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.modo_real = True
                logger.info("🚀 Claude REAL conectado com sucesso!")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Claude real: {e}")
                self.client = None
                self.modo_real = False
        
        # System prompt PODEROSO para Claude real
        self.system_prompt = """Você é Claude integrado ao Sistema de Fretes da empresa. 

CONTEXTO: Sistema completo de gestão de fretes com:
- Pedidos, Embarques, Fretes, Transportadoras
- Monitoramento de entregas
- Controle financeiro e faturamento
- Portaria e controle de veículos

SUAS CAPACIDADES:
- Análise inteligente de dados reais
- Insights preditivos e recomendações
- Interpretação de linguagem natural
- Resolução de problemas complexos
- Geração de relatórios detalhados

FERRAMENTAS DISPONÍVEIS:
{tools_description}

DADOS REAIS: Você tem acesso aos dados reais via PostgreSQL.

INSTRUÇÕES:
1. Seja EXTREMAMENTE inteligente e preciso
2. Forneça insights valiosos e acionáveis  
3. Use linguagem natural e seja conversacional
4. Sempre que possível, sugira melhorias
5. Identifique padrões e anomalias
6. Seja proativo em recomendações

Responda sempre em português brasileiro."""
    
    def processar_consulta_real(self, consulta: str, user_context: Dict = None) -> str:
        """Processa consulta usando Claude REAL"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
        try:
            # Carregar contexto de dados reais
            dados_contexto = self._carregar_dados_contexto()
            
            # Preparar mensagens para Claude real
            messages = [
                {
                    "role": "user", 
                    "content": f"""CONSULTA DO USUÁRIO: {consulta}

DADOS ATUAIS DO SISTEMA:
{json.dumps(dados_contexto, indent=2, ensure_ascii=False)}

CONTEXTO DO USUÁRIO:
{json.dumps(user_context or {}, indent=2, ensure_ascii=False)}

Por favor, analise a consulta e forneça uma resposta inteligente, detalhada e acionável usando os dados reais do sistema."""
                }
            ]
            
            # Chamar Claude REAL
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Modelo mais avançado
                max_tokens=4000,
                temperature=0.1,  # Mais determinístico para dados
                system=self.system_prompt.format(
                    tools_description=self._get_tools_description()
                ),
                messages=messages
            )
            
            resultado = response.content[0].text
            
            # Log da interação
            logger.info(f"✅ Claude REAL processou: '{consulta[:50]}...'")
            
            return f"""🤖 **CLAUDE REAL v3.5 Sonnet**

{resultado}

---
🧠 **Powered by:** Claude 3.5 Sonnet (Anthropic)
🕒 **Processado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Modo:** Inteligência Artificial Real"""
            
        except Exception as e:
            logger.error(f"❌ Erro no Claude real: {e}")
            return self._fallback_simulado(consulta)
    
    def _carregar_dados_contexto(self) -> Dict[str, Any]:
        """Carrega dados reais do sistema para contexto"""
        try:
            from app import db
            from app.fretes.models import Frete
            from app.embarques.models import Embarque
            from app.transportadoras.models import Transportadora
            from app.pedidos.models import Pedido
            from sqlalchemy import func
            
            # Estatísticas rápidas para contexto
            contexto = {
                "timestamp": datetime.now().isoformat(),
                "estatisticas": {
                    "total_fretes": db.session.query(Frete).count(),
                    "fretes_pendentes": db.session.query(Frete).filter(Frete.status == 'PENDENTE').count(),
                    "fretes_aprovados": db.session.query(Frete).filter(Frete.status == 'APROVADO').count(),
                    "total_embarques": db.session.query(Embarque).count(),
                    "embarques_ativos": db.session.query(Embarque).filter(Embarque.status == 'ativo').count(),
                    "total_transportadoras": db.session.query(Transportadora).count(),
                    "transportadoras_freteiros": db.session.query(Transportadora).filter(Transportadora.freteiro == True).count(),
                    "total_pedidos": db.session.query(Pedido).count(),
                },
                "fretes_recentes": [
                    {
                        "id": f.id,
                        "cliente": f.nome_cliente,
                        "uf_destino": f.uf_destino,
                        "valor": float(f.valor_cotado or 0),
                        "peso": float(f.peso_total or 0),
                        "status": f.status,
                        "data": f.criado_em.isoformat() if f.criado_em else None
                    }
                    for f in db.session.query(Frete).order_by(Frete.criado_em.desc()).limit(5).all()
                ],
                "transportadoras_ativas": [
                    {
                        "id": t.id,
                        "razao_social": t.razao_social,
                        "cidade": t.cidade,
                        "uf": t.uf,
                        "freteiro": t.freteiro,
                        "optante": t.optante
                    }
                    for t in db.session.query(Transportadora).limit(5).all()
                ]
            }
            
            return contexto
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar contexto: {e}")
            return {"erro": "Contexto não disponível", "timestamp": datetime.now().isoformat()}
    
    def _get_tools_description(self) -> str:
        """Descrição das ferramentas disponíveis"""
        return """
FERRAMENTAS DISPONÍVEIS:
1. consultar_fretes - Busca fretes por cliente, UF, status
2. consultar_embarques - Lista embarques ativos e pendentes  
3. consultar_transportadoras - Lista empresas e freteiros cadastrados
4. consultar_pedidos_cliente - Pedidos específicos por cliente
5. status_sistema - Métricas gerais e estatísticas
6. analisar_tendencias - Análise de padrões e tendências
7. detectar_anomalias - Identificação de problemas
8. otimizar_rotas - Sugestões de otimização
9. previsao_custos - Previsões financeiras
10. exportar_dados - Geração de relatórios
11. monitoramento_entregas - Status de entregas
"""
    
    def _fallback_simulado(self, consulta: str) -> str:
        """Fallback quando Claude real não está disponível"""
        return f"""🤖 **MODO SIMULADO** (Claude Real não disponível)

Consulta recebida: "{consulta}"

⚠️ **Para ativar Claude REAL:**
1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente
2. Obtenha chave em: https://console.anthropic.com/
3. Reinicie o sistema

💡 **Com Claude Real você terá:**
- Inteligência igual ao Claude Desktop
- Análises complexas e insights profundos
- Respostas contextuais e precisas
- Capacidade de raciocínio avançado

🔄 **Por enquanto, usando sistema básico...**"""

# Instância global
claude_integration = ClaudeRealIntegration()

def processar_com_claude_real(consulta: str, user_context: Dict = None) -> str:
    """Função pública para processar com Claude real"""
    return claude_integration.processar_consulta_real(consulta, user_context) 