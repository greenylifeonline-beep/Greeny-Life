#!/usr/bin/env python3
"""
Greeny-Life EOS Brain - Autonomous Code Governance & Remediation System
مع أدوات الفحص الشامل (Legacy Audit & Dependency Graph Generator)
"""

import os
import sys
import json
import subprocess
import logging
import ast
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

@dataclass
class ScanResult:
    tool: str
    passed: bool
    findings: List[Dict] = field(default_factory=list)
    summary: str = ""
    score: float = 0.0

class GreenyLifeBrainAuditEngine:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.logger = self._setup_logging()
        self.legacy_audit_dir = self.repo_path / "legacy_audit_reports"
        self.legacy_audit_dir.mkdir(exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("GreenyLifeAuditEngine")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def audit_legacy_codebase(self) -> Dict[str, Any]:
        """فحص وتحليل النظام القديم واستخراج التبعيات وهيكل الملفات"""
        self.logger.info("🔍 بدء فحص النظام القديم وتحليل هيكل الملفات والتبعيات...")
        
        inventory = {
            "total_files": 0,
            "python_files": [],
            "typescript_files": [],
            "json_configs": [],
            "todos_found": [],
            "dependency_graph": {}
        }

        for root, dirs, files in os.walk(self.repo_path):
            if any(exclude in root for exclude in ['node_modules', '.git', '.next', 'prisma/migrations', 'legacy_audit_reports']):
                continue
                
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.repo_path)
                inventory["total_files"] += 1

                if file.endswith('.py'):
                    inventory["python_files"].append(str(rel_path))
                    self._scan_file_for_todos(file_path, inventory["todos_found"])
                elif file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    inventory["typescript_files"].append(str(rel_path))
                    self._scan_file_for_todos(file_path, inventory["todos_found"])
                elif file.endswith('.json'):
                    inventory["json_configs"].append(str(rel_path))

        report_path = self.legacy_audit_dir / "legacy_system_inventory.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)

        self.logger.info(f"✨ تم الانتهاء من الفحص. إجمالي الملفات المكتشفة: {inventory['total_files']}")
        self.logger.info(f"📂 تم حفظ التقرير في: {report_path}")
        return inventory

    def _scan_file_for_todos(self, file_path: Path, todos_list: List[Dict]):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if any(keyword in line.upper() for keyword in ['TODO', 'FIXME', 'HACK', 'LEGACY', 'DEPRECATED']):
                        todos_list.append({
                            "file": str(file_path.relative_to(self.repo_path)),
                            "line": line_num,
                            "content": line.strip()
                        })
        except Exception as e:
            self.logger.warning(f"تعذر قراءة الملف {file_path}: {e}")

if __name__ == "__main__":
    current_repo = os.getcwd()
    brain = GreenyLifeBrainAuditEngine(current_repo)
    brain.audit_legacy_codebase()
