# enrich_context_fixed.py
# ============================================================================
# Context Enrichment Engine v2 - مع Stable Identity محسّن
# ============================================================================

import ast
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

class ContextEnricherV2:
    def __init__(self, source_path: Path, report_path: Path):
        self.source_path = source_path
        self.report_path = report_path
        self.source_code = source_path.read_text(encoding='utf-8')
        self.tree = ast.parse(self.source_code)
        self.git_info = self._get_git_info()
        
    def _get_git_info(self) -> Dict[str, str]:
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.source_path.parent).decode().strip()
            timestamp = subprocess.check_output(['git', 'log', '-1', '--format=%ci'], cwd=self.source_path.parent).decode().strip()
            return {'commit': commit, 'timestamp': timestamp}
        except:
            return {'commit': 'unknown', 'timestamp': datetime.now().isoformat()}
    
    def _get_ast_path(self, node: ast.AST) -> List[str]:
        path = []
        parent = node
        while parent:
            if isinstance(parent, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                path.append(parent.__class__.__name__ + (f":{parent.name}" if hasattr(parent, 'name') else ''))
            parent = getattr(parent, 'parent', None)
        return list(reversed(path))
    
    def _get_normalized_source(self, node: ast.AST) -> str:
        try:
            return ast.unparse(node).strip()
        except:
            return repr(node)
    
    def _get_stable_fingerprint(self, node: ast.AST, context: Dict[str, Any]) -> str:
        # بناء معرف مستقر يعتمد على المسار المعجمي + النوع + المصدر المطبع + السياق
        ast_path = ".".join(self._get_ast_path(node))
        node_type = node.__class__.__name__
        normalized = self._get_normalized_source(node)
        
        # إضافة السياق إذا كان متاحاً
        function_name = context.get("function_name", "")
        class_name = context.get("class_name", "")
        module = context.get("module", "brain")
        
        content = f"{module}:{class_name}:{function_name}:{ast_path}:{node_type}:{normalized}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_node_location(self, node: ast.AST) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        return (
            getattr(node, 'lineno', None),
            getattr(node, 'col_offset', None),
            getattr(node, 'end_lineno', None),
            getattr(node, 'end_col_offset', None)
        )
    
    def _get_context(self, node: ast.AST) -> Dict[str, Any]:
        line_start, col_start, line_end, col_end = self._get_node_location(node)
        
        module = "brain"
        class_name = None
        function_name = None
        parent_node = getattr(node, 'parent', None)
        if parent_node:
            if isinstance(parent_node, ast.ClassDef):
                class_name = parent_node.name
            elif isinstance(parent_node, ast.FunctionDef):
                function_name = parent_node.name
            elif isinstance(parent_node, ast.Module):
                module = "brain"
        
        # استخراج المصدر
        source_snippet = ""
        if line_start and line_end:
            lines = self.source_code.splitlines()
            if line_start <= len(lines):
                start_idx = max(0, line_start - 1)
                end_idx = min(len(lines), line_end if line_end else line_start)
                source_snippet = "\n".join(lines[start_idx:end_idx])
        
        return {
            "module": module,
            "class_name": class_name,
            "function_name": function_name,
            "parent_function": function_name,
            "ast_path": self._get_ast_path(node),
            "source_snippet": source_snippet,
            "normalized_source": self._get_normalized_source(node),
            "parent_node_type": parent_node.__class__.__name__ if parent_node else None
        }
    
    def enrich(self) -> Dict[str, Any]:
        with open(self.report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        # بناء قاموس العقد حسب الموقع
        nodes_by_location = {}
        for node in ast.walk(self.tree):
            if hasattr(node, 'lineno'):
                key = (node.lineno, getattr(node, 'col_offset', 0))
                nodes_by_location[key] = node
        
        enriched_findings = []
        stable_ids = set()
        
        # أنواع العقد التي لا تحمل موقعاً بطبيعتها
        inherently_unlocated_types = {
            'Load', 'Store', 'Add', 'Sub', 'Mult', 'Div', 'Mod', 'BitAnd', 'BitOr', 
            'BitXor', 'LShift', 'RShift', 'And', 'Or', 'Not', 'Eq', 'NotEq', 'Lt', 
            'LtE', 'Gt', 'GtE', 'Is', 'IsNot', 'In', 'NotIn', 'USub', 'UAdd'
        }
        
        for finding in report.get("findings", []):
            line = finding.get("line")
            col = finding.get("col", 0)
            node = None
            
            # محاولة العثور على العقدة
            if line is not None:
                key = (line, col)
                node = nodes_by_location.get(key)
            
            # إذا لم نجد العقدة، نحاول البحث بالنص
            if node is None:
                for n in ast.walk(self.tree):
                    if n.__class__.__name__ == finding.get("type"):
                        try:
                            if ast.unparse(n).strip() == finding.get("raw", "").strip():
                                node = n
                                break
                        except:
                            pass
            
            enriched = finding.copy()
            node_type = finding.get("type", "")
            
            if node:
                line_start, col_start, line_end, col_end = self._get_node_location(node)
                context = self._get_context(node)
                stable_fp = self._get_stable_fingerprint(node, context)
                
                enriched.update({
                    "line_start": line_start,
                    "col_start": col_start,
                    "line_end": line_end,
                    "col_end": col_end,
                    "stable_fingerprint": stable_fp,
                    "inherited_location": line_start is None and col_start is None,
                    "inherently_unlocated": node_type in inherently_unlocated_types,
                    "module": context["module"],
                    "class_name": context["class_name"],
                    "function_name": context["function_name"],
                    "ast_path": context["ast_path"],
                    "source_snippet": context["source_snippet"],
                    "normalized_source": context["normalized_source"],
                    "parent_node_type": context["parent_node_type"]
                })
                stable_ids.add(stable_fp)
            else:
                # إذا لم نجد العقدة، نستخدم البيانات الموجودة مع تنبيه
                enriched.update({
                    "line_start": line,
                    "col_start": col,
                    "line_end": line,
                    "col_end": col,
                    "stable_fingerprint": None,
                    "inherited_location": False,
                    "inherently_unlocated": False,
                    "module": "brain",
                    "class_name": None,
                    "function_name": None,
                    "ast_path": [],
                    "source_snippet": "",
                    "normalized_source": finding.get("raw", ""),
                    "parent_node_type": None
                })
            
            enriched_findings.append(enriched)
        
        enriched_report = {
            "source_file": str(self.source_path),
            "source_version": self.git_info.get("commit", "unknown"),
            "source_retrieved_at": self.git_info.get("timestamp", datetime.now().isoformat()),
            "total_findings": len(enriched_findings),
            "findings_without_location": sum(1 for f in enriched_findings if f.get("line_start") is None and not f.get("inherently_unlocated")),
            "stable_id_count": len(stable_ids),
            "findings": enriched_findings
        }
        
        return enriched_report

def main():
    source_path = Path("brain.py")
    report_path = Path("intelligence/ast_raw_findings_report.json")
    
    if not report_path.exists():
        print("❌ تقرير AST غير موجود.")
        return
    
    print("🧠 بدء إثراء السياق v2...")
    enricher = ContextEnricherV2(source_path, report_path)
    enriched = enricher.enrich()
    
    output_path = Path("intelligence/ast_enriched_findings_v2.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    
    print(f"✅ تم حفظ التقرير المُثرى v2 في: {output_path}")
    print(f"📊 إجمالي النتائج: {enriched['total_findings']}")
    print(f"🔍 بدون موقع (فعلي): {enriched['findings_without_location']}")
    print(f"🆔 معرفات مستقرة: {enriched['stable_id_count']}")

if __name__ == "__main__":
    main()
