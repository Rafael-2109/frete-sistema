from __future__ import annotations
import re
from . import meta as meta_mod


def _glob_to_regex(glob: str) -> re.Pattern:
    """Translate a glob pattern with ** semantics to a compiled regex.

    PurePath.match on Python 3.12 treats ** as a single-level wildcard (*),
    so it cannot match deep subpaths like docs/a/b/c/x.md against docs/**/*.md.
    This implementation walks the glob character by character and emits regex
    tokens with correct ** semantics:
      - `**/`  -> zero or more path components (prefix/ or nothing)
      - `**`   -> anything (terminal)
      - `*`    -> any characters except /
      - `?`    -> any single character except /
      - rest   -> re.escape'd literal
    """
    result = []
    i = 0
    while i < len(glob):
        if glob[i:i+3] == "**/":
            # Zero or more path components: matches "" or "something/"
            result.append("(?:.+/)?")
            i += 3
        elif glob[i:i+2] == "**":
            # Terminal **: matches anything (rest of path)
            result.append(".*")
            i += 2
        elif glob[i] == "*":
            # Single *: matches anything except path separator
            result.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            result.append("[^/]")
            i += 1
        else:
            result.append(re.escape(glob[i]))
            i += 1
    pattern = "".join(result)
    return re.compile(r"\A" + pattern + r"\Z")


def _match_any(path: str, globs) -> bool:
    """Return True if path matches any of the given glob patterns.

    Uses a **-aware regex matcher so that docs/**/*.md correctly matches
    docs/x.md, docs/a/b.md, docs/a/b/c/x.md etc. on Python 3.12.
    """
    # Normalize path separators to forward slash for consistent matching
    normalized = path.replace("\\\\", "/")
    for g in globs:
        pattern = _glob_to_regex(g)
        if pattern.match(normalized):
            return True
    return False


def is_ignored(path: str, cfg) -> bool:
    return _match_any(path, cfg.ignore_globs)


def is_managed_doc(path: str, cfg) -> bool:
    if is_ignored(path, cfg):
        return False
    return _match_any(path, cfg.managed_doc_globs)


def is_operational_script(path: str, cfg) -> bool:
    if is_ignored(path, cfg):
        return False
    return _match_any(path, cfg.operational_script_globs)


def is_scratch(content: str) -> bool:
    m = meta_mod.parse_doc(content)
    return m.fields.get("tipo") == "scratch"
