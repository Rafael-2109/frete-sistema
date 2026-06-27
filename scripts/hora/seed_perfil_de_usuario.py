"""Alimenta o ESQUELETO de um perfil HORA a partir da matriz efetiva de um usuario.

CONTEXTO
--------
Um perfil HORA (`hora_perfil` + `hora_perfil_permissao`, CLAUDE.md secao 28) e um
TEMPLATE de permissoes: ao ser atribuido a um usuario, PRE-PREENCHE
`hora_user_permissao` (a fonte de verdade efetiva). O esqueleto nasce VAZIO em
`criar_perfil` — o admin teria de marcar manualmente a matriz modulo x acao na tela
`/hora/permissoes/perfis/<id>`.

Este script captura a configuracao ja validada de um VENDEDOR REAL (ex.: Isabela,
`usuarios.id=84`, cujas permissoes granulares foram afinadas em producao) e a grava
como esqueleto do perfil — assim novos vendedores recebem exatamente o mesmo conjunto
ao serem atribuidos ao perfil.

O QUE FAZ (e o que NAO faz)
---------------------------
- LE a matriz EFETIVA do usuario-fonte via `permissao_service.get_matriz` (todos os
  MODULOS_HORA; modulo sem entry vem False).
- GRAVA essa matriz no esqueleto do perfil-alvo via `perfil_service.salvar_skeleton`
  (upsert de TODOS os modulos — cria linha faltante; zera modulo que o usuario nao tem).
- NAO toca em `hora_user_permissao` de ninguem (nao re-aplica o perfil a usuarios ja
  atribuidos — isso e acao separada, `redefinir_permissoes_pelo_perfil` / tela).
- NAO altera `Usuario.perfil` de ninguem.

E so um snapshot fiel: o perfil-alvo passa a refletir exatamente as flags do
usuario-fonte no momento da execucao.

USO
---
    # Dry-run contra PROD (NAO escreve) — fonte Isabela, alvo hora_vendedor (defaults):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/seed_perfil_de_usuario.py

    # Executar contra PROD:
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/seed_perfil_de_usuario.py --confirmar

    # Outro par fonte/alvo:
    ... seed_perfil_de_usuario.py --user-email fulano@x.com --perfil-slug hora_gerente --confirmar
    ... seed_perfil_de_usuario.py --user-id 99 --perfil-slug hora_vendedor
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402
from app.auth.models import Usuario  # noqa: E402
from app.hora.models import ACOES_HORA, MODULOS_HORA  # noqa: E402
from app.hora.services import perfil_service, permissao_service  # noqa: E402

# Defaults desta tarefa (2026-06-27): Isabela -> perfil "vendedor" das Lojas HORA.
DEFAULT_USER_EMAIL = 'isabela@motochefesp.com.br'
DEFAULT_PERFIL_SLUG = 'hora_vendedor'

_ACOES = [a for a, _ in ACOES_HORA]
# Letra por acao (espelha HoraUserPermissao.__repr__: apagar=A, aprovar=P — sem ambiguidade).
_LETRA = {'ver': 'V', 'criar': 'C', 'editar': 'E', 'apagar': 'A', 'aprovar': 'P'}


def _resolver_usuario(user_id: int | None, user_email: str | None) -> Usuario:
    if user_id is not None:
        u = Usuario.query.get(user_id)
        if u is None:
            raise SystemExit(f'ERRO: usuario id={user_id} nao encontrado.')
        return u
    u = Usuario.query.filter(Usuario.email == user_email).first()
    if u is None:
        raise SystemExit(f'ERRO: usuario email={user_email!r} nao encontrado.')
    return u


def _flags_str(flags: dict[str, bool]) -> str:
    return ''.join(_LETRA[a] if flags.get(a) else '-' for a in _ACOES)  # VCEAP


def main():
    parser = argparse.ArgumentParser(
        description='Alimenta o esqueleto de um perfil HORA com a matriz efetiva de um usuario.',
    )
    parser.add_argument('--user-id', type=int, default=None,
                        help='id do usuario-fonte (tem prioridade sobre --user-email)')
    parser.add_argument('--user-email', default=DEFAULT_USER_EMAIL,
                        help=f'email do usuario-fonte (default: {DEFAULT_USER_EMAIL})')
    parser.add_argument('--perfil-slug', default=DEFAULT_PERFIL_SLUG,
                        help=f'slug do perfil-alvo (default: {DEFAULT_PERFIL_SLUG})')
    parser.add_argument('--confirmar', action='store_true',
                        help='executa de fato (sem essa flag, so dry-run)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        usuario = _resolver_usuario(args.user_id, args.user_email)
        perfil = perfil_service.get_perfil_por_slug(args.perfil_slug)
        if perfil is None:
            raise SystemExit(f'ERRO: perfil slug={args.perfil_slug!r} nao encontrado.')

        matriz_nova = permissao_service.get_matriz(usuario.id)   # fonte: efetiva do usuario
        matriz_atual = perfil_service.get_skeleton(perfil.id)    # alvo: esqueleto atual

        print('=' * 78)
        print('SEED PERFIL HORA — copia matriz efetiva do usuario -> esqueleto do perfil')
        print('=' * 78)
        print(f'Fonte : usuario #{usuario.id}  {usuario.nome}  <{usuario.email}>  '
              f'(perfil_sistema={usuario.perfil!r}, sistema_lojas={usuario.sistema_lojas})')
        print(f'Alvo  : perfil  #{perfil.id}  slug={perfil.slug!r}  nome={perfil.nome!r}  '
              f'ativo={perfil.ativo}')
        print(f'Legenda flags: {"".join(_LETRA[a] for a in _ACOES)} = '
              f'{" / ".join(a.capitalize() for a in _ACOES)}')
        print('-' * 78)
        print(f'{"modulo":<24} {"atual":<7} {"novo":<7}  mudanca')
        print('-' * 78)

        n_mod_com_flag = 0
        n_mod_mudou = 0
        for modulo, _ in MODULOS_HORA:
            atual = matriz_atual.get(modulo, {})
            nova = matriz_nova.get(modulo, {})
            s_atual = _flags_str(atual)
            s_nova = _flags_str(nova)
            if any(nova.get(a) for a in _ACOES):
                n_mod_com_flag += 1
            mudou = s_atual != s_nova
            if mudou:
                n_mod_mudou += 1
            marca = '  <- muda' if mudou else ''
            # so imprime linha que tem alguma flag (atual ou nova) p/ enxugar
            if s_atual != '-----' or s_nova != '-----':
                print(f'{modulo:<24} {s_atual:<7} {s_nova:<7}{marca}')

        print('-' * 78)
        print(f'Modulos com ao menos 1 flag no NOVO esqueleto: {n_mod_com_flag}')
        print(f'Modulos que mudam vs esqueleto atual: {n_mod_mudou}')
        print()

        if n_mod_mudou == 0:
            print('Esqueleto ja identico a matriz da fonte — nada a fazer (idempotente).')
            return

        if not args.confirmar:
            print('*** DRY-RUN — nenhuma alteracao foi feita. Use --confirmar para gravar. ***')
            return

        print('*** EXECUTANDO COM --confirmar ***')
        salvos = perfil_service.salvar_skeleton(perfil.id, matriz_nova)
        print(f'  {salvos} modulo(s) persistido(s) no esqueleto do perfil '
              f'{perfil.slug!r} (#{perfil.id}).')

        # Verificacao pos.
        depois = perfil_service.get_skeleton(perfil.id)
        divergentes = [
            m for m, _ in MODULOS_HORA
            if _flags_str(depois.get(m, {})) != _flags_str(matriz_nova.get(m, {}))
        ]
        print()
        if divergentes:
            print(f'  !! ATENCAO: {len(divergentes)} modulo(s) ainda divergem: {divergentes}')
        else:
            print('  OK — esqueleto do perfil agora reflete fielmente a matriz da fonte.')


if __name__ == '__main__':
    main()
