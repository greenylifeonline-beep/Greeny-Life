# enrich_context.py
# ============================================================================
# Context Enrichment Engine
# ============================================================================
# يضيف لكل RawFinding سياقاً كاملاً: الموقع، المسار، المصدر، معلومات Git،
# ويولد stable_fingerprint لضمان استقرار المعرفات.
# ============================================================================

import ast
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

class ContextEnricher:
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
    
    def _get_stable_fingerprint(self, node: ast.AST) -> str:
        ast_path = ".".join(self._get_ast_path(node))
        node_type = node.__class__.__name__
        normalized = self._get_normalized_source(node)
        content = f"{ast_path}:{node_type}:{normalized}"
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
        
        # استخراج السياق: الدالة، الكلاس، الوحدة
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
        
        # استخراج السياق: الاستيرادات
        imports_context = []
        for node_import in ast.walk(self.tree):
            if isinstance(node_import, ast.Import):
                for alias in node_import.names:
                    imports_context.append(f"import {alias.name}")
            elif isinstance(node_import, ast.ImportFrom):
                imports_context.append(f"from {node_import.module} import {', '.join([a.name for a in node_import.names])}")
        
        # السياق: استدعاءات
        call_context = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_context.append(ast.unparse(child)[:100])
        
        # السياق: التحكم في التدفق
        control_flow_context = []
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                control_flow_context.append(child.__class__.__name__)
        
        return {
            "module": module,
            "class_name": class_name,
            "function_name": function_name,
            "parent_function": function_name,
            "ast_path": self._get_ast_path(node),
            "source_snippet": source_snippet,
            "normalized_source": self._get_normalized_source(node),
            "parent_node_type": parent_node.__class__.__name__ if parent_node else None,
            "imports_context": list(set(imports_context)),
            "call_context": call_context[:5],
            "control_flow_context": list(set(control_flow_context))
        }
    
    def enrich(self) -> Dict[str, Any]:
        # تحميل التقرير الأصلي
        with open(self.report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        enriched_findings = []
        stable_ids = []
        
        # بناء قاموس للعقد حسب الموقع لتحديدها بسرعة
        nodes_by_location = {}
        for node in ast.walk(self.tree):
            if hasattr(node, 'lineno'):
                key = (node.lineno, getattr(node, 'col_offset', 0))
                nodes_by_location[key] = node
        
        for finding in report.get("findings", []):
            line = finding.get("line")
            col = finding.get("col", 0)
            node = None
            if line is not None:
                key = (line, col)
                node = nodes_by_location.get(key)
            
            if node is None:
                # محاولة البحث عن العقدة عبر النص أو النوع
                for n in ast.walk(self.tree):
                    if n.__class__.__name__ == finding.get("type"):
                        try:
                            if ast.unparse(n).strip() == finding.get("raw", "").strip():
                                node = n
                                break
                        except:
                            pass
            
            enriched = finding.copy()
            if node:
                line_start, col_start, line_end, col_end = self._get_node_location(node)
                enriched.update({
                    "line_start": line_start,
                    "col_start": col_start,
                    "line_end": line_end,
                    "col_end": col_end,
                    "stable_fingerprint": self._get_stable_fingerprint(node),
                })
                # إضافة السياق
                context = self._get_context(node)
                enriched.update(context)
                stable_ids.append(enriched["stable_fingerprint"])
            else:
                # إذا لم نجد العقدة، نحاول استخدام المعلومات الموجودة
                enriched.update({
                    "line_start": line,
                    "col_start": col,
                    "line_end": line,
                    "col_end": col,
                    "stable_fingerprint": hashlib.sha256(f"{finding.get('type')}:{finding.get('raw', '')}".encode()).hexdigest()[:16],
                    "module": "brain",
                    "class_name": None,
                    "function_name": None,
                    "ast_path": [],
                    "source_snippet": "",
                    "normalized_source": finding.get("raw", ""),
                    "parent_node_type": None,
                    "imports_context": [],
                    "call_context": [],
                    "control_flow_context": []
                })
            
            enriched_findings.append(enriched)
        
        # إنشاء التقرير المُثرى
        enriched_report = {
            "source_file": str(self.source_path),
            "source_version": self.git_info.get("commit", "unknown"),
            "source_retrieved_at": self.git_info.get("timestamp", datetime.now().isoformat()),
            "total_findings": len(enriched_findings),
            "findings_by_type": {},
            "findings_without_location": 0,
            "stable_id_count": len(set(stable_ids)),
            "findings": enriched_findings
        }
        
        # إحصائيات
        for f in enriched_findings:
            node_type = f.get("type", "unknown")
            enriched_report["findings_by_type"][node_type] = enriched_report["findings_by_type"].get(node_type, 0) + 1
            if f.get("line_start") is None:
                enriched_report["findings_without_location"] += 1
        
        return enriched_report

def main():
    source_path = Path("brain.py")
    report_path = Path("intelligence/ast_raw_findings_report.json")
    
    if not report_path.exists():
        print("❌ تقرير AST غير موجود. قم بتشغيل standalone_ast_analysis.py أولاً.")
        return
    
    print("🧠 بدء إثراء السياق...")
    enricher = ContextEnricher(source_path, report_path)
    enriched = enricher.enrich()
    
    output_path = Path("intelligence/ast_enriched_findings.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    
    print(f"✅ تم حفظ التقرير المُثرى في: {output_path}")
    print(f"📊 إجمالي النتائج: {enriched['total_findings']}")
    print(f"🔍 بدون موقع: {enriched['findings_without_location']}")
    print(f"🆔 معرفات مستقرة: {enriched['stable_id_count']}")

if __name__ == "__main__":
    main()
