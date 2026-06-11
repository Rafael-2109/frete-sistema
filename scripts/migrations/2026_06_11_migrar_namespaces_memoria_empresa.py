"""Data-fix T0.4: migrar namespaces legados fora do protocolo para kinds canonicos.

T0.4 F0 arquitetura-conhecimento. Sem DDL — data fix Python only.

Namespaces legados (fora do protocolo protocolos/armadilhas/heuristicas):
  procedimentos -> protocolos
  pitfalls      -> armadilhas
  causas        -> armadilhas
  correcoes     -> armadilhas
  regras        -> heuristicas
  termos        -> heuristicas
  sped_ecd      -> heuristicas (dominio=fiscal forcado)

VERIFICACAO LOAD-BEARING (realizada antes de codar o mapeamento):
Namespaces EXCLUIDOS da migracao — encontrados em uso por prefixo de path no codigo:

  'usuarios'  — EXCLUIDO: app/agente/sdk/memory_injection.py:1309 usa
                path.like('/memories/empresa/usuarios/%') no Tier 1.5 para injecao
                de perfil empresa do usuario. Mover quebraria a injecao silenciosamente.

  'pendencias' — EXCLUIDO: app/agente/sdk/memory_injection.py:238-304 acumula
                pendencias via summary['tarefas_pendentes'] — estrutura separada,
                nao e path /memories/empresa/pendencias/. Mas ha 2 registros PROD
                sob esse prefixo; excluidos por precaucao.

  'perfis'    — EXCLUIDO: nao aparece em hardcode de path, mas nome ambiguo com
                Tier 1.5 usuarios; excluido por precaucao (2 registros PROD).

Colisao (path-alvo ja existe): NAO sobrescreve — marca COLISAO no relatorio
e pula. Revisao manual necessaria.

Rollback: relatorio e mapa de reversao. Versao criada antes de cada UPDATE
via AgentMemoryVersion.save_version. Para reverter manualmente: usar
view_memory_history + restore_memory_version por path afetado, ou consultar
o relatorio gerado.

Uso:
    # dry-run (default, zero writes):
    python scripts/migrations/2026_06_11_migrar_namespaces_memoria_empresa.py

    # aplicar (escreve no banco):
    python scripts/migrations/2026_06_11_migrar_namespaces_memoria_empresa.py --aplicar
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── Mapeamento de namespace legado -> kind canonico ───────────────────────────
# Formato: namespace_legado -> (kind_canonico, dominio_forcado_ou_None)
# dominio_forcado: se nao-None, sobrescreve o dominio do path original.
MAPEAMENTO_NAMESPACES = {
    'procedimentos': ('protocolos', None),
    'pitfalls':      ('armadilhas', None),
    'causas':        ('armadilhas', None),
    'correcoes':     ('armadilhas', None),
    'regras':        ('heuristicas', None),
    'termos':        ('heuristicas', None),
    'sped_ecd':      ('heuristicas', 'fiscal'),  # dominio=fiscal forcado
}

# Namespaces EXCLUIDOS: encontrados em uso por path em codigo critico.
# Nao migrar — registrar como EXCLUIDO no relatorio com razao.
NAMESPACES_EXCLUIDOS = {
    'usuarios': (
        'app/agente/sdk/memory_injection.py:1309 — '
        "path.like('/memories/empresa/usuarios/%') no Tier 1.5 (injecao perfil empresa)"
    ),
    'pendencias': (
        'app/agente/sdk/memory_injection.py:238-304 — '
        'estrutura pendencias acumuladas; excluido por precaucao'
    ),
    'perfis': (
        'nome ambiguo com Tier 1.5 usuarios; excluido por precaucao (2 registros PROD)'
    ),
}

# Dominios validos (enum T0.4) — para validar dominio preservado do path original
_DOMINIOS_VALIDOS = frozenset({
    'financeiro', 'integracao', 'expedicao', 'recebimento', 'estoque',
    'producao', 'fiscal', 'comercial', 'logistica', 'carvia', 'portal', 'geral',
})
_DOMINIO_ALIASES = {'odoo': 'integracao', 'agente': 'geral', 'operacional': 'geral'}


def _normalizar_dominio(dominio: str) -> str:
    """Normaliza dominio para enum valido; fallback 'geral'."""
    d = dominio.strip().lower()
    d = _DOMINIO_ALIASES.get(d, d)
    return d if d in _DOMINIOS_VALIDOS else 'geral'


def _construir_path_novo(path_antigo: str, kind_novo: str, dominio_forcado=None) -> str:
    """Constroi path canonico novo a partir do path legado.

    Extrai slug do filename original e preserva dominio se valido
    (com alias), ou usa 'geral'. Se dominio_forcado, usa esse.

    Formato destino: /memories/empresa/{kind_novo}/{dominio}/{slug}.xml
    """
    # /memories/empresa/{ns}/{dominio?}/{slug}.xml  (3 ou 4 segmentos apos /empresa/)
    after_empresa = path_antigo.replace('/memories/empresa/', '')
    parts = after_empresa.split('/')
    # parts[0] = namespace legado
    # parts[1..] = dominio? + slug.xml   (pode ter 1 ou 2 segmentos restantes)
    remaining = parts[1:]  # tudo apos o namespace

    if len(remaining) == 0:
        return ''  # path invalido

    if dominio_forcado:
        dominio = dominio_forcado
        slug_file = remaining[-1]
    elif len(remaining) >= 2:
        # Tem sub-segmento de dominio: ex: /memories/empresa/regras/financeiro/slug.xml
        dominio = _normalizar_dominio(remaining[0])
        slug_file = remaining[-1]
    else:
        # Sem sub-dominio: ex: /memories/empresa/procedimentos/slug.xml
        dominio = 'geral'
        slug_file = remaining[0]

    if not slug_file:
        return ''

    return f'/memories/empresa/{kind_novo}/{dominio}/{slug_file}'


def executar(aplicar: bool = False, app=None) -> dict:
    """Executa a migracao (ou dry-run). Savepoint-safe: NUNCA commita.

    Faz apenas db.session.flush() — o commit e responsabilidade do caller
    (main() CLI). Isso evita furar o begin_nested() do conftest nos testes
    (gotcha_commit_service_vaza_savepoint).

    Args:
        aplicar: True para escrever (flush) na transacao corrente; False = dry-run.
                 Com aplicar=True, app= e OBRIGATORIO (caller dono do commit).
        app: instancia Flask ja criada (opcional p/ dry-run; se None, cria via
             create_app). Testes passam o app da fixture (app_context ativo).

    Returns:
        Dict com 'relatorio' (lista de entradas) e 'writes' (int).
    """
    from app import db
    from app.agente.models import AgentMemory, AgentMemoryVersion
    from app.utils.timezone import agora_utc_naive

    relatorio = []
    writes = 0

    def _executar_no_contexto():
        nonlocal writes

        # Busca todas as memorias empresa user_id=0 que NAO sao diretorios
        memorias = AgentMemory.query.filter(
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.path.like('/memories/empresa/%'),
        ).all()

        for mem in memorias:
            path = mem.path
            # Extrai namespace: /memories/empresa/{ns}/...
            after_empresa = path.replace('/memories/empresa/', '')
            ns = after_empresa.split('/')[0]

            # ── Namespace excluido ──────────────────────────────────────────
            if ns in NAMESPACES_EXCLUIDOS:
                razao = NAMESPACES_EXCLUIDOS[ns]
                relatorio.append({
                    'path_antigo': path,
                    'path_novo': '',
                    'acao': f'EXCLUIDO — {razao}',
                })
                continue

            # ── Namespace nao legado (ja canonico) ─────────────────────────
            if ns not in MAPEAMENTO_NAMESPACES:
                continue  # ja no formato correto; nao aparece no relatorio

            kind_novo, dominio_forcado = MAPEAMENTO_NAMESPACES[ns]
            path_novo = _construir_path_novo(path, kind_novo, dominio_forcado)

            if not path_novo:
                relatorio.append({
                    'path_antigo': path,
                    'path_novo': '',
                    'acao': 'IGNORADO — path invalido (slug vazio)',
                })
                continue

            # ── Verificar colisao ───────────────────────────────────────────
            existente_no_alvo = AgentMemory.get_by_path(0, path_novo)
            if existente_no_alvo and existente_no_alvo.id != mem.id:
                relatorio.append({
                    'path_antigo': path,
                    'path_novo': path_novo,
                    'acao': 'COLISAO — path-alvo ja existe; revisao manual necessaria',
                })
                continue

            relatorio.append({
                'path_antigo': path,
                'path_novo': path_novo,
                'acao': 'MIGRAR',
            })

            if aplicar:
                # Versionar conteudo atual ANTES de alterar (trilha de rollback)
                if mem.content is not None:
                    AgentMemoryVersion.save_version(
                        memory_id=mem.id,
                        content=mem.content,
                        changed_by='claude',
                    )
                # Atualizar path
                mem.path = path_novo
                mem.updated_at = agora_utc_naive()
                writes += 1

        if aplicar and writes:
            # Savepoint-safe: NUNCA commit aqui (gotcha_commit_service_vaza_savepoint —
            # commit dentro da funcao importavel fura o begin_nested() dos testes e
            # grava dados de teste no banco). flush() materializa os UPDATEs na
            # transacao corrente; o commit e responsabilidade do entry-point CLI
            # (main()), fora do caminho importavel pelos testes.
            db.session.flush()

    # Se app fornecido (testes com app_context ativo ou main() CLI), executar
    # diretamente — o caller e dono do contexto E do commit.
    if app is not None:
        _executar_no_contexto()
    else:
        if aplicar:
            # Guard anti data-loss: sem app gerenciado pelo caller, os writes
            # (apenas flush) seriam descartados ao sair do contexto criado aqui.
            raise RuntimeError(
                'executar(aplicar=True) requer app= com contexto gerenciado pelo '
                'caller, que e responsavel pelo commit. Use main() via CLI.'
            )
        from app import create_app
        _app = create_app()
        with _app.app_context():
            _executar_no_contexto()

    return {'relatorio': relatorio, 'writes': writes}


def _gerar_relatorio_md(relatorio: list, aplicar: bool, writes: int) -> tuple:
    """Gera relatorio em formato Markdown."""
    from app.utils.timezone import agora_utc_naive
    ts = agora_utc_naive().strftime('%Y%m%d_%H%M%S')
    modo = 'APLICADO' if aplicar else 'DRY-RUN'

    linhas = [
        f'# Relatorio Migracao Namespaces Memoria Empresa',
        f'',
        f'**Modo**: {modo}',
        f'**Timestamp**: {ts}',
        f'**Writes**: {writes}',
        f'',
        f'## Entradas',
        f'',
        f'| path_antigo | path_novo | acao |',
        f'|---|---|---|',
    ]
    for entrada in relatorio:
        pa = entrada['path_antigo']
        pn = entrada['path_novo'] or '—'
        ac = entrada['acao']
        linhas.append(f'| `{pa}` | `{pn}` | {ac} |')

    migrar = [r for r in relatorio if r['acao'] == 'MIGRAR']
    colisao = [r for r in relatorio if 'COLISAO' in r['acao']]
    excluido = [r for r in relatorio if 'EXCLUIDO' in r['acao']]

    linhas += [
        f'',
        f'## Resumo',
        f'',
        f'- MIGRAR: {len(migrar)}',
        f'- COLISAO: {len(colisao)}',
        f'- EXCLUIDO: {len(excluido)}',
        f'- WRITES: {writes}',
    ]
    return '\n'.join(linhas), ts


def main():
    aplicar = '--aplicar' in sys.argv

    from app import create_app, db
    _app = create_app()
    with _app.app_context():
        resultado = executar(aplicar=aplicar, app=_app)
        writes_pendentes = resultado['writes']
        if aplicar and writes_pendentes:
            # Commit SOMENTE aqui, no entry-point CLI — fora do caminho
            # importavel pelos testes (gotcha_commit_service_vaza_savepoint).
            db.session.commit()
    relatorio = resultado['relatorio']
    writes = resultado['writes']

    # Exibir resumo no terminal
    migrar = [r for r in relatorio if r['acao'] == 'MIGRAR']
    colisao = [r for r in relatorio if 'COLISAO' in r['acao']]
    excluido = [r for r in relatorio if 'EXCLUIDO' in r['acao']]

    modo = 'APLICADO' if aplicar else 'DRY-RUN'
    print(f'\n[{modo}] Resultado:')
    print(f'  MIGRAR:   {len(migrar)}')
    print(f'  COLISAO:  {len(colisao)} (revisao manual)')
    print(f'  EXCLUIDO: {len(excluido)} (em uso no codigo)')
    print(f'  WRITES:   {writes}')

    for r in relatorio:
        acao = r['acao']
        tag = 'MIGRAR' if acao == 'MIGRAR' else ('COLISAO' if 'COLISAO' in acao else 'EXCLUIDO')
        print(f'  [{tag}] {r["path_antigo"]}')
        if r['path_novo']:
            print(f'         -> {r["path_novo"]}')
        if 'EXCLUIDO' in acao or 'COLISAO' in acao:
            print(f'         razao: {acao}')

    # Gerar relatorio MD
    conteudo_md, ts = _gerar_relatorio_md(relatorio, aplicar, writes)
    relatorio_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f'relatorio_migracao_namespaces_{ts}.md',
    )
    with open(relatorio_path, 'w', encoding='utf-8') as f:
        f.write(conteudo_md)
    print(f'\n[OK] Relatorio salvo em: {relatorio_path}')

    if not aplicar:
        print('\n[INFO] Dry-run: nenhum dado alterado. '
              'Re-rode com --aplicar para executar a migracao.')


if __name__ == '__main__':
    main()
