## Build & Run

- Ativar ambiente: `source .venv/bin/activate`
- Rodar servidor: `flask run --debug`
- Rodar com gunicorn: `gunicorn -w 4 -b 0.0.0.0:5000 run:app`

## Validation

Run these after implementing to get immediate feedback:

- Tests: `pytest app/tests/ -v`
- Typecheck: `pyright app/`
- Lint: `ruff check app/`

## Operational Notes

- SEMPRE consultar CLAUDE.md para nomes de campos
- Formato numérico brasileiro: usar filtros `valor_br` e `numero_br`
- Toda tela DEVE ter link no menu (base.html)

### Codebase Patterns

- Models em `app/<modulo>/models.py`
- Routes em `app/<modulo>/routes/`
- Services em `app/<modulo>/services/`
- Templates em `app/templates/<modulo>/`
