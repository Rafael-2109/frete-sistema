
"""
AIResolverService - Resolucao inteligente via Claude Haiku 4.5
===============================================================

Usa Claude Haiku 4.5 (claude-haiku-4-5-20251001) para:
1. De-Para de Produtos - Identificar nosso codigo a partir do codigo/descricao do cliente
2. NF de Venda Original - Extrair numero da NF das observacoes em texto livre
3. Motivo da Devolucao - Identificar motivo a partir das observacoes
4. Unidade de Medida - Normalizar unidades (CXA1, UNI9 → Caixa, Unidade)

Custo estimado: ~$0.003/chamada (muito baixo)

AUTOR: Sistema de Fretes - Modulo Devolucoes
DATA: 30/12/2024
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio

import anthropic

from app import db
from app.devolucao.models import NFDevolucaoLinha, DeParaProdutoCliente
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Modelo Haiku 4.5 para custo baixo
HAIKU_MODEL = "claude-haiku-4-5-20251001"


# =============================================================================
# DATACLASSES PARA RESULTADOS
# =============================================================================

@dataclass
class ProdutoSugestao:
    """Sugestao de produto do De-Para"""
    codigo_interno: str
    nome_interno: str
    confianca: float  # 0.0 a 1.0
    justificativa: str
    # Campos de conversao (opcional)
    fator_conversao: Optional[float] = None  # Ex: 1.0 = mesmo, 12.0 = 1 CX = 12 UN
    unidade_medida_cliente: Optional[str] = None  # UN, CX, KG
    unidade_medida_nosso: Optional[str] = None  # CX (normalmente vendemos em caixas)


@dataclass
class ResultadoResolucaoProduto:
    """Resultado da resolucao de produto"""
    sucesso: bool
    confianca: float  # ALTA (>0.9), MEDIA (0.5-0.9), BAIXA (<0.5)
    sugestao_principal: Optional[ProdutoSugestao]
    outras_sugestoes: List[ProdutoSugestao]
    requer_confirmacao: bool
    mensagem: str
    metodo_resolucao: str = 'SMART_FILTER'  # DEPARA, SMART_FILTER, DEPARA_GRUPO


@dataclass
class ResultadoExtracaoObservacao:
    """Resultado da extracao de observacoes"""
    numero_nf_venda: Optional[str]  # Mantido para compatibilidade (primeira NF)
    numeros_nf_venda: List[str]  # Lista de TODAS as NFs encontradas
    motivo_sugerido: Optional[str]
    descricao_motivo: Optional[str]
    confianca: float
    texto_original: str


@dataclass
class ResultadoNormalizacaoUnidade:
    """Resultado da normalizacao de unidade"""
    unidade_original: str
    tipo: str  # CAIXA, UNIDADE, PESO, OUTRO
    fator_conversao: Optional[float]
    confianca: float


# =============================================================================
# GLOSSARIO DE ABREVIACOES
# =============================================================================

GLOSSARIO_PRODUTOS = """
=== GLOSSARIO DE ABREVIACOES DA NACOM GOYA ===

EMBALAGENS (sufixo apos gramatura):
- VD = Vidro (ex: VD 100G = vidro de 100g)
- POUCH = Sachet/Pouch plastico
- BD = Balde (ex: BD 2KG = balde de 2kg)
- BD IND = Balde Industrial
- BR / BARRICA = Barrica grande
- GL / GALAO = Galao
- PET = Embalagem PET
- SACH / SACHET = Sache pequeno
- LATA = Lata

NOMES POPULARES (importante!):
- PEPININHO = PEPINO (nao confundir com PICLES)

MATERIAS-PRIMAS:
- AZ = Azeitona
- AZ VF = Azeitona Verde Fatiada
- AZ VSC / S/CAR = Azeitona Verde Sem Caroco
- AZ VI = Azeitona Verde Inteira
- AZ PF = Azeitona Preta Fatiada
- AZ PI = Azeitona Preta Inteira
- AZ VR = Azeitona Verde Recheada
- CF = Cogumelo Fatiado
- CI = Cogumelo Inteiro
- PIQ / BIQUINHO = Pimenta Biquinho
- PESSEGO = Pessego

MARCAS (aparecem no final do nome):
- CAMPO BELO / C BELO / CB = Marca principal (se nao houver marca, assume Campo Belo)
- LA FAMIGLIA = Marca La Famiglia
- ST ISABEL = Marca St Isabel
- CASABLANCA = Marca Casablanca
- DOM GAMEIRO = Marca Dom Gameiro
- MEZZANI = Marca Mezzani
- BENASSI = Marca Benassi
- IMPERIAL = Marca Imperial
- OUTBACK = Marca Outback
- BIDOLUX = Marca Bidolux
- COPACKER = Producao terceirizada
- INDUSTRIA / IND = Destinado a industria (B2B)

FORMATO DO NOME DO PRODUTO:
[PRODUTO] [TIPO] - [EMBALAGEM] [QTD_CX]X[GRAMATURA] [UNID] - [MARCA]

Exemplo: "AZEITONA VERDE FATIADA - POUCH 18X150 GR - CAMPO BELO"
- Produto: Azeitona Verde
- Tipo: Fatiada
- Embalagem: Pouch
- Quantidade na caixa: 18 unidades
- Gramatura: 150g cada
- Marca: Campo Belo

CONVERSAO DE UNIDADES:
- Nomes como "12X200 G" significam: 12 unidades de 200g na caixa
- Se cliente envia em UNIDADE (UN), dividir pela qtd na caixa para obter CAIXAS
- Se cliente envia em KG, dividir pelo peso total da caixa

ESTADOS DA MATERIA-PRIMA (importante!):
- FATIADA / FAT = Cortada em fatias
- INTEIRA / INT = Produto inteiro
- PICADA = Picado em pedacos
- TRITURADA = Triturada
- SEM CAROCO / S/CAR / S CAR / S C= Sem o caroco
- COM CAROCO / C CAR / C/CAR / INTEIRA = Com o caroco (produto inteiro)
- RECHEADA / RECH = Recheada com pimentao/outros

ABREVIACOES COMPOSTAS CRITICAS (clientes costumam usar):
- "S CAR" = "SEM CAROCO" = Produto sem o caroco
- "C CAR" = "COM CAROCO" = Mesmo que INTEIRA (produto inteiro com caroco)
- "S/CAR" = "SEM CAROCO" = Alternativa com barra
- "C/CAR" = "COM CAROCO" = Alternativa com barra
"""

# =============================================================================
# PROMPTS ESPECIALIZADOS
# =============================================================================

PROMPT_DEPARA_PRODUTO = """Voce e um especialista em produtos alimenticios da Nacom Goya.

{glossario}

=== CONTEXTO ===
- A Nacom Goya comercializa: azeitonas, cogumelos, palmitos, pessegos, pimentas, condimentos
- Cada cliente usa codigos e descricoes PROPRIOS para nossos produtos
- Precisamos mapear o codigo/descricao do CLIENTE para o NOSSO codigo interno

=== PRODUTO DO CLIENTE ===
Codigo cliente: {codigo_cliente}
Descricao cliente: {descricao_cliente}
CNPJ (prefixo): {prefixo_cnpj}
Unidade cliente: {unidade_cliente}
Quantidade: {quantidade}

{historico_faturamento}

=== NOSSOS PRODUTOS CANDIDATOS ===
{produtos_candidatos}

=== PASSO 1: EXTRAIR INFORMACOES DO PRODUTO DO CLIENTE ===
Analise a descricao do cliente e extraia:
- MATERIA_PRIMA: cogumelo, azeitona, palmito, pimenta, pessego, etc.
- ESTADO: fatiado (FAT), inteiro (INT), picado, sem caroco, recheado
- EMBALAGEM: VD (vidro), POUCH (sachet), BD (balde), LATA, PET
- GRAMATURA: extrair o numero exato (100G, 180G, 200G, 500G, 2KG, etc.)
- MARCA: Campo Belo (default), Mezzani, Benassi, etc.

Exemplo: "COGUMELO CAMPO BELO FAT VD 100G"
- MATERIA_PRIMA: cogumelo
- ESTADO: fatiado (FAT)
- EMBALAGEM: VD (vidro)
- GRAMATURA: 100G  <-- NUMERO EXATO, NAO APROXIMAR
- MARCA: Campo Belo

=== PASSO 2: REGRAS DE MATCHING (ORDEM DE PRIORIDADE) ===

**REGRA CRITICA #1 - GRAMATURA E OBRIGATORIA:**
A gramatura da embalagem primaria DEVE ser IDENTICA.
- 100G != 180G != 200G != 500G
- Se cliente pede 100G, SOMENTE produtos de 100G sao aceitos
- NUNCA sugira gramatura diferente, mesmo que seja "proxima"
- Se nao existir produto com gramatura EXATA, retorne null

**REGRA #2 - Materia-prima deve ser igual:**
- Cogumelo com cogumelo, azeitona com azeitona, etc.

**REGRA #3 - Estado deve ser igual (CRITICA!):**
- Fatiado com fatiado, inteiro com inteiro, sem caroco com sem caroco
- Se cliente diz "C CAR" (COM CAROCO) → SOMENTE produtos INTEIRA
- Se cliente diz "S CAR" (SEM CAROCO) → SOMENTE produtos SEM CAROCO
- NUNCA misture estados: "SEM CAROCO" e "INTEIRA" sao DIFERENTES!

**REGRA #4 - Embalagem deve ser igual:**
- VD com VD, POUCH com POUCH, BD com BD

**REGRA #5 - Historico de faturamento:**
- Se produto aparece no historico E atende regras acima, priorizar

=== PASSO 3: VALIDAR MATCH ===
Antes de retornar, VERIFIQUE:
1. A gramatura do candidato eh EXATAMENTE igual a do cliente?
2. A materia-prima eh a mesma?
3. O estado (fatiado/inteiro) eh o mesmo?
4. A embalagem eh a mesma?

Se qualquer item falhar (especialmente gramatura), NAO sugira esse produto.

=== RESPONDA EM JSON ===
{{
    "analise_cliente": {{
        "materia_prima": "cogumelo|azeitona|palmito|...",
        "estado": "fatiado|inteiro|picado|...",
        "embalagem": "VD|POUCH|BD|LATA|...",
        "gramatura": "100G|180G|200G|..." ,
        "marca": "CAMPO BELO|MEZZANI|..."
    }},
    "codigo_interno": "CODIGO_NOSSO ou null se nao encontrar MATCH EXATO",
    "confianca": 0.0 a 1.0,
    "justificativa": "Explicacao detalhada - se nao encontrou, dizer PORQUE",
    "gramatura_match": true ou false,
    "unidade_detectada": "CAIXA|UNIDADE|KG",
    "qtd_convertida_caixas": null ou numero,
    "outras_opcoes": [
        {{"codigo": "...", "confianca": 0.X, "motivo": "...", "gramatura": "..."}}
    ]
}}

=== NIVEIS DE CONFIANCA ===
- 0.95+: Match perfeito (TODOS os criterios iguais, especialmente gramatura)
- 0.85-0.94: Match provavel (gramatura OK, 1 diferenca menor como marca)
- 0.70-0.84: Incerto (gramatura OK mas embalagem diferente)
- <0.50: REJEITAR (gramatura diferente = sempre baixa confianca)

**IMPORTANTE: Se gramatura for diferente, confianca MAXIMA eh 0.40 e deve ir em outras_opcoes, NAO como codigo_interno principal.**

SE NAO ENCONTRAR produto com gramatura EXATA, retorne codigo_interno: null"""

PROMPT_EXTRAIR_OBSERVACAO = """Voce e um especialista em logistica de devolucoes.

TAREFA:
Extrair informacoes estruturadas das observacoes de uma NFD (Nota Fiscal de Devolucao).

OBSERVACOES/TEXTO:
{texto_observacao}

EXTRAIA:
1. NUMEROS DAS NFs DE VENDA ORIGINAIS (as NFs que o cliente esta devolvendo)
   - UMA DEVOLUCAO PODE REFERENCIAR MULTIPLAS NFs DE VENDA!
   - Pode aparecer como: "REF NF", "NF:", "NOTA", "REFERENTE", "NFS", etc.
   - Sao numeros de 4 a 6 digitos
   - Exemplos:
     * "REF NF 123456" -> ["123456"]
     * "DEVOLUCAO NFS 1234, 1235, 1236" -> ["1234", "1235", "1236"]
     * "NF 5678 E NF 5679" -> ["5678", "5679"]
     * "NOTAS 111/222/333" -> ["111", "222", "333"]

2. MOTIVO DA DEVOLUCAO (categorize):
   - AVARIA: Produto danificado, quebrado, amassado, vazando, estourado
   - QUALIDADE: Problema de qualidade, sem condições de comercialização
   - VENCIDO: Produto vencido, proximo vencimento, data curta
   - FALTA: Faltou mercadoria, quantidade menor que pedido
   - SOBRA: Sobrou mercadoria, quantidade maior que pedido
   - PRODUTO_ERRADO: Produto diferente do pedido, item trocado
   - PEDIDO_CANCELADO: Cliente cancelou pedido
   - CLIENTE_RECUSOU: Cliente recusou entrega, nao quis receber
   - COMERCIAL: Acordo comercial com o cliente, problema na negociação, desconto, etc.
   - PROBLEMA_FISCAL: SOMENTE quando ha ERRO na nota fiscal (CFOP errado, NCM errado, tributacao incorreta, nota rejeitada, cancelamento de nota). ATENCAO: Mencao de tributos como ICMS/IPI/PIS/COFINS na descricao NAO significa problema fiscal - sao apenas dados informativos da NF.
   - OUTROS: Nao se encaixa nos anteriores

3. DESCRICAO DO MOTIVO (texto livre resumido)

RESPONDA EM JSON:
{{
    "numeros_nf_venda": ["123456", "123457"],
    "motivo_sugerido": "AVARIA|QUALIDADE|VENCIDO|FALTA|...",
    "descricao_motivo": "Resumo do motivo",
    "confianca": 0.0 a 1.0
}}

IMPORTANTE:
- numeros_nf_venda DEVE SER UMA LISTA (array), mesmo que contenha apenas 1 NF
- Se nao encontrar NFs, retorne lista vazia []
- Nao invente numeros. So extraia o que realmente aparece no texto."""

PROMPT_NORMALIZAR_UNIDADE = """Voce e um especialista em unidades de medida de produtos alimenticios.

TAREFA:
Normalizar unidades de medida usadas por clientes.

UNIDADE DO CLIENTE: {unidade_cliente}

CATEGORIZE EM:
- CAIXA: CX, CXA, CAIXA, CXA1, CXA2, BOX, FD, FARDO, PCT, PACOTE, etc.
- UNIDADE: UN, UNI, UNID, UNI9, PC, PECA, UND, BD, BD1, BD2, BALDE, SC, SACO, etc.
- PESO: KG, GR, G, GRAMAS, QUILOS, TON, etc.
- OUTRO: Nao identificado

RESPONDA EM JSON:
{{
    "tipo": "CAIXA|UNIDADE|PESO|OUTRO",
    "fator_conversao": 1.0 (ou o numero de unidades por caixa caso seja unidade, pois nós vendemos por caixa),
    "confianca": 0.0 a 1.0
}}"""

PROMPT_EXTRAIR_TERMOS_BUSCA = """Voce e um especialista em produtos alimenticios (azeitonas, cogumelos, palmitos, pimentas, pessegos).

TAREFA:
Extrair termos de busca SQL ILIKE a partir da descricao do produto do cliente.

DESCRICAO DO CLIENTE: {descricao_cliente}
CODIGO DO CLIENTE: {codigo_cliente}

EXTRAIA termos para buscar em nosso banco de dados.
Gere termos PARCIAIS para capturar variacoes (ex: "RECHEA" pega "RECHEADA" e "RECHEADAS").

EXEMPLOS:
- "AZEITONA VERDE CAMPO BELO 180G RECHEADAS" -> ["AZEITONA", "180", "RECHEA"]
- "COG FAT VD 100G CB" -> ["COGUMELO", "FAT", "100"]
- "PALMITO PUPUNHA INTEIRO 300G" -> ["PALMITO", "PUPUNHA", "300", "INTEIR"]
- "AZ VF POUCH 500G MEZZANI" -> ["AZEITONA", "FATIA", "500", "POUCH", "MEZZANI"]
- "AZEITONA VERDE CAMPO BELO 1,010KG COM CAROCO" -> ["AZEITONA", "INTEIR", "1,01", "CAMPO BELO"]
- "CHAMPIGNON CAMPO BELO 1,010KG FATIADO" -> ["COGUMELO", "FATIA", "1,01", "CAMPO BELO"]

REGRAS:
1. SEMPRE inclua a materia-prima expandida (AZ->AZEITONA, COG->COGUMELO, PALM->PALMITO, CHAMPIGNON->COGUMELO)
2. GRAMATURA E CRITICA: Inclua gramatura exata (180G->"180", 1,010KG->"1,01", 2KG->"2")
3. Inclua estado do produto parcial (RECHEA, FATIA, INTEIR, PICAD, SEM CAROCO)
4. "COM CAROCO" = INTEIRA (a azeitona inteira tem caroco)
5. Inclua embalagem se relevante (VD, POUCH, BD, LATA)
6. Inclua marca se presente (CAMPO BELO, MEZZANI, BENASSI)
7. Gere 3-5 termos mais importantes
8. Ordene por importancia (materia-prima primeiro, GRAMATURA segundo)

RESPONDA EM JSON:
{{
    "termos": ["TERMO1", "TERMO2", "TERMO3"],
    "materia_prima": "AZEITONA|COGUMELO|PALMITO|PIMENTA|PESSEGO|null"
}}"""


# =============================================================================
# SERVICE PRINCIPAL
# =============================================================================

class AIResolverService:
    """
    Service para resolucao inteligente usando Claude Haiku 4.5.

    Uso:
        service = AIResolverService()

        # Resolver produto
        resultado = service.resolver_produto(
            codigo_cliente="7896",
            descricao_cliente="AZEITONA VERDE FATIADA",
            prefixo_cnpj="93209760"
        )

        # Extrair observacao
        resultado = service.extrair_observacao(
            "DEVOLUCAO REF NF 123456 - PRODUTO AVARIADO"
        )

        # Normalizar unidade
        resultado = service.normalizar_unidade("CXA1")
    """

    def __init__(self):
        """Inicializa cliente Anthropic."""
        self._client = None

    def _get_client(self) -> anthropic.Anthropic:
        """Lazy loading do cliente Anthropic."""
        if self._client is None:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY nao configurada")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    # =========================================================================
    # RESOLUCAO DE PRODUTO (De-Para)
    # =========================================================================

    def resolver_produto(
        self,
        codigo_cliente: str,
        descricao_cliente: str,
        prefixo_cnpj: str,
        unidade_cliente: str = None,
        quantidade: float = None,
        limite_candidatos: int = 20
    ) -> ResultadoResolucaoProduto:
        """
        Resolve codigo do cliente para nosso codigo interno.

        Fluxo:
        1. Busca De-Para existente
        2. Se nao encontrar, busca produtos candidatos via resolver_entidades
        3. Busca historico de faturamento para o CNPJ
        4. Envia para Haiku analisar com contexto completo
        5. Retorna sugestoes com nivel de confianca

        Args:
            codigo_cliente: Codigo do produto usado pelo cliente
            descricao_cliente: Descricao do produto do cliente
            prefixo_cnpj: Prefixo CNPJ (8 digitos) do cliente
            unidade_cliente: Unidade de medida da NFD (UN, CX, KG)
            quantidade: Quantidade na NFD
            limite_candidatos: Maximo de candidatos a enviar para Haiku

        Returns:
            ResultadoResolucaoProduto com sugestoes
        """
        try:
            # =========================================================
            # 0. De-Para especifico para grupos empresariais (Atacadao/Assai)
            # =========================================================
            # Verifica se o CNPJ pertence a um grupo e busca nas tabelas especificas
            # ANTES do De-Para generico para priorizar mapeamentos especializados
            # =========================================================
            depara_grupo = self._buscar_depara_grupo_empresarial(codigo_cliente, prefixo_cnpj)
            if depara_grupo:
                # Buscar nome completo do produto no CadastroPalletizacao
                nome_produto = None
                try:
                    from app.producao.models import CadastroPalletizacao
                    produto = CadastroPalletizacao.query.filter_by(
                        cod_produto=depara_grupo['nosso_codigo']
                    ).first()
                    if produto:
                        nome_produto = produto.nome_produto
                except Exception:
                    pass

                # Montar justificativa com info de conversao se houver
                fator = depara_grupo.get('fator_conversao', 1.0)
                justificativa = f"De-Para {depara_grupo['grupo'].upper()} (deterministico)"
                if fator and fator != 1.0:
                    justificativa += f" | Fator conversao: {fator}"

                return ResultadoResolucaoProduto(
                    sucesso=True,
                    confianca=1.0,  # Deterministico = 100%
                    sugestao_principal=ProdutoSugestao(
                        codigo_interno=depara_grupo['nosso_codigo'],
                        nome_interno=nome_produto or depara_grupo.get('descricao_nosso', ''),
                        confianca=1.0,
                        justificativa=justificativa,
                        fator_conversao=fator,
                        unidade_medida_cliente=depara_grupo.get('unidade_medida_cliente'),
                        unidade_medida_nosso=depara_grupo.get('unidade_medida_nosso')
                    ),
                    outras_sugestoes=[],
                    requer_confirmacao=False,
                    mensagem=f"Produto encontrado no De-Para {depara_grupo['grupo'].upper()}",
                    metodo_resolucao='DEPARA_GRUPO'
                )

            # =========================================================
            # 1. Verificar De-Para generico existente
            # =========================================================
            depara_existente = DeParaProdutoCliente.query.filter_by(
                prefixo_cnpj=prefixo_cnpj[:8],
                codigo_cliente=codigo_cliente,
                ativo=True
            ).first()

            if depara_existente:
                # Montar justificativa com info de conversao se houver
                fator = float(depara_existente.fator_conversao) if depara_existente.fator_conversao else 1.0
                justificativa = 'De-Para cadastrado'
                if fator != 1.0:
                    justificativa += f" | Fator conversao: {fator}"

                return ResultadoResolucaoProduto(
                    sucesso=True,
                    confianca=1.0,
                    sugestao_principal=ProdutoSugestao(
                        codigo_interno=depara_existente.nosso_codigo,
                        nome_interno=depara_existente.descricao_nosso or '',
                        confianca=1.0,
                        justificativa=justificativa,
                        fator_conversao=fator,
                        unidade_medida_cliente=depara_existente.unidade_medida_cliente,
                        unidade_medida_nosso=depara_existente.unidade_medida_nosso
                    ),
                    outras_sugestoes=[],
                    requer_confirmacao=False,
                    mensagem='Produto encontrado no De-Para',
                    metodo_resolucao='DEPARA'
                )

            # =========================================================
            # 2. SMART FILTER MODE - Pre-filtragem inteligente + Haiku
            # =========================================================
            # Estrategia otimizada (01/01/2026):
            # - Haiku extrai termos de busca da descricao do cliente
            # - Filtra produtos no banco usando esses termos (ILIKE)
            # - Envia lista focada (~10-50 produtos) para analise final
            # - Fallback progressivo: relaxa termos se necessario
            # Motivo: LIBERDADE TOTAL com 546 produtos confundia o modelo
            # =========================================================

            logger.info("[AI_RESOLVER] Iniciando SMART FILTER mode")

            # 2a. Buscar produtos PRE-FILTRADOS usando Haiku
            todos_produtos = self._buscar_produtos_prefiltrados(
                descricao_cliente=descricao_cliente,
                codigo_cliente=codigo_cliente,
                limite=50
            )

            # 2b. Buscar TODO o historico de faturamento do CNPJ
            historico_completo = self._buscar_historico_completo(prefixo_cnpj)

            if not todos_produtos:
                return ResultadoResolucaoProduto(
                    sucesso=False,
                    confianca=0.0,
                    sugestao_principal=None,
                    outras_sugestoes=[],
                    requer_confirmacao=True,
                    mensagem='Nenhum produto vendido encontrado no cadastro',
                    metodo_resolucao='SMART_FILTER'
                )

            # 2c. Formatar para o prompt do Haiku
            produtos_str = self._formatar_candidatos_amplo(todos_produtos)
            historico_str = self._formatar_historico_completo(historico_completo)

            # Usar todos os produtos para busca de nome depois
            candidatos = todos_produtos

            prompt = PROMPT_DEPARA_PRODUTO.format(
                glossario=GLOSSARIO_PRODUTOS,
                codigo_cliente=codigo_cliente,
                descricao_cliente=descricao_cliente,
                prefixo_cnpj=prefixo_cnpj[:8],
                unidade_cliente=unidade_cliente or 'NAO INFORMADA',
                quantidade=quantidade or 'NAO INFORMADA',
                historico_faturamento=historico_str,
                produtos_candidatos=produtos_str
            )

            client = self._get_client()

            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=1500,  # Aumentado para comportar JSON completo com justificativas
                temperature=0,  # Respostas deterministicas - evita instabilidade
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()

            # 5. Parsear resposta JSON
            resultado = self._parsear_resposta_produto(result_text, candidatos)

            logger.info(
                f"[AI_RESOLVER] Produto resolvido: {codigo_cliente} -> "
                f"{resultado.sugestao_principal.codigo_interno if resultado.sugestao_principal else 'N/A'} "
                f"(confianca: {resultado.confianca:.0%})"
            )

            return resultado

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao resolver produto: {e}")
            return ResultadoResolucaoProduto(
                sucesso=False,
                confianca=0.0,
                sugestao_principal=None,
                outras_sugestoes=[],
                requer_confirmacao=True,
                mensagem=f'Erro: {str(e)}',
                metodo_resolucao='LIBERDADE_TOTAL'
            )

    def _extrair_qtd_caixa(self, nome_produto: str) -> Optional[int]:
        """Extrai quantidade de unidades na caixa do nome do produto."""
        import re
        # Buscar padrao como "30X100", "12X200", etc.
        match = re.search(r'(\d+)[Xx]\d+', nome_produto)
        if match:
            return int(match.group(1))
        return None

    def _normalizar_unidade_deterministico(self, unidade: str) -> str:
        """
        Normaliza unidade de medida SEM usar Haiku - regras deterministicas.

        Baseado na analise de 1892 linhas de NFD no sistema:
        - CAIXA: CX, CXA, BOX, FD, FARDO, PCT, PACOTE, TAMBOR
        - UNIDADE: UN, UNI, PC, PECA, BD, BALDE, BLD, SC, SACO, PT, POTE, BL, BA, SH, SACHE
        - PESO: KG, GR, G, GRAM, QUILO, TON

        Args:
            unidade: Unidade original do cliente (ex: CXA1, UN, UND9, BD1)

        Returns:
            Tipo normalizado: CAIXA, UNIDADE, PESO ou OUTRO
        """
        if not unidade:
            return 'OUTRO'

        unidade_upper = unidade.upper().strip()

        # CAIXA (verificar primeiro - mais especifico)
        if any(u in unidade_upper for u in ['CX', 'CAIXA', 'BOX', 'FD', 'FARDO', 'PCT', 'PACOTE', 'TAMBOR']):
            return 'CAIXA'

        # UNIDADE (ordem importa - verificar padroes mais especificos primeiro)
        # Inclui: UN, UNI, UNID, UND, PC, BD, BLD, BALDE, SC, SACO, PT, POTE, BL, BA, SH
        if any(u in unidade_upper for u in ['UN', 'UNI', 'PC', 'PECA', 'PÇ', 'BD', 'BALDE', 'BLD',
                                             'SC', 'SACO', 'PT', 'POTE', 'BL', 'BA', 'SH', 'SACHE']): # noqa: E127
            return 'UNIDADE'

        # PESO
        if any(u in unidade_upper for u in ['KG', 'GR', 'GRAM', 'QUILO', 'TON']):
            return 'PESO'

        # Casos especiais - unidade de 1 caractere
        if unidade_upper == 'U':
            return 'UNIDADE'
        if unidade_upper == 'G':
            return 'PESO'

        return 'OUTRO'

    def _extrair_gramatura(self, nome_produto: str) -> Optional[str]:
        """
        Extrai a gramatura da embalagem primaria do nome do produto.

        Exemplos:
        - "COGUMELO FATIADO - VD 12X180 G" -> "180G"
        - "AZEITONA VF - POUCH 30X100 GR" -> "100G"
        - "PALMITO - BD 2KG" -> "2KG"
        - "AZEITONA - VD 200G" -> "200G"
        """
        import re
        nome = nome_produto.upper()

        # Padrao 1: NxGRAMATURA (ex: 12X180, 30X100)
        match = re.search(r'\d+[Xx](\d+)\s*(?:G|GR|KG|ML|L)\b', nome)
        if match:
            num = int(match.group(1))
            # Determinar unidade
            if 'KG' in nome[match.start():match.end()+3]:
                return f"{num}KG"
            elif 'ML' in nome[match.start():match.end()+3] or 'L' in nome[match.start():match.end()+3]:
                return f"{num}ML"
            else:
                return f"{num}G"

        # Padrao 2: GRAMATURA sozinha (ex: 200G, 2KG, 500ML)
        match = re.search(r'(\d+(?:,\d+)?)\s*(G|GR|KG|ML|L)\b', nome)
        if match:
            num = match.group(1).replace(',', '.')
            # Normalizar: remover zeros a direita (1.010 -> 1.01, 2.0 -> 2)
            try:
                num_float = float(num)
                # Formatar sem zeros desnecessarios
                if num_float == int(num_float):
                    num = str(int(num_float))
                else:
                    num = f"{num_float:g}"  # Remove trailing zeros
            except ValueError:
                pass
            unid = match.group(2)
            if unid == 'GR':
                unid = 'G'
            return f"{num}{unid}"

        return None

    def _extrair_estado(self, nome_produto: str) -> Optional[str]:
        """
        Extrai o estado do produto (fatiado, inteiro, etc).
        """
        nome = nome_produto.upper()

        if 'FATIADO' in nome or 'FATIADA' in nome or ' FAT ' in nome or nome.endswith(' FAT'):
            return 'FATIADO'
        elif 'INTEIRO' in nome or 'INTEIRA' in nome or ' INT ' in nome:
            return 'INTEIRO'
        elif 'PICADO' in nome or 'PICADA' in nome:
            return 'PICADO'
        elif 'S/CAR' in nome or 'SEM CAROCO' in nome or 'S/ CAR' in nome:
            return 'SEM CAROCO'
        elif 'RECHEA' in nome:
            return 'RECHEADA'

        return None

    def _buscar_historico_completo(self, prefixo_cnpj: str) -> List[Dict]:
        """
        HAIKU POWER MODE: Busca TODO o historico de faturamento para o CNPJ.

        Diferente da busca normal, esta funcao:
        - Nao filtra por relevancia
        - Retorna TODOS os produtos ja faturados
        - Inclui quantidade e frequencia

        Args:
            prefixo_cnpj: Prefixo do CNPJ (8 digitos)

        Returns:
            Lista de todos os produtos ja faturados para este cliente
        """
        try:
            from app.faturamento.models import FaturamentoProduto
            from sqlalchemy import func

            if not prefixo_cnpj or len(prefixo_cnpj) < 8:
                return []

            # Formatar prefixo para busca
            prefixo_limpo = prefixo_cnpj[:8].replace('.', '')
            prefixo_formatado = f"{prefixo_limpo[:2]}.{prefixo_limpo[2:5]}.{prefixo_limpo[5:8]}"

            # Buscar TODOS os produtos faturados para este CNPJ
            query = db.session.query(
                FaturamentoProduto.cod_produto,
                FaturamentoProduto.nome_produto,
                func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_total'),
                func.count(FaturamentoProduto.id).label('num_notas')
            ).filter(
                FaturamentoProduto.cnpj_cliente.like(f'{prefixo_formatado}%'),
                FaturamentoProduto.status_nf == 'Lançado'
            ).group_by(
                FaturamentoProduto.cod_produto,
                FaturamentoProduto.nome_produto
            ).order_by(
                func.sum(FaturamentoProduto.qtd_produto_faturado).desc()
            ).limit(100)  # Limite amplo

            resultados = query.all()

            produtos = []
            for r in resultados:
                produtos.append({
                    'cod_produto': r.cod_produto,
                    'nome_produto': r.nome_produto,
                    'qtd_total_faturada': float(r.qtd_total or 0),
                    'num_notas': r.num_notas
                })

            logger.info(f"[AI_RESOLVER] Historico completo: Encontrados {len(produtos)} produtos faturados")
            return produtos

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao buscar historico completo: {e}")
            return []

    def _buscar_todos_produtos_vendidos(self) -> List[Dict]:
        """
        LIBERDADE TOTAL: Busca TODOS os produtos vendidos sem nenhum filtro.

        Diferente da busca ampla, esta funcao:
        - NAO filtra por descricao
        - NAO filtra por termos
        - Retorna TODOS os produtos com produto_vendido=True

        Isso maximiza o contexto para o Haiku decidir com total liberdade.

        Returns:
            Lista de todos os produtos vendidos com informacoes completas
        """
        try:
            from app.producao.models import CadastroPalletizacao

            # Buscar TODOS os produtos vendidos
            produtos = CadastroPalletizacao.query.filter_by(
                produto_vendido=True,
                ativo=True
            ).all()

            # Formatar resultados com informacoes completas
            resultados = []
            for prod in produtos:
                resultados.append({
                    'cod_produto': prod.cod_produto,
                    'nome_produto': prod.nome_produto,
                    'categoria_produto': prod.categoria_produto,
                    'tipo_materia_prima': prod.tipo_materia_prima,
                    'tipo_embalagem': prod.tipo_embalagem,
                    'subcategoria': prod.subcategoria,
                    'palletizacao': float(prod.palletizacao) if prod.palletizacao else 0,
                    'peso_bruto': float(prod.peso_bruto) if prod.peso_bruto else 0
                })

            logger.info(f"[AI_RESOLVER] LIBERDADE TOTAL: Carregados {len(resultados)} produtos vendidos")
            return resultados

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao buscar todos produtos vendidos: {e}")
            return []

    def _extrair_termos_busca(
        self,
        descricao_cliente: str,
        codigo_cliente: str = ''
    ) -> Dict:
        """
        Usa Haiku para extrair termos de busca da descricao do cliente.

        O Haiku analisa a descricao e gera termos ILIKE para filtrar
        produtos no banco de dados.

        Args:
            descricao_cliente: Descricao do produto do cliente
            codigo_cliente: Codigo do produto (opcional)

        Returns:
            Dict com 'termos' (lista) e 'materia_prima' (str ou None)
        """
        try:
            if not descricao_cliente or len(descricao_cliente.strip()) < 3:
                return {'termos': [], 'materia_prima': None}

            prompt = PROMPT_EXTRAIR_TERMOS_BUSCA.format(
                descricao_cliente=descricao_cliente,
                codigo_cliente=codigo_cliente or 'N/A'
            )

            client = self._get_client()
            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text.strip()
            dados = self._extrair_json(result_text)

            termos = dados.get('termos', [])
            if not isinstance(termos, list):
                termos = [termos] if termos else []

            resultado = {
                'termos': termos,
                'materia_prima': dados.get('materia_prima')
            }

            logger.info(
                f"[AI_RESOLVER] Termos extraidos: {resultado['termos']} "
                f"(materia-prima: {resultado['materia_prima']})"
            )

            return resultado

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao extrair termos de busca: {e}")
            return {'termos': [], 'materia_prima': None}

    def _buscar_produtos_prefiltrados(
        self,
        descricao_cliente: str,
        codigo_cliente: str = '',
        limite: int = 50
    ) -> List[Dict]:
        """
        SMART FILTER: Busca produtos usando termos gerados pelo Haiku.

        Fluxo:
        1. Haiku extrai termos de busca da descricao
        2. Filtra produtos no banco com ILIKE
        3. Se poucos resultados, relaxa os termos
        4. Retorna lista focada de candidatos

        Args:
            descricao_cliente: Descricao do produto do cliente
            codigo_cliente: Codigo do produto (opcional)
            limite: Maximo de produtos a retornar

        Returns:
            Lista de produtos candidatos
        """
        try:
            from app.producao.models import CadastroPalletizacao

            # 1. Haiku extrai termos de busca
            termos_result = self._extrair_termos_busca(descricao_cliente, codigo_cliente)
            termos = termos_result.get('termos', [])
            materia_prima = termos_result.get('materia_prima')

            if not termos:
                logger.warning("[AI_RESOLVER] Nenhum termo extraido, usando fallback")
                return self._buscar_todos_produtos_vendidos()[:limite]

            # 2. Busca progressiva: começa com todos os termos, relaxa se necessário
            for num_termos in range(len(termos), 0, -1):
                termos_busca = termos[:num_termos]

                query = CadastroPalletizacao.query.filter(
                    CadastroPalletizacao.produto_vendido == True,
                    CadastroPalletizacao.ativo == True
                )

                # Aplica cada termo como ILIKE
                for termo in termos_busca:
                    query = query.filter(
                        CadastroPalletizacao.nome_produto.ilike(f'%{termo}%')
                    )

                produtos = query.limit(limite).all()

                if produtos:
                    logger.info(
                        f"[AI_RESOLVER] SMART FILTER: {len(produtos)} produtos "
                        f"encontrados com {num_termos} termos: {termos_busca}"
                    )
                    break
            else:
                # Nenhum resultado com nenhuma combinacao
                logger.warning("[AI_RESOLVER] Nenhum produto encontrado, usando fallback por materia-prima")

                # Fallback: buscar apenas pela materia-prima
                if materia_prima:
                    produtos = CadastroPalletizacao.query.filter(
                        CadastroPalletizacao.produto_vendido == True,
                        CadastroPalletizacao.ativo == True,
                        CadastroPalletizacao.nome_produto.ilike(f'%{materia_prima}%')
                    ).limit(limite).all()

                    if produtos:
                        logger.info(f"[AI_RESOLVER] Fallback por materia-prima: {len(produtos)} produtos")

                if not produtos:
                    # Ultimo fallback: todos os produtos
                    return self._buscar_todos_produtos_vendidos()[:limite]

            # 3. Formatar resultados
            resultados = []
            for prod in produtos:
                resultados.append({
                    'cod_produto': prod.cod_produto,
                    'nome_produto': prod.nome_produto,
                    'categoria_produto': prod.categoria_produto,
                    'tipo_materia_prima': prod.tipo_materia_prima,
                    'tipo_embalagem': prod.tipo_embalagem,
                    'subcategoria': prod.subcategoria,
                    'palletizacao': float(prod.palletizacao) if prod.palletizacao else 0,
                    'peso_bruto': float(prod.peso_bruto) if prod.peso_bruto else 0
                })

            return resultados

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro na busca pre-filtrada: {e}")
            return self._buscar_todos_produtos_vendidos()[:limite]

    def _buscar_depara_grupo_empresarial(
        self,
        codigo_cliente: str,
        cnpj_cliente: str
    ) -> Optional[Dict]:
        """
        Busca De-Para especifico para grupos empresariais (Atacadao/Assai).

        ANTES do De-Para generico, verifica se o CNPJ pertence a um grupo
        e busca nas tabelas especificas.

        Para Atacadao: trata prefixo "AR" + padding (ex: AR012345 -> 12345)

        Args:
            codigo_cliente: Codigo do produto do cliente
            cnpj_cliente: CNPJ completo ou prefixo do cliente

        Returns:
            Dict com nosso_codigo, descricao_nosso, fator_conversao, grupo
            ou None se nao encontrar
        """
        try:
            from app.portal.utils.grupo_empresarial import GrupoEmpresarial
            from app.portal.atacadao.models import ProdutoDeParaAtacadao
            from app.portal.sendas.models import ProdutoDeParaSendas

            grupo = GrupoEmpresarial.identificar_grupo(cnpj_cliente)

            if not grupo:
                return None

            logger.info(f"[AI_RESOLVER] Grupo empresarial identificado: {grupo}")

            if grupo == 'atacadao':
                # Tratar prefixo AR + padding
                # Exemplos: AR12345, AR012345, AR0012345
                codigo_busca = str(codigo_cliente).strip()

                # Remover prefixo AR se existir
                if codigo_busca.upper().startswith('AR'):
                    codigo_busca = codigo_busca[2:].lstrip('0')  # Remove AR e zeros a esquerda

                # Se ficou vazio, manter o original sem AR
                if not codigo_busca:
                    codigo_busca = str(codigo_cliente).strip()
                    if codigo_busca.upper().startswith('AR'):
                        codigo_busca = codigo_busca[2:]

                logger.info(f"[AI_RESOLVER] Atacadao - codigo original: {codigo_cliente}, busca: {codigo_busca}")

                # Buscar com ILIKE para cobrir variacoes de padding
                depara = ProdutoDeParaAtacadao.query.filter(
                    ProdutoDeParaAtacadao.ativo == True,
                    db.or_(
                        ProdutoDeParaAtacadao.codigo_atacadao == str(codigo_cliente),  # Match exato
                        ProdutoDeParaAtacadao.codigo_atacadao == codigo_busca,          # Sem AR/padding
                        ProdutoDeParaAtacadao.codigo_atacadao.ilike(f'%{codigo_busca}') # Termina com codigo
                    )
                ).first()

                if depara:
                    logger.info(f"[AI_RESOLVER] De-Para Atacadao encontrado: {codigo_cliente} -> {depara.codigo_nosso}")
                    return {
                        'nosso_codigo': depara.codigo_nosso,
                        'descricao_nosso': depara.descricao_nosso,
                        'fator_conversao': float(depara.fator_conversao or 1.0),
                        'grupo': 'atacadao'
                    }

            elif grupo == 'assai':
                # Busca direta - Assai nao tem prefixo especial
                nosso_codigo = ProdutoDeParaSendas.obter_nosso_codigo(str(codigo_cliente))

                if nosso_codigo:
                    depara = ProdutoDeParaSendas.query.filter_by(
                        codigo_sendas=str(codigo_cliente),
                        ativo=True
                    ).first()

                    logger.info(f"[AI_RESOLVER] De-Para Assai encontrado: {codigo_cliente} -> {nosso_codigo}")
                    return {
                        'nosso_codigo': nosso_codigo,
                        'descricao_nosso': depara.descricao_nosso if depara else None,
                        'fator_conversao': float(depara.fator_conversao or 1.0) if depara else 1.0,
                        'grupo': 'assai'
                    }

            return None

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao buscar De-Para grupo empresarial: {e}")
            return None

    def _buscar_depara_lote(
        self,
        codigos_clientes: List[str],
        prefixo_cnpj: str
    ) -> Dict[str, Dict]:
        """
        Busca De-Para em LOTE para multiplos codigos de uma vez.

        Otimizacao: 1 query para N produtos ao inves de N queries.
        NOTA: Fator de conversao sera calculado deterministicamente pela unidade.

        Args:
            codigos_clientes: Lista de codigos do cliente
            prefixo_cnpj: Prefixo CNPJ (8 digitos)

        Returns:
            Dict mapeando codigo_cliente -> resultado De-Para
        """
        resultado = {}

        if not codigos_clientes:
            return resultado

        try:
            from app.portal.utils.grupo_empresarial import GrupoEmpresarial
            from app.portal.atacadao.models import ProdutoDeParaAtacadao
            from app.portal.sendas.models import ProdutoDeParaSendas
            

            # =========================================================
            # FASE 1: Busca em lote no De-Para de grupo (Atacadao/Sendas)
            # =========================================================
            grupo = GrupoEmpresarial.identificar_grupo(prefixo_cnpj)

            if grupo == 'atacadao':
                # Preparar lista de codigos para busca (com e sem prefixo AR)
                codigos_busca = []
                mapa_original = {}  # codigo_busca -> codigo_original

                for cod in codigos_clientes:
                    cod_str = str(cod).strip()
                    codigos_busca.append(cod_str)
                    mapa_original[cod_str] = cod

                    # Adicionar versao sem AR/padding
                    if cod_str.upper().startswith('AR'):
                        cod_limpo = cod_str[2:].lstrip('0')
                        if cod_limpo:
                            codigos_busca.append(cod_limpo)
                            mapa_original[cod_limpo] = cod

                # Busca em lote com IN
                deparas = ProdutoDeParaAtacadao.query.filter(
                    ProdutoDeParaAtacadao.ativo == True,
                    ProdutoDeParaAtacadao.codigo_atacadao.in_(codigos_busca)
                ).all()

                for depara in deparas:
                    cod_original = mapa_original.get(depara.codigo_atacadao)
                    if cod_original and cod_original not in resultado:
                        resultado[cod_original] = {
                            'nosso_codigo': depara.codigo_nosso,
                            'descricao_nosso': depara.descricao_nosso,
                            'grupo': 'atacadao',
                            'metodo': 'DEPARA_GRUPO'
                        }

                logger.info(f"[AI_RESOLVER] De-Para Atacadao em lote: {len(resultado)}/{len(codigos_clientes)} encontrados")

            elif grupo == 'assai':
                # Busca em lote para Sendas/Assai
                deparas = ProdutoDeParaSendas.query.filter(
                    ProdutoDeParaSendas.ativo == True,
                    ProdutoDeParaSendas.codigo_sendas.in_([str(c) for c in codigos_clientes])
                ).all()

                for depara in deparas:
                    resultado[depara.codigo_sendas] = {
                        'nosso_codigo': depara.codigo_nosso,
                        'descricao_nosso': depara.descricao_nosso,
                        'grupo': 'assai',
                        'metodo': 'DEPARA_GRUPO'
                    }

                logger.info(f"[AI_RESOLVER] De-Para Assai em lote: {len(resultado)}/{len(codigos_clientes)} encontrados")

            # =========================================================
            # FASE 2: Busca em lote no De-Para generico (para os que faltam)
            # =========================================================
            codigos_faltantes = [c for c in codigos_clientes if c not in resultado]

            if codigos_faltantes:
                deparas_genericos = DeParaProdutoCliente.query.filter(
                    DeParaProdutoCliente.prefixo_cnpj == prefixo_cnpj[:8],
                    DeParaProdutoCliente.codigo_cliente.in_(codigos_faltantes),
                    DeParaProdutoCliente.ativo == True
                ).all()

                for depara in deparas_genericos:
                    resultado[depara.codigo_cliente] = {
                        'nosso_codigo': depara.nosso_codigo,
                        'descricao_nosso': depara.descricao_nosso,
                        'unidade_medida_cliente': depara.unidade_medida_cliente,
                        'unidade_medida_nosso': depara.unidade_medida_nosso,
                        'metodo': 'DEPARA'
                    }

                logger.info(f"[AI_RESOLVER] De-Para generico em lote: +{len(deparas_genericos)} encontrados")

            logger.info(f"[AI_RESOLVER] Total De-Para em lote: {len(resultado)}/{len(codigos_clientes)}")
            return resultado

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro na busca De-Para em lote: {e}")
            return resultado

    async def _resolver_produto_async(
        self,
        codigo_cliente: str,
        descricao_cliente: str,
        prefixo_cnpj: str,
        unidade_cliente: str = None,
        quantidade: float = None,
        semaforo: 'asyncio.Semaphore' = None
    ):
        """
        Versao async de resolver_produto para processamento paralelo.

        Args:
            semaforo: Semaforo para controlar concorrencia (evita rate limiting)
        """
        import asyncio

        if semaforo:
            async with semaforo:
                # Executar em thread pool para nao bloquear
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self.resolver_produto(
                        codigo_cliente=codigo_cliente,
                        descricao_cliente=descricao_cliente,
                        prefixo_cnpj=prefixo_cnpj,
                        unidade_cliente=unidade_cliente,
                        quantidade=quantidade
                    )
                )
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.resolver_produto(
                    codigo_cliente=codigo_cliente,
                    descricao_cliente=descricao_cliente,
                    prefixo_cnpj=prefixo_cnpj,
                    unidade_cliente=unidade_cliente,
                    quantidade=quantidade
                )
            )

    def _resolver_produtos_paralelo(
        self,
        linhas_pendentes: List[Dict],
        prefixo_cnpj: str,
        max_concurrent: int = 3
    ) -> Dict[int, 'ResultadoResolucaoProduto']:
        """
        Resolve multiplos produtos em PARALELO usando ThreadPoolExecutor.

        Args:
            linhas_pendentes: Lista de dicts com linha_id, codigo, descricao, etc.
            prefixo_cnpj: Prefixo CNPJ
            max_concurrent: Maximo de chamadas Haiku simultaneas (evita rate limit)

        Returns:
            Dict mapeando linha_id -> ResultadoResolucaoProduto
        """
        import concurrent.futures
        from flask import current_app

        if not linhas_pendentes:
            return {}

        resultados = {}

        # Capturar o app context para passar para as threads
        app = current_app._get_current_object()

        def resolver_com_contexto(linha_dict):
            """Resolve produto dentro do contexto Flask."""
            with app.app_context():
                try:
                    resultado = self.resolver_produto(
                        codigo_cliente=linha_dict['codigo'],
                        descricao_cliente=linha_dict['descricao'],
                        prefixo_cnpj=prefixo_cnpj,
                        unidade_cliente=linha_dict.get('unidade'),
                        quantidade=linha_dict.get('quantidade')
                    )
                    return (linha_dict['linha_id'], resultado)
                except Exception as e:
                    logger.error(f"[AI_RESOLVER] Erro ao resolver linha {linha_dict['linha_id']}: {e}")
                    return (linha_dict['linha_id'], ResultadoResolucaoProduto(
                        sucesso=False,
                        confianca=0.0,
                        sugestao_principal=None,
                        outras_sugestoes=[],
                        requer_confirmacao=True,
                        mensagem=f'Erro: {str(e)}',
                        metodo_resolucao='ERRO'
                    ))

        try:
            # Usar ThreadPoolExecutor com max_workers = max_concurrent
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                # Submeter todas as tarefas
                futures = [executor.submit(resolver_com_contexto, linha) for linha in linhas_pendentes]

                # Coletar resultados
                for future in concurrent.futures.as_completed(futures, timeout=120):
                    try:
                        linha_id, resultado = future.result()
                        resultados[linha_id] = resultado
                    except Exception as e:
                        logger.error(f"[AI_RESOLVER] Erro ao obter resultado: {e}")

            logger.info(f"[AI_RESOLVER] Processamento paralelo concluido: {len(resultados)}/{len(linhas_pendentes)}")
            return resultados

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro no processamento paralelo: {e}")
            # Fallback: processar sequencialmente
            for linha in linhas_pendentes:
                if linha['linha_id'] in resultados:
                    continue  # Ja processado
                try:
                    resultado = self.resolver_produto(
                        codigo_cliente=linha['codigo'],
                        descricao_cliente=linha['descricao'],
                        prefixo_cnpj=prefixo_cnpj,
                        unidade_cliente=linha.get('unidade'),
                        quantidade=linha.get('quantidade')
                    )
                    resultados[linha['linha_id']] = resultado
                except Exception as e2:
                    logger.error(f"[AI_RESOLVER] Erro fallback linha {linha['linha_id']}: {e2}")
            return resultados

    def _formatar_candidatos_amplo(self, candidatos: List[Dict]) -> str:
        """
        HAIKU POWER MODE: Formata candidatos com informacoes completas.

        Inclui categoria_produto, tipo_materia_prima, tipo_embalagem
        para dar mais contexto ao Haiku.
        """
        if not candidatos:
            return "(nenhum candidato encontrado)"

        linhas = []
        for c in candidatos:
            nome = c['nome_produto']
            gramatura = self._extrair_gramatura(nome)
            estado = self._extrair_estado(nome)

            linhas.append(
                f"- {c['cod_produto']}: {nome}\n"
                f"  >> Categoria: {c.get('categoria_produto', 'N/A')} | "
                f"Materia-prima: {c.get('tipo_materia_prima', 'N/A')} | "
                f"Embalagem: {c.get('tipo_embalagem', 'N/A')} | "
                f"Estado: {estado or 'N/A'} | "
                f"Gramatura: {gramatura or 'N/A'} | "
                f"Matches: {c.get('num_matches', 0)}"
            )

        return '\n'.join(linhas)

    def _formatar_historico_completo(self, historico: List[Dict]) -> str:
        """
        HAIKU POWER MODE: Formata historico completo de faturamento.
        """
        if not historico:
            return "=== HISTORICO COMPLETO DE FATURAMENTO ===\n(nenhum produto faturado para este cliente)"

        linhas = ["=== HISTORICO COMPLETO DE FATURAMENTO (todos os produtos ja vendidos) ==="]

        for h in historico:
            linhas.append(
                f"  * {h['cod_produto']}: {h['nome_produto']} "
                f"({h['num_notas']}x, total {h['qtd_total_faturada']:.0f} cx)"
            )

        return '\n'.join(linhas)

    def _parsear_resposta_produto(
        self,
        texto: str,
        candidatos: List[Dict],
        metodo_resolucao: str = 'LIBERDADE_TOTAL'
    ) -> ResultadoResolucaoProduto:
        """Parseia resposta JSON do Haiku."""
        try:
            # Tentar extrair JSON
            if '{' in texto:
                inicio = texto.find('{')
                fim = texto.rfind('}') + 1
                json_str = texto[inicio:fim]
                dados = json.loads(json_str)
            else:
                raise ValueError("JSON nao encontrado na resposta")

            codigo_interno = dados.get('codigo_interno')
            confianca = float(dados.get('confianca', 0))
            justificativa = dados.get('justificativa', '')

            # Buscar nome do produto usando funcao auxiliar
            nome_interno = self._buscar_nome_produto(codigo_interno, candidatos)

            # Montar sugestao principal
            sugestao_principal = None
            if codigo_interno:
                sugestao_principal = ProdutoSugestao(
                    codigo_interno=codigo_interno,
                    nome_interno=nome_interno,
                    confianca=confianca,
                    justificativa=justificativa
                )

            # Outras opcoes
            outras = []
            for opcao in dados.get('outras_opcoes', [])[:3]:
                cod = opcao.get('codigo')
                if cod and cod != codigo_interno:
                    nome = self._buscar_nome_produto(cod, candidatos)
                    outras.append(ProdutoSugestao(
                        codigo_interno=cod,
                        nome_interno=nome,
                        confianca=float(opcao.get('confianca', 0)),
                        justificativa=opcao.get('motivo', '')
                    ))

            # Determinar se requer confirmacao
            requer_confirmacao = confianca < 0.9

            return ResultadoResolucaoProduto(
                sucesso=codigo_interno is not None,
                confianca=confianca,
                sugestao_principal=sugestao_principal,
                outras_sugestoes=outras,
                requer_confirmacao=requer_confirmacao,
                mensagem='Analise concluida' if codigo_interno else 'Produto nao identificado',
                metodo_resolucao=metodo_resolucao
            )

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao parsear resposta: {e}")
            return ResultadoResolucaoProduto(
                sucesso=False,
                confianca=0.0,
                sugestao_principal=None,
                outras_sugestoes=[],
                requer_confirmacao=True,
                mensagem=f'Erro ao parsear: {e}',
                metodo_resolucao=metodo_resolucao
            )

    def _buscar_nome_produto(self, codigo: str, candidatos: List[Dict]) -> str:
        """
        Busca o nome do produto pelo codigo.

        Ordem de busca:
        1. Lista de candidatos (ja em memoria)
        2. CadastroPalletizacao (banco de dados)

        Args:
            codigo: Codigo do produto
            candidatos: Lista de candidatos ja buscados

        Returns:
            Nome do produto ou string vazia
        """
        if not codigo:
            return ''

        # 1. Buscar nos candidatos (mais rapido)
        for c in candidatos:
            if c.get('cod_produto') == codigo:
                return c.get('nome_produto', '')

        # 2. Buscar no CadastroPalletizacao
        try:
            from app.producao.models import CadastroPalletizacao
            produto = CadastroPalletizacao.query.filter_by(
                cod_produto=codigo
            ).first()
            if produto:
                return produto.nome_produto or ''
        except Exception as e:
            logger.warning(f"[AI_RESOLVER] Erro ao buscar nome do produto {codigo}: {e}")

        return ''

    # =========================================================================
    # EXTRACAO DE OBSERVACOES
    # =========================================================================

    def extrair_observacao(self, texto: str) -> ResultadoExtracaoObservacao:
        """
        Extrai NFs de venda e motivo das observacoes.

        IMPORTANTE: Uma NFD pode referenciar MULTIPLAS NFs de venda!

        Args:
            texto: Texto das observacoes da NFD

        Returns:
            ResultadoExtracaoObservacao com dados extraidos (incluindo lista de NFs)
        """
        try:
            if not texto or len(texto.strip()) < 3:
                return ResultadoExtracaoObservacao(
                    numero_nf_venda=None,
                    numeros_nf_venda=[],
                    motivo_sugerido=None,
                    descricao_motivo=None,
                    confianca=0.0,
                    texto_original=texto or ''
                )

            prompt = PROMPT_EXTRAIR_OBSERVACAO.format(
                texto_observacao=texto
            )

            client = self._get_client()

            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=500,  # Aumentado para comportar observacoes longas
                temperature=0,  # Respostas deterministicas
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()

            # Parsear JSON
            dados = self._extrair_json(result_text)

            # Extrair lista de NFs (novo formato)
            numeros_nf_venda = dados.get('numeros_nf_venda', [])
            if not isinstance(numeros_nf_venda, list):
                numeros_nf_venda = [numeros_nf_venda] if numeros_nf_venda else []

            # Manter compatibilidade com campo antigo
            numero_nf_venda = numeros_nf_venda[0] if numeros_nf_venda else dados.get('numero_nf_venda')

            resultado = ResultadoExtracaoObservacao(
                numero_nf_venda=numero_nf_venda,
                numeros_nf_venda=numeros_nf_venda,
                motivo_sugerido=dados.get('motivo_sugerido'),
                descricao_motivo=dados.get('descricao_motivo'),
                confianca=float(dados.get('confianca', 0)),
                texto_original=texto
            )

            logger.info(
                f"[AI_RESOLVER] Observacao extraida: NFs={resultado.numeros_nf_venda}, "
                f"Motivo={resultado.motivo_sugerido} (confianca: {resultado.confianca:.0%})"
            )

            return resultado

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao extrair observacao: {e}")
            return ResultadoExtracaoObservacao(
                numero_nf_venda=None,
                numeros_nf_venda=[],
                motivo_sugerido=None,
                descricao_motivo=None,
                confianca=0.0,
                texto_original=texto
            )

    # =========================================================================
    # NORMALIZACAO DE UNIDADE
    # =========================================================================

    def normalizar_unidade(self, unidade: str) -> ResultadoNormalizacaoUnidade:
        """
        Normaliza unidade de medida do cliente.

        Args:
            unidade: Unidade original (ex: CXA1, UNI9, KG)

        Returns:
            ResultadoNormalizacaoUnidade com tipo e fator
        """
        try:
            if not unidade:
                return ResultadoNormalizacaoUnidade(
                    unidade_original='',
                    tipo='OUTRO',
                    fator_conversao=None,
                    confianca=0.0
                )

            prompt = PROMPT_NORMALIZAR_UNIDADE.format(
                unidade_cliente=unidade
            )

            client = self._get_client()

            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=300,  # Aumentado para margem de seguranca
                temperature=0,  # Respostas deterministicas
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()

            # Parsear JSON
            dados = self._extrair_json(result_text)

            resultado = ResultadoNormalizacaoUnidade(
                unidade_original=unidade,
                tipo=dados.get('tipo', 'OUTRO'),
                fator_conversao=dados.get('fator_conversao'),
                confianca=float(dados.get('confianca', 0))
            )

            logger.info(
                f"[AI_RESOLVER] Unidade normalizada: {unidade} -> "
                f"{resultado.tipo} (fator: {resultado.fator_conversao})"
            )

            return resultado

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao normalizar unidade: {e}")
            return ResultadoNormalizacaoUnidade(
                unidade_original=unidade,
                tipo='OUTRO',
                fator_conversao=None,
                confianca=0.0
            )

    # =========================================================================
    # RESOLUCAO EM LOTE
    # =========================================================================

    def resolver_linhas_nfd(
        self,
        nfd_id: int,
        auto_gravar_depara: bool = False
    ) -> Dict[str, Any]:
        """
        Resolve todas as linhas pendentes de uma NFD.

        OTIMIZADO: Usa busca em lote para De-Para e processamento paralelo para Haiku.

        Args:
            nfd_id: ID da NFDevolucao
            auto_gravar_depara: Se True, grava De-Para para confianca > 90%

        Returns:
            Dict com estatisticas e resultados
        """
        import time
        from app.devolucao.models import NFDevolucao

        try:
            tempo_inicio = time.time()
            nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None
            if not nfd:
                return {'sucesso': False, 'erro': 'NFD nao encontrada'}

            prefixo_cnpj = nfd.prefixo_cnpj_emitente or ''

            # Buscar linhas pendentes (ORDER BY garante consistencia entre execucoes)
            linhas = NFDevolucaoLinha.query.filter_by(
                nf_devolucao_id=nfd_id,
                produto_resolvido=False
            ).order_by(NFDevolucaoLinha.id).all()

            if not linhas:
                return {
                    'sucesso': True,
                    'nfd_id': nfd_id,
                    'total_linhas': 0,
                    'resolvidas_auto': 0,
                    'requerem_confirmacao': 0,
                    'nao_identificadas': 0,
                    'linhas': [],
                    'tempo_processamento': 0
                }

            resultados = {
                'sucesso': True,
                'nfd_id': nfd_id,
                'total_linhas': len(linhas),
                'resolvidas_auto': 0,
                'requerem_confirmacao': 0,
                'nao_identificadas': 0,
                'linhas': []
            }

            # ===================================================================
            # FASE 1: Busca De-Para em LOTE (1 query para N produtos)
            # ===================================================================
            logger.info(f"[AI_RESOLVER] FASE 1: Buscando De-Para em lote para {len(linhas)} linhas...")
            tempo_fase1 = time.time()

            # Coletar codigos das linhas para busca em lote
            codigos_clientes = [linha.codigo_produto_cliente or '' for linha in linhas]

            # Busca em lote nas tabelas De-Para (retorna dict codigo -> resultado)
            depara_resultados = self._buscar_depara_lote(codigos_clientes, prefixo_cnpj)

            logger.info(f"[AI_RESOLVER] FASE 1 concluida em {time.time() - tempo_fase1:.2f}s - "
                       f"{len(depara_resultados)} encontrados via De-Para")

            # ===================================================================
            # FASE 2: Separar linhas (com De-Para vs precisa Haiku)
            # ===================================================================
            logger.info(f"[AI_RESOLVER] FASE 2: Separando linhas...")

            linhas_com_depara = []      # (linha, nosso_codigo, descricao_nosso, metodo)
            linhas_para_haiku = []      # linhas que precisam de Haiku

            for linha in linhas:
                codigo = linha.codigo_produto_cliente or ''
                depara = depara_resultados.get(codigo)

                if depara:
                    linhas_com_depara.append((
                        linha,
                        depara['nosso_codigo'],
                        depara['descricao_nosso'],
                        depara['metodo']
                    ))
                else:
                    linhas_para_haiku.append(linha)

            logger.info(f"[AI_RESOLVER] FASE 2: {len(linhas_com_depara)} via De-Para, "
                       f"{len(linhas_para_haiku)} precisam Haiku")

            # ===================================================================
            # FASE 3: Processar Haiku em PARALELO (se necessario)
            # ===================================================================
            haiku_resultados = {}
            if linhas_para_haiku:
                logger.info(f"[AI_RESOLVER] FASE 3: Processando {len(linhas_para_haiku)} linhas via Haiku paralelo...")
                tempo_fase3 = time.time()

                # Converter NFDevolucaoLinha para dicts (formato esperado por _resolver_produtos_paralelo)
                linhas_dicts = []
                for linha in linhas_para_haiku:
                    linhas_dicts.append({
                        'linha_id': linha.id,
                        'codigo': linha.codigo_produto_cliente or '',
                        'descricao': linha.descricao_produto_cliente or '',
                        'unidade': linha.unidade_medida,
                        'quantidade': float(linha.quantidade) if linha.quantidade else None
                    })

                # Chamar processamento paralelo
                haiku_resultados = self._resolver_produtos_paralelo(linhas_dicts, prefixo_cnpj)

                logger.info(f"[AI_RESOLVER] FASE 3 concluida em {time.time() - tempo_fase3:.2f}s")

            # ===================================================================
            # FASE 4: Processar resultados (De-Para + Haiku)
            # ===================================================================
            logger.info(f"[AI_RESOLVER] FASE 4: Processando resultados...")

            # 4.1 Processar linhas com De-Para (confianca 100%)
            for linha, nosso_codigo, descricao_nosso, metodo in linhas_com_depara:
                linha_info = self._processar_resultado_linha(
                    linha=linha,
                    codigo_interno=nosso_codigo,
                    nome_interno=descricao_nosso,
                    confianca=1.0,
                    metodo_resolucao=metodo,
                    justificativa=f"De-Para {metodo}",
                    outras_sugestoes=[],
                    auto_gravar_depara=False,  # Ja existe no De-Para
                    prefixo_cnpj=prefixo_cnpj
                )

                if linha_info['status'] == 'AUTO_RESOLVIDO':
                    resultados['resolvidas_auto'] += 1
                elif linha_info['status'] == 'REQUER_CONFIRMACAO':
                    resultados['requerem_confirmacao'] += 1
                else:
                    resultados['nao_identificadas'] += 1

                resultados['linhas'].append(linha_info)

            # 4.2 Processar linhas com Haiku
            for linha in linhas_para_haiku:
                resultado = haiku_resultados.get(linha.id)

                if resultado and resultado.sugestao_principal:
                    linha_info = self._processar_resultado_linha(
                        linha=linha,
                        codigo_interno=resultado.sugestao_principal.codigo_interno,
                        nome_interno=resultado.sugestao_principal.nome_interno,
                        confianca=resultado.confianca,
                        metodo_resolucao=resultado.metodo_resolucao,
                        justificativa=resultado.sugestao_principal.justificativa,
                        outras_sugestoes=resultado.outras_sugestoes,
                        auto_gravar_depara=auto_gravar_depara,
                        prefixo_cnpj=prefixo_cnpj
                    )
                else:
                    # Nao identificado
                    tipo_unidade = self._normalizar_unidade_deterministico(linha.unidade_medida)
                    linha_info = {
                        'linha_id': linha.id,
                        'codigo_cliente': linha.codigo_produto_cliente,
                        'descricao_cliente': linha.descricao_produto_cliente,
                        'unidade_cliente': linha.unidade_medida,
                        'quantidade': float(linha.quantidade) if linha.quantidade else None,
                        'confianca': 0.0,
                        'metodo_resolucao': 'NAO_ENCONTRADO',
                        'tipo_unidade': tipo_unidade,
                        'sugestao': None,
                        'outras_sugestoes': [],
                        'status': 'NAO_IDENTIFICADO'
                    }

                if linha_info['status'] == 'AUTO_RESOLVIDO':
                    resultados['resolvidas_auto'] += 1
                elif linha_info['status'] == 'REQUER_CONFIRMACAO':
                    resultados['requerem_confirmacao'] += 1
                else:
                    resultados['nao_identificadas'] += 1

                resultados['linhas'].append(linha_info)

            # Ordenar resultados pela ordem original das linhas
            resultados['linhas'].sort(key=lambda x: x['linha_id'])

            db.session.commit()

            tempo_total = time.time() - tempo_inicio
            resultados['tempo_processamento'] = round(tempo_total, 2)

            logger.info(
                f"[AI_RESOLVER] NFD {nfd_id} resolvida em {tempo_total:.2f}s: "
                f"{resultados['resolvidas_auto']} auto, "
                f"{resultados['requerem_confirmacao']} pendentes, "
                f"{resultados['nao_identificadas']} nao identificadas"
            )

            return resultados

        except Exception as e:
            db.session.rollback()
            logger.error(f"[AI_RESOLVER] Erro ao resolver linhas NFD: {e}")
            import traceback
            traceback.print_exc()
            return {'sucesso': False, 'erro': str(e)}

    def _processar_resultado_linha(
        self,
        linha: NFDevolucaoLinha,
        codigo_interno: str,
        nome_interno: str,
        confianca: float,
        metodo_resolucao: str,
        justificativa: str,
        outras_sugestoes: List,
        auto_gravar_depara: bool,
        prefixo_cnpj: str
    ) -> Dict[str, Any]:
        """
        Processa resultado de resolucao para uma linha (seja De-Para ou Haiku).

        Calcula conversao de unidade, peso, e monta estrutura de retorno.
        """
        from app.producao.models import CadastroPalletizacao

        # Normalizar unidade (funcao deterministica)
        tipo_unidade = self._normalizar_unidade_deterministico(linha.unidade_medida)

        linha_info = {
            'linha_id': linha.id,
            'codigo_cliente': linha.codigo_produto_cliente,
            'descricao_cliente': linha.descricao_produto_cliente,
            'unidade_cliente': linha.unidade_medida,
            'quantidade': float(linha.quantidade) if linha.quantidade else None,
            'confianca': confianca,
            'metodo_resolucao': metodo_resolucao,
            'tipo_unidade': tipo_unidade,
            'sugestao': None,
            'outras_sugestoes': [],
            'status': 'NAO_IDENTIFICADO'
        }

        if not codigo_interno:
            return linha_info

        # Buscar produto no CadastroPalletizacao
        produto = None
        try:
            produto = CadastroPalletizacao.query.filter_by(
                cod_produto=codigo_interno
            ).first()
        except Exception as e:
            logger.warning(f"[AI_RESOLVER] Erro ao buscar produto: {e}")

        # Extrair qtd por caixa do nome do produto
        nome_para_extracao = ''
        if produto and produto.nome_produto:
            nome_para_extracao = produto.nome_produto
        elif nome_interno:
            nome_para_extracao = nome_interno

        qtd_por_caixa = self._extrair_qtd_caixa(nome_para_extracao)

        # Calcular conversao se unidade for UNIDADE
        qtd_convertida_caixas = None
        valor_convertido = None
        if tipo_unidade == 'UNIDADE' and qtd_por_caixa and linha.quantidade:
            qtd_convertida_caixas = float(linha.quantidade) / qtd_por_caixa
            if linha.valor_unitario:
                valor_convertido = float(linha.valor_unitario) * qtd_por_caixa
            logger.info(f"[AI_RESOLVER] Conversao: {linha.quantidade} UN / {qtd_por_caixa} = {qtd_convertida_caixas:.2f} CX")
        else:
            # FALLBACK: Se quantidade >= qtd_por_caixa, provavelmente e unidade
            if qtd_por_caixa and linha.quantidade and float(linha.quantidade) >= qtd_por_caixa:
                qtd_convertida_caixas = float(linha.quantidade) / qtd_por_caixa
                if linha.valor_unitario:
                    valor_convertido = float(linha.valor_unitario) * qtd_por_caixa
                logger.info(f"[AI_RESOLVER] Conversao FALLBACK: {linha.quantidade} / {qtd_por_caixa} = {qtd_convertida_caixas:.2f} CX")

        # Calcular peso
        peso_calculado = None
        try:
            if produto and produto.peso_bruto:
                qtd_para_peso = qtd_convertida_caixas if qtd_convertida_caixas else float(linha.quantidade or 0)
                peso_calculado = round(qtd_para_peso * float(produto.peso_bruto), 2)
        except Exception as e:
            logger.warning(f"[AI_RESOLVER] Erro ao calcular peso: {e}")

        linha_info['sugestao'] = {
            'codigo': codigo_interno,
            'nome': nome_interno,
            'justificativa': justificativa,
            'qtd_por_caixa': qtd_por_caixa,
            'qtd_convertida_caixas': round(qtd_convertida_caixas, 3) if qtd_convertida_caixas else None,
            'valor_convertido_caixa': round(valor_convertido, 2) if valor_convertido else None,
            'peso_calculado': peso_calculado
        }

        if confianca >= 0.9:
            linha_info['status'] = 'AUTO_RESOLVIDO'

            # SOMENTE gravar automaticamente se auto_gravar_depara=True
            if auto_gravar_depara:
                linha.codigo_produto_interno = codigo_interno
                linha.descricao_produto_interno = nome_interno
                linha.produto_resolvido = True
                linha.metodo_resolucao = metodo_resolucao
                linha.confianca_resolucao = confianca

                if prefixo_cnpj:
                    self._gravar_depara(
                        prefixo_cnpj=prefixo_cnpj,
                        codigo_cliente=linha.codigo_produto_cliente,
                        descricao_cliente=linha.descricao_produto_cliente,
                        nosso_codigo=codigo_interno,
                        descricao_nosso=nome_interno
                    )
        else:
            linha_info['status'] = 'REQUER_CONFIRMACAO'

        # Outras sugestoes
        for outra in outras_sugestoes:
            qtd_caixa_outra = self._extrair_qtd_caixa(outra.nome_interno or '')
            qtd_conv_outra = None
            valor_conv_outra = None
            peso_outra = None

            if tipo_unidade == 'UNIDADE' and qtd_caixa_outra and linha.quantidade:
                qtd_conv_outra = round(float(linha.quantidade) / qtd_caixa_outra, 3)
                if linha.valor_unitario:
                    valor_conv_outra = round(float(linha.valor_unitario) * qtd_caixa_outra, 2)

            # Calcular peso para outras sugestoes
            try:
                prod_outra = CadastroPalletizacao.query.filter_by(
                    cod_produto=outra.codigo_interno
                ).first()
                if prod_outra and prod_outra.peso_bruto:
                    qtd_peso_outra = qtd_conv_outra if qtd_conv_outra else float(linha.quantidade or 0)
                    peso_outra = round(qtd_peso_outra * float(prod_outra.peso_bruto), 2)
            except Exception:
                pass

            linha_info['outras_sugestoes'].append({
                'codigo': outra.codigo_interno,
                'nome': outra.nome_interno,
                'confianca': outra.confianca,
                'qtd_por_caixa': qtd_caixa_outra,
                'qtd_convertida_caixas': qtd_conv_outra,
                'valor_convertido_caixa': valor_conv_outra,
                'peso_calculado': peso_outra
            })

        return linha_info

    def _gravar_depara(
        self,
        prefixo_cnpj: str,
        codigo_cliente: str,
        descricao_cliente: str,
        nosso_codigo: str,
        descricao_nosso: str
    ):
        """Grava De-Para no banco."""
        try:
            # Verificar se ja existe (inclui inativos para evitar violacao de constraint)
            existente = DeParaProdutoCliente.query.filter_by(
                prefixo_cnpj=prefixo_cnpj[:8],
                codigo_cliente=codigo_cliente
            ).first()

            if existente:
                if existente.ativo:
                    return  # Ja existe ativo, nao sobrescrever
                else:
                    # Registro inativo - reativar e atualizar
                    existente.nosso_codigo = nosso_codigo
                    existente.descricao_nosso = descricao_nosso
                    existente.descricao_cliente = descricao_cliente
                    existente.ativo = True
                    existente.atualizado_em = agora_utc_naive()
                    existente.atualizado_por = 'AIResolverService'
                    logger.info(f"[AI_RESOLVER] De-Para reativado: {codigo_cliente} -> {nosso_codigo}")
                    return

            depara = DeParaProdutoCliente(
                prefixo_cnpj=prefixo_cnpj[:8],
                codigo_cliente=codigo_cliente,
                descricao_cliente=descricao_cliente,
                nosso_codigo=nosso_codigo,
                descricao_nosso=descricao_nosso,
                ativo=True,
                criado_em=agora_utc_naive(),
                criado_por='AIResolverService',
            )

            db.session.add(depara)
            logger.info(f"[AI_RESOLVER] De-Para gravado: {codigo_cliente} -> {nosso_codigo}")

        except Exception as e:
            logger.error(f"[AI_RESOLVER] Erro ao gravar De-Para: {e}")

    # =========================================================================
    # UTILITARIOS
    # =========================================================================

    def _extrair_json(self, texto: str) -> Dict:
        """Extrai JSON de texto."""
        try:
            if '{' in texto:
                inicio = texto.find('{')
                fim = texto.rfind('}') + 1
                json_str = texto[inicio:fim]
                return json.loads(json_str)
            return {}
        except Exception:
            return {}


# =============================================================================
# FUNCOES HELPER
# =============================================================================

def get_ai_resolver() -> AIResolverService:
    """Retorna instancia do AIResolverService."""
    return AIResolverService()
