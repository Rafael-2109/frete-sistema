"""
🏗️ STRUCTURE SCANNER - Descoberta de Estrutura
==============================================

Especialista em descobrir estrutura de pastas,
modelos de dados e arquitetura do projeto.

Responsabilidades:
- Descoberta de estrutura de pastas
- Análise de modelos SQLAlchemy
- Mapeamento de relacionamentos
- Inspeção de banco de dados
"""

import os
import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from sqlalchemy import inspect as sql_inspect

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    sql_inspect = None
    SQLALCHEMY_AVAILABLE = False
from app.claude_ai_novo.utils.flask_fallback import get_db

logger = logging.getLogger(__name__)


class StructureScanner:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """
    Especialista em descoberta de estrutura e modelos.
    
    Mapeia a arquitetura completa do projeto e
    descobre todos os modelos de dados dinamicamente.
    """

    def __init__(self, app_path: Path):
        """
        Inicializa o scanner de estrutura.

        Args:
            app_path: Caminho raiz do projeto
        """
        self.app_path = app_path
        logger.info("🏗️ StructureScanner inicializado")

    def discover_project_structure(self) -> Dict[str, Any]:
        """
        Descobre estrutura completa de pastas e arquivos.

        Returns:
            Dict com estrutura organizada
        """
        structure = {}

        try:
            for root, dirs, files in os.walk(self.app_path):
                # Ignorar pastas desnecessárias
                dirs[:] = [d for d in dirs if not d.startswith((".", "__pycache__", "node_modules", "venv"))]

                rel_path = os.path.relpath(root, self.app_path)
                if rel_path == ".":
                    rel_path = "app_root"

                structure[rel_path] = {
                    "directories": dirs.copy(),
                    "python_files": [f for f in files if f.endswith(".py")],
                    "template_files": [f for f in files if f.endswith(".html")],
                    "static_files": [f for f in files if f.endswith((".css", ".js", ".jpg", ".png", ".ico"))],
                    "config_files": [f for f in files if f.endswith((".json", ".yaml", ".yml", ".ini", ".cfg"))],
                    "other_files": [
                        f
                        for f in files
                        if not f.endswith((".py", ".html", ".css", ".js", ".pyc", ".json", ".yaml", ".yml"))
                    ],
                }

            logger.info(f"📁 Estrutura descoberta: {len(structure)} diretórios")
            return structure

        except Exception as e:
            logger.error(f"❌ Erro ao descobrir estrutura: {e}")
            return {}

    def discover_all_models(self) -> Dict[str, Any]:
        """
        Descobre TODOS os modelos do projeto dinamicamente.

        Returns:
            Dict com modelos descobertos
        """
        models = {}

        try:
            # 1. DESCOBRIR VIA SQLALCHEMY METADATA (MAIS CONFIÁVEL)
            models.update(self._discover_models_via_database())

            # 2. DESCOBRIR VIA ARQUIVOS MODELS.PY (COMPLEMENTAR)
            models.update(self._discover_models_via_files())

            logger.info(f"🗃️ Modelos descobertos: {len(models)} encontrados")
            return models

        except Exception as e:
            logger.error(f"❌ Erro ao descobrir modelos: {e}")
            return {}

    def _discover_models_via_database(self) -> Dict[str, Any]:
        """Descobre modelos via inspeção do banco"""
        models = {}

        try:

            inspector = sql_inspect(self.db.engine)
            table_names = inspector.get_table_names()

            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    indexes = inspector.get_indexes(table_name)
                    pk_constraint = inspector.get_pk_constraint(table_name)

                    models[table_name] = {
                        "source": "database_inspection",
                        "table_name": table_name,
                        "columns": [
                            {
                                "name": col["name"],
                                "type": str(col["type"]),
                                "nullable": col["nullable"],
                                "default": str(col.get("default")) if col.get("default") else None,
                                "primary_key": col["name"] in pk_constraint.get("constrained_columns", []),
                            }
                            for col in columns
                        ],
                        "foreign_keys": [
                            {
                                "column": fk["constrained_columns"][0] if fk["constrained_columns"] else None,
                                "referenced_table": fk["referred_table"],
                                "referenced_column": fk["referred_columns"][0] if fk["referred_columns"] else None,
                            }
                            for fk in foreign_keys
                        ],
                        "indexes": [idx["name"] for idx in indexes],
                        "primary_key": pk_constraint.get("constrained_columns", []),
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao inspecionar tabela {table_name}: {e}")

            return models

        except Exception as e:
            logger.error(f"❌ Erro na inspeção do banco: {e}")
            return {}

    def _discover_models_via_files(self) -> Dict[str, Any]:
        """Descobre modelos via análise de arquivos models.py"""
        models = {}

        try:
            for module_dir in self.app_path.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith("."):
                    models_file = module_dir / "models.py"
                    if models_file.exists():
                        models.update(self._parse_models_file(models_file, module_dir.name))

            return models

        except Exception as e:
            logger.error(f"❌ Erro ao descobrir via arquivos: {e}")
            return {}

    def _parse_models_file(self, models_file: Path, module_name: str) -> Dict[str, Any]:
        """
        Parse detalhado de arquivo models.py.

        Args:
            models_file: Caminho para o arquivo
            module_name: Nome do módulo

        Returns:
            Dict com modelos encontrados
        """
        models = {}

        try:
            with open(models_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Verificar se herda de db.Model
                    is_model = self._is_sqlalchemy_model(node)

                    if is_model:
                        model_info = {
                            "source": f"models_file_{module_name}",
                            "file_path": str(models_file),
                            "module": module_name,
                            "class_name": node.name,
                            "fields": [],
                            "relationships": [],
                            "methods": [],
                            "table_name": self._extract_table_name(node),
                        }

                        # Extrair campos e relacionamentos
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                self._parse_model_assignment(item, model_info)
                            elif isinstance(item, ast.FunctionDef):
                                model_info["methods"].append(
                                    {
                                        "name": item.name,
                                        "is_property": any(
                                            isinstance(d, ast.Name) and d.id == "property" for d in item.decorator_list
                                        ),
                                    }
                                )

                        models[f"{module_name}_{node.name}"] = model_info

            return models

        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear {models_file}: {e}")
            return {}

    def _is_sqlalchemy_model(self, class_node: ast.ClassDef) -> bool:
        """Verifica se classe herda de SQLAlchemy Model"""
        for base in class_node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == "Model" and isinstance(base.value, ast.Name) and base.value.id == "db":
                    return True
            elif isinstance(base, ast.Name):
                if base.id in ["Model", "UserMixin"]:
                    return True
        return False

    def _extract_table_name(self, class_node: ast.ClassDef) -> Optional[str]:
        """Extrai nome da tabela definido em __tablename__"""
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            return item.value.value
                        elif isinstance(item.value, ast.Str):  # Python < 3.8
                            return item.value.s
        return None

    def _parse_model_assignment(self, assign_node: ast.Assign, model_info: Dict):
        """Parse de assignment de campo do modelo"""
        for target in assign_node.targets:
            if isinstance(target, ast.Name):
                field_name = target.id
                field_info = self._extract_field_info(assign_node.value)

                if field_info["type"] == "Column":
                    model_info["fields"].append(
                        {
                            "name": field_name,
                            "type": field_info["column_type"],
                            "nullable": field_info.get("nullable", True),
                            "primary_key": field_info.get("primary_key", False),
                            "foreign_key": field_info.get("foreign_key"),
                            "default": field_info.get("default"),
                        }
                    )
                elif field_info["type"] == "relationship":
                    model_info["relationships"].append(
                        {
                            "name": field_name,
                            "target": field_info.get("target"),
                            "back_populates": field_info.get("back_populates"),
                            "foreign_keys": field_info.get("foreign_keys"),
                        }
                    )

    def _extract_field_info(self, value_node) -> Dict[str, Any]:
        """Extrai informações detalhadas do campo"""
        field_info = {"type": "unknown"}

        try:
            if isinstance(value_node, ast.Call):
                if isinstance(value_node.func, ast.Attribute):
                    func_name = value_node.func.attr

                    if func_name == "Column":
                        field_info["type"] = "Column"
                        # Extrair tipo da coluna
                        if value_node.args:
                            first_arg = value_node.args[0]
                            field_info["column_type"] = self._extract_column_type(first_arg)

                        # Extrair argumentos nomeados
                        for keyword in value_node.keywords:
                            if keyword.arg == "nullable":
                                field_info["nullable"] = str(self._extract_boolean_value(keyword.value))
                            elif keyword.arg == "primary_key":
                                field_info["primary_key"] = str(self._extract_boolean_value(keyword.value))
                            elif keyword.arg == "default":
                                field_info["default"] = self._extract_value(keyword.value)

                    elif func_name == "relationship":
                        field_info["type"] = "relationship"
                        # Extrair target do relacionamento
                        if value_node.args:
                            first_arg = value_node.args[0]
                            if isinstance(first_arg, ast.Constant):
                                field_info["target"] = first_arg.value
                            elif isinstance(first_arg, ast.Str):
                                field_info["target"] = first_arg.s

                        # Extrair argumentos nomeados
                        for keyword in value_node.keywords:
                            if keyword.arg == "back_populates":
                                back_populates_value = self._extract_string_value(keyword.value)
                                if back_populates_value is not None:
                                    field_info["back_populates"] = back_populates_value
                            elif keyword.arg == "foreign_keys":
                                foreign_keys_value = self._extract_string_value(keyword.value)
                                if foreign_keys_value is not None:
                                    field_info["foreign_keys"] = foreign_keys_value

                elif isinstance(value_node.func, ast.Name):
                    field_info["type"] = value_node.func.id

        except Exception as e:
            logger.debug(f"Erro ao extrair campo: {e}")

        return field_info

    def _extract_column_type(self, type_node) -> str:
        """Extrai tipo da coluna SQLAlchemy"""
        try:
            if isinstance(type_node, ast.Attribute):
                return f"{type_node.value.id}.{type_node.attr}" if hasattr(type_node.value, "id") else type_node.attr
            elif isinstance(type_node, ast.Name):
                return type_node.id
            elif isinstance(type_node, ast.Call):
                if isinstance(type_node.func, ast.Name):
                    return f"{type_node.func.id}(...)"
        except:
            pass
        return "unknown"

    def _extract_boolean_value(self, value_node) -> bool:
        """Extrai valor booleano de um nó AST"""
        try:
            if isinstance(value_node, ast.Constant):
                return bool(value_node.value)
            elif isinstance(value_node, ast.NameConstant):  # Python < 3.8
                return bool(value_node.value)
        except:
            pass
        return False

    def _extract_string_value(self, value_node) -> Optional[str]:
        """Extrai valor string de um nó AST"""
        try:
            if isinstance(value_node, ast.Constant):
                return str(value_node.value)
            elif isinstance(value_node, ast.Str):  # Python < 3.8
                return value_node.s
        except:
            pass
        return None

    def _extract_value(self, value_node) -> Any:
        """Extrai valor genérico de um nó AST"""
        try:
            if isinstance(value_node, ast.Constant):
                return value_node.value
            elif isinstance(value_node, ast.Str):
                return value_node.s
            elif isinstance(value_node, ast.Num):
                return value_node.n
            elif isinstance(value_node, ast.NameConstant):
                return value_node.value
        except:
            pass
        return None


# Singleton para uso global
_structure_scanner = None


def get_structure_scanner(app_path: Optional[Path] = None) -> StructureScanner:
    """
    Obtém instância do scanner de estrutura.

    Args:
        app_path: Caminho do projeto

    Returns:
        Instância do StructureScanner
    """
    global _structure_scanner
    if _structure_scanner is None or app_path:
        if app_path is None:
            app_path = Path(__file__).parent.parent
        _structure_scanner = StructureScanner(app_path)
    return _structure_scanner
