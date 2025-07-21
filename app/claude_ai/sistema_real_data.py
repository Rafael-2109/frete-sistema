"""
🎯 SISTEMA DE DADOS REAIS
Busca dados VERDADEIROS do banco - ZERO invenção
"""

import logging
from typing import Dict, List, Any, Optional
from app import db
from sqlalchemy import inspect
import json

logger = logging.getLogger(__name__)

class SistemaRealData:
    """Sistema que busca dados REAIS do banco sem inventar nada"""
    
    def __init__(self):
        """Inicializa sistema de dados reais"""
        self._cache_dados = {}
        logger.info("🎯 Sistema de Dados Reais inicializado")
    
    def buscar_todos_modelos_reais(self) -> Dict[str, List[str]]:
        """Busca TODOS os modelos e campos reais do sistema"""
        try:
            # Importar TODOS os modelos do sistema
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            from app.pedidos.models import Pedido
            from app.embarques.models import Embarque, EmbarqueItem
            from app.fretes.models import Frete, DespesaExtra
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app.transportadoras.models import Transportadora
            from app.auth.models import Usuario
            from app.cotacao.models import Cotacao
            from app.financeiro.models import PendenciaFinanceiraNF
            from app.cadastros_agendamento.models import ContatoAgendamento
            from app.vinculos.models import CidadeAtendida
            from app.localidades.models import Cidade
            from app.carteira.models import CarteiraPrincipal, CarteiraCopia, ControleCruzadoSeparacao, InconsistenciaFaturamento, TipoCarga
            
            modelos_sistema = {
                'EntregaMonitorada': EntregaMonitorada,
                'AgendamentoEntrega': AgendamentoEntrega,
                'Pedido': Pedido,
                'Embarque': Embarque,
                'EmbarqueItem': EmbarqueItem,
                'Frete': Frete,
                'DespesaExtra': DespesaExtra,
                'RelatorioFaturamentoImportado': RelatorioFaturamentoImportado,
                'Transportadora': Transportadora,
                'Usuario': Usuario,
                'CotacaoFrete': Cotacao,
                'PendenciaFinanceiraNF': PendenciaFinanceiraNF,
                'ContatoAgendamento': ContatoAgendamento,
                'CidadeAtendida': CidadeAtendida,
                'Cidade': Cidade,
                'CarteiraPrincipal': CarteiraPrincipal,
                'CarteiraCopia': CarteiraCopia,
                'ControleCruzadoSeparacao': ControleCruzadoSeparacao,
                'InconsistenciaFaturamento': InconsistenciaFaturamento,
                'TipoCarga': TipoCarga,
            }
            
            campos_por_modelo = {}
            
            for nome_modelo, classe_modelo in modelos_sistema.items():
                try:
                    # Usar SQLAlchemy Inspector para pegar campos REAIS
                    inspector = inspect(classe_modelo)
                    campos_reais = []
                    
                    # Pegar todas as colunas
                    for coluna in inspector.columns:
                        campos_reais.append({
                            'nome': coluna.name,
                            'tipo': str(coluna.type),
                            'nullable': coluna.nullable,
                            'primary_key': coluna.primary_key
                        })
                    
                    # Pegar relacionamentos
                    relacionamentos = []
                    for rel_name, rel in inspector.relationships.items():
                        relacionamentos.append({
                            'nome': rel_name,
                            'tipo': 'relationship',
                            'modelo_relacionado': str(rel.mapper.class_.__name__)
                        })
                    
                    campos_por_modelo[nome_modelo] = {
                        'campos': campos_reais,
                        'relacionamentos': relacionamentos,
                        'tabela_banco': inspector.local_table.name
                    }
                    
                    logger.info(f"✅ {nome_modelo}: {len(campos_reais)} campos, {len(relacionamentos)} relacionamentos")
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao inspecionar {nome_modelo}: {e}")
                    campos_por_modelo[nome_modelo] = {'erro': str(e)}
            
            self._cache_dados['modelos'] = campos_por_modelo
            logger.info(f"✅ {len(campos_por_modelo)} modelos mapeados com dados REAIS")
            
            return campos_por_modelo
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar modelos reais: {e}")
            return {}
    
    def buscar_clientes_reais(self) -> List[str]:
        """Busca lista REAL de clientes do banco"""
        try:
            from app import create_app
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            # Garantir contexto de aplicação
            from flask import current_app
            if not current_app:
                # Se não há contexto, usar cache vazio e tentar na próxima chamada
                logger.info("🔄 Sem contexto Flask inicial - carregando dados dinamicamente")
                return []
            
            # Query REAL para buscar clientes únicos
            clientes_query = db.session.query(RelatorioFaturamentoImportado.nome_cliente).distinct()
            clientes_raw = clientes_query.filter(RelatorioFaturamentoImportado.nome_cliente.isnot(None)).all()
            
            # Extrair nomes dos clientes
            clientes_reais = [cliente[0].strip() for cliente in clientes_raw if cliente[0] and cliente[0].strip()]
            
            # Ordenar alfabeticamente
            clientes_reais.sort()
            
            logger.info(f"✅ {len(clientes_reais)} clientes REAIS encontrados no banco")
            
            # Cache dos dados reais
            self._cache_dados['clientes'] = clientes_reais
            
            return clientes_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar clientes reais: {e}")
            return []
    
    def buscar_transportadoras_reais(self) -> List[Dict[str, Any]]:
        """Busca lista REAL de transportadoras do banco"""
        try:
            from app.transportadoras.models import Transportadora
            from flask import current_app
            
            # Garantir contexto de aplicação
            if not current_app:
                logger.info("🔄 Sem contexto Flask inicial - carregando transportadoras dinamicamente")
                return []
            
            transportadoras_query = db.session.query(Transportadora).all()
            
            transportadoras_reais = []
            for transp in transportadoras_query:
                transportadoras_reais.append({
                    'id': transp.id,
                    'razao_social': transp.razao_social,
                    'cnpj': getattr(transp, 'cnpj', None),
                    'cidade': getattr(transp, 'cidade', None),
                    'uf': getattr(transp, 'uf', None),
                    'freteiro': getattr(transp, 'freteiro', False)
                })
            
            logger.info(f"✅ {len(transportadoras_reais)} transportadoras REAIS encontradas")
            self._cache_dados['transportadoras'] = transportadoras_reais
            
            return transportadoras_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar transportadoras reais: {e}")
            return []
    
    def buscar_ufs_reais(self) -> List[str]:
        """Busca lista REAL de UFs do banco"""
        try:
            from app.localidades.models import Cidade
            from flask import current_app
            
            # Garantir contexto de aplicação
            if not current_app:
                logger.info("🔄 Sem contexto Flask inicial - carregando UFs dinamicamente")
                return []
            
            ufs_query = db.session.query(Cidade.uf).distinct()
            ufs_raw = ufs_query.filter(Cidade.uf.isnot(None)).all()
            
            ufs_reais = [uf[0].strip().upper() for uf in ufs_raw if uf[0] and len(uf[0].strip()) == 2]
            ufs_reais.sort()
            
            logger.info(f"✅ {len(ufs_reais)} UFs REAIS encontradas: {ufs_reais}")
            self._cache_dados['ufs'] = ufs_reais
            
            return ufs_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar UFs reais: {e}")
            return []
    
    def buscar_vendedores_reais(self) -> List[str]:
        """Busca lista REAL de vendedores do banco"""
        try:
            from app.faturamento.models import RelatorioFaturamentoImportado
            from flask import current_app
            
            # Garantir contexto de aplicação
            if not current_app:
                logger.info("🔄 Sem contexto Flask inicial - carregando vendedores dinamicamente")
                return []
            
            vendedores_query = db.session.query(RelatorioFaturamentoImportado.vendedor).distinct()
            vendedores_raw = vendedores_query.filter(RelatorioFaturamentoImportado.vendedor.isnot(None)).all()
            
            vendedores_reais = [vend[0].strip() for vend in vendedores_raw if vend[0] and vend[0].strip()]
            vendedores_reais.sort()
            
            logger.info(f"✅ {len(vendedores_reais)} vendedores REAIS encontrados")
            self._cache_dados['vendedores'] = vendedores_reais
            
            return vendedores_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar vendedores reais: {e}")
            return []
    
    def buscar_status_reais(self) -> Dict[str, List[str]]:
        """Busca todos os status REAIS do sistema"""
        try:
            from flask import current_app
            
            # Garantir contexto de aplicação
            if not current_app:
                logger.info("🔄 Sem contexto Flask inicial - carregando status dinamicamente")
                return {}
            
            status_reais = {}
            
            # Status de EntregaMonitorada
            from app.monitoramento.models import EntregaMonitorada
            status_entregas = db.session.query(EntregaMonitorada.status_finalizacao).distinct().all()
            status_reais['entregas'] = [s[0] for s in status_entregas if s[0]]
            
            # Status de Pedidos (usando campo real do banco)
            from app.pedidos.models import Pedido
            try:
                # CORREÇÃO: usar campo 'status' real do banco, não a property 'status_calculado'
                status_pedidos = db.session.query(Pedido.status).distinct().all()
                status_reais['pedidos'] = [s[0] for s in status_pedidos if s[0]]
                logger.info(f"✅ Status de pedidos carregados: {status_reais['pedidos']}")
            except Exception as e:
                logger.warning(f"Erro ao carregar status de pedidos: {e}")
                status_reais['pedidos'] = []
            
            # Status de Embarques
            from app.embarques.models import Embarque
            status_embarques = db.session.query(Embarque.status).distinct().all()
            status_reais['embarques'] = [s[0] for s in status_embarques if s[0]]
            
            logger.info(f"✅ Status reais: {len(status_reais)} tipos encontrados")
            self._cache_dados['status'] = status_reais
            
            return status_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar status reais: {e}")
            return {}
    
    def gerar_system_prompt_real(self) -> str:
        """Gera system prompt baseado 100% em dados REAIS do sistema"""
        
        # Buscar TODOS os dados reais
        clientes_reais = self.buscar_clientes_reais()
        modelos_reais = self.buscar_todos_modelos_reais()
        transportadoras_reais = self.buscar_transportadoras_reais()
        ufs_reais = self.buscar_ufs_reais()
        vendedores_reais = self.buscar_vendedores_reais()
        status_reais = self.buscar_status_reais()
        
        # Importar mapeamento semântico
        try:
            from .mapeamento_semantico import get_mapeamento_semantico
            mapeamento = get_mapeamento_semantico()
            prompt_mapeamento = mapeamento.gerar_prompt_mapeamento()
        except ImportError:
            prompt_mapeamento = ""
        
        # Construir prompt com dados REAIS (CORRIGIDO - sem placeholders conflitantes)
        
        # Preparar dados formatados de forma segura
        clientes_lista = '\n'.join([f"  - {c}" for c in clientes_reais[:20]])
        clientes_mais = f"\n... e mais {len(clientes_reais) - 20} clientes" if len(clientes_reais) > 20 else ""
        
        transportadoras_lista = '\n'.join([f"  - {t['razao_social']}" for t in transportadoras_reais[:10]])
        transportadoras_mais = f"\n... e mais {len(transportadoras_reais) - 10} transportadoras" if len(transportadoras_reais) > 10 else ""
        
        vendedores_lista = '\n'.join([f"  - {v}" for v in vendedores_reais[:15]])
        vendedores_mais = f"\n... e mais {len(vendedores_reais) - 15} vendedores" if len(vendedores_reais) > 15 else ""
        
        # Converter status de forma segura
        status_texto = []
        for tipo, lista_status in status_reais.items():
            status_texto.append(f"  - {tipo}: {', '.join(lista_status)}")
        status_formatado = '\n'.join(status_texto)
        
        prompt = f"""VOCÊ É O ASSISTENTE IA DO SISTEMA DE FRETES COM DADOS 100% REAIS.

🏢 **CLIENTES REAIS DO SISTEMA** ({len(clientes_reais)} encontrados):
{clientes_lista}{clientes_mais}

🚛 **TRANSPORTADORAS REAIS** ({len(transportadoras_reais)} encontradas):
{transportadoras_lista}{transportadoras_mais}

🗺️ **UFs REAIS DO SISTEMA**: {', '.join(ufs_reais)}

👤 **VENDEDORES REAIS** ({len(vendedores_reais)} encontrados):
{vendedores_lista}{vendedores_mais}

📊 **STATUS REAIS POR TIPO**:
{status_formatado}

{prompt_mapeamento}

📋 **MODELOS E CAMPOS REAIS**:
"""
        
        # Adicionar informações detalhadas dos modelos
        for nome_modelo, info_modelo in modelos_reais.items():
            if isinstance(info_modelo, dict) and 'campos' in info_modelo:
                campos_info = info_modelo.get('campos', [])
                if isinstance(campos_info, list):
                    campos_nomes = [campo['nome'] for campo in campos_info if isinstance(campo, dict) and 'nome' in campo]
                    prompt += f"""
**{nome_modelo}** (Tabela: {info_modelo.get('tabela_banco', 'N/A')}):
• Campos: {', '.join(campos_nomes)}
• Relacionamentos: {len(info_modelo.get('relacionamentos', []))}"""
        
        prompt += """

🚨 **REGRAS CRÍTICAS - DADOS REAIS**:
1. Use APENAS os clientes listados acima (NUNCA invente clientes)
2. Use APENAS os campos de modelos listados acima
3. Use APENAS os status reais encontrados no sistema
4. Se não encontrar dados, diga claramente "Não encontrado no sistema"
5. NUNCA mencione clientes inexistentes (Magazine Luiza, Renner, etc.)

🎯 **INSTRUÇÕES DE USO**:
- Baseie TODAS as respostas nos dados reais fornecidos acima
- Se consulta mencionar cliente não listado, informe que não existe
- Use campos exatos dos modelos (não invente campos)
- Referencie dados específicos quando disponível

IMPORTANTE: Este prompt foi gerado automaticamente a partir dos dados REAIS do banco de dados."""

        return prompt
    
    def gerar_relatorio_dados_sistema(self) -> str:
        """Gera relatório completo dos dados reais do sistema"""
        
        clientes = self.buscar_clientes_reais()
        modelos = self.buscar_todos_modelos_reais()
        transportadoras = self.buscar_transportadoras_reais()
        ufs = self.buscar_ufs_reais()
        vendedores = self.buscar_vendedores_reais()
        status = self.buscar_status_reais()
        
        relatorio = f"""📊 **RELATÓRIO COMPLETO - DADOS REAIS DO SISTEMA**

🏢 **CLIENTES**: {len(clientes)} encontrados
• Primeiros 10: {', '.join(clientes[:10])}
• Últimos 10: {', '.join(clientes[-10:])}

🚛 **TRANSPORTADORAS**: {len(transportadoras)} encontradas
• Freteiros: {len([t for t in transportadoras if t.get('freteiro')])}
• Empresas: {len([t for t in transportadoras if not t.get('freteiro')])}

🗺️ **COBERTURA GEOGRÁFICA**: {len(ufs)} UFs
• UFs ativas: {', '.join(ufs)}

👤 **VENDEDORES**: {len(vendedores)} ativos
• Amostra: {', '.join(vendedores[:5])}

📊 **STATUS POR MÓDULO**:
• Entregas: {len(status.get('entregas', []))} status diferentes
• Pedidos: {len(status.get('pedidos', []))} status diferentes  
• Embarques: {len(status.get('embarques', []))} status diferentes

📋 **MODELOS MAPEADOS**: {len(modelos)} modelos
• Total de campos mapeados: {sum(len(m.get('campos', [])) for m in modelos.values())}
• Total de relacionamentos: {sum(len(m.get('relacionamentos', [])) for m in modelos.values())}

⚡ **RESUMO EXECUTIVO**:
Sistema com {len(clientes)} clientes reais, {len(transportadoras)} transportadoras,
cobrindo {len(ufs)} estados com {len(vendedores)} vendedores ativos.

✅ **DADOS 100% REAIS**: Todas as informações extraídas diretamente do banco PostgreSQL.
"""
        
        return relatorio
    
    def validar_cliente_existe(self, nome_cliente: str) -> bool:
        """Valida se cliente realmente existe no sistema"""
        if 'clientes' not in self._cache_dados:
            self.buscar_clientes_reais()
        
        clientes_reais = self._cache_dados.get('clientes', [])
        
        # Busca case-insensitive
        for cliente_real in clientes_reais:
            if nome_cliente.lower() in cliente_real.lower():
                return True
        
        return False
    
    def sugerir_cliente_similar(self, nome_cliente: str) -> List[str]:
        """Sugere clientes similares quando cliente não existe"""
        if 'clientes' not in self._cache_dados:
            self.buscar_clientes_reais()
        
        clientes_reais = self._cache_dados.get('clientes', [])
        sugestoes = []
        
        nome_lower = nome_cliente.lower()
        
        for cliente_real in clientes_reais:
            cliente_lower = cliente_real.lower()
            # Busca por palavras similares
            palavras_busca = nome_lower.split()
            for palavra in palavras_busca:
                if palavra in cliente_lower and len(palavra) > 2:
                    sugestoes.append(cliente_real)
                    break
        
        return list(set(sugestoes))[:5]  # Máximo 5 sugestões únicas

# Instância global
sistema_real_data = SistemaRealData()

def get_sistema_real_data() -> SistemaRealData:
    """Retorna instância do sistema de dados reais"""
    return sistema_real_data 