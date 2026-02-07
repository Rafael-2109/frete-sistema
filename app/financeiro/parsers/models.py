# -*- coding: utf-8 -*-
"""
Dataclass normalizada para comprovantes PIX (banco-agnóstica).

Todos os parsers (Sicoob, Grafeno, etc.) devem retornar instâncias
de ComprovantePix com campos normalizados.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ComprovantePix:
    """Comprovante de pagamento PIX — saída normalizada de qualquer parser."""

    # Cabeçalho
    data_comprovante: Optional[str] = None      # "29/12/2025"
    hora_comprovante: Optional[str] = None      # "13:48:16"
    tipo_pagamento: Optional[str] = None        # "Pix via chave" / "Pix via manual"
    banco_origem: Optional[str] = None          # "sicoob" / "grafeno" / etc

    # Pagador (quem efetuou o pagamento)
    pagador_instituicao: Optional[str] = None
    pagador_nome: Optional[str] = None
    pagador_cnpj_cpf: Optional[str] = None

    # Destinatário (quem recebe o pagamento)
    destinatario_nome: Optional[str] = None
    destinatario_cnpj_cpf: Optional[str] = None
    destinatario_instituicao: Optional[str] = None

    # Pagamento
    data_pagamento: Optional[str] = None        # "29/12/2025 11:31:03"
    valor: Optional[str] = None                 # "200,41"
    id_transacao: Optional[str] = None          # EndToEndId (CHAVE ÚNICA GLOBAL)
    situacao: Optional[str] = None              # "Finalizado com sucesso"

    # Metadados
    pagina: int = 0
