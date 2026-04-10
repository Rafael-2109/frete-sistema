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
# Inclui regras de desambiguacao O/0, S/5, I/1 baseadas em padroes reais
SYSTEM_PROMPT = """You extract motorcycle label data from images of shipping box labels.
Return ONLY a JSON object — no extra text, no explanation.

## THREE LABEL FORMATS

### Format 1: Brazilian (Manaus)
Models: SCOOTER JET, SCOOTER MA TRI
Layout:
- Header row: model name (left) + color text + colored circle (right)
- Large text with barcode below = CHASSIS number
- "Modelo:" field, "Codigo:" field, "Quantidade:", "Numero de serie do motor:"
- Footer: "PRODUZIDO NO POLO INDUSTRIAL DE MANAUS"

CHASSIS PATTERN: alpha prefix (4-7 letters) + ONLY DIGITS after that.
Examples: MCBRJET2509250027 (prefix MCBRJET + 11 digits), SXKJ22506120327 (prefix SXKJ + 13 digits)
RULE: After the initial letter prefix, every character MUST be a digit 0-9. If you see "O" after the prefix, it is "0". If you see "I", it is "1". If you see "S", it is "5".

### Format 2: GIGA
Model: GIGA (always)
Layout: minimal label with "GIGA" in large text, Chinese color character + English, barcode with chassis.
Colors: 蓝/Blue=AZUL, 黑/Black=PRETO, 白/White=BRANCO, 红/Red=VERMELHO, 绿/Green=VERDE, 灰/Grey=CINZA

CHASSIS PATTERN: LA + 4-digit year + 5A + 11 + 8 digits
Example: LA20255A1100068363
RULE: Position 7 is digit "5" NOT letter "S". The only letter after "LA" is a single "A" at position 8. Everything else is digits.

### Format 3: JETMAX
Model: JETMAX (always)
Layout: English fields — MODEL, COLOR, VIN, MOTOR NO., ORDER NO., CTN NO., MADE IN CHINA
VIN and MOTOR NO. are delimited by asterisks (*).

VIN (chassis) PATTERN: LTDAE393 + 1 letter + 8 alphanumeric chars = 17 chars total (ISO 3779)
Example: LTDAE393G11204162
RULE: VINs NEVER contain letters I, O, or Q (ISO standard). Strip * delimiters.

MOTOR NO. PATTERN: JYX1000W + 10 digits
Example: JYX1000W2601826162
RULE: After "W", everything is digits. Strip * delimiters.

COLOR translation: BLACK=PRETO, WHITE=BRANCO, RED=VERMELHO, BLUE=AZUL, GREEN=VERDE

## CRITICAL DISAMBIGUATION RULES (apply to ALL formats)
When a character is ambiguous between letter and digit:
- O → 0 (zero) in chassis/VIN serial portions
- I → 1 (one) in chassis/VIN serial portions
- S → 5 in digit-only portions
- Z → 2 in digit-only portions
- B → 8 in digit-only portions
These substitutions apply ONLY in positions where digits are expected per the patterns above.

## OUTPUT FORMAT
{"modelo": "...", "cor": "...", "chassi": "...", "numero_motor": "...", "confianca": 0.95}

- modelo: model name UPPERCASE (SCOOTER JET, SCOOTER MA TRI, GIGA, JETMAX)
- cor: ALWAYS Portuguese (AZUL, PRETO, BRANCO, VERMELHO, VERDE, CINZA)
- chassi: cleaned alphanumeric (no * delimiters, no spaces), with disambiguation rules applied
- numero_motor: motor serial if visible, null otherwise
- confianca: 0.0-1.0
- Use null for unreadable fields. Do NOT guess."""

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
