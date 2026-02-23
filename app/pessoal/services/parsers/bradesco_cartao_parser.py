"""Parser para fatura Bradesco Cartao de Credito (CSV separado por ;, encoding latin-1)."""
from datetime import date
from decimal import Decimal
from typing import Optional
import re

from app.pessoal.services.parsers.base_parser import (
    TransacaoRaw, parse_valor_brasileiro, parse_data_brasileira,
    normalizar_historico, extrair_parcela, gerar_identificador_parcela,
    remover_data_transacao, remover_todas_datas, _eh_pix,
)


class BradescoFaturaCartao:
    """Parser de fatura de cartao de credito Bradesco.

    Formato CSV (;):
    - Header com data fatura e situacao (PAGO/ABERTA)
    - Secoes de titular: "NOME TITULAR  ;  ;  ;DDDD" (DDDD = ultimos digitos)
    - Transacoes: Data;Historico;Valor(US$);Valor(R$)
    - Valor negativo = credito/estorno
    - "Total da fatura" encerra
    - Ignorar: Resumo, Taxas, Cotacao, Encargos
    """

    def __init__(self):
        self.data_fatura: Optional[date] = None
        self.situacao: Optional[str] = None  # PAGO | ABERTA

    def parsear(self, conteudo: str, ano_referencia: int = None) -> list[TransacaoRaw]:
        """Parseia conteudo do CSV (ja decodificado). Retorna lista de TransacaoRaw.

        Args:
            ano_referencia: ano a usar quando datas no CSV sao DD/MM (sem ano).
                Se None e o header nao tiver data de fatura, fallback = ano corrente.
        """
        linhas = conteudo.splitlines()
        transacoes = []

        titular_atual: Optional[str] = None
        digitos_atual: Optional[str] = None
        em_transacoes = False
        secoes_ignorar = {'RESUMO', 'TAXAS', 'COTACAO', 'ENCARGOS', 'INFORMACOES'}
        ano_ref = ano_referencia  # Fallback do usuario; header pode sobrescrever

        for linha_raw in linhas:
            linha = linha_raw.strip()
            if not linha:
                continue

            campos = [c.strip().strip('"') for c in linha.split(';')]
            texto_upper = linha.upper()

            # Extrair situacao (somente no header, antes de entrar em transacoes)
            if not self.situacao and not em_transacoes:
                if 'PAGO' in texto_upper:
                    self.situacao = 'PAGO'
                elif 'ABERTA' in texto_upper:
                    self.situacao = 'ABERTA'

            # Extrair header
            if not self.data_fatura:
                self._extrair_header(campos)
                if self.data_fatura:
                    ano_ref = self.data_fatura.year
                continue

            # Detectar fim
            if 'TOTAL DA FATURA' in texto_upper or 'TOTAL GERAL' in texto_upper:
                em_transacoes = False
                continue

            # Detectar secoes a ignorar (mas so se a linha NAO comeca com data)
            tem_data = campos[0].strip() and re.match(r'\d{1,2}/\d{1,2}', campos[0].strip())
            if not tem_data:
                ignorar = False
                for secao in secoes_ignorar:
                    if secao in texto_upper and len(texto_upper) < 50:
                        em_transacoes = False
                        ignorar = True
                        break
                if ignorar:
                    continue

            # Detectar titular: "NOME  ;  ;  ;DIGITOS"
            titular_match = self._detectar_titular(campos)
            if titular_match:
                titular_atual, digitos_atual = titular_match
                em_transacoes = True
                continue

            # Detectar cabecalho de colunas (pular)
            if any('DATA' in c.upper() for c in campos[:2]) and any('VALOR' in c.upper() for c in campos):
                continue

            if not em_transacoes or not titular_atual:
                continue

            # Parsear transacao
            transacao = self._parsear_transacao(campos, titular_atual, digitos_atual, ano_ref)
            if transacao:
                transacoes.append(transacao)

        # Limpar datas redundantes de historico
        for t in transacoes:
            if _eh_pix(t.historico):
                # PIX nunca e parcelado — qualquer DD/MM e data, remover todas
                t.historico = remover_todas_datas(t.historico)
                if t.descricao:
                    t.descricao = remover_todas_datas(t.descricao)
            else:
                # Nao-PIX: remover apenas quando DD/MM == data da transacao
                t.historico = remover_data_transacao(t.historico, t.data)
                if t.descricao:
                    t.descricao = remover_data_transacao(t.descricao, t.data)

        # Montar historico_completo
        for t in transacoes:
            partes = [normalizar_historico(t.historico)]
            if t.descricao:
                partes.append(normalizar_historico(t.descricao))
            t.historico_completo = ' | '.join(partes)

        return transacoes

    def _extrair_header(self, campos: list[str]):
        """Extrai data fatura do header."""
        # Data fatura
        for campo in campos:
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', campo)
            if match:
                dt = parse_data_brasileira(match.group(1))
                if dt:
                    self.data_fatura = dt
                    return

    def _detectar_titular(self, campos: list[str]) -> Optional[tuple[str, str]]:
        """Detecta linha de titular: 'NOME TITULAR;  ;  ;DDDD'."""
        if len(campos) < 2:
            return None

        primeiro = campos[0].strip()
        if not primeiro:
            return None

        # Titular: nome em maiusculas + digitos no final
        # Formato: "NOME COMPLETO  ;  ;  ;DDDD" ou "NOME COMPLETO;;;;;DDDD"
        ultimo_campo = None
        for c in reversed(campos):
            c = c.strip()
            if c:
                ultimo_campo = c
                break

        if not ultimo_campo:
            return None

        # Digitos do cartao (4 ou 5 digitos)
        if re.match(r'^\d{4,5}$', ultimo_campo):
            # Verificar se o primeiro campo parece um nome (maiusculas, sem numeros no inicio)
            if re.match(r'^[A-Z\s]+$', primeiro) and len(primeiro) > 3:
                return (primeiro.strip(), ultimo_campo)

        return None

    def _parsear_transacao(self, campos: list[str], titular: str, digitos: str, ano_ref: int) -> Optional[TransacaoRaw]:
        """Parseia uma linha de transacao de cartao."""
        if len(campos) < 4:
            return None

        data_str = campos[0].strip()
        if not data_str or not re.match(r'\d{1,2}/\d{1,2}', data_str):
            return None

        dt = parse_data_brasileira(data_str, ano_ref)
        if not dt:
            return None

        historico = campos[1].strip()
        if not historico:
            return None

        # Valor em R$
        valor_brl_str = campos[3].strip() if len(campos) > 3 else ''
        if not valor_brl_str:
            return None

        # Detectar credito (valor negativo = estorno)
        eh_negativo = '-' in valor_brl_str
        valor = parse_valor_brasileiro(valor_brl_str)
        if valor == Decimal('0'):
            return None

        tipo = 'credito' if eh_negativo else 'debito'

        # Valor em dolar (se presente)
        valor_dolar = None
        if len(campos) > 2:
            dolar_str = campos[2].strip()
            if dolar_str and re.search(r'\d', dolar_str):
                valor_dolar = parse_valor_brasileiro(dolar_str)
                if valor_dolar == Decimal('0'):
                    valor_dolar = None

        # Extrair parcela
        parcela_atual, parcela_total = extrair_parcela(historico)
        id_parcela = gerar_identificador_parcela(historico)

        return TransacaoRaw(
            data=dt,
            historico=historico,
            valor=valor,
            tipo=tipo,
            valor_dolar=valor_dolar,
            parcela_atual=parcela_atual,
            parcela_total=parcela_total,
            identificador_parcela=id_parcela,
            titular_cartao=titular,
            ultimos_digitos_cartao=digitos,
        )
