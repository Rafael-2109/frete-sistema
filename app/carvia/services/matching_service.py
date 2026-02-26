"""
Matching Service — NF <-> CTe
==============================

Algoritmo:
1. Para cada CTe XML parseado, extrair NFs referenciadas (chave ou nDoc+CNPJ)
2. Match exato por chave_acesso_nf (44 digitos) -> confianca CHAVE
3. Fallback: match por (cnpj_emitente + numero_nf) -> confianca CNPJ_NUMERO
4. CTe referenciando NF nao importada -> flag "NF nao encontrada"
5. Retorno: lista de matches com nivel de confianca
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class MatchResult:
    """Resultado de um match NF <-> CTe"""

    CONFIANCA_CHAVE = 'CHAVE'           # Match por chave de acesso 44 digitos
    CONFIANCA_CNPJ_NUMERO = 'CNPJ_NUMERO'  # Match por CNPJ + numero NF
    CONFIANCA_NAO_ENCONTRADA = 'NAO_ENCONTRADA'  # NF referenciada nao encontrada

    def __init__(self, nf_ref: Dict, nf_importada: Dict = None,
                 confianca: str = 'NAO_ENCONTRADA'):
        self.nf_ref = nf_ref          # Dados da NF conforme CTe
        self.nf_importada = nf_importada  # Dados da NF importada (ou None)
        self.confianca = confianca

    def to_dict(self):
        return {
            'nf_ref': self.nf_ref,
            'nf_importada': self.nf_importada,
            'confianca': self.confianca,
            'encontrada': self.confianca != self.CONFIANCA_NAO_ENCONTRADA,
        }


class MatchingService:
    """Servico de matching NF <-> CTe"""

    def match_cte_com_nfs(self, cte_data: Dict, nfs_importadas: List[Dict]) -> List[MatchResult]:
        """
        Para 1 CTe, encontra as NFs correspondentes.

        Args:
            cte_data: Dict retornado por CTeXMLParserCarvia.get_todas_informacoes_carvia()
                      Deve ter 'nfs_referenciadas' (lista de dicts com chave, numero_nf, cnpj_emitente)
            nfs_importadas: Lista de dicts com dados das NFs importadas
                           (chave_acesso_nf, numero_nf, cnpj_emitente, etc.)

        Returns:
            Lista de MatchResult
        """
        nfs_ref = cte_data.get('nfs_referenciadas', [])
        if not nfs_ref:
            logger.info("CTe sem NFs referenciadas")
            return []

        # Indexar NFs importadas por chave e por (cnpj, numero)
        idx_chave = {}
        idx_cnpj_numero = {}
        for nf in nfs_importadas:
            chave = nf.get('chave_acesso_nf')
            if chave:
                idx_chave[chave] = nf

            cnpj = (nf.get('cnpj_emitente') or '').strip()
            numero = (nf.get('numero_nf') or '').strip()
            if cnpj and numero:
                idx_cnpj_numero[(cnpj, numero)] = nf

        results = []
        for nf_ref in nfs_ref:
            match = self._tentar_match(nf_ref, idx_chave, idx_cnpj_numero)
            results.append(match)

        encontradas = sum(1 for r in results if r.confianca != MatchResult.CONFIANCA_NAO_ENCONTRADA)
        logger.info(
            f"Matching: {encontradas}/{len(results)} NFs encontradas "
            f"(CTe {cte_data.get('cte_numero', '?')})"
        )

        return results

    def _tentar_match(self, nf_ref: Dict, idx_chave: Dict,
                      idx_cnpj_numero: Dict) -> MatchResult:
        """Tenta match por chave, depois por CNPJ+numero"""
        chave = nf_ref.get('chave')

        # 1. Match exato por chave de acesso
        if chave and chave in idx_chave:
            return MatchResult(
                nf_ref=nf_ref,
                nf_importada=idx_chave[chave],
                confianca=MatchResult.CONFIANCA_CHAVE,
            )

        # 2. Fallback: match por CNPJ + numero
        cnpj = (nf_ref.get('cnpj_emitente') or '').strip()
        numero = (nf_ref.get('numero_nf') or '').strip()
        if cnpj and numero and (cnpj, numero) in idx_cnpj_numero:
            return MatchResult(
                nf_ref=nf_ref,
                nf_importada=idx_cnpj_numero[(cnpj, numero)],
                confianca=MatchResult.CONFIANCA_CNPJ_NUMERO,
            )

        # 3. Nao encontrada
        return MatchResult(
            nf_ref=nf_ref,
            confianca=MatchResult.CONFIANCA_NAO_ENCONTRADA,
        )

    def match_multiplos_ctes(self, ctes_data: List[Dict],
                             nfs_importadas: List[Dict]) -> Dict[str, List[MatchResult]]:
        """
        Match de multiplos CTes contra NFs.

        Returns:
            Dict com chave = indice do CTe -> lista de MatchResult
        """
        resultado = {}
        for i, cte in enumerate(ctes_data):
            key = cte.get('cte_numero') or str(i)
            resultado[key] = self.match_cte_com_nfs(cte, nfs_importadas)
        return resultado
