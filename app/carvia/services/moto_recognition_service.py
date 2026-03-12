"""
MotoRecognitionService — Reconhecimento de motos em itens de NF
================================================================

Extrai modelo de moto do texto de descricao de produto,
calcula peso cubado automatico usando tabela CarviaModeloMoto.

Fluxo:
1. Para cada item de NF da operacao, tenta match de modelo via regex
2. Se match: calcula volume unitario * cubagem_minima * quantidade
3. Soma peso cubado de todos os itens matcheados
"""

import logging
import re
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)

# Patterns padrao para modelos de moto conhecidos
# Formato: MARCA + NUMERO (ex: CG 160, FACTOR 150, BIZ 125)
DEFAULT_MOTO_PATTERN = re.compile(
    r'\b(CG|FACTOR|BIZ|NXR|POP|XRE|TITAN|YBR|FAZER|FAN|CB|CBR|BROS|CROSSER'
    r'|LANDER|TENERE|MT|XTZ|NMAX|NEO|FLUO|PCX|SH|ADV|SAHARA'
    r'|DUKE|NINJA|Z\d{3}|TRACER|R\d)'
    r'\s*'
    r'(\d{2,3})',
    re.IGNORECASE
)


class MotoRecognitionService:
    """Servico de reconhecimento de motos em itens de NF"""

    def extrair_modelo(self, texto: str) -> Optional[str]:
        """
        Extrai modelo de moto do texto da descricao.

        Tenta primeiro patterns customizados de CarviaModeloMoto,
        depois o pattern padrao.

        Args:
            texto: Descricao do produto

        Returns:
            Nome normalizado do modelo (ex: 'CG 160') ou None
        """
        if not texto:
            return None

        texto_upper = texto.upper().strip()

        # 1. Tentar patterns customizados dos modelos cadastrados
        from app.carvia.models import CarviaModeloMoto
        modelos = CarviaModeloMoto.query.filter_by(ativo=True).all()
        for modelo in modelos:
            if modelo.regex_pattern:
                try:
                    if re.search(modelo.regex_pattern, texto_upper, re.IGNORECASE):
                        return modelo.nome
                except re.error:
                    logger.warning(
                        "Regex invalido no modelo %s: %s",
                        modelo.nome, modelo.regex_pattern
                    )

            # Match por nome exato (case insensitive)
            if modelo.nome.upper() in texto_upper:
                return modelo.nome

        # 2. Fallback: pattern padrao
        match = DEFAULT_MOTO_PATTERN.search(texto_upper)
        if match:
            marca = match.group(1).upper()
            cilindrada = match.group(2)
            return f'{marca} {cilindrada}'

        return None

    def identificar_motos_operacao(self, operacao_id: int) -> List[Dict]:
        """
        Para cada NF da operacao, para cada item da NF, tenta match.

        Args:
            operacao_id: ID da CarviaOperacao

        Returns:
            Lista de dicts com itens matcheados:
            [{'item_id', 'codigo_produto', 'descricao', 'modelo_match',
              'modelo_moto_id', 'quantidade'}]
        """
        from app.carvia.models import CarviaOperacao, CarviaNfItem, CarviaOperacaoNf

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return []

        # Buscar todos os itens de NFs vinculadas
        itens = db.session.query(CarviaNfItem).join(
            CarviaOperacaoNf,
            CarviaOperacaoNf.nf_id == CarviaNfItem.nf_id
        ).filter(
            CarviaOperacaoNf.operacao_id == operacao_id
        ).all()

        resultados = []
        from app.carvia.models import CarviaModeloMoto

        for item in itens:
            modelo_nome = self.extrair_modelo(item.descricao)
            if modelo_nome:
                # Tentar encontrar modelo cadastrado
                modelo_db = CarviaModeloMoto.query.filter(
                    CarviaModeloMoto.nome == modelo_nome,
                    CarviaModeloMoto.ativo == True,  # noqa: E712
                ).first()

                resultados.append({
                    'item_id': item.id,
                    'codigo_produto': item.codigo_produto,
                    'descricao': item.descricao,
                    'modelo_match': modelo_nome,
                    'modelo_moto_id': modelo_db.id if modelo_db else None,
                    'quantidade': float(item.quantidade or 1),
                })

        return resultados

    def calcular_peso_cubado_operacao(self, operacao_id: int) -> Optional[Dict]:
        """
        Calcula peso cubado total da operacao baseado em motos identificadas.

        Para cada item matcheado com modelo cadastrado:
            volume_unitario = comprimento * largura * altura (m3)
            peso_cubado_unitario = volume_unitario * cubagem_minima (default 300 kg/m3)
            peso_cubado_item = peso_cubado_unitario * quantidade

        Args:
            operacao_id: ID da CarviaOperacao

        Returns:
            Dict com resultado ou None se nenhum match:
            {'peso_cubado_total': float, 'itens': [...], 'detalhes_calculo': str}
        """
        from app.carvia.models import CarviaModeloMoto

        itens_match = self.identificar_motos_operacao(operacao_id)
        if not itens_match:
            return None

        itens_calculados = []
        peso_cubado_total = 0
        detalhes_parts = []

        for item in itens_match:
            modelo_id = item.get('modelo_moto_id')
            if not modelo_id:
                continue

            modelo = db.session.get(CarviaModeloMoto, modelo_id)
            if not modelo:
                continue

            comp = float(modelo.comprimento)
            larg = float(modelo.largura)
            alt = float(modelo.altura)
            cubagem = float(modelo.cubagem_minima)
            qtd = item['quantidade']

            volume_unitario = comp * larg * alt  # m3
            peso_cubado_unitario = volume_unitario * cubagem
            peso_cubado_item = peso_cubado_unitario * qtd

            itens_calculados.append({
                'item_id': item['item_id'],
                'modelo': modelo.nome,
                'dimensoes': f'{comp}x{larg}x{alt}m',
                'volume_m3': round(volume_unitario, 4),
                'cubagem_minima': cubagem,
                'peso_cubado_unitario': round(peso_cubado_unitario, 2),
                'quantidade': qtd,
                'peso_cubado_item': round(peso_cubado_item, 2),
            })

            peso_cubado_total += peso_cubado_item

            detalhes_parts.append(
                f'{modelo.nome}: {comp}x{larg}x{alt}m = '
                f'{volume_unitario:.4f}m3 x {cubagem}kg/m3 = '
                f'{peso_cubado_unitario:.2f}kg x {int(qtd)} = '
                f'{peso_cubado_item:.2f}kg'
            )

        if not itens_calculados:
            return None

        return {
            'peso_cubado_total': round(peso_cubado_total, 2),
            'itens': itens_calculados,
            'detalhes_calculo': '\n'.join(detalhes_parts),
        }

    def empresa_usa_cubagem(self, cnpj: str) -> bool:
        """
        Verifica se a empresa (CNPJ) esta configurada para usar cubagem.

        Args:
            cnpj: CNPJ da empresa (com ou sem formatacao)

        Returns:
            True se empresa tem considerar_cubagem=True
        """
        if not cnpj:
            return False

        from app.carvia.models import CarviaEmpresaCubagem
        import re as _re

        cnpj_limpo = _re.sub(r'\D', '', cnpj)
        empresa = CarviaEmpresaCubagem.query.filter(
            db.func.regexp_replace(
                CarviaEmpresaCubagem.cnpj_empresa, r'\D', '', 'g'
            ) == cnpj_limpo
        ).first()

        return bool(empresa and empresa.considerar_cubagem)
