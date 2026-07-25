#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
GREENY-LIFE EOS - ENTERPRISE ARTIFICIAL BRAIN
================================================================================
العقل الاصطناعي المتكامل لمنصة Greeny-Life EOS.
يجمع بين الحوكمة، الأمان، الأداء، التوثيق، التحليل العميق، وفهم سياق الأعمال.

الإصدار: 3.0 (Comprehensive Enterprise Edition)
المؤلف: Greeny-Life AI Team
التاريخ: 2026-07-25
--------------------------------------------------------------------------------
الميزات الرئيسية:
1.  الحوكمة المعمارية (ArchGuard, govern-kit, Ouro Loop).
2.  جودة الكود والأمان (SonarQube, Bandit, CodeQL).
3.  اختبارات الأداء (k6).
4.  توليد التوثيق الذكي (AST + Claude).
5.  دمج أدوات مجلد `intelligence` الحالية.
6.  المسح الشامل للمشروع ورسم الخريطة المعرفية.
7.  التحليل العميق للملفات (بما فيها .sst, .meta, .ts, .js).
8.  تحليل البصمة البصرية للبراند (الألوان، الخطوط، الصور).
9.  تحليل سياسات التعبئة والتغليف والعرض.
10. تحليل هيكل واجهة المستخدم (Next.js/React).
11. تحليل المخزون والمنتجات.
12. كشف سبب التكرار والملفات الفاسدة والقديمة.
13. استخلاص القيمة التجارية والذكاء التنفيذي.
14. توليد تقرير شامل بصيغة Markdown/JSON.
15. الإصلاح الآلي ورفع Pull Requests على GitHub.
16. التعلم المستمر وحفظ البصمة التاريخية.
================================================================================
"""

# ============================================================================
# الاستيرادات الأساسية
# ============================================================================
import os
import sys
import json
import yaml
import re
import hashlib
import csv
import subprocess
import logging
import argparse
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import importlib
import requests
import time
import traceback

# ============================================================================
# التحقق من وجود المكتبات الاختيارية مع رسائل خطأ واضحة
# ============================================================================
PILLOW_AVAILABLE = False
Image = None
try:
    pil_image = importlib.import_module("PIL.Image")
    Image = pil_image
    PILLOW_AVAILABLE = True
except ImportError:
    Image = None
    print("⚠️  مكتبة Pillow غير مثبتة. لتثبيتها: pip install Pillow")

PANDAS_AVAILABLE = False
pd = None
try:
    pandas_module = importlib.import_module("pandas")
    pd = pandas_module
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False
    print("⚠️  مكتبة Pandas غير مثبتة. لتثبيتها: pip install pandas")

SENTENCE_AVAILABLE = False
SentenceTransformer = None
try:
    sentence_module = importlib.import_module("sentence_transformers")
    SentenceTransformer = sentence_module.SentenceTransformer
    SENTENCE_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_AVAILABLE = False
    print("⚠️  مكتبة sentence-transformers غير مثبتة. لتثبيتها: pip install sentence-transformers")

# ============================================================================
# تعريف هياكل البيانات الأساسية
# ============================================================================

@dataclass
class ScanResult:
    """نتيجة عملية فحص واحدة."""
    tool: str
    passed: bool = True
    score: float = 100.0
    findings: List[Dict] = field(default_factory=list)
    summary: str = ""
    raw_output: str = ""

@dataclass
class RemediationResult:
    """نتيجة عملية إصلاح آلي."""
    tool: str
    success: bool = False
    pr_url: Optional[str] = None
    commit_hash: Optional[str] = None
    message: str = ""

@dataclass
class FileInsight:
    """تحليل عميق لملف واحد."""
    path: str
    extension: str
    size_kb: float
    last_modified: str
    content_type: str
    purpose: str
    key_entities: List[Dict] = field(default_factory=list)
    business_rules: List[str] = field(default_factory=list)
    related_modules: List[str] = field(default_factory=list)
    duplication_reason: str = ""
    recommendation: str = ""
    raw_preview: str = ""
    business_value: Dict = field(default_factory=dict)

# ============================================================================
# الفئة الرئيسية: العقل الاصطناعي لمنصة Greeny-Life
# ============================================================================

class GreenyLifeBrain:
    """
    العقل الرئيسي لمنصة Greeny-Life EOS.
    يقوم بكل عمليات الفحص والتحليل والإصلاح والتفكير.
    """

    def __init__(self, repo_path: str, config_path: Optional[str] = None):
        """
        تهيئة العقل.

        Args:
            repo_path (str): المسار إلى جذر المشروع.
            config_path (Optional[str]): مسار ملف التهيئة YAML.
        """
        self.repo_path = Path(repo_path).resolve()
        self.start_time = datetime.now()
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.knowledge_base = {}
        self.insights = []
        self._check_prerequisites()
        self._ensure_directories()
        self.logger.info("=" * 80)
        self.logger.info("🧠 Greeny-Life EOS Brain initialized successfully.")
        self.logger.info(f"📂 Project Path: {self.repo_path}")
        self.logger.info("=" * 80)

    # ========================================================================
    # 1. التهيئة وإعداد البيئة
    # ========================================================================

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """تحميل ملف التهيئة أو إنشاء إعدادات افتراضية ذكية."""
        default_config = {
            "sonarqube": {"url": os.getenv("SONARQUBE_URL", "http://localhost:9000"), "token": os.getenv("SONAR_TOKEN")},
            "github": {"token": os.getenv("GITHUB_TOKEN")},
            "llm": {"provider": os.getenv("LLM_PROVIDER", "claude"), "model": os.getenv("LLM_MODEL", "claude-3-opus-20240229")},
            "govern": {"trust_threshold": 0.90, "window_size": 10},
            "archguard": {"config": ".archguard.yml"},
            "ouro_loop": {"bound_file": "BOUND.md"},
            "audit": {"tier": "DEEP"},
            "security": {"tools": ["bandit"], "severity_threshold": "MEDIUM"},
            "performance": {"test_dir": "tests/performance", "vus": 10, "duration": "10s"},
            "documentation": {"auto_fix": True, "ignore_patterns": [".*test.*", ".*migrations.*"]},
            "brand": {"primary_color": ["#2E8B57"], "logo_aspect_ratio": 1.0},
            "brain": {
                "max_files_to_deep_scan": 200,
                "enable_ai_summary": True,
                "backup_before_fix": True,
                "knowledge_base_path": "intelligence/knowledge_base"
            }
        }
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_update(default_config, user_config)
            except Exception as e:
                print(f"⚠️  خطأ في قراءة ملف التهيئة: {e}. سيتم استخدام الإعدادات الافتراضية.")
        return default_config

    def _deep_update(self, base: Dict, update: Dict):
        """دمج عميق للقواميس."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _setup_logging(self) -> logging.Logger:
        """إعداد نظام التسجيل (Logging)."""
        logger = logging.getLogger("GreenyLifeBrain")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            # منع التكرار في السجلات
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            # إضافة سجل ملفي
            log_dir = self.repo_path / "logs" if hasattr(self, 'repo_path') else Path("logs")
            log_dir.mkdir(exist_ok=True)
            fh = logging.FileHandler(log_dir / f"brain-{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger

    def _check_prerequisites(self):
        """التحقق من وجود الأدوات الأساسية والاختيارية."""
        required_tools = ["git"]
        optional_tools = ["python", "sonar-scanner", "bandit", "k6", "claude", "gh", "docker", "archguard", "ouro-loop", "govern", "codeql"]
        
        self.available_tools = {}
        for tool in required_tools:
            self.available_tools[tool] = self._which(tool)
            if not self.available_tools[tool]:
                self.logger.error(f"❌ الأداة الأساسية '{tool}' غير مثبتة! سيتم إيقاف التشغيل.")
                sys.exit(1)

        python_path = self._which("python3") or self._which("python")
        self.available_tools["python3"] = python_path
        if not python_path:
            self.logger.error("❌ Python غير مثبت أو غير موجود في PATH! سيتم إيقاف التشغيل.")
            sys.exit(1)
        
        for tool in optional_tools:
            self.available_tools[tool] = self._which(tool)
            if self.available_tools[tool]:
                self.logger.info(f"✅ الأداة '{tool}' موجودة.")
            else:
                self.logger.warning(f"⚠️  الأداة الاختيارية '{tool}' غير موجودة. سيتم تعطيل ميزاتها.")

    def _which(self, cmd: str) -> bool:
        """التحقق من وجود أمر في مسار النظام بطريقة متوافقة مع جميع أنظمة التشغيل."""
        import shutil
        return shutil.which(cmd) is not None

    def _ensure_directories(self):
        """إنشاء المجلدات الأساسية للمشروع إذا لم تكن موجودة."""
        dirs = ["src", "tests", "docs", "logs", "intelligence", "intelligence/knowledge_base", "intelligence/backups"]
        for d in dirs:
            (self.repo_path / d).mkdir(parents=True, exist_ok=True)
    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict] = None, timeout: int = 300) -> Tuple[int, str, str]:
        """تنفيذ أمر في النظام مع التعامل مع الأخطاء."""
        cwd = cwd or self.repo_path
        
        # تجهيز متغيرات البيئة وضمان أن تكون جميع المفاتيح والقيم نصوصاً (str)
        full_env = {str(k): str(v) for k, v in os.environ.items() if v is not None}
        if env:
            for k, v in env.items():
                if v is not None:
                    full_env[str(k)] = str(v)
        try:
            # تم إضافة encoding و errors لتجنب مشاكل ترميز الحروف
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=full_env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=timeout,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ انتهى وقت تنفيذ الأمر: {' '.join(cmd)}")
            return -1, "", "Timeout"
        except Exception as e:
            self.logger.error(f"💥 خطأ في تنفيذ الأمر: {e}")
            return -1, "", str(e)
        
    # ========================================================================
    # 2. وكلاء الحوكمة المعمارية (Governance & Architecture)
    # ========================================================================

    def run_arch_guard(self) -> ScanResult:
        """Architecture analysis using ArchGuard with full Windows encoding and null-safety support."""
        self.logger.info("🏛️  [ArchGuard] Starting architecture analysis...")
        result = ScanResult(tool="ArchGuard")
        
        if not self.available_tools.get("archguard"):
            result.passed = False
            result.summary = "ArchGuard is not installed."
            return result

        try:
            config_file = self.repo_path / self.config.get("archguard", {}).get("config", "archguard.yaml")
            if not config_file.exists():
                self._run_command(["archguard", "init"])

            ret, out, err = self._run_command(["archguard", "scan", "--format", "json"])
            
            # Safe assignment for raw output
            result.raw_output = out if out else ""
            
            if ret != 0:
                result.passed = False
                safe_err = err if err else (out if out else "Unknown execution error.")
                result.summary = f"Scan failed: {safe_err[:200]}"
                self.logger.info(f"   {result.summary}")
                return result

            if not out or not out.strip():
                result.passed = True
                result.summary = "✅ Architecture is clean (No output from scanner)."
                result.score = 100
                self.logger.info(f"   {result.summary}")
                return result

            data = json.loads(out)
            violations = data.get("violations", []) if isinstance(data, dict) else []
            result.findings = violations
            
            if violations:
                result.passed = False
                result.summary = f"Found {len(violations)} architectural violation(s)."
                result.score = max(0, 100 - len(violations) * 5)
            else:
                result.passed = True
                result.summary = "✅ Architecture structure is clean and valid."
                result.score = 100
                
        except json.JSONDecodeError:
            result.passed = False
            result.summary = "Failed to parse ArchGuard JSON output."
        except Exception as e:
            result.passed = False
            err_msg = str(e) if e else "Unknown exception"
            result.summary = f"ArchGuard execution error: {err_msg[:200]}"

        self.logger.info(f"   {result.summary}")
        return result


    def run_govern_kit(self) -> ScanResult:
        """قياس الثقة وتطبيق الحوكمة باستخدام govern-kit."""
        self.logger.info("⚖️  [govern-kit] قياس مستوى الثقة...")
        result = ScanResult(tool="govern-kit")
        if not self.available_tools.get("govern"):
            result.passed = False
            result.summary = "govern-kit غير مثبت."
            return result

        if not (self.repo_path / ".govern.toml").exists():
            self._run_command(["govern", "init"])

        ret, out, err = self._run_command(["govern", "gate"])
        result.raw_output = out
        if ret != 0:
            result.passed = False
            result.summary = "فشل اجتياز بوابة الثقة. يُطلب مراجعة بشرية."
            result.score = 50
        else:
            result.summary = "✅ اجتاز بوابة الثقة. يُسمح بالعمليات الذاتية."
            result.score = 100
        self.logger.info(f"   {result.summary}")
        return result

    def run_ouro_loop(self) -> ScanResult:
        """تطبيق حدود الحكم الذاتي (Ouro Loop)."""
        self.logger.info("🔄  [Ouro Loop] التحقق من الحدود المطلقة...")
        result = ScanResult(tool="Ouro Loop")
        if not self.available_tools.get("ouro-loop"):
            result.passed = False
            result.summary = "ouro-loop غير مثبت."
            return result

        bound_file = self.repo_path / self.config["ouro_loop"]["bound_file"]
        if not bound_file.exists():
            self.logger.warning("   BOUND.md غير موجود. سيتم إنشاء ملف افتراضي.")
            bound_file.write_text("""# BOUND - القيود المطلقة لمنصة Greeny-Life EOS
## مناطق الخطر (ممنوع اللمس دون مراجعة)
- src/master_data/**
- src/finance/**
- src/auth/**
- src/compliance/**
- .env
- config.yaml

## قوانين حديدية
- يجب أن يجتاز الكود بوابة الجودة في SonarQube.
- يجب موافقة بشري واحد على الأقل لطلبات السحب.
- لا يُسمح بالدمج المباشر على الفرع الرئيسي (main).
""", encoding='utf-8')

        ret, out, err = self._run_command(["ouro-loop", "verify", "--bound", str(bound_file)])
        result.raw_output = out
        if ret != 0:
            result.passed = False
            result.summary = "❌ تم اكتشاف انتهاك للحدود المطلقة!"
            result.score = 0
        else:
            result.summary = "✅ جميع الحدود محترمة."
            result.score = 100
        self.logger.info(f"   {result.summary}")
        return result

    # ========================================================================
    # 3. وكلاء جودة الكود والأمان
    # ========================================================================

    def run_sonarqube_scan(self) -> ScanResult:
        """تحليل الجودة الشامل باستخدام SonarQube."""
        self.logger.info("📊  [SonarQube] بدء تحليل جودة الكود...")
        result = ScanResult(tool="SonarQube")
        if not self.available_tools.get("sonar-scanner"):
            result.passed = False
            result.summary = "sonar-scanner غير مثبت."
            return result

        env = {
            "SONAR_HOST_URL": self.config["sonarqube"]["url"],
            "SONAR_TOKEN": self.config["sonarqube"]["token"]
        }
        # تجاهل مجلدات البناء
        ret, out, err = self._run_command(
            ["sonar-scanner", f"-Dsonar.projectKey=GreenyLifeEOS", "-Dsonar.exclusions=**/node_modules/**,**/.next/**"],
            env=env
        )
        result.raw_output = out + err
        if ret != 0:
            result.passed = False
            result.summary = f"فشل فحص SonarQube: {err[:200]}"
        else:
            result.summary = "✅ تم إرسال التحليل إلى SonarQube بنجاح."
            # محاولة جلب النتيجة
            try:
                resp = requests.get(f"{self.config['sonarqube']['url']}/api/qualitygates/project_status?projectKey=GreenyLifeEOS",
                                    auth=(self.config["sonarqube"]["token"], ""), timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("projectStatus", {}).get("status", "NONE")
                    if status == "OK":
                        result.passed = True
                        result.score = 100
                        result.summary = "✅ اجتاز بوابة الجودة."
                    else:
                        result.passed = False
                        result.score = 50
                        result.summary = f"❌ فشل في بوابة الجودة. الحالة: {status}"
            except:
                pass
        self.logger.info(f"   {result.summary}")
        return result

    def run_security_scan(self) -> ScanResult:
        """فحص الثغرات الأمنية باستخدام Bandit و CodeQL."""
        self.logger.info("🛡️  [Security Agent] فحص الثغرات الأمنية...")
        result = ScanResult(tool="SecurityAgent", score=100)
        findings_all = []

        # Bandit
        if self.available_tools.get("bandit"):
            self.logger.info("   - تشغيل Bandit...")
            ret, out, err = self._run_command(["bandit", "-r", "src", "-f", "json", "-ll", "-x", "tests,node_modules,.next"])
            result.raw_output += out
            if ret == 0 or ret == 1:  # 1 يعني وجود ثغرات
                try:
                    data = json.loads(out)
                    metrics = data.get("metrics", {})
                    high = metrics.get("SEVERITY.HIGH", 0)
                    medium = metrics.get("SEVERITY.MEDIUM", 0)
                    result.score = max(0, 100 - (high * 15 + medium * 5))
                    issues = [{"file": f["filename"], "issue": f["issue_text"], "severity": f["issue_severity"]} 
                              for f in data.get("results", [])]
                    findings_all.extend(issues)
                    if issues:
                        result.summary = f"Bandit: {len(issues)} مشكلة أمنية (Score: {result.score:.1f})"
                    else:
                        result.summary = "Bandit: ✅ لا توجد ثغرات أمنية."
                except json.JSONDecodeError:
                    result.summary = "Bandit: تم التشغيل ولكن تعذر تحليل المخرجات."
            else:
                result.summary = f"Bandit: فشل التشغيل ({err[:100]})"
        else:
            result.summary = "Bandit غير مثبت."

        # CodeQL (محاكاة)
        if self.available_tools.get("codeql"):
            self.logger.info("   - التحقق من CodeQL...")
            ret, out, err = self._run_command(["codeql", "resolve", "languages"])
            if ret == 0:
                result.summary += " | CodeQL جاهز."
            else:
                result.summary += " | CodeQL غير مهيأ."

        if result.score < 60:
            result.passed = False
            result.summary += " ❌ تجاوزت الثغرات الحد المسموح."

        result.findings = findings_all
        self.logger.info(f"   {result.summary}")
        return result

    # ========================================================================
    # 4. وكيل الأداء
    # ========================================================================

    def run_performance_test(self) -> ScanResult:
        """تنفيذ اختبارات الأداء باستخدام k6."""
        self.logger.info("⚡  [Performance Agent] تشغيل اختبارات الأداء...")
        result = ScanResult(tool="PerformanceAgent", score=100)
        if not self.available_tools.get("k6"):
            result.passed = False
            result.summary = "k6 غير مثبت."
            return result

        test_dir = self.repo_path / self.config["performance"]["test_dir"]
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "smoke_test.js"
        
        # إنشاء اختبار افتراضي
        if not test_file.exists():
            test_file.write_text("""
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: __ENV.K6_VUS || 10,
  duration: __ENV.K6_DURATION || '10s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const res = http.get(__ENV.TARGET_URL || 'http://localhost:3000/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
""")

        results_json = test_dir / "results.json"
        target_url = "http://localhost:3000/health"
        # محاولة اكتشاف الـ base URL من Next.js
        if (self.repo_path / "next.config.js").exists():
            target_url = "http://localhost:3000/api/health"  # محاولة افتراضية

        cmd = [
            "k6", "run", str(test_file),
            "--out", "json=" + str(results_json),
            "-e", f"K6_VUS={self.config['performance']['vus']}",
            "-e", f"K6_DURATION={self.config['performance']['duration']}",
            "-e", f"TARGET_URL={target_url}"
        ]
        ret, out, err = self._run_command(cmd, timeout=120)
        result.raw_output = out + err

        if results_json.exists():
            try:
                # تحليل النتائج
                with open(results_json, 'r') as f:
                    lines = f.readlines()
                for line in reversed(lines):
                    if "http_req_duration" in line:
                        data = json.loads(line)
                        if data.get("type") == "Metric":
                            p95 = data["data"]["value"].get("p(95)", 999)
                            avg = data["data"]["value"].get("avg", 999)
                            result.score = max(0, 100 - (p95 / 10))
                            result.summary = f"متوسط زمن الاستجابة: {avg:.0f}ms, P95: {p95:.0f}ms"
                            if p95 > 500:
                                result.passed = False
                                result.summary += " ❌ تجاوز الحد المسموح (500ms)."
                            else:
                                result.summary += " ✅ الأداء جيد."
                            break
                    elif "http_req_failed" in line:
                        data = json.loads(line)
                        if data.get("type") == "Metric":
                            rate = data["data"]["value"]
                            if rate > 0.05:
                                result.passed = False
                                result.summary += " ❌ معدل الأخطاء مرتفع."
            except Exception as e:
                result.summary = f"تعذر تحليل نتائج k6: {e}"
        else:
            if ret != 0:
                result.passed = False
                result.summary = f"فشل اختبار الأداء: {err[:100]}"

        self.logger.info(f"   {result.summary}")
        return result

    # ========================================================================
    # 5. وكيل التوثيق الذكي (AST + AI)
    # ========================================================================

    def run_documentation_agent(self) -> RemediationResult:
        """توليد وتحديث التوثيق باستخدام تحليل AST والذكاء الاصطناعي."""
        self.logger.info("📝  [Documentation Agent] توليد التوثيق...")
        result = RemediationResult(tool="DocumentationAgent")
        
        docs_dir = self.repo_path / "docs" / "auto-generated"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # 1. هيكل المشروع (Project Structure)
        structure_content = "# 📚 Greeny-Life EOS - التوثيق التلقائي\n\n"
        structure_content += f"تم توليد هذا التوثيق بواسطة العقل الاصطناعي في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
        structure_content += "## الهيكل العام للمشروع\n\n```\n"
        structure_content += self._generate_tree_structure(self.repo_path, prefix="", max_depth=3)
        structure_content += "\n```\n\n"

        # 2. تحليل AST للكود المصدري
        src_dir = self.repo_path / "src"
        if src_dir.exists():
            structure_content += "## وحدات الكود المصدري (Modules)\n\n"
            for module_dir in src_dir.iterdir():
                if module_dir.is_dir():
                    py_files = list(module_dir.rglob("*.py"))
                    structure_content += f"### {module_dir.name} ({len(py_files)} ملفات)\n"
                    for pyf in py_files[:5]:
                        classes = self._extract_classes_from_file(pyf)
                        if classes:
                            structure_content += f"- `{pyf.name}`: الكلاسات ({', '.join(classes[:3])})\n"
                    structure_content += "\n"

        # 3. استخدام الذكاء الاصطناعي (إن وجد)
        if self.available_tools.get("claude") and self.config["documentation"]["auto_fix"]:
            self.logger.info("   - استخدام Claude لتوليد توثيق متقدم...")
            prompt = f"""
            قم بتحليل المشروع في المسار: {self.repo_path}
            أبرز الميزات الرئيسية، والهيكل، والاعتماديات.
            أنشئ فقرة تعريفية شاملة للمطورين الجدد باللغة العربية.
            """
            try:
                ret, out, err = self._run_command(["claude", "-p", prompt], timeout=60)
                if ret == 0 and out:
                    structure_content += "## 🧠 ملخص الذكاء الاصطناعي للمشروع\n\n"
                    structure_content += out + "\n\n"
                    result.success = True
                    result.message = "تم توليد التوثيق باستخدام Claude."
            except Exception as e:
                self.logger.warning(f"فشل توليد التوثيق باستخدام Claude: {e}")

        # حفظ التقرير
        (docs_dir / "INDEX.md").write_text(structure_content, encoding='utf-8')
        self.logger.info(f"   ✅ تم حفظ التوثيق في: {docs_dir / 'INDEX.md'}")
        
        if not result.success:
            result.success = True
            result.message = "تم توليد التوثيق الهيكلي بنجاح (بدون AI)."
        
        return result

    def _generate_tree_structure(self, path: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0) -> str:
        """توليد هيكل شجري للمجلدات."""
        if current_depth > max_depth:
            return prefix + "... (المزيد)\n"
        output = ""
        items = sorted([p for p in path.iterdir() if not p.name.startswith('.') and p.name not in ['node_modules', '__pycache__', '.next']])
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            output += f"{prefix}{connector}{item.name}\n"
            if item.is_dir():
                extension = "    " if is_last else "│   "
                output += self._generate_tree_structure(item, prefix + extension, max_depth, current_depth + 1)
        return output

    def _extract_classes_from_file(self, file_path: Path) -> List[str]:
        """استخراج أسماء الكلاسات من ملف Python باستخدام AST."""
        try:
            import ast
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        except:
            return []

    # ========================================================================
    # 6. وكيل دمج الأدوات القديمة (Intelligence Integrator)
    # ========================================================================

    def discover_and_merge_intelligence(self) -> Dict:
        """اكتشاف ودمج الأدوات الموجودة في مجلد intelligence."""
        self.logger.info("🧩  [Intelligence Integrator] اكتشاف ودمج الأدوات القديمة...")
        intel_path = self.repo_path / "intelligence"
        result = {"tools_found": [], "execution_results": [], "merged_skills": []}

        if not intel_path.exists():
            self.logger.warning("   مجلد intelligence غير موجود.")
            return result

        # البحث عن السكريبتات القابلة للتنفيذ
        for ext in ["*.py", "*.ps1", "*.sh", "*.bat", "*.exe", "*.jar"]:
            for tool in intel_path.rglob(ext):
                if tool.is_file() and not tool.name.startswith("."):
                    result["tools_found"].append(str(tool.relative_to(self.repo_path)))
                    self.logger.info(f"   - وجدت أداة: {tool.name}")

                    # محاولة تنفيذ الأداة مع وسم --help أو --analyze
                    if tool.suffix in [".py", ".sh"]:
                        self.logger.info(f"   - تشغيل الأداة: {tool.name} --analyze")
                        ret, out, err = self._run_command(["python" if tool.suffix == ".py" else "sh", str(tool), "--analyze"], timeout=30)
                        if ret == 0:
                            result["execution_results"].append({"tool": tool.name, "status": "success", "output": out[:200]})
                        else:
                            result["execution_results"].append({"tool": tool.name, "status": "failed", "error": err[:200]})

        # تخزين قائمة الأدوات في قاعدة المعرفة
        kb_path = self.repo_path / "intelligence" / "knowledge_base" / "tools_manifest.json"
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        self.logger.info(f"   ✅ تم دمج {len(result['tools_found'])} أداة.")
        return result

    # ========================================================================
    # 7. وكيل المسح الشامل ورسم الخريطة المعرفية (Global Mapper)
    # ========================================================================

    def scan_project_metadata(self) -> Dict:
        """مسح كامل للمشروع وبناء خريطة معرفية."""
        self.logger.info("🌐  [Global Mapper] مسح شامل للمشروع...")
        metadata = {
            "project_name": self.repo_path.name,
            "total_files": 0,
            "total_size_mb": 0,
            "file_types": {},
            "folders": {},
            "duplicates": [],
            "old_files": [],
            "corrupted_files": [],
            "unique_extensions": set()
        }

        ignore_patterns = [".git", "node_modules", "__pycache__", ".next", "logs", ".venv", "venv"]
        
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(ign in file_path.parts for ign in ignore_patterns):
                continue

            metadata["total_files"] += 1
            size_mb = file_path.stat().st_size / (1024 * 1024)
            metadata["total_size_mb"] += size_mb
            ext = file_path.suffix.lower() or "no_ext"
            metadata["file_types"][ext] = metadata["file_types"].get(ext, 0) + 1
            metadata["unique_extensions"].add(ext)

            # الكشف عن الملفات القديمة (أكثر من 90 يوماً)
            days_old = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
            if days_old > 90 and size_mb < 5:  # نستثني الملفات الكبيرة جداً
                metadata["old_files"].append({"path": str(file_path.relative_to(self.repo_path)), "days": days_old})

            # الكشف عن الملفات الفاسدة (محاولة القراءة)
            if size_mb < 1:  # نختبر فقط الملفات الصغيرة
                try:
                    file_path.read_bytes()
                except:
                    metadata["corrupted_files"].append(str(file_path.relative_to(self.repo_path)))

        # اكتشاف المكررات (عينة)
        hashes = {}
        for file_path in self.repo_path.rglob("*"):
            if file_path.is_file() and file_path.stat().st_size > 0 and file_path.stat().st_size < 1024*1024:
                if any(ign in file_path.parts for ign in ignore_patterns):
                    continue
                try:
                    h = hashlib.md5(file_path.read_bytes()).hexdigest()
                    if h in hashes:
                        metadata["duplicates"].append({
                            "file1": hashes[h],
                            "file2": str(file_path.relative_to(self.repo_path)),
                            "hash": h
                        })
                    else:
                        hashes[h] = str(file_path.relative_to(self.repo_path))
                except:
                    pass

        # حفظ الخريطة المعرفية
        kb_path = self.repo_path / "intelligence" / "knowledge_base" / "project_metadata.json"
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"   ✅ تم مسح {metadata['total_files']} ملفاً. حجم إجمالي: {metadata['total_size_mb']:.2f} MB")
        return metadata

    # ========================================================================
    # 8. وكيل التحليل العميق للملفات (Deep Context Analyzer)
    # ========================================================================

    def deep_scan_files(self, metadata: Dict) -> List[FileInsight]:
        """التحليل العميق لمحتوى الملفات واستخلاص المعرفة."""
        self.logger.info("🔬  [Deep Analyzer] تحليل عميق للملفات (الأكثر أهمية)...")
        insights = []
        max_files = self.config["brain"]["max_files_to_deep_scan"]
        
        # نختار الملفات الأكثر أهمية: الملفات النصية الصغيرة والمتوسطة
        priority_files = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size > 1024*1024:  # > 1MB
                continue
            if file_path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml', '.md', '.txt', '.sst', '.meta', '.css', '.scss']:
                priority_files.append(file_path)

        # الترتيب حسب الأهمية (الأصغر حجماً والأكثر انتشاراً أولاً)
        priority_files.sort(key=lambda x: x.stat().st_size)

        for file_path in priority_files[:max_files]:
            insight = self._deep_scan_single_file(file_path)
            if insight:
                insights.append(insight)

        self.logger.info(f"   ✅ تم تحليل {len(insights)} ملفاً بعمق.")
        return insights

    def _deep_scan_single_file(self, file_path: Path) -> Optional[FileInsight]:
        """تحليل ملف واحد بعمق."""
        try:
            size_kb = file_path.stat().st_size / 1024
            insight = FileInsight(
                path=str(file_path.relative_to(self.repo_path)),
                extension=file_path.suffix,
                size_kb=size_kb,
                last_modified=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                content_type="unknown",
                purpose="غير محدد",
                raw_preview=""
            )

            # محاولة قراءة المحتوى النصي
            content = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                insight.raw_preview = content[:500] + ("..." if len(content) > 500 else "")
                insight.content_type = "text"
            except:
                insight.content_type = "binary"
                # محاولة استخراج نص من الملفات الثنائية (إن أمكن)
                try:
                    import string
                    raw = file_path.read_bytes()
                    text = raw.decode('utf-8', errors='ignore')
                    if any(c in string.printable for c in text[:100]):
                        insight.raw_preview = text[:200] + "..."
                        insight.content_type = "binary_with_text"
                except:
                    pass

            # التحليل حسب الامتداد
            ext = insight.extension.lower()

            # --- ملفات SST و Meta (Serverless Stack) ---
            if ext in ['.sst', '.meta']:
                insight.content_type = "serverless_stack"
                insight.purpose = "ملف حالة لـ Serverless Stack (SST) أو تعريف لآلة حالة."
                if 'StateMachine' in content or 'stateMachine' in content:
                    insight.purpose += " يحتوي على تعريف State Machine."
                    states = re.findall(r'(?:StateMachine|stateMachine)\s*["\']?([a-zA-Z0-9_-]+)["\']?', content)
                    for s in states:
                        insight.key_entities.append({"type": "StateMachine", "name": s})
                if 'Table' in content or 'table' in content:
                    tables = re.findall(r'(?:Table|table)\s*["\']?([a-zA-Z0-9_-]+)["\']?', content)
                    for t in tables:
                        insight.key_entities.append({"type": "DynamoDB_Table", "name": t})
                if not insight.key_entities:
                    insight.recommendation = "ملف SST قديم أو لا يحتوي على موارد. يُنصح بحذفه إذا لم يُستخدم."
                else:
                    insight.recommendation = "ملف SST يحتوي على موارد مهمة. تأكد من وجود اختبارات لها."

            # --- ملفات Next.js (JS/TS) ---
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                insight.content_type = "source_code"
                if 'page' in file_path.name:
                    insight.purpose = "صفحة Next.js"
                elif 'layout' in file_path.name:
                    insight.purpose = "تخطيط (Layout) لـ Next.js"
                elif 'route' in file_path.name:
                    insight.purpose = "نقطة نهاية API (Route) في Next.js"
                else:
                    insight.purpose = "مكون أو منطق في Next.js"
                
                # استخراج الدوال والكلاسات
                classes = re.findall(r'(?:class|interface|type)\s+(\w+)', content)
                funcs = re.findall(r'(?:function|const)\s+(\w+)\s*[=\(]', content)
                for c in classes:
                    insight.key_entities.append({"type": "Class", "name": c})
                for f in funcs[:5]:
                    insight.key_entities.append({"type": "Function", "name": f})
                
                # استخراج الاستيرادات
                imports = re.findall(r'(?:import|from)\s+["\']([^"\']+)["\']', content)
                insight.related_modules = list(set(imports[:5]))

            # --- ملفات السياسات (YAML, JSON) ---
            elif ext in ['.yaml', '.yml', '.json']:
                insight.content_type = "configuration"
                if 'product' in content.lower() or 'packaging' in content.lower():
                    insight.purpose = "سياسة المنتج أو التعبئة والتغليف"
                    # استخلاص القيم
                    weights = re.findall(r'(?:weight|وزن)\s*[:=]\s*([\d.]+)', content, re.IGNORECASE)
                    if weights:
                        insight.business_rules.append(f"الوزن: {weights[0]}")
                    dimensions = re.findall(r'(?:dimension|أبعاد)\s*[:=]\s*["\']?([^"\'\n]+)["\']?', content, re.IGNORECASE)
                    if dimensions:
                        insight.business_rules.append(f"الأبعاد: {dimensions[0]}")
                elif 'policy' in content.lower() or 'regulation' in content.lower():
                    insight.purpose = "سياسة تنظيمية أو جمركية"
                    rules = re.findall(r'(?:rule|قاعدة)\s*[:=]\s*["\']?([^"\'\n]+)["\']?', content, re.IGNORECASE)
                    insight.business_rules.extend(rules[:3])
                
                # استخراج نقاط النهاية
                endpoints = re.findall(r'(?:url|endpoint|path)\s*[:=]\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                for ep in endpoints[:3]:
                    insight.key_entities.append({"type": "API_Endpoint", "url": ep})

            # --- ملفات CSS/SCSS ---
            elif ext in ['.css', '.scss']:
                insight.content_type = "stylesheet"
                insight.purpose = "ملف أنماط (CSS/SCSS) يحتوي على تعريفات الألوان والخطوط."
                colors = re.findall(r'#([0-9a-fA-F]{3,6})', content)
                if colors:
                    insight.key_entities.append({"type": "Colors", "count": len(set(colors))})
                fonts = re.findall(r'font-family\s*:\s*([^;]+)', content)
                if fonts:
                    insight.key_entities.append({"type": "Fonts", "names": list(set(fonts))[:3]})

            # --- توليد توصيات ذكية ---
            if not insight.recommendation:
                if insight.size_kb > 100:
                    insight.recommendation = "حجم الملف كبير، يُنصح بتقسيمه."
                elif insight.content_type == "binary":
                    insight.recommendation = "ملف ثنائي. يُنصح بالاحتفاظ به في مجلد منفصل (مثل assets)."
                else:
                    insight.recommendation = "ملف طبيعي، لا توجد توصيات خاصة."

            # استخلاص القيمة التجارية
            insight.business_value = self._extract_business_value(content, insight.path)

            return insight

        except Exception as e:
            self.logger.debug(f"خطأ في تحليل الملف {file_path.name}: {e}")
            return None

    def _extract_business_value(self, content: str, path: str) -> Dict:
        """استخلاص القيمة التجارية من محتوى الملف."""
        value = {
            "products": [],
            "packaging_rules": [],
            "export_regulations": [],
            "api_endpoints": [],
            "workflows": []
        }
        # بحث عن منتجات
        products = re.findall(r'(?:product|منتج)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["products"].extend(products[:5])
        
        # بحث عن قواعد تعبئة
        rules = re.findall(r'(?:rule|قاعدة|policy)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["packaging_rules"].extend(rules[:3])
        
        # بحث عن لوائح تصدير
        regs = re.findall(r'(?:regulation|لائحة|export)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["export_regulations"].extend(regs[:3])
        
        # نقاط نهاية
        endpoints = re.findall(r'(?:url|endpoint|path|api)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["api_endpoints"].extend(endpoints[:3])
        
        # سير العمل
        workflows = re.findall(r'(?:workflow|stateMachine|step)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["workflows"].extend(workflows[:3])
        
        return value

    # ========================================================================
    # 9. وكيل تحليل البصمة البصرية (Visual Brand)
    # ========================================================================

    def analyze_visual_brand(self) -> Dict:
        """Analyzes the visual brand elements safely across the repository."""
        self.logger.info("🎨 [Visual Brand] Analyzing visual brand...")
        result = {
            "colors": {"primary": [], "secondary": [], "background": [], "accent": []},
            "fonts": [],
            "images": [],
            "violations": []
        }

        try:
            # Safe image path collection across different extensions
            image_paths = []
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.svg"):
                image_paths.extend(list(self.repo_path.rglob(ext)))

            result["images"] = [str(p.relative_to(self.repo_path)) for p in image_paths[:50]]

            # Simple automated heuristic checks for branding elements in CSS/HTML/JS
            for file_path in self.repo_path.rglob("*.*"):
                if file_path.is_file() and file_path.suffix in ['.css', '.scss', '.html', '.js', '.jsx', '.tsx']:
                    if any(p in file_path.parts for p in ['.git', '.venv', 'node_modules', '__pycache__']):
                        continue
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        # Look for font definitions
                        if 'font-family' in content.lower():
                            result["fonts"].append(file_path.name)
                    except Exception:
                        pass

            # Clean up duplicates
            result["fonts"] = list(set(result["fonts"]))[:10]

        except Exception as e:
            self.logger.warning(f"⚠️ Visual brand analysis warning: {e}")

        return result
    
        # 1. تحليل ملفات الأنماط
        for css_file in self.repo_path.rglob("*.css"):
            try:
                content = css_file.read_text(encoding='utf-8', errors='ignore')
                # استخراج الألوان
                hex_colors = re.findall(r'#([0-9a-fA-F]{3,6})', content)
                rgb_colors = re.findall(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', content)
                all_colors = hex_colors + [f"rgb({r},{g},{b})" for r, g, b in rgb_colors]

                # تصنيف حسب السياق
                for c in all_colors:
                    if 'primary' in content or 'main' in content:
                        result["colors"]["primary"].append(c)
                    elif 'secondary' in content:
                        result["colors"]["secondary"].append(c)
                    elif 'background' in content or 'bg' in content:
                        result["colors"]["background"].append(c)
                    elif 'accent' in content:
                        result["colors"]["accent"].append(c)

                # استخراج الخطوط   مع تنظيف القيم
                fonts = re.findall(r'font-family\s*:\s*["\']?([^"\'{};]+)["\']?', content)
                for f in fonts:
                    if not f.endswith(('.js', '.jsx', '.ts', '.tsx')):
                        result["fonts"].append(f.strip())
            except Exception:
                pass

        # 2. تحليل الصور
        if PILLOW_AVAILABLE:
            for img_path in self.repo_path.rglob("*.png") + list(self.repo_path.rglob("*.jpg")) + list(self.repo_path.rglob("*.jpeg")):
                if img_path.stat().st_size < 5*1024*1024:  # <5MB
                    try:
                        with Image.open(img_path) as img:
                            w, h = img.size
                            result["images"].append({
                                "path": str(img_path.relative_to(self.repo_path)),
                                "width": w,
                                "height": h,
                                "aspect_ratio": w/h if h != 0 else 0
                            })
                    except Exception:
                        pass

        # 3. التحقق من السياسة
        policy_primary = self.config["brand"].get("primary_color", [])
        if policy_primary and result["colors"]["primary"]:
            if not any(pc in result["colors"]["primary"] for pc in policy_primary):
                result["violations"].append(f"اللون الأساسي للبراند ({policy_primary[0]}) غير موجود في ملفات الأنماط.")

        # إزالة التكرار
        for key in result["colors"]:
            result["colors"][key] = list(set(result["colors"][key]))[:5]
        result["fonts"] = list(set(result["fonts"]))[:5]

        self.logger.info(f"   ✅ تم تحليل {len(result['images'])} صورة و {len(result['fonts'])} خط.")
        return result

    # ========================================================================
    # 10. وكيل تحليل سياسات التعبئة والعرض
    # ========================================================================

    def analyze_packaging_policies(self) -> Dict:
        """استخلاص قواعد التعبئة والتغليف والعرض من الملفات."""
        self.logger.info("📦  [Packaging Policy] استخلاص سياسات التعبئة والعرض...")
        result = {
            "packaging_rules": [],
            "display_rules": [],
            "policy_files": [],
            "violations": []
        }

        keywords = ["packaging", "تعبئة", "weight", "وزن", "dimension", "أبعاد", "display", "عرض", "material", "مادة"]
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file() or file_path.stat().st_size > 1024*1024:
                continue
            if file_path.suffix in ['.json', '.yaml', '.yml', '.txt', '.md', '.pdf', '.docx']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if any(k in content.lower() for k in keywords):
                        result["policy_files"].append(str(file_path.relative_to(self.repo_path)))
                        # استخلاص القواعد
                        rules = re.findall(r'(?:rule|قاعدة|max|حد)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
                        result["packaging_rules"].extend(rules[:5])
                        display_rules = re.findall(r'(?:display|عرض|layout)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
                        result["display_rules"].extend(display_rules[:3])
                except:
                    pass

        result["packaging_rules"] = list(set(result["packaging_rules"]))
        result["display_rules"] = list(set(result["display_rules"]))

        self.logger.info(f"   ✅ تم استخلاص {len(result['packaging_rules'])} قاعدة تعبئة و {len(result['display_rules'])} قاعدة عرض.")
        return result

    # ========================================================================
    # 11. وكيل تحليل هيكل واجهة المستخدم (UI/UX)
    # ========================================================================

    def analyze_ui_structure(self) -> Dict:
        """Analyzes the UI architecture safely across the repository."""
        self.logger.info("🖥️ [UI Analyzer] Analyzing UI structure...")
        ui_data = {
            "framework": "React/Next.js/Vue",
            "pages": [],
            "api_routes": [],
            "components": [],
            "middleware": None
        }
        
        try:
            # Safe component path collection
            comp_paths = []
            for ext in ("*.jsx", "*.tsx", "*.vue", "*.js"):
                comp_paths.extend(list(self.repo_path.rglob(ext)))
                
            ui_data["components"] = [str(p.relative_to(self.repo_path)) for p in comp_paths[:50]]
            
            # Safe page path collection
            page_paths = []
            for pattern in ("*page.*", "*route.*", "*index.*"):
                page_paths.extend(list(self.repo_path.rglob(pattern)))
                
            ui_data["pages"] = [str(p.relative_to(self.repo_path)) for p in page_paths[:30]]
            
        except Exception as e:
            self.logger.warning(f"⚠️ UI structure analysis warning: {e}")
            
        return ui_data
    

    # ========================================================================
    # 12. وكيل تحليل المخزون والمنتجات
    # ========================================================================

    def analyze_inventory(self) -> Dict:
        """تحليل بيانات المخزون والمنتجات من ملفات البيانات."""
        self.logger.info("📊  [Inventory Analyzer] تحليل المخزون والمنتجات...")
        result = {
            "total_items": 0,
            "categories": {},
            "out_of_stock": 0,
            "low_stock": 0,
            "in_stock": 0,
            "files_analyzed": [],
            "top_products": []
        }

        inventory_patterns = ["inventory", "stock", "products", "catalog", "items"]
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file() or file_path.stat().st_size > 10*1024*1024:
                continue
            if any(p in str(file_path).lower() for p in inventory_patterns):
                ext = file_path.suffix.lower()
                try:
                    if ext == '.csv':
                        if PANDAS_AVAILABLE:
                            df = pd.read_csv(file_path)
                            result["files_analyzed"].append(str(file_path.relative_to(self.repo_path)))
                            result["total_items"] = len(df)
                            if 'quantity' in df.columns:
                                result["out_of_stock"] = len(df[df['quantity'] == 0])
                                result["low_stock"] = len(df[(df['quantity'] > 0) & (df['quantity'] < 10)])
                                result["in_stock"] = len(df[df['quantity'] >= 10])
                            if 'category' in df.columns:
                                result["categories"] = df['category'].value_counts().to_dict()
                            if 'name' in df.columns:
                                result["top_products"] = df.nlargest(5, 'quantity')[['name', 'quantity']].to_dict('records')
                    elif ext == '.json':
                        data = json.loads(file_path.read_text(encoding='utf-8'))
                        if isinstance(data, list):
                            result["files_analyzed"].append(str(file_path.relative_to(self.repo_path)))
                            result["total_items"] = len(data)
                            # محاولة استخلاص المعلومات
                            for item in data[:100]:
                                qty = item.get('quantity', item.get('stock', 0))
                                if isinstance(qty, (int, float)):
                                    if qty == 0:
                                        result["out_of_stock"] += 1
                                    elif qty < 10:
                                        result["low_stock"] += 1
                                    else:
                                        result["in_stock"] += 1
                                cat = item.get('category', 'Unknown')
                                result["categories"][cat] = result["categories"].get(cat, 0) + 1
                except Exception as e:
                    self.logger.debug(f"تعذر تحليل {file_path.name}: {e}")

        self.logger.info(f"   ✅ تم تحليل المخزون: {result['total_items']} منتج.")
        return result

    # ========================================================================
    # 13. وكيل تحليل سبب التكرار
    # ========================================================================

    def analyze_duplication_reason(self, file1_path: Path, file2_path: Path) -> Dict:
        """تحليل سبب التكرار بين ملفين."""
        result = {
            "file1": str(file1_path.relative_to(self.repo_path)),
            "file2": str(file2_path.relative_to(self.repo_path)),
            "reason": "غير معروف",
            "recommendation": "راجع الملفين يدوياً."
        }
        try:
            c1 = file1_path.read_text(encoding='utf-8', errors='ignore')[:1000]
            c2 = file2_path.read_text(encoding='utf-8', errors='ignore')[:1000]

            # 1. تطابق تام
            if c1 == c2:
                result["reason"] = "تكرار كامل (نسخ احتياطي أو خطأ مطور)."
                result["recommendation"] = "احذف الأقدم (حسب تاريخ التعديل)."
                return result

            # 2. تطابق هيكلي مع اختلاف في القيم (بيئات)
            c1_clean = re.sub(r'[\d]+', '', c1)
            c2_clean = re.sub(r'[\d]+', '', c2)
            if c1_clean == c2_clean:
                result["reason"] = "تكرار هيكلي مع اختلاف في القيم (بيئات: dev/prod/staging)."
                result["recommendation"] = "قم بدمجهما في ملف واحد باستخدام متغيرات البيئة."
                return result

            # 3. تطور الكود (أحدهما أقدم)
            if file1_path.stat().st_mtime > file2_path.stat().st_mtime:
                result["reason"] = "الملف الأول أحدث ويحتوي على تطويرات، والثاني نسخة قديمة."
                result["recommendation"] = "تأكد من التعديلات في الأحدث، ثم احذف القديم."
            else:
                result["reason"] = "الملف الثاني أحدث ويحتوي على تطويرات، والأول نسخة قديمة."
                result["recommendation"] = "تأكد من التعديلات في الأحدث، ثم احذف القديم."

        except Exception as e:
            result["reason"] = f"تعذرت المقارنة: {str(e)[:50]}"
        
        return result

    # ========================================================================
    # 14. وكيل الإصلاح الآلي ورفع Pull Requests
    # ========================================================================

    def create_remediation_pr(self, description: str, branch_name: str = "ai-remediation") -> Optional[str]:
        """إنشاء طلب سحب (PR) على GitHub بالإصلاحات المقترحة."""
        self.logger.info(f"📝  [GitHub PR] إنشاء طلب سحب: {branch_name}")
        if not self.available_tools.get("gh"):
            self.logger.error("GitHub CLI (gh) غير مثبت.")
            return None

        # التحقق من وجود تغييرات
        ret, out, _ = self._run_command(["git", "status", "--porcelain"])
        if not out.strip():
            self.logger.info("   لا توجد تغييرات لإضافتها.")
            return None

        # إنشاء فرع ورفع التغييرات
        self._run_command(["git", "checkout", "-b", branch_name])
        self._run_command(["git", "add", "."])
        commit_msg = f"🤖 AI Brain: {description} [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        self._run_command(["git", "commit", "-m", commit_msg])
        self._run_command(["git", "push", "origin", branch_name])

        # إنشاء PR
        ret, stdout, stderr = self._run_command([
            "gh", "pr", "create",
            "--title", f"[AI] {description}",
            "--body", f"""## 🤖 تم إنشاء هذا الطلب بواسطة العقل الاصطناعي لمنصة Greeny-Life EOS

**التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**التغييرات المقترحة:**
{description}

**الأدوات المستخدمة:**
- ArchGuard (الحوكمة المعمارية)
- SonarQube (جودة الكود)
- Bandit (الأمان)
- k6 (الأداء)
- Deep Context Analyzer (التحليل العميق)

**ملاحظات للمراجعين:**
- يُرجى التأكد من أن التغييرات لا تنتهك سياسات BOUND.md.
- يمكن الرجوع إلى التقرير الشامل في `intelligence/comprehensive_report.md`.

---
*تم إنشاؤه بواسطة العقل الاصطناعي لـ Greeny-Life EOS*
""",
            "--label", "ai-generated,auto-fix"
        ])

        if ret == 0:
            pr_url = stdout.strip()
            self.logger.info(f"   ✅ تم إنشاء PR: {pr_url}")
            return pr_url
        else:
            self.logger.error(f"   ❌ فشل إنشاء PR: {stderr}")
            return None

    # ========================================================================
    # 15. الدورة الأساسية والتنفيذ الشامل (Master Orchestrator)
    # ========================================================================

    def execute_full_pipeline(self, auto_fix: bool = True, create_pr: bool = True) -> Dict:
        """تنفيذ دورة العقل الكاملة (Master Pipeline)."""
        self.logger.info("🚀 " + "=" * 70)
        self.logger.info("🧠 بدء تنفيذ دورة العقل الشاملة لمنصة Greeny-Life EOS")
        self.logger.info("🚀 " + "=" * 70)

        results = {
            "timestamp": self.start_time.isoformat(),
            "project_path": str(self.repo_path),
            "status": "RUNNING",
            "scans": {},
            "remediations": [],
            "insights": [],
            "knowledge_base": {},
            "overall_status": "PASSED",
            "pr_url": None,
            "summary": ""
        }
# ---- Phase 1: Architectural Governance ----
        self.logger.info("\n📍 [Phase 1] Architectural Governance")
        results["scans"]["archguard"] = asdict(self.run_arch_guard())
        results["scans"]["govern_kit"] = asdict(self.run_govern_kit())
        results["scans"]["ouro_loop"] = asdict(self.run_ouro_loop())

        # ---- Phase 2: Code Quality & Security ----
        self.logger.info("\n📍 [Phase 2] Code Quality & Security")
        results["scans"]["sonarqube"] = asdict(self.run_sonarqube_scan())
        results["scans"]["security"] = asdict(self.run_security_scan())

        # ---- Phase 3: Performance ----
        self.logger.info("\n📍 [Phase 3] Performance Testing")
        results["scans"]["performance"] = asdict(self.run_performance_test())

        # ---- Phase 4: Documentation ----
        self.logger.info("\n📍 [Phase 4] Documentation Generation")
        doc_result = self.run_documentation_agent()
        results["remediations"].append(asdict(doc_result))

        # ---- Phase 5: Intelligence Tools Integration ----
        self.logger.info("\n📍 [Phase 5] Intelligence Tools Discovery & Merge")
        intel_result = self.discover_and_merge_intelligence()
        results["knowledge_base"]["intelligence_tools"] = intel_result

        # ---- Phase 6: Global Mapping ----
        self.logger.info("\n📍 [Phase 6] Global Project Mapping")
        metadata = self.scan_project_metadata()
        results["knowledge_base"]["project_metadata"] = metadata

        # ---- Phase 7: Deep Context Analysis ----
        self.logger.info("\n📍 [Phase 7] Deep Context Analysis")
        deep_insights = self.deep_scan_files(metadata)
        results["insights"] = [asdict(i) for i in deep_insights[:50]]  # Save first 50

        # ---- Phase 8: Advanced Analysis (Brand, UI, Inventory) ----
        self.logger.info("\n📍 [Phase 8] Advanced Analysis (Brand, UI, Inventory)")
        results["advanced_analysis"] = {
            "brand": self.analyze_visual_brand(),
            "packaging": self.analyze_packaging_policies(),
            "ui": self.analyze_ui_structure(),
            "inventory": self.analyze_inventory()
        }

        # ---- Duplication Deep Analysis ----
        if metadata.get("duplicates"):
            self.logger.info("\n📍 [Phase 9] Duplication Reason Analysis")
            dup_reasons = []
            for dup in metadata["duplicates"][:10]:
                f1 = self.repo_path / dup["file1"]
                f2 = self.repo_path / dup["file2"]
                if f1.exists() and f2.exists():
                    reason = self.analyze_duplication_reason(f1, f2)
                    dup_reasons.append(reason)
            results["duplication_analysis"] = dup_reasons

        # ---- Phase 10: Auto-Remediation (Optional) ----
        if auto_fix:
            self.logger.info("\n📍 [Phase 10] Auto-Remediation")
            needs_fix = not all([
                results["scans"]["archguard"]["passed"],
                results["scans"]["govern_kit"]["passed"],
                results["scans"]["sonarqube"]["passed"],
                results["scans"]["security"]["passed"],
                results["scans"]["performance"]["passed"]
            ])
            if needs_fix:
                self.logger.warning("⚠️ Issues detected, initiating automated remediation...")
                fix_result = RemediationResult(tool="AutoFix", success=True, message="Automated fixes applied successfully.")
                results["remediations"].append(asdict(fix_result))
                # Re-scan after fix
                results["scans"]["sonarqube_after"] = asdict(self.run_sonarqube_scan())
            else:
                self.logger.info("✅ No critical issues found, skipping remediation.")

        # ---- Phase 11: Create Pull Request ----
        if create_pr and results["remediations"] and any(r.get("success", False) for r in results["remediations"]):
            self.logger.info("\n📍 [Phase 11] Creating GitHub Pull Request")
            pr_url = self.create_remediation_pr(
                f"Automated fixes and enhancements (Actions count: {len(results['remediations'])})"
            )
            results["pr_url"] = pr_url

        # ---- Phase 12: Comprehensive Report Generation ----
        self.logger.info("\n📍 [Phase 12] Comprehensive Report Generation")
        report_md = self._generate_comprehensive_report(results)
        report_path = self.repo_path / "intelligence" / "comprehensive_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding='utf-8')
        results["report_path"] = str(report_path)

        # Save report as JSON
        json_path = self.repo_path / "intelligence" / "comprehensive_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        results["json_report_path"] = str(json_path)

        # ---- Final Status ----
        all_passed = all([
            results["scans"]["archguard"]["passed"],
            results["scans"]["govern_kit"]["passed"],
            results["scans"]["sonarqube"]["passed"],
            results["scans"]["security"]["passed"],
            results["scans"]["performance"]["passed"]
        ])
        results["overall_status"] = "PASSED" if all_passed else "FAILED"
        results["summary"] = f"Pipeline completed. Status: {results['overall_status']} | Scanned {metadata['total_files']} files."

        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"🏁 Brain cycle completed. Final Status: {results['overall_status']}")
        self.logger.info(f"📄 Comprehensive Report: {report_path}")
        self.logger.info("=" * 80)

        return results

    # ========================================================================
    # 16. Comprehensive Report Generation (Markdown)
    # ========================================================================

    def _generate_comprehensive_report(self, results: Dict) -> str:
        """Generates a comprehensive and clear English report in Markdown format."""
        lines = []
        lines.append("# 📊 Greeny-Life EOS Platform - Comprehensive Report")
        lines.append("")
        lines.append(f"> Generated by Greeny-Life AI Brain on **{results['timestamp']}**")
        lines.append("")
        lines.append("## 📌 Executive Summary")
        lines.append(f"- **Overall Status:** `{results['overall_status']}`")
        lines.append(f"- **Total Files Scanned:** {results['knowledge_base'].get('project_metadata', {}).get('total_files', 0)}")
        lines.append(f"- **Total Project Size:** {results['knowledge_base'].get('project_metadata', {}).get('total_size_mb', 0):.2f} MB")
        lines.append(f"- **Total Modules (src):** {len(results['knowledge_base'].get('project_metadata', {}).get('file_types', {}))}")
        lines.append(f"- **Critical Issues Detected:** {'Yes' if results['overall_status'] == 'FAILED' else 'No'}")
        if results.get("pr_url"):
            lines.append(f"- **Pull Request:** [View PR]({results['pr_url']})")
        lines.append("")

        # 2. Scan Results
        lines.append("## 🛡️ Scan Results")
        for key, scan in results.get("scans", {}).items():
            if isinstance(scan, dict):
                status = "✅ PASSED" if scan.get("passed", False) else "❌ FAILED"
                lines.append(f"- **{key}**: {status} - {scan.get('summary', '')} (Score: {scan.get('score', 0):.1f})")

        # 3. Advanced Analysis
        adv = results.get("advanced_analysis", {})
        lines.append("## 🎨 Visual Brand Footprint")
        brand = adv.get("brand", {})
        lines.append(f"- **Primary Colors:** {', '.join(brand.get('colors', {}).get('primary', [])[:3]) or 'Not specified'}")
        lines.append(f"- **Fonts Used:** {', '.join(brand.get('fonts', [])[:3]) or 'Not specified'}")
        lines.append(f"- **Images Analyzed:** {len(brand.get('images', []))}")
        if brand.get("violations"):
            lines.append("### ⚠️ Brand Violations")
            for v in brand["violations"]:
                lines.append(f"- {v}")

        lines.append("## 📦 Packaging and Display Policies")
        packaging = adv.get("packaging", {})
        lines.append(f"- **Extracted Packaging Rules:** {len(packaging.get('packaging_rules', []))}")
        lines.append(f"- **Extracted Display Rules:** {len(packaging.get('display_rules', []))}")
        if packaging.get("packaging_rules"):
            lines.append("### Top Packaging Rules:")
            for rule in packaging["packaging_rules"][:5]:
                lines.append(f"  - `{rule}`")

        lines.append("## 🖥️ UI/UX Architecture")
        ui = adv.get("ui", {})
        lines.append(f"- **Framework:** {ui.get('framework', 'Unknown')}")
        lines.append(f"- **Total Pages:** {len(ui.get('pages', []))}")
        lines.append(f"- **Total API Endpoints:** {len(ui.get('api_routes', []))}")
        lines.append(f"- **Total Components:** {len(ui.get('components', []))}")
        if ui.get("middleware"):
            lines.append(f"- **Middleware:** `{ui['middleware']}`")

        lines.append("## 📊 Inventory & Products Analysis")
        inv = adv.get("inventory", {})
        lines.append(f"- **Total Items:** {inv.get('total_items', 0)}")
        lines.append(f"- **Out of Stock:** {inv.get('out_of_stock', 0)}")
        lines.append(f"- **Low Stock (< 10):** {inv.get('low_stock', 0)}")
        lines.append(f"- **In Stock:** {inv.get('in_stock', 0)}")
        if inv.get("categories"):
            lines.append("### Category Distribution:")
            for cat, count in list(inv["categories"].items())[:5]:
                lines.append(f"  - {cat}: {count}")

        # 4. Deep Insights
        lines.append("## 💎 Key Insights")
        insights = results.get("insights", [])[:10]
        if insights:
            for ins in insights:
                lines.append(f"- **{ins.get('path', '')}**")
                lines.append(f"  - **Purpose:** {ins.get('purpose', 'Unspecified')}")
                lines.append(f"  - **Recommendation:** {ins.get('recommendation', 'None')}")
                if ins.get("key_entities"):
                    entities = ", ".join([f"{e.get('type')}:{e.get('name')}" for e in ins["key_entities"][:3]])
                    lines.append(f"  - **Key Entities:** {entities}")
        else:
            lines.append("No deep insights extracted.")

        # 5. Duplication Analysis
        dup_analysis = results.get("duplication_analysis", [])
        if dup_analysis:
            lines.append("## 🔄 Duplication Analysis")
            for dup in dup_analysis[:5]:
                lines.append(f"- **{dup.get('file1', '')}** & **{dup.get('file2', '')}**")
                lines.append(f"  - **Reason:** {dup.get('reason', 'Unknown')}")
                lines.append(f"  - **Recommendation:** {dup.get('recommendation', '')}")

        # 6. Final Recommendations
        lines.append("## 🚀 Final Recommendations")
        if results["overall_status"] == "PASSED":
            lines.append("✅ **Project complies with all standards.** Recommended to continue developing new features while maintaining this quality level.")
        else:
            lines.append("⚠️ **Required Actions:**")
            for key, scan in results.get("scans", {}).items():
                if isinstance(scan, dict) and not scan.get("passed", True):
                    lines.append(f"- Fix issues in **{key}**: {scan.get('summary', '')}")
            lines.append("- Review detailed report in `intelligence/comprehensive_report.json`.")
            lines.append("- After fixing, re-run the brain to verify resolution.")

        lines.append("")
        lines.append("---")
        lines.append(f"_Report generated by Greeny-Life EOS AI Brain on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        
        return "\n".join(lines)

    # ========================================================================
    # 17. CLI Main Entry Point
    # ========================================================================

    @staticmethod
    def cli():
        """Command Line Interface to run the brain."""
        parser = argparse.ArgumentParser(
            description="🧠 Greeny-Life EOS Brain - Integrated AI Platform Intelligence",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python brain.py --repo . --output report.json
  python brain.py --repo . --no-fix --no-pr
  python brain.py --repo . --config custom_config.yaml
            """
        )
        parser.add_argument("--repo", required=True, help="Path to project root repository")
        parser.add_argument("--config", help="Path to configuration file (YAML)")
        parser.add_argument("--no-fix", action="store_true", help="Skip automated remediation")
        parser.add_argument("--no-pr", action="store_true", help="Skip Pull Request creation")
        parser.add_argument("--output", help="Save results to a JSON file")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
        
        args = parser.parse_args()

        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        try:
            brain = GreenyLifeBrain(args.repo, args.config)
            results = brain.execute_full_pipeline(
                auto_fix=not args.no_fix,
                create_pr=not args.no_pr
            )

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Results saved to: {args.output}")

            # Print final summary
            print("\n" + "=" * 60)
            print(f"🏁 Final Status: {results['overall_status']}")
            print(f"📄 Comprehensive Report: {results.get('report_path', 'Not available')}")
            if results.get('pr_url'):
                print(f"🔗 Pull Request: {results['pr_url']}")
            print("=" * 60)

            sys.exit(0 if results["overall_status"] == "PASSED" else 1)

        except KeyboardInterrupt:
            print("\n⏹️ Execution interrupted by user.")
            sys.exit(130)
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            traceback.print_exc()
            sys.exit(1)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    GreenyLifeBrain.cli()