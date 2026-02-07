# -*- coding: utf-8 -*-
"""
Parsers de Comprovantes de Pagamento
=====================================

Arquitetura multi-banco extensível para parsing de comprovantes PIX e boleto.

Módulos:
- models.py:       Dataclass ComprovantePix (saída normalizada)
- dispatcher.py:   Detector de tipo (boleto/pix) e banco de origem
- pix_sicoob.py:   Parser PIX Sicoob (pypdf text-native)
"""
