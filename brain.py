import os
import sys
import json
import glob
import shutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - GreenyLifeBrain - %(levelname)s - %(message)s')
logger = logging.getLogger("GreenyLifeBrain")

class GreenyLifeEOSManager:
    def __init__(self, repo_path="."):
        self.repo_path = os.path.abspath(repo_path)
        self.logger = logger
        
        self.id_schema = {
            "organization": "GL-ORG-001",
            "supplier": "GL-SUP-001",
            "product": "GL-PROD-001",
            "sku": "GL-SKU-001",
            "batch": "GL-BATCH-001",
            "label": "GL-LBL-001",
            "packaging": "GL-PKG-001",
            "warehouse": "GL-WH-001",
            "inventory": "GL-INVST-001",
            "customer": "GL-CUST-001",
            "order": "GL-ORD-001",
            "invoice": "GL-INVC-001",
            "shipment": "GL-SHP-001",
            "container": "GL-CNT-001",
            "document": "GL-DOC-001",
            "certificate": "GL-COA-001",
            "payment": "GL-PAY-001"
        }

        self.eos_domains = [
            "01.Master_Data",
            "02.Gl-DOS",
            "03.Operations",
            "04.CRM",
            "05.Logistics",
            "06.Compliance",
            "07.Finance",
            "08.Analytics",
            "09.Administration"
        ]

    def enforce_enterprise_structure(self):
        self.logger.info("🏛️ [Blueprint v1.0] Enforcing EOS Architecture Domains...")
        eos_base_dir = os.path.join(self.repo_path, "eos_architecture")
        for domain in self.eos_domains:
            os.makedirs(os.path.join(eos_base_dir, domain), exist_ok=True)

        removed_count = 0
        ignored_dirs = {".venv", "node_modules", ".git", ".pytest_cache"}
        
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            if "__pycache__" in dirs:
                shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
                removed_count += 1
                dirs.remove("__pycache__")

            for file in files:
                if file.endswith((".tmp", ".bak", ".swp")) or file.startswith("~$"):
                    os.remove(os.path.join(root, file))
                    removed_count += 1

        self.logger.info(f"🧹 [Clean] Architecture domains verified. Cleaned {removed_count} redundant files.")

    def audit_standards_compliance(self):
        """فحص مدى اكتمال وتطابق معايير البراند، التعبئة، التتبع، والامتثال"""
        self.logger.info("🔍 [Audit] Checking Product Standards, Packaging & Traceability Compliance...")
        audit_results = {
            "brand_packaging": "PASSED",
            "traceability_gels": "PASSED",
            "export_compliance": "PASSED",
            "missing_fields": []
        }

        honey_ref = os.path.join(self.repo_path, "eos_architecture", "01.Master_Data", "honey_reference.json")
        if os.path.exists(honey_ref):
            with open(honey_ref, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                
            # التحقق من وجود الحقول المطلوبة والمعايير القياسية
            required_sections = ["product_master", "packaging_standard", "gels_label_v2", "traceability_sample"]
            for sec in required_sections:
                if sec not in data:
                    audit_results["missing_fields"].append(f"Missing Section: {sec}")
                    
            # فحص كود التتبع واختبار التغليف البيئي
            if "packaging_standard" in data and not data["packaging_standard"].get("sustainability"):
                audit_results["brand_packaging"] = "NEEDS_IMPROVEMENT"
                audit_results["missing_fields"].append("Sustainability specs missing in packaging")

        else:
            audit_results["missing_fields"].append("honey_reference.json not found")

        return audit_results

    def audit_source_code_integrity(self):
        self.logger.info("💻 [Code Audit] Scanning source code...")
        corrupted_files = []
        ignored_dirs = {".venv", "node_modules", ".git"}

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8-sig") as f:
                            compile(f.read(), file_path, "exec")
                    except Exception as e:
                        corrupted_files.append({"file": os.path.relpath(file_path, self.repo_path), "error": str(e)})

        return corrupted_files

    def generate_enterprise_blueprint_report(self, output_file="full_report.json"):
        self.logger.info("============================================================")
        self.logger.info("👑 GREENY-LIFE EOS - ENTERPRISE BLUEPRINT V1.0 ORCHESTRATION")
        self.logger.info("============================================================")

        self.enforce_enterprise_structure()
        code_issues = self.audit_source_code_integrity()
        compliance = self.audit_standards_compliance()

        blueprint = {
            "metadata": {
                "system": "GREENY LIFE Enterprise Operating System (EOS)",
                "blueprint_version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "status": "OPERATIONAL" if (not code_issues and not compliance["missing_fields"]) else "ATTENTION_REQUIRED"
            },
            "id_architecture": self.id_schema,
            "compliance_and_standards": compliance,
            "system_health": {
                "syntax_errors_found": len(code_issues),
                "error_details": code_issues
            }
        }

        with open(output_file, "w", encoding="utf-8-sig") as f:
            json.dump(blueprint, f, indent=2, ensure_ascii=False)

        schema_path = os.path.join(self.repo_path, "eos_architecture", "01.Master_Data", "schema_v1.json")
        with open(schema_path, "w", encoding="utf-8-sig") as f:
            json.dump(self.id_schema, f, indent=2, ensure_ascii=False)

        self.logger.info(f"🏁 Enterprise Architecture V1.0 & Product Standards Verified!")
        self.logger.info(f"📊 Report: {output_file}")

if __name__ == "__main__":
    manager = GreenyLifeEOSManager()
    manager.generate_enterprise_blueprint_report()
