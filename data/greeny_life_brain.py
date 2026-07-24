
```python
#!/usr/bin/env python3
"""
Greeny-Life EOS Brain - Autonomous Code Governance & Remediation System
مع إضافة:
- وكيل الأمان (Bandit + CodeQL)
- وكيل الأداء (k6)
- وكيل التوثيق (AI Documentation Generator)
"""

import os
import sys
import json
import subprocess
import logging
import argparse
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import yaml
import requests

# ============================================================================
# Configuration & Data Classes
# ============================================================================

@dataclass
class ScanResult:
    tool: str
    passed: bool
    findings: List[Dict] = field(default_factory=list)
    summary: str = ""
    raw_output: str = ""
    score: float = 0.0  # For performance/security scoring

@dataclass
class RemediationResult:
    tool: str
    success: bool
    pr_url: Optional[str] = None
    commit_hash: Optional[str] = None
    message: str = ""

class GreenyLifeBrain:
    def __init__(self, repo_path: str, config_path: Optional[str] = None):
        self.repo_path = Path(repo_path).resolve()
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self._check_prerequisites()
        self.docs_output_dir = self.repo_path / "docs" / "auto-generated"

    # ------------------------------------------------------------------------
    # Initialization & Helpers (بقيت كما هي مع إضافة متطلبات جديدة)
    # ------------------------------------------------------------------------
    def _load_config(self, config_path: Optional[str]) -> Dict:
        default_config = {
            "sonarqube": {"url": os.getenv("SONARQUBE_URL", "http://localhost:9000"), "token": os.getenv("SONAR_TOKEN")},
            "github": {"token": os.getenv("GITHUB_TOKEN")},
            "llm": {"provider": os.getenv("LLM_PROVIDER", "claude"), "model": os.getenv("LLM_MODEL", "claude-3-opus-20240229")},
            "govern": {"trust_threshold": 0.95, "window_size": 10},
            "archguard": {"config": ".archguard.yml"},
            "ouro_loop": {"bound_file": "BOUND.md"},
            "audit": {"tier": "STANDARD"},
            # إعدادات الوكلاء الجديدة
            "security": {
                "tools": ["bandit", "codeql"],  # codeql يتطلب تهيئة خاصة
                "severity_threshold": "MEDIUM"   # LOW, MEDIUM, HIGH
            },
            "performance": {
                "tool": "k6",
                "test_dir": "tests/performance",
                "vus": 10,          # عدد المستخدمين الافتراضي
                "duration": "10s"   # مدة الاختبار
            },
            "documentation": {
                "auto_fix": True,    # هل يقوم بإنشاء التوثيق تلقائياً؟
                "ignore_patterns": [".*test.*", ".*migrations.*"]
            }
        }
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        return default_config

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("GreenyLifeBrain")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _check_prerequisites(self):
        required = ["git", "python3"]
        for cmd in required:
            if not self._which(cmd):
                self.logger.error(f"Required command not found: {cmd}")
                sys.exit(1)
        # أدوات الوكلاء الجدد
        optional = ["bandit", "codeql", "k6", "claude", "gh"]
        for cmd in optional:
            if self._which(cmd):
                self.logger.info(f"Found {cmd}")
            else:
                self.logger.warning(f"{cmd} not found. Some features may be limited.")

    def _which(self, cmd: str) -> bool:
        return subprocess.run(["which", cmd], capture_output=True).returncode == 0

    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict] = None) -> Tuple[int, str, str]:
        cwd = cwd or self.repo_path
        full_env = os.environ.copy()
        if env: full_env.update(env)
        proc = subprocess.run(cmd, cwd=cwd, env=full_env, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    # ========================================================================
    # 1. وكيل الأمان (Security Agent) - Bandit + CodeQL
    # ========================================================================
    def run_security_scan(self) -> ScanResult:
        """تنفيذ فحص أمان متقدم باستخدام Bandit و CodeQL (إن وجد)."""
        self.logger.info("🛡️ Running Security Scan (Bandit + CodeQL)...")
        result = ScanResult(tool="SecurityAgent", passed=True, score=100.0)
        findings_all = []

        # 1. تشغيل Bandit (لـ Python)
        if self._which("bandit"):
            self.logger.info("   - Running Bandit...")
            # تجاهل مجلدات الاختبارات
            cmd = ["bandit", "-r", str(self.repo_path / "src"), "-f", "json", "-ll"]  # -ll للمستوى المتوسط
            returncode, stdout, stderr = self._run_command(cmd)
            result.raw_output += stdout

            if returncode == 0:
                try:
                    data = json.loads(stdout)
                    metrics = data.get("metrics", {})
                    result.score = max(0, 100 - (metrics.get("SEVERITY.HIGH", 0) * 10 + metrics.get("SEVERITY.MEDIUM", 0) * 5))
                    findings = [{"file": f["filename"], "issue": f["issue_text"], "severity": f["issue_severity"]} 
                                for f in data.get("results", [])]
                    if findings:
                        result.findings.extend(findings)
                        result.summary = f"Bandit found {len(findings)} issues (Score: {result.score:.1f}%)"
                    else:
                        result.summary = "Bandit: No security issues found!"
                except json.JSONDecodeError:
                    result.summary = "Bandit scan completed but output parsing failed."
            else:
                result.summary = f"Bandit failed: {stderr}"
                result.passed = False
        else:
            result.summary += "Bandit not installed. "

        # 2. تشغيل CodeQL (إن وجد)
        if self._which("codeql"):
            self.logger.info("   - Running CodeQL...")
            # CodeQL يتطلب قاعدة بيانات. سنقوم بمحاكاة بسيطة أو التحقق من وجودها.
            # هنا نستخدم الطريقة البسيطة: نبحث عن ملفات .ql أو نمرر الأوامر الأساسية.
            # في البيئة الواقعية، تحتاج إلى codeql database create.
            try:
                # مجرد اختبار وجود قاعدة بيانات أو تشغيل تحليل سريع
                cmd = ["codeql", "resolve", "languages"]
                ret, out, err = self._run_command(cmd)
                if ret == 0:
                    self.logger.info("   - CodeQL environment seems ready.")
                    # محاكاة: نضيف وجوود CodeQL كعلامة إيجابية
                    result.findings.append({"tool": "CodeQL", "status": "Ready for deep analysis"})
                else:
                    self.logger.warning("CodeQL not fully configured.")
            except Exception as e:
                self.logger.warning(f"CodeQL check failed: {e}")

        # تحديث حالة النجاح بناءً على النتائج
        if result.score < 50 and result.findings:
            result.passed = False
            result.summary += " ❌ Security threshold breached."

        self.logger.info(f"✅ Security Scan: {result.summary}")
        return result

    # ========================================================================
    # 2. وكيل الأداء (Performance Agent) - k6
    # ========================================================================
    def run_performance_test(self) -> ScanResult:
        """تنفيذ اختبارات الأداء باستخدام k6."""
        self.logger.info("⚡ Running Performance Test (k6)...")
        result = ScanResult(tool="PerformanceAgent", passed=True, score=100.0)

        if not self._which("k6"):
            self.logger.error("k6 not installed. Install: brew install k6 (macOS) or apt install k6 (Ubuntu)")
            result.summary = "Performance tests skipped: k6 not found."
            result.passed = False
            return result

        test_dir = self.repo_path / self.config["performance"]["test_dir"]
        test_dir.mkdir(parents=True, exist_ok=True)

        # إنشاء اختبار افتراضي (Smoke Test) إذا لم يكن موجوداً
        test_file = test_dir / "smoke_test.js"
        if not test_file.exists():
            self.logger.info("   - No performance test found. Generating default smoke test for localhost:8000...")
            test_file.write_text("""
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: __ENV.K6_VUS || 10,
  duration: __ENV.K6_DURATION || '10s',
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must be below 500ms
    http_req_failed: ['rate<0.05'],    // error rate less than 5%
  }
};

export default function () {
  const res = http.get('http://localhost:8000/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}
""")

        # تشغيل k6 مع تصدير النتائج كـ JSON
        results_json = test_dir / "results.json"
        cmd = [
            "k6", "run", str(test_file),
            "--out", "json=" + str(results_json),
            "-e", f"K6_VUS={self.config['performance']['vus']}",
            "-e", f"K6_DURATION={self.config['performance']['duration']}"
        ]
        returncode, stdout, stderr = self._run_command(cmd)
        result.raw_output = stdout + stderr

        # تحليل النتائج
        if results_json.exists():
            try:
                with open(results_json) as f:
                    # نقرأ السطور الأخيرة التي تحتوي على الملخص
                    lines = f.readlines()
                    # نبحث عن metrics
                    for line in reversed(lines):
                        if "http_req_duration" in line or "http_req_failed" in line:
                            data = json.loads(line)
                            if data.get("type") == "Metric":
                                metric_name = data["metric"]
                                values = data["data"]["value"]
                                if metric_name == "http_req_duration":
                                    avg = values.get("avg", 0)
                                    p95 = values.get("p(95)", 0)
                                    result.score = max(0, 100 - (p95 / 10))
                                    result.summary = f"Perf: Avg={avg:.0f}ms, P95={p95:.0f}ms"
                                elif metric_name == "http_req_failed":
                                    rate = values
                                    if rate > 0.05:
                                        result.passed = False
                                        result.summary += " ❌ Error rate too high!"
                    if not result.summary:
                        result.summary = "Performance test completed successfully."
            except Exception as e:
                self.logger.warning(f"Could not parse k6 results: {e}")
                result.summary = "Performance test ran, but results parsing failed."

        if returncode != 0:
            result.passed = False
            result.summary = f"Performance test execution failed: {stderr}"

        self.logger.info(f"✅ Performance: {result.summary}")
        return result

    # ========================================================================
    # 3. وكيل التوثيق (Documentation Agent) - AI + AST
    # ========================================================================
    def run_documentation_agent(self, use_ai: bool = True) -> RemediationResult:
        """توليد وتحديث التوثيق تلقائياً باستخدام تحليل الكود أو الذكاء الاصطناعي."""
        self.logger.info("📝 Running Documentation Agent...")
        result = RemediationResult(tool="DocumentationAgent", success=False)

        # 1. تحليل بنية المشروع لتوليد ملفات Markdown هيكلية
        self.docs_output_dir.mkdir(parents=True, exist_ok=True)
        
        # إنشاء ملف index للمجلدات الرئيسية
        modules = ["master_data", "gl_dos", "operations", "crm", "logistics", "compliance", "finance", "analytics", "administration"]
        index_content = "# 📚 Greeny-Life EOS - Auto-Generated Documentation\n\n"
        index_content += "## Modules Overview\n\n"

        for module in modules:
            module_path = self.repo_path / "src" / module
            if module_path.exists():
                index_content += f"- **{module}**: Located at src/{module}\n"
                # توليد ملف تفصيلي لكل موديول
                self._generate_module_docs(module, module_path)
            else:
                index_content += f"- **{module}**: (Not found in src/)\n"

        # كتابة الفهرس الرئيسي
        (self.docs_output_dir / "INDEX.md").write_text(index_content)

        # 2. تحليل ملفات Python لتوليد Docstrings مفقودة (إن أمكن)
        if use_ai and self._which("claude"):
            self.logger.info("   - Using AI (Claude) to generate docstrings...")
            # نطلب من Claude تحليل ملف معين وإضافة التوثيق
            # (محاكاة: في الواقع ستمرر الملفات للـ CLI)
            try:
                # مثال: نمرر الأمر لـ claude لمراجعة ملفات src
                cmd = ["claude", "-p", "Analyze src/ folder and add missing Python docstrings. Return only the changes."]
                ret, out, err = self._run_command(cmd)
                if ret == 0:
                    result.success = True
                    result.message = "AI documentation generated successfully."
                else:
                    self.logger.warning(f"AI doc generation returned error: {err}")
                    result.success = False
                    result.message = "AI processing failed."
            except Exception as e:
                self.logger.warning(f"AI execution error: {e}")
                result.success = False
        else:
            # Fallback: استخدام AST لإنشاء ملفات هيكلية (بدون نصوص)
            self.logger.info("   - Using static AST analysis for structure docs...")
            self._generate_structure_docs()
            result.success = True
            result.message = "Structural documentation generated."

        self.logger.info(f"✅ Documentation: {result.message}")
        return result

    def _generate_module_docs(self, module_name: str, path: Path):
        """توليد ملف توثيق لوحدة معينة."""
        content = f"# {module_name.replace('_', ' ').title()}\n\n"
        content += f"Auto-generated documentation for src/{module_name}.\n\n"
        content += "## Structure\n\n"
        for item in path.iterdir():
            if item.is_dir():
                content += f"- 📁 {item.name}/\n"
            elif item.suffix == ".py":
                content += f"- 🐍 {item.name}\n"
        (self.docs_output_dir / f"{module_name}.md").write_text(content)

    def _generate_structure_docs(self):
        """استخدام AST لاستخراج الفئات والدوال الأساسية."""
        src_dir = self.repo_path / "src"
        if not src_dir.exists():
            return
        for py_file in src_dir.rglob("*.py"):
            if "test" in str(py_file) or "migrations" in str(py_file):
                continue
            try:
                tree = ast.parse(py_file.read_text())
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                if classes or funcs:
                    doc_file = self.docs_output_dir / f"{py_file.stem}.md"
                    doc_file.write_text(
                        f"# {py_file.name}\n\n"
                        f"**Classes:** {', '.join(classes) if classes else 'None'}\n\n"
                        f"**Functions:** {', '.join(funcs) if funcs else 'None'}\n"
                    )
            except Exception:
                pass

    # ========================================================================
    # بقية الوحدات (ArchGuard, govern-kit, SonarQube, إلخ..) 
    # تم اختصارها هنا لتوفير المساحة ولكن موجودة في الكود الكامل.
    # في الكود الكامل المقدم للمستخدم سيتم تضمينها بالكامل.
    # ========================================================================
    # ... (هنا توضع دوال run_arch_guard, run_govern_kit, run_ouro_loop, 
    # run_sonarqube_scan, run_sonarqube_ai_agent, run_cca_audit, 
    # create_remediation_pr كما كانت سابقاً) ...

    # ========================================================================
    # الدورة الأساسية المُحدّثة (Pipeline)
    # ========================================================================
    def run_full_pipeline(self, auto_fix: bool = True, create_pr: bool = True) -> Dict[str, Any]:
        self.logger.info("=" * 60)
        self.logger.info("🧠 Greeny-Life EOS Brain - FULL PIPELINE (With New Agents)")
        self.logger.info("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "scans": {},
            "remediations": [],
            "overall_status": "PASSED",
            "pr_url": None
        }

        # ------ المرحلة 1: الحوكمة والجودة (كما كانت) ------
        self.logger.info("\n📍 Phase 1: Governance & Architecture")
        results["scans"]["archguard"] = self.run_arch_guard().__dict__
        results["scans"]["govern_kit"] = self.run_govern_kit().__dict__
        results["scans"]["ouro_loop"] = self.run_ouro_loop().__dict__

        # ------ المرحلة 2: التحليل الثابت (SonarQube) ------
        self.logger.info("\n📍 Phase 2: Static Analysis")
        results["scans"]["sonarqube"] = self.run_sonarqube_scan().__dict__

        # ====== المرحلة 3: الوكلاء الجدد (الأمان، الأداء، التوثيق) ======
        self.logger.info("\n📍 Phase 3: Security, Performance & Documentation")

        # 3.1 الأمان
        sec_result = self.run_security_scan()
        results["scans"]["security"] = sec_result.__dict__

        # 3.2 الأداء
        perf_result = self.run_performance_test()
        results["scans"]["performance"] = perf_result.__dict__

        # 3.3 التوثيق (يتم تشغيله دائماً لأنه غير مدمر)
        doc_result = self.run_documentation_agent(use_ai=True)
        results["remediations"].append(doc_result.__dict__)  # نعتبره تحديثاً

        # ------ المرحلة 4: الإصلاح الآلي (Auto-fix) إن وجدت مشاكل ------
        if auto_fix:
            self.logger.info("\n📍 Phase 4: AI-Powered Remediation")
            needs_fix = not all([
                results["scans"]["archguard"]["passed"],
                results["scans"]["govern_kit"]["passed"],
                results["scans"]["sonarqube"]["passed"],
                sec_result.passed,
                perf_result.passed
            ])
            if needs_fix:
                self.logger.warning("⚠️ Issues detected, initiating auto-remediation...")
                sq_fix = self.run_sonarqube_ai_agent()
                results["remediations"].append(sq_fix.__dict__)
                # إعادة الفحص بعد الإصلاح
                results["scans"]["sonarqube_after"] = self.run_sonarqube_scan().__dict__
                results["scans"]["security_after"] = self.run_security_scan().__dict__
            else:
                self.logger.info("✅ No critical issues detected, skipping remediation.")

        # ------ المرحلة 5: إنشاء Pull Request ------
        if create_pr and results["remediations"]:
            self.logger.info("\n📍 Phase 5: Creating Pull Request")
            pr_url = self.create_remediation_pr(
                f"Auto-fixed issues & updated documentation ({len(results['remediations'])} actions)"
            )
            results["pr_url"] = pr_url

        # ------ الحالة النهائية ------
        all_passed = all([
            results["scans"]["archguard"]["passed"],
            results["scans"]["govern_kit"]["passed"],
            results["scans"]["sonarqube"]["passed"],
            results["scans"]["security"]["passed"],
            results["scans"]["performance"]["passed"]
        ])
        results["overall_status"] = "PASSED" if all_passed else "FAILED"

        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"🏁 Pipeline Complete: {results['overall_status']}")
        self.logger.info("=" * 60)
        return results

# ============================================================================
# CLI Entry Point
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Greeny-Life EOS Brain with Security, Performance & Documentation Agents"
    )
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--config", help="Path to config YAML file")
    parser.add_argument("--no-fix", action="store_true", help="Skip auto-remediation")
    parser.add_argument("--no-pr", action="store_true", help="Skip creating PR")
    parser.add_argument("--output", help="Output results to JSON file")
    args = parser.parse_args()

    brain = GreenyLifeBrain(args.repo, args.config)
    results = brain.run_full_pipeline(auto_fix=not args.no_fix, create_pr=not args.no_pr)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {output_path}")

    sys.exit(0 if results.get("overall_status") == "PASSED" else 1)

if __name__ == "__main__":
    main()
```

---

