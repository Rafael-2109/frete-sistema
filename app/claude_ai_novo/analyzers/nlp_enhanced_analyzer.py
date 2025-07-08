# -*- coding: utf-8 -*-
"""
🧠 ANALISADOR NLP AVANÇADO
Melhora significativa no entendimento usando SpaCy e NLTK
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
import re

# Tentativa de importar bibliotecas NLP
try:
    import spacy
    from spacy.lang.pt.stop_words import STOP_WORDS
    NLP_SPACY_AVAILABLE = True
    
    # Tentar carregar modelo português
    try:
        nlp = spacy.load("pt_core_news_sm")
    except:
        # Fallback para modelo vazio se não tiver o português
        nlp = spacy.blank("pt")
        logging.warning("⚠️ Modelo português do spaCy não instalado. Use: python -m spacy download pt_core_news_sm")
except ImportError:
    NLP_SPACY_AVAILABLE = False
    logging.warning("⚠️ SpaCy não instalado. Usando análise básica.")

try:
    from fuzzywuzzy import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    logging.warning("⚠️ FuzzyWuzzy não instalado. Matching exato apenas.")

try:
    import nltk
    from nltk.corpus import stopwords
    # Baixar recursos necessários
    try:
        nltk.download('stopwords', quiet=True)
        nltk.download('punkt', quiet=True)
        NLTK_STOPWORDS = set(stopwords.words('portuguese'))
    except:
        NLTK_STOPWORDS = set()
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    NLTK_STOPWORDS = set()
    logging.warning("⚠️ NLTK não instalado.")

logger = logging.getLogger(__name__)

@dataclass
class AnaliseNLP:
    """Resultado da análise NLP avançada"""
    tokens_limpos: List[str]
    entidades_nomeadas: List[Dict[str, str]]
    palavras_chave: List[str]
    correcoes_sugeridas: Dict[str, str]
    similaridades: Dict[str, float]
    negacoes_detectadas: List[str]
    tempo_verbal: str
    sentimento: str

class NLPEnhancedAnalyzer:
    """Analisador com capacidades NLP avançadas"""
    
    def __init__(self):
        # Dicionário de correções comuns
        self.correcoes_comuns = {
            "assaí": "assai",
            "assaï": "assai",
            "asai": "assai",
            "atacadao": "atacadão",
            "atacadaum": "atacadão",
            "carrefur": "carrefour",
            "carefour": "carrefour",
            "entregass": "entregas",
            "entrega": "entregas",
            "atrazadas": "atrasadas",
            "atrazado": "atrasado",
            "pendente": "pendentes",
            "relatorio": "relatório",
            "sao paulo": "são paulo",
            "nf": "nota fiscal",
            "cte": "conhecimento de transporte",
            "pdd": "pedido"
        }
        
        # Sinônimos importantes
        self.sinonimos = {
            "atrasado": ["atrasada", "atrasados", "atrasadas", "atraso", "em atraso", "pendente", "vencido"],
            "entrega": ["entregas", "entregue", "entregou", "entregar", "remessa", "envio"],
            "cliente": ["clientes", "empresa", "comprador", "destinatário"],
            "frete": ["fretes", "transporte", "fretamento", "carreto"],
            "pedido": ["pedidos", "ordem", "pdd", "solicitação"],
            "nota": ["nf", "nota fiscal", "nfe", "danfe", "documento"],
            "mostrar": ["mostre", "listar", "exibir", "ver", "visualizar", "trazer"],
            "quantidade": ["quantos", "quantas", "total", "número", "qtd", "qtde"]
        }
        
        # Palavras de negação
        self.palavras_negacao = {
            "não", "nao", "nunca", "jamais", "nenhum", "nenhuma", 
            "sem", "exceto", "menos", "fora", "além"
        }
        
        logger.info(f"🧠 NLP Enhanced Analyzer inicializado")
        logger.info(f"   SpaCy: {'✅' if NLP_SPACY_AVAILABLE else '❌'}")
        logger.info(f"   Fuzzy: {'✅' if FUZZY_AVAILABLE else '❌'}")
        logger.info(f"   NLTK: {'✅' if NLTK_AVAILABLE else '❌'}")
    
    def analisar_com_nlp(self, texto: str) -> AnaliseNLP:
        """Análise completa com NLP avançado"""
        
        # Preparação inicial
        texto_lower = texto.lower().strip()
        
        # 1. Correções ortográficas
        correcoes = self._aplicar_correcoes(texto_lower)
        
        # 2. Tokenização e limpeza
        if NLP_SPACY_AVAILABLE:
            tokens_limpos = self._tokenizar_spacy(correcoes['texto_corrigido'])
            entidades = self._extrair_entidades_spacy(correcoes['texto_corrigido'])
        else:
            tokens_limpos = self._tokenizar_basico(correcoes['texto_corrigido'])
            entidades = []
        
        # 3. Detecção de negações
        negacoes = self._detectar_negacoes(tokens_limpos)
        
        # 4. Análise de similaridade
        similaridades = self._calcular_similaridades(correcoes['texto_corrigido'])
        
        # 5. Palavras-chave
        palavras_chave = self._extrair_palavras_chave(tokens_limpos)
        
        # 6. Análise de tempo verbal
        tempo_verbal = self._detectar_tempo_verbal(texto_lower)
        
        # 7. Sentimento básico
        sentimento = self._analisar_sentimento_basico(texto_lower)
        
        return AnaliseNLP(
            tokens_limpos=tokens_limpos,
            entidades_nomeadas=entidades,
            palavras_chave=palavras_chave,
            correcoes_sugeridas=correcoes['correcoes_aplicadas'],
            similaridades=similaridades,
            negacoes_detectadas=negacoes,
            tempo_verbal=tempo_verbal,
            sentimento=sentimento
        )
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Alias para analisar_com_nlp para compatibilidade"""
        resultado = self.analisar_com_nlp(text)
        
        # Converter AnaliseNLP para dict
        return {
            'entities': resultado.entidades_nomeadas,
            'keywords': resultado.palavras_chave,
            'sentiment': resultado.sentimento,
            'complexity': 1.0, # Placeholder, as confianca_analise is not in AnaliseNLP
            'tokens': resultado.tokens_limpos,
            'corrections': resultado.correcoes_sugeridas,
            'similarity_scores': resultado.similaridades,
            'verb_tense': resultado.tempo_verbal,
            'confidence': 1.0
        }
    
    def _aplicar_correcoes(self, texto: str) -> Dict[str, Any]:
        """Aplica correções ortográficas comuns"""
        texto_corrigido = texto
        correcoes_aplicadas = {}
        
        # Aplicar correções diretas
        for erro, correcao in self.correcoes_comuns.items():
            if erro in texto_corrigido:
                texto_corrigido = texto_corrigido.replace(erro, correcao)
                correcoes_aplicadas[erro] = correcao
        
        # Correções com fuzzy matching se disponível
        if FUZZY_AVAILABLE:
            palavras = texto_corrigido.split()
            palavras_corrigidas = []
            
            for palavra in palavras:
                # Verificar se palavra precisa correção
                if len(palavra) > 3:  # Apenas palavras maiores
                    melhores = process.extractOne(
                        palavra, 
                        list(self.correcoes_comuns.values()),
                        scorer=fuzz.ratio
                    )
                    if melhores and melhores[1] > 85:  # 85% de similaridade
                        palavras_corrigidas.append(melhores[0])
                        if palavra != melhores[0]:
                            correcoes_aplicadas[palavra] = melhores[0]
                    else:
                        palavras_corrigidas.append(palavra)
                else:
                    palavras_corrigidas.append(palavra)
            
            texto_corrigido = " ".join(palavras_corrigidas)
        
        return {
            'texto_corrigido': texto_corrigido,
            'correcoes_aplicadas': correcoes_aplicadas
        }
    
    def _tokenizar_spacy(self, texto: str) -> List[str]:
        """Tokenização usando SpaCy"""
        doc = nlp(texto)
        # Remover stopwords e pontuação
        tokens = [
            token.text.lower() for token in doc 
            if not token.is_stop and not token.is_punct and len(token.text) > 1
        ]
        return tokens
    
    def _tokenizar_basico(self, texto: str) -> List[str]:
        """Tokenização básica sem SpaCy"""
        # Remover pontuação
        texto_limpo = re.sub(r'[^\w\s]', ' ', texto)
        # Dividir e filtrar
        palavras = texto_limpo.lower().split()
        # Remover stopwords básicas
        stopwords_basicas = {'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'uma'}
        return [p for p in palavras if p not in stopwords_basicas and len(p) > 1]
    
    def _extrair_entidades_spacy(self, texto: str) -> List[Dict[str, str]]:
        """Extrai entidades nomeadas usando SpaCy"""
        if not NLP_SPACY_AVAILABLE:
            return []
        
        doc = nlp(texto)
        entidades = []
        
        for ent in doc.ents:
            entidades.append({
                'texto': ent.text,
                'tipo': ent.label_,
                'inicio': ent.start_char,
                'fim': ent.end_char
            })
        
        return entidades
    
    def _detectar_negacoes(self, tokens: List[str]) -> List[str]:
        """Detecta palavras de negação no contexto"""
        negacoes_encontradas = []
        
        for i, token in enumerate(tokens):
            if token in self.palavras_negacao:
                # Capturar contexto (palavra anterior e próxima)
                contexto = []
                if i > 0:
                    contexto.append(tokens[i-1])
                contexto.append(token)
                if i < len(tokens) - 1:
                    contexto.append(tokens[i+1])
                
                negacoes_encontradas.append(" ".join(contexto))
        
        return negacoes_encontradas
    
    def _calcular_similaridades(self, texto: str) -> Dict[str, float]:
        """Calcula similaridade com termos importantes"""
        if not FUZZY_AVAILABLE:
            return {}
        
        similaridades = {}
        termos_importantes = [
            "entregas atrasadas",
            "pedidos pendentes", 
            "relatório excel",
            "status do sistema",
            "problemas urgentes"
        ]
        
        for termo in termos_importantes:
            score = fuzz.partial_ratio(texto.lower(), termo)
            if score > 60:  # Apenas similaridades relevantes
                similaridades[termo] = score / 100.0
        
        return similaridades
    
    def _extrair_palavras_chave(self, tokens: List[str]) -> List[str]:
        """Extrai palavras-chave mais importantes"""
        # Palavras importantes para o domínio
        palavras_dominio = {
            'entrega', 'entregas', 'pedido', 'pedidos', 'cliente', 'clientes',
            'frete', 'fretes', 'atraso', 'atrasado', 'atrasada', 'pendente',
            'urgente', 'problema', 'relatório', 'excel', 'assai', 'atacadão',
            'carrefour', 'transportadora', 'nota', 'fiscal', 'cte'
        }
        
        # Filtrar apenas palavras relevantes
        palavras_chave = []
        for token in tokens:
            # Verificar match direto
            if token in palavras_dominio:
                palavras_chave.append(token)
            # Verificar sinônimos
            else:
                for termo, sinonimos in self.sinonimos.items():
                    if token in sinonimos:
                        palavras_chave.append(termo)
                        break
        
        # Remover duplicatas mantendo ordem
        palavras_unicas = []
        for palavra in palavras_chave:
            if palavra not in palavras_unicas:
                palavras_unicas.append(palavra)
        
        return palavras_unicas
    
    def _detectar_tempo_verbal(self, texto: str) -> str:
        """Detecta tempo verbal predominante"""
        # Indicadores simples
        if any(palavra in texto for palavra in ['foi', 'eram', 'estava', 'tinha', 'fez']):
            return "passado"
        elif any(palavra in texto for palavra in ['será', 'vai', 'irá', 'quando', 'previsão']):
            return "futuro"
        else:
            return "presente"
    
    def _analisar_sentimento_basico(self, texto: str) -> str:
        """Análise básica de sentimento"""
        palavras_negativas = {'problema', 'erro', 'atraso', 'urgente', 'crítico', 'falha', 'ruim'}
        palavras_positivas = {'bom', 'ótimo', 'excelente', 'perfeito', 'sucesso', 'ok'}
        
        score_negativo = sum(1 for palavra in palavras_negativas if palavra in texto)
        score_positivo = sum(1 for palavra in palavras_positivas if palavra in texto)
        
        if score_negativo > score_positivo:
            return "negativo"
        elif score_positivo > score_negativo:
            return "positivo"
        else:
            return "neutro"

# Singleton
_nlp_analyzer = None

def get_nlp_analyzer() -> NLPEnhancedAnalyzer:
    """Retorna instância singleton do analisador NLP"""
    global _nlp_analyzer
    if _nlp_analyzer is None:
        _nlp_analyzer = NLPEnhancedAnalyzer()
    return _nlp_analyzer

# FUNÇÃO GET_ ÓRFÃ CRÍTICA - ESTAVA FALTANDO!
def get_nlp_enhanced_analyzer() -> NLPEnhancedAnalyzer:
    """Retorna instância do analisador NLP avançado - FUNÇÃO ÓRFÃ RECUPERADA"""
    return get_nlp_analyzer() 