"""Parser para extrato Bradesco Conta Corrente (CSV separado por ;, encoding latin-1)."""
from datetime import date
from decimal import Decimal
from typing import Optional
import re

from unidecode import unidecode

from app.pessoal.services.parsers.base_parser import (
    TransacaoRaw, parse_valor_brasileiro, parse_data_brasileira,
    normalizar_historico, limpar_prefixo_descricao, remover_data_transacao,
    remover_todas_datas, _eh_pix,
)


class BradescoExtratoCC:
    """Parser de extrato de conta corrente Bradesco.

    Formato CSV (;):
    - Header com info da conta (agencia, conta, periodo)
    - Linhas de colunas: Data;Historico;Docto.;Credito;Debito;Saldo
    - Data preenchida = nova transacao
    - Data vazia = descricao da transacao anterior (Des:, Rem:, etc.)
    - Parar em "Os dados acima" ou "Ultimos Lancamentos"
    - Secao "Ultimos Lancamentos": marcar como provisorias
    """

    def __init__(self):
        self.agencia: Optional[str] = None
        self.conta: Optional[str] = None
        self.periodo_inicio: Optional[date] = None
        self.periodo_fim: Optional[date] = None

    def parsear(self, conteudo: str, ano_referencia: int = None) -> list[TransacaoRaw]:
        """Parseia conteudo do CSV (ja decodificado). Retorna lista de TransacaoRaw.

        Args:
            ano_referencia: ano a usar quando datas no CSV sao DD/MM (sem ano).
                Se None e o header nao tiver periodo, fallback = ano corrente.
        """
        linhas = conteudo.splitlines()
        transacoes = []

        # Estado
        em_dados = False
        em_ultimos = False
        transacao_atual: Optional[TransacaoRaw] = None
        ano_ref = ano_referencia  # Fallback do usuario; header pode sobrescrever

        for linha_raw in linhas:
            linha = linha_raw.strip()
            if not linha:
                continue

            campos = [c.strip().strip('"') for c in linha.split(';')]

            # Detectar header de periodo
            if not em_dados:
                self._extrair_header(campos, linha)
                if self.periodo_inicio:
                    ano_ref = self.periodo_inicio.year

            # Detectar inicio dos dados
            if any('Hist' in c for c in campos[:3]) and any('Docto' in c or 'Doc' in c for c in campos[:5]):
                em_dados = True
                continue

            # Detectar marcadores de secao (unidecode para acentos: Últimos→ULTIMOS)
            texto_linha = unidecode(linha.upper())

            if em_dados and 'OS DADOS ACIMA' in texto_linha:
                if transacao_atual:
                    transacoes.append(transacao_atual)
                    transacao_atual = None
                em_dados = False
                continue

            # "Ultimos Lancamentos" pode vir APOS "Os dados acima" (em_dados=False)
            if 'ULTIMOS LANCAMENTOS' in texto_linha or 'LANCAMENTOS FUTUROS' in texto_linha:
                if transacao_atual:
                    transacoes.append(transacao_atual)
                    transacao_atual = None
                em_ultimos = True
                continue

            if not em_dados and not em_ultimos:
                continue

            # Parsear linha de dados
            if len(campos) < 4:
                continue

            data_str = campos[0].strip()

            if data_str and re.match(r'\d{1,2}/\d{1,2}', data_str):
                # Nova transacao
                if transacao_atual:
                    transacoes.append(transacao_atual)

                dt = parse_data_brasileira(data_str, ano_ref)
                if not dt:
                    continue

                historico = campos[1].strip() if len(campos) > 1 else ''
                documento = campos[2].strip() if len(campos) > 2 else ''

                # Credito e Debito podem estar em colunas diferentes
                credito_str = campos[3].strip() if len(campos) > 3 else ''
                debito_str = campos[4].strip() if len(campos) > 4 else ''
                saldo_str = campos[5].strip() if len(campos) > 5 else ''

                if credito_str and credito_str != '0' and credito_str != '0,00':
                    valor = parse_valor_brasileiro(credito_str)
                    tipo = 'credito'
                elif debito_str and debito_str != '0' and debito_str != '0,00':
                    valor = parse_valor_brasileiro(debito_str)
                    tipo = 'debito'
                else:
                    transacao_atual = None  # Zerar para nao re-appendar
                    continue  # Sem valor

                saldo = parse_valor_brasileiro(saldo_str) if saldo_str else None
                # Saldo pode ser negativo no original
                if saldo is not None and saldo_str and '-' in saldo_str:
                    saldo = -saldo

                transacao_atual = TransacaoRaw(
                    data=dt,
                    historico=historico,
                    documento=documento,
                    valor=valor,
                    tipo=tipo,
                    saldo=saldo,
                    eh_provisoria=em_ultimos,
                )
            elif transacao_atual and not data_str:
                # Linha de descricao (continuacao da transacao anterior)
                desc_raw = campos[1].strip() if len(campos) > 1 else ''
                if desc_raw:
                    desc_limpa = limpar_prefixo_descricao(desc_raw)
                    if transacao_atual.descricao:
                        transacao_atual.descricao += ' | ' + desc_limpa
                    else:
                        transacao_atual.descricao = desc_limpa

        # Ultima transacao
        if transacao_atual:
            transacoes.append(transacao_atual)

        # Limpar datas redundantes de historico/descricao
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

        # Montar historico_completo para cada transacao
        for t in transacoes:
            partes = [normalizar_historico(t.historico)]
            if t.descricao:
                partes.append(normalizar_historico(t.descricao))
            t.historico_completo = ' | '.join(partes)

        return transacoes

    def _extrair_header(self, campos: list[str], linha: str):
        """Extrai info do header (agencia, conta, periodo)."""
        texto = linha.upper()

        # Agencia
        if 'AGENCIA' in texto or 'AG' in texto:
            match = re.search(r'AG(?:ENCIA)?[\s:]*(\d+)', texto)
            if match:
                self.agencia = match.group(1)

        # Conta
        if 'CONTA' in texto or 'C/C' in texto:
            match = re.search(r'(?:CONTA|C/C)[\s:]*(\d[\d.-]+)', texto)
            if match:
                self.conta = match.group(1)

        # Periodo
        for campo in campos:
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})\s*[aAeE]\s*(\d{1,2}/\d{1,2}/\d{2,4})', campo)
            if match:
                self.periodo_inicio = parse_data_brasileira(match.group(1))
                self.periodo_fim = parse_data_brasileira(match.group(2))
