"""
🔍 VALIDADOR DE DADOS REAIS
Sistema que garante que Claude use apenas dados verdadeiros do sistema
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from app import db

logger = logging.getLogger(__name__)

class DataValidator:
    """Validador que garante uso exclusivo de dados reais"""
    
    def __init__(self):
        """Inicializa validador com dados reais do sistema"""
        self.clientes_reais = self._carregar_clientes_reais()
        self.campos_validados = self._definir_campos_banco()
        self.valores_proibidos = self._definir_valores_proibidos()
    
    def _carregar_clientes_reais(self) -> List[str]:
        """Carrega lista de clientes reais do banco de dados"""
        try:
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            # Buscar clientes únicos das entregas
            clientes_db = db.session.query(RelatorioFaturamentoImportado.nome_cliente).distinct().all()
            clientes_reais = [cliente[0] for cliente in clientes_db if cliente[0]]
            
            logger.info(f"✅ Carregados {len(clientes_reais)} clientes reais do banco")
            return clientes_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar clientes reais: {e}")
            # Fallback para clientes conhecidos
            return ['Assai', 'Atacadão', 'Carrefour', 'Tenda', 'Beirao da Serra', 'Walmart', 'Mateus', 'Fort']
    
    def _definir_campos_banco(self) -> Dict[str, List[str]]:
        """Define campos corretos de cada modelo"""
        return {
            'EntregaMonitorada': [
                'id', 'numero_nf', 'cliente', 'destino', 'municipio', 'uf',
                'transportadora', 'vendedor', 'observacao_operacional',
                'status_finalizacao', 'entregue', 'pendencia_financeira',
                'data_embarque', 'data_entrega_prevista', 'data_hora_entrega_realizada',
                'valor_nf', 'lead_time', 'criado_em'
            ],
            'Pedido': [
                'id', 'num_pedido', 'raz_social_red', 'cnpj_cpf',
                'nome_cidade', 'cod_uf', 'valor_saldo_total', 'peso_total',
                'expedicao', 'agendamento', 'protocolo', 'nf',
                'cotacao_id', 'status_calculado', 'transportadora'
            ],
            'AgendamentoEntrega': [
                'id', 'entrega_id', 'protocolo_agendamento',
                'forma_agendamento', 'contato_agendamento',
                'data_agendada', 'hora_agendada', 'status',
                'criado_em', 'observacoes_confirmacao'
            ]
        }
    
    def _definir_valores_proibidos(self) -> Dict[str, List[str]]:
        """Define valores que NUNCA devem aparecer nas respostas"""
        return {
            'campos_incorretos': [
                'data_entrega_realizada',  # Correto: data_hora_entrega_realizada
                'status',  # Correto: status_finalizacao
                'username',  # Correto: nome
                'data_criacao'  # Correto: criado_em
            ],
            'valores_inventados': [
                'dados ficticios', 'exemplo', 'simulado', 'teste',
                'hipotetico', 'generico', 'mockup', 'demo'
            ]
        }
    
    def validar_resposta_claude(self, resposta: str) -> Dict[str, Any]:
        """
        Valida resposta do Claude para garantir uso apenas de dados reais
        
        Returns:
            Dict com resultado da validação e sugestões
        """
        resultado = {
            'valida': True,
            'problemas': [],
            'sugestoes': [],
            'pontuacao': 100
        }
        
        resposta_lower = resposta.lower()
        
        # 1. Verificar se usa apenas clientes reais (validação dinâmica)
        # Se menciona cliente que não está na lista real, é problema
        palavras_resposta = resposta_lower.split()
        for palavra in palavras_resposta:
            if len(palavra) > 4:  # Palavras grandes que podem ser nomes de clientes
                # Verificar se palavra parece ser nome de cliente mas não está na lista real
                cliente_encontrado = False
                for cliente_real in self.clientes_reais:
                    if palavra in cliente_real.lower():
                        cliente_encontrado = True
                        break
                
                # Se parece ser nome de empresa mas não está nos clientes reais
                if any(indicador in palavra for indicador in ['ltda', 'sa', 'supermercado', 'loja', 'mercado', 'atacado']):
                    if not cliente_encontrado:
                        resultado['problemas'].append(f"⚠️ Possível cliente não real mencionado: {palavra}")
                        resultado['pontuacao'] -= 10
        
        # 2. Verificar campos incorretos
        for campo_incorreto in self.valores_proibidos['campos_incorretos']:
            if campo_incorreto in resposta_lower:
                resultado['valida'] = False
                resultado['problemas'].append(f"❌ Campo incorreto usado: {campo_incorreto}")
                
                # Sugerir campo correto
                if campo_incorreto == 'data_entrega_realizada':
                    resultado['sugestoes'].append("✅ Use: data_hora_entrega_realizada")
                elif campo_incorreto == 'status':
                    resultado['sugestoes'].append("✅ Use: status_finalizacao")
                elif campo_incorreto == 'username':
                    resultado['sugestoes'].append("✅ Use: nome")
                
                resultado['pontuacao'] -= 15
        
        # 3. Verificar valores inventados
        for valor_inventado in self.valores_proibidos['valores_inventados']:
            if valor_inventado in resposta_lower:
                resultado['valida'] = False
                resultado['problemas'].append(f"❌ Valor inventado detectado: {valor_inventado}")
                resultado['sugestoes'].append("✅ Use apenas dados reais fornecidos no contexto")
                resultado['pontuacao'] -= 20
        
        # 4. Verificar se menciona dados específicos (positivo)
        indicadores_dados_reais = [
            'número nf', 'data embarque', 'transportadora', 'vendedor',
            'protocolo', 'valor nf', 'município', 'status finalizacao'
        ]
        
        dados_reais_mencionados = 0
        for indicador in indicadores_dados_reais:
            if indicador in resposta_lower:
                dados_reais_mencionados += 1
        
        if dados_reais_mencionados >= 3:
            resultado['sugestoes'].append("✅ Boa referência a dados específicos do sistema")
        else:
            resultado['problemas'].append("⚠️ Resposta muito genérica - incluir mais dados específicos")
            resultado['pontuacao'] -= 10
        
        # 5. Verificar se diferencia Assai de Atacadão (crítico)
        if 'assai' in resposta_lower and 'atacadão' in resposta_lower:
            # Verificar se não os confunde
            if 'assai atacadão' in resposta_lower or 'atacadão assai' in resposta_lower:
                resultado['valida'] = False
                resultado['problemas'].append("❌ CRÍTICO: Confundindo Assai com Atacadão")
                resultado['sugestoes'].append("✅ CRÍTICO: Assai ≠ Atacadão - são concorrentes diferentes")
                resultado['pontuacao'] -= 30
        
        # Ajustar pontuação final
        resultado['pontuacao'] = max(0, min(100, resultado['pontuacao']))
        
        return resultado
    
    def validar_query_sql(self, query_sql: str) -> Dict[str, Any]:
        """Valida queries SQL para garantir uso de campos corretos"""
        resultado = {
            'valida': True,
            'problemas': [],
            'sugestoes': []
        }
        
        query_lower = query_sql.lower()
        
        # Verificar campos incorretos em queries
        mapeamento_campos = {
            'data_entrega_realizada': 'data_hora_entrega_realizada',
            'cliente.nome': 'cliente',
            'username': 'nome',
            'status': 'status_finalizacao'
        }
        
        for campo_incorreto, campo_correto in mapeamento_campos.items():
            if campo_incorreto in query_lower:
                resultado['valida'] = False
                resultado['problemas'].append(f"❌ Query com campo incorreto: {campo_incorreto}")
                resultado['sugestoes'].append(f"✅ Use: {campo_correto}")
        
        return resultado
    
    def sugerir_dados_contexto(self, tipo_consulta: str) -> Dict[str, Any]:
        """Sugere quais dados carregar baseado no tipo de consulta"""
        sugestoes = {
            'entregas': {
                'tabelas': ['EntregaMonitorada', 'AgendamentoEntrega'],
                'campos_essenciais': [
                    'numero_nf', 'cliente', 'status_finalizacao',
                    'data_embarque', 'data_entrega_prevista', 'data_hora_entrega_realizada',
                    'transportadora', 'vendedor', 'valor_nf'
                ],
                'relacionamentos': ['AgendamentoEntrega.entrega_id = EntregaMonitorada.id']
            },
            'pedidos': {
                'tabelas': ['Pedido'],
                'campos_essenciais': [
                    'num_pedido', 'raz_social_red', 'status_calculado',
                    'valor_saldo_total', 'expedicao', 'agendamento', 'nf'
                ],
                'relacionamentos': []
            },
            'fretes': {
                'tabelas': ['Frete', 'DespesaExtra'],
                'campos_essenciais': [
                    'numero_cte', 'valor_frete', 'status_aprovacao',
                    'transportadora_id', 'data_embarque'
                ],
                'relacionamentos': []
            }
        }
        
        return sugestoes.get(tipo_consulta, sugestoes['entregas'])
    
    def gerar_relatorio_validacao(self, validacoes: List[Dict]) -> str:
        """Gera relatório consolidado de validações"""
        if not validacoes:
            return "✅ **NENHUMA VALIDAÇÃO EXECUTADA**"
        
        total_validacoes = len(validacoes)
        validacoes_ok = len([v for v in validacoes if v['valida']])
        taxa_sucesso = (validacoes_ok / total_validacoes) * 100
        
        problemas_frequentes = {}
        for validacao in validacoes:
            for problema in validacao.get('problemas', []):
                problemas_frequentes[problema] = problemas_frequentes.get(problema, 0) + 1
        
        relatorio = f"""📊 **RELATÓRIO DE VALIDAÇÃO DE DADOS**

✅ **Taxa de Sucesso**: {taxa_sucesso:.1f}% ({validacoes_ok}/{total_validacoes})
📈 **Pontuação Média**: {sum(v.get('pontuacao', 0) for v in validacoes) / total_validacoes:.1f}/100

"""
        
        if problemas_frequentes:
            relatorio += "⚠️ **PROBLEMAS MAIS FREQUENTES**:\n"
            for problema, frequencia in sorted(problemas_frequentes.items(), key=lambda x: x[1], reverse=True)[:5]:
                relatorio += f"• {problema} ({frequencia}x)\n"
        
        if taxa_sucesso < 80:
            relatorio += """
🚨 **AÇÃO NECESSÁRIA**:
Sistema apresenta muitos dados incorretos. Revisar system prompt e validar sources.
"""
        else:
            relatorio += """
✅ **SISTEMA SAUDÁVEL**:
Dados sendo utilizados corretamente na maioria dos casos.
"""
        
        return relatorio

# Instância global
data_validator = DataValidator()

def get_data_validator() -> DataValidator:
    """Retorna instância do validador de dados"""
    return data_validator 