# greenlines_brain/dna/extractor.py
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class DNAExtractor:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.source_code = brain_path.read_text(encoding='utf-8')
    
    def extract_knowledge(self) -> Dict[str, Any]:
        """يستخرج المعرفة من brain.py مع تصنيفها ومصدرها."""
        knowledge = {
            "source_file": str(self.brain_path),
            "entities": [],
            "relationships": [],
            "business_rules": [],
            "master_data": [],
            "capabilities": [],
            "workflows": [],
            "evidence": []
        }
        
        # ====================================================================
        # 1. استخراج الكيانات (من التعليقات والأسماء)
        # ====================================================================
        entity_keywords = ['Product', 'Supplier', 'Customer', 'Order', 'Certificate', 
                          'Shipment', 'Invoice', 'User', 'Role', 'Permission']
        for keyword in entity_keywords:
            if keyword in self.source_code:
                knowledge["entities"].append({
                    "name": keyword,
                    "type": "ENTITY",
                    "source_file": str(self.brain_path),
                    "confidence": "HIGH",
                    "legacy_origin": str(self.brain_path)
                })
        
        # ====================================================================
        # 2. استخراج البيانات الرئيسية (Master Data)
        # ====================================================================
        master_patterns = [
            r'(master_certificates|suppliers|packaging_profiles|ports|carriers|markets|visual_identity)\s*=\s*\[',
            r'(master_certificates|suppliers|packaging_profiles|ports|carriers|markets|visual_identity)\s*=\s*\{'
        ]
        for pattern in master_patterns:
            for match in re.finditer(pattern, self.source_code, re.MULTILINE):
                var_name = match.group(1)
                start = match.start()
                end = self._find_block_end(self.source_code, start)
                content = self.source_code[start:end]
                line_no = self.source_code[:start].count('\n') + 1
                knowledge["master_data"].append({
                    "name": var_name,
                    "content": content[:500] + "..." if len(content) > 500 else content,
                    "source_line": line_no,
                    "type": "MASTER_DATA",
                    "confidence": "HIGH",
                    "legacy_origin": f"{self.brain_path.name}:{line_no}"
                })
        
        # ====================================================================
        # 3. استخراج القواعد التجارية (من الشروط المنطقية)
        # ====================================================================
        # 3.1 من if statements مع تعليقات
        rule_pattern = r'if\s+([^:]+):\s*#\s*(.*?)(?:\n|$)'
        for match in re.finditer(rule_pattern, self.source_code):
            condition = match.group(1).strip()
            comment = match.group(2).strip() if match.group(2) else ""
            if any(kw in condition.lower() for kw in ['product', 'customer', 'certificate', 
                                                       'supplier', 'weight', 'price', 'export', 
                                                       'validation', 'check']):
                line_no = self.source_code[:match.start()].count('\n') + 1
                knowledge["business_rules"].append({
                    "condition": condition,
                    "comment": comment,
                    "source_line": line_no,
                    "type": "BUSINESS_RULE",
                    "confidence": "MEDIUM",
                    "legacy_origin": f"{self.brain_path.name}:{line_no}"
                })
        
        # 3.2 استخراج القواعد من دوال build_* (مثل build_supplier_master)
        build_pattern = r'def\s+(build_\w+)\s*\([^)]*\):.*?(?=\n\s*def|\Z)'
        for match in re.finditer(build_pattern, self.source_code, re.DOTALL):
            func_name = match.group(1)
            func_body = match.group(0)
            line_no = self.source_code[:match.start()].count('\n') + 1
            # نبحث عن شروط داخل الدالة
            for cond_match in re.finditer(r'if\s+([^:]+):', func_body):
                condition = cond_match.group(1).strip()
                if any(kw in condition.lower() for kw in ['product', 'category', 'supplier', 'certificate']):
                    knowledge["business_rules"].append({
                        "condition": condition,
                        "comment": f"من دالة {func_name}",
                        "source_line": line_no,
                        "type": "BUILD_RULE",
                        "confidence": "MEDIUM",
                        "legacy_origin": f"{self.brain_path.name}:{line_no} ({func_name})"
                    })
        
        # ====================================================================
        # 4. استخراج العلاقات (من روابط البيانات)
        # ====================================================================
        # 4.1 استخراج العلاقات من القوائم المرتبطة (مثل supplier-product-links)
        link_pattern = r'(\w+_links|links)\s*=\s*\[([^\]]+)\]'
        for match in re.finditer(link_pattern, self.source_code, re.DOTALL):
            var_name = match.group(1)
            content = match.group(2)
            line_no = self.source_code[:match.start()].count('\n') + 1
            # استخراج الروابط الفردية من المحتوى
            for item_match in re.finditer(r'\{([^}]+)\}', content):
                item = item_match.group(1)
                # استخراج العلاقات مثل "supplier_id": "SUP-001", "product_id": "PROD-001"
                ids = re.findall(r'"(\w+_id)"\s*:\s*"([^"]+)"', item)
                if len(ids) >= 2:
                    source_type = ids[0][0].replace('_id', '')
                    source_id = ids[0][1]
                    target_type = ids[1][0].replace('_id', '')
                    target_id = ids[1][1]
                    knowledge["relationships"].append({
                        "source_type": source_type,
                        "source_id": source_id,
                        "relation": f"{source_type}_to_{target_type}",
                        "target_type": target_type,
                        "target_id": target_id,
                        "source_line": line_no,
                        "type": "RELATIONSHIP",
                        "confidence": "HIGH",
                        "legacy_origin": f"{self.brain_path.name}:{line_no}"
                    })
        
        # 4.2 استخراج العلاقات من دوال الحلقات (for product in products)
        loop_pattern = r'for\s+(\w+)\s+in\s+(\w+):\s*#?\s*(.*?)(?=\n|$)'
        for match in re.finditer(loop_pattern, self.source_code):
            var_name = match.group(1)
            iterable = match.group(2)
            comment = match.group(3).strip() if match.group(3) else ""
            if iterable in ['products', 'suppliers', 'certificates']:
                line_no = self.source_code[:match.start()].count('\n') + 1
                knowledge["relationships"].append({
                    "source_type": iterable.rstrip('s'),
                    "relation": f"iterates_over_{var_name}",
                    "target_type": var_name,
                    "comment": comment,
                    "source_line": line_no,
                    "type": "ITERATION",
                    "confidence": "MEDIUM",
                    "legacy_origin": f"{self.brain_path.name}:{line_no}"
                })
        
        # ====================================================================
        # 5. استخراج القدرات (من الدوال الرئيسية)
        # ====================================================================
        capability_patterns = [
            r'def\s+(run_\w+)\s*\(',
            r'def\s+(build_\w+)\s*\(',
            r'def\s+(analyze_\w+)\s*\(',
            r'def\s+(generate_\w+)\s*\(',
            r'def\s+(integrate_\w+)\s*\(',
            r'def\s+(validate_\w+)\s*\(',
            r'def\s+(execute_\w+)\s*\('
        ]
        for pattern in capability_patterns:
            for match in re.finditer(pattern, self.source_code):
                func_name = match.group(1)
                line_no = self.source_code[:match.start()].count('\n') + 1
                # تحديد نوع القدرة
                if func_name.startswith('run_'):
                    cap_type = "EXECUTION"
                elif func_name.startswith('build_'):
                    cap_type = "BUILD"
                elif func_name.startswith('analyze_'):
                    cap_type = "ANALYSIS"
                elif func_name.startswith('generate_'):
                    cap_type = "GENERATION"
                elif func_name.startswith('integrate_'):
                    cap_type = "INTEGRATION"
                elif func_name.startswith('validate_'):
                    cap_type = "VALIDATION"
                elif func_name.startswith('execute_'):
                    cap_type = "EXECUTION"
                else:
                    cap_type = "UNKNOWN"
                
                knowledge["capabilities"].append({
                    "name": func_name,
                    "type": cap_type,
                    "source_line": line_no,
                    "confidence": "MEDIUM",
                    "legacy_origin": f"{self.brain_path.name}:{line_no}"
                })
        
        # ====================================================================
        # 6. استخراج سير العمل (من تسلسل استدعاءات الدوال)
        # ====================================================================
        # نبحث عن دوال تستدعي دوال أخرى
        call_pattern = r'self\.(run_\w+|build_\w+|analyze_\w+)\s*\('
        for match in re.finditer(call_pattern, self.source_code):
            caller_line = self.source_code[:match.start()].count('\n') + 1
            callee = match.group(1)
            # نبحث عن اسم الدالة التي تحتوي على هذا الاستدعاء
            # نبحث للخلف عن def
            before = self.source_code[:match.start()]
            def_match = re.search(r'def\s+(\w+)\s*\(', before[::-1])
            if def_match:
                caller = def_match.group(1)[::-1]  # نعكس النص
                knowledge["workflows"].append({
                    "caller": caller,
                    "callee": callee,
                    "source_line": caller_line,
                    "type": "WORKFLOW_STEP",
                    "confidence": "MEDIUM",
                    "legacy_origin": f"{self.brain_path.name}:{caller_line}"
                })
        
        # ====================================================================
        # 7. تسجيل الأدلة العامة
        # ====================================================================
        knowledge["evidence"].append({
            "source": str(self.brain_path),
            "extracted_at": "2026-08-09",
            "total_lines": len(self.source_code.splitlines()),
            "extraction_rules": ["regex_based", "pattern_matching"],
            "confidence": "HIGH"
        })
        
        return knowledge
    
    def _find_block_end(self, text: str, start: int) -> int:
        """يجد نهاية كتلة (قائمة أو قاموس) بشكل تقريبي."""
        lines = text[start:].splitlines()
        depth = 0
        in_string = False
        for i, line in enumerate(lines):
            for char in line:
                if char in ('"', "'"):
                    in_string = not in_string
                if not in_string:
                    if char in '([{':
                        depth += 1
                    elif char in ')]}':
                        depth -= 1
            if depth == 0 and i > 0:
                return start + text[start:].index('\n'.join(lines[:i+1])) + len('\n'.join(lines[:i+1]))
        return len(text)
    
    def save_knowledge(self, output_path: Path):
        """يحفظ المعرفة المستخرجة في ملف JSON."""
        knowledge = self.extract_knowledge()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, indent=2, ensure_ascii=False)
        print(f"✅ تم استخراج المعرفة وحفظها في: {output_path}")
        return knowledge