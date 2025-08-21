"""
Utilitário para identificar grupos empresariais baseado em CNPJ
Identifica automaticamente qual portal usar baseado no grupo empresarial
"""

import re
from typing import Optional, Dict, List

# Mapeamento de prefixos CNPJ para grupos empresariais
GRUPOS_EMPRESARIAIS = {
    'atacadao': {
        'nome': 'Rede Atacadão',
        'portal': 'atacadao',
        'prefixos': [
            '93209765',  # Atacadão S.A.
            '75315333',  # Atacadão Distribuição
            '00063960'   # Atacadão Comercial
        ]
    },
    'tenda': {
        'nome': 'Rede Tenda',
        'portal': 'tenda',
        'prefixos': [
            '01157555'   # Tenda Atacado
        ]
    },
    'assai': {
        'nome': 'Rede Assaí (Sendas)',
        'portal': 'sendas',
        'prefixos': [
            '06057223'   # Assaí/Sendas
        ]
    }
}

class GrupoEmpresarial:
    """Identifica e gerencia grupos empresariais"""
    
    @staticmethod
    def limpar_cnpj(cnpj: str) -> str:
        """
        Remove formatação do CNPJ
        
        Args:
            cnpj: CNPJ com ou sem formatação
            
        Returns:
            CNPJ apenas com números
        """
        if not cnpj:
            return ''
        return re.sub(r'\D', '', str(cnpj))
    
    @staticmethod
    def obter_raiz_cnpj(cnpj: str) -> str:
        """
        Obtém a raiz do CNPJ (primeiros 8 dígitos)
        
        Args:
            cnpj: CNPJ completo ou parcial
            
        Returns:
            Raiz do CNPJ (8 dígitos)
        """
        cnpj_limpo = GrupoEmpresarial.limpar_cnpj(cnpj)
        if len(cnpj_limpo) >= 8:
            return cnpj_limpo[:8]
        return cnpj_limpo
    
    @staticmethod
    def identificar_grupo(cnpj: str) -> Optional[str]:
        """
        Identifica o grupo empresarial pelo CNPJ
        
        Args:
            cnpj: CNPJ do cliente
            
        Returns:
            Código do grupo (atacadao, tenda, assai) ou None
        """
        raiz_cnpj = GrupoEmpresarial.obter_raiz_cnpj(cnpj)
        
        if not raiz_cnpj:
            return None
        
        # Verificar cada grupo
        for codigo_grupo, info_grupo in GRUPOS_EMPRESARIAIS.items():
            if raiz_cnpj in info_grupo['prefixos']:
                return codigo_grupo
        
        return None
    
    @staticmethod
    def identificar_portal(cnpj: str) -> Optional[str]:
        """
        Identifica qual portal usar baseado no CNPJ
        
        Args:
            cnpj: CNPJ do cliente
            
        Returns:
            Nome do portal (atacadao, sendas, tenda) ou None
        """
        grupo = GrupoEmpresarial.identificar_grupo(cnpj)
        
        if grupo and grupo in GRUPOS_EMPRESARIAIS:
            return GRUPOS_EMPRESARIAIS[grupo]['portal']
        
        return None
    
    @staticmethod
    def obter_info_grupo(cnpj: str) -> Optional[Dict]:
        """
        Obtém informações completas do grupo empresarial
        
        Args:
            cnpj: CNPJ do cliente
            
        Returns:
            Dict com informações do grupo ou None
        """
        grupo = GrupoEmpresarial.identificar_grupo(cnpj)
        
        if grupo and grupo in GRUPOS_EMPRESARIAIS:
            return {
                'codigo': grupo,
                'nome': GRUPOS_EMPRESARIAIS[grupo]['nome'],
                'portal': GRUPOS_EMPRESARIAIS[grupo]['portal'],
                'prefixos': GRUPOS_EMPRESARIAIS[grupo]['prefixos']
            }
        
        return None
    
    @staticmethod
    def eh_cliente_atacadao(cnpj: str) -> bool:
        """
        Verifica se o CNPJ é de um cliente Atacadão
        
        Args:
            cnpj: CNPJ do cliente
            
        Returns:
            True se for Atacadão
        """
        return GrupoEmpresarial.identificar_grupo(cnpj) == 'atacadao'
    
    @staticmethod
    def eh_cliente_tenda(cnpj: str) -> bool:
        """
        Verifica se o CNPJ é de um cliente Tenda
        
        Args:
            cnpj: CNPJ do cliente
            
        Returns:
            True se for Tenda
        """
        return GrupoEmpresarial.identificar_grupo(cnpj) == 'tenda'
    
    @staticmethod
    def eh_cliente_assai(cnpj: str) -> bool:
        """
        Verifica se o CNPJ é de um cliente Assaí/Sendas
        
        Args:
            cnpj: CNPJ do cliente
            
        Returns:
            True se for Assaí/Sendas
        """
        return GrupoEmpresarial.identificar_grupo(cnpj) == 'assai'
    
    @staticmethod
    def listar_cnpjs_grupo(grupo: str) -> List[str]:
        """
        Lista todos os prefixos CNPJ de um grupo
        
        Args:
            grupo: Código do grupo (atacadao, tenda, assai)
            
        Returns:
            Lista de prefixos CNPJ
        """
        if grupo in GRUPOS_EMPRESARIAIS:
            return GRUPOS_EMPRESARIAIS[grupo]['prefixos']
        return []
    
    @staticmethod
    def formatar_cnpj(cnpj: str) -> str:
        """
        Formata CNPJ para exibição
        
        Args:
            cnpj: CNPJ sem formatação
            
        Returns:
            CNPJ formatado (XX.XXX.XXX/XXXX-XX)
        """
        cnpj_limpo = GrupoEmpresarial.limpar_cnpj(cnpj)
        
        if len(cnpj_limpo) == 14:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
        elif len(cnpj_limpo) == 8:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}"
        
        return cnpj
    
    @staticmethod
    def adicionar_grupo(codigo: str, nome: str, portal: str, prefixos: List[str]):
        """
        Adiciona novo grupo empresarial (dinâmico)
        
        Args:
            codigo: Código único do grupo
            nome: Nome do grupo empresarial
            portal: Portal associado
            prefixos: Lista de prefixos CNPJ
        """
        GRUPOS_EMPRESARIAIS[codigo] = {
            'nome': nome,
            'portal': portal,
            'prefixos': [GrupoEmpresarial.limpar_cnpj(p)[:8] for p in prefixos]
        }
    
    @staticmethod
    def remover_grupo(codigo: str):
        """
        Remove grupo empresarial
        
        Args:
            codigo: Código do grupo a remover
        """
        if codigo in GRUPOS_EMPRESARIAIS:
            del GRUPOS_EMPRESARIAIS[codigo]
    
    @staticmethod
    def listar_grupos() -> Dict:
        """
        Lista todos os grupos empresariais cadastrados
        
        Returns:
            Dict com todos os grupos
        """
        return GRUPOS_EMPRESARIAIS.copy()


# Funções de conveniência para uso direto
def identificar_portal_por_cnpj(cnpj: str) -> Optional[str]:
    """
    Função de conveniência para identificar portal pelo CNPJ
    
    Args:
        cnpj: CNPJ do cliente
        
    Returns:
        Nome do portal ou None
    """
    return GrupoEmpresarial.identificar_portal(cnpj)


def eh_cliente_com_portal(cnpj: str) -> bool:
    """
    Verifica se o cliente tem portal de agendamento
    
    Args:
        cnpj: CNPJ do cliente
        
    Returns:
        True se tiver portal
    """
    return GrupoEmpresarial.identificar_portal(cnpj) is not None


# Exemplos de uso
if __name__ == '__main__':
    # Testar identificação
    testes = [
        '93.209.765/0001-00',  # Atacadão
        '75315333000130',      # Atacadão
        '00063960000134',      # Atacadão
        '01.157.555/0001-00',  # Tenda
        '06057223000171',      # Assaí
        '12345678000190'       # Desconhecido
    ]
    
    for cnpj in testes:
        info = GrupoEmpresarial.obter_info_grupo(cnpj)
        if info:
            print(f"CNPJ: {GrupoEmpresarial.formatar_cnpj(cnpj)}")
            print(f"  Grupo: {info['nome']}")
            print(f"  Portal: {info['portal']}")
            print()
        else:
            print(f"CNPJ: {cnpj} - Grupo não identificado")
            print()