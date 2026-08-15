# greenlines_brain/dna/ast_analyzer.py
# ============================================================================
# محرك التحليل المعجمي للكود (AST Engine) - الإصدار المُحسَّن
# ============================================================================
# يقرأ ملفات Python ويستخرج الأدلة الخام (Raw Findings) مع الموقع الدقيق.
# ============================================================================

import ast
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..evidence.models import (
    Evidence, Provenance, Source, RawFinding, Claim, AuthorityLevel
)

class ASTAnalyzer:
    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.source_code = source_path.read_text(encoding='utf-8')
        self.tree = ast.parse(self.source_code)
        self.findings: List[RawFinding] = []
        self.evidence_counter = 0

    def _get_node_location(self, node: ast.AST) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """يسترجع الموقع الدقيق للعقدة (بداية السطر، نهاية السطر، بداية العمود، نهاية العمود)."""
        line_start = getattr(node, 'lineno', None)
        col_start = getattr(node, 'col_offset', None)
        line_end = getattr(node, 'end_lineno', None)
        col_end = getattr(node, 'end_col_offset', None)
        
        # إذا لم يكن للعقدة موقع مباشر، نحاول الحصول عليه من العقدة الأصلية
        if line_start is None and hasattr(node, 'parent'):
            parent = node.parent
            if parent:
                line_start = getattr(parent, 'lineno', None)
                col_start = getattr(parent, 'col_offset', None)
                line_end = getattr(parent, 'end_lineno', None)
                col_end = getattr(parent, 'end_col_offset', None)
        
        return line_start, col_start, line_end, col_end

    def _get_source_segment(self, node: ast.AST) -> str:
        """يسترجع النص المصدر للعقدة باستخدام ast.get_source_segment إن أمكن."""
        try:
            return ast.get_source_segment(self.source_code, node) or ast.unparse(node)
        except Exception:
            return repr(node)

    def _create_evidence(self, node: ast.AST, node_type: str) -> Evidence:
        self.evidence_counter += 1
        ev_id = f"ev_{self.evidence_counter:04d}"
        
        line_start, col_start, line_end, col_end = self._get_node_location(node)
        raw_content = self._get_source_segment(node)
        
        source = Source(
            source_type="brain.py",
            uri=str(self.source_path),
            version="1.0"
        )
        provenance = Provenance(
            source=source,
            extracted_by="ASTAnalyzer",
            confidence=0.5
        )
        return Evidence(
            id=ev_id,
            provenance=provenance,
            raw_content=raw_content,
            context={
                "node_type": node_type,
                "line_start": line_start,
                "col_start": col_start,
                "line_end": line_end,
                "col_end": col_end
            },
            line_number=line_start,
            function_name=self._get_current_function(node),
            ast_node_type=node_type
        )

    def _get_current_function(self, node: ast.AST) -> Optional[str]:
        """يبحث عن اسم الدالة المحيطة بالعقدة."""
        parent = node
        while parent:
            if isinstance(parent, ast.FunctionDef):
                return parent.name
            parent = getattr(parent, 'parent', None)
        return None

    def _set_parents(self, node: ast.AST, parent: Optional[ast.AST] = None):
        """يضبط العقدة الأصلية لكل عقدة في الشجرة."""
        node.parent = parent
        for child in ast.iter_child_nodes(node):
            self._set_parents(child, node)

    def _add_finding(self, node: ast.AST, node_type: str, classification: str = "UNCLASSIFIED"):
        evidence = self._create_evidence(node, node_type)
        claim = Claim(
            id=f"cl_{len(self.findings)+1}",
            statement=evidence.raw_content,
            confidence=0.5,
            classification=classification
        )
        finding = RawFinding(
            id=f"rf_{len(self.findings)+1}",
            evidence=evidence,
            claim=claim,
            status="UNCLASSIFIED"
        )
        self.findings.append(finding)

    def analyze(self) -> List[RawFinding]:
        """يحلل الملف المصدر ويستخرج جميع الأدلة الخام."""
        self.findings.clear()
        # إضافة العقدة الأصلية لكل عقدة
        self._set_parents(self.tree, None)
        
        # جولة على كل العقد في الشجرة
        for node in ast.walk(self.tree):
            node_type = node.__class__.__name__
            # تخطي العقد التي ليس لها موقع (مثل القوائم الداخلية)
            if not hasattr(node, 'lineno') and not hasattr(node, 'end_lineno'):
                continue
            self._add_finding(node, node_type)
        return self.findings

    def generate_report(self) -> Dict[str, Any]:
        """يولّد تقريراً مفصلاً عن النتائج."""
        findings = self.analyze()
        report = {
            "source_file": str(self.source_path),
            "total_lines": len(self.source_code.splitlines()),
            "total_findings": len(findings),
            "findings_by_type": {},
            "findings_without_location": 0,
            "findings": []
        }
        for finding in findings:
            node_type = finding.evidence.ast_node_type
            report["findings_by_type"][node_type] = report["findings_by_type"].get(node_type, 0) + 1
            
            # التحقق من وجود موقع
            line = finding.evidence.line_number
            if line is None:
                report["findings_without_location"] += 1
            
            report["findings"].append({
                "id": finding.id,
                "type": node_type,
                "raw": finding.evidence.raw_content[:200],
                "line": line,
                "col": finding.evidence.context.get("col_start"),
                "line_end": finding.evidence.context.get("line_end"),
                "function": finding.evidence.function_name
            })
        return report

    def save_report(self, output_path: Path) -> None:
        """يحفظ التقرير في ملف JSON."""
        import json
        report = self.generate_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"✅ تم حفظ تقرير التحليل في: {output_path}")