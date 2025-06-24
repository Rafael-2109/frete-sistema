"""
🧠 MAPEAMENTO SEMÂNTICO REAL - Linguagem Natural → Campos Reais do Banco
Sistema que traduz termos do usuário para campos REAIS do sistema
"""

import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)

class MapeamentoSemanticoReal:
    """Mapeia linguagem natural para campos REAIS do banco"""
    
    def __init__(self):
        """Inicializa mapeamento semântico com dados REAIS"""
        # Buscar dados REAIS do sistema primeiro
        self.campos_reais = self._buscar_campos_reais_do_sistema()
        self.mapeamentos = self._criar_mapeamentos_com_dados_reais()
        self.relacionamentos = self._criar_relacionamentos_reais()
        logger.info("🧠 Mapeamento Semântico inicializado com dados REAIS")
    
    def _buscar_campos_reais_do_sistema(self) -> Dict[str, Any]:
        """Busca campos REAIS do sistema usando sistema_real_data"""
        try:
            from .sistema_real_data import get_sistema_real_data
            sistema_real = get_sistema_real_data()
            
            # Buscar modelos reais do banco
            modelos_reais = sistema_real.buscar_todos_modelos_reais()
            
            logger.info(f"✅ Campos reais carregados de {len(modelos_reais)} modelos")
            return modelos_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos reais: {e}")
            return {}
    
    def _criar_mapeamentos_com_dados_reais(self) -> Dict[str, Dict[str, Any]]:
        """Cria mapeamentos usando APENAS campos reais do sistema"""
        
        if not self.campos_reais:
            logger.warning("⚠️ Nenhum campo real encontrado - mapeamento será limitado")
            return {}
        
        mapeamentos = {}
        
        # Para cada modelo real, criar mapeamentos baseados nos campos reais
        for nome_modelo, info_modelo in self.campos_reais.items():
            if 'campos' not in info_modelo:
                continue
                
            campos_reais = info_modelo['campos']
            
            # Mapear cada campo real
            for campo_info in campos_reais:
                nome_campo = campo_info['nome']
                tipo_campo = campo_info['tipo']
                
                # Gerar termos naturais baseados no nome do campo
                termos_naturais = self._gerar_termos_naturais_para_campo(nome_campo, nome_modelo)
                
                if termos_naturais:  # Só adicionar se gerou termos
                    chave_mapeamento = f"{nome_modelo.lower()}_{nome_campo}"
                    
                    mapeamentos[chave_mapeamento] = {
                        'modelo': nome_modelo,
                        'campo_principal': nome_campo,
                        'campo_busca': nome_campo,  # Campo real do banco
                        'tipo': self._normalizar_tipo_sqlalchemy(tipo_campo),
                        'termos_naturais': termos_naturais
                    }
        
        logger.info(f"✅ {len(mapeamentos)} mapeamentos criados com campos REAIS")
        return mapeamentos
    
    def _gerar_termos_naturais_para_campo(self, nome_campo: str, nome_modelo: str) -> List[str]:
        """Gera termos naturais para um campo baseado no seu nome REAL"""
        
        termos = []
        
        # Adicionar o nome limpo do campo (básico)
        nome_limpo = nome_campo.replace('_', ' ')
        termos.append(nome_limpo)
        
        # Gerar variações baseadas no padrão do nome do campo
        if '_' in nome_campo:
            # Campo composto (ex: data_embarque -> "data de embarque", "data do embarque")
            partes = nome_campo.split('_')
            if len(partes) == 2:
                termo_de = f"{partes[0]} de {partes[1]}"
                termo_do = f"{partes[0]} do {partes[1]}"
                termos.extend([termo_de, termo_do])
                
                # Variações especiais por tipo
                if partes[0] == 'data':
                    termos.append(f"quando {partes[1]}")
                elif partes[0] == 'numero' or partes[0] == 'num':
                    termos.extend([f"número de {partes[1]}", f"número do {partes[1]}"])
                elif partes[0] == 'valor':
                    termos.extend([f"preço de {partes[1]}", f"preço do {partes[1]}"])
        
        # Padrões específicos baseados no início do campo
        if nome_campo.startswith('num_') or nome_campo.startswith('numero_'):
            base = nome_campo.replace('num_', '').replace('numero_', '')
            termos.extend([f"número {base}", f"numero {base}", f"id {base}"])
            
        elif nome_campo.startswith('data_'):
            base = nome_campo.replace('data_', '')
            termos.extend([f"data {base}", f"quando {base}"])
            
        elif nome_campo.startswith('valor_'):
            base = nome_campo.replace('valor_', '')
            termos.extend([f"valor {base}", f"preço {base}", f"montante {base}"])
            
        elif nome_campo.startswith('status_'):
            base = nome_campo.replace('status_', '')
            termos.extend([f"status {base}", f"situação {base}", f"estado {base}"])
        
        # Adicionar variações contextuais por modelo
        if nome_modelo == 'Pedido':
            if any(x in nome_campo for x in ['cliente', 'raz_social']):
                termos.extend(['cliente', 'empresa', 'razão social'])
        elif nome_modelo == 'EntregaMonitorada':
            if nome_campo == 'numero_nf':
                termos.extend(['nf', 'nota fiscal', 'número da nota'])
            elif nome_campo == 'cliente':
                termos.extend(['destinatário', 'cliente destino'])
        
        # Remover duplicatas mantendo ordem
        termos_unicos = []
        for termo in termos:
            if termo not in termos_unicos:
                termos_unicos.append(termo)
        
        return termos_unicos
    
    def _normalizar_tipo_sqlalchemy(self, tipo_sqlalchemy: str) -> str:
        """Normaliza tipos do SQLAlchemy para tipos simples"""
        
        tipo_lower = str(tipo_sqlalchemy).lower()
        
        if 'varchar' in tipo_lower or 'text' in tipo_lower or 'string' in tipo_lower:
            return 'string'
        elif 'integer' in tipo_lower or 'bigint' in tipo_lower:
            return 'integer'
        elif 'decimal' in tipo_lower or 'numeric' in tipo_lower or 'float' in tipo_lower:
            return 'decimal'
        elif 'boolean' in tipo_lower:
            return 'boolean'
        elif 'date' in tipo_lower:
            return 'datetime' if 'datetime' in tipo_lower or 'timestamp' in tipo_lower else 'date'
        else:
            return 'string'  # Fallback
    
    def _criar_relacionamentos_reais(self) -> Dict[str, Dict[str, Any]]:
        """Cria relacionamentos baseados nos dados reais dos modelos"""
        
        relacionamentos = {}
        
        # Buscar relacionamentos reais dos modelos
        for nome_modelo, info_modelo in self.campos_reais.items():
            if 'relacionamentos' not in info_modelo:
                continue
                
            for rel_info in info_modelo['relacionamentos']:
                nome_rel = rel_info['nome']
                modelo_relacionado = rel_info['modelo_relacionado']
                
                chave_rel = f"{nome_modelo}_para_{modelo_relacionado}".lower()
                
                relacionamentos[chave_rel] = {
                    'origem': nome_modelo,
                    'destino': modelo_relacionado,
                    'campo_relacionamento': nome_rel,
                    'tipo': rel_info['tipo']
                }
        
        logger.info(f"✅ {len(relacionamentos)} relacionamentos reais mapeados")
        return relacionamentos
    
    def mapear_termo_natural(self, termo: str) -> List[Dict[str, Any]]:
        """
        Mapeia termo em linguagem natural para campos do banco
        
        Args:
            termo: Termo em linguagem natural (ex: "número do pedido")
            
        Returns:
            Lista de mapeamentos possíveis
        """
        termo_lower = termo.lower().strip()
        mapeamentos_encontrados = []
        
        # Buscar correspondências em todos os mapeamentos
        for chave, mapeamento in self.mapeamentos.items():
            for termo_natural in mapeamento['termos_naturais']:
                
                # Correspondência exata (prioridade alta)
                if termo_natural.lower() == termo_lower:
                    mapeamentos_encontrados.append({
                        'chave': chave,
                        'modelo': mapeamento['modelo'],
                        'campo': mapeamento['campo_principal'],
                        'campo_busca': mapeamento['campo_busca'],
                        'tipo': mapeamento['tipo'],
                        'confianca': 100,
                        'termo_original': termo,
                        'termo_mapeado': termo_natural
                    })
                
                # Correspondência parcial (prioridade menor)
                elif termo_lower in termo_natural.lower() or termo_natural.lower() in termo_lower:
                    confianca = 70  # Correspondência parcial
                    mapeamentos_encontrados.append({
                        'chave': chave,
                        'modelo': mapeamento['modelo'],
                        'campo': mapeamento['campo_principal'],
                        'campo_busca': mapeamento['campo_busca'],
                        'tipo': mapeamento['tipo'],
                        'confianca': confianca,
                        'termo_original': termo,
                        'termo_mapeado': termo_natural
                    })
        
        # Ordenar por confiança e remover duplicatas
        mapeamentos_encontrados.sort(key=lambda x: x['confianca'], reverse=True)
        
        # Remover duplicatas por campo
        mapeamentos_unicos = []
        campos_vistos = set()
        for mapeamento in mapeamentos_encontrados:
            chave_unica = f"{mapeamento['modelo']}_{mapeamento['campo']}"
            if chave_unica not in campos_vistos:
                campos_vistos.add(chave_unica)
                mapeamentos_unicos.append(mapeamento)
        
        logger.info(f"🔍 Mapeamento '{termo}': {len(mapeamentos_unicos)} correspondências")
        
        return mapeamentos_unicos[:5]  # Máximo 5 resultados
    
    def gerar_prompt_mapeamento(self) -> str:
        """Gera prompt explicando mapeamentos para Claude"""
        
        if not self.mapeamentos:
            return "⚠️ **NENHUM MAPEAMENTO DISPONÍVEL** - Campos reais não foram carregados"
        
        prompt = """🧠 **MAPEAMENTO SEMÂNTICO REAL - Linguagem Natural → Campos do Banco**

Quando o usuário mencionar estes termos, use os campos correspondentes do banco:

"""
        
        # Agrupar por modelo
        modelos_agrupados = {}
        for chave, mapeamento in self.mapeamentos.items():
            modelo = mapeamento['modelo']
            if modelo not in modelos_agrupados:
                modelos_agrupados[modelo] = []
            modelos_agrupados[modelo].append(mapeamento)
        
        for modelo, mapeamentos_modelo in modelos_agrupados.items():
            prompt += f"**{modelo}** (Tabela Real):\n"
            for mapeamento in mapeamentos_modelo[:10]:  # Máximo 10 por modelo
                campo = mapeamento['campo_busca']
                termos = ', '.join(mapeamento['termos_naturais'][:3])  # Primeiros 3 termos
                if len(mapeamento['termos_naturais']) > 3:
                    termos += "..."
                prompt += f"• '{termos}' → **{campo}** ({mapeamento['tipo']})\n"
            
            if len(mapeamentos_modelo) > 10:
                prompt += f"... e mais {len(mapeamentos_modelo) - 10} campos\n"
            prompt += "\n"
        
        prompt += f"""
📊 **RELACIONAMENTOS REAIS**: {len(self.relacionamentos)} relacionamentos mapeados

🎯 **INSTRUÇÕES CRÍTICAS**:
1. Use APENAS os campos EXATOS listados acima
2. NUNCA invente campos que não estão na lista
3. Se termo não estiver mapeado, pergunte esclarecimento
4. Todos os campos acima são REAIS do banco PostgreSQL

✅ **DADOS 100% REAIS**: {len(self.mapeamentos)} mapeamentos criados a partir do banco real"""

        return prompt

# Instância global
mapeamento_semantico_real = MapeamentoSemanticoReal()

def get_mapeamento_semantico_real() -> MapeamentoSemanticoReal:
    """Retorna instância do mapeamento semântico real"""
    return mapeamento_semantico_real 