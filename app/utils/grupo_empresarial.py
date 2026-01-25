#!/usr/bin/env python3
"""
🏢 DETECTOR AUTOMÁTICO DE GRUPOS EMPRESARIAIS
Identifica automaticamente grupos empresariais baseado nos dados reais do sistema
VERSÃO AVANÇADA: Suporte a detecção por CNPJ + múltiplos padrões
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

class GrupoEmpresarialDetector:
    """Detector inteligente de grupos empresariais com suporte a CNPJ"""
    
    def __init__(self):
        self.grupos_manuais = self._carregar_grupos_manuais()
        self.grupos_automaticos = {}
        self._cache_analise = {}
    
    def _carregar_grupos_manuais(self) -> Dict[str, Dict[str, Any]]:
        """Carrega grupos empresariais conhecidos manualmente com detecção por CNPJ"""
        return {
            'assai': {
                'nome_grupo': 'Rede Assai (Todas as Lojas)',
                'filtro_sql': '%assai%',
                'keywords': ['assai', 'rede assai'],
                'descricao': 'Rede de atacarejo com 300+ lojas',
                'tipo': 'atacarejo',
                # PADRÃO UNIFORME: CNPJ único para toda a rede
                'cnpj_prefixos': ['06.057.223/'],  
                'metodo_deteccao': 'cnpj_uniforme_e_nome'
            },
            'atacadao': {
                'nome_grupo': 'Grupo Atacadão (Todas as Lojas)', 
                'filtro_sql': '%atacad%',
                'keywords': ['atacadao', 'atacadão', 'grupo atacadao'],
                'descricao': 'Rede de atacarejo nacional',
                'tipo': 'atacarejo',
                # PADRÃO COMPLEXO: Múltiplos CNPJs + Padrão Nome
                'cnpj_prefixos': ['75.315.333/', '00.063.960/', '93.209.765/'],
                'padrao_nome_regex': r'atacad[aã]o.*\([0-9]+',
                'metodo_deteccao': 'multiplo_cnpj_e_nome',
                'estatisticas_conhecidas': {
                    '75.315.333/': '~200 lojas',
                    '00.063.960/': '4 lojas', 
                    '93.209.765/': '~100 lojas'
                }
            },
            'tenda': {
                'nome_grupo': 'Rede Tenda (Todas as Lojas)',
                'filtro_sql': '%tenda%',
                'keywords': ['tenda', 'rede tenda'],
                'descricao': 'Rede de atacarejo regional',
                'tipo': 'atacarejo',
                # PADRÃO UNIFORME: CNPJ único para toda a rede
                'cnpj_prefixos': ['01.157.555/'], 
                'metodo_deteccao': 'cnpj_uniforme_e_nome'
            },
            'carrefour': {
                'nome_grupo': 'Grupo Carrefour (Todas as Unidades)',
                'filtro_sql': '%carrefour%', 
                'keywords': ['carrefour', 'grupo carrefour'],
                'descricao': 'Rede francesa de varejo',
                'tipo': 'supermercado',
                'cnpj_prefixos': ['45.543.915/'],  
                'metodo_deteccao': 'cnpj_uniforme_e_nome'
            },
            'mateus': {
                'nome_grupo': 'Grupo Mateus (Todas as Unidades)',
                'filtro_sql': '%mateus%',
                'keywords': ['mateus', 'grupo mateus'],
                'descricao': 'Rede nordestina',
                'tipo': 'regional',
                'cnpj_prefixos': ['03.995.515/', '23.439.441/', '59.009.691/'],
                'metodo_deteccao': 'multiplo_cnpj_e_nome',
            },
            # NOVO: Exemplo do padrão "nome uniforme + CNPJs diversos"
            'coco_bambu': {
                'nome_grupo': 'Coco Bambu (Todas as Unidades)',
                'filtro_sql': '%coco%bambu%',
                'keywords': ['coco bambu', 'coco', 'bambu'],
                'descricao': 'Rede de restaurantes',
                'tipo': 'restaurante',
                # PADRÃO ESPECIAL: Nome idêntico, CNPJs completamente diferentes
                'nome_exato': 'COCO BAMBU',
                'metodo_deteccao': 'nome_uniforme_cnpj_diversos',
                'observacao': 'Cada unidade tem CNPJ diferente mas nome idêntico'
            },
           
            'fort': {
                'nome_grupo': 'Fort Atacadista (Todas as Unidades)',
                'filtro_sql': '%fort%',
                'keywords': ['fort', 'fort atacadista', 'fort/comper'],
                'descricao': 'Atacadista regional Ceará',
                'tipo': 'regional',
                'cnpj_prefixos': ['09.477.652/'],
                'metodo_deteccao': 'cnpj_uniforme_e_nome'
            },
            'mercantil rodrigues': {
                'nome_grupo': 'Grupo Mercantil (Todas as Unidades)',
                'filtro_sql': '%mercantil rodrigues%',
                'keywords': ['mercantil rodrigues', 'grupo mercantil rodrigues', 'mercantil', 'grupo mercantil'],
                'descricao': 'Rede nordestina',
                'tipo': 'regional',
            },
            'mercadao': {
                'nome_grupo': 'Rede Mercadão (Todas as Lojas)',
                'filtro_sql': '%mercad%',
                'keywords': ['mercadao', 'mercadão', 'rede mercadao', 'rede mercadão'],
                'descricao': 'Rede de supermercados com 10+ lojas',
                'tipo': 'supermercado',
                'cnpj_prefixos': [],  # Adicionar quando descobrir CNPJs
                'metodo_deteccao': 'nome_padrao',
                'filiais_conhecidas': ['LJ 01', 'LJ 02', 'LJ 03', 'LJ 04', 'LJ 05', 'LJ 06', 'LJ 07', 'LJ 08', 'LJ 09', 'LJ 10', 'LJ 11', 'LJ 12', 'LJ 13']
            }
        }
    
    def detectar_grupo_na_consulta(self, consulta: str) -> Optional[Dict[str, Any]]:
        """Detecta se a consulta menciona um grupo empresarial"""
        consulta_lower = consulta.lower()
        
        # 1. Verificar grupos manuais primeiro
        for grupo_key, grupo_info in self.grupos_manuais.items():
            for keyword in grupo_info['keywords']:
                if keyword in consulta_lower:
                    logger.info(f"🏢 GRUPO EMPRESARIAL DETECTADO: {grupo_info['nome_grupo']}")
                    logger.info(f"📊 Tipo: {grupo_info['tipo']} | Método: {grupo_info.get('metodo_deteccao', 'nome_padrao')}")
                    
                    return {
                        'grupo_detectado': grupo_info['nome_grupo'],
                        'filtro_sql': grupo_info['filtro_sql'],
                        'tipo_deteccao': 'GRUPO_EMPRESARIAL',
                        'tipo_negocio': grupo_info['tipo'],
                        'descricao': grupo_info['descricao'],
                        'keyword_encontrada': keyword,
                        'metodo_deteccao': grupo_info.get('metodo_deteccao', 'nome_padrao'),
                        'cnpj_prefixos': grupo_info.get('cnpj_prefixos', []),
                        'estatisticas': grupo_info.get('estatisticas_conhecidas', {})
                    }
        
        # 2. Tentar detecção automática
        return self._detectar_grupo_automatico(consulta_lower)
    
    def detectar_grupo_por_cnpj(self, cnpj: str, nome_cliente: str = "") -> Optional[Dict[str, Any]]:
        """🆕 NOVA FUNCIONALIDADE: Detecta grupo baseado no CNPJ"""
        try:
            cnpj_limpo = re.sub(r'[^\d]', '', cnpj)  # Remove formatação
            cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
            cnpj_prefixo = cnpj_formatado[:11]  # Primeiros 10 dígitos + /
            
            logger.info(f"🔍 Analisando CNPJ: {cnpj_prefixo}")
            
            for grupo_key, grupo_info in self.grupos_manuais.items():
                cnpj_prefixos = grupo_info.get('cnpj_prefixos', [])
                metodo = grupo_info.get('metodo_deteccao', 'nome_padrao')
                
                # Verificar se CNPJ corresponde a algum prefixo conhecido
                for prefixo in cnpj_prefixos:
                    if cnpj_formatado.startswith(prefixo):
                        logger.info(f"✅ CNPJ MATCH: {prefixo} → {grupo_info['nome_grupo']}")
                        
                        # Validação adicional baseada no método
                        if metodo == 'multiplo_cnpj_e_nome':
                            # Para Atacadão: verificar também padrão do nome
                            padrao_nome = grupo_info.get('padrao_nome_regex')
                            if padrao_nome and nome_cliente:
                                if re.search(padrao_nome, nome_cliente.lower()):
                                    logger.info(f"✅ NOME MATCH: {nome_cliente} → padrão {padrao_nome}")
                                    return self._criar_resultado_deteccao_cnpj(grupo_info, prefixo, cnpj_formatado, nome_cliente)
                                else:
                                    logger.warning(f"⚠️ CNPJ match mas nome não confere: {nome_cliente}")
                                    continue
                            else:
                                return self._criar_resultado_deteccao_cnpj(grupo_info, prefixo, cnpj_formatado, nome_cliente)
                        
                        elif metodo == 'cnpj_uniforme_e_nome':
                            # Para Assai/Tenda: CNPJ já é suficiente
                            return self._criar_resultado_deteccao_cnpj(grupo_info, prefixo, cnpj_formatado, nome_cliente)
                        
                        elif metodo == 'nome_uniforme_cnpj_diversos':
                            # Para Coco Bambu: verificar nome exato
                            nome_exato = grupo_info.get('nome_exato', '')
                            if nome_exato and nome_exato.lower() in nome_cliente.lower():
                                return self._criar_resultado_deteccao_cnpj(grupo_info, 'DIVERSOS', cnpj_formatado, nome_cliente)
            
            logger.info(f"❌ CNPJ {cnpj_prefixo} não corresponde a nenhum grupo conhecido")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao detectar grupo por CNPJ {cnpj}: {e}")
            return None

    def _criar_resultado_deteccao_cnpj(self, grupo_info: Dict, prefixo_match: str, cnpj_completo: str, nome_cliente: str) -> Dict[str, Any]:
        """Cria resultado estruturado da detecção por CNPJ"""
        return {
            'grupo_detectado': grupo_info['nome_grupo'],
            'filtro_sql': grupo_info['filtro_sql'],
            'tipo_deteccao': 'GRUPO_POR_CNPJ',
            'tipo_negocio': grupo_info['tipo'],
            'descricao': grupo_info['descricao'],
            'metodo_deteccao': grupo_info.get('metodo_deteccao'),
            'cnpj_prefixo_match': prefixo_match,
            'cnpj_completo': cnpj_completo,
            'nome_cliente': nome_cliente,
            'confianca': 'ALTA',  # Detecção por CNPJ tem alta confiança
            'estatisticas': grupo_info.get('estatisticas_conhecidas', {})
        }

    def analisar_clientes_com_cnpj(self) -> Dict[str, Any]:
        """🆕 Analisa todos os clientes considerando CNPJ para detectar grupos"""
        try:
            from app import db
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            # Buscar clientes com CNPJ
            clientes_cnpj = db.session.query(
                RelatorioFaturamentoImportado.nome_cliente,
                RelatorioFaturamentoImportado.cnpj_cliente
            ).filter(
                RelatorioFaturamentoImportado.cnpj_cliente.isnot(None),
                RelatorioFaturamentoImportado.cnpj_cliente != ''
            ).distinct().all()
            
            grupos_detectados = defaultdict(list)
            clientes_sem_grupo = []
            estatisticas_cnpj = defaultdict(int)
            
            for nome_cliente, cnpj in clientes_cnpj:
                if not cnpj:
                    continue
                    
                # Tentar detectar grupo por CNPJ
                resultado = self.detectar_grupo_por_cnpj(cnpj, nome_cliente)
                
                if resultado:
                    grupo_nome = resultado['grupo_detectado']
                    grupos_detectados[grupo_nome].append({
                        'nome': nome_cliente,
                        'cnpj': cnpj,
                        'prefixo_match': resultado['cnpj_prefixo_match'],
                        'metodo': resultado['metodo_deteccao']
                    })
                    
                    # Estatísticas por prefixo CNPJ
                    prefixo = cnpj[:11] if len(cnpj) >= 11 else cnpj[:8]
                    estatisticas_cnpj[prefixo] += 1
                else:
                    clientes_sem_grupo.append({'nome': nome_cliente, 'cnpj': cnpj})
            
            # Gerar sugestões de novos grupos baseados em CNPJs frequentes
            sugestoes_cnpj = self._analisar_cnpjs_frequentes(clientes_sem_grupo)
            
            return {
                'total_clientes_com_cnpj': len(clientes_cnpj),
                'grupos_detectados_por_cnpj': dict(grupos_detectados),
                'clientes_sem_grupo': len(clientes_sem_grupo),
                'estatisticas_cnpj': dict(estatisticas_cnpj),
                'sugestoes_novos_grupos': sugestoes_cnpj,
                'resumo_por_grupo': {
                    grupo: len(clientes) for grupo, clientes in grupos_detectados.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na análise com CNPJ: {e}")
            return {'erro': str(e)}

    def _analisar_cnpjs_frequentes(self, clientes_sem_grupo: List[Dict]) -> List[Dict[str, Any]]:
        """Analisa CNPJs frequentes para sugerir novos grupos"""
        cnpj_counts = defaultdict(list)
        
        for cliente in clientes_sem_grupo:
            cnpj = cliente['cnpj']
            if cnpj and len(cnpj) >= 11:
                prefixo = cnpj[:11]  # Primeiros 10 dígitos + /
                cnpj_counts[prefixo].append(cliente)
        
        sugestoes = []
        for prefixo, clientes in cnpj_counts.items():
            if len(clientes) >= 3:  # 3+ clientes com mesmo prefixo
                # Analisar padrões de nome
                nomes = [c['nome'] for c in clientes]
                padrao_comum = self._encontrar_padrao_nome_comum(nomes)
                
                sugestao = {
                    'cnpj_prefixo': prefixo,
                    'total_clientes': len(clientes),
                    'clientes_exemplos': nomes[:5],
                    'padrao_nome_detectado': padrao_comum,
                    'tipo_grupo_sugerido': self._determinar_tipo_por_nomes(nomes),
                    'codigo_sugerido': self._gerar_codigo_grupo_cnpj(prefixo, padrao_comum, len(clientes))
                }
                sugestoes.append(sugestao)
        
        return sorted(sugestoes, key=lambda x: x['total_clientes'], reverse=True)[:10]

    def _encontrar_padrao_nome_comum(self, nomes: List[str]) -> str:
        """Encontra padrão comum nos nomes dos clientes"""
        if not nomes:
            return ""
        
        # Procurar palavra mais frequente
        todas_palavras = []
        for nome in nomes:
            palavras = re.findall(r'\w+', nome.lower())
            todas_palavras.extend([p for p in palavras if len(p) > 3])
        
        from collections import Counter
        palavra_mais_comum = Counter(todas_palavras).most_common(1)
        
        if palavra_mais_comum and palavra_mais_comum[0][1] >= len(nomes) * 0.7:
            return palavra_mais_comum[0][0]
        
        return "padrão não identificado"

    def _determinar_tipo_por_nomes(self, nomes: List[str]) -> str:
        """Determina tipo de negócio baseado nos nomes"""
        texto_total = ' '.join(nomes).lower()
        
        if 'atacad' in texto_total:
            return 'atacarejo'
        elif 'super' in texto_total:
            return 'supermercado'
        elif 'distribuid' in texto_total:
            return 'distribuidor'
        elif 'restaurante' in texto_total or 'bar' in texto_total:
            return 'alimentacao'
        else:
            return 'comercio'

    def _gerar_codigo_grupo_cnpj(self, prefixo: str, padrao_nome: str, total: int) -> str:
        """Gera código Python para novo grupo detectado por CNPJ"""
        nome_grupo = f'grupo_{padrao_nome}' if padrao_nome != "padrão não identificado" else f'grupo_cnpj_{prefixo.replace(".", "").replace("/", "")}'
        
        return f"""'{nome_grupo}': {{
    'nome_grupo': 'Grupo {padrao_nome.title()} (Todas as Unidades)',
    'filtro_sql': '%{padrao_nome}%',
    'keywords': ['{padrao_nome}'],
    'descricao': 'Grupo detectado automaticamente por CNPJ ({total} clientes)',
    'tipo': 'detectado_automaticamente',
    'cnpj_prefixos': ['{prefixo}'],
    'metodo_deteccao': 'cnpj_uniforme_e_nome'
}},"""

    def _detectar_grupo_automatico(self, consulta_lower: str) -> Optional[Dict[str, Any]]:
        """Detecção automática de grupos baseada em padrões nos dados"""
        try:
            # Padrões comuns de grupos empresariais
            padroes_grupo = [
                r'rede\s+(\w+)',  # "rede walmart", "rede extra"
                r'grupo\s+(\w+)',  # "grupo carrefour"
                r'(\w+)\s+atacadista',  # "fort atacadista"
                r'(\w+)\s+supermercados',  # "mateus supermercados"
            ]
            
            for padrao in padroes_grupo:
                match = re.search(padrao, consulta_lower)
                if match:
                    nome_detectado = match.group(1)
                    
                    # Verificar se este nome aparece frequentemente nos dados
                    if self._verificar_frequencia_nos_dados(nome_detectado):
                        logger.info(f"🤖 GRUPO AUTOMÁTICO DETECTADO: {nome_detectado}")
                        
                        return {
                            'grupo_detectado': f'Grupo {nome_detectado.title()} (Auto-detectado)',
                            'filtro_sql': f'%{nome_detectado}%',
                            'tipo_deteccao': 'GRUPO_AUTOMATICO',
                            'tipo_negocio': 'auto',
                            'descricao': f'Grupo detectado automaticamente: {nome_detectado}',
                            'keyword_encontrada': nome_detectado
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro na detecção automática: {e}")
            return None
    
    def _verificar_frequencia_nos_dados(self, nome: str) -> bool:
        """Verifica se um nome aparece com frequência suficiente para ser considerado grupo"""
        try:
            from app import db
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            # Contar quantos clientes diferentes contêm este nome
            count = db.session.query(RelatorioFaturamentoImportado.nome_cliente).filter(
                RelatorioFaturamentoImportado.nome_cliente.ilike(f'%{nome}%')
            ).distinct().count()
            
            # Se há 3+ clientes diferentes com este nome, provavelmente é um grupo
            return count >= 3
            
        except Exception as e:
            logger.error(f"Erro ao verificar frequência de {nome}: {e}")
            return False
    
    def analisar_todos_clientes(self) -> Dict[str, Any]:
        """Analisa todos os clientes para identificar possíveis grupos não mapeados"""
        try:
            from app import db
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            if 'analise_completa' in self._cache_analise:
                return self._cache_analise['analise_completa']
            
            # Buscar todos os clientes
            clientes = db.session.query(RelatorioFaturamentoImportado.nome_cliente).distinct().all()
            clientes_nomes = [c[0] for c in clientes if c[0]]
            
            # Agrupar por palavras-chave comuns
            grupos_potenciais = defaultdict(list)
            
            for cliente in clientes_nomes:
                cliente_lower = cliente.lower()
                
                # Procurar padrões de grupo
                if 'rede' in cliente_lower or 'grupo' in cliente_lower:
                    # Extrair nome do grupo
                    palavras = cliente_lower.split()
                    for palavra in palavras:
                        if palavra not in ['rede', 'grupo', 'ltda', 'sa', 'comercio', 'distribuidora']:
                            grupos_potenciais[palavra].append(cliente)
                            break
                else:
                    # Procurar por palavras que se repetem
                    primeira_palavra = cliente_lower.split()[0] if cliente_lower.split() else ""
                    if len(primeira_palavra) > 3:
                        grupos_potenciais[primeira_palavra].append(cliente)
            
            # Filtrar apenas grupos com 2+ clientes
            grupos_reais = {k: v for k, v in grupos_potenciais.items() if len(v) >= 2}
            
            analise = {
                'total_clientes': len(clientes_nomes),
                'grupos_manuais_mapeados': len(self.grupos_manuais),
                'grupos_potenciais_detectados': len(grupos_reais),
                'grupos_detalhados': grupos_reais,
                'sugestoes': self._gerar_sugestoes_grupos(grupos_reais)
            }
            
            self._cache_analise['analise_completa'] = analise
            return analise
            
        except Exception as e:
            logger.error(f"Erro na análise completa: {e}")
            return {'erro': str(e)}
    
    def _gerar_sugestoes_grupos(self, grupos_detectados: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Gera sugestões de novos grupos para adicionar ao sistema"""
        sugestoes = []
        
        for palavra_chave, clientes in grupos_detectados.items():
            if len(clientes) >= 3 and palavra_chave not in self.grupos_manuais:
                # Determinar tipo de negócio baseado nos nomes
                tipo_negocio = 'desconhecido'
                if any('atacad' in c.lower() for c in clientes):
                    tipo_negocio = 'atacarejo'
                elif any('super' in c.lower() for c in clientes):
                    tipo_negocio = 'supermercado'
                elif any('distribuid' in c.lower() for c in clientes):
                    tipo_negocio = 'distribuidor'
                
                sugestao = {
                    'palavra_chave': palavra_chave,
                    'nome_grupo_sugerido': f'Grupo {palavra_chave.title()} (Todas as Unidades)',
                    'filtro_sql_sugerido': f'%{palavra_chave}%',
                    'keywords_sugeridas': [palavra_chave, f'grupo {palavra_chave}'],
                    'tipo_negocio': tipo_negocio,
                    'clientes_exemplos': clientes[:5],  # Primeiros 5 como exemplo
                    'total_clientes': len(clientes),
                    'codigo_implementacao': self._gerar_codigo_grupo(palavra_chave, tipo_negocio)
                }
                
                sugestoes.append(sugestao)
        
        # Ordenar por quantidade de clientes
        sugestoes.sort(key=lambda x: x['total_clientes'], reverse=True)
        
        return sugestoes[:10]  # Top 10 sugestões
    
    def _gerar_codigo_grupo(self, palavra_chave: str, tipo_negocio: str) -> str:
        """Gera código Python para adicionar novo grupo"""
        return f"""'{palavra_chave}': {{
    'nome_grupo': 'Grupo {palavra_chave.title()} (Todas as Unidades)',
    'filtro_sql': '%{palavra_chave}%',
    'keywords': ['{palavra_chave}', 'grupo {palavra_chave}'],
    'descricao': 'Grupo {tipo_negocio} detectado automaticamente',
    'tipo': '{tipo_negocio}'
}},"""

class GrupoEmpresarialService:
    """Serviço para gerenciar grupos empresariais de transportadoras"""
    
    def __init__(self):
        self.detector = GrupoEmpresarialDetector()
        self._cache_grupos = {}
    
    def obter_transportadoras_grupo(self, transportadora_id: int) -> List[int]:
        """
        Retorna lista de IDs de transportadoras que pertencem ao mesmo grupo empresarial.

        Detecta grupo de duas formas:
        1. Via prefixo CNPJ (primeiros 10 dígitos iguais = mesma empresa matriz)
        2. Via detector de grupos manuais (quando cadastrado)

        Isso permite buscar tabelas de frete em todas as filiais de uma mesma
        transportadora matriz.

        Args:
            transportadora_id: ID da transportadora de referência

        Returns:
            Lista de IDs de transportadoras do mesmo grupo (inclui a própria)
        """
        try:
            from app.transportadoras.models import Transportadora

            # 1. Buscar transportadora por ID
            transportadora = Transportadora.query.get(transportadora_id)
            if not transportadora:
                logger.warning(f"⚠️ Transportadora {transportadora_id} não encontrada")
                return [transportadora_id]  # Fallback seguro

            if not transportadora.cnpj:
                logger.warning(f"⚠️ Transportadora {transportadora_id} sem CNPJ cadastrado")
                return [transportadora_id]  # Fallback seguro

            # 2. Extrair prefixo CNPJ (primeiros 10 dígitos = mesma empresa matriz)
            # Formato típico: "65.523.110/0001-83"
            # Prefixo: "65.523.110/" (identifica a empresa matriz)
            cnpj = transportadora.cnpj.strip()

            # Buscar posição da barra
            barra_pos = cnpj.find('/')
            if barra_pos == -1:
                # CNPJ sem formatação, tentar extrair primeiros 8 dígitos
                cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
                if len(cnpj_limpo) >= 8:
                    prefixo_busca = cnpj_limpo[:8]
                else:
                    logger.debug(f"📦 CNPJ inválido para transportadora {transportadora_id}")
                    return [transportadora_id]
            else:
                # CNPJ formatado, usar tudo até a barra (inclusive)
                prefixo_busca = cnpj[:barra_pos + 1]

            # 3. Buscar todas as transportadoras com mesmo prefixo CNPJ
            transportadoras_grupo = Transportadora.query.filter(
                Transportadora.cnpj.ilike(f"{prefixo_busca}%")
            ).all()

            # 4. Retornar lista de IDs
            ids = [t.id for t in transportadoras_grupo if t.id]

            if len(ids) > 1:
                logger.info(f"🏢 Grupo de transportadoras detectado via CNPJ {prefixo_busca}: "
                           f"{len(ids)} membros → IDs {ids}")
            else:
                logger.debug(f"📦 Transportadora {transportadora_id} não pertence a grupo (CNPJ único)")

            return ids if ids else [transportadora_id]

        except Exception as e:
            logger.error(f"❌ Erro ao obter transportadoras do grupo para {transportadora_id}: {e}")
            return [transportadora_id]  # Fallback seguro
    
    def detectar_grupo_na_consulta(self, consulta: str) -> Optional[Dict[str, Any]]:
        """Detecta grupo empresarial na consulta"""
        return self.detector.detectar_grupo_na_consulta(consulta)
    
    def detectar_grupo_por_cnpj(self, cnpj: str, nome_cliente: str = "") -> Optional[Dict[str, Any]]:
        """Detecta grupo empresarial por CNPJ"""
        return self.detector.detectar_grupo_por_cnpj(cnpj, nome_cliente)

# Instâncias globais
detector_grupos = GrupoEmpresarialDetector()
grupo_service = GrupoEmpresarialService()  # ✅ CORREÇÃO: Objeto que estava faltando

def detectar_grupo_empresarial(consulta: str) -> Optional[Dict[str, Any]]:
    """Função utilitária para detectar grupos empresariais"""
    return detector_grupos.detectar_grupo_na_consulta(consulta)

def detectar_grupo_por_cnpj(cnpj: str, nome_cliente: str = "") -> Optional[Dict[str, Any]]:
    """🆕 Função utilitária para detectar grupos por CNPJ"""
    return detector_grupos.detectar_grupo_por_cnpj(cnpj, nome_cliente)

def analisar_grupos_sistema() -> Dict[str, Any]:
    """Análise completa dos grupos no sistema"""
    return detector_grupos.analisar_todos_clientes()

def analisar_grupos_com_cnpj() -> Dict[str, Any]:
    """🆕 Análise completa incluindo detecção por CNPJ"""
    return detector_grupos.analisar_clientes_com_cnpj()