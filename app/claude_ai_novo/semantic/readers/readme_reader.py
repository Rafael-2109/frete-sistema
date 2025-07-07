"""
📚 README READER - Leitor Inteligente do README de Mapeamento
==========================================================

Módulo responsável por ler e extrair informações semânticas
do arquivo README_MAPEAMENTO_SEMANTICO_COMPLETO.md.

Funcionalidades:
- Parser inteligente de seções do README
- Extração de termos naturais por campo
- Busca de campos por modelo
- Validação de estrutura do README
"""

import os
import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ReadmeReader:
    """
    Leitor inteligente do README de mapeamento semântico.
    
    Responsável por extrair termos naturais e informações de contexto
    do arquivo README_MAPEAMENTO_SEMANTICO_COMPLETO.md.
    """
    
    def __init__(self):
        """Inicializa o leitor do README"""
        self.readme_path = self._localizar_readme()
        self.conteudo = None
        self._cache_secoes = {}
        
        if self.readme_path:
            self._carregar_readme()
    
    def _localizar_readme(self) -> Optional[str]:
        """
        Localiza o arquivo README_MAPEAMENTO_SEMANTICO_COMPLETO.md
        
        Returns:
            Caminho para o README ou None se não encontrado
        """
        try:
            # Caminhos possíveis para o README
            caminhos_possiveis = [
                # Caminho a partir do semantic/readers/
                os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'README_MAPEAMENTO_SEMANTICO_COMPLETO.md'),
                # Caminho a partir da raiz do projeto
                os.path.join(os.getcwd(), 'README_MAPEAMENTO_SEMANTICO_COMPLETO.md'),
                # Caminho absoluto baseado no arquivo atual
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'README_MAPEAMENTO_SEMANTICO_COMPLETO.md'))
            ]
            
            for caminho in caminhos_possiveis:
                caminho_normalizado = os.path.normpath(caminho)
                if os.path.exists(caminho_normalizado):
                    logger.info(f"📄 README encontrado: {caminho_normalizado}")
                    return caminho_normalizado
            
            logger.warning(f"📄 README não encontrado em nenhum dos caminhos: {caminhos_possiveis}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao localizar README: {e}")
            return None
    
    def _carregar_readme(self) -> bool:
        """
        Carrega o conteúdo do README na memória.
        
        Returns:
            True se carregado com sucesso, False caso contrário
        """
        if not self.readme_path:
            logger.error("❌ Caminho do README não definido")
            return False
            
        try:
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                self.conteudo = f.read()
            
            logger.info(f"📄 README carregado: {len(self.conteudo)} caracteres")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar README: {e}")
            return False
    
    def buscar_termos_naturais(self, nome_campo: str, nome_modelo: Optional[str] = None) -> List[str]:
        """
        Busca termos naturais para um campo específico no README.
        
        Args:
            nome_campo: Nome do campo a buscar
            nome_modelo: Nome do modelo (opcional, para busca mais específica)
            
        Returns:
            Lista de termos naturais encontrados
        """
        if not self.conteudo:
            return []
        
        termos_encontrados = []
        
        try:
            # Padrão 1: Buscar campo específico com LINGUAGEM_NATURAL
            pattern_especifico = rf'-\s*\*\*{re.escape(nome_campo)}\*\*.*?LINGUAGEM_NATURAL:\s*\[(.*?)\]'
            match = re.search(pattern_especifico, self.conteudo, re.DOTALL | re.IGNORECASE)
            
            if match:
                termos_str = match.group(1)
                termos = self._extrair_termos_da_string(termos_str)
                termos_encontrados.extend(termos)
                logger.debug(f"✅ Campo {nome_campo}: {len(termos)} termos encontrados (busca específica)")
            
            # Padrão 2: Buscar no contexto do modelo se especificado
            if nome_modelo and not termos_encontrados:
                secao_modelo = self._extrair_secao_modelo(nome_modelo)
                if secao_modelo:
                    termos_modelo = self._buscar_campo_na_secao(nome_campo, secao_modelo)
                    termos_encontrados.extend(termos_modelo)
                    logger.debug(f"✅ Campo {nome_campo} no modelo {nome_modelo}: {len(termos_modelo)} termos")
            
            # Padrão 3: Busca genérica por campo (fallback)
            if not termos_encontrados:
                pattern_generico = rf'LINGUAGEM_NATURAL:\s*\[[^\]]*{re.escape(nome_campo)}[^\]]*\]'
                matches = re.findall(pattern_generico, self.conteudo, re.IGNORECASE)
                for match in matches:
                    termos = self._extrair_termos_da_string(match)
                    termos_encontrados.extend(termos)
                
                if termos_encontrados:
                    logger.debug(f"✅ Campo {nome_campo}: {len(termos_encontrados)} termos (busca genérica)")
            
            # Remover duplicatas mantendo ordem
            termos_unicos = []
            for termo in termos_encontrados:
                if termo not in termos_unicos:
                    termos_unicos.append(termo)
            
            return termos_unicos
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar termos para {nome_campo}: {e}")
            return []
    
    def _extrair_termos_da_string(self, texto: str) -> List[str]:
        """
        Extrai termos naturais de uma string contendo array de termos.
        
        Args:
            texto: String contendo termos entre aspas ou similar
            
        Returns:
            Lista de termos extraídos
        """
        termos = []
        
        try:
            # Padrão 1: Termos entre aspas duplas
            pattern_aspas_duplas = r'"([^"]+)"'
            termos_aspas_duplas = re.findall(pattern_aspas_duplas, texto)
            termos.extend(termos_aspas_duplas)
            
            # Padrão 2: Termos entre aspas simples
            if not termos:
                pattern_aspas_simples = r"'([^']+)'"
                termos_aspas_simples = re.findall(pattern_aspas_simples, texto)
                termos.extend(termos_aspas_simples)
            
            # Padrão 3: Termos separados por vírgula sem aspas (fallback)
            if not termos:
                # Limpar [ ] e dividir por vírgula
                texto_limpo = texto.strip('[]').strip()
                if texto_limpo:
                    termos_virgula = [t.strip().strip('"\'') for t in texto_limpo.split(',')]
                    termos.extend([t for t in termos_virgula if t])
            
            # Limpar termos
            termos_limpos = []
            for termo in termos:
                termo_limpo = termo.strip().strip('"\'')
                if termo_limpo and len(termo_limpo) > 1:  # Evitar termos muito curtos
                    termos_limpos.append(termo_limpo)
            
            return termos_limpos
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair termos de: {texto[:50]}... → {e}")
            return []
    
    def _extrair_secao_modelo(self, nome_modelo: str) -> Optional[str]:
        """
        Extrai a seção específica de um modelo do README.
        
        Args:
            nome_modelo: Nome do modelo a buscar
            
        Returns:
            String com conteúdo da seção ou None se não encontrada
        """
        if not self.conteudo:
            return None
        
        # Cache de seções
        if nome_modelo in self._cache_secoes:
            return self._cache_secoes[nome_modelo]
        
        try:
            # Padrões para identificar início da seção do modelo
            patterns_inicio = [
                rf'### 🔸 {re.escape(nome_modelo.upper())}',
                rf'## {re.escape(nome_modelo)}',
                rf'### {re.escape(nome_modelo)}',
                rf'\*\*Tabela:\*\*.*{re.escape(nome_modelo.lower())}'
            ]
            
            inicio_secao = None
            for pattern in patterns_inicio:
                match = re.search(pattern, self.conteudo, re.IGNORECASE)
                if match:
                    inicio_secao = match.start()
                    break
            
            if inicio_secao is None:
                logger.debug(f"⚠️ Seção do modelo {nome_modelo} não encontrada")
                return None
            
            # Encontrar fim da seção (próxima seção ou fim do documento)
            fim_secao = len(self.conteudo)
            
            # Buscar próxima seção de mesmo nível
            resto_documento = self.conteudo[inicio_secao + 10:]  # +10 para pular o header atual
            match_proximo = re.search(r'^### 🔸|\n## ', resto_documento, re.MULTILINE)
            
            if match_proximo:
                fim_secao = inicio_secao + 10 + match_proximo.start()
            
            secao = self.conteudo[inicio_secao:fim_secao]
            
            # Cache da seção
            self._cache_secoes[nome_modelo] = secao
            
            logger.debug(f"✅ Seção do modelo {nome_modelo} extraída: {len(secao)} caracteres")
            return secao
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair seção do modelo {nome_modelo}: {e}")
            return None
    
    def _buscar_campo_na_secao(self, nome_campo: str, secao: str) -> List[str]:
        """
        Busca um campo específico dentro de uma seção do modelo.
        
        Args:
            nome_campo: Nome do campo a buscar
            secao: Conteúdo da seção do modelo
            
        Returns:
            Lista de termos naturais encontrados
        """
        try:
            # Buscar campo na seção
            pattern = rf'-\s*\*\*{re.escape(nome_campo)}\*\*.*?LINGUAGEM_NATURAL:\s*\[(.*?)\]'
            match = re.search(pattern, secao, re.DOTALL | re.IGNORECASE)
            
            if match:
                termos_str = match.group(1)
                return self._extrair_termos_da_string(termos_str)
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campo {nome_campo} na seção: {e}")
            return []
    
    def obter_informacoes_campo(self, nome_campo: str, nome_modelo: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém informações completas de um campo do README.
        
        Args:
            nome_campo: Nome do campo
            nome_modelo: Nome do modelo (opcional)
            
        Returns:
            Dict com informações do campo (significado, contexto, observações, etc.)
        """
        if not self.conteudo:
            return {}
        
        informacoes = {
            'campo': nome_campo,
            'modelo': nome_modelo,
            'termos_naturais': [],
            'significado': '',
            'contexto': '',
            'observacoes': ''
        }
        
        try:
            # Buscar seção do modelo se especificado
            secao_busca = self.conteudo
            if nome_modelo:
                secao_modelo = self._extrair_secao_modelo(nome_modelo)
                if secao_modelo:
                    secao_busca = secao_modelo
            
            # Buscar bloco completo do campo
            pattern_bloco = rf'-\s*\*\*{re.escape(nome_campo)}\*\*.*?(?=\n-\s*\*\*|\nFIM|\n###|\n##|$)'
            match = re.search(pattern_bloco, secao_busca, re.DOTALL | re.IGNORECASE)
            
            if match:
                bloco_campo = match.group(0)
                
                # Extrair termos naturais
                pattern_termos = r'LINGUAGEM_NATURAL:\s*\[(.*?)\]'
                match_termos = re.search(pattern_termos, bloco_campo, re.DOTALL)
                if match_termos:
                    informacoes['termos_naturais'] = self._extrair_termos_da_string(match_termos.group(1))
                
                # Extrair significado
                pattern_significado = r'SIGNIFICADO:\s*(.*?)(?=\nLINGUAGEM_NATURAL|\nCONTEXTO|\nOBSERVAÇÕES|\n-|\nFIM|$)'
                match_significado = re.search(pattern_significado, bloco_campo, re.DOTALL)
                if match_significado:
                    informacoes['significado'] = match_significado.group(1).strip()
                
                # Extrair contexto
                pattern_contexto = r'CONTEXTO:\s*(.*?)(?=\nOBSERVAÇÕES|\n-|\nFIM|$)'
                match_contexto = re.search(pattern_contexto, bloco_campo, re.DOTALL)
                if match_contexto:
                    informacoes['contexto'] = match_contexto.group(1).strip()
                
                # Extrair observações
                pattern_obs = r'OBSERVAÇÕES:\s*(.*?)(?=\n-|\nFIM|$)'
                match_obs = re.search(pattern_obs, bloco_campo, re.DOTALL)
                if match_obs:
                    informacoes['observacoes'] = match_obs.group(1).strip()
            
            return informacoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter informações do campo {nome_campo}: {e}")
            return informacoes
    
    def listar_modelos_disponiveis(self) -> List[str]:
        """
        Lista todos os modelos disponíveis no README.
        
        Returns:
            Lista de nomes dos modelos encontrados
        """
        if not self.conteudo:
            return []
        
        try:
            modelos = []
            
            # Buscar seções de modelos
            pattern_modelos = r'### 🔸 ([A-Z_]+)'
            matches = re.findall(pattern_modelos, self.conteudo)
            
            for match in matches:
                # Converter para formato padrão (primeira letra maiúscula)
                modelo_formatado = match.lower().replace('_', '').capitalize()
                if modelo_formatado not in modelos:
                    modelos.append(modelo_formatado)
            
            logger.info(f"📄 Modelos encontrados no README: {modelos}")
            return modelos
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar modelos: {e}")
            return []
    
    def validar_estrutura_readme(self) -> Dict[str, Any]:
        """
        Valida a estrutura e qualidade do README.
        
        Returns:
            Dict com resultado da validação
        """
        if not self.conteudo:
            return {'valido': False, 'erro': 'README não carregado'}
        
        validacao = {
            'valido': True,
            'warnings': [],
            'estatisticas': {
                'total_caracteres': len(self.conteudo),
                'total_modelos': 0,
                'total_campos': 0,
                'campos_com_termos': 0
            }
        }
        
        try:
            # Contar modelos
            modelos = self.listar_modelos_disponiveis()
            validacao['estatisticas']['total_modelos'] = len(modelos)
            
            # Contar campos com LINGUAGEM_NATURAL
            pattern_campos = r'-\s*\*\*([^*]+)\*\*.*?LINGUAGEM_NATURAL:\s*\[(.*?)\]'
            matches = re.findall(pattern_campos, self.conteudo, re.DOTALL)
            
            validacao['estatisticas']['total_campos'] = len(matches)
            
            campos_com_termos = 0
            for campo, termos_str in matches:
                termos = self._extrair_termos_da_string(termos_str)
                if termos:
                    campos_com_termos += 1
            
            validacao['estatisticas']['campos_com_termos'] = campos_com_termos
            
            # Validações
            if validacao['estatisticas']['total_modelos'] == 0:
                validacao['warnings'].append('Nenhum modelo encontrado')
            
            if validacao['estatisticas']['total_campos'] == 0:
                validacao['warnings'].append('Nenhum campo com mapeamento encontrado')
            
            if validacao['estatisticas']['campos_com_termos'] < validacao['estatisticas']['total_campos']:
                campos_sem_termos = validacao['estatisticas']['total_campos'] - validacao['estatisticas']['campos_com_termos']
                validacao['warnings'].append(f'{campos_sem_termos} campos sem termos naturais')
            
            logger.info(f"📄 Validação README: {validacao['estatisticas']}")
            return validacao
            
        except Exception as e:
            logger.error(f"❌ Erro na validação do README: {e}")
            return {'valido': False, 'erro': str(e)}
    
    def esta_disponivel(self) -> bool:
        """
        Verifica se o README está disponível e carregado.
        
        Returns:
            True se README está disponível, False caso contrário
        """
        return self.readme_path is not None and self.conteudo is not None
    
    def __str__(self) -> str:
        """Representação string do reader"""
        status = "DISPONÍVEL" if self.esta_disponivel() else "INDISPONÍVEL"
        return f"<ReadmeReader status={status} path={self.readme_path}>"
    
    def __repr__(self) -> str:
        """Representação detalhada do reader"""
        return self.__str__() 