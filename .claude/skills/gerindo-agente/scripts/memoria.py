#!/usr/bin/env python3
"""
Dominio 1: Memoria — CRUD + cold + versions + pendencias + pitfalls.

Gerencia memorias persistentes do agente (agent_memories).

Subcomandos:
  view              Ver conteudo de memoria ou listar diretorio
  save              Criar/sobrescrever memoria com auto-categorizacao
  update            str_replace em memoria existente (deve ser match unico)
  delete            Remover memoria (arquivo ou diretorio)
  list              Listar todas as memorias com stats
  clear             Limpar TODAS as memorias (requer --confirm)
  search-cold       Buscar no tier frio
  versions          Historico de versoes de uma memoria
  restore           Restaurar versao anterior (backup do atual)
  resolve-pendencia Marcar pendencia como resolvida
  log-pitfall       Registrar gotcha do sistema
  stats             Estatisticas agregadas de memorias
"""

import json
import sys

# Setup path antes de qualquer import do app
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_datetime, format_json,
    format_table, get_app_context, parse_args_with_subcommands,
    resolve_user, truncate,
)


# =====================================================================
# DEFINICAO DE SUBCOMANDOS
# =====================================================================

SUBCOMMANDS = {
    'view': {
        'help': 'Ver conteudo de memoria ou listar diretorio',
        'args': [
            {'name': '--path', 'default': '/memories', 'help': 'Path da memoria (default: /memories)'},
        ],
    },
    'save': {
        'help': 'Criar/sobrescrever memoria com auto-categorizacao',
        'args': [
            {'name': '--path', 'required': True, 'help': 'Path da memoria'},
            {'name': '--content', 'required': True, 'help': 'Conteudo da memoria'},
            {'name': '--skip-dedup', 'action': 'store_true', 'help': 'Pular verificacao de duplicata'},
        ],
    },
    'update': {
        'help': 'str_replace em memoria existente (match unico)',
        'args': [
            {'name': '--path', 'required': True, 'help': 'Path da memoria'},
            {'name': '--old', 'required': True, 'help': 'Texto a substituir'},
            {'name': '--new', 'required': True, 'help': 'Texto novo'},
        ],
    },
    'delete': {
        'help': 'Remover memoria (arquivo ou diretorio)',
        'args': [
            {'name': '--path', 'required': True, 'help': 'Path da memoria'},
            {'name': '--confirm', 'action': 'store_true', 'help': 'Confirmar exclusao'},
        ],
    },
    'list': {
        'help': 'Listar todas as memorias com stats',
        'args': [
            {'name': '--include-cold', 'action': 'store_true', 'help': 'Incluir memorias do tier frio'},
            {'name': '--category', 'default': None, 'help': 'Filtrar por categoria'},
        ],
    },
    'clear': {
        'help': 'Limpar TODAS as memorias (requer --confirm)',
        'args': [
            {'name': '--confirm', 'action': 'store_true', 'help': 'Confirmar limpeza total'},
        ],
    },
    'search-cold': {
        'help': 'Buscar no tier frio',
        'args': [
            {'name': '--query', 'required': True, 'help': 'Termo de busca'},
        ],
    },
    'versions': {
        'help': 'Historico de versoes de uma memoria',
        'args': [
            {'name': '--path', 'required': True, 'help': 'Path da memoria'},
        ],
    },
    'restore': {
        'help': 'Restaurar versao anterior (backup do atual)',
        'args': [
            {'name': '--path', 'required': True, 'help': 'Path da memoria'},
            {'name': '--version', 'type': int, 'required': True, 'help': 'Numero da versao a restaurar'},
        ],
    },
    'resolve-pendencia': {
        'help': 'Marcar pendencia como resolvida',
        'args': [
            {'name': '--description', 'required': True, 'help': 'Descricao da pendencia resolvida'},
        ],
    },
    'log-pitfall': {
        'help': 'Registrar gotcha/pitfall do sistema',
        'args': [
            {'name': '--area', 'required': True, 'help': 'Area do pitfall (odoo, ssw, banco, api, deploy, sistema)'},
            {'name': '--description', 'required': True, 'help': 'Descricao do pitfall'},
        ],
    },
    'stats': {
        'help': 'Estatisticas agregadas de memorias',
        'args': [],
    },
}


# =====================================================================
# HANDLERS
# =====================================================================

def handle_view(args):
    """Ver conteudo de memoria ou listar diretorio."""
    from app.agente.models import AgentMemory
    from app.agente.tools.memory_mcp_tool import _validate_path

    path = _validate_path(args.path)
    user_id = args.user_id

    mem = AgentMemory.get_by_path(user_id, path)

    if mem and mem.is_directory:
        # Listar conteudo do diretorio
        children = AgentMemory.list_directory(user_id, path)
        if args.json_mode:
            data = [{
                'path': c.path,
                'is_directory': c.is_directory,
                'category': c.category,
                'importance': round(c.importance_score, 2),
                'updated_at': format_datetime(c.updated_at),
            } for c in children]
            print(format_json({'path': path, 'type': 'directory', 'children': data}))
        else:
            if not children:
                print(f"Diretorio {path} esta vazio.")
                return
            print(f"Diretorio: {path} ({len(children)} itens)\n")
            rows = []
            for c in children:
                tipo = 'DIR' if c.is_directory else 'FILE'
                rows.append([
                    tipo,
                    c.path,
                    c.category or '-',
                    str(round(c.importance_score, 2)),
                    format_datetime(c.updated_at),
                ])
            print(format_table(['Tipo', 'Path', 'Categoria', 'Import.', 'Atualizado'], rows))
    elif mem:
        # Mostrar conteudo do arquivo
        if args.json_mode:
            print(format_json({
                'path': mem.path,
                'type': 'file',
                'content': mem.content,
                'category': mem.category,
                'importance_score': round(mem.importance_score, 2),
                'usage_count': mem.usage_count,
                'effective_count': mem.effective_count,
                'correction_count': mem.correction_count,
                'is_cold': mem.is_cold,
                'escopo': mem.escopo,
                'has_potential_conflict': mem.has_potential_conflict,
                'created_at': format_datetime(mem.created_at),
                'updated_at': format_datetime(mem.updated_at),
                'last_accessed_at': format_datetime(mem.last_accessed_at),
            }))
        else:
            print(f"Path: {mem.path}")
            print(f"Categoria: {mem.category} | Importancia: {round(mem.importance_score, 2)}")
            print(f"Uso: {mem.usage_count}x injetada | {mem.effective_count}x efetiva | {mem.correction_count}x corrigida")
            print(f"Cold: {'Sim' if mem.is_cold else 'Nao'} | Escopo: {mem.escopo}")
            if mem.has_potential_conflict:
                print("*** CONFLITO POTENCIAL DETECTADO ***")
            print(f"Criado: {format_datetime(mem.created_at)} | Atualizado: {format_datetime(mem.updated_at)}")
            print(f"\n--- Conteudo ---\n{mem.content}")
    else:
        # Tentar listar como diretorio (path pode nao ter registro proprio)
        children = AgentMemory.list_directory(user_id, path)
        if children:
            if args.json_mode:
                data = [{
                    'path': c.path,
                    'is_directory': c.is_directory,
                    'category': c.category,
                } for c in children]
                print(format_json({'path': path, 'type': 'directory', 'children': data}))
            else:
                print(f"Diretorio: {path} ({len(children)} itens)\n")
                for c in children:
                    tipo = 'DIR' if c.is_directory else 'FILE'
                    print(f"  [{tipo}] {c.path}")
        else:
            error_exit(f"Memoria nao encontrada: {path}")


def handle_save(args):
    """Criar/sobrescrever memoria com auto-categorizacao."""
    from app import db
    from app.agente.models import AgentMemory, AgentMemoryVersion
    from app.agente.tools.memory_mcp_tool import (
        _calculate_importance_score,
        _classify_memory_category,
        _sanitize_content,
        _validate_path,
    )

    path = _validate_path(args.path)
    content = _sanitize_content(args.content)
    user_id = args.user_id

    importance = _calculate_importance_score(path, content)
    category = _classify_memory_category(path, content)

    existing = AgentMemory.get_by_path(user_id, path)
    if existing:
        # Versionar conteudo anterior
        if existing.content:
            AgentMemoryVersion.save_version(
                existing.id, existing.content, changed_by='claude-code'
            )
        existing.content = content
        existing.importance_score = importance
        existing.category = category
        action = 'Atualizado'
    else:
        mem = AgentMemory.create_file(user_id, path, content)
        mem.importance_score = importance
        mem.category = category
        action = 'Criado'

    db.session.commit()

    result = {
        'sucesso': True,
        'acao': action.lower(),
        'path': path,
        'category': category,
        'importance_score': round(importance, 2),
    }

    # ── Paridade com MCP tool: dedup warning + embedding + pitfall hint ──
    # Best-effort: falhas nao bloqueiam o save

    # 1. Dedup check (warning, nao bloqueia)
    if not args.skip_dedup:
        try:
            from app.agente.tools.memory_mcp_tool import _check_memory_duplicate
            dup_path = _check_memory_duplicate(user_id, content, current_path=path)
            if dup_path:
                result['dedup_warning'] = f'Memoria similar encontrada em: {dup_path}'
        except Exception:
            pass  # Embeddings/Voyage nao disponiveis

    # 2. Embedding (best-effort, nao bloqueia)
    try:
        from app.agente.tools.memory_mcp_tool import _embed_memory_best_effort
        _embed_memory_best_effort(user_id, path, content)
    except Exception:
        pass  # Voyage nao disponivel ou outro erro

    # 3. Pitfall hint detection
    try:
        from app.agente.tools.memory_mcp_tool import _detect_pitfall_hint
        hint = _detect_pitfall_hint(path, content)
        if hint:
            result['pitfall_hint'] = True
    except Exception:
        pass

    if args.json_mode:
        print(format_json(result))
    else:
        print(f"{action}: {path} (categoria={category}, importancia={round(importance, 2)})")
        if result.get('dedup_warning'):
            print(f"  AVISO: {result['dedup_warning']}")
        if result.get('pitfall_hint'):
            print(f"  DICA: Parece um pitfall de sistema. Use log-pitfall para registrar.")


def handle_update(args):
    """str_replace em memoria existente."""
    from app import db
    from app.agente.models import AgentMemory, AgentMemoryVersion
    from app.agente.tools.memory_mcp_tool import _validate_path

    path = _validate_path(args.path)
    user_id = args.user_id

    mem = AgentMemory.get_by_path(user_id, path)
    if not mem:
        error_exit(f"Memoria nao encontrada: {path}")

    if not mem.content:
        error_exit(f"Memoria em {path} nao tem conteudo (e diretorio?).")

    # Verificar match unico
    count = mem.content.count(args.old)
    if count == 0:
        error_exit(f"Texto nao encontrado em {path}.")
    if count > 1:
        error_exit(f"Texto encontrado {count} vezes em {path}. Deve ser match unico.")

    # Versionar antes de alterar
    AgentMemoryVersion.save_version(mem.id, mem.content, changed_by='claude-code')

    mem.content = mem.content.replace(args.old, args.new, 1)
    db.session.commit()

    if args.json_mode:
        print(format_json({'sucesso': True, 'path': path, 'acao': 'atualizado'}))
    else:
        print(f"Atualizado: {path}")


def handle_delete(args):
    """Remover memoria."""
    from app import db
    from app.agente.models import AgentMemory
    from app.agente.tools.memory_mcp_tool import _validate_path

    path = _validate_path(args.path)

    if not args.confirm:
        error_exit("Use --confirm para confirmar exclusao.")

    count = AgentMemory.delete_by_path(args.user_id, path)
    db.session.commit()

    if count == 0:
        error_exit(f"Nenhuma memoria encontrada em: {path}")

    if args.json_mode:
        print(format_json({'sucesso': True, 'path': path, 'deletados': count}))
    else:
        print(f"Deletado: {path} ({count} registro(s))")


def handle_list(args):
    """Listar todas as memorias com stats."""
    from app.agente.models import AgentMemory

    query = AgentMemory.query.filter(
        AgentMemory.user_id == args.user_id,
        AgentMemory.is_directory == False,  # noqa: E712
    )

    if not args.include_cold:
        query = query.filter(AgentMemory.is_cold == False)  # noqa: E712

    if args.category:
        query = query.filter(AgentMemory.category == args.category)

    memories = query.order_by(AgentMemory.updated_at.desc()).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'id': m.id,
            'path': m.path,
            'category': m.category,
            'importance_score': round(m.importance_score, 2),
            'usage_count': m.usage_count,
            'effective_count': m.effective_count,
            'correction_count': m.correction_count,
            'is_cold': m.is_cold,
            'escopo': m.escopo,
            'has_potential_conflict': m.has_potential_conflict,
            'content_length': len(m.content) if m.content else 0,
            'updated_at': format_datetime(m.updated_at),
            'last_accessed_at': format_datetime(m.last_accessed_at),
        } for m in memories]
        print(format_json({'total': len(data), 'memorias': data}))
    else:
        if not memories:
            print("Nenhuma memoria encontrada.")
            return

        print(f"Memorias ({len(memories)} encontradas):\n")
        rows = []
        for m in memories:
            flags = []
            if m.is_cold:
                flags.append('COLD')
            if m.has_potential_conflict:
                flags.append('CONFLITO')
            if m.escopo == 'empresa':
                flags.append('EMPRESA')

            rows.append([
                str(m.id),
                m.path,
                m.category or '-',
                str(round(m.importance_score, 2)),
                f"{m.usage_count}/{m.effective_count}",
                ' '.join(flags) if flags else '-',
                format_datetime(m.updated_at),
            ])
        print(format_table(
            ['ID', 'Path', 'Cat.', 'Imp.', 'Uso/Efet.', 'Flags', 'Atualizado'],
            rows
        ))


def handle_clear(args):
    """Limpar TODAS as memorias."""
    from app import db
    from app.agente.models import AgentMemory

    if not args.confirm:
        error_exit("OPERACAO DESTRUTIVA: Use --confirm para limpar TODAS as memorias.")

    count = AgentMemory.clear_all_for_user(args.user_id)
    db.session.commit()

    if args.json_mode:
        print(format_json({'sucesso': True, 'deletados': count}))
    else:
        print(f"Todas as memorias limpas: {count} registro(s) removidos.")


def handle_search_cold(args):
    """Buscar no tier frio."""
    from app.agente.models import AgentMemory

    query_text = f"%{args.query}%"
    results = AgentMemory.query.filter(
        AgentMemory.user_id == args.user_id,
        AgentMemory.is_cold == True,  # noqa: E712
        AgentMemory.content.ilike(query_text),
    ).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'path': r.path,
            'content': truncate(r.content, 200) if r.content else '',
            'category': r.category,
            'usage_count': r.usage_count,
            'effective_count': r.effective_count,
        } for r in results]
        print(format_json({'query': args.query, 'resultados': data}))
    else:
        if not results:
            print(f"Nenhuma memoria fria encontrada para: '{args.query}'")
            return

        print(f"Busca no tier frio por '{args.query}' ({len(results)} resultados):\n")
        for r in results:
            print(f"  [{r.category}] {r.path}")
            print(f"    {truncate(r.content, 100) if r.content else '(vazio)'}")
            print()


def handle_versions(args):
    """Historico de versoes de uma memoria."""
    from app.agente.models import AgentMemory, AgentMemoryVersion
    from app.agente.tools.memory_mcp_tool import _validate_path

    path = _validate_path(args.path)
    mem = AgentMemory.get_by_path(args.user_id, path)
    if not mem:
        error_exit(f"Memoria nao encontrada: {path}")

    versions = AgentMemoryVersion.get_versions(mem.id, limit=args.limit)

    if args.json_mode:
        data = [{
            'version': v.version,
            'changed_by': v.changed_by,
            'changed_at': format_datetime(v.changed_at),
            'content_length': len(v.content) if v.content else 0,
            'content_preview': truncate(v.content, 200) if v.content else '',
        } for v in versions]
        print(format_json({
            'path': path,
            'current_content_preview': truncate(mem.content, 200) if mem.content else '',
            'total_versions': len(data),
            'versions': data,
        }))
    else:
        if not versions:
            print(f"Nenhuma versao anterior para: {path}")
            return

        print(f"Versoes de {path} ({len(versions)} versoes):\n")
        print(f"  [ATUAL] {truncate(mem.content, 100) if mem.content else '(vazio)'}")
        print()
        for v in versions:
            print(f"  [v{v.version}] por {v.changed_by or 'desconhecido'} em {format_datetime(v.changed_at)}")
            print(f"    {truncate(v.content, 100) if v.content else '(vazio)'}")
            print()


def handle_restore(args):
    """Restaurar versao anterior."""
    from app import db
    from app.agente.models import AgentMemory, AgentMemoryVersion
    from app.agente.tools.memory_mcp_tool import _validate_path

    path = _validate_path(args.path)
    mem = AgentMemory.get_by_path(args.user_id, path)
    if not mem:
        error_exit(f"Memoria nao encontrada: {path}")

    target_version = AgentMemoryVersion.get_version(mem.id, args.version)
    if not target_version:
        error_exit(f"Versao {args.version} nao encontrada para: {path}")

    # Backup do conteudo atual antes de restaurar
    if mem.content:
        AgentMemoryVersion.save_version(mem.id, mem.content, changed_by='claude-code-restore')

    mem.content = target_version.content
    db.session.commit()

    if args.json_mode:
        print(format_json({
            'sucesso': True,
            'path': path,
            'restored_version': args.version,
            'content_preview': truncate(target_version.content, 200) if target_version.content else '',
        }))
    else:
        print(f"Restaurado: {path} para versao {args.version}")
        print(f"Conteudo atual salvo como nova versao (backup).")


def handle_resolve_pendencia(args):
    """Marcar pendencia como resolvida."""
    from app import db
    from app.agente.models import AgentMemory

    user_id = args.user_id
    path = '/memories/system/resolved_pendencias.json'

    mem = AgentMemory.get_by_path(user_id, path)
    if mem and mem.content:
        try:
            resolved = json.loads(mem.content)
        except json.JSONDecodeError:
            resolved = []
    else:
        resolved = []

    # Adicionar nova pendencia resolvida (formato: lista de strings,
    # compativel com _load_resolved_pendencias em client.py que filtra isinstance(item, str))
    resolved.append(args.description)

    new_content = json.dumps(resolved, indent=2, ensure_ascii=False)

    if mem:
        mem.content = new_content
    else:
        new_mem = AgentMemory.create_file(user_id, path, new_content)
        new_mem.category = 'operational'
        new_mem.importance_score = 0.3

    db.session.commit()

    if args.json_mode:
        print(format_json({'sucesso': True, 'pendencia': args.description, 'total_resolvidas': len(resolved)}))
    else:
        print(f"Pendencia resolvida: {args.description}")
        print(f"Total de pendencias resolvidas: {len(resolved)}")


def handle_log_pitfall(args):
    """Registrar gotcha/pitfall do sistema."""
    from app import db
    from app.agente.models import AgentMemory
    from app.agente.tools.memory_mcp_tool import _regenerate_pitfalls_xml
    from app.utils.timezone import agora_utc_naive

    user_id = args.user_id
    path = '/memories/system/pitfalls.json'

    mem = AgentMemory.get_by_path(user_id, path)
    if mem and mem.content:
        try:
            pitfalls = json.loads(mem.content)
        except json.JSONDecodeError:
            pitfalls = []
    else:
        pitfalls = []

    # Verificar duplicata
    for p in pitfalls:
        if p.get('description', '').lower() == args.description.lower():
            p['hit_count'] = p.get('hit_count', 1) + 1
            p['last_hit_at'] = agora_utc_naive().isoformat()
            db.session.commit()
            if args.json_mode:
                print(format_json({'sucesso': True, 'acao': 'incrementado', 'hit_count': p['hit_count']}))
            else:
                print(f"Pitfall ja existe. hit_count incrementado para {p['hit_count']}.")
            return

    # Limite de 20 pitfalls
    if len(pitfalls) >= 20:
        error_exit("Limite de 20 pitfalls atingido. Remova pitfalls antigos primeiro.")

    pitfalls.append({
        'area': args.area,
        'description': args.description,
        'hit_count': 1,
        'created_at': agora_utc_naive().isoformat(),
        'last_hit_at': agora_utc_naive().isoformat(),
    })

    new_content = json.dumps(pitfalls, indent=2, ensure_ascii=False)

    if mem:
        mem.content = new_content
    else:
        new_mem = AgentMemory.create_file(user_id, path, new_content)
        new_mem.category = 'structural'
        new_mem.importance_score = 0.9

    # Regenerar XML
    _regenerate_pitfalls_xml(user_id, pitfalls)

    db.session.commit()

    if args.json_mode:
        print(format_json({
            'sucesso': True,
            'acao': 'criado',
            'area': args.area,
            'total_pitfalls': len(pitfalls),
        }))
    else:
        print(f"Pitfall registrado: [{args.area}] {args.description}")
        print(f"Total de pitfalls: {len(pitfalls)}")


def handle_stats(args):
    """Estatisticas agregadas de memorias."""
    from app import db
    from app.agente.models import AgentMemory
    from sqlalchemy import func

    user_id = args.user_id
    base_filter = [
        AgentMemory.user_id == user_id,
        AgentMemory.is_directory == False,  # noqa: E712
    ]

    total = AgentMemory.query.filter(*base_filter).count()
    cold_count = AgentMemory.query.filter(
        *base_filter, AgentMemory.is_cold == True  # noqa: E712
    ).count()
    conflict_count = AgentMemory.query.filter(
        *base_filter, AgentMemory.has_potential_conflict == True  # noqa: E712
    ).count()

    # Por categoria
    cat_counts = db.session.query(
        AgentMemory.category, func.count(AgentMemory.id)
    ).filter(*base_filter).group_by(AgentMemory.category).all()

    # Total chars
    total_chars = db.session.query(
        func.sum(func.length(AgentMemory.content))
    ).filter(*base_filter).scalar() or 0

    # Metricas de uso
    avg_usage = db.session.query(
        func.avg(AgentMemory.usage_count)
    ).filter(*base_filter).scalar() or 0

    avg_effective = db.session.query(
        func.avg(AgentMemory.effective_count)
    ).filter(*base_filter).scalar() or 0

    # Por escopo
    escopo_counts = db.session.query(
        AgentMemory.escopo, func.count(AgentMemory.id)
    ).filter(*base_filter).group_by(AgentMemory.escopo).all()

    stats_data = {
        'total_memorias': total,
        'total_caracteres': int(total_chars),
        'cold': cold_count,
        'conflitos': conflict_count,
        'media_uso': round(float(avg_usage), 1),
        'media_efetividade': round(float(avg_effective), 1),
        'por_categoria': {cat: count for cat, count in cat_counts},
        'por_escopo': {esc: count for esc, count in escopo_counts},
    }

    if args.json_mode:
        print(format_json(stats_data))
    else:
        print(f"Estatisticas de Memorias (user_id={user_id}):\n")
        print(f"  Total: {total} memorias ({int(total_chars)} chars)")
        print(f"  Cold: {cold_count} | Conflitos: {conflict_count}")
        print(f"  Media uso: {round(float(avg_usage), 1)}x | Media efetividade: {round(float(avg_effective), 1)}x")
        print(f"\n  Por categoria:")
        for cat, count in cat_counts:
            print(f"    {cat}: {count}")
        print(f"\n  Por escopo:")
        for esc, count in escopo_counts:
            print(f"    {esc}: {count}")


# =====================================================================
# DISPATCH
# =====================================================================

HANDLERS = {
    'view': handle_view,
    'save': handle_save,
    'update': handle_update,
    'delete': handle_delete,
    'list': handle_list,
    'clear': handle_clear,
    'search-cold': handle_search_cold,
    'versions': handle_versions,
    'restore': handle_restore,
    'resolve-pendencia': handle_resolve_pendencia,
    'log-pitfall': handle_log_pitfall,
    'stats': handle_stats,
}


def main():
    args, subcommand = parse_args_with_subcommands(
        'Gerenciamento de memorias do agente', SUBCOMMANDS
    )

    app, ctx = get_app_context()
    with ctx:
        resolve_user(args.user_id)
        handler = HANDLERS.get(subcommand)
        if handler:
            handler(args)
        else:
            error_exit(f"Subcomando desconhecido: {subcommand}")


if __name__ == '__main__':
    main()
