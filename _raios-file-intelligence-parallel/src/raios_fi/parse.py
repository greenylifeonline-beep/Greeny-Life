"""Code structure. Python ast first. Tree-sitter/ctags if present. Qwen is not used for symbols."""
from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .adapters import is_ast_grep, is_universal_ctags
from .config import deterministic_id, which
from .spi import BaseProvider
from .store import IndexStore
from .types import classify_file


@dataclass(frozen=True)
class SymbolObject:
    symbol_id: str
    file_id: str
    kind: str
    name: str
    qualified_name: str
    line: int
    state: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParseResult:
    language: str | None
    parser: str
    symbols: list[SymbolObject] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: str = ""
    qwen_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.symbols]
        return payload


class CodeParserProvider(BaseProvider):
    name = "code-parser"
    capability = "parse"
    per_file_cost = 0.08
    accuracy = 0.9
    supported_types = ("CODE",)

    def health(self) -> dict[str, Any]:
        tree_sitter = bool(which("tree-sitter"))
        uctags = is_universal_ctags()
        ast_grep = is_ast_grep()
        return {
            "ok": True,
            "tree_sitter": tree_sitter,
            "universal_ctags": uctags,
            "ast_grep": ast_grep,
            "python_ast": True,
            "qwen_used": False,
            "fallback": None if tree_sitter else "python-ast + heuristic-ts/ps1/sql",
            "gnu_emacs_ctags_rejected": (not uctags) and bool(which("ctags")),
        }

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        parsed = parse_file(path, file_id=obj.get("file_id") or "anon")
        return {
            "symbols": [s.to_dict() for s in parsed.symbols],
            "parser": parsed.parser,
            "qwen": parsed.qwen_used,
            "imports": parsed.imports,
            "routes": parsed.routes,
        }


class SymbolProvider(CodeParserProvider):
    name = "symbols"
    capability = "symbols"


def parse_file(path: Path, file_id: str | None = None, store: IndexStore | None = None) -> ParseResult:
    typed = classify_file(path)
    fid = file_id or str(path)
    digest = None
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        digest = None
    if store is not None and digest:
        cached = store.cache_get(digest)
        if cached and cached.get("kind") == "parse":
            return _parse_from_cache(cached)
    lang = typed.language
    if lang == "python" or path.suffix.lower() == ".py" or typed.detector.startswith("parser-probe-python"):
        result = _python_parse(path, fid)
    elif lang in {"typescript", "tsx", "javascript"} or path.suffix.lower() in {".ts", ".tsx", ".js"}:
        result = _js_parse(path, fid, lang or "javascript")
    elif lang == "powershell" or path.suffix.lower() == ".ps1":
        result = _ps_parse(path, fid)
    elif lang == "sql" or path.suffix.lower() == ".sql":
        result = _sql_parse(path, fid)
    else:
        result = ParseResult(
            language=lang,
            parser="unavailable",
            confidence=0.0,
            evidence="no_deterministic_parser",
            qwen_used=False,
        )
    if store is not None and digest:
        store.cache_put(digest, {"kind": "parse", **result.to_dict()})
    return result


def _parse_from_cache(cached: dict[str, Any]) -> ParseResult:
    symbols = []
    for item in cached.get("symbols") or []:
        if isinstance(item, dict) and "symbol_id" in item:
            symbols.append(
                SymbolObject(
                    symbol_id=item["symbol_id"],
                    file_id=item["file_id"],
                    kind=item["kind"],
                    name=item["name"],
                    qualified_name=item.get("qualified_name") or item["name"],
                    line=int(item.get("line") or 0),
                    state=item.get("state") or "PROVEN",
                    confidence=float(item.get("confidence") or 0),
                )
            )
    return ParseResult(
        language=cached.get("language"),
        parser=cached.get("parser") or "cache",
        symbols=symbols,
        imports=list(cached.get("imports") or []),
        exports=list(cached.get("exports") or []),
        routes=list(cached.get("routes") or []),
        confidence=float(cached.get("confidence") or 0),
        evidence="parser_cache",
        qwen_used=False,
    )


def _python_parse(path: Path, file_id: str) -> ParseResult:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ParseResult(
            language="python",
            parser="python-ast-failed",
            evidence=f"{type(exc).__name__}:{exc.lineno}",
            confidence=0.2,
            qwen_used=False,
        )
    except (UnicodeError, OSError) as exc:
        return ParseResult(
            language="python",
            parser="python-ast-failed",
            evidence=type(exc).__name__,
            confidence=0.1,
            qwen_used=False,
        )
    symbols: list[SymbolObject] = []
    imports: list[str] = []
    class_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            class_stack.append(node.name)
            symbols.append(_sym(file_id, "class", node.name, ".".join(class_stack), getattr(node, "lineno", 0)))
            self.generic_visit(node)
            class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            qn = ".".join([*class_stack, node.name])
            kind = "method" if class_stack else "function"
            symbols.append(_sym(file_id, kind, node.name, qn, getattr(node, "lineno", 0)))

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            qn = ".".join([*class_stack, node.name])
            kind = "method" if class_stack else "function"
            symbols.append(_sym(file_id, kind, node.name, qn, getattr(node, "lineno", 0)))

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                imports.append(alias.name)
                symbols.append(_sym(file_id, "import", alias.name, alias.name, getattr(node, "lineno", 0)))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            mod = node.module or "."
            imports.append(mod)
            symbols.append(_sym(file_id, "import", mod, mod, getattr(node, "lineno", 0)))

    Visitor().visit(tree)
    return ParseResult(
        language="python",
        parser="python-ast",
        symbols=symbols,
        imports=imports,
        confidence=0.95,
        evidence="ast.parse",
        qwen_used=False,
    )


def _js_parse(path: Path, file_id: str, lang: str) -> ParseResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    symbols: list[SymbolObject] = []
    imports: list[str] = []
    exports: list[str] = []
    routes: list[str] = []
    for rx, kind in (
        (r"export\s+(?:async\s+)?function\s+(\w+)", "function"),
        (r"function\s+(\w+)\s*\(", "function"),
        (r"class\s+(\w+)", "class"),
        (r"interface\s+(\w+)", "interface"),
        (r"type\s+(\w+)\s*=", "type"),
        (r"from ['\"]([^'\"]+)['\"]", "import"),
        (r"export\s+(?:default\s+)?(?:function|class|const)\s+(\w+)", "export"),
        (r"app\.(get|post|put|delete)\(['\"]([^'\"]+)", "route"),
        (r"(?:export\s+)?async\s+function\s+(GET|POST|PUT|DELETE|PATCH)\b", "route"),
    ):
        for match in re.finditer(rx, text):
            name = match.group(match.lastindex or 1)
            line = text[: match.start()].count("\n") + 1
            symbols.append(_sym(file_id, kind, name, name, line))
            if kind == "import":
                imports.append(name)
            elif kind == "export":
                exports.append(name)
            elif kind == "route":
                routes.append(name)
    return ParseResult(
        language=lang,
        parser="heuristic-ts",
        symbols=symbols,
        imports=imports,
        exports=exports,
        routes=routes,
        confidence=0.55,
        evidence="regex-heuristic;tree-sitter-missing",
        qwen_used=False,
    )


def _ps_parse(path: Path, file_id: str) -> ParseResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    symbols = []
    for match in re.finditer(r"function\s+([A-Za-z][\w-]*)", text):
        symbols.append(_sym(file_id, "function", match.group(1), match.group(1), text[: match.start()].count("\n") + 1))
    return ParseResult(
        language="powershell",
        parser="heuristic-ps1",
        symbols=symbols,
        confidence=0.5,
        evidence="regex-heuristic",
        qwen_used=False,
    )


def _sql_parse(path: Path, file_id: str) -> ParseResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    symbols = []
    for match in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.]+)", text, re.I):
        symbols.append(_sym(file_id, "table", match.group(1), match.group(1), text[: match.start()].count("\n") + 1))
    return ParseResult(
        language="sql",
        parser="heuristic-sql",
        symbols=symbols,
        confidence=0.6,
        evidence="regex-create-table",
        qwen_used=False,
    )


def _sym(file_id: str, kind: str, name: str, qualified: str, line: int) -> SymbolObject:
    return SymbolObject(
        symbol_id=deterministic_id("sym", file_id, kind, name, str(line)),
        file_id=file_id,
        kind=kind,
        name=name,
        qualified_name=qualified,
        line=line,
        state="PROVEN",
        confidence=0.9,
    )
