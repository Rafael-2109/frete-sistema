#!/usr/bin/env python3
"""
Integração Claude REAL - API Anthropic
Sistema que usa o Claude verdadeiro ao invés de simulação
"""

import os
import anthropic
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from flask_login import current_user

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
        
        # Cache para evitar queries repetitivas
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos
        
        # System prompt PODEROSO para Claude real
        self.system_prompt = """Você é Claude integrado ao Sistema de Fretes de uma INDÚSTRIA QUE FATURA R$ 200 MILHÕES/ANO. 

CONTEXTO EMPRESARIAL:
- Sistema crítico de gestão de fretes
- Volume alto de operações
- Precisão é fundamental para tomada de decisão

IMPORTANTE - DIFERENCIAÇÃO DE CLIENTES:
🏢 **ATACADOS** (múltiplos clientes): "Total Atacado", "Bento Atacado", "ATR Atacado", "MIKRO ATACADO E DISTRIBUIDOR"
🎯 **ATACADÃO** (cliente específico): Refere-se especificamente ao cliente "Atacadão"
🏪 **FILIAIS**: "Atacadão 154", "Atacadão 183", "Assai LJ 189", "Assai LJ 315"

DIFERENÇA CONCEITUAL NO SISTEMA:
🚚 **FRETES** = Cotações, contratos de transporte, valores, aprovações
📦 **ENTREGAS** = Monitoramento pós-embarque, status de entrega, canhotos, datas realizadas
🚛 **EMBARQUES** = Despachos, envios, movimentação física

FLUXO DE PEDIDOS:
1. **ABERTO**: Sem cotação, tem data_expedicao (previsão), data_agenda, protocolo_agendamento
2. **COTADO**: Com embarques, data_embarque_prevista, data_agenda, protocolo_agendamento  
3. **FATURADO**: Procurar num_pedido → RelatorioFaturamentoImportado.origem → numero_nf → EntregaMonitorada

DADOS DISPONÍVEIS EM CONTEXTO:
{dados_contexto_especifico}

SUAS CAPACIDADES AVANÇADAS:
- Análise inteligente de dados reais
- Insights preditivos e recomendações estratégicas
- Detecção de padrões e anomalias
- Cálculos de performance automatizados
- Comparações temporais flexíveis

INSTRUÇÕES CRÍTICAS:
1. **PRECISÃO ABSOLUTA** - Dados incorretos custam milhões
2. **CONTEXTO ESPECÍFICO** - Se perguntou sobre Atacadão, foque no Atacadão
3. **ANÁLISE TEMPORAL** - Default 7 dias, mas aceite personalizações (30, 60 dias, comparações)
4. **MÉTRICAS CALCULADAS** - Inclua % entregas no prazo, atrasos médios, comparações
5. **VENDEDORES** - Mostre apenas clientes que têm permissão
6. **INTELIGÊNCIA CONTEXTUAL** - Diferencie "atacados" de "Atacadão" de "filiais"

EXEMPLOS DE INTERPRETAÇÃO:
- "Entregas dos atacados" → Todos clientes com "atacado" no nome
- "Entregas do Atacadão" → Cliente específico "Atacadão"  
- "Atacadão 154" → Filial específica do Atacadão
- "Como estão as entregas?" → Últimos 7 dias, oferecer outros períodos

Responda sempre em português brasileiro com precisão industrial."""
    
    def processar_consulta_real(self, consulta: str, user_context: Dict = None) -> str:
        """Processa consulta usando Claude REAL com contexto inteligente"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
        try:
            # Analisar consulta para contexto inteligente
            contexto_analisado = self._analisar_consulta(consulta)
            
            # Carregar dados específicos baseados na análise
            dados_contexto = self._carregar_contexto_inteligente(contexto_analisado)
            
            # Preparar mensagens para Claude real
            messages = [
                {
                    "role": "user", 
                    "content": f"""CONSULTA DO USUÁRIO: {consulta}

ANÁLISE DA CONSULTA:
{json.dumps(contexto_analisado, indent=2, ensure_ascii=False)}

DADOS ESPECÍFICOS CARREGADOS:
{json.dumps(dados_contexto, indent=2, ensure_ascii=False)}

CONTEXTO DO USUÁRIO:
{json.dumps(user_context or {}, indent=2, ensure_ascii=False)}

Por favor, analise a consulta e forneça uma resposta inteligente, precisa e acionável usando os dados específicos carregados para esta consulta."""
                }
            ]
            
            # Chamar Claude REAL (agora Claude 4 Sonnet!)
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
                max_tokens=4000,
                temperature=0.1,  # Determinístico para dados críticos
                system=self.system_prompt.format(
                    dados_contexto_especifico=self._descrever_contexto_carregado(contexto_analisado)
                ),
                messages=messages
            )
            
            resultado = response.content[0].text
            
            # Log da interação
            logger.info(f"✅ Claude REAL (4.0) processou: '{consulta[:50]}...'")
            
            return f"""🤖 **CLAUDE 4 SONNET REAL** (Industrial R$ 200MM/ano)

{resultado}

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) - Modelo mais avançado disponível
🎯 **Contexto:** {contexto_analisado.get('tipo_consulta', 'Geral').title()}
📊 **Dados:** {contexto_analisado.get('periodo_dias', 7)} dias | {contexto_analisado.get('registros_carregados', 0)} registros
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Modo:** IA Real Industrial"""
            
        except Exception as e:
            logger.error(f"❌ Erro no Claude real: {e}")
            return self._fallback_simulado(consulta)
    
    def _analisar_consulta(self, consulta: str) -> Dict[str, Any]:
        """Analisa a consulta para determinar contexto específico"""
        consulta_lower = consulta.lower()
        
        analise = {
            "consulta_original": consulta,
            "timestamp_analise": datetime.now().isoformat(),
            "tipo_consulta": "geral",
            "cliente_especifico": None,
            "periodo_dias": 7,  # Default 7 dias
            "filtro_geografico": None,
            "foco_dados": [],
            "metricas_solicitadas": []
        }
        
        # ANÁLISE DE CLIENTE ESPECÍFICO
        if "atacadão" in consulta_lower and not re.search(r"atacad[oa]s", consulta_lower):
            analise["cliente_especifico"] = "Atacadão"
            analise["tipo_consulta"] = "cliente_especifico"
            
            # Verificar se é filial específica
            filial_match = re.search(r"atacadão\s*(\d+)", consulta_lower)
            if filial_match:
                analise["filial"] = filial_match.group(1)
                analise["cliente_especifico"] = f"Atacadão {filial_match.group(1)}"
        
        elif "assai" in consulta_lower:
            analise["cliente_especifico"] = "Assai"
            analise["tipo_consulta"] = "cliente_especifico"
            
            # Verificar filial Assai
            filial_match = re.search(r"assai\s*(?:lj\s*)?(\d+)", consulta_lower)
            if filial_match:
                analise["filial"] = filial_match.group(1)
                analise["cliente_especifico"] = f"Assai LJ {filial_match.group(1)}"
                
        elif re.search(r"atacad[oa]s", consulta_lower):
            analise["tipo_consulta"] = "grupo_atacados"
            analise["cliente_especifico"] = "GRUPO_ATACADOS"
        
        # ANÁLISE TEMPORAL
        if re.search(r"(\d+)\s*dias?", consulta_lower):
            dias_match = re.search(r"(\d+)\s*dias?", consulta_lower)
            analise["periodo_dias"] = int(dias_match.group(1))
        elif "30 dias" in consulta_lower or "mês" in consulta_lower:
            analise["periodo_dias"] = 30
        elif "60 dias" in consulta_lower or "2 meses" in consulta_lower:
            analise["periodo_dias"] = 60
        elif "semana" in consulta_lower:
            analise["periodo_dias"] = 7
            
        # ANÁLISE GEOGRÁFICA
        ufs = ["sp", "rj", "mg", "rs", "pr", "sc", "go", "df", "ba", "pe"]
        for uf in ufs:
            if f" {uf}" in consulta_lower or f" {uf.upper()}" in consulta:
                analise["filtro_geografico"] = uf.upper()
                analise["tipo_consulta"] = "geografico"
                break
        
        # ANÁLISE DE FOCO DOS DADOS
        if "entrega" in consulta_lower:
            analise["foco_dados"].append("entregas_monitoradas")
        if "frete" in consulta_lower:
            analise["foco_dados"].append("fretes")
        if "embarque" in consulta_lower:
            analise["foco_dados"].append("embarques")
        if "pedido" in consulta_lower:
            analise["foco_dados"].append("pedidos")
            
        # Se não especificou, usar padrão baseado na consulta
        if not analise["foco_dados"]:
            if any(palavra in consulta_lower for palavra in ["como está", "status", "situação"]):
                analise["foco_dados"] = ["entregas_monitoradas", "embarques"]
            else:
                analise["foco_dados"] = ["entregas_monitoradas"]
        
        # MÉTRICAS SOLICITADAS
        if any(palavra in consulta_lower for palavra in ["prazo", "atraso", "pontualidade"]):
            analise["metricas_solicitadas"].append("performance_prazo")
        if any(palavra in consulta_lower for palavra in ["comparar", "comparação", "tendência"]):
            analise["metricas_solicitadas"].append("comparacao_temporal")
        if "média" in consulta_lower:
            analise["metricas_solicitadas"].append("medias")
            
        return analise
    
    def _carregar_contexto_inteligente(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega dados específicos baseados na análise da consulta"""
        try:
            from app import db
            from app.fretes.models import Frete
            from app.embarques.models import Embarque
            from app.transportadoras.models import Transportadora
            from app.pedidos.models import Pedido
            from app.monitoramento.models import EntregaMonitorada
            from app.faturamento.models import RelatorioFaturamentoImportado
            from sqlalchemy import func, and_, or_
            
            # Data limite baseada na análise
            data_limite = datetime.now() - timedelta(days=analise.get("periodo_dias", 7))
            
            contexto = {
                "analise_aplicada": analise,
                "timestamp": datetime.now().isoformat(),
                "registros_carregados": 0,
                "dados_especificos": {}
            }
            
            # FILTROS BASEADOS NO USUÁRIO (VENDEDOR)
            filtros_usuario = self._obter_filtros_usuario()
            
            # CARREGAR DADOS ESPECÍFICOS POR FOCO
            if "entregas_monitoradas" in analise["foco_dados"]:
                query_entregas = db.session.query(EntregaMonitorada).filter(
                    EntregaMonitorada.data_embarque >= data_limite
                )
                
                # Aplicar filtro de cliente específico
                if analise.get("cliente_especifico"):
                    if analise["cliente_especifico"] == "GRUPO_ATACADOS":
                        query_entregas = query_entregas.filter(
                            EntregaMonitorada.cliente.ilike('%atacado%')
                        )
                    else:
                        query_entregas = query_entregas.filter(
                            EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%')
                        )
                
                # Aplicar filtro geográfico
                if analise.get("filtro_geografico"):
                    query_entregas = query_entregas.filter(
                        EntregaMonitorada.uf == analise["filtro_geografico"]
                    )
                
                # Aplicar filtros de usuário (vendedor)
                if filtros_usuario.get("vendedor_restricao"):
                    query_entregas = query_entregas.filter(
                        EntregaMonitorada.vendedor == filtros_usuario["vendedor"]
                    )
                
                entregas = query_entregas.order_by(EntregaMonitorada.data_embarque.desc()).limit(50).all()
                
                # Calcular métricas se solicitado
                metricas_entregas = {}
                if "performance_prazo" in analise.get("metricas_solicitadas", []):
                    metricas_entregas = self._calcular_metricas_prazo(entregas)
                
                contexto["dados_especificos"]["entregas"] = {
                    "registros": [
                        {
                            "id": e.id,
                            "numero_nf": e.numero_nf,
                            "cliente": e.cliente,
                            "uf": e.uf,
                            "municipio": e.municipio,
                            "transportadora": e.transportadora,
                            "status_finalizacao": e.status_finalizacao,
                            "data_embarque": e.data_embarque.isoformat() if e.data_embarque else None,
                            "data_entrega_prevista": e.data_entrega_prevista.isoformat() if e.data_entrega_prevista else None,
                            "data_entrega_realizada": e.data_hora_entrega_realizada.isoformat() if e.data_hora_entrega_realizada else None,
                            "entregue": e.entregue,
                            "valor_nf": float(e.valor_nf or 0),
                            "vendedor": e.vendedor,
                            "lead_time": e.lead_time
                        }
                        for e in entregas
                    ],
                    "total_registros": len(entregas),
                    "metricas": metricas_entregas
                }
                contexto["registros_carregados"] += len(entregas)
            
            # CARREGAR FRETES SE SOLICITADO
            if "fretes" in analise["foco_dados"]:
                query_fretes = db.session.query(Frete).filter(
                    Frete.criado_em >= data_limite
                )
                
                if analise.get("cliente_especifico") and analise["cliente_especifico"] != "GRUPO_ATACADOS":
                    query_fretes = query_fretes.filter(
                        Frete.nome_cliente.ilike(f'%{analise["cliente_especifico"]}%')
                    )
                
                fretes = query_fretes.order_by(Frete.criado_em.desc()).limit(30).all()
                
                contexto["dados_especificos"]["fretes"] = {
                    "registros": [
                        {
                            "id": f.id,
                            "cliente": f.nome_cliente,
                            "uf_destino": f.uf_destino,
                            "valor_cotado": float(f.valor_cotado or 0),
                            "valor_considerado": float(f.valor_considerado or 0),
                            "peso_total": float(f.peso_total or 0),
                            "status": f.status,
                            "data_criacao": f.criado_em.isoformat() if f.criado_em else None
                        }
                        for f in fretes
                    ],
                    "total_registros": len(fretes)
                }
                contexto["registros_carregados"] += len(fretes)
            
            # ESTATÍSTICAS GERAIS (CACHE)
            stats_key = f"stats_{analise.get('cliente_especifico', 'geral')}_{analise.get('periodo_dias', 7)}"
            if stats_key not in self._cache or (datetime.now().timestamp() - self._cache[stats_key]["timestamp"]) > self._cache_timeout:
                estatisticas = self._calcular_estatisticas_especificas(analise, filtros_usuario)
                self._cache[stats_key] = {
                    "data": estatisticas,
                    "timestamp": datetime.now().timestamp()
                }
            else:
                estatisticas = self._cache[stats_key]["data"]
            
            contexto["estatisticas"] = estatisticas
            
            return contexto
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar contexto inteligente: {e}")
            return {"erro": str(e), "timestamp": datetime.now().isoformat()}
    
    def _obter_filtros_usuario(self) -> Dict[str, Any]:
        """Obtém filtros específicos do usuário atual"""
        filtros = {
            "vendedor_restricao": False,
            "vendedor": None,
            "perfil": "admin"
        }
        
        try:
            if hasattr(current_user, 'vendedor') and current_user.vendedor:
                filtros["vendedor_restricao"] = True
                filtros["vendedor"] = current_user.nome
                filtros["perfil"] = "vendedor"
        except:
            pass  # Se não conseguir identificar, usar padrão admin
            
        return filtros
    
    def _calcular_metricas_prazo(self, entregas: List) -> Dict[str, Any]:
        """Calcula métricas de performance de prazo"""
        if not entregas:
            return {}
        
        total_entregas = len(entregas)
        entregas_realizadas = [e for e in entregas if e.data_hora_entrega_realizada]
        entregas_no_prazo = [
            e for e in entregas_realizadas 
            if e.data_entrega_prevista and e.data_hora_entrega_realizada 
            and e.data_hora_entrega_realizada.date() <= e.data_entrega_prevista
        ]
        
        return {
            "total_entregas": total_entregas,
            "entregas_realizadas": len(entregas_realizadas),
            "entregas_no_prazo": len(entregas_no_prazo),
            "percentual_no_prazo": round((len(entregas_no_prazo) / len(entregas_realizadas) * 100), 1) if entregas_realizadas else 0,
            "media_lead_time": round(sum(e.lead_time for e in entregas if e.lead_time) / len([e for e in entregas if e.lead_time]), 1) if any(e.lead_time for e in entregas) else None
        }
    
    def _calcular_estatisticas_especificas(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula estatísticas específicas para o contexto"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada
            from app.fretes.models import Frete
            
            data_limite = datetime.now() - timedelta(days=analise.get("periodo_dias", 7))
            
            # Base query para entregas
            query_base = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.data_embarque >= data_limite
            )
            
            # Aplicar filtros específicos
            if analise.get("cliente_especifico"):
                if analise["cliente_especifico"] == "GRUPO_ATACADOS":
                    query_base = query_base.filter(EntregaMonitorada.cliente.ilike('%atacado%'))
                else:
                    query_base = query_base.filter(EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%'))
            
            if filtros_usuario.get("vendedor_restricao"):
                query_base = query_base.filter(EntregaMonitorada.vendedor == filtros_usuario["vendedor"])
            
            total_entregas = query_base.count()
            entregas_entregues = query_base.filter(EntregaMonitorada.status_finalizacao == 'Entregue').count()
            entregas_pendentes = query_base.filter(EntregaMonitorada.status_finalizacao.in_(['Pendente', 'Em trânsito'])).count()
            
            return {
                "periodo_analisado": f"{analise.get('periodo_dias', 7)} dias",
                "total_entregas": total_entregas,
                "entregas_entregues": entregas_entregues,
                "entregas_pendentes": entregas_pendentes,
                "percentual_entregues": round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0,
                "cliente_especifico": analise.get("cliente_especifico"),
                "filtro_geografico": analise.get("filtro_geografico"),
                "restricao_vendedor": filtros_usuario.get("vendedor_restricao", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas: {e}")
            return {"erro": str(e)}
    
    def _descrever_contexto_carregado(self, analise: Dict[str, Any]) -> str:
        """Descreve o contexto carregado para o prompt"""
        descricao = []
        
        if analise.get("cliente_especifico"):
            descricao.append(f"- Dados específicos do cliente: {analise['cliente_especifico']}")
        
        if analise.get("periodo_dias"):
            descricao.append(f"- Período: Últimos {analise['periodo_dias']} dias")
        
        if analise.get("filtro_geografico"):
            descricao.append(f"- Filtro geográfico: {analise['filtro_geografico']}")
        
        if analise.get("foco_dados"):
            descricao.append(f"- Foco dos dados: {', '.join(analise['foco_dados'])}")
        
        if analise.get("metricas_solicitadas"):
            descricao.append(f"- Métricas calculadas: {', '.join(analise['metricas_solicitadas'])}")
        
        return "\n".join(descricao) if descricao else "- Dados gerais do sistema"
    
    def _get_tools_description(self) -> str:
        """Descrição das ferramentas disponíveis"""
        return """
FERRAMENTAS AVANÇADAS DISPONÍVEIS:
1. Análise contextual inteligente - Detecta automaticamente cliente, período, geografia
2. Filtros por permissão - Vendedores veem apenas seus clientes
3. Métricas calculadas - Performance, atrasos, comparações temporais
4. Cache inteligente - Estatísticas otimizadas para consultas frequentes
5. Diferenciação semântica - Distingue "atacados" vs "Atacadão" vs filiais
6. Análises temporais flexíveis - 7, 30, 60 dias ou períodos customizados
7. Correlação de dados - Liga pedidos → faturamento → monitoramento
"""
    
    def _fallback_simulado(self, consulta: str) -> str:
        """Fallback quando Claude real não está disponível"""
        return f"""🤖 **MODO SIMULADO** (Claude Real não disponível)

Consulta recebida: "{consulta}"

⚠️ **Para ativar Claude REAL:**
1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente
2. Obtenha chave em: https://console.anthropic.com/
3. Reinicie o sistema

💡 **Com Claude 4 Sonnet Real você terá:**
- Inteligência de R$ 200MM/ano industrial
- Análises contextuais precisas
- Diferenciação inteligente de clientes
- Métricas calculadas automaticamente
- Performance otimizada com cache

🔄 **Por enquanto, usando sistema básico...**"""

# Instância global
claude_integration = ClaudeRealIntegration()

def processar_com_claude_real(consulta: str, user_context: Dict = None) -> str:
    """Função pública para processar com Claude real"""
    return claude_integration.processar_consulta_real(consulta, user_context) 