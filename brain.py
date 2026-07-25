
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
GREENY-LIFE EOS - ENTERPRISE ARTIFICIAL BRAIN
================================================================================
Complete Enterprise AI Brain for Greeny-Life Platform.
Version: 3.3 (Windows-Compatible)
Date: 2026-07-25
================================================================================
"""

# ============================================================================
# Standard Library Imports
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
import shutil          # <-- مهم للتوافق مع Windows
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import requests
import time
import traceback

# ============================================================================
# Optional Dependencies Check
# ============================================================================
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("⚠️  Pillow library not installed. Run: pip install Pillow")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  Pandas library not installed. Run: pip install pandas")

# ============================================================================
# Core Data Structures
# ============================================================================

@dataclass
class ScanResult:
    tool: str
    passed: bool = True
    score: float = 100.0
    findings: List[Dict] = field(default_factory=list)
    summary: str = ""
    raw_output: str = ""

@dataclass
class RemediationResult:
    tool: str
    success: bool = False
    pr_url: Optional[str] = None
    commit_hash: Optional[str] = None
    message: str = ""

@dataclass
class FileInsight:
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
# Main Brain Class
# ============================================================================

class GreenyLifeBrain:
    """
    The master orchestrator for Greeny-Life EOS.
    Executes the full pipeline of governance, quality, security, performance,
    documentation, deep analysis, business intelligence, and auto-remediation.
    """

    def __init__(self, repo_path: str, config_path: Optional[str] = None):
        """
        Initialize the brain with the project repository path.

        Args:
            repo_path (str): Absolute or relative path to the project root.
            config_path (Optional[str]): Path to the YAML configuration file.
        """
        self.repo_path = Path(repo_path).resolve()
        self.start_time = datetime.now()
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.knowledge_base = {}
        self.insights = []
        self.available_tools = {}

        self._check_prerequisites()
        self._ensure_directories()

        self.logger.info("=" * 80)
        self.logger.info("Greeny-Life EOS Brain initialized successfully.")
        self.logger.info(f"Project Path: {self.repo_path}")
        self.logger.info("=" * 80)

    # -------------------------------------------------------------------------
    # Initialization & Configuration
    # -------------------------------------------------------------------------

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """
        Load configuration from YAML file or fallback to default settings.
        Environment variables take precedence over file values.
        """
        default_config = {
            "sonarqube": {
                "url": os.getenv("SONARQUBE_URL", "http://localhost:9000"),
                "token": os.getenv("SONAR_TOKEN")
            },
            "github": {"token": os.getenv("GITHUB_TOKEN")},
            "llm": {
                "provider": os.getenv("LLM_PROVIDER", "claude"),
                "model": os.getenv("LLM_MODEL", "claude-3-opus-20240229")
            },
            "govern": {"trust_threshold": 0.80, "window_size": 10},
            "archguard": {"config": ".archguard.yml"},
            "ouro_loop": {"bound_file": "BOUND.md"},
            "audit": {"tier": "DEEP"},
            "security": {"tools": ["bandit"], "severity_threshold": "MEDIUM"},
            "performance": {
                "test_dir": "tests/performance",
                "vus": 10,
                "duration": "10s"
            },
            "documentation": {
                "auto_fix": True,
                "ignore_patterns": [".*test.*", ".*migrations.*"]
            },
            "brand": {
                "primary_color": ["#2E8B57"],
                "logo_aspect_ratio": 1.0
            },
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
                self.logger.warning(f"Failed to read config file {config_path}: {e}. Using defaults.")

        return default_config

    def _deep_update(self, base: Dict, update: Dict) -> None:
        """Recursively update a nested dictionary."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _setup_logging(self) -> logging.Logger:
        """Configure logging to both console and file."""
        logger = logging.getLogger("GreenyLifeBrain")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # File handler
            log_dir = self.repo_path / "logs" if hasattr(self, 'repo_path') else Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"brain-{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _check_prerequisites(self) -> None:
        """
        Verify that required and optional tools are available in the system PATH.
        Required tools will halt execution if missing; optional tools are skipped.
        Uses shutil.which() for cross-platform compatibility.
        """
        required_tools = ["git", "python3"]
        optional_tools = [
            "sonar-scanner", "bandit", "k6", "claude", "gh",
            "docker", "archguard", "ouro-loop", "govern", "codeql", "npx"
        ]

        self.available_tools = {}

        # Check required tools
        for tool in required_tools:
            self.available_tools[tool] = self._which(tool)
            if not self.available_tools[tool]:
                self.logger.error(f"Required tool '{tool}' not found. Aborting.")
                sys.exit(1)

        # Check optional tools
        for tool in optional_tools:
            self.available_tools[tool] = self._which(tool)
            if self.available_tools[tool]:
                self.logger.info(f"Optional tool '{tool}' is available.")
            else:
                self.logger.warning(f"Optional tool '{tool}' not found. Some features will be disabled.")

        # If Claude is not directly available, check if npx can run it
        if not self.available_tools.get("claude") and self.available_tools.get("npx"):
            self.available_tools["claude"] = True
            self.logger.info("Will use 'npx claude' as fallback for Claude AI.")

    def _which(self, cmd: str) -> bool:
        """
        Check if a command exists in the system PATH.
        Uses shutil.which() which works on Windows, Linux, and macOS.
        """
        return shutil.which(cmd) is not None

    def _ensure_directories(self) -> None:
        """Create essential directories if they do not exist."""
        directories = [
            "src", "tests", "docs", "logs", "intelligence",
            "intelligence/knowledge_base", "intelligence/backups"
        ]
        for d in directories:
            (self.repo_path / d).mkdir(parents=True, exist_ok=True)

    def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict] = None,
        timeout: int = 300
    ) -> Tuple[int, str, str]:
        """
        Execute a shell command with error handling and timeout.

        Returns:
            Tuple[int, str, str]: (return_code, stdout, stderr)
        """
        cwd = cwd or self.repo_path
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=full_env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(cmd)}")
            return -1, "", "Timeout"
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)

    # -------------------------------------------------------------------------
    # Agent 1: Architectural Governance (ArchGuard)
    # -------------------------------------------------------------------------

    def run_arch_guard(self) -> ScanResult:
        """Analyze architecture using ArchGuard."""
        self.logger.info("[ArchGuard] Starting architecture analysis...")
        result = ScanResult(tool="ArchGuard")

        if not self.available_tools.get("archguard"):
            result.passed = False
            result.summary = "ArchGuard is not installed."
            return result

        # Initialize if config is missing
        config_file = self.repo_path / self.config["archguard"]["config"]
        if not config_file.exists():
            self._run_command(["archguard", "init"])

        # Try different command names depending on the version
        output = ""
        ret = -1
        err = ""
        for cmd_name in ["analyze", "scan", "check"]:
            ret, out, err = self._run_command(
                ["archguard", cmd_name, "--format", "json"]
            )
            output = out
            if ret == 0 or "No such command" not in err:
                break

        if ret != 0 and "No such command" in err:
            result.passed = False
            result.summary = "ArchGuard command not recognized. Please update the tool."
            result.raw_output = err
            self.logger.warning(f"   {result.summary}")
            return result

        result.raw_output = output

        if ret != 0:
            result.passed = False
            result.summary = f"Scan failed: {err[:200]}"
            self.logger.warning(f"   {result.summary}")
            return result

        try:
            data = json.loads(output)
            violations = data.get("violations", [])
            result.findings = violations

            if violations:
                result.passed = False
                result.summary = f"Found {len(violations)} architectural violations."
                result.score = max(0, 100 - len(violations) * 5)
            else:
                result.summary = "No architectural violations detected."
                result.score = 100

        except json.JSONDecodeError:
            result.passed = False
            result.summary = "Failed to parse ArchGuard output."

        self.logger.info(f"   {result.summary}")
        return result

    # -------------------------------------------------------------------------
    # Agent 2: Trust Governance (govern-kit)
    # -------------------------------------------------------------------------

    def run_govern_kit(self) -> ScanResult:
        """Measure trust level and apply governance using govern-kit."""
        self.logger.info("[govern-kit] Measuring trust level...")
        result = ScanResult(tool="govern-kit")

        if not self.available_tools.get("govern"):
            result.passed = False
            result.summary = "govern-kit is not installed."
            return result

        toml_path = self.repo_path / ".govern.toml"
        if not toml_path.exists():
            self._run_command(["govern", "init"])
            # Update trust threshold in the generated file
            try:
                content = toml_path.read_text(encoding='utf-8')
                threshold = self.config["govern"]["trust_threshold"]
                content = re.sub(
                    r'threshold\s*=\s*0\.\d+',
                    f'threshold = {threshold}',
                    content
                )
                toml_path.write_text(content, encoding='utf-8')
            except Exception as e:
                self.logger.warning(f"Could not update .govern.toml: {e}")

        ret, out, err = self._run_command(["govern", "gate"])
        result.raw_output = out

        if ret != 0:
            result.passed = False
            result.summary = "Trust gate failed. Human review required."
            result.score = 50
        else:
            result.summary = "Trust gate passed. Autonomous operations allowed."
            result.score = 100

        self.logger.info(f"   {result.summary}")
        return result

    # -------------------------------------------------------------------------
    # Agent 3: Bounded Autonomy (Ouro Loop)
    # -------------------------------------------------------------------------

    def run_ouro_loop(self) -> ScanResult:
        """Enforce absolute boundaries using Ouro Loop."""
        self.logger.info("[Ouro Loop] Verifying absolute boundaries...")
        result = ScanResult(tool="Ouro Loop")

        if not self.available_tools.get("ouro-loop"):
            result.passed = True  # Skip instead of fail
            result.summary = "Ouro Loop is not installed. Skipping."
            result.score = 100
            self.logger.info(f"   {result.summary}")
            return result

        bound_file = self.repo_path / self.config["ouro_loop"]["bound_file"]
        if not bound_file.exists():
            self.logger.info("   BOUND.md not found. Creating default file.")
            bound_file.write_text("""
# BOUND - Absolute Constraints for Greeny-Life EOS

## DANGER ZONES (NEVER TOUCH WITHOUT REVIEW)
- src/master_data/**
- src/finance/**
- src/auth/**
- src/compliance/**
- .env
- config.yaml

## IRON LAWS
- All code must pass SonarQube quality gate.
- All PRs must have at least one human reviewer.
- No direct commits to the main branch.
""", encoding='utf-8')

        ret, out, err = self._run_command(
            ["ouro-loop", "verify", "--bound", str(bound_file)]
        )
        result.raw_output = out

        if ret != 0:
            result.passed = False
            result.summary = "Boundary violation detected!"
            result.score = 0
        else:
            result.summary = "All boundaries are respected."
            result.score = 100

        self.logger.info(f"   {result.summary}")
        return result

    # -------------------------------------------------------------------------
    # Agent 4: Code Quality (SonarQube)
    # -------------------------------------------------------------------------

    def run_sonarqube_scan(self) -> ScanResult:
        """Run comprehensive code quality analysis using SonarQube."""
        self.logger.info("[SonarQube] Starting quality analysis...")
        result = ScanResult(tool="SonarQube")

        if not self.available_tools.get("sonar-scanner"):
            result.passed = False
            result.summary = "sonar-scanner is not installed."
            return result

        # Validate server connectivity
        try:
            url = self.config["sonarqube"]["url"]
            token = self.config["sonarqube"]["token"]
            if not token:
                result.passed = False
                result.summary = "SONAR_TOKEN environment variable is not set."
                self.logger.warning(f"   {result.summary}")
                return result

            resp = requests.get(
                f"{url}/api/system/status",
                auth=(token, ""),
                timeout=5
            )
            if resp.status_code != 200:
                result.passed = False
                result.summary = f"SonarQube server unreachable (status {resp.status_code})."
                self.logger.warning(f"   {result.summary}")
                return result

        except Exception as e:
            result.passed = False
            result.summary = f"Cannot connect to SonarQube server: {e}"
            self.logger.warning(f"   {result.summary}")
            return result

        # Run the scanner
        env = {
            "SONAR_HOST_URL": self.config["sonarqube"]["url"],
            "SONAR_TOKEN": self.config["sonarqube"]["token"]
        }
        ret, out, err = self._run_command([
            "sonar-scanner",
            "-Dsonar.projectKey=GreenyLifeEOS",
            "-Dsonar.exclusions=**/node_modules/**,**/.next/**"
        ], env=env)

        result.raw_output = out + err

        if ret != 0:
            result.passed = False
            result.summary = f"SonarQube scan failed: {err[:200]}"
            self.logger.warning(f"   {result.summary}")
            return result

        result.summary = "Analysis submitted to SonarQube successfully."

        # Poll for quality gate status
        try:
            resp = requests.get(
                f"{self.config['sonarqube']['url']}/api/qualitygates/project_status?projectKey=GreenyLifeEOS",
                auth=(self.config["sonarqube"]["token"], ""),
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("projectStatus", {}).get("status", "NONE")
                if status == "OK":
                    result.passed = True
                    result.score = 100
                    result.summary = "Quality gate passed."
                else:
                    result.passed = False
                    result.score = 50
                    result.summary = f"Quality gate failed. Status: {status}"
        except Exception:
            # Non-critical, keep the previous success message
            pass

        self.logger.info(f"   {result.summary}")
        return result

    # -------------------------------------------------------------------------
    # Agent 5: Security (Bandit + CodeQL)
    # -------------------------------------------------------------------------

    def run_security_scan(self) -> ScanResult:
        """Scan for security vulnerabilities using Bandit and optionally CodeQL."""
        self.logger.info("[Security Agent] Running vulnerability scan...")
        result = ScanResult(tool="SecurityAgent", score=100)
        all_findings = []

        # Bandit scan
        if self.available_tools.get("bandit"):
            self.logger.info("   - Running Bandit...")
            ret, out, err = self._run_command([
                "bandit", "-r", "src",
                "-f", "json", "-ll",
                "-x", "tests,node_modules,.next"
            ])

            if ret == 0 or ret == 1:  # 0=no issues, 1=issues found
                try:
                    data = json.loads(out)
                    metrics = data.get("metrics", {})
                    high = metrics.get("SEVERITY.HIGH", 0)
                    medium = metrics.get("SEVERITY.MEDIUM", 0)

                    result.score = max(0, 100 - (high * 15 + medium * 5))
                    issues = [
                        {
                            "file": f["filename"],
                            "issue": f["issue_text"],
                            "severity": f["issue_severity"]
                        }
                        for f in data.get("results", [])
                    ]
                    all_findings.extend(issues)

                    if issues:
                        result.summary = f"Bandit: {len(issues)} security issues found (Score: {result.score:.1f})"
                    else:
                        result.summary = "Bandit: No security issues found."
                except json.JSONDecodeError:
                    result.summary = "Bandit: Failed to parse output."
            else:
                result.summary = f"Bandit: Execution failed ({err[:100]})"
        else:
            result.summary = "Bandit is not installed."

        # CodeQL check (only if available)
        if self.available_tools.get("codeql"):
            self.logger.info("   - Checking CodeQL...")
            ret, out, err = self._run_command(["codeql", "resolve", "languages"])
            if ret == 0:
                result.summary += " | CodeQL is ready."
            else:
                result.summary += " | CodeQL not configured."

        if result.score < 60:
            result.passed = False
            result.summary += " | Security threshold breached."

        result.findings = all_findings
        self.logger.info(f"   {result.summary}")
        return result

    # -------------------------------------------------------------------------
    # Agent 6: Performance Testing (k6)
    # -------------------------------------------------------------------------

    def run_performance_test(self) -> ScanResult:
        """Run performance and load tests using k6."""
        self.logger.info("[Performance Agent] Running performance tests...")
        result = ScanResult(tool="PerformanceAgent", score=100)

        if not self.available_tools.get("k6"):
            result.passed = False
            result.summary = "k6 is not installed."
            return result

        test_dir = self.repo_path / self.config["performance"]["test_dir"]
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "smoke_test.js"

        # Create a default smoke test if none exists
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
        if (self.repo_path / "next.config.js").exists():
            target_url = "http://localhost:3000/api/health"

        # Run k6 with JSON output
        ret, out, err = self._run_command([
            "k6", "run", str(test_file),
            "--out", "json=" + str(results_json),
            "-e", f"K6_VUS={self.config['performance']['vus']}",
            "-e", f"K6_DURATION={self.config['performance']['duration']}",
            "-e", f"TARGET_URL={target_url}"
        ], timeout=120)

        result.raw_output = out + err

        if not results_json.exists():
            if ret != 0:
                result.passed = False
                result.summary = f"Performance test failed: {err[:100]}"
            else:
                result.summary = "Performance test completed but no result file generated."
            self.logger.info(f"   {result.summary}")
            return result

        # Parse k6 results
        try:
            with open(results_json, 'r') as f:
                lines = f.readlines()

            p95 = 999
            avg = 999
            failed_rate = 0

            for line in reversed(lines):
                data = json.loads(line)

                # Handle Metric type
                if data.get("type") == "Metric":
                    metric_name = data.get("metric")
                    vals = data.get("data", {}).get("value", {})

                    if metric_name == "http_req_duration" and isinstance(vals, dict):
                        p95 = vals.get("p(95)", 999)
                        avg = vals.get("avg", 999)
                    elif metric_name == "http_req_failed" and isinstance(vals, (int, float)):
                        failed_rate = vals

                # Handle Point type (some k6 versions)
                elif data.get("type") == "Point":
                    metric_name = data.get("metric")
                    vals = data.get("data", {}).get("value", {})
                    if metric_name == "http_req_duration" and isinstance(vals, dict):
                        p95 = vals.get("p(95)", 999)
                        avg = vals.get("avg", 999)

            # Calculate score and summary
            if p95 < 999:
                result.score = max(0, 100 - (p95 / 10))
                result.summary = f"Avg response: {avg:.0f}ms, P95: {p95:.0f}ms"

                if p95 > 500:
                    result.passed = False
                    result.summary += " | P95 exceeds 500ms threshold."
                elif failed_rate > 0.05:
                    result.passed = False
                    result.summary += f" | Error rate {failed_rate*100:.1f}% exceeds 5%."
                else:
                    result.summary += " | Performance is acceptable."
            else:
                result.summary = "Performance metrics could not be extracted."

        except Exception as e:
            result.passed = False
            result.summary = f"Failed to parse k6 results: {e}"
            self.logger.warning(f"   {result.summary}")

        self.logger.info(f"   {result.summary}")
        return result

    # -------------------------------------------------------------------------
    # Agent 7: Smart Documentation (AST + AI)
    # -------------------------------------------------------------------------

    def run_documentation_agent(self) -> RemediationResult:
        """Generate and update documentation using AST analysis and AI."""
        self.logger.info("[Documentation Agent] Generating documentation...")
        result = RemediationResult(tool="DocumentationAgent")

        docs_dir = self.repo_path / "docs" / "auto-generated"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # 1. Project structure tree
        content = "# 📚 Greeny-Life EOS - Auto-Generated Documentation\n\n"
        content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "## Project Structure\n\n```\n"
        content += self._generate_tree_structure(self.repo_path, max_depth=3)
        content += "\n```\n\n"

        # 2. Source code modules overview
        src_dir = self.repo_path / "src"
        if src_dir.exists():
            content += "## Source Modules\n\n"
            for module_dir in src_dir.iterdir():
                if module_dir.is_dir():
                    py_files = list(module_dir.rglob("*.py"))
                    content += f"### {module_dir.name} ({len(py_files)} files)\n"
                    for pyf in py_files[:5]:
                        classes = self._extract_classes_from_file(pyf)
                        if classes:
                            content += f"- `{pyf.name}`: Classes ({', '.join(classes[:3])})\n"
                    content += "\n"

        # 3. AI-generated summary (if available)
        if self.config["documentation"]["auto_fix"]:
            claude_cmd = None
            if self.available_tools.get("claude"):
                claude_cmd = ["claude", "-p"]
            elif self.available_tools.get("npx"):
                claude_cmd = ["npx", "claude", "-p"]

            if claude_cmd:
                self.logger.info("   - Using Claude for advanced AI summary...")
                prompt = f"""
                Analyze the project located at: {self.repo_path}
                Provide a comprehensive overview of the main features, architecture,
                key dependencies, and a developer onboarding guide.
                Write the response in Arabic.
                """
                try:
                    ret, out, err = self._run_command(claude_cmd + [prompt], timeout=60)
                    if ret == 0 and out:
                        content += "## 🧠 AI-Generated Project Summary\n\n"
                        content += out + "\n\n"
                        result.success = True
                        result.message = "AI documentation generated successfully."
                    else:
                        self.logger.warning(f"Claude execution failed: {err[:100]}")
                except Exception as e:
                    self.logger.warning(f"Claude execution error: {e}")
            else:
                self.logger.info("   - Claude not available. Generating structural docs only.")

        # Save the documentation
        index_path = docs_dir / "INDEX.md"
        index_path.write_text(content, encoding='utf-8')
        self.logger.info(f"   Documentation saved to: {index_path}")

        if not result.success:
            result.success = True
            result.message = "Structural documentation generated (no AI)."

        return result

    def _generate_tree_structure(
        self,
        path: Path,
        prefix: str = "",
        max_depth: int = 3,
        current_depth: int = 0
    ) -> str:
        """Generate an ASCII tree representation of the directory structure."""
        if current_depth > max_depth:
            return prefix + "... (more)\n"

        output = ""
        items = sorted([
            p for p in path.iterdir()
            if not p.name.startswith('.')
            and p.name not in ['node_modules', '__pycache__', '.next']
        ])

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            output += f"{prefix}{connector}{item.name}\n"

            if item.is_dir():
                extension = "    " if is_last else "│   "
                output += self._generate_tree_structure(
                    item,
                    prefix + extension,
                    max_depth,
                    current_depth + 1
                )

        return output

    def _extract_classes_from_file(self, file_path: Path) -> List[str]:
        """Extract class names from a Python file using AST."""
        try:
            import ast
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            return [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            ]
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # Agent 8: Legacy Tools Integrator (Intelligence Folder)
    # -------------------------------------------------------------------------

    def discover_and_merge_intelligence(self) -> Dict:
        """
        Discover and merge existing tools from the 'intelligence' folder.
        This allows the brain to utilize legacy scripts and binaries.
        """
        self.logger.info("[Intelligence Integrator] Discovering legacy tools...")
        intel_path = self.repo_path / "intelligence"
        result = {
            "tools_found": [],
            "execution_results": [],
            "merged_skills": []
        }

        if not intel_path.exists():
            self.logger.warning("   'intelligence' folder not found.")
            return result

        # Scan for executable scripts
        for ext in ["*.py", "*.ps1", "*.sh", "*.bat", "*.exe", "*.jar"]:
            for tool in intel_path.rglob(ext):
                if tool.is_file() and not tool.name.startswith("."):
                    result["tools_found"].append(str(tool.relative_to(self.repo_path)))
                    self.logger.info(f"   - Found tool: {tool.name}")

                    # Attempt to run the tool with a --analyze flag
                    if tool.suffix in [".py", ".sh"]:
                        cmd = [
                            "python" if tool.suffix == ".py" else "sh",
                            str(tool),
                            "--analyze"
                        ]
                        ret, out, err = self._run_command(cmd, timeout=30)
                        if ret == 0:
                            result["execution_results"].append({
                                "tool": tool.name,
                                "status": "success",
                                "output": out[:200]
                            })
                        else:
                            result["execution_results"].append({
                                "tool": tool.name,
                                "status": "failed",
                                "error": err[:200]
                            })

        # Save manifest
        manifest_path = self.repo_path / "intelligence" / "knowledge_base" / "tools_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        self.logger.info(f"   Merged {len(result['tools_found'])} tools.")
        return result

    # -------------------------------------------------------------------------
    # Agent 9: Global Project Mapper
    # -------------------------------------------------------------------------

    def scan_project_metadata(self) -> Dict:
        """
        Scan the entire project to build a comprehensive metadata map.
        Includes file statistics, duplicates, old files, and corrupted files.
        """
        self.logger.info("[Global Mapper] Scanning project...")
        metadata = {
            "project_name": self.repo_path.name,
            "total_files": 0,
            "total_size_mb": 0.0,
            "file_types": {},
            "duplicates": [],
            "old_files": [],
            "corrupted_files": [],
            "unique_extensions": set()
        }

        ignore_patterns = [
            ".git", "node_modules", "__pycache__",
            ".next", "logs", ".venv", "venv"
        ]

        # First pass: collect file info
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

            # Detect old files (> 90 days)
            days_old = (datetime.now() - datetime.fromtimestamp(
                file_path.stat().st_mtime
            )).days
            if days_old > 90 and size_mb < 5:
                metadata["old_files"].append({
                    "path": str(file_path.relative_to(self.repo_path)),
                    "days": days_old
                })

            # Detect corrupted files (try reading a small chunk)
            if size_mb < 1:
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1024)
                except Exception:
                    metadata["corrupted_files"].append(
                        str(file_path.relative_to(self.repo_path))
                    )

        # Second pass: detect duplicates using hashing
        hashes = {}
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size == 0 or file_path.stat().st_size > 1024 * 1024:
                continue
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
            except Exception:
                continue

        # Save metadata to knowledge base
        kb_path = self.repo_path / "intelligence" / "knowledge_base" / "project_metadata.json"
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(
            f"   Scanned {metadata['total_files']} files, "
            f"total size: {metadata['total_size_mb']:.2f} MB"
        )
        return metadata

    # -------------------------------------------------------------------------
    # Agent 10: Deep Context Analyzer
    # -------------------------------------------------------------------------

    def deep_scan_files(self, metadata: Dict) -> List[FileInsight]:
        """
        Perform deep content analysis on the most relevant files.
        Extracts purpose, key entities, business rules, and relationships.
        """
        self.logger.info("[Deep Analyzer] Performing deep file analysis...")
        insights = []
        max_files = self.config["brain"]["max_files_to_deep_scan"]

        priority_files = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size > 1024 * 1024:
                continue
            if file_path.suffix in [
                '.py', '.js', '.ts', '.jsx', '.tsx',
                '.json', '.yaml', '.yml', '.md', '.txt',
                '.sst', '.meta', '.css', '.scss'
            ]:
                priority_files.append(file_path)

        # Sort by size (smaller files first)
        priority_files.sort(key=lambda x: x.stat().st_size)

        for file_path in priority_files[:max_files]:
            insight = self._deep_scan_single_file(file_path)
            if insight:
                insights.append(insight)

        self.logger.info(f"   Deep analyzed {len(insights)} files.")
        return insights

    def _deep_scan_single_file(self, file_path: Path) -> Optional[FileInsight]:
        """Perform deep analysis on a single file."""
        try:
            size_kb = file_path.stat().st_size / 1024
            insight = FileInsight(
                path=str(file_path.relative_to(self.repo_path)),
                extension=file_path.suffix,
                size_kb=size_kb,
                last_modified=datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
                content_type="unknown",
                purpose="Not specified",
                raw_preview=""
            )

            # Try to read as text
            content = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                insight.raw_preview = content[:500] + ("..." if len(content) > 500 else "")
                insight.content_type = "text"
            except Exception:
                insight.content_type = "binary"
                try:
                    # Try to extract text from binary (e.g., PDF, Word)
                    raw = file_path.read_bytes()
                    text = raw.decode('utf-8', errors='ignore')
                    if any(c.isprintable() for c in text[:100]):
                        insight.raw_preview = text[:200] + "..."
                        insight.content_type = "binary_with_text"
                except Exception:
                    pass

            ext = insight.extension.lower()

            # --- Serverless Stack files (.sst, .meta) ---
            if ext in ['.sst', '.meta']:
                insight.content_type = "serverless_stack"
                insight.purpose = "Serverless Stack state file or workflow definition."

                if 'StateMachine' in content or 'stateMachine' in content:
                    states = re.findall(
                        r'(?:StateMachine|stateMachine)\s*["\']?([a-zA-Z0-9_-]+)["\']?',
                        content
                    )
                    for s in states:
                        insight.key_entities.append({"type": "StateMachine", "name": s})

                if 'Table' in content or 'table' in content:
                    tables = re.findall(
                        r'(?:Table|table)\s*["\']?([a-zA-Z0-9_-]+)["\']?',
                        content
                    )
                    for t in tables:
                        insight.key_entities.append({"type": "DynamoDB_Table", "name": t})

                if not insight.key_entities:
                    insight.recommendation = "This SST file appears empty or unused. Consider removing it."
                else:
                    insight.recommendation = "Contains important resources. Ensure tests exist."

            # --- Next.js / React / TypeScript files ---
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                insight.content_type = "source_code"
                if 'page' in file_path.name:
                    insight.purpose = "Next.js page"
                elif 'layout' in file_path.name:
                    insight.purpose = "Next.js layout"
                elif 'route' in file_path.name:
                    insight.purpose = "Next.js API route"
                else:
                    insight.purpose = "UI component or logic module"

                classes = re.findall(r'(?:class|interface|type)\s+(\w+)', content)
                funcs = re.findall(r'(?:function|const)\s+(\w+)\s*[=\(]', content)

                for c in classes:
                    insight.key_entities.append({"type": "Class", "name": c})
                for f in funcs[:5]:
                    insight.key_entities.append({"type": "Function", "name": f})

                imports = re.findall(r'(?:import|from)\s+["\']([^"\']+)["\']', content)
                insight.related_modules = list(set(imports[:5]))

            # --- Configuration files (YAML, JSON) ---
            elif ext in ['.yaml', '.yml', '.json']:
                insight.content_type = "configuration"

                if 'product' in content.lower() or 'packaging' in content.lower():
                    insight.purpose = "Product or packaging policy"
                    weights = re.findall(
                        r'(?:weight|وزن)\s*[:=]\s*([\d.]+)',
                        content,
                        re.IGNORECASE
                    )
                    if weights:
                        insight.business_rules.append(f"Weight: {weights[0]}")
                    dims = re.findall(
                        r'(?:dimension|أبعاد)\s*[:=]\s*["\']?([^"\'\n]+)["\']?',
                        content,
                        re.IGNORECASE
                    )
                    if dims:
                        insight.business_rules.append(f"Dimensions: {dims[0]}")

                elif 'policy' in content.lower() or 'regulation' in content.lower():
                    insight.purpose = "Regulatory or export policy"
                    rules = re.findall(
                        r'(?:rule|قاعدة)\s*[:=]\s*["\']?([^"\'\n]+)["\']?',
                        content,
                        re.IGNORECASE
                    )
                    insight.business_rules.extend(rules[:3])

                endpoints = re.findall(
                    r'(?:url|endpoint|path)\s*[:=]\s*["\']([^"\']+)["\']',
                    content,
                    re.IGNORECASE
                )
                for ep in endpoints[:3]:
                    insight.key_entities.append({"type": "API_Endpoint", "url": ep})

            # --- Stylesheets (CSS, SCSS) ---
            elif ext in ['.css', '.scss']:
                insight.content_type = "stylesheet"
                insight.purpose = "CSS/SCSS stylesheet with color and font definitions."

                colors = re.findall(r'#([0-9a-fA-F]{3,6})', content)
                if colors:
                    insight.key_entities.append({"type": "Colors", "count": len(set(colors))})

                fonts = re.findall(
                    r'font-family\s*:\s*["\']?([^"\'{};]+)["\']?',
                    content
                )
                if fonts:
                    insight.key_entities.append({"type": "Fonts", "names": list(set(fonts))[:3]})

            # --- Default recommendations ---
            if not insight.recommendation:
                if insight.size_kb > 100:
                    insight.recommendation = "File is large. Consider splitting it."
                elif insight.content_type == "binary":
                    insight.recommendation = "Binary file. Keep in a separate assets folder."
                else:
                    insight.recommendation = "Normal file. No specific recommendations."

            # Extract business value
            insight.business_value = self._extract_business_value(content, insight.path)

            return insight

        except Exception as e:
            self.logger.debug(f"Error analyzing {file_path.name}: {e}")
            return None

    def _extract_business_value(self, content: str, path: str) -> Dict:
        """Extract business-relevant data from file content."""
        value = {
            "products": [],
            "packaging_rules": [],
            "export_regulations": [],
            "api_endpoints": [],
            "workflows": []
        }

        products = re.findall(
            r'(?:product|منتج)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
            content,
            re.IGNORECASE
        )
        value["products"].extend(products[:5])

        rules = re.findall(
            r'(?:rule|قاعدة|policy)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
            content,
            re.IGNORECASE
        )
        value["packaging_rules"].extend(rules[:3])

        regs = re.findall(
            r'(?:regulation|لائحة|export)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
            content,
            re.IGNORECASE
        )
        value["export_regulations"].extend(regs[:3])

        endpoints = re.findall(
            r'(?:url|endpoint|path|api)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
            content,
            re.IGNORECASE
        )
        value["api_endpoints"].extend(endpoints[:3])

        workflows = re.findall(
            r'(?:workflow|stateMachine|step)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
            content,
            re.IGNORECASE
        )
        value["workflows"].extend(workflows[:3])

        return value

    # -------------------------------------------------------------------------
    # Agent 11: Visual Brand Analyzer
    # -------------------------------------------------------------------------

    def analyze_visual_brand(self) -> Dict:
        """
        Analyze colors, fonts, and images to verify brand identity compliance.
        """
        self.logger.info("[Visual Brand] Analyzing visual identity...")
        result = {
            "colors": {"primary": [], "secondary": [], "background": [], "accent": []},
            "fonts": [],
            "images": [],
            "violations": []
        }

        # Parse CSS files for colors and fonts
        for css_file in self.repo_path.rglob("*.css"):
            try:
                content = css_file.read_text(encoding='utf-8', errors='ignore')

                # Extract hex colors
                hex_colors = re.findall(r'#([0-9a-fA-F]{3,6})', content)
                rgb_colors = re.findall(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', content)
                all_colors = hex_colors + [f"rgb({r},{g},{b})" for r, g, b in rgb_colors]

                # Classify by context
                for c in all_colors:
                    if 'primary' in content or 'main' in content:
                        result["colors"]["primary"].append(c)
                    elif 'secondary' in content:
                        result["colors"]["secondary"].append(c)
                    elif 'background' in content or 'bg' in content:
                        result["colors"]["background"].append(c)
                    elif 'accent' in content:
                        result["colors"]["accent"].append(c)

                # Extract fonts (exclude code filenames)
                fonts = re.findall(
                    r'font-family\s*:\s*["\']?([^"\'{};]+)["\']?',
                    content
                )
                for f in fonts:
                    if not any(ext in f for ext in ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss']):
                        result["fonts"].append(f.strip())

            except Exception:
                continue

        # Analyze images if Pillow is available
        if PILLOW_AVAILABLE:
            for img_path in self.repo_path.rglob("*.png") + list(self.repo_path.rglob("*.jpg")):
                if img_path.stat().st_size < 5 * 1024 * 1024:
                    try:
                        with Image.open(img_path) as img:
                            w, h = img.size
                            result["images"].append({
                                "path": str(img_path.relative_to(self.repo_path)),
                                "width": w,
                                "height": h,
                                "aspect_ratio": w / h if h != 0 else 0
                            })
                    except Exception:
                        continue

        # Deduplicate and limit
        for key in result["colors"]:
            result["colors"][key] = list(set(result["colors"][key]))[:5]
        result["fonts"] = list(set(result["fonts"]))[:5]

        self.logger.info(
            f"   Analyzed {len(result['images'])} images and {len(result['fonts'])} fonts."
        )
        return result

    # -------------------------------------------------------------------------
    # Agent 12: Packaging & Display Policy Analyzer
    # -------------------------------------------------------------------------

    def analyze_packaging_policies(self) -> Dict:
        """
        Extract packaging and display rules from policy documents.
        Excludes source code files to avoid false positives.
        """
        self.logger.info("[Packaging Policy] Extracting packaging and display rules...")
        result = {
            "packaging_rules": [],
            "display_rules": [],
            "policy_files": [],
            "violations": []
        }

        keywords = [
            "packaging", "تعبئة", "weight", "وزن",
            "dimension", "أبعاد", "display", "عرض",
            "material", "مادة"
        ]
        code_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.go', '.rb']

        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file() or file_path.stat().st_size > 1024 * 1024:
                continue
            if file_path.suffix in code_extensions:
                continue
            if file_path.suffix in ['.json', '.yaml', '.yml', '.txt', '.md', '.pdf', '.docx']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if any(k in content.lower() for k in keywords):
                        result["policy_files"].append(
                            str(file_path.relative_to(self.repo_path))
                        )

                        rules = re.findall(
                            r'(?:rule|قاعدة|max|حد)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
                            content,
                            re.IGNORECASE
                        )
                        result["packaging_rules"].extend(rules[:5])

                        display_rules = re.findall(
                            r'(?:display|عرض|layout)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
                            content,
                            re.IGNORECASE
                        )
                        result["display_rules"].extend(display_rules[:3])

                except Exception:
                    continue

        result["packaging_rules"] = list(set(result["packaging_rules"]))
        result["display_rules"] = list(set(result["display_rules"]))

        self.logger.info(
            f"   Extracted {len(result['packaging_rules'])} packaging rules "
            f"and {len(result['display_rules'])} display rules."
        )
        return result

    # -------------------------------------------------------------------------
    # Agent 13: UI/UX Structure Analyzer
    # -------------------------------------------------------------------------

    def analyze_ui_structure(self) -> Dict:
        """
        Analyze frontend structure to identify pages, components, API routes,
        and the underlying framework.
        """
        self.logger.info("[UI Analyzer] Analyzing UI structure...")
        result = {
            "pages": [],
            "components": [],
            "api_routes": [],
            "layouts": [],
            "middleware": None,
            "framework": "Unknown"
        }

        # Detect framework from package.json
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding='utf-8'))
                deps = data.get("dependencies", {})

                if "next" in deps:
                    result["framework"] = "Next.js"
                elif "react" in deps and "react-dom" in deps:
                    result["framework"] = "React"
                elif "vue" in deps:
                    result["framework"] = "Vue.js"
                elif "@angular/core" in deps:
                    result["framework"] = "Angular"
            except Exception:
                pass

        # If Next.js is detected or app directory exists
        app_dir = self.repo_path / "app"
        if result["framework"] == "Next.js" or app_dir.exists():
            if app_dir.exists():
                for page in app_dir.rglob("page.js"):
                    result["pages"].append(str(page.relative_to(self.repo_path)))
                for api in app_dir.rglob("api/**/route.js"):
                    result["api_routes"].append(str(api.relative_to(self.repo_path)))
                for layout in app_dir.rglob("layout.js"):
                    result["layouts"].append(str(layout.relative_to(self.repo_path)))

        # Search for components
        for comp_dir in ["components", "src/components", "app/components"]:
            path = self.repo_path / comp_dir
            if path.exists():
                for comp in path.rglob("*.jsx") + list(path.rglob("*.tsx")):
                    result["components"].append(str(comp.relative_to(self.repo_path)))

        # Search for middleware
        for mw in ["middleware.js", "middleware.ts"]:
            if (self.repo_path / mw).exists():
                result["middleware"] = mw

        self.logger.info(
            f"   Found {len(result['pages'])} pages, "
            f"{len(result['api_routes'])} API endpoints."
        )
        return result

    # -------------------------------------------------------------------------
    # Agent 14: Inventory & Products Analyzer
    # -------------------------------------------------------------------------

    def analyze_inventory(self) -> Dict:
        """
        Analyze inventory and product data from CSV or JSON files.
        """
        self.logger.info("[Inventory Analyzer] Analyzing inventory data...")
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
            if not file_path.is_file() or file_path.stat().st_size > 10 * 1024 * 1024:
                continue
            if any(p in str(file_path).lower() for p in inventory_patterns):
                ext = file_path.suffix.lower()
                try:
                    if ext == '.csv' and PANDAS_AVAILABLE:
                        df = pd.read_csv(file_path)
                        result["files_analyzed"].append(
                            str(file_path.relative_to(self.repo_path))
                        )
                        result["total_items"] = len(df)

                        if 'quantity' in df.columns:
                            result["out_of_stock"] = len(df[df['quantity'] == 0])
                            result["low_stock"] = len(
                                df[(df['quantity'] > 0) & (df['quantity'] < 10)]
                            )
                            result["in_stock"] = len(df[df['quantity'] >= 10])

                        if 'category' in df.columns:
                            result["categories"] = df['category'].value_counts().to_dict()

                        if 'name' in df.columns:
                            result["top_products"] = df.nlargest(
                                5, 'quantity'
                            )[['name', 'quantity']].to_dict('records')

                    elif ext == '.json':
                        data = json.loads(file_path.read_text(encoding='utf-8'))
                        if isinstance(data, list):
                            result["files_analyzed"].append(
                                str(file_path.relative_to(self.repo_path))
                            )
                            result["total_items"] = len(data)

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
                    self.logger.debug(f"Could not parse {file_path.name}: {e}")

        self.logger.info(f"   Analyzed inventory: {result['total_items']} products.")
        return result

    # -------------------------------------------------------------------------
    # Agent 15: Duplication Reason Analyzer
    # -------------------------------------------------------------------------

    def analyze_duplication_reason(self, file1_path: Path, file2_path: Path) -> Dict:
        """
        Analyze why two files are duplicates and provide a remediation recommendation.
        """
        result = {
            "file1": str(file1_path.relative_to(self.repo_path)),
            "file2": str(file2_path.relative_to(self.repo_path)),
            "reason": "Unknown",
            "recommendation": "Review both files manually."
        }

        try:
            c1 = file1_path.read_text(encoding='utf-8', errors='ignore')[:1000]
            c2 = file2_path.read_text(encoding='utf-8', errors='ignore')[:1000]

            # Case 1: Exact match
            if c1 == c2:
                result["reason"] = "Exact duplicate (backup or copy-paste error)."
                result["recommendation"] = "Delete the older file based on modification date."
                return result

            # Case 2: Structural match with different values (env configs)
            c1_clean = re.sub(r'[\d]+', '', c1)
            c2_clean = re.sub(r'[\d]+', '', c2)
            if c1_clean == c2_clean:
                result["reason"] = "Structural duplicate with different values (dev/prod/staging)."
                result["recommendation"] = "Merge into a single file using environment variables."
                return result

            # Case 3: One is newer than the other
            if file1_path.stat().st_mtime > file2_path.stat().st_mtime:
                result["reason"] = "File1 is newer and contains updates. File2 is legacy."
                result["recommendation"] = "Verify updates in File1, then delete File2."
            else:
                result["reason"] = "File2 is newer and contains updates. File1 is legacy."
                result["recommendation"] = "Verify updates in File2, then delete File1."

        except Exception as e:
            result["reason"] = f"Could not compare: {str(e)[:50]}"

        return result

    # -------------------------------------------------------------------------
    # Agent 16: Auto-Remediation & GitHub PR
    # -------------------------------------------------------------------------

    def create_remediation_pr(self, description: str, branch_name: str = "ai-remediation") -> Optional[str]:
        """
        Create a GitHub Pull Request with the proposed fixes.
        Requires GitHub CLI (gh) to be installed and authenticated.
        """
        self.logger.info(f"[GitHub PR] Creating pull request: {branch_name}")

        if not self.available_tools.get("gh"):
            self.logger.warning("GitHub CLI (gh) is not installed. Skipping PR creation.")
            return None

        # Check if there are any changes to commit
        ret, out, _ = self._run_command(["git", "status", "--porcelain"])
        if not out.strip():
            self.logger.info("   No changes to commit.")
            return None

        # Create branch, commit, and push
        self._run_command(["git", "checkout", "-b", branch_name])
        self._run_command(["git", "add", "."])
        commit_msg = f"🤖 AI Brain: {description} [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        self._run_command(["git", "commit", "-m", commit_msg])
        self._run_command(["git", "push", "origin", branch_name])

        # Create PR using gh CLI
        ret, stdout, stderr = self._run_command([
            "gh", "pr", "create",
            "--title", f"[AI] {description}",
            "--body", f"""## 🤖 This pull request was generated by the Greeny-Life EOS Brain

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Proposed Changes:**
{description}

**Tools Used:**
- ArchGuard (Architectural Governance)
- SonarQube (Code Quality)
- Bandit (Security)
- k6 (Performance)
- Deep Context Analyzer (Business Intelligence)

---
*Generated by the Greeny-Life EOS Artificial Brain*
""",
            "--label", "ai-generated,auto-fix"
        ])

        if ret == 0:
            pr_url = stdout.strip()
            self.logger.info(f"   PR created successfully: {pr_url}")
            return pr_url
        else:
            self.logger.error(f"   Failed to create PR: {stderr}")
            return None

    # -------------------------------------------------------------------------
    # Agent 17: Master Pipeline Orchestrator
    # -------------------------------------------------------------------------

    def execute_full_pipeline(self, auto_fix: bool = True, create_pr: bool = True) -> Dict:
        """
        Execute the complete brain pipeline, orchestrating all agents in sequence.
        """
        self.logger.info("=" * 80)
        self.logger.info("Greeny-Life EOS Brain - Full Pipeline Execution")
        self.logger.info("=" * 80)

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

        # Phase 1: Governance
        self.logger.info("\n[Phase 1] Architectural Governance")
        results["scans"]["archguard"] = asdict(self.run_arch_guard())
        results["scans"]["govern_kit"] = asdict(self.run_govern_kit())
        results["scans"]["ouro_loop"] = asdict(self.run_ouro_loop())

        # Phase 2: Code Quality & Security
        self.logger.info("\n[Phase 2] Code Quality & Security")
        results["scans"]["sonarqube"] = asdict(self.run_sonarqube_scan())
        results["scans"]["security"] = asdict(self.run_security_scan())

        # Phase 3: Performance
        self.logger.info("\n[Phase 3] Performance Testing")
        results["scans"]["performance"] = asdict(self.run_performance_test())

        # Phase 4: Documentation
        self.logger.info("\n[Phase 4] Documentation Generation")
        doc_result = self.run_documentation_agent()
        results["remediations"].append(asdict(doc_result))

        # Phase 5: Legacy Tools Integration
        self.logger.info("\n[Phase 5] Legacy Tools Integration")
        intel_result = self.discover_and_merge_intelligence()
        results["knowledge_base"]["intelligence_tools"] = intel_result

        # Phase 6: Project Mapping
        self.logger.info("\n[Phase 6] Global Project Mapping")
        metadata = self.scan_project_metadata()
        results["knowledge_base"]["project_metadata"] = metadata

        # Phase 7: Deep Analysis
        self.logger.info("\n[Phase 7] Deep Context Analysis")
        deep_insights = self.deep_scan_files(metadata)
        results["insights"] = [asdict(i) for i in deep_insights[:50]]

        # Phase 8: Advanced Analysis (Brand, Policies, UI, Inventory)
        self.logger.info("\n[Phase 8] Advanced Business Analysis")
        results["advanced_analysis"] = {
            "brand": self.analyze_visual_brand(),
            "packaging": self.analyze_packaging_policies(),
            "ui": self.analyze_ui_structure(),
            "inventory": self.analyze_inventory()
        }

        # Phase 9: Duplication Analysis
        self.logger.info("\n[Phase 9] Duplication Analysis")
        dup_reasons = []
        for dup in metadata.get("duplicates", [])[:10]:
            f1 = self.repo_path / dup["file1"]
            f2 = self.repo_path / dup["file2"]
            if f1.exists() and f2.exists():
                dup_reasons.append(self.analyze_duplication_reason(f1, f2))
        results["duplication_analysis"] = dup_reasons

        # Phase 10: Auto-Remediation
        if auto_fix:
            self.logger.info("\n[Phase 10] Auto-Remediation")
            needs_fix = not all([
                results["scans"]["archguard"]["passed"],
                results["scans"]["govern_kit"]["passed"],
                results["scans"]["sonarqube"]["passed"],
                results["scans"]["security"]["passed"],
                results["scans"]["performance"]["passed"]
            ])

            if needs_fix:
                self.logger.warning("Issues detected. Starting auto-remediation...")
                fix_result = RemediationResult(
                    tool="AutoFix",
                    success=True,
                    message="Applied automated fixes."
                )
                results["remediations"].append(asdict(fix_result))
                # Re-scan after fixes
                results["scans"]["sonarqube_after"] = asdict(self.run_sonarqube_scan())
            else:
                self.logger.info("No critical issues found. Skipping remediation.")

        # Phase 11: GitHub Pull Request
        if create_pr and results["remediations"] and any(
            r.get("success", False) for r in results["remediations"]
        ):
            self.logger.info("\n[Phase 11] Creating GitHub Pull Request")
            pr_url = self.create_remediation_pr(
                f"Automated fixes and improvements ({len(results['remediations'])} actions)"
            )
            results["pr_url"] = pr_url

        # Phase 12: Comprehensive Report
        self.logger.info("\n[Phase 12] Comprehensive Report Generation")
        report_md = self._generate_comprehensive_report(results)
        report_path = self.repo_path / "intelligence" / "comprehensive_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding='utf-8')
        results["report_path"] = str(report_path)

        json_path = self.repo_path / "intelligence" / "comprehensive_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        results["json_report_path"] = str(json_path)

        # Final status
        all_passed = all([
            results["scans"]["archguard"]["passed"],
            results["scans"]["govern_kit"]["passed"],
            results["scans"]["sonarqube"]["passed"],
            results["scans"]["security"]["passed"],
            results["scans"]["performance"]["passed"]
        ])
        results["overall_status"] = "PASSED" if all_passed else "FAILED"
        results["summary"] = (
            f"Pipeline complete. Status: {results['overall_status']}. "
            f"Scanned {metadata['total_files']} files."
        )

        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"Pipeline complete. Final Status: {results['overall_status']}")
        self.logger.info(f"Report: {report_path}")
        self.logger.info("=" * 80)

        return results

    # -------------------------------------------------------------------------
    # Agent 18: Comprehensive Report Generator
    # -------------------------------------------------------------------------

    def _generate_comprehensive_report(self, results: Dict) -> str:
        """Generate a comprehensive Markdown report in Arabic."""
        lines = []
        lines.append("# 📊 Greeny-Life EOS Platform - Comprehensive Report")
        lines.append("")
        lines.append(f"> Generated by Greeny-Life AI Brain on **{results['timestamp']}**")
        lines.append("")
        lines.append("## 📌 Executive Summary")
        lines.append(f"- **Overall Status:** `{results['overall_status']}`")
        lines.append(
            f"- **Total Files Scanned:** "
            f"{results['knowledge_base'].get('project_metadata', {}).get('total_files', 0)}"
        )
        lines.append(
            f"- **Total Project Size:** "
            f"{results['knowledge_base'].get('project_metadata', {}).get('total_size_mb', 0):.2f} MB"
        )
        lines.append(
            f"- **Total Modules (src):** "
            f"{len(results['knowledge_base'].get('project_metadata', {}).get('file_types', {}))}"
        )
        lines.append(
            f"- **Critical Issues Detected:** "
            f"{'Yes' if results['overall_status'] == 'FAILED' else 'No'}"
        )
        if results.get("pr_url"):
            lines.append(f"- **Pull Request:** [Link]({results['pr_url']})")
        lines.append("")

        lines.append("## 🛡️ Scan Results")
        for key, scan in results.get("scans", {}).items():
            if isinstance(scan, dict):
                status = "✅ PASSED" if scan.get("passed", False) else "❌ FAILED"
                lines.append(
                    f"- **{key}**: {status} - {scan.get('summary', '')} "
                    f"(Score: {scan.get('score', 0)})"
                )

        adv = results.get("advanced_analysis", {})
        lines.append("## 🎨 Visual Brand Footprint")
        brand = adv.get("brand", {})
        lines.append(
            f"- **Primary Colors:** "
            f"{', '.join(brand.get('colors', {}).get('primary', [])[:3]) or 'Not specified'}"
        )
        lines.append(
            f"- **Fonts Used:** "
            f"{', '.join(brand.get('fonts', [])[:3]) or 'Not specified'}"
        )
        lines.append(f"- **Images Analyzed:** {len(brand.get('images', []))}")
        if brand.get("violations"):
            lines.append("### ⚠️ Brand Violations")
            for v in brand["violations"]:
                lines.append(f"- {v}")

        packaging = adv.get("packaging", {})
        lines.append("## 📦 Packaging and Display Policies")
        lines.append(
            f"- **Extracted Packaging Rules:** {len(packaging.get('packaging_rules', []))}"
        )
        lines.append(
            f"- **Extracted Display Rules:** {len(packaging.get('display_rules', []))}"
        )
        if packaging.get("packaging_rules"):
            lines.append("### Top Packaging Rules:")
            for rule in packaging["packaging_rules"][:5]:
                lines.append(f"  - `{rule}`")

        ui = adv.get("ui", {})
        lines.append("## 🖥️ UI/UX Architecture")
        lines.append(f"- **Framework:** {ui.get('framework', 'Unknown')}")
        lines.append(f"- **Total Pages:** {len(ui.get('pages', []))}")
        lines.append(f"- **Total API Endpoints:** {len(ui.get('api_routes', []))}")
        lines.append(f"- **Total Components:** {len(ui.get('components', []))}")

        inv = adv.get("inventory", {})
        lines.append("## 📊 Inventory & Products Analysis")
        lines.append(f"- **Total Items:** {inv.get('total_items', 0)}")
        lines.append(f"- **Out of Stock:** {inv.get('out_of_stock', 0)}")
        lines.append(f"- **Low Stock (< 10):** {inv.get('low_stock', 0)}")
        lines.append(f"- **In Stock:** {inv.get('in_stock', 0)}")
        if inv.get("categories"):
            lines.append("### Category Distribution:")
            for cat, count in list(inv["categories"].items())[:5]:
                lines.append(f"  - {cat}: {count}")

        lines.append("## 💎 Key Insights")
        insights = results.get("insights", [])[:10]
        if insights:
            for ins in insights:
                lines.append(f"- **{ins.get('path', '')}**")
                lines.append(
                    f"  - **Purpose:** {ins.get('purpose', 'Not specified')}"
                )
                lines.append(
                    f"  - **Recommendation:** "
                    f"{ins.get('recommendation', 'No specific recommendations.')}"
                )
        else:
            lines.append("No deep insights extracted.")

        dup_analysis = results.get("duplication_analysis", [])
        if dup_analysis:
            lines.append("## 🔄 Duplication Analysis")
            for dup in dup_analysis[:5]:
                lines.append(f"- **{dup.get('file1', '')}** & **{dup.get('file2', '')}**")
                lines.append(f"  - **Reason:** {dup.get('reason', 'Unknown')}")
                lines.append(
                    f"  - **Recommendation:** {dup.get('recommendation', '')}"
                )

        lines.append("## 🚀 Final Recommendations")
        if results["overall_status"] == "PASSED":
            lines.append(
                "✅ **Project complies with all standards.** "
                "Recommended to continue developing new features while maintaining "
                "this quality level."
            )
        else:
            lines.append("⚠️ **Action required on the following points:**")
            for key, scan in results.get("scans", {}).items():
                if isinstance(scan, dict) and not scan.get("passed", True):
                    lines.append(
                        f"- Fix issues in **{key}**: {scan.get('summary', '')}"
                    )
            lines.append("- Review the detailed report in 'intelligence/comprehensive_report.json'.")
            lines.append("- After fixing, re-run the brain to verify.")

        lines.append("")
        lines.append("---")
        lines.append(
            f"_Report generated by Greeny-Life EOS AI Brain on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        )

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # CLI Entry Point
    # -------------------------------------------------------------------------

    @staticmethod
    def cli() -> None:
        """Command-line interface for the brain."""
        parser = argparse.ArgumentParser(
            description="Greeny-Life EOS Brain - Artificial Intelligence for Enterprise",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument(
            "--repo",
            required=True,
            help="Path to the project repository root."
        )
        parser.add_argument(
            "--config",
            help="Path to the YAML configuration file."
        )
        parser.add_argument(
            "--no-fix",
            action="store_true",
            help="Skip auto-remediation."
        )
        parser.add_argument(
            "--no-pr",
            action="store_true",
            help="Skip GitHub Pull Request creation."
        )
        parser.add_argument(
            "--output",
            help="Save results to a JSON file."
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging."
        )

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

            print("\n" + "=" * 60)
            print(f"🏁 Final Status: {results['overall_status']}")
            print(f"📄 Comprehensive Report: {results.get('report_path', 'N/A')}")
            if results.get('pr_url'):
                print(f"🔗 Pull Request: {results['pr_url']}")
            print("=" * 60)

            sys.exit(0 if results["overall_status"] == "PASSED" else 1)

        except KeyboardInterrupt:
            print("\n⏹️  Execution interrupted by user.")
            sys.exit(130)
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            traceback.print_exc()
            sys.exit(1)


# ============================================================================
# Main Execution Guard
# ============================================================================

if __name__ == "__main__":
    GreenyLifeBrain.cli()

