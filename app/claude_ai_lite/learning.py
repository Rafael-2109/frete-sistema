"""
Serviço de Aprendizado do Claude AI Lite.

Detecta e processa comandos de aprendizado:
- "Lembre que..." → Salvar conhecimento
- "Esqueça que..." → Remover conhecimento
- "O que você sabe?" → Listar conhecimentos

Limite: 250 linhas
"""

import re
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

# Padrões de comandos
PADROES_LEMBRAR = [
    r"^lembr[ea]r?\s+que\s+(.+)",
    r"^guard[ea]r?\s+que\s+(.+)",
    r"^salv[ea]r?\s+que\s+(.+)",
    r"^anot[ea]r?\s+que\s+(.+)",
    r"^memoriz[ea]r?\s+que\s+(.+)",
    r"^não\s+esquec[ea]r?\s+que\s+(.+)",
    r"^registr[ea]r?\s+que\s+(.+)",
]

PADROES_ESQUECER = [
    r"^esquec[ea]r?\s+que\s+(.+)",
    r"^esque[cç][ea]r?\s+que\s+(.+)",
    r"^remov[ea]r?\s+(?:o\s+)?conhecimento\s+(?:sobre\s+)?(.+)",
    r"^delet[ea]r?\s+(?:o\s+)?aprendizado\s+(?:sobre\s+)?(.+)",
    r"^apag[ea]r?\s+que\s+(.+)",
]

PADROES_LISTAR = [
    r"^o\s+que\s+voc[êe]\s+sabe",
    r"^quais?\s+(?:são\s+)?(?:os\s+)?(?:seus\s+)?conhecimentos",
    r"^list[ea]r?\s+(?:os\s+)?aprendizados",
    r"^mostr[ea]r?\s+(?:sua\s+)?mem[oó]ria",
    r"^o\s+que\s+voc[êe]\s+lembra",
    r"^o\s+que\s+voc[êe]\s+aprendeu",
]

# Categorias automáticas baseadas em palavras-chave
CATEGORIAS_AUTO = {
    'cliente': ['cliente', 'cnpj', 'empresa', 'razão social', 'comprador'],
    'produto': ['produto', 'item', 'mercadoria', 'sku', 'código'],
    'regra_negocio': ['sempre', 'nunca', 'regra', 'política', 'procedimento', 'processo'],
    'preferencia': ['prefiro', 'gosto', 'quero', 'meu', 'minha', 'pessoal'],
    'fato': ['é', 'são', 'significa', 'equivale', 'igual'],
    'correcao': ['na verdade', 'correto é', 'errado', 'certo é'],
}


class LearningService:
    """Detecta e processa comandos de aprendizado."""

    @staticmethod
    def detectar_comando(texto: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detecta se o texto é um comando de aprendizado.

        Returns:
            Tupla (tipo_comando, conteudo) ou (None, None)
            tipo_comando: 'lembrar', 'esquecer', 'listar'
        """
        texto_lower = texto.lower().strip()

        # Verifica padrões de LEMBRAR
        for padrao in PADROES_LEMBRAR:
            match = re.search(padrao, texto_lower, re.IGNORECASE)
            if match:
                return ('lembrar', match.group(1).strip())

        # Verifica padrões de ESQUECER
        for padrao in PADROES_ESQUECER:
            match = re.search(padrao, texto_lower, re.IGNORECASE)
            if match:
                return ('esquecer', match.group(1).strip())

        # Verifica padrões de LISTAR
        for padrao in PADROES_LISTAR:
            if re.search(padrao, texto_lower, re.IGNORECASE):
                return ('listar', None)

        return (None, None)

    @staticmethod
    def processar_comando(
        tipo: str,
        conteudo: str,
        usuario_id: int,
        usuario_nome: str,
        global_: bool = False
    ) -> Dict:
        """
        Processa um comando de aprendizado.

        Args:
            tipo: 'lembrar', 'esquecer', 'listar'
            conteudo: Conteúdo do comando
            usuario_id: ID do usuário
            usuario_nome: Nome do usuário
            global_: Se True, aplica globalmente

        Returns:
            Dict com resultado da operação
        """
        if tipo == 'lembrar':
            return LearningService._processar_lembrar(
                conteudo, usuario_id, usuario_nome, global_
            )
        elif tipo == 'esquecer':
            return LearningService._processar_esquecer(
                conteudo, usuario_id, usuario_nome
            )
        elif tipo == 'listar':
            return LearningService._processar_listar(usuario_id)

        return {'sucesso': False, 'erro': 'Comando não reconhecido'}

    @staticmethod
    def _processar_lembrar(
        conteudo: str,
        usuario_id: int,
        usuario_nome: str,
        global_: bool = False
    ) -> Dict:
        """Processa comando de lembrar/salvar."""
        try:
            from .models import ClaudeAprendizado

            # Detecta categoria automaticamente
            categoria = LearningService._detectar_categoria(conteudo)

            # Gera chave única
            chave = LearningService._gerar_chave(conteudo)

            # Define escopo
            uid = None if global_ else usuario_id

            # Salva aprendizado
            aprendizado, criado = ClaudeAprendizado.adicionar(
                categoria=categoria,
                chave=chave,
                valor=conteudo,
                usuario_id=uid,
                criado_por=usuario_nome,
                prioridade=5,
                contexto={'comando': 'lembrar', 'texto_original': conteudo}
            )

            escopo = "globalmente" if global_ else "para você"
            acao = "Memorizado" if criado else "Atualizado"

            return {
                'sucesso': True,
                'tipo': 'aprendizado',
                'acao': acao.lower(),
                'mensagem': f"{acao} {escopo}: \"{conteudo}\"",
                'aprendizado': aprendizado.to_dict()
            }

        except Exception as e:
            logger.error(f"[LEARNING] Erro ao lembrar: {e}")
            return {'sucesso': False, 'erro': str(e)}

    @staticmethod
    def _processar_esquecer(
        conteudo: str,
        usuario_id: int,
        usuario_nome: str
    ) -> Dict:
        """Processa comando de esquecer/remover."""
        try:
            from .models import ClaudeAprendizado

            # Gera chave
            chave = LearningService._gerar_chave(conteudo)

            # Tenta desativar do usuário primeiro
            removido = ClaudeAprendizado.desativar(
                chave=chave,
                usuario_id=usuario_id,
                desativado_por=usuario_nome
            )

            if removido:
                return {
                    'sucesso': True,
                    'tipo': 'aprendizado',
                    'acao': 'removido',
                    'mensagem': f"Esquecido: \"{conteudo}\""
                }

            # Tenta busca parcial
            from sqlalchemy import or_
            from app import db

            encontrados = ClaudeAprendizado.query.filter(
                or_(
                    ClaudeAprendizado.usuario_id == usuario_id,
                    ClaudeAprendizado.usuario_id.is_(None)
                ),
                ClaudeAprendizado.ativo == True,
                ClaudeAprendizado.valor.ilike(f"%{conteudo}%")
            ).all()

            if encontrados:
                # Remove o primeiro encontrado
                encontrados[0].ativo = False
                encontrados[0].atualizado_por = usuario_nome
                db.session.commit()

                return {
                    'sucesso': True,
                    'tipo': 'aprendizado',
                    'acao': 'removido',
                    'mensagem': f"Esquecido: \"{encontrados[0].valor}\""
                }

            return {
                'sucesso': False,
                'mensagem': f"Não encontrei conhecimento sobre: \"{conteudo}\""
            }

        except Exception as e:
            logger.error(f"[LEARNING] Erro ao esquecer: {e}")
            return {'sucesso': False, 'erro': str(e)}

    @staticmethod
    def _processar_listar(usuario_id: int) -> Dict:
        """Processa comando de listar conhecimentos."""
        try:
            from .models import ClaudeAprendizado

            aprendizados = ClaudeAprendizado.buscar_aprendizados(
                usuario_id=usuario_id,
                incluir_globais=True
            )

            if not aprendizados:
                return {
                    'sucesso': True,
                    'tipo': 'listagem',
                    'mensagem': "Ainda não tenho conhecimentos salvos. Use 'Lembre que...' para me ensinar algo!",
                    'aprendizados': []
                }

            # Formata para exibição
            linhas = ["Aqui está o que eu sei:\n"]

            # Agrupa por escopo
            globais = [a for a in aprendizados if a.usuario_id is None]
            pessoais = [a for a in aprendizados if a.usuario_id is not None]

            if globais:
                linhas.append("**Conhecimentos Globais:**")
                for a in globais:
                    linhas.append(f"- [{a.categoria}] {a.valor}")
                linhas.append("")

            if pessoais:
                linhas.append("**Seus Conhecimentos:**")
                for a in pessoais:
                    linhas.append(f"- [{a.categoria}] {a.valor}")

            return {
                'sucesso': True,
                'tipo': 'listagem',
                'mensagem': "\n".join(linhas),
                'aprendizados': [a.to_dict() for a in aprendizados]
            }

        except Exception as e:
            logger.error(f"[LEARNING] Erro ao listar: {e}")
            return {'sucesso': False, 'erro': str(e)}

    @staticmethod
    def _detectar_categoria(texto: str) -> str:
        """Detecta categoria automaticamente baseado em palavras-chave."""
        texto_lower = texto.lower()

        for categoria, palavras in CATEGORIAS_AUTO.items():
            for palavra in palavras:
                if palavra in texto_lower:
                    return categoria

        return 'fato'  # Default

    @staticmethod
    def _gerar_chave(texto: str) -> str:
        """Gera uma chave única para o aprendizado."""
        import hashlib

        # Normaliza texto
        normalizado = texto.lower().strip()
        normalizado = re.sub(r'[^\w\s]', '', normalizado)
        normalizado = re.sub(r'\s+', '_', normalizado)

        # Limita tamanho e adiciona hash para unicidade
        if len(normalizado) > 50:
            hash_suffix = hashlib.md5(texto.encode()).hexdigest()[:8]
            normalizado = normalizado[:42] + '_' + hash_suffix

        return normalizado

    @staticmethod
    def verificar_comando_global(texto: str) -> bool:
        """Verifica se o comando deve ser aplicado globalmente."""
        padroes_global = [
            r'\(?\s*global\s*\)?',
            r'para\s+todos',
            r'para\s+todo\s+mundo',
            r'para\s+a\s+empresa',
            r'para\s+o\s+sistema',
        ]

        texto_lower = texto.lower()
        for padrao in padroes_global:
            if re.search(padrao, texto_lower):
                return True

        return False
