"""
ScannerMotoService — Leitura de etiquetas de moto via Claude Vision API
========================================================================

Recebe imagem base64 (JPEG) de uma etiqueta de moto e extrai:
- modelo: nome do modelo (ex: SCOOTER JET, GIGA, JETMAX)
- cor: cor em portugues (ex: AZUL, PRETO, BRANCO)
- chassi: numero do chassi/VIN
- numero_motor: numero de serie do motor (quando visivel)
- confianca: 0.0-1.0

Suporta 3 formatos de etiqueta:
1. Brasileiro (Manaus): SCOOTER JET, SCOOTER MA TRI
2. Chines (GIGA): etiqueta minimalista com caracteres chineses
3. JETMAX (importado): campos em ingles (MODEL, COLOR, VIN)

Custo: ~R$0,01 por leitura (Claude Haiku Vision)
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def _extrair_json(text: str) -> dict:
    """
    Extrai o primeiro objeto JSON valido de uma string.

    Haiku frequentemente retorna JSON seguido de texto explicativo:
        {"modelo": "SCOOTER JET", ...}
        Note: I detected the label format as Brazilian...

    json.loads() falha com "Extra data" nesses casos.
    Usa json.JSONDecoder().raw_decode() que para no fim do JSON valido.
    """
    text = text.strip()

    # Remover markdown fencing (```json ... ```)
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]).strip()

    # Tentar raw_decode (ignora texto apos o JSON)
    try:
        decoder = json.JSONDecoder()
        # Encontrar o inicio do JSON (primeiro { ou [)
        match = re.search(r'[{\[]', text)
        if match:
            result, _ = decoder.raw_decode(text, match.start())
            if isinstance(result, dict):
                return result
    except json.JSONDecodeError:
        pass

    # Fallback: tentar json.loads direto (caso nao tenha extra data)
    return json.loads(text)

# Prompt otimizado para extracao estruturada dos 3 formatos de etiqueta
SYSTEM_PROMPT = """You extract motorcycle label data from images of shipping box labels.

There are three label formats you must handle:

1. **Brazilian (Manaus production)**: Portuguese fields.
   - "Modelo:" or header text = model name (e.g. SCOOTER JET, SCOOTER MA TRI)
   - Color shown as text ("AZUL") and/or a colored circle
   - Chassis in barcode text and printed text (e.g. MCBRJET2509250027, SXKJ2250612O327)
   - "Numero de serie do motor:" = motor serial number

2. **Chinese (GIGA)**: Minimal label.
   - Model name printed prominently: "GIGA"
   - Color in Chinese character + sometimes English: 蓝=Azul, 黑=Preto, 白=Branco, 红=Vermelho, 绿=Verde, 灰=Cinza
   - Chassis encoded in barcode text (e.g. LA20255A1100068363)

3. **JETMAX (imported)**: English fields.
   - "MODEL:" = model name (JETMAX)
   - "COLOR:" = color in English (BLACK, WHITE, RED, BLUE)
   - "VIN:" = chassis/VIN number (e.g. LTDAE393G11204162, may have * delimiters)
   - "MOTOR NO:" = motor serial number

Return ONLY valid JSON with exactly these keys:
{"modelo": "...", "cor": "...", "chassi": "...", "numero_motor": "...", "confianca": 0.95}

Rules:
- modelo: the motorcycle model name, uppercase
- cor: ALWAYS in Portuguese (AZUL, PRETO, BRANCO, VERMELHO, VERDE, CINZA, AMARELO, LARANJA, ROSA)
- chassi: alphanumeric only (strip * delimiters), typically 10-30 chars
- numero_motor: motor serial number if visible, null otherwise
- confianca: your confidence in the overall extraction (0.0 to 1.0)
- If a field is not visible or unreadable, use null
- Do NOT guess or invent values — use null for anything uncertain"""

# Maximo de bytes da imagem base64 (500KB encoded ~= 375KB raw)
MAX_IMAGE_BASE64_BYTES = 500_000


class ScannerMotoService:
    """Servico de leitura de etiquetas de moto via Claude Vision API."""

    @staticmethod
    def ler_etiqueta(image_base64: str) -> dict:
        """
        Le uma etiqueta de moto a partir de imagem base64 JPEG.

        Args:
            image_base64: Imagem JPEG codificada em base64

        Returns:
            dict com {modelo, cor, chassi, numero_motor, confianca}

        Raises:
            ValueError: Imagem invalida ou muito grande
            RuntimeError: Erro na API de visao
        """
        # Validar tamanho
        if len(image_base64) > MAX_IMAGE_BASE64_BYTES:
            raise ValueError(
                f"Imagem muito grande ({len(image_base64)} bytes). "
                f"Maximo: {MAX_IMAGE_BASE64_BYTES} bytes."
            )

        # Validar formato JPEG (base64 de JPEG comeca com /9j/)
        if not image_base64.startswith('/9j/'):
            raise ValueError("Formato de imagem invalido. Apenas JPEG e aceito.")

        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "Pacote 'anthropic' nao instalado. "
                "Execute: pip install anthropic"
            )

        import os
        if not os.environ.get('ANTHROPIC_API_KEY'):
            raise RuntimeError(
                "ANTHROPIC_API_KEY nao configurada. "
                "Configure a variavel de ambiente."
            )

        try:
            client = anthropic.Anthropic()  # Usa ANTHROPIC_API_KEY do env

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": "Read this motorcycle shipping label and extract the data as JSON."
                        }
                    ]
                }]
            )

            # Validar resposta nao vazia
            if not response.content:
                raise RuntimeError(
                    "API retornou resposta vazia. "
                    "Tente com outra imagem."
                )

            # Extrair texto da resposta
            response_text = response.content[0].text.strip()

            # Extrair JSON da resposta (Haiku pode adicionar texto apos o JSON)
            result = _extrair_json(response_text)

            # Garantir campos esperados
            campos = ['modelo', 'cor', 'chassi', 'numero_motor', 'confianca']
            for campo in campos:
                if campo not in result:
                    result[campo] = None

            # Normalizar confianca
            if result.get('confianca') is not None:
                result['confianca'] = max(0.0, min(1.0, float(result['confianca'])))
            else:
                result['confianca'] = 0.0

            # Limpar chassi (remover * e espacos)
            if result.get('chassi'):
                result['chassi'] = result['chassi'].replace('*', '').replace(' ', '').strip()

            logger.info(
                "Etiqueta lida: modelo=%s, cor=%s, chassi=%s, confianca=%.2f",
                result.get('modelo'), result.get('cor'),
                result.get('chassi'), result.get('confianca', 0)
            )

            return result

        except json.JSONDecodeError as e:
            logger.error("Resposta da Vision API nao e JSON valido: %s", e)
            raise ValueError(f"Formato de resposta invalido da API de visao: {e}")

        except anthropic.APIError as e:
            logger.error("Erro na API Anthropic: %s", e)
            raise RuntimeError(f"Erro na API de visao: {e}")

        except Exception as e:
            logger.error("Erro inesperado ao ler etiqueta: %s", e)
            raise RuntimeError(f"Erro ao processar imagem: {e}")
