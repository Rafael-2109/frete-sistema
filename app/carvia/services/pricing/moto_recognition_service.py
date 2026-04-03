"""
MotoRecognitionService — Reconhecimento de motos em itens de NF
================================================================

Extrai modelo de moto do texto de descricao de produto,
calcula peso cubado automatico usando tabela CarviaModeloMoto.

Fluxo:
1. Para cada item de NF da operacao, tenta match de modelo via regex
2. Se match: usa peso_medio (se disponivel) ou calcula volume * cubagem_minima
3. Soma peso cubado de todos os itens matcheados

IMPORTANTE — Dimensoes em CENTIMETROS:
As colunas comprimento/largura/altura de CarviaModeloMoto armazenam valores
em centimetros (ex: 137 = 137cm = 1.37m).
Formula: C(cm) × L(cm) × A(cm) / 1.000.000 = volume(m3) × cubagem_minima(kg/m3)
"""

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)

# --- Patterns de reconhecimento de motos (3 camadas) ---

# Camada 1: Motos convencionais — MARCA + cilindrada (ex: CG 160, BIZ 125)
CONVENCIONAL_MOTO_PATTERN = re.compile(
    r'\b(CG|FACTOR|BIZ|NXR|POP|XRE|TITAN|YBR|FAZER|FAN|CB|CBR|BROS|CROSSER'
    r'|LANDER|TENERE|MT|XTZ|NMAX|NEO|FLUO|PCX|SH|ADV|SAHARA'
    r'|DUKE|NINJA|Z\d{3}|TRACER|R\d)'
    r'\s*'
    r'(\d{2,3})',
    re.IGNORECASE
)

# Camada 2: Veiculos eletricos — deteccao por keyword
VEICULO_ELETRICO_DETECT = re.compile(
    r'\b(MOTO|SCOOTER|BIKE)\b',
    re.IGNORECASE
)

# Camada 2b: Modelos conhecidos de veiculos eletricos (producao real)
# Patterns mais longos PRIMEIRO para evitar match parcial (X11 MINI antes de X11)
VEICULO_ELETRICO_MODELOS = re.compile(
    r'\b(X11[\s-]?MINI|JOY[\s-]?SUPER|MIA[\s-]?TRI'
    r'|X12|X15|X11|B2|B3|GRID|JET|ROMA|GIGA|RET|S8|BOB|DOT|POP|VED)\b',
    re.IGNORECASE
)

# Camada 3: Prefixo de codigo de produto (MT-JET, MT-X12, etc.)
CODIGO_MOTO_PREFIX = re.compile(r'^MT-(.+)$', re.IGNORECASE)


class MotoRecognitionService:
    """Servico de reconhecimento de motos em itens de NF"""

    @staticmethod
    def _calcular_peso_modelo(modelo, qtd: float) -> float:
        """Calcula peso cubado de um modelo * quantidade.

        Usa peso_medio se disponivel (ja pre-calculado em kg).
        Fallback: C(cm) × L(cm) × A(cm) / 1.000.000 × cubagem_minima(kg/m3).
        """
        if modelo.peso_medio:
            return float(modelo.peso_medio) * qtd

        # Dimensoes em centimetros — converter para m3 dividindo por 1.000.000
        comp_cm = float(modelo.comprimento)
        larg_cm = float(modelo.largura)
        alt_cm = float(modelo.altura)
        cubagem = float(modelo.cubagem_minima)
        volume_m3 = comp_cm * larg_cm * alt_cm / 1_000_000
        return volume_m3 * cubagem * qtd

    @staticmethod
    def _match_descricao(
        texto: str,
        modelos: list,
        codigo_produto: str = None,
        ncm: str = None,
    ) -> Optional[str]:
        """Match descricao contra lista de modelos pre-carregada (sem query DB).

        Ordem de prioridade:
        0. Gate NCM: se NCM presente e nao comeca com 8711, pular (nao e moto)
        1. Patterns customizados de CarviaModeloMoto (regex_pattern ou nome exato)
        2. Motos convencionais (MARCA + cilindrada: CG 160, BIZ 125)
        3. Veiculos eletricos (keyword MOTO/SCOOTER/BIKE + modelo conhecido)
        4. Prefixo codigo_produto MT-XXX

        Args:
            texto: Descricao do produto
            modelos: Lista de CarviaModeloMoto (ja carregados)
            codigo_produto: Codigo do produto (opcional, usado como fallback)
            ncm: NCM do item (opcional). Se presente e nao 8711*, rejeita match

        Returns:
            Nome do modelo matcheado ou None
        """
        if not texto:
            return None

        # Gate NCM: se item tem NCM e NAO e veiculo/moto (8711*), pular
        if ncm:
            ncm_limpo = re.sub(r'[.\-\s]', '', ncm).strip()
            if ncm_limpo and not ncm_limpo.startswith('8711'):
                return None

        texto_upper = texto.upper().strip()

        # 1. Patterns customizados do banco
        for modelo in modelos:
            if modelo.regex_pattern:
                try:
                    if re.search(modelo.regex_pattern, texto_upper, re.IGNORECASE):
                        return modelo.nome
                except re.error:
                    pass
            # Match por nome com word boundary (evita falso positivo:
            # modelo "RET" nao deve matchear em "PRETA")
            nome_escaped = re.escape(modelo.nome.upper())
            if re.search(r'(?<![A-Za-z])' + nome_escaped + r'(?![A-Za-z])', texto_upper):
                return modelo.nome

        # 2. Motos convencionais (Honda, Yamaha, etc.)
        match = CONVENCIONAL_MOTO_PATTERN.search(texto_upper)
        if match:
            marca = match.group(1).upper()
            cilindrada = match.group(2)
            return f'{marca} {cilindrada}'

        # 3. Veiculos eletricos — keyword + modelo conhecido
        if VEICULO_ELETRICO_DETECT.search(texto_upper):
            modelo_match = VEICULO_ELETRICO_MODELOS.search(texto_upper)
            if modelo_match:
                nome = modelo_match.group(1).upper().strip()
                # Normalizar separadores: "X11-MINI" → "X11 MINI"
                return re.sub(r'[\s-]+', ' ', nome)

        # 4. Fallback: prefixo codigo de produto (MT-JET, MT-X12, etc.)
        if codigo_produto:
            cod_match = CODIGO_MOTO_PREFIX.match(codigo_produto.strip())
            if cod_match:
                return cod_match.group(1).upper()

        return None

    def extrair_modelo(
        self, texto: str, codigo_produto: str = None, ncm: str = None,
    ) -> Optional[str]:
        """
        Extrai modelo de moto do texto da descricao.

        Args:
            texto: Descricao do produto
            codigo_produto: Codigo do produto (opcional, usado como fallback)
            ncm: NCM do item (opcional). Se presente e nao 8711*, rejeita

        Returns:
            Nome normalizado do modelo (ex: 'CG 160', 'X12', 'JET') ou None
        """
        from app.carvia.models import CarviaModeloMoto
        modelos = CarviaModeloMoto.query.filter_by(ativo=True).all()
        return self._match_descricao(texto, modelos, codigo_produto, ncm=ncm)

    def identificar_motos_operacao(self, operacao_id: int) -> List[Dict]:
        """
        Para cada NF da operacao, lista itens com modelo de moto.

        Le do campo persistido item.modelo_moto_id (preenchido na importacao).

        Args:
            operacao_id: ID da CarviaOperacao

        Returns:
            Lista de dicts com itens matcheados:
            [{'item_id', 'codigo_produto', 'descricao', 'modelo_match',
              'modelo_moto_id', 'quantidade'}]
        """
        from app.carvia.models import CarviaOperacao, CarviaNfItem, CarviaOperacaoNf
        from app.carvia.models import CarviaModeloMoto

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return []

        # Buscar itens com modelo_moto_id persistido
        itens = db.session.query(CarviaNfItem).join(
            CarviaOperacaoNf,
            CarviaOperacaoNf.nf_id == CarviaNfItem.nf_id
        ).filter(
            CarviaOperacaoNf.operacao_id == operacao_id,
            CarviaNfItem.modelo_moto_id.isnot(None),
        ).all()

        resultados = []
        for item in itens:
            modelo = db.session.get(CarviaModeloMoto, item.modelo_moto_id)
            resultados.append({
                'item_id': item.id,
                'codigo_produto': item.codigo_produto,
                'descricao': item.descricao,
                'modelo_match': modelo.nome if modelo else None,
                'modelo_moto_id': item.modelo_moto_id,
                'quantidade': float(item.quantidade or 1),
            })

        return resultados

    def calcular_peso_cubado_operacao(self, operacao_id: int) -> Optional[Dict]:
        """
        Calcula peso cubado total da operacao baseado em motos identificadas.

        Para cada item matcheado com modelo cadastrado:
            Se peso_medio disponivel: peso_cubado = peso_medio * quantidade
            Senao: C×L×A / 1.000.000 * cubagem_minima * quantidade

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

            qtd = item['quantidade']
            peso_cubado_item = self._calcular_peso_modelo(modelo, qtd)

            # Detalhes para exibicao (dimensoes em CM)
            comp_cm = float(modelo.comprimento)
            larg_cm = float(modelo.largura)
            alt_cm = float(modelo.altura)
            cubagem = float(modelo.cubagem_minima)
            volume_m3 = comp_cm * larg_cm * alt_cm / 1_000_000
            peso_cubado_unitario = self._calcular_peso_modelo(modelo, 1)

            itens_calculados.append({
                'item_id': item['item_id'],
                'modelo': modelo.nome,
                'dimensoes': f'{comp_cm:.0f}x{larg_cm:.0f}x{alt_cm:.0f}cm',
                'volume_m3': round(volume_m3, 4),
                'cubagem_minima': cubagem,
                'peso_cubado_unitario': round(peso_cubado_unitario, 2),
                'quantidade': qtd,
                'peso_cubado_item': round(peso_cubado_item, 2),
            })

            peso_cubado_total += peso_cubado_item

            detalhes_parts.append(
                f'{modelo.nome}: {comp_cm:.0f}x{larg_cm:.0f}x{alt_cm:.0f}cm = '
                f'{volume_m3:.4f}m3 x {cubagem}kg/m3 = '
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

    def calcular_peso_cubado_nf(self, nf_id: int) -> Optional[Dict]:
        """
        Calcula peso cubado total de uma NF a partir do modelo persistido nos itens.

        Le item.modelo_moto_id (preenchido na importacao ou via edicao manual).
        NAO re-executa deteccao — apenas consulta o campo salvo.

        Args:
            nf_id: ID da CarviaNf

        Returns:
            Dict com resultado ou None se nenhum item com modelo:
            {'peso_cubado_total': float, 'itens': [...]}
        """
        from app.carvia.models import CarviaNfItem, CarviaModeloMoto

        itens = CarviaNfItem.query.filter(
            CarviaNfItem.nf_id == nf_id,
            CarviaNfItem.modelo_moto_id.isnot(None),
        ).all()
        if not itens:
            return None

        itens_calculados = []
        peso_cubado_total = 0

        for item in itens:
            modelo = db.session.get(CarviaModeloMoto, item.modelo_moto_id)
            if not modelo:
                continue

            qtd = float(item.quantidade or 1)
            peso_item = self._calcular_peso_modelo(modelo, qtd)

            itens_calculados.append({
                'item_id': item.id,
                'modelo': modelo.nome,
                'quantidade': qtd,
                'peso_cubado_item': round(peso_item, 2),
                'comprimento_cm': float(modelo.comprimento or 0),
                'largura_cm': float(modelo.largura or 0),
                'altura_cm': float(modelo.altura or 0),
                'cubagem_minima': float(modelo.cubagem_minima or 0),
                'peso_medio': float(modelo.peso_medio) if modelo.peso_medio else None,
            })
            peso_cubado_total += peso_item

        if not itens_calculados:
            return None

        return {
            'peso_cubado_total': round(peso_cubado_total, 2),
            'itens': itens_calculados,
        }

    def calcular_peso_cubado_batch(self, nf_ids: List[int]) -> Dict[int, float]:
        """
        Calcula peso cubado para multiplas NFs em batch a partir do persistido.

        Le item.modelo_moto_id — NAO re-executa deteccao.

        Args:
            nf_ids: Lista de IDs de CarviaNf

        Returns:
            Dict mapeando nf_id -> peso_cubado_total (somente NFs com match)
        """
        if not nf_ids:
            return {}

        from app.carvia.models import CarviaNfItem, CarviaModeloMoto

        itens = CarviaNfItem.query.filter(
            CarviaNfItem.nf_id.in_(nf_ids),
            CarviaNfItem.modelo_moto_id.isnot(None),
        ).all()
        if not itens:
            return {}

        # Carregar modelos em batch
        modelo_ids = {item.modelo_moto_id for item in itens}
        modelos_by_id = {
            m.id: m for m in CarviaModeloMoto.query.filter(
                CarviaModeloMoto.id.in_(modelo_ids)
            ).all()
        }

        itens_por_nf = defaultdict(list)
        for item in itens:
            itens_por_nf[item.nf_id].append(item)

        resultado = {}
        for nf_id in nf_ids:
            peso_cubado = 0.0
            for item in itens_por_nf.get(nf_id, []):
                modelo = modelos_by_id.get(item.modelo_moto_id)
                if not modelo:
                    continue
                qtd = float(item.quantidade or 1)
                peso_cubado += self._calcular_peso_modelo(modelo, qtd)

            if peso_cubado > 0:
                resultado[nf_id] = round(peso_cubado, 2)

        return resultado

    def categorizar_itens_operacao(self, operacao_id: int) -> Dict:
        """Identifica motos nos itens de NF e agrupa por categoria.

        Args:
            operacao_id: ID da CarviaOperacao

        Returns:
            Dict com 'por_categoria', 'total_motos', 'nao_categorizados'
        """
        from app.carvia.models import CarviaModeloMoto, CarviaCategoriaMoto

        itens_match = self.identificar_motos_operacao(operacao_id)
        if not itens_match:
            return {'por_categoria': [], 'total_motos': 0, 'nao_categorizados': 0}

        # Agrupar por categoria
        categorias = {}  # cat_id -> {'nome', 'quantidade', 'modelos': set}
        nao_categorizados = 0
        total_motos = 0

        for item in itens_match:
            qtd = int(item.get('quantidade', 1))
            total_motos += qtd
            modelo_id = item.get('modelo_moto_id')

            if not modelo_id:
                nao_categorizados += qtd
                continue

            modelo = db.session.get(CarviaModeloMoto, modelo_id)
            if not modelo or not modelo.categoria_moto_id:
                nao_categorizados += qtd
                continue

            cat_id = modelo.categoria_moto_id
            if cat_id not in categorias:
                categoria = db.session.get(CarviaCategoriaMoto, cat_id)
                categorias[cat_id] = {
                    'categoria_id': cat_id,
                    'categoria_nome': categoria.nome if categoria else f'Cat#{cat_id}',
                    'quantidade': 0,
                    'modelos': set(),
                }
            categorias[cat_id]['quantidade'] += qtd
            categorias[cat_id]['modelos'].add(item.get('modelo_match', ''))

        # Converter sets para listas
        por_categoria = []
        for info in categorias.values():
            info['modelos'] = sorted(info['modelos'])
            por_categoria.append(info)

        return {
            'por_categoria': por_categoria,
            'total_motos': total_motos,
            'nao_categorizados': nao_categorizados,
        }

    def detectar_e_persistir_nf(self, nf_id: int) -> int:
        """
        Roda deteccao automatica nos itens de uma NF e persiste modelo_moto_id.

        Chamado na importacao (uma vez). Itens que ja tem modelo_moto_id
        sao ignorados (preserva override manual).

        Args:
            nf_id: ID da CarviaNf

        Returns:
            Quantidade de itens que receberam modelo
        """
        from app.carvia.models import CarviaNfItem, CarviaModeloMoto

        itens = CarviaNfItem.query.filter_by(nf_id=nf_id).filter(
            CarviaNfItem.modelo_moto_id.is_(None)
        ).all()
        if not itens:
            return 0

        modelos = CarviaModeloMoto.query.filter_by(ativo=True).all()
        modelos_by_nome = {m.nome: m for m in modelos}
        count = 0

        for item in itens:
            modelo_nome = self._match_descricao(
                item.descricao, modelos, item.codigo_produto, ncm=item.ncm,
            )
            if not modelo_nome or modelo_nome not in modelos_by_nome:
                continue

            item.modelo_moto_id = modelos_by_nome[modelo_nome].id
            count += 1

        if count > 0:
            db.session.flush()
            logger.info(
                "detectar_e_persistir_nf: nf_id=%d — %d item(ns) com modelo",
                nf_id, count,
            )

        return count

    def reprocessar_itens_nf(self, nf_id: int) -> Dict:
        """
        Re-roda deteccao em TODOS os itens da NF (limpa e re-detecta).

        Usado quando o usuario clica 'Re-processar motos' na tela de detalhe.

        Args:
            nf_id: ID da CarviaNf

        Returns:
            {'total_itens': int, 'detectados': int, 'limpos': int}
        """
        from app.carvia.models import CarviaNfItem, CarviaModeloMoto

        itens = CarviaNfItem.query.filter_by(nf_id=nf_id).all()
        if not itens:
            return {'total_itens': 0, 'detectados': 0, 'limpos': 0}

        modelos = CarviaModeloMoto.query.filter_by(ativo=True).all()
        modelos_by_nome = {m.nome: m for m in modelos}

        detectados = 0
        limpos = 0

        for item in itens:
            modelo_nome = self._match_descricao(
                item.descricao, modelos, item.codigo_produto, ncm=item.ncm,
            )
            if modelo_nome and modelo_nome in modelos_by_nome:
                novo_id = modelos_by_nome[modelo_nome].id
                if item.modelo_moto_id != novo_id:
                    item.modelo_moto_id = novo_id
                detectados += 1
            else:
                if item.modelo_moto_id is not None:
                    item.modelo_moto_id = None
                    limpos += 1

        db.session.flush()
        logger.info(
            "reprocessar_itens_nf: nf_id=%d — %d detectados, %d limpos de %d total",
            nf_id, detectados, limpos, len(itens),
        )

        return {
            'total_itens': len(itens),
            'detectados': detectados,
            'limpos': limpos,
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
