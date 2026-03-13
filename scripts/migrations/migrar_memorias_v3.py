"""
Migração de memórias do agente: formato legado → CAPDo v3.0

Converte TODAS as memórias empresa (user_id=0) para o novo formato:
- <regra> → <conhecimento tipo="armadilha" nivel="4">
- <correcao> → <conhecimento tipo="armadilha" nivel="4">
- <termo> → <conhecimento tipo="heuristica" nivel="3">
- <usuario> → <conhecimento tipo="heuristica" nivel="3">
- <admin_correction> → <conhecimento tipo="armadilha" nivel="4">
- v3 com tipos antigos (causal, relacional, procedimental, condicional) → tipos novos

Também:
- Relocar paths para hierarquia v3: /memories/empresa/{protocolos|armadilhas|heuristicas}/{dominio}/{slug}.xml
- Remover 4 duplicatas identificadas

Executar: python scripts/migrations/migrar_memorias_v3.py [--dry-run]
"""
import sys
import os
import re
import unicodedata
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# =====================================================================
# HELPERS (replicados de pattern_analyzer.py para independência)
# =====================================================================

def _xml_escape(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _xml_unescape(text: str) -> str:
    """Desfaz escape XML para extrair texto limpo."""
    if not text:
        return ""
    return unescape(
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )


def _slugify(text: str, max_len: int = 60) -> str:
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')
    if len(slug) <= max_len:
        return slug
    truncated = slug[:max_len]
    last_sep = truncated.rfind('-')
    if last_sep > max_len / 2:
        return truncated[:last_sep]
    return truncated


def _extract_tag_content(xml: str, tag: str) -> str:
    """Extrai conteúdo de uma tag XML simples."""
    # Tenta com atributos
    pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
    match = re.search(pattern, xml, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _extract_tag_attr(xml: str, tag: str, attr: str) -> str:
    """Extrai atributo de uma tag XML."""
    pattern = rf'<{tag}\s+[^>]*{attr}="([^"]*)"'
    match = re.search(pattern, xml, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _build_v3_content(tipo, nivel, dominio, titulo, descricao, prescricao, criterios=""):
    """Constrói XML no formato CAPDo v3.0."""
    return (
        f'<conhecimento tipo="{_xml_escape(tipo)}" '
        f'nivel="{nivel}" '
        f'dominio="{_xml_escape(dominio)}">'
        f'\n  <titulo>{_xml_escape(titulo)}</titulo>'
        f'\n  <descricao>{_xml_escape(descricao)}</descricao>'
        f'\n  <prescricao>{_xml_escape(prescricao)}</prescricao>'
        f'\n  <criterios>{criterios}</criterios>'
        f'\n</conhecimento>'
    )


def _build_v3_path(tipo, dominio, titulo, descricao=""):
    """Constrói path hierárquico v3."""
    _TIPO_TO_SUBDIR = {
        "protocolo": "protocolos",
        "armadilha": "armadilhas",
        "heuristica": "heuristicas",
    }
    subdir = _TIPO_TO_SUBDIR.get(tipo, "protocolos")
    if dominio:
        subdir = f"{subdir}/{dominio}"

    slug_source = titulo.strip() if titulo else (descricao or "sem-titulo")[:80]
    slug = _slugify(slug_source)
    if not slug:
        slug = _slugify((descricao or "sem-titulo")[:80])
    return f"/memories/empresa/{subdir}/{slug}.xml"


# =====================================================================
# PARSERS POR FORMATO LEGADO
# =====================================================================

def _parse_regra(content: str) -> dict:
    """Converte <regra> → armadilha nivel 4."""
    descricao = _extract_tag_content(content, 'descricao')
    contexto = _extract_tag_content(content, 'contexto')

    if not descricao:
        return None

    titulo = descricao[:60]
    prescricao = (
        f'Quando a situacao envolver: {contexto or "contexto geral"}, '
        f'aplicar a regra: {descricao}'
    )

    # Inferir domínio pelo contexto
    dominio = _inferir_dominio(descricao + " " + contexto)

    return {
        'tipo': 'armadilha',
        'nivel': '4',
        'dominio': dominio,
        'titulo': titulo,
        'descricao': descricao,
        'prescricao': prescricao,
        'criterios': '2,3',
    }


def _parse_correcao(content: str) -> dict:
    """Converte <correcao> → armadilha nivel 4."""
    errado = _extract_tag_content(content, 'errado') or _extract_tag_content(content, 'erro_comum')
    correto = _extract_tag_content(content, 'correto')
    contexto = _extract_tag_content(content, 'contexto')

    if not errado or not correto:
        return None

    titulo = f'Correcao: {correto[:50]}'
    descricao = f'Errado: {errado}. Correto: {correto}'
    prescricao = (
        f'Quando a situacao envolver {contexto or "este tema"}, '
        f'NUNCA usar "{errado[:60]}" — o correto eh "{correto[:60]}"'
    )

    dominio = _inferir_dominio(descricao + " " + contexto)

    return {
        'tipo': 'armadilha',
        'nivel': '4',
        'dominio': dominio,
        'titulo': titulo,
        'descricao': descricao,
        'prescricao': prescricao,
        'criterios': '2,4',
    }


def _parse_termo(content: str) -> dict:
    """Converte <termo> → heuristica nivel 3."""
    nome = _extract_tag_attr(content, 'termo', 'nome')
    definicao = _extract_tag_content(content, 'definicao')

    if not nome or not definicao:
        return None

    titulo = f'Definicao de {nome}'
    descricao = f'{nome}: {definicao}'
    prescricao = f'Quando alguem mencionar "{nome}", interpretar como: {definicao}'

    dominio = _inferir_dominio(descricao)

    return {
        'tipo': 'heuristica',
        'nivel': '3',
        'dominio': dominio,
        'titulo': titulo,
        'descricao': descricao,
        'prescricao': prescricao,
        'criterios': '3,4',
    }


def _parse_usuario(content: str) -> dict:
    """Converte <usuario> → heuristica nivel 3."""
    nome = _extract_tag_attr(content, 'usuario', 'nome')
    cargo = _extract_tag_content(content, 'cargo')
    user_id_tag = _extract_tag_content(content, 'user_id')
    canal = _extract_tag_content(content, 'canal')
    workflow = _extract_tag_content(content, 'workflow_principal')

    if not nome:
        return None

    # Construir descrição rica
    parts = [f'{nome}']
    if cargo:
        parts.append(f'cargo: {cargo}')
    if user_id_tag:
        parts.append(f'user_id: {user_id_tag}')
    if canal:
        parts.append(f'canal: {canal}')
    descricao = '. '.join(parts)
    if workflow:
        descricao += f'. Workflow: {workflow[:200]}'

    titulo = f'Perfil de {nome}'
    prescricao = (
        f'Quando interagir com {nome}, lembrar que: {cargo or "usuario do sistema"}. '
    )
    if canal:
        prescricao += f'Canal: {canal}. '
    if workflow:
        prescricao += f'Workflow principal: {workflow[:150]}'

    return {
        'tipo': 'heuristica',
        'nivel': '3',
        'dominio': 'usuarios',
        'titulo': titulo,
        'descricao': descricao,
        'prescricao': prescricao,
        'criterios': '3,4',
    }


def _parse_admin_correction(content: str) -> dict:
    """Converte <admin_correction> → armadilha nivel 4."""
    text = _extract_tag_content(content, 'text')
    if not text:
        return None

    # Extrair primeira frase como título
    first_sentence = text.split('\n')[0].strip()
    if len(first_sentence) > 60:
        first_sentence = first_sentence[:57] + '...'

    titulo = first_sentence
    descricao = text[:500]
    prescricao = text  # O texto já é prescritivo

    dominio = _inferir_dominio(text)

    return {
        'tipo': 'armadilha',
        'nivel': '4',
        'dominio': dominio,
        'titulo': titulo,
        'descricao': descricao,
        'prescricao': prescricao,
        'criterios': '1,2,4',
    }


def _parse_v3_antigo(content: str) -> dict:
    """Atualiza v3 com tipos epistemológicos antigos para tipos operacionais novos."""
    tipo_antigo = _extract_tag_attr(content, 'conhecimento', 'tipo')
    descricao = _extract_tag_content(content, 'descricao')
    prescricao = _extract_tag_content(content, 'prescricao')
    problema = _extract_tag_content(content, 'problema_que_resolve')

    _LEGACY_MAP = {
        'procedimental': 'protocolo',
        'conceitual': 'heuristica',
        'condicional': 'armadilha',
        'causal': 'armadilha',
        'relacional': 'heuristica',
    }

    tipo_novo = _LEGACY_MAP.get(tipo_antigo)
    if not tipo_novo:
        return None  # Já é v3 com tipo novo

    # Se não tem prescricao mas tem problema_que_resolve, gerar prescricao
    if not prescricao and problema:
        prescricao = problema
    if not prescricao and descricao:
        prescricao = descricao

    # Extrair título do path ou gerar do descricao
    titulo = descricao[:60] if descricao else "Sem titulo"

    dominio = _inferir_dominio(descricao or "")

    return {
        'tipo': tipo_novo,
        'nivel': '4' if tipo_novo == 'armadilha' else ('3' if tipo_novo == 'heuristica' else '4'),
        'dominio': dominio,
        'titulo': titulo,
        'descricao': descricao or "",
        'prescricao': prescricao or descricao or "",
        'criterios': '2,3',
    }


# =====================================================================
# INFERÊNCIA DE DOMÍNIO
# =====================================================================

_DOMINIO_KEYWORDS = {
    'odoo': ['odoo', 'purchase order', 'pedido de venda', 'cotação odoo', 'locked',
             'purchase_order_id', 'sale.order', 'draft'],
    'expedicao': ['separação', 'separacao', 'expedição', 'expedicao', 'lote',
                  'VCD', 'carteira', 'estoque'],
    'financeiro': ['NF', 'nota fiscal', 'frete', 'faturamento', 'embarque',
                   'CNPJ', 'frete minimo', 'valor_cotado'],
    'recebimento': ['recebimento', 'integração', 'integracao', 'DFe',
                    'PO', 'fornecedor', 'compras'],
    'teams': ['Teams', 'teams', 'bot', 'saudação', 'saudacao'],
    'clientes': ['Atacadão', 'Atacadao', 'Assaí', 'Assai', 'Sanna',
                 'cliente', 'loja'],
    'usuarios': ['Elaine', 'Denise', 'Gabriella', 'Edson', 'Kerley',
                 'Fernando', 'Rafael', 'operador'],
    'sistema': ['agente', 'agent', 'sistema', 'produção', 'producao',
                'SDK', 'debug', 'modo debug'],
}


def _inferir_dominio(text: str) -> str:
    """Infere domínio a partir do conteúdo."""
    if not text:
        return "geral"

    scores = {}
    text_lower = text.lower()
    for dominio, keywords in _DOMINIO_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[dominio] = score

    if not scores:
        return "geral"
    return max(scores, key=scores.get)


# =====================================================================
# DUPLICATAS A REMOVER
# =====================================================================

DUPLICATAS_REMOVER = [
    # (user_id, path, motivo)
    (0, "/memories/empresa/regras/pedidos-de-separacao-feitos-via-teams-de.xml",
     "subset de operadores-do-teams-bot"),
    (0, "/memories/empresa/regras/elaine-possui-dois-cadastros-no-sistema.xml",
     "subset de operadores-do-teams-bot"),
    (0, "/memories/empresa/correcoes/a-instancia-e-especifica-mas-a-necessid.xml",
     "duplicata de avaliar-se-o-comando"),
    (0, "/memories/empresa/regras/uma-necessidade-operacional-pode-se-repe.xml",
     "duplicata de avaliar-se-o-comando"),
]


# =====================================================================
# MAIN
# =====================================================================

def main():
    dry_run = '--dry-run' in sys.argv

    from app import create_app, db
    from app.agente.models import AgentMemory
    from app.utils.timezone import agora_utc_naive

    app = create_app()
    with app.app_context():
        print("=" * 70)
        print(f"MIGRAÇÃO DE MEMÓRIAS → CAPDo v3.0 {'(DRY-RUN)' if dry_run else '(PRODUÇÃO)'}")
        print("=" * 70)

        # === 1. Remover duplicatas ===
        print(f"\n🗑️  Fase 1: Remoção de {len(DUPLICATAS_REMOVER)} duplicatas")
        removed = 0
        for user_id, path, motivo in DUPLICATAS_REMOVER:
            mem = AgentMemory.query.filter_by(
                user_id=user_id, path=path, is_directory=False
            ).first()
            if not mem:
                print(f"  ⚠️  {path} já não existe (skip)")
                continue
            print(f"  {'[DRY] ' if dry_run else ''}Removendo ID={mem.id}: {motivo}")
            if not dry_run:
                db.session.delete(mem)
                removed += 1

        if not dry_run and removed > 0:
            db.session.commit()
            print(f"  ✅ {removed} duplicatas removidas")

        # === 2. Migrar empresa (user_id=0) ===
        print("\n📦 Fase 2: Migração de memórias empresa (user_id=0)")
        empresa_mems = AgentMemory.query.filter_by(
            user_id=0, is_directory=False
        ).all()
        print(f"  Total: {len(empresa_mems)} memórias")

        migrated = 0
        skipped = 0
        errors = 0
        already_v3 = 0

        for mem in empresa_mems:
            content = mem.content or ""

            # Detectar formato
            parsed = None
            old_format = None

            if '<conhecimento' in content:
                tipo_attr = _extract_tag_attr(content, 'conhecimento', 'tipo')
                if tipo_attr in ('procedimental', 'conceitual', 'condicional', 'causal', 'relacional'):
                    parsed = _parse_v3_antigo(content)
                    old_format = f'v3-{tipo_attr}'
                else:
                    # Já é v3 com tipo válido — verificar se tem prescricao
                    if '<prescricao>' in content:
                        prescricao = _extract_tag_content(content, 'prescricao')
                        if prescricao and len(prescricao) >= 10:
                            already_v3 += 1
                            continue
                    # v3 sem prescricao — tentar enriquecer
                    parsed = _parse_v3_antigo(content)
                    if not parsed:
                        already_v3 += 1
                        continue
                    old_format = f'v3-sem-prescricao'
            elif '<admin_correction>' in content:
                parsed = _parse_admin_correction(content)
                old_format = 'admin_correction'
            elif '<correcao' in content:
                parsed = _parse_correcao(content)
                old_format = 'correcao'
            elif '<regra' in content:
                parsed = _parse_regra(content)
                old_format = 'regra'
            elif '<termo' in content:
                parsed = _parse_termo(content)
                old_format = 'termo'
            elif '<usuario' in content:
                parsed = _parse_usuario(content)
                old_format = 'usuario'
            else:
                print(f"  ⚠️  ID={mem.id} formato desconhecido: {content[:80]}")
                skipped += 1
                continue

            if not parsed:
                print(f"  ⚠️  ID={mem.id} parse falhou ({old_format}): {mem.path}")
                skipped += 1
                continue

            # Construir novo content e path
            new_content = _build_v3_content(
                tipo=parsed['tipo'],
                nivel=parsed['nivel'],
                dominio=parsed['dominio'],
                titulo=parsed['titulo'],
                descricao=parsed['descricao'],
                prescricao=parsed['prescricao'],
                criterios=parsed['criterios'],
            )
            new_path = _build_v3_path(
                tipo=parsed['tipo'],
                dominio=parsed['dominio'],
                titulo=parsed['titulo'],
                descricao=parsed['descricao'],
            )

            # Verificar colisão de path
            if new_path != mem.path:
                existing = AgentMemory.query.filter_by(
                    user_id=0, path=new_path, is_directory=False
                ).first()
                if existing and existing.id != mem.id:
                    # Path já existe — manter path original
                    print(f"  ⚠️  ID={mem.id} colisão path {new_path} (já ID={existing.id}), mantendo path original")
                    new_path = mem.path

            # Exibir mudança
            path_changed = new_path != mem.path
            print(f"  {'[DRY] ' if dry_run else ''}ID={mem.id} [{old_format}→{parsed['tipo']}]"
                  f"{' PATH→' + new_path if path_changed else ''}")

            if not dry_run:
                mem.content = new_content
                if path_changed:
                    mem.path = new_path
                mem.updated_at = agora_utc_naive()
                migrated += 1

        if not dry_run and migrated > 0:
            db.session.commit()

        # === 3. Resumo ===
        print("\n" + "=" * 70)
        print("📊 RESUMO")
        print("=" * 70)
        print(f"  Duplicatas removidas: {removed}")
        print(f"  Já em v3 (sem alteração): {already_v3}")
        print(f"  Migradas para v3: {migrated if not dry_run else f'(seriam {migrated + skipped - errors})'}")
        print(f"  Skipped (parse falhou): {skipped}")
        print(f"  Erros: {errors}")

        if dry_run:
            print("\n⚠️  DRY-RUN: nenhuma alteração foi feita no banco")
        else:
            remaining = AgentMemory.query.filter_by(user_id=0, is_directory=False).count()
            print(f"\n✅ Memórias empresa restantes: {remaining}")
            v3_count = AgentMemory.query.filter(
                AgentMemory.user_id == 0,
                AgentMemory.is_directory == False,
                AgentMemory.content.like('%<conhecimento%'),
                AgentMemory.content.like('%<prescricao>%'),
            ).count()
            print(f"✅ Em formato v3 com prescricao: {v3_count}/{remaining}")


if __name__ == '__main__':
    main()
