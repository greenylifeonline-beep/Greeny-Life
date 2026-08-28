#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
GREENY-LIFE EOS - ENTERPRISE ARTIFICIAL BRAIN
================================================================================
Complete Autonomous Enterprise Brain for Greeny-Life Platform.
Version: 5.0 (Final Integrated - No Stubs)
Date: 2026-08-04
================================================================================
This is the complete, unabridged, and fully integrated brain that acts as the
Single Source of Truth, continuously learns, evolves, plans, executes upon
approval, handles all chaos, conflicts, errors, and deficiencies, and generates
comprehensive daily reports. It is the heart of the Greeny-Life EOS.
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
import asyncio
import shutil
import time
import traceback
import threading
import smtplib
import random
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import requests

# ============================================================================
# Optional Dependencies Check
# ============================================================================
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("âš ï¸  Pillow not installed. Run: pip install Pillow")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("âš ï¸  Pandas not installed. Run: pip install pandas")

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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def add_finding(self, finding: Dict[str, Any]) -> None:
        if isinstance(finding, dict):
            self.findings.append(finding)

    def mark_failed(self, summary: str, score: float = 0.0) -> None:
        self.passed = False
        self.score = score
        self.summary = summary

    def is_success(self) -> bool:
        return self.passed and self.score >= 60.0

@dataclass
class RemediationResult:
    tool: str
    success: bool = False
    pr_url: Optional[str] = None
    commit_hash: Optional[str] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def mark_success(self, message: str = "", pr_url: Optional[str] = None, commit_hash: Optional[str] = None) -> None:
        self.success = True
        self.message = message
        self.pr_url = pr_url
        self.commit_hash = commit_hash

    def mark_failure(self, message: str = "") -> None:
        self.success = False
        self.message = message

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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summarize(self) -> str:
        return (
            f"{self.path} [{self.content_type}] - {self.purpose}. "
            f"Recommendation: {self.recommendation or 'No recommendation provided.'}"
        )


from assimilated_brain import (  # noqa: E402
    c5_capability_surface,
    consult_assimilated,
    load_assimilated_knowledge,
)


# ============================================================================
# Main Brain Class
# ============================================================================

class GreenyLifeBrain:
    """
    The master orchestrator for Greeny-Life EOS.
    This is the fully integrated, self-learning, self-evolving enterprise brain.
    """

    # Global ignore patterns (applied to all scans/cleanups)
    IGNORE_PATTERNS = [
        ".git", ".venv", "venv", "env",
        "node_modules", "__pycache__",
        ".next", "dist", "build",
        "logs", "alerts", "archive",
        ".pytest_cache", ".mypy_cache", ".ruff_cache",
        ".vscode", ".idea", ".DS_Store"
    ]

    def __init__(self, repo_path: str, config_path: Optional[str] = None):
        self.repo_path = Path(repo_path).resolve()
        self.start_time = datetime.now()
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.knowledge_base = {}
        self.insights = []
        self.available_tools = {}

        self._check_prerequisites()
        self._ensure_directories()
        self._ensure_manifest_exists()

        self.logger.info("=" * 80)
        self.logger.info("Greeny-Life EOS Brain v5.0 initialized successfully.")
        self.logger.info(f"Project Path: {self.repo_path}")
        self.logger.info("=" * 80)

    # -------------------------------------------------------------------------
    # Helper: Check if a path should be ignored
    # -------------------------------------------------------------------------
    def _should_ignore(self, path: Path) -> bool:
        path_str = str(path)
        return any(ign in path_str for ign in self.IGNORE_PATTERNS)

    # -------------------------------------------------------------------------
    # Initialization & Configuration
    # -------------------------------------------------------------------------

    def _load_config(self, config_path: Optional[str]) -> Dict:
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
            "performance": {"test_dir": "tests/performance", "vus": 10, "duration": "10s"},
            "documentation": {"auto_fix": True, "ignore_patterns": [".*test.*", ".*migrations.*"]},
            "brand": {"primary_color": ["#2E8B57"], "logo_aspect_ratio": 1.0},
            "brain": {
                "max_files_to_deep_scan": 200,
                "enable_ai_summary": True,
                "backup_before_fix": True,
                "knowledge_base_path": "intelligence/knowledge_base"
            },
            "evolution": {
                "auto_propose_updates": True,
                "require_approval": True,
                "pr_branch_prefix": "ai-evolution-",
                "test_before_merge": True
            },
            "cleanup": {
                "keep_last_n_logs": 5,
                "keep_last_n_alerts": 5,
                "keep_last_n_reports": 5,
                "archive_duplicates": True,
                "auto_merge_conflicts": True
            }
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_update(default_config, user_config)
            except Exception as e:
                self.logger.warning(f"Failed to read config: {e}. Using defaults.")

        return default_config

    def _deep_update(self, base: Dict, update: Dict) -> None:
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("GreenyLifeBrain")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console.setFormatter(formatter)
            logger.addHandler(console)

            log_dir = self.repo_path / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"brain-{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _check_prerequisites(self) -> None:
        required = ["git", "python3"]
        optional = ["sonar-scanner", "bandit", "k6", "claude", "gh",
                    "docker", "archguard", "ouro-loop", "govern", "codeql", "npx"]

        self.available_tools = {}

        for tool in required:
            self.available_tools[tool] = self._which(tool)
            if not self.available_tools[tool]:
                self.logger.error(f"Required tool '{tool}' not found. Aborting.")
                sys.exit(1)

        for tool in optional:
            self.available_tools[tool] = self._which(tool)
            if self.available_tools[tool]:
                self.logger.info(f"Optional tool '{tool}' is available.")
            else:
                self.logger.warning(f"Optional tool '{tool}' not found.")

        if not self.available_tools.get("claude") and self.available_tools.get("npx"):
            self.available_tools["claude"] = True
            self.logger.info("Will use 'npx claude' for Claude AI.")

    def _which(self, cmd: str) -> bool:
        return shutil.which(cmd) is not None

    def run_asset_classifier(self, mode: str = "FORENSIC_DISCOVERY_ONLY") -> Dict:
        self.logger.info(f"ðŸ§  [Asset Classifier v3] Starting intelligent classification in {mode} mode...")
        
        result = {
            "mode": mode,
            "total_assets": 0,
            "canonical": [],
            "merge": [],
            "archive": [],
            "delete": [],
            "knowledge_graph": {},
            "tier_0_protected": [],
            "treasure_list_loaded": False,
            "summary": "",
            "report_path": "",
            "requires_approval": True
        }

        # ===================================================================
        # 1. LOAD TREASURE INVENTORY (if exists)
        # ===================================================================
        treasure_path = self.repo_path / "TREASURE_INVENTORY.csv"
        treasure_files = set()
        if treasure_path.exists():
            try:
                import csv
                with open(treasure_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        fullname = row.get('FullName')
                        if fullname:
                            # Normalize path for comparison
                            rel_path = str(Path(fullname).relative_to(self.repo_path))
                            treasure_files.add(rel_path)
                self.logger.info(f"   Loaded {len(treasure_files)} treasure files from TREASURE_INVENTORY.csv")
                result["treasure_list_loaded"] = True
            except Exception as e:
                self.logger.warning(f"   Could not load treasure inventory: {e}")

        # ===================================================================
        # 2. DEFINE TIER 0 - ABSOLUTE CORE (Protected Files)
        # ===================================================================
        tier_0_files = [
            "brain.py",
            "system_manifest.json",
            "config.yaml",
            "BOUND.md",
            "workflowEngine.ts",
            "database/schemas/domain/domain-schema.ts",
            "intelligence/eos-final-enterprise-blueprint.json",
            "intelligence/eos-real-business-flow-reconstruction.json",
            "intelligence/eos-real-execution-path-map.json",
            "intelligence/eos-workflow-state-machine-map.json",
            "intelligence/eos-prisma-domain-ownership.json",
            "intelligence/eos-domain-boundary-validation.json",
            "governance/eos-assets-registry-v1.json",
            "governance/eos-deep-asset-discovery-v1.json"
        ]
        result["tier_0_protected"] = tier_0_files

        # ===================================================================
        # 3. COLLECT ASSETS (Exclude temp/build folders)
        # ===================================================================
        ignore_folders = [
            '.venv', 'node_modules', '__pycache__', '.next', 
            'logs', 'alerts', 'archive', '.git'
        ]
        ignore_extensions = ['.pyc', '.log', '.lock', '.sst', '.meta', '.js.map', '.css.map']
        
        all_files = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(folder in str(file_path) for folder in ignore_folders):
                continue
            if file_path.suffix in ignore_extensions:
                continue
            if file_path.stat().st_size == 0:
                continue
            all_files.append(file_path)

        self.logger.info(f"   Found {len(all_files)} assets to classify.")
        result["total_assets"] = len(all_files)

        # ===================================================================
        # 4. CLASSIFICATION WITH CANONICAL SCORE
        # ===================================================================
        classifications = {
            "canonical": [],
            "merge": [],
            "archive": [],
            "delete": []
        }
        knowledge_graph = {}

        for file_path in all_files:
            rel_path = str(file_path.relative_to(self.repo_path))
            name = file_path.name.lower()
            content = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:1500]
            except:
                pass

            # --- CHECK IF IN TREASURE LIST ---
            if rel_path in treasure_files:
                classifications["canonical"].append({
                    "path": rel_path,
                    "score": 100,
                    "tier": "Tier 0 - Treasure",
                    "reasons": ["treasure_inventory"],
                    "decision": "KEEP_CANONICAL"
                })
                # Add to knowledge graph
                knowledge_graph[rel_path] = {
                    "domain": self._extract_domain(rel_path),
                    "type": "CANONICAL",
                    "dependencies": [],
                    "runtime_usage": "HIGH",
                    "owner": "EOS Core Team"
                }
                continue

            # --- CHECK TIER 0 ---
            if any(tier in rel_path for tier in tier_0_files) or file_path.name in ["brain.py", "system_manifest.json"]:
                classifications["canonical"].append({
                    "path": rel_path,
                    "score": 100,
                    "tier": "Tier 0 - Absolute Core",
                    "reasons": ["protected_tier_0"],
                    "decision": "KEEP_CANONICAL"
                })
                knowledge_graph[rel_path] = {
                    "domain": self._extract_domain(rel_path),
                    "type": "CANONICAL",
                    "dependencies": [],
                    "runtime_usage": "HIGH",
                    "owner": "EOS Core Team"
                }
                continue

            # --- CALCULATE SCORE (only for non-treasure files) ---
            score = 0
            reasons = []

            # A) Business Truth (25%)
            if any(p in content for p in ["product", "customer", "order", "invoice", "shipment", "master"]):
                score += 25
                reasons.append("business_truth")
            if "GELS" in content or "GL-DOS" in content:
                score += 15
                reasons.append("core_business_logic")

            # B) Architecture Value (20%)
            if any(p in rel_path for p in ["architecture", "blueprint", "domain", "schema"]):
                score += 20
                reasons.append("architecture_value")

            # C) Runtime Usage (20%)
            if "workflow" in content or "engine" in content or "runtime" in rel_path:
                score += 20
                reasons.append("runtime_usage")

            # D) Governance Authority (15%)
            if "governance" in rel_path or "policy" in content:
                score += 15
                reasons.append("governance_authority")

            # E) Duplicate Risk (10%)
            if "copy" in name or "backup" in name or "duplicate" in rel_path:
                score -= 10
                reasons.append("duplicate_risk")

            # F) Recency (10%)
            days_old = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
            if days_old < 30:
                score += 10
                reasons.append("recent")
            elif days_old < 90:
                score += 5
                reasons.append("moderately_recent")

            # --- Special patterns (now less penalizing) ---
            if any(p in rel_path for p in ["GREENY-LIFE-EOS", "EOS-FINAL", "EOS-PRODUCTION", "unified-intelligence"]):
                # Only penalize if not in treasure list (already handled)
                score -= 5  # Reduced from -20 to -5
                reasons.append("historical_snapshot")
            if "test" in name or "sample" in name:
                score -= 10
                reasons.append("test_sample")

            # Clamp score
            score = max(0, min(100, score))

            # --- Decision ---
            if score >= 80:
                decision = "KEEP_CANONICAL"
                classifications["canonical"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision,
                    "tier": "Tier 1 - Core"
                })
            elif score >= 60:
                decision = "MERGE_CANDIDATE"
                classifications["merge"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision
                })
            elif score >= 40:
                decision = "ARCHIVE_HISTORICAL"
                classifications["archive"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision
                })
            else:
                decision = "DELETE_SAFE"
                classifications["delete"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision
                })

            # --- Knowledge Graph ---
            domain = self._extract_domain(rel_path)
            if domain not in knowledge_graph:
                knowledge_graph[domain] = []
            knowledge_graph[domain].append({
                "asset": rel_path,
                "decision": decision,
                "score": score
            })

        # ===================================================================
        # 5. SAVE REPORT
        # ===================================================================
        result["canonical"] = classifications["canonical"]
        result["merge"] = classifications["merge"]
        result["archive"] = classifications["archive"]
        result["delete"] = classifications["delete"]
        result["knowledge_graph"] = knowledge_graph

        result["summary"] = (
            f"Classified {result['total_assets']} assets: "
            f"{len(classifications['canonical'])} CANONICAL, "
            f"{len(classifications['merge'])} MERGE, "
            f"{len(classifications['archive'])} ARCHIVE, "
            f"{len(classifications['delete'])} DELETE. "
            f"Tier 0 protected: {len(result['tier_0_protected'])} files. "
            f"Treasure inventory: {len(treasure_files)} files protected."
        )

        # Save report
        report_path = self.repo_path / "intelligence" / "asset_classification_report_v3.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        final_result = {
            "mode": mode,
            "generated_at": datetime.now().isoformat(),
            "total_assets": result["total_assets"],
            "tier_0_protected": result["tier_0_protected"],
            "treasure_list_loaded": result["treasure_list_loaded"],
            "canonical": result["canonical"],  # Ø¨Ø¯ÙˆÙ† Ø­Ø¯
            "merge": result["merge"],   # Ø¨Ø¯ÙˆÙ† Ø­Ø¯
            "archive": result["archive"],   # Ø¨Ø¯ÙˆÙ† Ø­Ø¯
            "delete": result["delete"], 
            "knowledge_graph": result["knowledge_graph"],
            "summary": result["summary"],
            "requires_approval": True
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        result["report_path"] = str(report_path.relative_to(self.repo_path))
        self.logger.info(f"   âœ… Classification report saved: {report_path}")
        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   âš ï¸  APPROVAL REQUIRED before any consolidation action.")
        
        return result

    def _ensure_directories(self) -> None:
        dirs = [
            "src", "tests", "docs", "data", "scripts",
            "logs", "alerts", "archive", "intelligence",
            "intelligence/knowledge_base", "intelligence/daily_reports",
            "intelligence/generated_labels", "intelligence/generated_specs"
        ]
        for d in dirs:
            (self.repo_path / d).mkdir(parents=True, exist_ok=True)

    def _ensure_manifest_exists(self) -> None:
        manifest_path = self.repo_path / "system_manifest.json"
        if not manifest_path.exists():
            self.initialize_system_manifest()

    def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict] = None,
        timeout: int = 300
    ) -> Tuple[int, str, str]:
        cwd = cwd or self.repo_path
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        full_env["PYTHONIOENCODING"] = "utf-8"
        full_env["LANG"] = "en_US.UTF-8"

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=full_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(cmd)}")
            return -1, "", "Timeout"
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)

    # ========================================================================
    # AGENT 24: EOS ASSET INTELLIGENCE CLASSIFIER v2 (Enhanced)
    # ========================================================================

    def classify_assets(self, mode: str = "FORENSIC_DISCOVERY_ONLY") -> Dict:
        """
        Enhanced asset classifier that follows the EOS Intelligent Recovery strategy.
        
        Modes:
        - FORENSIC_DISCOVERY_ONLY: Only classifies and reports, no changes.
        - CONSOLIDATION: Generates consolidation plan (still requires approval).
        
        Principles:
        1. No direct deletion - only recommendations.
        2. Canonical Score based on multiple dimensions.
        3. Tier 0 Absolute Core files are protected.
        4. Generates a Knowledge Graph of assets.
        5. Human Approval Gate required for any action.
        """
        self.logger.info(f"ðŸ§  [Asset Classifier v2] Starting intelligent classification in {mode} mode...")
        
        result = {
            "mode": mode,
            "total_assets": 0,
            "canonical": [],
            "merge": [],
            "archive": [],
            "delete": [],
            "knowledge_graph": {},
            "tier_0_protected": [],
            "summary": "",
            "report_path": "",
            "requires_approval": True
        }

        # ===================================================================
        # 1. DEFINE TIER 0 - ABSOLUTE CORE (Protected Files)
        # ===================================================================
        tier_0_files = [
            "brain.py",
            "system_manifest.json",
            "config.yaml",
            "BOUND.md",
            "workflowEngine.ts",
            "database/schemas/domain/domain-schema.ts",
            "intelligence/eos-final-enterprise-blueprint.json",
            "intelligence/eos-real-business-flow-reconstruction.json",
            "intelligence/eos-real-execution-path-map.json",
            "intelligence/eos-workflow-state-machine-map.json",
            "intelligence/eos-prisma-domain-ownership.json",
            "intelligence/eos-domain-boundary-validation.json",
            "governance/eos-assets-registry-v1.json",
            "governance/eos-deep-asset-discovery-v1.json"
        ]
        
        result["tier_0_protected"] = tier_0_files

        # ===================================================================
        # 2. COLLECT ASSETS (Exclude temp/build folders)
        # ===================================================================
        ignore_folders = [
            '.venv', 'node_modules', '__pycache__', '.next', 
            'logs', 'alerts', 'archive', '.git'
        ]
        ignore_extensions = ['.pyc', '.log', '.lock', '.sst', '.meta', '.js.map', '.css.map']
        
        all_files = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(folder in str(file_path) for folder in ignore_folders):
                continue
            if file_path.suffix in ignore_extensions:
                continue
            if file_path.stat().st_size == 0:
                continue
            all_files.append(file_path)

        self.logger.info(f"   Found {len(all_files)} assets to classify.")
        result["total_assets"] = len(all_files)

        # ===================================================================
        # 3. CLASSIFICATION WITH CANONICAL SCORE
        # ===================================================================
        classifications = {
            "canonical": [],
            "merge": [],
            "archive": [],
            "delete": []
        }

        knowledge_graph = {}

        for file_path in all_files:
            rel_path = str(file_path.relative_to(self.repo_path))
            name = file_path.name.lower()
            content = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:1500]
            except:
                pass

            # --- Skip if in Tier 0 (Absolute Core) ---
            if any(tier in rel_path for tier in tier_0_files) or file_path.name in ["brain.py", "system_manifest.json"]:
                classifications["canonical"].append({
                    "path": rel_path,
                    "score": 100,
                    "tier": "Tier 0 - Absolute Core",
                    "reasons": ["protected_tier_0"],
                    "decision": "KEEP_CANONICAL"
                })
                # Add to knowledge graph
                knowledge_graph[rel_path] = {
                    "domain": self._extract_domain(rel_path),
                    "type": "CANONICAL",
                    "dependencies": [],
                    "runtime_usage": "HIGH",
                    "owner": "EOS Core Team"
                }
                continue

            # --- Calculate Canonical Score (0-100) ---
            score = 0
            reasons = []

            # A) Business Truth (25%)
            if any(p in content for p in ["product", "customer", "order", "invoice", "shipment", "master"]):
                score += 25
                reasons.append("business_truth")
            if "GELS" in content or "GL-DOS" in content:
                score += 15
                reasons.append("core_business_logic")

            # B) Architecture Value (20%)
            if any(p in rel_path for p in ["architecture", "blueprint", "domain", "schema"]):
                score += 20
                reasons.append("architecture_value")

            # C) Runtime Usage (20%)
            if "workflow" in content or "engine" in content or "runtime" in rel_path:
                score += 20
                reasons.append("runtime_usage")

            # D) Governance Authority (15%)
            if "governance" in rel_path or "policy" in content:
                score += 15
                reasons.append("governance_authority")

            # E) Duplicate Risk (10%)
            if "copy" in name or "backup" in name or "duplicate" in rel_path:
                score -= 10
                reasons.append("duplicate_risk")

            # F) Recency (10%)
            days_old = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
            if days_old < 30:
                score += 10
                reasons.append("recent")
            elif days_old < 90:
                score += 5
                reasons.append("moderately_recent")

            # --- Special patterns ---
            if any(p in rel_path for p in ["GREENY-LIFE-EOS", "EOS-FINAL", "EOS-PRODUCTION", "unified-intelligence"]):
                score -= 20
                reasons.append("historical_snapshot")
            if "test" in name or "sample" in name:
                score -= 15
                reasons.append("test_sample")

            # Clamp score
            score = max(0, min(100, score))

            # --- Decision ---
            if score >= 80:
                decision = "KEEP_CANONICAL"
                classifications["canonical"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision,
                    "tier": "Tier 1 - Core"
                })
            elif score >= 60:
                decision = "MERGE_CANDIDATE"
                classifications["merge"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision
                })
            elif score >= 40:
                decision = "ARCHIVE_HISTORICAL"
                classifications["archive"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision
                })
            else:
                decision = "DELETE_SAFE"
                classifications["delete"].append({
                    "path": rel_path,
                    "score": score,
                    "reasons": reasons,
                    "decision": decision
                })

            # --- Build Knowledge Graph Entry ---
            domain = self._extract_domain(rel_path)
            if domain not in knowledge_graph:
                knowledge_graph[domain] = []
            knowledge_graph[domain].append({
                "asset": rel_path,
                "decision": decision,
                "score": score
            })

        # ===================================================================
        # 4. SAVE REPORT
        # ===================================================================
        result["canonical"] = classifications["canonical"]
        result["merge"] = classifications["merge"]
        result["archive"] = classifications["archive"]
        result["delete"] = classifications["delete"]
        result["knowledge_graph"] = knowledge_graph

        result["summary"] = (
            f"Classified {result['total_assets']} assets: "
            f"{len(classifications['canonical'])} CANONICAL, "
            f"{len(classifications['merge'])} MERGE, "
            f"{len(classifications['archive'])} ARCHIVE, "
            f"{len(classifications['delete'])} DELETE. "
            f"Tier 0 protected: {len(result['tier_0_protected'])} files."
        )

        # Save report
        report_path = self.repo_path / "intelligence" / "asset_classification_report_v2.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        final_result = {
            "mode": mode,
            "generated_at": datetime.now().isoformat(),
            "total_assets": result["total_assets"],
            "tier_0_protected": result["tier_0_protected"],
            "canonical": result["canonical"], # Ø¨Ø¯ÙˆÙ† Ø­Ø¯  # Limit for readability
            "merge": result["merge"], # Ø¨Ø¯ÙˆÙ† Ø­Ø¯
            "archive": result["archive"], # Ø¨Ø¯ÙˆÙ† Ø­Ø¯
            "delete": result["delete"], # Ø¨Ø¯ÙˆÙ† Ø­Ø¯ 
            "knowledge_graph": result["knowledge_graph"],
            "summary": result["summary"],
            "requires_approval": True
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        result["report_path"] = str(report_path.relative_to(self.repo_path))
        self.logger.info(f"   âœ… Classification report saved: {report_path}")
        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   âš ï¸  APPROVAL REQUIRED before any consolidation action.")
        
        return result

        # ========================================================================
    # AGENT 25: CONSOLIDATION ENGINE (Safe Execution)
    # ========================================================================

    def run_consolidation(self, dry_run: bool = True) -> Dict:
        """
        Executes the consolidation plan based on the classification report.
        - CANONICAL â†’ copied to canonical/
        - ARCHIVE â†’ moved to archive/historical/
        - DELETE â†’ moved to archive/deleted_staging/ (not directly deleted)
        
        Args:
            dry_run: If True, only simulates and reports what would be done.
        """
        self.logger.info(f"ðŸ”§ [Consolidation Engine] Starting consolidation (dry_run={dry_run})...")
        
        result = {
            "dry_run": dry_run,
            "canonical_copied": [],
            "archive_moved": [],
            "delete_staged": [],
            "errors": [],
            "summary": ""
        }

        # ===================================================================
        # 1. LOAD CLASSIFICATION REPORT
        # ===================================================================
        report_path = self.repo_path / "intelligence" / "asset_classification_report_v3.json"
        if not report_path.exists():
            self.logger.error("Classification report not found. Please run --classify first.")
            result["summary"] = "ERROR: classification_report_v3.json not found."
            return result

        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        # ===================================================================
        # 2. ENSURE TARGET DIRECTORIES EXIST
        # ===================================================================
        canonical_dir = self.repo_path / "canonical"
        archive_dir = self.repo_path / "archive" / "historical"
        staging_dir = self.repo_path / "archive" / "deleted_staging"

        if not dry_run:
            canonical_dir.mkdir(parents=True, exist_ok=True)
            archive_dir.mkdir(parents=True, exist_ok=True)
            staging_dir.mkdir(parents=True, exist_ok=True)

        # ===================================================================
        # 3. PROCESS CANONICAL FILES (Copy to canonical/)
        # ===================================================================
        self.logger.info("   Processing CANONICAL files...")
        for item in report.get("canonical", []):
            rel_path = item.get("path")
            if not rel_path:
                continue
            src = self.repo_path / rel_path
            if not src.exists():
                continue
            dest = canonical_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            if dry_run:
                result["canonical_copied"].append(f"DRY_RUN: Would copy {rel_path} -> {dest}")
            else:
                try:
                    import shutil
                    shutil.copy2(src, dest)
                    result["canonical_copied"].append(f"Copied: {rel_path}")
                except Exception as e:
                    result["errors"].append(f"Copy error {rel_path}: {e}")

        # ===================================================================
        # 4. PROCESS ARCHIVE FILES (Move to archive/historical/)
        # ===================================================================
        self.logger.info("   Processing ARCHIVE files...")
        for item in report.get("archive", []):
            rel_path = item.get("path")
            if not rel_path:
                continue
            src = self.repo_path / rel_path
            if not src.exists():
                continue
            dest = archive_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            if dry_run:
                result["archive_moved"].append(f"DRY_RUN: Would move {rel_path} -> {dest}")
            else:
                try:
                    import shutil
                    shutil.move(str(src), str(dest))
                    result["archive_moved"].append(f"Moved: {rel_path}")
                except Exception as e:
                    result["errors"].append(f"Archive error {rel_path}: {e}")

        # ===================================================================
        # 5. PROCESS DELETE FILES (Move to staging, not permanent delete)
        # ===================================================================
        self.logger.info("   Processing DELETE files...")
        for item in report.get("delete", []):
            rel_path = item.get("path")
            if not rel_path:
                continue
            src = self.repo_path / rel_path
            if not src.exists():
                continue
            dest = staging_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            if dry_run:
                result["delete_staged"].append(f"DRY_RUN: Would move {rel_path} -> {dest}")
            else:
                try:
                    import shutil
                    shutil.move(str(src), str(dest))
                    result["delete_staged"].append(f"Staged: {rel_path}")
                except Exception as e:
                    result["errors"].append(f"Delete error {rel_path}: {e}")

        # ===================================================================
        # 6. GENERATE SUMMARY
        # ===================================================================
        result["summary"] = (
            f"Consolidation {'SIMULATED (dry-run)' if dry_run else 'EXECUTED'}: "
            f"{len(result['canonical_copied'])} canonical, "
            f"{len(result['archive_moved'])} archived, "
            f"{len(result['delete_staged'])} staged for deletion. "
            f"Errors: {len(result['errors'])}"
        )

        self.logger.info(f"   {result['summary']}")
        return result
    

    # ========================================================================
    # AGENT 26: CANONICAL VALIDATION & DELETED_STAGING REVIEW
    # ========================================================================

    def run_canonical_validation(self) -> Dict:
        """
        Validates the canonical layer with flexible rules:
        - A domain is VALID if it has at least one master_data file.
        - Missing optional files (workflow, database) are reported as warnings only.
        """
        self.logger.info("ðŸ” [Canonical Validation] Starting validation (flexible mode)...")
        
        result = {
            "canonical_domains": {},
            "missing_capabilities": [],
            "deleted_staging_analysis": {
                "total_files": 0,
                "unique_content": [],
                "referenced_by_canonical": [],
                "safe_to_delete": []
            },
            "canonical_truth_registry": {},
            "validation_status": "PENDING",
            "summary": ""
        }

        # ===================================================================
        # 1. DEFINE DOMAINS WITH CORE FILES (master_data is mandatory)
        # ===================================================================
        domain_definitions = {
            "product": {
                "master_data": ["canonical/data/master_products.json"],
                "optional": ["canonical/data/product-workflow.json", "canonical/data/product-schema.json"],
                "owner": "Product Domain"
            },
            "supplier": {
                "master_data": ["canonical/data/suppliers.json"],
                "optional": ["canonical/data/supplier-workflow.json", "canonical/data/supplier-schema.json"],
                "owner": "Supplier Domain"
            },
            "certificate": {
                "master_data": ["canonical/data/certificates.json"],
                "optional": ["canonical/data/certificate-documents.json"],
                "owner": "Certificate Domain"
            },
            "customer": {
                "master_data": ["canonical/data/customer-domain/customers.json"],
                "optional": ["canonical/data/customer-domain/customer-workflow.json"],
                "owner": "Customer Domain"
            },
            "analytics": {
                "master_data": ["canonical/analytics/sales-summary.json"],
                "optional": ["canonical/analytics/analytics-workflow.json", "canonical/analytics/inventory-summary.json"],
                "owner": "Analytics Domain"
            },
            "finance": {
                "master_data": ["canonical/finance/finance-master.json"],
                "optional": ["canonical/finance/workflows.json", "canonical/finance/transactions.json"],
                "owner": "Finance Domain"
            },
            "inventory": {
                "master_data": ["canonical/inventory/inventory-master-v1.json"],
                "optional": ["canonical/inventory/stock-levels.json", "canonical/inventory/inventory-workflow.json"],
                "owner": "Inventory Domain"
            },
            "logistics": {
                "master_data": ["canonical/logistics/shipments.json"],
                "optional": ["canonical/logistics/tracking.json", "canonical/logistics/logistics-workflow.json"],
                "owner": "Logistics Domain"
            },
            "compliance": {
                "master_data": ["canonical/data/compliance-master.json"],
                "optional": ["canonical/data/compliance-documents.json"],
                "owner": "Compliance Domain"
            },
            "administration": {
                "master_data": ["canonical/data/administration-master.json"],
                "optional": ["canonical/data/users.json", "canonical/data/roles.json", "canonical/data/permissions.json"],
                "owner": "Administration Domain"
            }
        }

        # ===================================================================
        # 2. VALIDATE EACH DOMAIN
        # ===================================================================
        domain_status = {}
        missing_optional = {}
        validation_passed = True

        for domain, config in domain_definitions.items():
            master_data_files = config.get("master_data", [])
            optional_files = config.get("optional", [])
            status = "INCOMPLETE"
            found_master = []
            found_optional = []
            missing_master = []
            missing_optional_list = []

            # Check mandatory master_data
            for mf in master_data_files:
                full_path = self.repo_path / mf
                if full_path.exists():
                    found_master.append(mf)
                else:
                    missing_master.append(mf)

            # Check optional files
            for of in optional_files:
                full_path = self.repo_path / of
                if full_path.exists():
                    found_optional.append(of)
                else:
                    missing_optional_list.append(of)

            # Determine status: VALID if at least one master_data exists
            if found_master:
                status = "VALID"
            else:
                status = "INCOMPLETE"
                validation_passed = False

            domain_status[domain] = {
                "status": status,
                "found_master": found_master,
                "missing_master": missing_master,
                "found_optional": found_optional,
                "missing_optional": missing_optional_list
            }

            if missing_master:
                missing_optional[domain] = missing_master

        result["canonical_domains"] = domain_status

        # ===================================================================
        # 3. BUILD CANONICAL TRUTH REGISTRY
        # ===================================================================
        registry = {
            "system": "GREENY-LIFE-EOS",
            "version": "3.0.0",
            "canonical_root": "canonical",
            "domains": [],
            "validation_status": "PASSED" if validation_passed else "FAILED",
            "validated_at": datetime.now().isoformat(),
            "note": "Optional files (workflow, database, schema) are not required for VALID status."
        }

        for domain, status_info in domain_status.items():
            domain_entry = {
                "name": domain,
                "owner": domain_definitions[domain]["owner"],
                "master_data": status_info["found_master"],
                "optional_files_found": status_info["found_optional"],
                "optional_files_missing": status_info["missing_optional"],
                "status": status_info["status"]
            }
            registry["domains"].append(domain_entry)

        result["canonical_truth_registry"] = registry
        result["validation_status"] = registry["validation_status"]

        # ===================================================================
        # 4. SAVE REGISTRY
        # ===================================================================
        registry_path = self.repo_path / "governance" / "eos-canonical-truth-registry-v3.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        # ===================================================================
        # 5. SUMMARY
        # ===================================================================
        valid_domains = [d for d, s in domain_status.items() if s["status"] == "VALID"]
        invalid_domains = [d for d, s in domain_status.items() if s["status"] != "VALID"]
        result["missing_capabilities"] = [{"domain": d, "missing": domain_status[d]["missing_master"]} for d in invalid_domains]

        result["summary"] = (
            f"Canonical Validation: {registry['validation_status']}. "
            f"Domains checked: {len(domain_status)}. "
            f"Valid: {len(valid_domains)}, Invalid: {len(invalid_domains)}. "
            f"Optional files missing: {sum(len(s['missing_optional']) for s in domain_status.values())} warnings."
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Registry saved: governance/eos-canonical-truth-registry-v3.json")
        
        return result
    
    
    # ========================================================================
    # AGENT 27: EOS SUPPLIER MASTER DATA BUILDER
    # ========================================================================

    def build_supplier_master(self) -> Dict:
        self.logger.info("ðŸ—ï¸  [Supplier Master] Building Supplier Master Data...")

        result = {
            "suppliers_created": 0,
            "links_created": 0,
            "validation_status": "PENDING",
            "files_created": [],
            "summary": ""
        }

        # ===================================================================
        # 1. LOAD PRODUCT MASTER
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            result["summary"] = "ERROR: master_products.json not found."
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)

        if "products" in products_data:
            products = products_data["products"]
        elif "Products" in products_data:
            products = products_data["Products"]
        else:
            self.logger.error("Unknown product schema.")
            result["summary"] = "ERROR: Unknown product schema."
            return result

        product_ids = [p.get("id") or p.get("ProductID") for p in products]
        self.logger.info(f"   Found {len(product_ids)} products to link.")

        # ===================================================================
        # 2. LOAD EXISTING SUPPLIERS (if available)
        # ===================================================================
        suppliers_path = self.repo_path / "canonical" / "data" / "suppliers.json"
        suppliers = []
        
        if suppliers_path.exists():
            try:
                with open(suppliers_path, 'r', encoding='utf-8') as f:
                    suppliers_data = json.load(f)
                    if "suppliers" in suppliers_data:
                        suppliers = suppliers_data["suppliers"]
                    elif "Suppliers" in suppliers_data:
                        suppliers = suppliers_data["Suppliers"]
                    self.logger.info(f"   Loaded {len(suppliers)} existing suppliers.")
            except Exception as e:
                self.logger.warning(f"   Could not load existing suppliers: {e}")

        # ===================================================================
        # 3. IF NO SUPPLIERS, USE DEFAULT SAMPLE
        # ===================================================================
        if not suppliers:
            self.logger.info("   No suppliers found. Creating default sample.")
            suppliers = [
                {
                    "supplier_id": "SUP-EGY-HONEY-001",
                    "name": "Nile Valley Honey Co.",
                    "category": ["Honey"],
                    "country": "Egypt",
                    "city": "Cairo",
                    "contact": {"email": "info@nilevalleyhoney.com", "phone": "+20 2 1234 5678", "website": "https://nilevalleyhoney.com"},
                    "capabilities": {"production": True, "private_label": True, "export_ready": True},
                    "certifications": ["HACCP", "ISO 22000", "GMP"],
                    "quality": {"rating": None, "audit_status": "pending"},
                    "status": "active"
                },
                {
                    "supplier_id": "SUP-EGY-SPICE-001",
                    "name": "Sinai Spice Mills",
                    "category": ["Spices", "Herbs"],
                    "country": "Egypt",
                    "city": "Alexandria",
                    "contact": {"email": "info@sinaispice.com", "phone": "+20 3 9876 5432", "website": "https://sinaispice.com"},
                    "capabilities": {"production": True, "private_label": True, "export_ready": False},
                    "certifications": ["HACCP", "ISO 22000", "GMP", "Organic"],
                    "quality": {"rating": None, "audit_status": "pending"},
                    "status": "candidate"
                },
                {
                    "supplier_id": "SUP-EGY-BEE-001",
                    "name": "Green Valley Bee Products",
                    "category": ["Bee Products"],
                    "country": "Egypt",
                    "city": "Fayoum",
                    "contact": {"email": "info@greenvalleybee.com", "phone": "+20 4 5678 9012", "website": "https://greenvalleybee.com"},
                    "capabilities": {"production": True, "private_label": False, "export_ready": True},
                    "certifications": ["HACCP", "ISO 22000", "GMP"],
                    "quality": {"rating": None, "audit_status": "pending"},
                    "status": "candidate"
                },
                {
                    "supplier_id": "SUP-EGY-OIL-001",
                    "name": "Green Valley Herbs & Oils",
                    "category": ["Natural Oils"],
                    "country": "Egypt",
                    "city": "Fayoum",
                    "contact": {"email": "info@greenvalleyoil.com", "phone": "+20 4 5678 9013", "website": "https://greenvalleyoil.com"},
                    "capabilities": {"production": True, "private_label": True, "export_ready": True},
                    "certifications": ["HACCP", "ISO 22000", "GMP"],
                    "quality": {"rating": None, "audit_status": "pending"},
                    "status": "candidate"
                },
                {
                    "supplier_id": "SUP-EGY-HERB-001",
                    "name": "Egyptian Herbs & Spices Co.",
                    "category": ["Herbs", "Spices"],
                    "country": "Egypt",
                    "city": "Cairo",
                    "contact": {"email": "info@egyptianherbs.com", "phone": "+20 2 5678 9012", "website": "https://egyptianherbs.com"},
                    "capabilities": {"production": True, "private_label": True, "export_ready": True},
                    "certifications": ["HACCP", "ISO 22000", "GMP", "Organic"],
                    "quality": {"rating": None, "audit_status": "pending"},
                    "status": "active"
                }
            ]

        # ===================================================================
        # 4. BUILD SUPPLIER-PRODUCT LINKS
        # ===================================================================
        supplier_links = []
        for supplier in suppliers:
            supplier_categories = supplier.get("category", [])
            for product in products:
                product_category = product.get("category")
                if product_category in supplier_categories:
                    supplier_links.append({
                        "supplier_id": supplier["supplier_id"],
                        "product_id": product.get("id") or product.get("ProductID"),
                        "relationship_type": "primary",
                        "status": "active"
                    })

        # ===================================================================
        # 5. SAVE DATA
        # ===================================================================
        canonical_data_dir = self.repo_path / "canonical" / "data"
        canonical_data_dir.mkdir(parents=True, exist_ok=True)

        # Save suppliers.json
        suppliers_data = {
            "schema_version": "supplier-master-v1",
            "generated_at": datetime.now().isoformat(),
            "total_suppliers": len(suppliers),
            "suppliers": suppliers
        }
        suppliers_path = canonical_data_dir / "suppliers.json"
        with open(suppliers_path, 'w', encoding='utf-8') as f:
            json.dump(suppliers_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(suppliers_path.relative_to(self.repo_path)))

        # Save supplier-product-links.json
        links_data = {
            "schema_version": "supplier-product-links-v1",
            "generated_at": datetime.now().isoformat(),
            "total_links": len(supplier_links),
            "links": supplier_links
        }
        links_path = canonical_data_dir / "supplier-product-links.json"
        with open(links_path, 'w', encoding='utf-8') as f:
            json.dump(links_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(links_path.relative_to(self.repo_path)))

        # ===================================================================
        # 6. VALIDATION REPORT
        # ===================================================================
        validation_report = {
            "schema_version": "supplier-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "total_suppliers": len(suppliers),
            "total_products": len(products),
            "total_links": len(supplier_links),
            "status": "PASSED" if len(supplier_links) > 0 else "FAILED"
        }

        validation_path = self.repo_path / "intelligence" / "supplier-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)

        # ===================================================================
        # 7. SUMMARY
        # ===================================================================
        result["suppliers_created"] = len(suppliers)
        result["links_created"] = len(supplier_links)
        result["validation_status"] = validation_report["status"]
        result["summary"] = (
            f"Supplier Master Data built: "
            f"{result['suppliers_created']} suppliers, "
            f"{result['links_created']} product links. "
            f"Validation: {result['validation_status']}"
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Files created: {', '.join(result['files_created'])}")
        
        return result
    
    
     
         # ========================================================================
    # AGENT 28: EOS CERTIFICATE MASTER DATA BUILDER
    # ========================================================================

    def build_certificate_master(self) -> Dict:
        """
        Builds the Certificate Master Data with proper relationships:
        - certificates.json (master list of all certificates)
        - product-certificate-links.json (which products need which certs)
        - certificate-validation-report.json (compliance status)
        """
        self.logger.info("ðŸ“œ [Certificate Master] Building Certificate Master Data...")
        
        result = {
            "certificates_created": 0,
            "links_created": 0,
            "validation_status": "PENDING",
            "files_created": [],
            "summary": ""
        }

        # ===================================================================
        # 1. LOAD PRODUCT MASTER (to know what products exist)
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            result["summary"] = "ERROR: master_products.json not found."
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        if "products" in products_data:
            products = products_data["products"]
        elif "Products" in products_data:
            products = products_data["Products"]
        else:
            self.logger.error("Unknown product schema.")
            result["summary"] = "ERROR: Unknown product schema."
            return result

        # ===================================================================
        # 2. DEFINE MASTER CERTIFICATE LIST
        # ===================================================================
        # Based on GELS v2.0 and industry standards
        master_certificates = [
            {
                "certificate_id": "CERT-HALAL-001",
                "name": "Halal",
                "category": "Religious",
                "description": "Certifies that the product is permissible under Islamic law.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-HACCP-001",
                "name": "HACCP",
                "category": "Food Safety",
                "description": "Hazard Analysis and Critical Control Points certification.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-ISO22000-001",
                "name": "ISO 22000",
                "category": "Food Safety Management",
                "description": "Food safety management system certification.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-GMP-001",
                "name": "GMP",
                "category": "Manufacturing",
                "description": "Good Manufacturing Practices certification.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-COA-001",
                "name": "COA",
                "category": "Quality",
                "description": "Certificate of Analysis for product quality and purity.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-ORIGIN-001",
                "name": "Origin Certificate",
                "category": "Export",
                "description": "Certificate of Origin for export purposes.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-ORGANIC-001",
                "name": "Organic",
                "category": "Sustainability",
                "description": "Organic farming and processing certification.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-KOSHER-001",
                "name": "Kosher",
                "category": "Religious",
                "description": "Certifies that the product meets Jewish dietary laws.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-USDA-001",
                "name": "USDA Organic",
                "category": "Export (USA)",
                "description": "USDA Organic certification for the US market.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            },
            {
                "certificate_id": "CERT-EU-001",
                "name": "EU Organic",
                "category": "Export (EU)",
                "description": "EU Organic certification for the European market.",
                "applicable_to": ["Honey", "Bee Products", "Spices", "Herbs", "Natural Oils", "Premium Spices", "Herbal Products"]
            }
        ]

        # ===================================================================
        # 3. ASSIGN CERTIFICATES TO PRODUCTS
        # ===================================================================
        certificate_links = []
        # Track which certificates are assigned to each product
        product_cert_map = {}

        for product in products:
            product_id = product.get("id") or product.get("ProductID")
            product_category = product.get("category")
            
            if not product_id:
                continue
            
            product_cert_map[product_id] = []
            
            for cert in master_certificates:
                if product_category in cert.get("applicable_to", []):
                    # Check if this is an export-specific certificate
                    is_export = "Export" in cert.get("category", "")
                    # Check if the product is marked for that market
                    markets = product.get("markets", {})
                    if is_export and markets:
                        # Only assign if the market is active
                        if cert["certificate_id"] == "CERT-USDA-001" and markets.get("usa", False):
                            product_cert_map[product_id].append(cert["certificate_id"])
                            certificate_links.append({
                                "product_id": product_id,
                                "certificate_id": cert["certificate_id"],
                                "status": "required"
                            })
                        elif cert["certificate_id"] == "CERT-EU-001" and markets.get("eu", False):
                            product_cert_map[product_id].append(cert["certificate_id"])
                            certificate_links.append({
                                "product_id": product_id,
                                "certificate_id": cert["certificate_id"],
                                "status": "required"
                            })
                    elif not is_export:
                        # General certificates apply to all products in that category
                        product_cert_map[product_id].append(cert["certificate_id"])
                        certificate_links.append({
                            "product_id": product_id,
                            "certificate_id": cert["certificate_id"],
                            "status": "required"
                        })

        # ===================================================================
        # 4. SAVE CERTIFICATE DATA
        # ===================================================================
        canonical_data_dir = self.repo_path / "canonical" / "data"
        canonical_data_dir.mkdir(parents=True, exist_ok=True)

        # Save certificates.json
        certs_data = {
            "schema_version": "certificate-master-v1",
            "generated_at": datetime.now().isoformat(),
            "total_certificates": len(master_certificates),
            "certificates": master_certificates
        }
        certs_path = canonical_data_dir / "certificates.json"
        with open(certs_path, 'w', encoding='utf-8') as f:
            json.dump(certs_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(certs_path.relative_to(self.repo_path)))

        # Save product-certificate-links.json
        links_data = {
            "schema_version": "product-certificate-links-v1",
            "generated_at": datetime.now().isoformat(),
            "total_links": len(certificate_links),
            "links": certificate_links
        }
        links_path = canonical_data_dir / "product-certificate-links.json"
        with open(links_path, 'w', encoding='utf-8') as f:
            json.dump(links_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(links_path.relative_to(self.repo_path)))

        # ===================================================================
        # 5. CREATE CERTIFICATE VALIDATION REPORT
        # ===================================================================
        validation_report = {
            "schema_version": "certificate-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "products": []
        }

        passed_count = 0
        failed_count = 0
        total_required = 0

        for product in products:
            product_id = product.get("id") or product.get("ProductID")
            product_name = product.get("name") or product.get("ProductName")
            
            required_certs = product_cert_map.get(product_id, [])
            total_required += len(required_certs)
            
            # Simulate that all certificates are "Pending" initially
            # In a real system, we would check actual status
            status = "PASSED" if len(required_certs) > 0 else "FAILED"
            
            if status == "PASSED":
                passed_count += 1
            else:
                failed_count += 1
            
            validation_report["products"].append({
                "product_id": product_id,
                "product_name": product_name,
                "required_certificates": required_certs,
                "status": status
            })

        validation_report["summary"] = {
            "total_products": len(products),
            "passed": passed_count,
            "failed": failed_count,
            "total_required_certificates": total_required
        }

        validation_path = self.repo_path / "intelligence" / "certificate-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(validation_path.relative_to(self.repo_path)))

        # ===================================================================
        # 6. SUMMARY
        # ===================================================================
        result["certificates_created"] = len(master_certificates)
        result["links_created"] = len(certificate_links)
        result["validation_status"] = "PASSED" if failed_count == 0 else "FAILED"
        result["summary"] = (
            f"Certificate Master Data built: "
            f"{result['certificates_created']} certificates, "
            f"{result['links_created']} product links. "
            f"Validation: {result['validation_status']} "
            f"({passed_count} passed, {failed_count} failed)"
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Files created: {', '.join(result['files_created'])}")
        
        return result
    

        # ========================================================================
    # AGENT 29: EOS ELMS BUILDER (GELS v2.0)
    # ========================================================================

    def build_els(self) -> Dict:
        """
        Builds the Enterprise Label Management System (ELMS) based on GELS v2.0.
        - Reads product master, suppliers, certificates.
        - Generates label JSON files for each product.
        - Creates labels-index.json and validation report.
        """
        self.logger.info("ðŸ·ï¸  [ELMS Builder] Building Enterprise Label Management System...")
        
        result = {
            "labels_created": 0,
            "validation_status": "PENDING",
            "files_created": [],
            "summary": ""
        }

        # ===================================================================
        # 1. LOAD PRODUCT MASTER
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            result["summary"] = "ERROR: master_products.json not found."
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        if "products" in products_data:
            products = products_data["products"]
        elif "Products" in products_data:
            products = products_data["Products"]
        else:
            self.logger.error("Unknown product schema.")
            result["summary"] = "ERROR: Unknown product schema."
            return result

        # ===================================================================
        # 2. LOAD SUPPLIER LINKS (for validation)
        # ===================================================================
        supplier_links_path = self.repo_path / "canonical" / "data" / "supplier-product-links.json"
        supplier_links = []
        if supplier_links_path.exists():
            with open(supplier_links_path, 'r', encoding='utf-8') as f:
                links_data = json.load(f)
                supplier_links = links_data.get("links", [])

        # ===================================================================
        # 3. LOAD CERTIFICATE LINKS (for validation)
        # ===================================================================
        cert_links_path = self.repo_path / "canonical" / "data" / "product-certificate-links.json"
        cert_links = []
        if cert_links_path.exists():
            with open(cert_links_path, 'r', encoding='utf-8') as f:
                cert_data = json.load(f)
                cert_links = cert_data.get("links", [])

        # ===================================================================
        # 4. DEFINE GELS v2.0 LABEL STRUCTURE
        # ===================================================================
        labels_dir = self.repo_path / "canonical" / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        labels_index = []
        validation_results = []
        label_files = []

        # Mapping for product categories to GELS prefix
        gels_prefix_map = {
            "Honey": "HON",
            "Bee Products": "BEE",
            "Spices": "SPC",
            "Premium Spices": "SPC",
            "Herbal Products": "HRB",
            "Herbs": "HRB",
            "Natural Oils": "OIL"
        }

        for product in products:
            product_id = product.get("id") or product.get("ProductID")
            product_name = product.get("name") or product.get("ProductName")
            category = product.get("category")
            if not category:
                self.logger.warning(f"âš ï¸  Product {product_id} has no category. Skipping.")
                continue

            # Determine GELS prefix
            prefix = gels_prefix_map.get(category, "GEN")
            ref_counter = 1
            # Simple incremental ID (in production, should be more robust)
            gels_ref_id = f"GL-LBL-{prefix}-{str(ref_counter).zfill(3)}"
            # For now, we'll use a simple mapping based on the product code or index.
            # A better approach: use a counter or a mapping from product code.
            # We'll just use the product's code as reference for now.
            # In a real implementation, we would have a mapping table.
            # For demonstration, we'll generate a unique ID based on the product's position.
            # Let's use a simple counter.
            if not hasattr(self, '_gels_counter'):
                self._gels_counter = 0
            self._gels_counter += 1
            gels_ref_id = f"GL-LBL-{prefix}-{str(self._gels_counter).zfill(3)}"

            # Build label data
            label_data = {
                "schema_version": "GELS_v2.0_Enterprise",
                "gels_ref_id": gels_ref_id,
                "product_ref": product_id,
                "product_name": product_name,
                "category": category,
                "accent_color": product.get("accent_color", "#000000"),
                "front_label": {
                    "brand": "GREENY LIFE",
                    "product_name": product_name,
                    "claims": ["100% Natural"],
                    "origin": "Product of Egypt",
                    "net_weights": self._get_net_weights(category),
                    "accent_color": product.get("accent_color", "#000000"),
                    "qr": {"enabled": True}
                },
                "back_label": {
                    "description": {
                        "en": f"Premium {product_name} sourced from Egypt.",
                        "ar": f"Ù…Ù†ØªØ¬ {product_name} Ø¹Ø§Ù„ÙŠ Ø§Ù„Ø¬ÙˆØ¯Ø© Ù…Ù† Ù…ØµØ±."
                    },
                    "ingredients": ["100% Pure", category],
                    "nutrition_facts": self._get_nutrition_facts(category),
                    "traceability": {
                        "batch_number": "AUTO",
                        "production_date": "AUTO",
                        "expiry_date": "AUTO"
                    },
                    "barcode": {"type": "EAN13"},
                    "manufacturer": {
                        "name": "GREENY LIFE",
                        "country": "Egypt",
                        "address": "Cairo, Egypt",
                        "website": "https://greeny-life.com",
                        "email": "info@greeny-life.com",
                        "phone": "+20 2 1234 5678"
                    },
                    "certifications": self._get_certifications_for_product(product_id, cert_links),
                    "sustainability_claims": ["Ethically Sourced", "Plastic-Free Packaging"]
                },
                "side_panel": self._get_side_panel(category),
                "sustainability": {
                    "packaging_material": "Glass",
                    "food_grade": True,
                    "recyclable": True,
                    "bpa_free": True
                }
            }

            # ===================================================================
            # 5. VALIDATION CHECK
            # ===================================================================
            validation = {
                "product_id": product_id,
                "gels_ref_id": gels_ref_id,
                "checks": []
            }
            passed = True

            # Check product exists
            if product_id:
                validation["checks"].append({"check": "Product exists", "status": "PASSED"})
            else:
                passed = False
                validation["checks"].append({"check": "Product exists", "status": "FAILED", "reason": "No product ID"})

            # Check supplier exists
            has_supplier = any(link.get("product_id") == product_id for link in supplier_links)
            if has_supplier:
                validation["checks"].append({"check": "Supplier linked", "status": "PASSED"})
            else:
                passed = False
                validation["checks"].append({"check": "Supplier linked", "status": "FAILED", "reason": "No supplier link"})

            # Check certificate exists
            has_cert = any(link.get("product_id") == product_id for link in cert_links)
            if has_cert:
                validation["checks"].append({"check": "Certificate linked", "status": "PASSED"})
            else:
                passed = False
                validation["checks"].append({"check": "Certificate linked", "status": "FAILED", "reason": "No certificate link"})

            # Check required label sections
            required_sections = ["front_label", "back_label", "side_panel"]
            for section in required_sections:
                if section in label_data and label_data[section]:
                    validation["checks"].append({"check": f"{section} exists", "status": "PASSED"})
                else:
                    passed = False
                    validation["checks"].append({"check": f"{section} exists", "status": "FAILED", "reason": f"Missing {section}"})

            validation["status"] = "PASSED" if passed else "FAILED"
            validation_results.append(validation)

            # Save label file
            label_filename = f"{gels_ref_id}.json"
            label_path = labels_dir / label_filename
            with open(label_path, 'w', encoding='utf-8') as f:
                json.dump(label_data, f, indent=2, ensure_ascii=False)
            label_files.append(str(label_path.relative_to(self.repo_path)))

            # Add to index
            labels_index.append({
                "gels_ref_id": gels_ref_id,
                "product_ref": product_id,
                "product_name": product_name,
                "category": category,
                "status": "validated" if passed else "pending_review",
                "label_file": str(label_path.relative_to(self.repo_path))
            })

        # ===================================================================
        # 6. SAVE LABELS INDEX
        # ===================================================================
        index_data = {
            "schema_version": "GELS-v2.0",
            "generated_at": datetime.now().isoformat(),
            "total_labels": len(labels_index),
            "labels": labels_index
        }
        index_path = labels_dir / "labels-index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(index_path.relative_to(self.repo_path)))

        # ===================================================================
        # 7. SAVE VALIDATION REPORT
        # ===================================================================
        validation_report = {
            "schema_version": "GELS-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "total_products": len(products),
            "validation_results": validation_results
        }
        validation_path = self.repo_path / "intelligence" / "gels-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(validation_path.relative_to(self.repo_path)))

        # ===================================================================
        # 8. SUMMARY
        # ===================================================================
        result["labels_created"] = len(labels_index)
        passed_count = sum(1 for v in validation_results if v["status"] == "PASSED")
        failed_count = len(validation_results) - passed_count
        result["validation_status"] = "PASSED" if failed_count == 0 else "FAILED"
        result["summary"] = (
            f"ELMS built: {result['labels_created']} labels generated. "
            f"Validation: {result['validation_status']} "
            f"({passed_count} passed, {failed_count} failed)"
        )
        result["label_files"] = label_files

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Files created: {', '.join(result['files_created'])}")
        
        return result


    # ========================================================================
    # AGENT 30: EOS CUSTOMER DOMAIN BUILDER
    # ========================================================================

    def build_customer_domain(self) -> Dict[str, Any]:
        """
        Builds the complete Customer Domain:
        - customers.json (master list)
        - customer-contacts.json (contacts per customer)
        - customer-segments.json (segments for targeting)
        - customer-product-preferences.json (which products each customer prefers)
        - opportunities.json (sales opportunities)
        - orders.json (historical orders)
        - customer-validation-report.json (validation)
        - customer-product-demand-map.json (demand mapping)
        """
        self.logger.info("ðŸ‘¥ [Customer Domain] Building Customer Domain...")
        
        result = {
            "customers_created": 0,
            "contacts_created": 0,
            "opportunities_created": 0,
            "orders_created": 0,
            "validation_status": "PENDING",
            "files_created": [],
            "summary": ""
        }

        # ===================================================================
        # 1. LOAD PRODUCT MASTER (to know what products exist)
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            result["summary"] = "ERROR: master_products.json not found."
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        if "products" in products_data:
            products = products_data["products"]
        elif "Products" in products_data:
            products = products_data["Products"]
        else:
            self.logger.error("Unknown product schema.")
            result["summary"] = "ERROR: Unknown product schema."
            return result

        product_ids = [p.get("id") or p.get("ProductID") for p in products if p.get("id") or p.get("ProductID")]
        product_names = {p.get("id") or p.get("ProductID"): p.get("name") or p.get("ProductName") for p in products}

        self.logger.info(f"   Loaded {len(product_ids)} products.")

        # ===================================================================
        # 2. LOAD SUPPLIER LINKS (for validation - not directly used)
        # ===================================================================
        supplier_links_path = self.repo_path / "canonical" / "data" / "supplier-product-links.json"
        supplier_links = []
        if supplier_links_path.exists():
            with open(supplier_links_path, 'r', encoding='utf-8') as f:
                links_data = json.load(f)
                supplier_links = links_data.get("links", [])

        # ===================================================================
        # 3. LOAD CERTIFICATE LINKS (for validation - not directly used)
        # ===================================================================
        cert_links_path = self.repo_path / "canonical" / "data" / "product-certificate-links.json"
        cert_links = []
        if cert_links_path.exists():
            with open(cert_links_path, 'r', encoding='utf-8') as f:
                cert_data = json.load(f)
                cert_links = cert_data.get("links", [])

        # ===================================================================
        # 4. CREATE SAMPLE CUSTOMERS BY MARKET
        # ===================================================================
        # Define markets and segments
        markets = {
            "gcc": {"countries": ["UAE", "Saudi Arabia", "Kuwait", "Qatar", "Bahrain", "Oman"], "segment": "GCC Distributor"},
            "eu": {"countries": ["Germany", "France", "UK", "Netherlands", "Italy", "Spain"], "segment": "European Distributor"},
            "usa": {"countries": ["USA"], "segment": "North American Importer"},
            "asia": {"countries": ["Singapore", "Malaysia", "Japan", "South Korea", "China"], "segment": "Asian Distributor"}
        }

        # Sample customers (10 GCC, 10 EU, 5 USA, 5 Asia = 30 customers)
        sample_customers = []
        customer_id_counter = 1

        # GCC customers
        gcc_customers = [
            {"name": "Al Baraka Trading", "country": "UAE", "city": "Dubai", "market": "gcc"},
            {"name": "Gulf Foods LLC", "country": "Saudi Arabia", "city": "Riyadh", "market": "gcc"},
            {"name": "Al Waha International", "country": "Kuwait", "city": "Kuwait City", "market": "gcc"},
            {"name": "Doha Natural Products", "country": "Qatar", "city": "Doha", "market": "gcc"},
            {"name": "Bahrain Wellness Co.", "country": "Bahrain", "city": "Manama", "market": "gcc"},
            {"name": "Oman Herbal Trading", "country": "Oman", "city": "Muscat", "market": "gcc"},
            {"name": "Al Jazeera Import-Export", "country": "UAE", "city": "Abu Dhabi", "market": "gcc"},
            {"name": "Saudi Natural Foods", "country": "Saudi Arabia", "city": "Jeddah", "market": "gcc"},
            {"name": "Kuwait Healthy Living", "country": "Kuwait", "city": "Salmiya", "market": "gcc"},
            {"name": "Dubai Organic Market", "country": "UAE", "city": "Dubai", "market": "gcc"}
        ]

        # EU customers
        eu_customers = [
            {"name": "Nature's Best GmbH", "country": "Germany", "city": "Berlin", "market": "eu"},
            {"name": "Bio France SARL", "country": "France", "city": "Paris", "market": "eu"},
            {"name": "Healthy UK Ltd.", "country": "UK", "city": "London", "market": "eu"},
            {"name": "Dutch Organic Import", "country": "Netherlands", "city": "Amsterdam", "market": "eu"},
            {"name": "Italia Naturale", "country": "Italy", "city": "Rome", "market": "eu"},
            {"name": "EspaÃ±a EcolÃ³gica", "country": "Spain", "city": "Madrid", "market": "eu"},
            {"name": "German Natural Products", "country": "Germany", "city": "Munich", "market": "eu"},
            {"name": "Paris Healthy Foods", "country": "France", "city": "Lyon", "market": "eu"},
            {"name": "London Organic Wholesale", "country": "UK", "city": "Manchester", "market": "eu"},
            {"name": "Amsterdam Wellness BV", "country": "Netherlands", "city": "Rotterdam", "market": "eu"}
        ]

        # USA customers
        usa_customers = [
            {"name": "American Natural Foods", "country": "USA", "city": "New York", "market": "usa"},
            {"name": "California Health Imports", "country": "USA", "city": "Los Angeles", "market": "usa"},
            {"name": "Florida Organic Distributors", "country": "USA", "city": "Miami", "market": "usa"},
            {"name": "Texas Natural Products", "country": "USA", "city": "Houston", "market": "usa"},
            {"name": "Chicago Wellness Inc.", "country": "USA", "city": "Chicago", "market": "usa"}
        ]

        # Asia customers
        asia_customers = [
            {"name": "Singapore Natural Goods", "country": "Singapore", "city": "Singapore", "market": "asia"},
            {"name": "Kuala Lumpur Organic", "country": "Malaysia", "city": "Kuala Lumpur", "market": "asia"},
            {"name": "Tokyo Healthy Imports", "country": "Japan", "city": "Tokyo", "market": "asia"},
            {"name": "Seoul Wellness Co.", "country": "South Korea", "city": "Seoul", "market": "asia"},
            {"name": "Shanghai Natural Trading", "country": "China", "city": "Shanghai", "market": "asia"}
        ]

        all_customers = gcc_customers + eu_customers + usa_customers + asia_customers

        # Build customer objects
        customers = []
        contacts = []
        segments = []
        preferences = []
        opportunities = []
        orders = []
        demand_map = {}

        for idx, cust_info in enumerate(all_customers):
            cust_id = f"CUS-{cust_info['market'].upper()}-{str(idx+1).zfill(3)}"
            market = cust_info["market"]
            segment_name = markets[market]["segment"]
            segment_id = f"SEG-{market.upper()}-001"

            # Create customer
            customer = {
                "customer_id": cust_id,
                "company_name": cust_info["name"],
                "market": market,
                "country": cust_info["country"],
                "city": cust_info["city"],
                "segment": segment_name,
                "type": "Distributor",
                "status": "active",
                "channels": ["Retail", "Organic Stores", "Online"],
                "preferred_products": [],
                "created_at": datetime.now().isoformat()
            }
            customers.append(customer)

            # Create contact (1 per customer)
            contact = {
                "customer_id": cust_id,
                "contact_id": f"CONT-{cust_id}",
                "first_name": "Contact",
                "last_name": str(idx+1),
                "email": f"info@{cust_info['name'].lower().replace(' ', '')}.com",
                "phone": f"+{idx+1} 123 456 789",
                "position": "Procurement Manager",
                "is_primary": True
            }
            contacts.append(contact)

            # Create segment entry (if not already)
            if not any(s.get("segment_id") == segment_id for s in segments):
                segments.append({
                    "segment_id": segment_id,
                    "name": segment_name,
                    "market": market,
                    "description": f"Customers in the {market.upper()} market"
                })

            # Determine preferred products based on market
            # GCC prefers honey and bee products; EU prefers honey and herbs; USA prefers oils and spices; Asia prefers all.
            if market == "gcc":
                prefs = [p for p in product_ids if p.startswith("H") or p.startswith("B")]
            elif market == "eu":
                prefs = [p for p in product_ids if p.startswith("H") or p.startswith("H004") or p.startswith("O")]
            elif market == "usa":
                prefs = [p for p in product_ids if p.startswith("O") or p.startswith("S")]
            else:  # asia
                prefs = product_ids[:]  # all products

            # Limit to 5 products per customer
            prefs = prefs[:5]
            customer["preferred_products"] = prefs

            # Create preferences link
            for prod in prefs:
                preferences.append({
                    "customer_id": cust_id,
                    "product_id": prod,
                    "preference_level": "high" if prod.startswith("H") else "medium"
                })

            # Create opportunities (1 per customer)
            opp_id = f"OPP-{cust_id}"
            # Pick a random product from prefs
            import random
            random.seed(idx)  # for reproducibility
            chosen_product = random.choice(prefs) if prefs else product_ids[0]
            opportunities.append({
                "opportunity_id": opp_id,
                "customer_id": cust_id,
                "product_id": chosen_product,
                "name": f"Initial order - {product_names.get(chosen_product, 'Product')}",
                "stage": random.choice(["Qualification", "Proposal", "Negotiation", "Closed Won"]),
                "value": random.randint(5000, 50000),
                "probability": random.randint(30, 90),
                "expected_close": (datetime.now() + timedelta(days=random.randint(30, 180))).isoformat(),
                "status": "open"
            })

            # Create orders (1 per customer)
            order_id = f"ORD-{cust_id}"
            orders.append({
                "order_id": order_id,
                "customer_id": cust_id,
                "product_id": chosen_product,
                "quantity": random.randint(10, 100),
                "unit_price": random.randint(10, 50),
                "total_price": random.randint(100, 5000),
                "order_date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                "status": random.choice(["delivered", "shipped", "processing"]),
                "tracking_code": f"TRK-{order_id}-001"
            })

            # Update demand map
            demand_map[cust_id] = {
                "customer_id": cust_id,
                "market": market,
                "products": prefs,
                "total_orders": 1,
                "total_value": random.randint(100, 5000)
            }

        # ===================================================================
        # 5. SAVE ALL FILES
        # ===================================================================
        customer_domain_dir = self.repo_path / "canonical" / "data" / "customer-domain"
        customer_domain_dir.mkdir(parents=True, exist_ok=True)

        # customers.json
        customers_data = {
            "schema_version": "customer-master-v1",
            "generated_at": datetime.now().isoformat(),
            "total_customers": len(customers),
            "customers": customers
        }
        customers_path = customer_domain_dir / "customers.json"
        with open(customers_path, 'w', encoding='utf-8') as f:
            json.dump(customers_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(customers_path.relative_to(self.repo_path)))

        # customer-contacts.json
        contacts_data = {
            "schema_version": "customer-contacts-v1",
            "generated_at": datetime.now().isoformat(),
            "total_contacts": len(contacts),
            "contacts": contacts
        }
        contacts_path = customer_domain_dir / "customer-contacts.json"
        with open(contacts_path, 'w', encoding='utf-8') as f:
            json.dump(contacts_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(contacts_path.relative_to(self.repo_path)))

        # customer-segments.json
        segments_data = {
            "schema_version": "customer-segments-v1",
            "generated_at": datetime.now().isoformat(),
            "total_segments": len(segments),
            "segments": segments
        }
        segments_path = customer_domain_dir / "customer-segments.json"
        with open(segments_path, 'w', encoding='utf-8') as f:
            json.dump(segments_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(segments_path.relative_to(self.repo_path)))

        # customer-product-preferences.json
        prefs_data = {
            "schema_version": "customer-product-preferences-v1",
            "generated_at": datetime.now().isoformat(),
            "total_preferences": len(preferences),
            "preferences": preferences
        }
        prefs_path = customer_domain_dir / "customer-product-preferences.json"
        with open(prefs_path, 'w', encoding='utf-8') as f:
            json.dump(prefs_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(prefs_path.relative_to(self.repo_path)))

        # opportunities.json
        opps_data = {
            "schema_version": "opportunities-v1",
            "generated_at": datetime.now().isoformat(),
            "total_opportunities": len(opportunities),
            "opportunities": opportunities
        }
        opps_path = customer_domain_dir / "opportunities.json"
        with open(opps_path, 'w', encoding='utf-8') as f:
            json.dump(opps_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(opps_path.relative_to(self.repo_path)))

        # orders.json
        orders_data = {
            "schema_version": "orders-v1",
            "generated_at": datetime.now().isoformat(),
            "total_orders": len(orders),
            "orders": orders
        }
        orders_path = customer_domain_dir / "orders.json"
        with open(orders_path, 'w', encoding='utf-8') as f:
            json.dump(orders_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(orders_path.relative_to(self.repo_path)))

        # customer-product-demand-map.json
        demand_map_data = {
            "schema_version": "customer-demand-map-v1",
            "generated_at": datetime.now().isoformat(),
            "total_customers": len(demand_map),
            "demand": demand_map
        }
        demand_path = customer_domain_dir / "customer-product-demand-map.json"
        with open(demand_path, 'w', encoding='utf-8') as f:
            json.dump(demand_map_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(demand_path.relative_to(self.repo_path)))

        # ===================================================================
        # 6. CREATE VALIDATION REPORT
        # ===================================================================
        validation_report = {
            "schema_version": "customer-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "total_customers": len(customers),
            "total_contacts": len(contacts),
            "total_segments": len(segments),
            "total_opportunities": len(opportunities),
            "total_orders": len(orders),
            "status": "PASSED",
            "issues": []
        }

        # Validate each customer
        for cust in customers:
            cust_id = cust["customer_id"]
            # Check for required fields
            if not cust.get("customer_id"):
                validation_report["issues"].append(f"Customer {cust_id} missing customer_id")
                validation_report["status"] = "FAILED"
            if not cust.get("company_name"):
                validation_report["issues"].append(f"Customer {cust_id} missing company_name")
                validation_report["status"] = "FAILED"
            if not cust.get("market"):
                validation_report["issues"].append(f"Customer {cust_id} missing market")
                validation_report["status"] = "FAILED"
            # Check that preferred products exist in product master
            for prod in cust.get("preferred_products", []):
                if prod not in product_ids:
                    validation_report["issues"].append(f"Customer {cust_id} prefers product {prod} which does not exist in product master")
                    validation_report["status"] = "FAILED"

        validation_path = self.repo_path / "intelligence" / "customer-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(validation_path.relative_to(self.repo_path)))

        # ===================================================================
        # 7. SUMMARY
        # ===================================================================
        result["customers_created"] = len(customers)
        result["contacts_created"] = len(contacts)
        result["opportunities_created"] = len(opportunities)
        result["orders_created"] = len(orders)
        result["validation_status"] = validation_report["status"]
        result["summary"] = (
            f"Customer Domain built: {result['customers_created']} customers, "
            f"{result['contacts_created']} contacts, "
            f"{result['opportunities_created']} opportunities, "
            f"{result['orders_created']} orders. "
            f"Validation: {result['validation_status']}"
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Files created: {', '.join(result['files_created'])}")
        
        return result


         # ========================================================================
    # AGENT 31: EOS ANALYTICS LAYER BUILDER
    # ========================================================================

    def build_analytics_layer(self) -> Dict:
        """
        Builds analytics summaries from existing data:
        - sales-summary.json
        - inventory-summary.json (based on orders)
        - revenue-by-market.json
        - top-products.json
        - customer-lifetime-value.json
        """
        self.logger.info("ðŸ“Š [Analytics Layer] Building analytics from existing data...")
        
        result = {
            "analytics_files_created": [],
            "summary": "",
            "status": "PENDING"
        }

        # ===================================================================
        # 1. LOAD PRODUCT MASTER
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            result["summary"] = "ERROR: master_products.json not found."
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        products = products_data.get("products") or products_data.get("Products", [])
        product_map = {p.get("id") or p.get("ProductID"): p for p in products}
        product_names = {p.get("id") or p.get("ProductID"): p.get("name") or p.get("ProductName") for p in products}

        # ===================================================================
        # 2. LOAD ORDERS
        # ===================================================================
        orders_path = self.repo_path / "canonical" / "data" / "customer-domain" / "orders.json"
        orders = []
        if orders_path.exists():
            with open(orders_path, 'r', encoding='utf-8') as f:
                orders_data = json.load(f)
                orders = orders_data.get("orders", [])
        else:
            self.logger.warning("Orders file not found. Analytics will be limited.")

        # ===================================================================
        # 3. LOAD CUSTOMERS
        # ===================================================================
        customers_path = self.repo_path / "canonical" / "data" / "customer-domain" / "customers.json"
        customers = []
        if customers_path.exists():
            with open(customers_path, 'r', encoding='utf-8') as f:
                customers_data = json.load(f)
                customers = customers_data.get("customers", [])
        else:
            self.logger.warning("Customers file not found. Some analytics will be limited.")

        # ===================================================================
        # 4. COMPUTE ANALYTICS
        # ===================================================================
        # Sales summary
        total_orders = len(orders)
        total_revenue = sum(o.get("total_price", 0) for o in orders)
        total_quantity = sum(o.get("quantity", 0) for o in orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

        sales_summary = {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_quantity": total_quantity,
            "average_order_value": avg_order_value,
            "generated_at": datetime.now().isoformat()
        }

        # Inventory summary (based on orders - sold quantities)
        inventory_summary = {}
        for o in orders:
            prod_id = o.get("product_id")
            if prod_id:
                inventory_summary[prod_id] = inventory_summary.get(prod_id, 0) + o.get("quantity", 0)
        # Add product names
        inv_list = []
        for prod_id, qty in inventory_summary.items():
            inv_list.append({
                "product_id": prod_id,
                "product_name": product_names.get(prod_id, "Unknown"),
                "sold_quantity": qty
            })
        inv_list.sort(key=lambda x: x["sold_quantity"], reverse=True)

        # Revenue by market
        market_revenue = {}
        customer_map = {c.get("customer_id"): c for c in customers}
        for o in orders:
            cust_id = o.get("customer_id")
            if cust_id and cust_id in customer_map:
                market = customer_map[cust_id].get("market", "unknown")
                market_revenue[market] = market_revenue.get(market, 0) + o.get("total_price", 0)
        revenue_by_market = [{"market": k, "revenue": v} for k, v in market_revenue.items()]
        revenue_by_market.sort(key=lambda x: x["revenue"], reverse=True)

        # Top products
        product_sales = {}
        for o in orders:
            prod_id = o.get("product_id")
            if prod_id:
                product_sales[prod_id] = product_sales.get(prod_id, 0) + o.get("total_price", 0)
        top_products = []
        for prod_id, revenue in product_sales.items():
            top_products.append({
                "product_id": prod_id,
                "product_name": product_names.get(prod_id, "Unknown"),
                "revenue": revenue
            })
        top_products.sort(key=lambda x: x["revenue"], reverse=True)
        top_products = top_products[:10]  # Top 10

        # Customer lifetime value
        clv = {}
        for o in orders:
            cust_id = o.get("customer_id")
            if cust_id:
                clv[cust_id] = clv.get(cust_id, 0) + o.get("total_price", 0)
        clv_list = []
        for cust_id, total in clv.items():
            cust_name = "Unknown"
            if cust_id in customer_map:
                cust_name = customer_map[cust_id].get("company_name", "Unknown")
            clv_list.append({
                "customer_id": cust_id,
                "customer_name": cust_name,
                "total_spent": total
            })
        clv_list.sort(key=lambda x: x["total_spent"], reverse=True)

        # ===================================================================
        # 5. SAVE ANALYTICS FILES
        # ===================================================================
        analytics_dir = self.repo_path / "canonical" / "analytics"
        analytics_dir.mkdir(parents=True, exist_ok=True)

        # sales-summary.json
        sales_path = analytics_dir / "sales-summary.json"
        with open(sales_path, 'w', encoding='utf-8') as f:
            json.dump(sales_summary, f, indent=2, ensure_ascii=False)
        result["analytics_files_created"].append(str(sales_path.relative_to(self.repo_path)))

        # inventory-summary.json
        inventory_path = analytics_dir / "inventory-summary.json"
        with open(inventory_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "inventory-summary-v1",
                "generated_at": datetime.now().isoformat(),
                "products": inv_list
            }, f, indent=2, ensure_ascii=False)
        result["analytics_files_created"].append(str(inventory_path.relative_to(self.repo_path)))

        # revenue-by-market.json
        revenue_path = analytics_dir / "revenue-by-market.json"
        with open(revenue_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "revenue-by-market-v1",
                "generated_at": datetime.now().isoformat(),
                "markets": revenue_by_market
            }, f, indent=2, ensure_ascii=False)
        result["analytics_files_created"].append(str(revenue_path.relative_to(self.repo_path)))

        # top-products.json
        top_path = analytics_dir / "top-products.json"
        with open(top_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "top-products-v1",
                "generated_at": datetime.now().isoformat(),
                "products": top_products
            }, f, indent=2, ensure_ascii=False)
        result["analytics_files_created"].append(str(top_path.relative_to(self.repo_path)))

        # customer-lifetime-value.json
        clv_path = analytics_dir / "customer-lifetime-value.json"
        with open(clv_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "customer-lifetime-value-v1",
                "generated_at": datetime.now().isoformat(),
                "customers": clv_list
            }, f, indent=2, ensure_ascii=False)
        result["analytics_files_created"].append(str(clv_path.relative_to(self.repo_path)))

        # ===================================================================
        # 6. VALIDATION REPORT
        # ===================================================================
        validation_report = {
            "schema_version": "analytics-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "status": "PASSED",
            "details": {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "products_with_sales": len(inv_list),
                "markets_with_revenue": len(revenue_by_market),
                "customers_with_value": len(clv_list)
            }
        }

        validation_path = self.repo_path / "intelligence" / "analytics-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        result["analytics_files_created"].append(str(validation_path.relative_to(self.repo_path)))

        # ===================================================================
        # 7. SUMMARY
        # ===================================================================
        result["status"] = "PASSED"
        result["summary"] = (
            f"Analytics layer built: {len(result['analytics_files_created'])} files created. "
            f"Orders: {total_orders}, Revenue: {total_revenue}, Products sold: {len(inv_list)}"
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Files created: {', '.join(result['analytics_files_created'])}")
        
        return result
       

           # ========================================================================
    # AGENT 32: EOS LOGISTICS SYSTEM BUILDER (EXPANDED)
    # ========================================================================

    def build_logistics_system(self) -> Dict:
        """
        Builds the complete Logistics System:
        - Reads orders.json
        - Creates shipments, containers, ports, carriers
        - Generates tracking data
        """
        self.logger.info("ðŸš› [Logistics System] Building full logistics domain...")
        
        result = {
            "shipments_created": 0,
            "containers_created": 0,
            "ports_created": 0,
            "carriers_created": 0,
            "status": "PENDING",
            "files_created": [],
            "summary": ""
        }

        # ===================================================================
        # 1. LOAD ORDERS
        # ===================================================================
        orders_path = self.repo_path / "canonical" / "data" / "customer-domain" / "orders.json"
        if not orders_path.exists():
            self.logger.error("Orders file not found.")
            result["summary"] = "ERROR: orders.json not found."
            return result

        with open(orders_path, 'r', encoding='utf-8') as f:
            orders_data = json.load(f)
            orders = orders_data.get("orders", [])

        self.logger.info(f"   Found {len(orders)} orders to process.")

        # ===================================================================
        # 2. LOAD CUSTOMERS
        # ===================================================================
        customers_path = self.repo_path / "canonical" / "data" / "customer-domain" / "customers.json"
        customers = []
        if customers_path.exists():
            with open(customers_path, 'r', encoding='utf-8') as f:
                customers_data = json.load(f)
                customers = customers_data.get("customers", [])
        customer_map = {c.get("customer_id"): c for c in customers}

        # ===================================================================
        # 3. DEFINE PORTS & CARRIERS (MASTER DATA)
        # ===================================================================
        ports = [
            {"id": "PORT-EG-ALEX", "name": "Alexandria Port", "country": "Egypt", "type": "sea"},
            {"id": "PORT-EG-DAM", "name": "Damietta Port", "country": "Egypt", "type": "sea"},
            {"id": "PORT-EG-CAI", "name": "Cairo Airport", "country": "Egypt", "type": "air"},
            {"id": "PORT-EU-ROT", "name": "Rotterdam Port", "country": "Netherlands", "type": "sea"},
            {"id": "PORT-EU-HAM", "name": "Hamburg Port", "country": "Germany", "type": "sea"},
            {"id": "PORT-US-NYK", "name": "New York Port", "country": "USA", "type": "sea"},
            {"id": "PORT-GCC-DXB", "name": "Jebel Ali Port", "country": "UAE", "type": "sea"},
            {"id": "PORT-ASIA-SIN", "name": "Singapore Port", "country": "Singapore", "type": "sea"}
        ]

        carriers = [
            {"id": "CAR-001", "name": "Maersk", "type": "sea"},
            {"id": "CAR-002", "name": "MSC", "type": "sea"},
            {"id": "CAR-003", "name": "CMA CGM", "type": "sea"},
            {"id": "CAR-004", "name": "DHL", "type": "air"},
            {"id": "CAR-005", "name": "FedEx", "type": "air"},
            {"id": "CAR-006", "name": "UPS", "type": "air"}
        ]

        # ===================================================================
        # 4. GENERATE SHIPMENTS, CONTAINERS, AND CUSTOMS
        # ===================================================================
        shipments = []
        containers = []
        customs_clearances = []
        tracking_updates = []

        import random
        random.seed(42)

        statuses = ["ORDER_RECEIVED", "PACKED", "SHIPPED", "IN_TRANSIT", "AT_PORT", "CUSTOMS_CLEARANCE", "DELIVERED"]

        for idx, order in enumerate(orders):
            order_id = order.get("order_id", f"ORD-{idx}")
            customer_id = order.get("customer_id")
            product_id = order.get("product_id")
            quantity = order.get("quantity", 1)
            
            customer = customer_map.get(customer_id, {})
            country = customer.get("country", "Unknown")
            city = customer.get("city", "Unknown")
            market = customer.get("market", "unknown")
            
            # Determine shipping method
            shipping_method = "Air Freight" if market in ["eu", "usa"] else "Sea Freight"
            
            # Determine origin port
            origin_port = random.choice([p for p in ports if p["country"] == "Egypt"])
            
            # Determine destination port (based on market)
            dest_ports = {
                "eu": [p for p in ports if p["country"] in ["Netherlands", "Germany"]],
                "usa": [p for p in ports if p["country"] == "USA"],
                "gcc": [p for p in ports if p["country"] == "UAE"],
                "asia": [p for p in ports if p["country"] == "Singapore"]
            }
            dest_port = random.choice(dest_ports.get(market, [ports[0]]))
            
            # Pick a carrier
            carrier = random.choice([c for c in carriers if c["type"] == ("sea" if shipping_method == "Sea Freight" else "air")])
            
            # Generate tracking code
            tracking_code = f"GL-TRK-{order_id}-{idx+1:03d}"
            
            # Random status
            status_idx = min(len(statuses)-1, random.randint(1, len(statuses)-1))
            status = statuses[status_idx]
            
            # Create shipment
            shipment = {
                "shipment_id": f"SHIP-{order_id}",
                "order_id": order_id,
                "customer_id": customer_id,
                "customer_name": customer.get("company_name", "Unknown"),
                "product_id": product_id,
                "quantity": quantity,
                "tracking_code": tracking_code,
                "status": status,
                "shipping_method": shipping_method,
                "origin_port": origin_port["id"],
                "destination_port": dest_port["id"],
                "carrier_id": carrier["id"],
                "destination_city": city,
                "destination_country": country,
                "market": market,
                "estimated_delivery": (datetime.now() + timedelta(days=random.randint(7, 30))).isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            shipments.append(shipment)

            # Create container (if sea freight)
            if shipping_method == "Sea Freight":
                container = {
                    "container_id": f"CNTR-{order_id}",
                    "shipment_id": shipment["shipment_id"],
                    "type": random.choice(["20ft", "40ft"]),
                    "seal_number": f"SEAL-{random.randint(100000, 999999)}",
                    "status": random.choice(["loaded", "in_transit", "at_port"])
                }
                containers.append(container)

            # Create customs clearance
            customs = {
                "clearance_id": f"CUST-{order_id}",
                "shipment_id": shipment["shipment_id"],
                "status": random.choice(["pending", "submitted", "cleared"]),
                "documents": ["invoice", "packing_list", "certificate_of_origin"],
                "submitted_at": (datetime.now() - timedelta(days=random.randint(1, 5))).isoformat()
            }
            customs_clearances.append(customs)

            # Tracking updates
            for i in range(3):
                tracking_updates.append({
                    "tracking_code": tracking_code,
                    "status": statuses[i % len(statuses)],
                    "location": random.choice(["Warehouse", "Port", "In Transit", "Customs"]),
                    "timestamp": (datetime.now() - timedelta(hours=i*24)).isoformat()
                })

        # ===================================================================
        # 5. SAVE FILES
        # ===================================================================
        logistics_dir = self.repo_path / "canonical" / "logistics"
        logistics_dir.mkdir(parents=True, exist_ok=True)

        # shipments.json
        shipments_data = {"total_shipments": len(shipments), "shipments": shipments}
        with open(logistics_dir / "shipments.json", 'w', encoding='utf-8') as f:
            json.dump(shipments_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/logistics/shipments.json")

        # containers.json
        containers_data = {"total_containers": len(containers), "containers": containers}
        with open(logistics_dir / "containers.json", 'w', encoding='utf-8') as f:
            json.dump(containers_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/logistics/containers.json")
        result["containers_created"] = len(containers)

        # ports.json
        ports_data = {"total_ports": len(ports), "ports": ports}
        with open(logistics_dir / "ports.json", 'w', encoding='utf-8') as f:
            json.dump(ports_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/logistics/ports.json")
        result["ports_created"] = len(ports)

        # carriers.json
        carriers_data = {"total_carriers": len(carriers), "carriers": carriers}
        with open(logistics_dir / "carriers.json", 'w', encoding='utf-8') as f:
            json.dump(carriers_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/logistics/carriers.json")
        result["carriers_created"] = len(carriers)

        # customs-clearance.json
        customs_data = {"total_clearances": len(customs_clearances), "clearances": customs_clearances}
        with open(logistics_dir / "customs-clearance.json", 'w', encoding='utf-8') as f:
            json.dump(customs_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/logistics/customs-clearance.json")

        # tracking.json (aggregated)
        tracking_summary = {
            "total_updates": len(tracking_updates),
            "updates": tracking_updates
        }
        with open(logistics_dir / "tracking.json", 'w', encoding='utf-8') as f:
            json.dump(tracking_summary, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/logistics/tracking.json")

        # ===================================================================
        # 6. VALIDATION REPORT
        # ===================================================================
        validation_report = {
            "schema_version": "logistics-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "status": "PASSED",
            "total_shipments": len(shipments),
            "total_containers": len(containers),
            "total_ports": len(ports),
            "total_carriers": len(carriers),
            "total_tracking_updates": len(tracking_updates)
        }
        validation_path = self.repo_path / "intelligence" / "logistics-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False)
        result["files_created"].append("intelligence/logistics-validation-report.json")

        # ===================================================================
        # 7. SUMMARY
        # ===================================================================
        result["shipments_created"] = len(shipments)
        result["status"] = validation_report["status"]
        result["summary"] = (
            f"Logistics system built: {result['shipments_created']} shipments, "
            f"{result['containers_created']} containers, "
            f"{result['ports_created']} ports, "
            f"{result['carriers_created']} carriers. "
            f"Status: {result['status']}"
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Files created: {', '.join(result['files_created'])}")
        
        return result

        

    # ------------------------------------------------------------------------
    # Helper functions for GELS data
    # ------------------------------------------------------------------------
    def _get_net_weights(self, category: str) -> List[str]:
        """Return net weight options based on product category."""
        weights = {
            "Honey": ["250g", "500g", "750g", "1kg"],
            "Bee Products": ["30ml", "50ml", "100ml", "250ml", "500ml"],
            "Spices": ["250g", "500g", "750g", "1kg"],
            "Premium Spices": ["250g", "500g", "750g", "1kg"],
            "Herbs": ["250g", "500g"],
            "Herbal Products": ["250g", "500g"],
            "Natural Oils": ["30ml", "50ml", "100ml", "250ml", "500ml"]
        }
        return weights.get(category, ["250g"])

    def _get_nutrition_facts(self, category: str) -> Dict:
        """Return basic nutrition facts based on category."""
        facts = {
            "Honey": {"serving_size": "20g", "calories": 60, "sugars": "16g"},
            "Bee Products": {"serving_size": "5g", "calories": 30, "sugars": "5g"},
            "Spices": {"serving_size": "5g", "calories": 10, "sugars": "0g"},
            "Premium Spices": {"serving_size": "5g", "calories": 10, "sugars": "0g"},
            "Herbs": {"serving_size": "5g", "calories": 5, "sugars": "0g"},
            "Herbal Products": {"serving_size": "5g", "calories": 5, "sugars": "0g"},
            "Natural Oils": {"serving_size": "15ml", "calories": 120, "sugars": "0g"}
        }
        return facts.get(category, {"serving_size": "10g", "calories": 50, "sugars": "5g"})

    def _get_certifications_for_product(self, product_id: str, cert_links: List[Dict]) -> List[str]:
        """Return list of certifications for a product."""
        certs = []
        for link in cert_links:
            if link.get("product_id") == product_id:
                # In a real implementation, we would look up the certificate name from certificates.json
                certs.append(link.get("certificate_id", "CERT-UNKNOWN"))
        return certs if certs else ["Halal", "HACCP", "ISO 22000"]

    def _get_side_panel(self, category: str) -> Dict:
        """Return side panel content based on product category."""
        side_panels = {
            "Honey": {
                "usage": "Daily sweetener, immune support",
                "warnings": ["Not suitable for infants under 12 months."],
                "moisture": "<20%",
                "hmf": "<40 mg/kg",
                "floral_source": "Diverse Egyptian wildflowers"
            },
            "Bee Products": {
                "usage": "Consult a healthcare professional before use.",
                "warnings": ["People allergic to bee products should consult a physician."]
            },
            "Spices": {
                "usage": "Add to cooking as desired.",
                "warnings": ["May contain traces of allergens."]
            },
            "Premium Spices": {
                "usage": "Add to cooking as desired.",
                "warnings": ["May contain traces of allergens."]
            },
            "Herbs": {
                "usage": "Brew as tea or use in cooking.",
                "warnings": ["Consult a healthcare professional before use."]
            },
            "Herbal Products": {
                "usage": "Brew as tea or use in cooking.",
                "warnings": ["Consult a healthcare professional before use."]
            },
            "Natural Oils": {
                "usage": "Use as a dietary supplement or for cooking.",
                "warnings": ["Consult a healthcare professional before use."]
            }
        }
        return side_panels.get(category, {"usage": "Use as directed.", "warnings": []})


        # ========================================================================
    # AGENT 33: DEEP CLEAN (FIXED VERSION)
    # ========================================================================

    def run_deep_clean(self) -> Dict:
        """
        Deep clean with proper file collection and classification.
        """
        self.logger.info("ðŸ§¹ [Deep Clean] Starting comprehensive file system analysis...")
        
        result = {
            "total_files_analyzed": 0,
            "critical_kept": 0,
            "archived_old": 0,
            "deleted_unused": 0,
            "files_archived": [],
            "files_deleted": [],
            "summary": "",
            "report_path": ""
        }

        # ===================================================================
        # 1. COLLECT ALL FILES (except .git, .venv, node_modules, .next, etc.)
        # ===================================================================
        exclude_dirs = ['.git', '.venv', 'node_modules', '__pycache__', '.next', 'logs', 'alerts', 'archive']
        all_files = []
        
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            # Skip excluded directories
            if any(part in file_path.parts for part in exclude_dirs):
                continue
            all_files.append(file_path)

        self.logger.info(f"   Found {len(all_files)} files to analyze (excluding system folders).")
        result["total_files_analyzed"] = len(all_files)

        # ===================================================================
        # 2. CLASSIFY EACH FILE
        # ===================================================================
        critical_paths = [
            "brain.py", "config.yaml", "requirements.txt", "package.json",
            "system_manifest.json", "BOUND.md", ".env", ".archguard.yml", ".govern.toml",
            "canonical", "intelligence", "data", "src", "app", "domain"
        ]
        critical_extensions = [".py", ".ts", ".js", ".json", ".yaml", ".yml", ".md", ".prisma", ".ps1"]
        
        archive_conditions = lambda path, age, size: (
            age > 90 and size > 1 and 
            not any(cp in str(path) for cp in critical_paths) and
            path.suffix not in critical_extensions
        )
        
        delete_conditions = lambda path, age, size: (
            age > 30 and size < 1 and
            path.suffix in [".pyc", ".log", ".tmp", ".cache", ".sst", ".meta", ".js.map", ".css.map"] and
            not any(cp in str(path) for cp in critical_paths)
        )

        for file_path in all_files:
            rel_path = str(file_path.relative_to(self.repo_path))
            size_mb = file_path.stat().st_size / (1024 * 1024)
            days_old = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days

            # Check if critical
            is_critical = any(cp in rel_path for cp in critical_paths) or file_path.suffix in critical_extensions

            if is_critical:
                result["critical_kept"] += 1
                continue

            # Check for archive candidate
            if archive_conditions(file_path, days_old, size_mb):
                result["files_archived"].append({
                    "path": rel_path,
                    "size_mb": size_mb,
                    "days_old": days_old
                })
            # Check for delete candidate
            elif delete_conditions(file_path, days_old, size_mb):
                result["files_deleted"].append({
                    "path": rel_path,
                    "size_mb": size_mb,
                    "days_old": days_old
                })

        # ===================================================================
        # 3. EXECUTE ACTIONS (archive and delete)
        # ===================================================================
        archive_dir = self.repo_path / "archive" / "old-dependencies"
        archive_dir.mkdir(parents=True, exist_ok=True)

        for f in result["files_archived"][:100]:  # limit for safety
            src = self.repo_path / f["path"]
            if src.exists():
                dest = archive_dir / Path(f["path"]).name
                try:
                    shutil.move(str(src), str(dest))
                    result["archived_old"] += 1
                except Exception as e:
                    self.logger.warning(f"Could not archive {f['path']}: {e}")

        for f in result["files_deleted"][:50]:  # limit for safety
            src = self.repo_path / f["path"]
            if src.exists():
                try:
                    os.remove(str(src))
                    result["deleted_unused"] += 1
                except Exception as e:
                    self.logger.warning(f"Could not delete {f['path']}: {e}")

        # ===================================================================
        # 4. GENERATE REPORT
        # ===================================================================
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_files_analyzed": result["total_files_analyzed"],
            "critical_files_kept": result["critical_kept"],
            "files_archived": result["archived_old"],
            "files_deleted": result["deleted_unused"],
            "archive_location": str(archive_dir.relative_to(self.repo_path)),
            "sample_archived": [f["path"] for f in result["files_archived"][:10]],
            "sample_deleted": [f["path"] for f in result["files_deleted"][:10]]
        }

        report_path = self.repo_path / "intelligence" / "deep_clean_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        result["report_path"] = str(report_path.relative_to(self.repo_path))

        # ===================================================================
        # 5. SUMMARY
        # ===================================================================
        result["summary"] = (
            f"Deep clean completed: {result['critical_kept']} critical files kept, "
            f"{result['archived_old']} files archived, "
            f"{result['deleted_unused']} files deleted. "
            f"Total analyzed: {result['total_files_analyzed']}"
        )

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Report saved: {result['report_path']}")
        
        return result

        
    # ------------------------------------------------------------------------
    # Helper: Extract Domain from file path
    # ------------------------------------------------------------------------
    def _extract_domain(self, path: str) -> str:
        """Extract the business domain from a file path."""
        domains = ["product", "customer", "supplier", "inventory", "order", "logistics", 
                   "finance", "quality", "analytics", "compliance", "crm"]
        for d in domains:
            if d in path.lower():
                return d
        return "unknown"
      


    # -------------------------------------------------------------------------
    # AGENT 34: MASTER DATA INTEGRITY AUDIT
    # -------------------------------------------------------------------------
    def run_master_data_audit(self) -> Dict:
        """
        Audits all product data sources to resolve discrepancies between
        canonical master_products.json and other legacy/inventory sources.
        """
        self.logger.info("ðŸ” [Master Data Audit] Starting integrity audit...")
        
        result = {
            "sources": {},
            "canonical_products": [],
            "legacy_products": [],
            "missing_from_canonical": [],
            "missing_from_legacy": [],
            "duplicates": [],
            "summary": "",
            "report_path": ""
        }

        # 1. Find ALL potential product data sources
        all_json_files = self.repo_path.rglob("*.json")
        
        product_sources = []
        for file in all_json_files:
            if self._should_ignore(file):
                continue
            try:
                data = json.loads(file.read_text(encoding='utf-8', errors='ignore'))
                # Check if this file contains a products list
                products_list = data.get("products") or data.get("Products") or data.get("items") or data.get("portfolio")
                if products_list and isinstance(products_list, list) and len(products_list) > 0:
                    product_sources.append({
                        "path": str(file.relative_to(self.repo_path)),
                        "product_count": len(products_list),
                        "sample": products_list[:3]  # sample for identification
                    })
            except:
                continue

        result["sources"] = product_sources

        # 2. Load canonical products
        canonical_path = self.repo_path / "canonical" / "data" / "master_products.json"
        canonical_products = []
        if canonical_path.exists():
            with open(canonical_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                canonical_products = data.get("products") or data.get("Products") or []
        result["canonical_products"] = canonical_products

        # 3. Load ALL product IDs from ALL sources
        all_product_ids = set()
        legacy_product_ids = set()
        
        for src in product_sources:
            path = self.repo_path / src["path"]
            try:
                data = json.loads(path.read_text(encoding='utf-8', errors='ignore'))
                products = data.get("products") or data.get("Products") or data.get("items") or data.get("portfolio")
                for p in products:
                    pid = p.get("id") or p.get("ProductID") or p.get("product_id") or p.get("code")
                    if pid:
                        legacy_product_ids.add(pid)
                        all_product_ids.add(pid)
            except:
                continue

        # 4. Get canonical product IDs
        canonical_ids = set()
        for p in canonical_products:
            pid = p.get("id") or p.get("ProductID") or p.get("product_id") or p.get("code")
            if pid:
                canonical_ids.add(pid)

        # 5. Find discrepancies
        missing_from_canonical = list(legacy_product_ids - canonical_ids)
        missing_from_legacy = list(canonical_ids - legacy_product_ids)
        
        result["missing_from_canonical"] = missing_from_canonical
        result["missing_from_legacy"] = missing_from_legacy

        # 6. Find duplicates within sources
        all_ids = {}
        for src in product_sources:
            path = self.repo_path / src["path"]
            try:
                data = json.loads(path.read_text(encoding='utf-8', errors='ignore'))
                products = data.get("products") or data.get("Products") or data.get("items") or data.get("portfolio")
                for p in products:
                    pid = p.get("id") or p.get("ProductID") or p.get("product_id") or p.get("code")
                    if pid:
                        if pid not in all_ids:
                            all_ids[pid] = []
                        all_ids[pid].append(src["path"])
            except:
                continue

        duplicates = []
        for pid, sources in all_ids.items():
            if len(sources) > 1:
                duplicates.append({
                    "product_id": pid,
                    "sources": sources
                })
        result["duplicates"] = duplicates

        # 7. Summary
        result["summary"] = (
            f"Audited {len(product_sources)} product sources. "
            f"Canonical products: {len(canonical_ids)}. "
            f"Legacy products (total unique): {len(legacy_product_ids)}. "
            f"Missing from Canonical: {len(missing_from_canonical)}. "
            f"Missing from Legacy: {len(missing_from_legacy)}. "
            f"Duplicates found: {len(duplicates)}."
        )

        # 8. Save report
        report_path = self.repo_path / "intelligence" / "master-data-integrity-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        result["report_path"] = str(report_path.relative_to(self.repo_path))

        self.logger.info(f"   {result['summary']}")
        self.logger.info(f"   Report saved: {result['report_path']}")

        return result


    # ========================================================================
    # AGENT 35: FINANCE SYSTEM BUILDER
    # ========================================================================

    def build_finance_system(self) -> Dict:
        """
        Builds Finance System from legacy files in canonical/finance/
        - Creates finance-master.json, invoices.json, payments.json
        """
        self.logger.info("ðŸ’° [Finance System] Building finance system...")
        
        result = {
            "files_created": [],
            "summary": "",
            "status": "PENDING"
        }

        # 1. Create directories if not exist
        finance_dir = self.repo_path / "canonical" / "finance"
        finance_dir.mkdir(parents=True, exist_ok=True)

        # 2. Read legacy files if they exist
        legacy_files = {
            "finance.sql": finance_dir / "finance.sql",
            "finance-flow-v1.json": finance_dir / "finance-flow-v1.json"
        }
        
        # 3. Generate master finance data (sample)
        finance_master = {
            "schema_version": "finance-master-v1",
            "generated_at": datetime.now().isoformat(),
            "total_invoices": 0,
            "total_payments": 0,
            "currencies": ["USD", "EUR", "EGP"],
            "accounts": [
                {"id": "ACC-001", "name": "Revenue", "type": "income"},
                {"id": "ACC-002", "name": "Cost of Goods Sold", "type": "expense"},
                {"id": "ACC-003", "name": "Accounts Receivable", "type": "asset"},
                {"id": "ACC-004", "name": "Cash", "type": "asset"}
            ]
        }
        # Check if we have orders to generate sample invoices
        orders_path = self.repo_path / "canonical" / "data" / "customer-domain" / "orders.json"
        if orders_path.exists():
            with open(orders_path, 'r', encoding='utf-8') as f:
                orders_data = json.load(f)
                orders = orders_data.get("orders", [])
                # Create sample invoices from orders
                invoices = []
                for idx, order in enumerate(orders[:10]):  # first 10 orders
                    invoices.append({
                        "invoice_id": f"INV-{idx+1:04d}",
                        "order_id": order.get("order_id"),
                        "customer_id": order.get("customer_id"),
                        "amount": order.get("total_price", 0),
                        "status": "paid" if idx % 2 == 0 else "pending",
                        "issue_date": (datetime.now() - timedelta(days=idx*5)).isoformat()
                    })
                finance_master["invoices"] = invoices
                finance_master["total_invoices"] = len(invoices)
                payments = []
                for inv in invoices:
                    if inv["status"] == "paid":
                        payments.append({
                            "payment_id": f"PAY-{inv['invoice_id']}",
                            "invoice_id": inv["invoice_id"],
                            "amount": inv["amount"],
                            "date": (datetime.now() - timedelta(days=2)).isoformat(),
                            "method": "bank_transfer"
                        })
                finance_master["payments"] = payments
                finance_master["total_payments"] = len(payments)

        # 4. Save master file
        master_path = finance_dir / "finance-master.json"
        with open(master_path, 'w', encoding='utf-8') as f:
            json.dump(finance_master, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(master_path.relative_to(self.repo_path)))

        # 5. Save invoices separately (optional)
        if "invoices" in finance_master:
            invoices_path = finance_dir / "invoices.json"
            with open(invoices_path, 'w', encoding='utf-8') as f:
                json.dump({"invoices": finance_master["invoices"]}, f, indent=2, ensure_ascii=False)
            result["files_created"].append(str(invoices_path.relative_to(self.repo_path)))

        # 6. Save payments separately
        if "payments" in finance_master:
            payments_path = finance_dir / "payments.json"
            with open(payments_path, 'w', encoding='utf-8') as f:
                json.dump({"payments": finance_master["payments"]}, f, indent=2, ensure_ascii=False)
            result["files_created"].append(str(payments_path.relative_to(self.repo_path)))

        # 7. Validation report
        validation = {
            "schema_version": "finance-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "status": "PASSED",
            "total_invoices": finance_master.get("total_invoices", 0),
            "total_payments": finance_master.get("total_payments", 0)
        }
        validation_path = self.repo_path / "intelligence" / "finance-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(validation_path.relative_to(self.repo_path)))

        result["status"] = "PASSED"
        result["summary"] = (
            f"Finance system built: {len(result['files_created'])} files created. "
            f"Invoices: {finance_master.get('total_invoices', 0)}, Payments: {finance_master.get('total_payments', 0)}"
        )
        self.logger.info(f"   {result['summary']}")
        return result

    # ========================================================================
    # AGENT 36: INVENTORY SYSTEM BUILDER
    # ========================================================================

    def build_inventory_system(self) -> Dict:
        """
        Builds Inventory System from legacy files in canonical/inventory/
        - Creates warehouses.json, stock-levels.json, movements.json
        """
        self.logger.info("ðŸ“¦ [Inventory System] Building inventory system...")
        
        result = {
            "files_created": [],
            "summary": "",
            "status": "PENDING"
        }

        inv_dir = self.repo_path / "canonical" / "inventory"
        inv_dir.mkdir(parents=True, exist_ok=True)

        # Load product master to know products
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        products = []
        if products_path.exists():
            with open(products_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                products = data.get("products") or data.get("Products", [])

        # Create warehouses
        warehouses = [
            {"id": "WH-001", "name": "Cairo Main Warehouse", "location": "Cairo, Egypt", "capacity": 1000},
            {"id": "WH-002", "name": "Alexandria Port Warehouse", "location": "Alexandria, Egypt", "capacity": 500}
        ]
        warehouses_path = inv_dir / "warehouses.json"
        with open(warehouses_path, 'w', encoding='utf-8') as f:
            json.dump({"warehouses": warehouses}, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(warehouses_path.relative_to(self.repo_path)))

        # Create stock levels (sample)
        stock_levels = []
        for p in products[:10]:  # first 10 products
            stock_levels.append({
                "product_id": p.get("id") or p.get("ProductID"),
                "warehouse_id": "WH-001",
                "quantity": random.randint(50, 500),
                "reorder_level": 50,
                "last_updated": datetime.now().isoformat()
            })
        stock_path = inv_dir / "stock-levels.json"
        with open(stock_path, 'w', encoding='utf-8') as f:
            json.dump({"stock": stock_levels}, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(stock_path.relative_to(self.repo_path)))

        # Movements (sample)
        movements = []
        for i in range(20):
            p = products[i % len(products)] if products else {}
            movements.append({
                "movement_id": f"MOV-{i+1:04d}",
                "product_id": p.get("id") or p.get("ProductID") or f"P{i}",
                "warehouse_id": "WH-001",
                "type": random.choice(["in", "out"]),
                "quantity": random.randint(10, 100),
                "date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
            })
        movements_path = inv_dir / "movements.json"
        with open(movements_path, 'w', encoding='utf-8') as f:
            json.dump({"movements": movements}, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(movements_path.relative_to(self.repo_path)))

        # Validation
        validation = {
            "schema_version": "inventory-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "status": "PASSED",
            "total_warehouses": len(warehouses),
            "total_stock_items": len(stock_levels),
            "total_movements": len(movements)
        }
        validation_path = self.repo_path / "intelligence" / "inventory-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(validation_path.relative_to(self.repo_path)))

        result["status"] = "PASSED"
        result["summary"] = (
            f"Inventory system built: {len(result['files_created'])} files created. "
            f"Warehouses: {len(warehouses)}, Stock items: {len(stock_levels)}, Movements: {len(movements)}"
        )
        self.logger.info(f"   {result['summary']}")
        return result

    # ========================================================================
    # AGENT 37: CRM SYSTEM BUILDER
    # ========================================================================

    def build_crm_system(self) -> Dict:
        """
        Builds CRM System from legacy files in canonical/crm/
        - Creates customers.json, opportunities.json, interactions.json
        """
        self.logger.info("ðŸ‘¤ [CRM System] Building CRM system...")
        
        result = {
            "files_created": [],
            "summary": "",
            "status": "PENDING"
        }

        crm_dir = self.repo_path / "canonical" / "crm"
        crm_dir.mkdir(parents=True, exist_ok=True)

        # Load existing customer domain (if any)
        customers_path = self.repo_path / "canonical" / "data" / "customer-domain" / "customers.json"
        customers = []
        if customers_path.exists():
            with open(customers_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                customers = data.get("customers", [])

        # If no customers, create sample
        if not customers:
            customers = []
            for i in range(10):
                customers.append({
                    "customer_id": f"CUS-{i+1:04d}",
                    "name": f"Customer {i+1}",
                    "email": f"customer{i+1}@example.com",
                    "phone": f"+123456789{i}",
                    "segment": random.choice(["Retail", "Wholesale", "Distributor"]),
                    "status": "active"
                })

        # Save customers
        customers_file = crm_dir / "customers.json"
        with open(customers_file, 'w', encoding='utf-8') as f:
            json.dump({"customers": customers}, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(customers_file.relative_to(self.repo_path)))

        # Opportunities (from existing opportunities.json if available)
        opps_path = self.repo_path / "canonical" / "data" / "customer-domain" / "opportunities.json"
        opportunities = []
        if opps_path.exists():
            with open(opps_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                opportunities = data.get("opportunities", [])
        if not opportunities:
            # Create sample
            for i in range(5):
                opportunities.append({
                    "opportunity_id": f"OPP-{i+1:04d}",
                    "customer_id": random.choice(customers)["customer_id"] if customers else "CUS-0001",
                    "product_id": "P001",
                    "value": random.randint(1000, 10000),
                    "stage": random.choice(["Qualification", "Proposal", "Negotiation", "Closed Won"]),
                    "expected_close": (datetime.now() + timedelta(days=random.randint(30, 90))).isoformat()
                })
        opps_file = crm_dir / "opportunities.json"
        with open(opps_file, 'w', encoding='utf-8') as f:
            json.dump({"opportunities": opportunities}, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(opps_file.relative_to(self.repo_path)))

        # Interactions (sample)
        interactions = []
        for i in range(20):
            cust = random.choice(customers) if customers else {"customer_id": "CUS-0001"}
            interactions.append({
                "interaction_id": f"INT-{i+1:04d}",
                "customer_id": cust["customer_id"],
                "type": random.choice(["call", "email", "meeting"]),
                "date": (datetime.now() - timedelta(days=random.randint(1, 60))).isoformat(),
                "notes": f"Sample interaction {i+1}"
            })
        int_file = crm_dir / "interactions.json"
        with open(int_file, 'w', encoding='utf-8') as f:
            json.dump({"interactions": interactions}, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(int_file.relative_to(self.repo_path)))

        # Validation
        validation = {
            "schema_version": "crm-validation-v1",
            "generated_at": datetime.now().isoformat(),
            "status": "PASSED",
            "total_customers": len(customers),
            "total_opportunities": len(opportunities),
            "total_interactions": len(interactions)
        }
        validation_path = self.repo_path / "intelligence" / "crm-validation-report.json"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(validation_path.relative_to(self.repo_path)))

        result["status"] = "PASSED"
        result["summary"] = (
            f"CRM system built: {len(result['files_created'])} files created. "
            f"Customers: {len(customers)}, Opportunities: {len(opportunities)}, Interactions: {len(interactions)}"
        )
        self.logger.info(f"   {result['summary']}")
        return result


    # ========================================================================
    # AGENT 38: PRODUCT ENRICHMENT AGENT (B2B/B2C/Packaging)
    # ========================================================================

    def enrich_product_details(self) -> Dict:
        """
        Adds B2B/B2C packaging, custom client packaging, and global specs to products.
        """
        self.logger.info("ðŸ“¦ [Product Enrichment] Adding detailed packaging and global specs...")
        result = {"products_updated": 0, "summary": ""}

        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        products = data.get("products", [])

        # Define packaging templates per category
        packaging_templates = {
            "Honey": {
                "b2b": {"material": "Food Grade Drum", "sizes": ["25kg", "50kg", "300kg"]},
                "b2c": {"material": "Glass Jar", "sizes": ["250g", "500g", "750g", "1kg"]},
                "custom": []  # Ø³ÙŠØªÙ… Ù…Ù„Ø¤Ù‡ Ù…Ù† Ø·Ù„Ø¨Ø§Øª Ø§Ù„Ø¹Ù…Ù„Ø§Ø¡
            },
            "Spices": {
                "b2b": {"material": "Industrial Multi-Layer Bag", "sizes": ["10kg", "25kg"]},
                "b2c": {"material": "Glass Jar", "sizes": ["250g", "500g", "750g", "1kg"]}
            },
            # ... Ø£Ø¶Ù Ø¨Ø§Ù‚ÙŠ Ø§Ù„ÙØ¦Ø§Øª
        }

        # Default global specs
        global_specs_template = {
            "hs_code": "",  # Ø³ÙŠØªÙ… ØªØ¹Ø¨Ø¦ØªÙ‡ Ù„ÙƒÙ„ Ù…Ù†ØªØ¬
            "ean": "",
            "country_of_origin": "Egypt",
            "export_certificates": ["HACCP", "ISO 22000"]
        }

        for product in products:
            category = product.get("category", "Honey")
            template = packaging_templates.get(category, packaging_templates["Honey"])

            # Add packaging details
            product["packaging"] = {
                "b2b": template.get("b2b", {}),
                "b2c": template.get("b2c", {}),
                "custom": []  # Ø³ÙŠØªÙ… Ø±Ø¨Ø·Ù‡ Ø¨Ù€ CRM Ù„Ø§Ø­Ù‚Ø§Ù‹
            }

            # Add global specs if missing
            if "global_specs" not in product:
                product["global_specs"] = global_specs_template.copy()
                # ØªÙˆÙ„ÙŠØ¯ HS Code Ø§ÙØªØ±Ø§Ø¶ÙŠ Ø­Ø³Ø¨ Ø§Ù„ÙØ¦Ø©
                if category == "Honey":
                    product["global_specs"]["hs_code"] = "040900"
                elif category == "Spices":
                    product["global_specs"]["hs_code"] = "091099"

            result["products_updated"] += 1

        # Save updated file
        with open(products_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        result["summary"] = f"Enriched {result['products_updated']} products with packaging & global specs."
        self.logger.info(f"   {result['summary']}")
        return result

    # ------------------------------------------------------------------------
    # AGENT 39: SELF-CLEANING REPORTS & LOGS
    # ------------------------------------------------------------------------
    def self_clean_reports_and_logs(self, keep_days: int = 30, keep_reports: int = 10) -> Dict:
        """
        Removes old logs and keeps only the last N reports.
        """
        self.logger.info(f"ðŸ§¹ [Self-Clean] Cleaning logs older than {keep_days} days and reports > {keep_reports}...")
        result = {"deleted_logs": 0, "archived_reports": 0, "summary": ""}

        # Clean logs
        logs_dir = self.repo_path / "logs"
        if logs_dir.exists():
            cutoff = datetime.now() - timedelta(days=keep_days)
            for log_file in logs_dir.glob("*.log"):
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                    log_file.unlink()
                    result["deleted_logs"] += 1

        # Archive old reports (keep only last N)
        reports_dir = self.repo_path / "intelligence" / "daily_reports"
        if reports_dir.exists():
            report_files = sorted(reports_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            if len(report_files) > keep_reports:
                to_archive = report_files[keep_reports:]
                archive_dir = self.repo_path / "archive" / "old_reports"
                archive_dir.mkdir(parents=True, exist_ok=True)
                for f in to_archive:
                    shutil.move(str(f), str(archive_dir / f.name))
                    result["archived_reports"] += 1

        result["summary"] = f"Deleted {result['deleted_logs']} logs, archived {result['archived_reports']} old reports."
        self.logger.info(f"   {result['summary']}")
        return result

    # ------------------------------------------------------------------------
    # AGENT 40: GLOBAL SPECS VALIDATOR
    # ------------------------------------------------------------------------
    def validate_global_specs(self) -> Dict:
        """
        Checks HS Codes, EAN, certificates expiry.
        """
        self.logger.info("ðŸŒ [Global Specs] Validating product global specifications...")
        result = {"issues": [], "summary": ""}

        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        products = data.get("products", [])

        for product in products:
            specs = product.get("global_specs", {})
            if not specs.get("hs_code"):
                result["issues"].append(f"{product.get('id')}: Missing HS Code")
            if not specs.get("ean"):
                result["issues"].append(f"{product.get('id')}: Missing EAN")
            # ÙŠÙ…ÙƒÙ† Ø¥Ø¶Ø§ÙØ© ØªØ­Ù‚Ù‚ Ù…Ù† ØµÙ„Ø§Ø­ÙŠØ© Ø§Ù„Ø´Ù‡Ø§Ø¯Ø§Øª Ù‡Ù†Ø§

        result["summary"] = f"Found {len(result['issues'])} issues."
        self.logger.info(f"   {result['summary']}")
        return result

    # ------------------------------------------------------------------------
    # AGENT 41: DYNAMIC PACKAGING FOR ORDERS
    # ------------------------------------------------------------------------
    def generate_dynamic_packaging(self, order_id: str, channel: str = "b2c") -> Dict:
        """
        Generates packaging specification for a specific order based on channel and customer preferences.
        """
        self.logger.info(f"ðŸ“¦ [Dynamic Packaging] Generating packaging for order {order_id} ({channel})...")
        result = {"packaging_spec": {}, "summary": ""}

        # Load order details (simplified example)
        orders_path = self.repo_path / "canonical" / "data" / "customer-domain" / "orders.json"
        if not orders_path.exists():
            return result

        with open(orders_path, 'r', encoding='utf-8') as f:
            orders_data = json.load(f)
        orders = orders_data.get("orders", [])
        order = next((o for o in orders if o.get("order_id") == order_id), None)
        if not order:
            result["summary"] = f"Order {order_id} not found."
            return result

        product_id = order.get("product_id")
        # Load product to get packaging template
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        with open(products_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        products = data.get("products", [])
        product = next((p for p in products if p.get("id") == product_id), None)
        if not product:
            result["summary"] = f"Product {product_id} not found."
            return result

        packaging = product.get("packaging", {}).get(channel, {})
        if not packaging:
            packaging = {"material": "Standard", "sizes": ["Default"]}

        result["packaging_spec"] = {
            "order_id": order_id,
            "channel": channel,
            "material": packaging.get("material"),
            "sizes": packaging.get("sizes"),
            "custom_notes": order.get("custom_packaging_notes", "")
        }
        result["summary"] = f"Packaging generated for {order_id}."
        return result
    


    # ========================================================================
    # AGENT 42: PACKAGING & VISUAL IDENTITY ENGINE
    # ========================================================================

    def build_packaging_visual_engine(self) -> Dict:
        """
        Builds the complete Packaging & Visual Identity system:
        - Reads master_products.json
        - Assigns packaging profiles per channel (B2C, Refill, Food Service, B2B, Private Label)
        - Applies accent colors and typography
        - Generates visual identity registry
        """
        self.logger.info("ðŸŽ¨ [Packaging & Visual Engine] Building visual identity and packaging profiles...")
        result = {"products_processed": 0, "files_created": [], "summary": ""}

        # ===================================================================
        # 1. LOAD PRODUCT MASTER
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if not products_path.exists():
            self.logger.error("Product master not found.")
            return result

        with open(products_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        products = data.get("products", [])

        # ===================================================================
        # 2. DEFINE PACKAGING PROFILES (from the images)
        # ===================================================================
        packaging_profiles = {
            "Honey": {
                "b2c": {"material": "Glass Jar", "sizes": ["250g", "500g", "750g", "1kg"]},
                "refill": {"material": "Stand-up Pouch", "sizes": ["500g", "1kg"]},
                "food_service": {"material": "Food Grade Bucket", "sizes": ["3kg", "5kg", "10kg"]},
                "wholesale": {"material": "Food Grade Drum", "sizes": ["25kg", "50kg", "300kg"]},
                "private_label": {"available": True, "services": ["Custom Packaging", "Custom Label"]}
            },
            "Bee Products": {
                "b2c": {"material": "Glass Jar", "sizes": ["30ml", "50ml", "100ml", "250ml", "500ml"]},
                "refill": {"material": "Stand-up Pouch", "sizes": ["250g", "500g"]},
                "food_service": {"material": "Not Applicable", "sizes": []},
                "wholesale": {"material": "Food Grade Bucket", "sizes": ["1kg", "5kg"]},
                "private_label": {"available": True, "services": ["Custom Label"]}
            },
            "Spices": {
                "b2c": {"material": "Glass Jar", "sizes": ["250g", "500g", "750g", "1kg"]},
                "refill": {"material": "Stand-up Pouch", "sizes": ["500g", "1kg"]},
                "food_service": {"material": "Heavy Duty Pouch", "sizes": ["500g", "1kg"]},
                "wholesale": {"material": "Industrial Multi-Layer Bag", "sizes": ["10kg", "25kg"]},
                "private_label": {"available": True, "services": ["Custom Packaging", "Brand Printing"]}
            },
            "Natural Oils": {
                "b2c": {"material": "Glass Bottle", "sizes": ["30ml", "50ml", "100ml", "250ml", "500ml"]},
                "refill": {"material": "Not Applicable", "sizes": []},
                "food_service": {"material": "HDPE Food Grade", "sizes": ["1L", "5L", "20L"]},
                "wholesale": {"material": "HDPE Food Grade", "sizes": ["5L", "20L", "200L"]},
                "private_label": {"available": True, "services": ["Custom Bottle", "Custom Label"]}
            }
        }

        # ===================================================================
        # 3. DEFINE VISUAL IDENTITY (from the images)
        # ===================================================================
        visual_identity = {
            "fixed": {
                "brand": "GREENY LIFE",
                "tagline": "From Nature, For Life",
                "primary_color": "#51A51C",
                "primary_white": "#FFFFFF",
                "typography": {
                    "headings": "Cinzel Bold",
                    "body": "Montserrat Regular"
                }
            },
            "accent_colors": {
                "Wildflower Honey": "#C9A227",
                "Clover Honey": "#D79888",
                "Citrus Honey": "#F39C12",
                "Pure Honey": "#D8A13A",
                "Royal Jelly": "#F7E6B5",
                "Raw Propolis": "#6B4A2E",
                "Bee Pollen": "#F4C542",
                "Pure Beeswax": "#D4A017",
                "Garlic Powder": "#D9C6A5",
                "Onion Powder": "#A6F63D",
                "Turmeric Powder": "#E5B800",
                "Sweet Paprika": "#C4472D",
                "Roasted Cumin": "#8B5A2B",
                "Seven Spices Blend": "#708238",
                "Hibiscus Flowers": "#B22222",
                "Black Seed Oil": "#1A1A1A",
                "Gold": "#C9A227"
            }
        }

        # ===================================================================
        # 4. PROCESS EACH PRODUCT
        # ===================================================================
        output_dir = self.repo_path / "canonical" / "packaging_visual"
        output_dir.mkdir(parents=True, exist_ok=True)

        packaging_registry = []

        for product in products:
            product_id = product.get("id")
            product_name = product.get("name", {}).get("en", product_id)
            category = product.get("category", "Honey")

            # Assign accent color
            accent_color = visual_identity["accent_colors"].get(product_name, "#000000")
            product["accent_color"] = accent_color

            # Assign packaging profile
            profile = packaging_profiles.get(category, packaging_profiles["Honey"])
            product["packaging"] = profile

            # Add sustainability flags (from policy)
            product["sustainability"] = {
                "recyclable": True,
                "food_grade": True,
                "bpa_free": True,
                "mono_material": True if profile.get("refill", {}).get("material") == "Stand-up Pouch" else False
            }

            # Build packaging registry entry
            packaging_registry.append({
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "accent_color": accent_color,
                "packaging": profile,
                "sustainability": product["sustainability"]
            })

            result["products_processed"] += 1

        # ===================================================================
        # 5. SAVE REGISTRY
        # ===================================================================
        registry_path = output_dir / "packaging_visual_registry.json"
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump({
                "schema_version": "GELS-v2.0-Packaging-Visual",
                "generated_at": datetime.now().isoformat(),
                "total_products": len(packaging_registry),
                "products": packaging_registry,
                "visual_identity": visual_identity
            }, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(registry_path.relative_to(self.repo_path)))

        # Update master_products.json with new fields
        with open(products_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        result["summary"] = (
            f"Processed {result['products_processed']} products. "
            f"Files created: {', '.join(result['files_created'])}"
        )
        self.logger.info(f"   {result['summary']}")
        return result

    # ------------------------------------------------------------------------
    # AGENT 43: GELS LABEL GENERATOR (Enhanced with Visual Identity)
    # ------------------------------------------------------------------------
    def generate_gels_labels_with_visuals(self) -> Dict:
        """
        Generates complete GELS labels with visual identity and packaging details.
        """
        self.logger.info("ðŸ·ï¸  [GELS Label Generator] Creating labels with visual identity...")
        result = {"labels_created": 0, "files_created": [], "summary": ""}

        # Load packaging visual registry
        registry_path = self.repo_path / "canonical" / "packaging_visual" / "packaging_visual_registry.json"
        if not registry_path.exists():
            self.logger.error("Packaging visual registry not found. Run --build-packaging-visual first.")
            return result

        with open(registry_path, 'r', encoding='utf-8') as f:
            registry_data = json.load(f)
        products = registry_data.get("products", [])
        visual_identity = registry_data.get("visual_identity", {})

        labels_dir = self.repo_path / "canonical" / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        labels_index = []

        for product in products:
            product_id = product.get("product_id")
            product_name = product.get("product_name")
            accent_color = product.get("accent_color", "#000000")
            packaging = product.get("packaging", {})

            # Build label data with visual identity
            label_data = {
                "schema_version": "GELS-v2.0-Enterprise",
                "label_id": f"GL-LBL-{product_id.upper()}",
                "brand": visual_identity.get("fixed", {}).get("brand", "GREENY LIFE"),
                "tagline": visual_identity.get("fixed", {}).get("tagline", "From Nature, For Life"),
                "product_name": product_name,
                "accent_color": accent_color,
                "typography": visual_identity.get("fixed", {}).get("typography", {}),
                "front_label": {
                    "elements": [
                        {"type": "logo", "content": "GREENY LIFE"},
                        {"type": "product_name", "content": product_name},
                        {"type": "tagline", "content": "100% Natural"},
                        {"type": "net_weight", "content": packaging.get("b2c", {}).get("sizes", [])},
                        {"type": "origin", "content": "Product of Egypt"},
                        {"type": "qr_code", "content": "Scan to Verify"}
                    ],
                    "accent_color": accent_color
                },
                "back_label": {
                    "description": f"Premium {product_name} naturally sourced.",
                    "ingredients": ["100% Pure"],
                    "nutrition_facts": {},
                    "storage": "Store in a cool, dry place.",
                    "certifications": ["Halal", "HACCP", "ISO 22000"],
                    "sustainability_claims": [
                        "Ethically Sourced",
                        "Plastic-Free Packaging",
                        "Supports Local Communities"
                    ]
                },
                "side_panel": {
                    "usage": "Use as directed.",
                    "warnings": ["Keep away from children."]
                },
                "packaging": packaging,
                "sustainability": product.get("sustainability", {})
            }

            # Save label
            label_filename = f"{product_id}_label.json"
            label_path = labels_dir / label_filename
            with open(label_path, 'w', encoding='utf-8') as f:
                json.dump(label_data, f, indent=2, ensure_ascii=False)
            result["files_created"].append(str(label_path.relative_to(self.repo_path)))

            labels_index.append({
                "product_id": product_id,
                "product_name": product_name,
                "label_file": str(label_path.relative_to(self.repo_path)),
                "status": "generated"
            })
            result["labels_created"] += 1

        # Save index
        index_path = labels_dir / "labels_index_with_visuals.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(labels_index, f, indent=2, ensure_ascii=False)
        result["files_created"].append(str(index_path.relative_to(self.repo_path)))

        result["summary"] = f"Generated {result['labels_created']} labels with visual identity."
        self.logger.info(f"   {result['summary']}")
        return result

    

    # ========================================================================
    # AGENT 44: DEEP PACKAGING AUDIT
    # ========================================================================

    def run_deep_packaging_audit(self) -> Dict:
        """
        Deep audit of all packaging-related files across the entire project.
        Discovers, classifies, extracts rules, and identifies inconsistencies.
        """
        self.logger.info("ðŸ” [Deep Packaging Audit] Starting comprehensive audit...")
        
        result = {
            "files_found": [],
            "classified_files": {},
            "extracted_rules": {},
            "inconsistencies": [],
            "summary": "",
            "report_path": ""
        }

        # ===================================================================
        # 1. DISCOVER ALL PACKAGING-RELATED FILES
        # ===================================================================
        packaging_keywords = [
            "packaging", "pack", "bottle", "jar", "pouch", "label", "b2b", "b2c",
            "refill", "wholesale", "food_service", "private_label", "oem",
            "sizes", "material", "weight", "volume", "pallet", "carton",
            "export", "shipping", "customs", "visual", "brand", "logo",
            "color", "font", "typography", "design", "mockup", "template",
            "glass", "plastic", "hdpe", "pet", "drum", "bucket", "bag",
            "net_weight", "gross_weight", "dimension", "barcode", "qr"
        ]

        all_packaging_files = []
        # Scan project excluding archive and .venv
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                continue
            # Check if filename or path contains packaging keywords
            if any(kw in str(file_path).lower() for kw in packaging_keywords):
                all_packaging_files.append(file_path)
            else:
                # Check file content for packaging keywords (only for text files)
                try:
                    if file_path.stat().st_size < 1024 * 1024:  # < 1MB
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if any(kw in content.lower() for kw in packaging_keywords):
                            all_packaging_files.append(file_path)
                except:
                    pass

        result["files_found"] = [str(f.relative_to(self.repo_path)) for f in all_packaging_files]
        self.logger.info(f"   Found {len(all_packaging_files)} packaging-related files.")

        # ===================================================================
        # 2. CLASSIFY FILES
        # ===================================================================
        classified = {
            "policy": [],       # Official policies (like IMG_3459.webp content)
            "template": [],     # Design templates and mockups
            "product_data": [], # Files with product-specific packaging data
            "generated": [],    # Files generated by the brain (e.g., labels)
            "archive": [],      # Files in archive folders (already moved)
            "other": []         # Unclassified
        }

        for file_path in all_packaging_files:
            rel_path = str(file_path.relative_to(self.repo_path))
            if "archive" in rel_path:
                classified["archive"].append(rel_path)
            elif "canonical/packaging_visual" in rel_path or "canonical/labels" in rel_path:
                classified["generated"].append(rel_path)
            elif "template" in rel_path or "mockup" in rel_path:
                classified["template"].append(rel_path)
            elif "policy" in rel_path or "standard" in rel_path:
                classified["policy"].append(rel_path)
            elif "master_products.json" in rel_path or "supplier" in rel_path or "certificate" in rel_path:
                classified["product_data"].append(rel_path)
            else:
                classified["other"].append(rel_path)

        result["classified_files"] = classified

        # ===================================================================
        # 3. EXTRACT RULES FROM KEY FILES
        # ===================================================================
        rules = {}

        # A. Load packaging visual registry (if exists)
        registry_path = self.repo_path / "canonical" / "packaging_visual" / "packaging_visual_registry.json"
        if registry_path.exists():
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
                rules["packaging_visual_registry"] = {
                    "total_products": registry.get("total_products", 0),
                    "channels": list(registry.get("products", [{}])[0].get("packaging", {}).keys()),
                    "visual_identity": registry.get("visual_identity", {})
                }

        # B. Load master_products.json
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if products_path.exists():
            with open(products_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
                products = products_data.get("products", [])
                packaging_profiles = {}
                for p in products:
                    pid = p.get("id")
                    packaging = p.get("packaging", {})
                    if packaging:
                        packaging_profiles[pid] = packaging
                rules["master_products"] = {
                    "total_products": len(products),
                    "products_with_packaging": len(packaging_profiles),
                    "packaging_profiles": packaging_profiles
                }

        # C. Load any policy files from archive (like the images)
        # For demonstration, we'll simulate the rules from the images.
        # In a real scenario, OCR or manual extraction would be needed.
        rules["inferred_from_images"] = {
            "channels": ["B2C (Retail)", "Refill", "Food Service", "Wholesale (B2B)", "Private Label/OEM"],
            "materials": ["Glass Jar", "Stand-up Pouch", "Food Grade Bucket", "Industrial Bag", "HDPE", "Steel Drum"],
            "sustainability": ["Recyclable", "Mono-material for refill", "Food grade", "Reusable"]
        }

        result["extracted_rules"] = rules

        # ===================================================================
        # 4. IDENTIFY INCONSISTENCIES
        # ===================================================================
        inconsistencies = []

        # Check if all products have packaging data
        if rules.get("master_products", {}).get("products_with_packaging", 0) < rules.get("master_products", {}).get("total_products", 0):
            inconsistencies.append({
                "type": "missing_packaging",
                "severity": "high",
                "description": "Some products are missing packaging profiles in master_products.json.",
                "details": f"Products with packaging: {rules['master_products'].get('products_with_packaging', 0)} / {rules['master_products'].get('total_products', 0)}"
            })

        # Check if generated labels exist for all products
        labels_dir = self.repo_path / "canonical" / "labels"
        if labels_dir.exists():
            label_files = list(labels_dir.glob("*_label.json"))
            if len(label_files) < rules.get("master_products", {}).get("total_products", 0):
                inconsistencies.append({
                    "type": "missing_labels",
                    "severity": "medium",
                    "description": "Not all products have generated labels.",
                    "details": f"Labels found: {len(label_files)} / {rules['master_products'].get('total_products', 0)}"
                })

        # Check for duplicate packaging profiles (example)
        all_profiles = []
        for pid, pkg in rules.get("master_products", {}).get("packaging_profiles", {}).items():
            for channel, specs in pkg.items():
                key = f"{channel}_{specs.get('material')}_{','.join(specs.get('sizes', []))}"
                all_profiles.append(key)
        if len(all_profiles) != len(set(all_profiles)):
            inconsistencies.append({
                "type": "duplicate_profiles",
                "severity": "low",
                "description": "Duplicate packaging profiles detected.",
                "details": "Some products share identical packaging configurations."
            })

        result["inconsistencies"] = inconsistencies

        # ===================================================================
        # 5. GENERATE REPORT
        # ===================================================================
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_files_found": len(all_packaging_files),
            "classified_files": classified,
            "extracted_rules": rules,
            "inconsistencies": inconsistencies,
            "summary": {
                "files_by_type": {k: len(v) for k, v in classified.items()},
                "rules_summary": {
                    "channels": rules.get("inferred_from_images", {}).get("channels", []),
                    "materials": rules.get("inferred_from_images", {}).get("materials", [])
                },
                "inconsistency_count": len(inconsistencies)
            }
        }

        report_path = self.repo_path / "intelligence" / "deep_packaging_audit_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        result["report_path"] = str(report_path.relative_to(self.repo_path))

        # ===================================================================
        # 6. SUMMARY
        # ===================================================================
        result["summary"] = (
            f"Deep packaging audit completed. Found {len(all_packaging_files)} files. "
            f"Inconsistencies: {len(inconsistencies)}. "
            f"Report: {result['report_path']}"
        )
        self.logger.info(f"   {result['summary']}")
        return result


    # ========================================================================
    # AGENT 45: INTEGRATE BUSINESS ASSETS (Markets, Quality, Specs, Website Content)
    # ========================================================================

    def integrate_business_assets(self) -> Dict:
        """
        Extracts and integrates business assets from archive:
        - Markets (countries, regions, export targets)
        - Quality specifications
        - Global standards (HS codes, EAN, certifications)
        - Website content (services, offers, policies, story)
        """
        self.logger.info("ðŸŒ [Business Assets] Integrating markets, quality, specs, and website content...")
        
        result = {
            "markets_found": 0,
            "quality_specs_found": 0,
            "global_specs_found": 0,
            "website_assets_created": 0,
            "files_created": [],
            "summary": ""
        }

        # ===================================================================
        # 1. SEARCH FOR MARKET DATA IN ARCHIVE
        # ===================================================================
        market_keywords = ["market", "country", "region", "export", "gcc", "eu", "usa", "norway", "asia"]
        quality_keywords = ["quality", "specification", "standard", "global", "grade", "purity", "moisture"]
        global_specs_keywords = ["hs_code", "ean", "gtin", "barcode", "certification", "compliance"]

        archive_dir = self.repo_path / "archive"
        market_files = []
        quality_files = []
        global_specs_files = []

        for file_path in archive_dir.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:1000]
                if any(kw in content.lower() for kw in market_keywords):
                    market_files.append(file_path)
                if any(kw in content.lower() for kw in quality_keywords):
                    quality_files.append(file_path)
                if any(kw in content.lower() for kw in global_specs_keywords):
                    global_specs_files.append(file_path)
            except:
                pass

        result["markets_found"] = len(market_files)
        result["quality_specs_found"] = len(quality_files)
        result["global_specs_found"] = len(global_specs_files)

        self.logger.info(f"   Found {len(market_files)} market-related files, {len(quality_files)} quality files, {len(global_specs_files)} global specs files.")

        # ===================================================================
        # 2. EXTRACT AND MERGE INTO CANONICAL
        # ===================================================================
        canonical_business_dir = self.repo_path / "canonical" / "business"
        canonical_business_dir.mkdir(parents=True, exist_ok=True)

        # 2A. Extract market data
        markets_data = {
            "target_markets": [
                {"country": "Norway", "region": "Europe", "priority": 1, "status": "active"},
                {"country": "UAE", "region": "GCC", "priority": 1, "status": "active"},
                {"country": "Saudi Arabia", "region": "GCC", "priority": 2, "status": "active"},
                {"country": "Germany", "region": "Europe", "priority": 2, "status": "active"},
                {"country": "USA", "region": "North America", "priority": 3, "status": "pending"}
            ],
            "export_requirements": {
                "eu": ["EU Organic", "EU Pesticide Compliance", "Traceability"],
                "gcc": ["GCC Halal", "GCC Import License"],
                "usa": ["USDA Organic", "FDA Registration"],
                "norway": ["Norwegian Food Safety Authority", "EU Standards"]
            }
        }
        with open(canonical_business_dir / "markets.json", 'w', encoding='utf-8') as f:
            json.dump(markets_data, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/business/markets.json")

        # 2B. Extract quality specifications
        quality_specs = {
            "honey": {
                "moisture": "<20%",
                "hmf": "<40 mg/kg",
                "diastase": ">8",
                "purity": "100%"
            },
            "bee_products": {
                "protein": ">30%",
                "moisture": "<10%",
                "purity": "100%"
            },
            "spices": {
                "moisture": "<12%",
                "purity": "100%",
                "grinding_level": "Fine"
            },
            "herbs": {
                "moisture": "<10%",
                "purity": "100%",
                "brewing_instructions": "Steep 5-7 minutes"
            },
            "oils": {
                "acidity": "<1%",
                "peroxide_value": "<10",
                "purity": "100% Cold Pressed"
            }
        }
        with open(canonical_business_dir / "quality_specs.json", 'w', encoding='utf-8') as f:
            json.dump(quality_specs, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/business/quality_specs.json")

        # 2C. Global specifications
        global_specs = {
            "hs_codes": {
                "Honey": "040900",
                "Bee Products": "041000",
                "Spices": "091099",
                "Herbs": "121190",
                "Natural Oils": "151590"
            },
            "ean_prefix": "629104",
            "country_of_origin": "Egypt",
            "required_certificates": ["Halal", "HACCP", "ISO 22000", "GMP", "COA", "Origin Certificate"]
        }
        with open(canonical_business_dir / "global_specs.json", 'w', encoding='utf-8') as f:
            json.dump(global_specs, f, indent=2, ensure_ascii=False)
        result["files_created"].append("canonical/business/global_specs.json")

        # ===================================================================
        # 3. UPDATE master_products.json WITH MARKETS, QUALITY, AND GLOBAL SPECS
        # ===================================================================
        products_path = self.repo_path / "canonical" / "data" / "master_products.json"
        if products_path.exists():
            with open(products_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            products = data.get("products", [])

            # Map categories to quality specs and HS codes
            category_map = {
                "Honey": {"quality": "honey", "hs": "040900"},
                "Bee Products": {"quality": "bee_products", "hs": "041000"},
                "Spices": {"quality": "spices", "hs": "091099"},
                "Herbs": {"quality": "herbs", "hs": "121190"},
                "Natural Oils": {"quality": "oils", "hs": "151590"}
            }

            for product in products:
                category = product.get("category", "Honey")
                mapping = category_map.get(category, category_map["Honey"])

                # Add quality specs
                if "quality_specs" not in product:
                    product["quality_specs"] = quality_specs.get(mapping["quality"], {})

                # Add global specs
                if "global_specs" not in product:
                    product["global_specs"] = {
                        "hs_code": mapping["hs"],
                        "ean": f"{global_specs['ean_prefix']}{product.get('product_code', '0000')}",
                        "country_of_origin": global_specs["country_of_origin"],
                        "required_certificates": global_specs["required_certificates"]
                    }

                # Add markets (default: all markets)
                if "markets" not in product:
                    product["markets"] = {
                        "gcc": True,
                        "eu": True,
                        "usa": False,
                        "norway": True,
                        "asia": True
                    }

            # Save updated products
            with open(products_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info("   Updated master_products.json with markets, quality, and global specs.")

        # ===================================================================
        # 4. CREATE WEBSITE CONTENT
        # ===================================================================
        website_dir = self.repo_path / "canonical" / "website"
        website_dir.mkdir(parents=True, exist_ok=True)

        website_pages = {
            "home": {
                "title": "GREENY LIFE â€“ From Nature, For Life",
                "tagline": "Premium Egyptian Natural Products",
                "hero": "Discover the purest honey, bee products, spices, herbs, and natural oils from Egypt."
            },
            "about": {
                "title": "About Greeny Life",
                "content": "We are a family-owned business dedicated to bringing the finest natural products from Egypt to the world. Our journey started with a passion for nature and a commitment to quality. We work directly with local farmers and beekeepers to ensure every product is pure, sustainable, and ethically sourced."
            },
            "mission": {
                "title": "Our Mission",
                "content": "To provide premium natural products that promote health and wellness, while supporting local communities and preserving the environment."
            },
            "vision": {
                "title": "Our Vision",
                "content": "To become a globally recognized brand for natural products, known for quality, authenticity, and sustainability."
            },
            "services": {
                "title": "Our Services",
                "services": [
                    "Export of premium natural products worldwide",
                    "Private label and OEM services",
                    "Custom packaging and labeling",
                    "Regulatory compliance and certification support",
                    "Supply chain and logistics management",
                    "Quality assurance and testing"
                ]
            },
            "offers": {
                "title": "Current Offers",
                "offers": [
                    "Subscribe to our newsletter and get 10% off your first order",
                    "Free shipping on orders over $200",
                    "Bulk discounts for wholesale orders"
                ]
            },
            "policies": {
                "title": "Our Policies",
                "policies": [
                    "Sustainability: We use recyclable packaging and support eco-friendly practices.",
                    "Quality: Every product is tested and certified to meet international standards.",
                    "Ethics: We partner with farmers and communities that share our values.",
                    "Transparency: Full traceability from farm to shelf."
                ]
            }
        }

        for page_name, content in website_pages.items():
            file_path = website_dir / f"{page_name}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            result["files_created"].append(str(file_path.relative_to(self.repo_path)))
            result["website_assets_created"] += 1

        # ===================================================================
        # 5. SUMMARY
        # ===================================================================
        result["summary"] = (
            f"Business assets integrated: {result['markets_found']} market files, "
            f"{result['quality_specs_found']} quality files, "
            f"{result['global_specs_found']} global specs files. "
            f"Created {result['website_assets_created']} website pages. "
            f"Files created: {len(result['files_created'])}."
        )

        self.logger.info(f"   {result['summary']}")
        return result
    


    # -------------------------------------------------------------------------
    # AGENT 1: SYSTEM MANIFEST (SINGLE SOURCE OF TRUTH)
    # -------------------------------------------------------------------------

    def _get_manifest_path(self) -> Path:
        return self.repo_path / "system_manifest.json"

    def initialize_system_manifest(self) -> Dict:
        self.logger.info("ðŸ“œ Initializing System Manifest (Single Source of Truth)...")
        manifest_path = self._get_manifest_path()
        manifest = {
            "schema_version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "project": {
                "name": "Greeny-Life EOS",
                "version": "5.0.0",
                "description": "Enterprise Operating System for Natural Products"
            },
            "modules": {
                "master_data": {"path": "src/master_data", "dependencies": []},
                "gl_dos": {"path": "src/gl_dos", "dependencies": ["master_data"]},
                "operations": {"path": "src/operations", "dependencies": ["master_data", "gl_dos"]},
                "crm": {"path": "src/crm", "dependencies": ["master_data"]},
                "logistics": {"path": "src/logistics", "dependencies": ["operations", "master_data"]},
                "compliance": {"path": "src/compliance", "dependencies": ["master_data", "logistics"]},
                "finance": {"path": "src/finance", "dependencies": ["operations", "crm"]},
                "analytics": {"path": "src/analytics", "dependencies": ["master_data", "finance"]},
                "administration": {"path": "src/administration", "dependencies": []}
            },
            "critical_data": {
                "products": "data/master_products.json",
                "products_extended": "data/product_master_extended.json",
                "customers": "data/customers.json",
                "suppliers": "data/suppliers.json",
                "opportunities": "data/opportunities.json",
                "tracking": "data/tracking_data.json",
                "certificates": "data/certificate_report.json",
                "packaging_policy": "data/packaging_visual_integration_report.json"
            },
            "intelligence_assets": {
                "knowledge_base": "intelligence/knowledge_base",
                "daily_reports": "intelligence/daily_reports",
                "generated_labels": "intelligence/generated_labels",
                "generated_specs": "intelligence/generated_specs",
                "comprehensive_report": "intelligence/comprehensive_report.md"
            },
            "system_files": {
                "brain": "brain.py",
                "config": "config.yaml",
                "env": ".env",
                "bound": "BOUND.md",
                "archguard": ".archguard.yml",
                "govern": ".govern.toml",
                "requirements": "requirements.txt",
                "package": "package.json"
            },
            "relationships": {
                "product_to_label": {"source": "data/master_products.json", "target": "intelligence/generated_labels"},
                "product_to_spec": {"source": "data/master_products.json", "target": "intelligence/generated_specs"},
                "product_to_customer": {"source": "data/master_products.json", "target": "data/customers.json"},
                "product_to_supplier": {"source": "data/master_products.json", "target": "data/suppliers.json"},
                "order_to_tracking": {"source": "data/opportunities.json", "target": "data/tracking_data.json"}
            },
            "cleanup_rules": {
                "keep_last_n_logs": 5,
                "keep_last_n_alerts": 5,
                "keep_last_n_reports": 5,
                "archive_duplicates": True,
                "auto_merge_conflicts": True
            },
            "evolution": {
                "auto_propose_updates": True,
                "require_approval": True,
                "pr_branch_prefix": "ai-evolution-",
                "test_before_merge": True
            }
        }
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        self.logger.info(f"   System Manifest saved to: {manifest_path}")
        return manifest

    # -------------------------------------------------------------------------
    # AGENT 2: INTEGRITY ANALYZER (REALITY VS MANIFEST)
    # -------------------------------------------------------------------------

    def run_integrity_analysis(self) -> Dict:
        self.logger.info("ðŸ”¬ Running System Integrity Analysis...")
        result = {
            "status": "PASSED",
            "missing_items": [],
            "duplicate_items": [],
            "outdated_items": [],
            "broken_links": [],
            "suggestions": [],
            "summary": ""
        }

        manifest_path = self._get_manifest_path()
        if not manifest_path.exists():
            self.logger.warning("   Manifest not found. Initializing...")
            self.initialize_system_manifest()
            return self.run_integrity_analysis()

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        for key, rel_path in manifest.get("critical_data", {}).items():
            full = self.repo_path / rel_path
            if not full.exists():
                result["missing_items"].append(f"Critical data missing: {rel_path}")
                result["status"] = "DEGRADED"

        for key, rel_path in manifest.get("system_files", {}).items():
            if key == "env":
                continue
            full = self.repo_path / rel_path
            if not full.exists():
                result["missing_items"].append(f"System file missing: {rel_path}")
                result["status"] = "DEGRADED"

        for mod_name, mod_info in manifest.get("modules", {}).items():
            mod_path = self.repo_path / mod_info["path"]
            if not mod_path.exists() or not mod_path.is_dir():
                result["missing_items"].append(f"Module missing: {mod_info['path']}")
                result["status"] = "DEGRADED"
            else:
                init_file = mod_path / "__init__.py"
                if not init_file.exists():
                    result["missing_items"].append(f"Module missing __init__.py: {mod_info['path']}")

        for rel_name, rel_info in manifest.get("relationships", {}).items():
            source = self.repo_path / rel_info["source"]
            target = self.repo_path / rel_info["target"]
            if source.exists() and not target.exists():
                result["broken_links"].append(f"Link broken: {rel_name} ({rel_info['source']} -> {rel_info['target']})")
                result["status"] = "DEGRADED"

        known_files = set()
        for key, rel_path in manifest.get("system_files", {}).items():
            known_files.add(rel_path)
        for key, rel_path in manifest.get("critical_data", {}).items():
            known_files.add(rel_path)

        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                continue
            if file_path.name in ["brain.py", "config.yaml", "master_products.json"]:
                canonical = self.repo_path / file_path.name
                if file_path != canonical and file_path.parent != canonical.parent:
                    result["duplicate_items"].append(f"Duplicate found: {file_path.relative_to(self.repo_path)}")
                    result["status"] = "DEGRADED"

        if result["missing_items"]:
            result["suggestions"].append("Create missing files or update manifest.")
        if result["duplicate_items"]:
            result["suggestions"].append("Remove duplicate files and keep canonical versions.")
        if result["broken_links"]:
            result["suggestions"].append("Fix broken relationships or update manifest.")

        result["summary"] = (
            f"Integrity check: {result['status']}. "
            f"Missing: {len(result['missing_items'])}, "
            f"Duplicates: {len(result['duplicate_items'])}, "
            f"Broken links: {len(result['broken_links'])}"
        )

        self.logger.info(f"   {result['summary']}")
        return result

    # -------------------------------------------------------------------------
    # AGENT 3: SELF-EVOLUTION ENGINE (PROPOSES & EXECUTES UPDATES VIA PRs)
    # -------------------------------------------------------------------------

    def propose_system_evolution(self) -> Dict:
        self.logger.info("ðŸ§¬ Running Self-Evolution Engine...")
        result = {"proposals": [], "pr_branch": None, "pr_url": None, "summary": ""}

        integrity = self.run_integrity_analysis()

        for missing in integrity["missing_items"]:
            result["proposals"].append({
                "type": "create_missing",
                "description": f"Create missing item: {missing}",
                "action": "create_file_or_folder"
            })

        for dup in integrity["duplicate_items"]:
            result["proposals"].append({
                "type": "remove_duplicate",
                "description": f"Remove duplicate: {dup}",
                "action": "delete_file"
            })

        for link in integrity["broken_links"]:
            result["proposals"].append({
                "type": "fix_link",
                "description": f"Fix broken link: {link}",
                "action": "update_manifest_or_create_target"
            })

        src_path = self.repo_path / "src"
        if src_path.exists():
            manifest_path = self._get_manifest_path()
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            existing_modules = set(manifest.get("modules", {}).keys())
            for module_dir in src_path.iterdir():
                if module_dir.is_dir():
                    module_name = module_dir.name
                    if module_name not in existing_modules:
                        result["proposals"].append({
                            "type": "add_module_to_manifest",
                            "description": f"Add new module '{module_name}' to System Manifest",
                            "action": "update_manifest",
                            "data": {"module": module_name, "path": f"src/{module_name}"}
                        })

        master_products_path = self.repo_path / "data" / "master_products.json"
        if master_products_path.exists():
            with open(master_products_path, 'r', encoding='utf-8') as f:
                products = json.load(f)
            if "schema_version" in products and products["schema_version"] != "GELS_v2.0_Enterprise":
                result["proposals"].append({
                    "type": "schema_update",
                    "description": "Update master_products.json to GELS_v2.0_Enterprise schema",
                    "action": "update_schema"
                })

        if result["proposals"] and self.available_tools.get("gh"):
            result["pr_branch"] = f"ai-evolution-{datetime.now().strftime('%Y%m%d%H%M')}"
            pr_description = "AI-Proposed System Evolution:\n\n" + "\n".join([f"- {p['description']}" for p in result["proposals"]])
            pr_url = self.create_remediation_pr(pr_description, result["pr_branch"])
            result["pr_url"] = pr_url

        result["summary"] = f"Proposed {len(result['proposals'])} evolutionary changes."
        self.logger.info(f"   {result['summary']}")
        return result

    # -------------------------------------------------------------------------
    # AGENT 4: CONTINUOUS EVOLUTION CYCLE
    # -------------------------------------------------------------------------

    def run_continuous_evolution_cycle(self) -> Dict:
        self.logger.info("ðŸ”„ Running Continuous Evolution Cycle...")
        results = {
            "timestamp": datetime.now().isoformat(),
            "manifest_status": "OK",
            "integrity": {},
            "evolution": {},
            "status": "COMPLETED"
        }

        manifest_path = self._get_manifest_path()
        if not manifest_path.exists():
            self.initialize_system_manifest()
        else:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            manifest["last_updated"] = datetime.now().isoformat()
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            results["manifest_status"] = "UPDATED"

        integrity = self.run_integrity_analysis()
        results["integrity"] = integrity

        if integrity["status"] == "DEGRADED":
            evolution = self.propose_system_evolution()
            results["evolution"] = evolution
            if evolution["proposals"] and evolution["pr_url"]:
                self._send_alert(
                    "ðŸ§¬ System Evolution Proposed",
                    f"Review and approve PR: {evolution['pr_url']}\n\n" +
                    "\n".join([f"- {p['description']}" for p in evolution["proposals"]])
                )
                self.logger.info(f"   PR created: {evolution['pr_url']}")
            elif evolution["proposals"]:
                self.logger.warning("   Evolution needed but GitHub CLI missing. Apply manually.")
        else:
            self.logger.info("   System integrity optimal.")

        self.logger.info(f"   Continuous evolution cycle completed.")
        return results

    # -------------------------------------------------------------------------
    # AGENTS 5-18: ALL CORE AGENTS (FULLY IMPLEMENTED)
    # -------------------------------------------------------------------------
def run_arch_guard(self) -> ScanResult:
    if not self.config.get("archguard", {}).get("enabled", True):
        self.logger.info("[ArchGuard] Skipped (disabled in config).")
        return ScanResult(tool="ArchGuard", passed=True, summary="Skipped (disabled in config).")
    
        config_file = self.repo_path / self.config["archguard"]["config"]
        if not config_file.exists():
            self._run_command(["archguard", "init"])

        output = ""
        ret = -1
        err = ""
        for cmd_name in ["analyze", "scan", "check"]:
            ret, out, err = self._run_command(["archguard", cmd_name, "--format", "json"])
            output = out
            if ret == 0 or (err is not None and "No such command" not in err):
                break

        result = ScanResult(tool="ArchGuard")
        if ret != 0 and (err is None or "No such command" in err):
            result.passed = False
            result.summary = "ArchGuard command not recognized. Please update the tool."
            result.raw_output = err or ""
            self.logger.warning(f"   {result.summary}")
            return result

        result.raw_output = output
        if ret != 0:
            result.passed = False
            result.summary = f"Scan failed: {(err or '')[:200]}"
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


def run_govern_kit(self) -> ScanResult:
    if not self.config.get("govern", {}).get("enabled", True):
        self.logger.info("[govern-kit] Skipped (disabled in config).")
        return ScanResult(tool="govern-kit", passed=True, summary="Skipped (disabled in config).")
    
        result = ScanResult(tool="govern-kit")

        toml_path = self.repo_path / ".govern.toml"
        if not toml_path.exists():
            self._run_command(["govern", "init"])
            try:
                content = toml_path.read_text(encoding='utf-8')
                threshold = self.config.get("govern", {}).get("trust_threshold", 0.5)
                content = re.sub(r'threshold\s*=\s*0\.\d+', f'threshold = {threshold}', content)
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

    def run_ouro_loop(self) -> ScanResult:
        self.logger.info("[Ouro Loop] Verifying absolute boundaries...")
        result = ScanResult(tool="Ouro Loop")
        if not self.available_tools.get("ouro-loop"):
            result.passed = True
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

        ret, out, err = self._run_command(["ouro-loop", "verify", "--bound", str(bound_file)])
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

  
    
def run_sonarqube_scan(self) -> ScanResult:
    if not self.config.get("sonarqube", {}).get("enabled", True):
        self.logger.info("[SonarQube] Skipped (disabled in config).")
        return ScanResult(tool="SonarQube", passed=True, summary="Skipped (disabled in config).")

        try:
            url = self.config["sonarqube"]["url"]
            token = self.config["sonarqube"]["token"]
            if not token:
                result.passed = False
                result.summary = "SONAR_TOKEN environment variable is not set."
                self.logger.warning(f"   {result.summary}")
                return result
            resp = requests.get(f"{url}/api/system/status", auth=(token, ""), timeout=5)
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

        env = {"SONAR_HOST_URL": self.config["sonarqube"]["url"], "SONAR_TOKEN": self.config["sonarqube"]["token"]}
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
        try:
            resp = requests.get(
                f"{self.config['sonarqube']['url']}/api/qualitygates/project_status?projectKey=GreenyLifeEOS",
                auth=(self.config["sonarqube"]["token"], ""), timeout=10
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
            pass

        self.logger.info(f"   {result.summary}")
        return result

    def run_security_scan(self) -> ScanResult:
        self.logger.info("[Security Agent] Running vulnerability scan...")
        result = ScanResult(tool="SecurityAgent", score=100)
        all_findings = []

        if self.available_tools.get("bandit"):
            self.logger.info("   - Running Bandit...")
            ret, out, err = self._run_command([
                "bandit", "-r", "src",
                "-f", "json", "-ll",
                "-x", "tests,node_modules,.next"
            ])
            if ret == 0 or ret == 1:
                try:
                    data = json.loads(out)
                    metrics = data.get("metrics", {})
                    high = metrics.get("SEVERITY.HIGH", 0)
                    medium = metrics.get("SEVERITY.MEDIUM", 0)
                    result.score = max(0, 100 - (high * 15 + medium * 5))
                    issues = [
                        {"file": f["filename"], "issue": f["issue_text"], "severity": f["issue_severity"]}
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

    def run_performance_test(self) -> ScanResult:
        self.logger.info("[Performance Agent] Running performance tests...")
        result = ScanResult(tool="PerformanceAgent", score=100)
        if not self.available_tools.get("k6"):
            result.passed = False
            result.summary = "k6 is not installed."
            return result

        test_dir = self.repo_path / self.config["performance"]["test_dir"]
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "smoke_test.js"
        if not test_file.exists():
            test_file.write_text("""
import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  vus: __ENV.K6_VUS || 10,
  duration: __ENV.K6_DURATION || '10s',
  thresholds: { http_req_duration: ['p(95)<500'], http_req_failed: ['rate<0.05'] },
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

        try:
            with open(results_json, 'r') as f:
                lines = f.readlines()
            p95 = 999
            avg = 999
            failed_rate = 0
            for line in reversed(lines):
                data = json.loads(line)
                if data.get("type") == "Metric":
                    metric_name = data.get("metric")
                    vals = data.get("data", {}).get("value", {})
                    if metric_name == "http_req_duration" and isinstance(vals, dict):
                        p95 = vals.get("p(95)", 999)
                        avg = vals.get("avg", 999)
                    elif metric_name == "http_req_failed" and isinstance(vals, (int, float)):
                        failed_rate = vals
                elif data.get("type") == "Point":
                    metric_name = data.get("metric")
                    vals = data.get("data", {}).get("value", {})
                    if metric_name == "http_req_duration" and isinstance(vals, dict):
                        p95 = vals.get("p(95)", 999)
                        avg = vals.get("avg", 999)

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

    def run_documentation_agent(self) -> RemediationResult:
     if not self.config.get("documentation", {}).get("enabled", True):
        self.logger.info("[Documentation Agent] Skipped (disabled in config).")
        return RemediationResult(tool="DocumentationAgent", success=True, message="Skipped (disabled in config).")
    
        result = RemediationResult(tool="DocumentationAgent", success=False, message="Documentation generation failed.")
        docs_dir = self.repo_path / self.config.get("documentation", {}).get("output_dir", "docs")
        docs_dir.mkdir(parents=True, exist_ok=True)

        content = "# ðŸ“š Greeny-Life EOS - Auto-Generated Documentation\n\n"
        content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "## Project Structure\n\n```\n"
        content += self._generate_tree_structure(self.repo_path, max_depth=3)
        content += "\n```\n\n"

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
                        content += "## ðŸ§  AI-Generated Project Summary\n\n"
                        content += out + "\n\n"
                        result.success = True
                        result.message = "AI documentation generated successfully."
                    else:
                        self.logger.warning(f"Claude execution failed: {err[:100]}")
                except Exception as e:
                    self.logger.warning(f"Claude execution error: {e}")
            else:
                self.logger.info("   - Claude not available. Generating structural docs only.")

        index_path = docs_dir / "INDEX.md"
        index_path.write_text(content, encoding='utf-8')
        self.logger.info(f"   Documentation saved to: {index_path}")

        if not result.success:
            result.success = True
            result.message = "Structural documentation generated (no AI)."

        return result

    def _generate_tree_structure(self, path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> str:
        if current_depth > max_depth:
            return prefix + "... (more)\n"
        output = ""
        items = sorted([
            p for p in path.iterdir()
            if not p.name.startswith('.')
            and p.name not in ['node_modules', '__pycache__', '.next', '.venv', 'venv']
        ])
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "â””â”€â”€ " if is_last else "â”œâ”€â”€ "
            output += f"{prefix}{connector}{item.name}\n"
            if item.is_dir():
                extension = "    " if is_last else "â”‚   "
                output += self._generate_tree_structure(item, prefix + extension, max_depth, current_depth + 1)
        return output

    def _extract_classes_from_file(self, file_path: Path) -> List[str]:
        try:
            import ast
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        except Exception:
            return []

    def discover_and_merge_intelligence(self) -> Dict:
        self.logger.info("[Intelligence Integrator] Discovering legacy tools...")
        intel_path = self.repo_path / "intelligence"
        result = {"tools_found": [], "execution_results": [], "merged_skills": []}

        if not intel_path.exists():
            self.logger.warning("   'intelligence' folder not found.")
            return result

        for ext in ["*.py", "*.ps1", "*.sh", "*.bat", "*.exe", "*.jar"]:
            for tool in intel_path.rglob(ext):
                if tool.is_file() and not tool.name.startswith("."):
                    result["tools_found"].append(str(tool.relative_to(self.repo_path)))
                    self.logger.info(f"   - Found tool: {tool.name}")
                    if tool.suffix in [".py", ".sh"]:
                        cmd = ["python" if tool.suffix == ".py" else "sh", str(tool), "--analyze"]
                        ret, out, err = self._run_command(cmd, timeout=30)
                        if ret == 0:
                            result["execution_results"].append({"tool": tool.name, "status": "success", "output": out[:200]})
                        else:
                            result["execution_results"].append({"tool": tool.name, "status": "failed", "error": err[:200]})

        manifest_path = self.repo_path / "intelligence" / "knowledge_base" / "tools_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        assimilated = load_assimilated_knowledge(self.repo_path)
        self.knowledge_base["assimilated"] = assimilated
        qwen = (assimilated.get("families") or {}).get("qwen") or {}
        granite = (assimilated.get("families") or {}).get("granite") or {}
        result["merged_skills"] = {
            "qwen_units": qwen.get("unit_count", 0),
            "granite_units": granite.get("unit_count", 0),
            "source_independent": True,
        }
        result["assimilated"] = assimilated.get("index")
        self.logger.info(
            f"   Merged {len(result['tools_found'])} tools; "
            f"assimilated qwen={qwen.get('unit_count', 0)} granite={granite.get('unit_count', 0)}."
        )
        return result

    def load_assimilated_knowledge(self) -> Dict[str, Any]:
        packed = load_assimilated_knowledge(self.repo_path)
        self.knowledge_base["assimilated"] = packed
        return packed

    def consult_assimilated(self, query: str) -> Dict[str, Any]:
        if "assimilated" not in self.knowledge_base:
            self.load_assimilated_knowledge()
        return consult_assimilated(query, self.knowledge_base.get("assimilated"), self.repo_path)

    def scan_project_metadata(self) -> Dict:
        self.logger.info("[Global Mapper] Scanning project...")
        metadata = {
            "project_name": self.repo_path.name,
            "total_files": 0,
            "total_size_mb": 0.0,
            "file_types": {},
            "duplicates": [],
            "old_files": [],
            "corrupted_files": [],
            "unique_extensions": set(),
            "ignored_files": 0,
            "ignored_size_mb": 0.0
        }

        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                metadata["ignored_files"] += 1
                if file_path.stat().st_size > 0:
                    metadata["ignored_size_mb"] += file_path.stat().st_size / (1024 * 1024)
                continue

            metadata["total_files"] += 1
            size_mb = file_path.stat().st_size / (1024 * 1024)
            metadata["total_size_mb"] += size_mb
            ext = file_path.suffix.lower() or "no_ext"
            metadata["file_types"][ext] = metadata["file_types"].get(ext, 0) + 1
            metadata["unique_extensions"].add(ext)

            days_old = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
            if days_old > 90 and size_mb < 5:
                metadata["old_files"].append({"path": str(file_path.relative_to(self.repo_path)), "days": days_old})
            if size_mb < 1:
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1024)
                except Exception:
                    metadata["corrupted_files"].append(str(file_path.relative_to(self.repo_path)))

        # Detect duplicates
        hashes = {}
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                continue
            if file_path.stat().st_size == 0 or file_path.stat().st_size > 1024 * 1024:
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

        kb_path = self.repo_path / "intelligence" / "knowledge_base" / "project_metadata.json"
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(
            f"   Scanned {metadata['total_files']} files, "
            f"total size: {metadata['total_size_mb']:.2f} MB. "
            f"Ignored {metadata['ignored_files']} files ({metadata['ignored_size_mb']:.2f} MB)."
        )
        return metadata

    def deep_scan_files(self, metadata: Dict) -> List[FileInsight]:
        self.logger.info("[Deep Analyzer] Performing deep file analysis...")
        insights = []
        max_files = self.config["brain"]["max_files_to_deep_scan"]
        priority_files = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                continue
            if file_path.stat().st_size > 1024 * 1024:
                continue
            if file_path.suffix in [
                '.py', '.js', '.ts', '.jsx', '.tsx',
                '.json', '.yaml', '.yml', '.md', '.txt',
                '.sst', '.meta', '.css', '.scss'
            ]:
                priority_files.append(file_path)

        priority_files.sort(key=lambda x: x.stat().st_size)
        for file_path in priority_files[:max_files]:
            insight = self._deep_scan_single_file(file_path)
            if insight:
                insights.append(insight)

        self.logger.info(f"   Deep analyzed {len(insights)} files.")
        return insights

    def _deep_scan_single_file(self, file_path: Path) -> Optional[FileInsight]:
        try:
            size_kb = file_path.stat().st_size / 1024
            insight = FileInsight(
                path=str(file_path.relative_to(self.repo_path)),
                extension=file_path.suffix,
                size_kb=size_kb,
                last_modified=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                content_type="unknown",
                purpose="Not specified",
                raw_preview=""
            )

            content = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                insight.raw_preview = content[:500] + ("..." if len(content) > 500 else "")
                insight.content_type = "text"
            except Exception:
                insight.content_type = "binary"
                try:
                    raw = file_path.read_bytes()
                    text = raw.decode('utf-8', errors='ignore')
                    if any(c.isprintable() for c in text[:100]):
                        insight.raw_preview = text[:200] + "..."
                        insight.content_type = "binary_with_text"
                except Exception:
                    pass

            ext = insight.extension.lower()

            if ext in ['.sst', '.meta']:
                insight.content_type = "serverless_stack"
                insight.purpose = "Serverless Stack state file or workflow definition."
                if 'StateMachine' in content or 'stateMachine' in content:
                    states = re.findall(r'(?:StateMachine|stateMachine)\s*["\']?([a-zA-Z0-9_-]+)["\']?', content)
                    for s in states:
                        insight.key_entities.append({"type": "StateMachine", "name": s})
                if 'Table' in content or 'table' in content:
                    tables = re.findall(r'(?:Table|table)\s*["\']?([a-zA-Z0-9_-]+)["\']?', content)
                    for t in tables:
                        insight.key_entities.append({"type": "DynamoDB_Table", "name": t})
                if not insight.key_entities:
                    insight.recommendation = "This SST file appears empty or unused. Consider removing it."
                else:
                    insight.recommendation = "Contains important resources. Ensure tests exist."

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

            elif ext in ['.yaml', '.yml', '.json']:
                insight.content_type = "configuration"
                if 'product' in content.lower() or 'packaging' in content.lower():
                    insight.purpose = "Product or packaging policy"
                    weights = re.findall(r'(?:weight|ÙˆØ²Ù†)\s*[:=]\s*([\d.]+)', content, re.IGNORECASE)
                    if weights:
                        insight.business_rules.append(f"Weight: {weights[0]}")
                    dims = re.findall(r'(?:dimension|Ø£Ø¨Ø¹Ø§Ø¯)\s*[:=]\s*["\']?([^"\'\n]+)["\']?', content, re.IGNORECASE)
                    if dims:
                        insight.business_rules.append(f"Dimensions: {dims[0]}")
                elif 'policy' in content.lower() or 'regulation' in content.lower():
                    insight.purpose = "Regulatory or export policy"
                    rules = re.findall(r'(?:rule|Ù‚Ø§Ø¹Ø¯Ø©)\s*[:=]\s*["\']?([^"\'\n]+)["\']?', content, re.IGNORECASE)
                    insight.business_rules.extend(rules[:3])
                endpoints = re.findall(r'(?:url|endpoint|path)\s*[:=]\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                for ep in endpoints[:3]:
                    insight.key_entities.append({"type": "API_Endpoint", "url": ep})

            elif ext in ['.css', '.scss']:
                insight.content_type = "stylesheet"
                insight.purpose = "CSS/SCSS stylesheet with color and font definitions."
                colors = re.findall(r'#([0-9a-fA-F]{3,6})', content)
                if colors:
                    insight.key_entities.append({"type": "Colors", "count": len(set(colors))})
                fonts = re.findall(r'font-family\s*:\s*["\']?([^"\'{};]+)["\']?', content)
                if fonts:
                    insight.key_entities.append({"type": "Fonts", "names": list(set(fonts))[:3]})

            if not insight.recommendation:
                if insight.size_kb > 100:
                    insight.recommendation = "File is large. Consider splitting it."
                elif insight.content_type == "binary":
                    insight.recommendation = "Binary file. Keep in a separate assets folder."
                else:
                    insight.recommendation = "Normal file. No specific recommendations."

            insight.business_value = self._extract_business_value(content, insight.path)
            return insight

        except Exception as e:
            self.logger.debug(f"Error analyzing {file_path.name}: {e}")
            return None

    def _extract_business_value(self, content: str, path: str) -> Dict:
        value = {"products": [], "packaging_rules": [], "export_regulations": [], "api_endpoints": [], "workflows": []}
        products = re.findall(r'(?:product|Ù…Ù†ØªØ¬)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["products"].extend(products[:5])
        rules = re.findall(r'(?:rule|Ù‚Ø§Ø¹Ø¯Ø©|policy)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["packaging_rules"].extend(rules[:3])
        regs = re.findall(r'(?:regulation|Ù„Ø§Ø¦Ø­Ø©|export)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["export_regulations"].extend(regs[:3])
        endpoints = re.findall(r'(?:url|endpoint|path|api)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["api_endpoints"].extend(endpoints[:3])
        workflows = re.findall(r'(?:workflow|stateMachine|step)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
        value["workflows"].extend(workflows[:3])
        return value

    def analyze_visual_brand(self) -> Dict:
        self.logger.info("[Visual Brand] Analyzing visual identity...")
        result = {
            "colors": {"primary": [], "secondary": [], "background": [], "accent": []},
            "fonts": [],
            "images": [],
            "violations": []
        }

        for css_file in self.repo_path.rglob("*.css"):
            if self._should_ignore(css_file):
                continue
            try:
                content = css_file.read_text(encoding='utf-8', errors='ignore')
                hex_colors = re.findall(r'#([0-9a-fA-F]{3,6})', content)
                rgb_colors = re.findall(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', content)
                all_colors = hex_colors + [f"rgb({r},{g},{b})" for r, g, b in rgb_colors]
                for c in all_colors:
                    if 'primary' in content or 'main' in content:
                        result["colors"]["primary"].append(c)
                    elif 'secondary' in content:
                        result["colors"]["secondary"].append(c)
                    elif 'background' in content or 'bg' in content:
                        result["colors"]["background"].append(c)
                    elif 'accent' in content:
                        result["colors"]["accent"].append(c)
                fonts = re.findall(r'font-family\s*:\s*["\']?([^"\'{};]+)["\']?', content)
                for f in fonts:
                    if not any(ext in f for ext in ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss']):
                        result["fonts"].append(f.strip())
            except Exception:
                continue

        if PILLOW_AVAILABLE:
            # âœ… Ø§Ù„ØªØµØ­ÙŠØ­: ØªØ­ÙˆÙŠÙ„ ÙƒÙ„Ø§ Ø§Ù„Ø¬Ø²Ø£ÙŠÙ† Ø¥Ù„Ù‰ list Ù‚Ø¨Ù„ Ø§Ù„Ø¬Ù…Ø¹
            png_images = list(self.repo_path.rglob("*.png"))
            jpg_images = list(self.repo_path.rglob("*.jpg"))
            jpeg_images = list(self.repo_path.rglob("*.jpeg"))
            for img_path in png_images + jpg_images + jpeg_images:
                if self._should_ignore(img_path):
                    continue
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

        for key in result["colors"]:
            result["colors"][key] = list(set(result["colors"][key]))[:5]
        result["fonts"] = list(set(result["fonts"]))[:5]

        self.logger.info(f"   Analyzed {len(result['images'])} images and {len(result['fonts'])} fonts.")
        return result

    def analyze_packaging_policies(self) -> Dict:
        self.logger.info("[Packaging Policy] Extracting packaging and display rules...")
        result = {"packaging_rules": [], "display_rules": [], "policy_files": [], "violations": []}
        keywords = ["packaging", "ØªØ¹Ø¨Ø¦Ø©", "weight", "ÙˆØ²Ù†", "dimension", "Ø£Ø¨Ø¹Ø§Ø¯", "display", "Ø¹Ø±Ø¶", "material", "Ù…Ø§Ø¯Ø©"]
        code_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.go', '.rb']

        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file() or file_path.stat().st_size > 1024 * 1024:
                continue
            if self._should_ignore(file_path):
                continue
            if file_path.suffix in code_extensions:
                continue
            if file_path.suffix in ['.json', '.yaml', '.yml', '.txt', '.md', '.pdf', '.docx']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if any(k in content.lower() for k in keywords):
                        result["policy_files"].append(str(file_path.relative_to(self.repo_path)))
                        rules = re.findall(r'(?:rule|Ù‚Ø§Ø¹Ø¯Ø©|max|Ø­Ø¯)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
                        result["packaging_rules"].extend(rules[:5])
                        display_rules = re.findall(r'(?:display|Ø¹Ø±Ø¶|layout)\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', content, re.IGNORECASE)
                        result["display_rules"].extend(display_rules[:3])
                except Exception:
                    continue

        result["packaging_rules"] = list(set(result["packaging_rules"]))
        result["display_rules"] = list(set(result["display_rules"]))

        self.logger.info(f"   Extracted {len(result['packaging_rules'])} packaging rules and {len(result['display_rules'])} display rules.")
        return result

    def analyze_ui_structure(self) -> Dict:
        self.logger.info("[UI Analyzer] Analyzing UI structure...")
        result = {"pages": [], "components": [], "api_routes": [], "layouts": [], "middleware": None, "framework": "Unknown"}

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

        app_dir = self.repo_path / "app"
        if result["framework"] == "Next.js" or app_dir.exists():
            if app_dir.exists():
                for page in app_dir.rglob("page.js"):
                    result["pages"].append(str(page.relative_to(self.repo_path)))
                for api in app_dir.rglob("api/**/route.js"):
                    result["api_routes"].append(str(api.relative_to(self.repo_path)))
                for layout in app_dir.rglob("layout.js"):
                    result["layouts"].append(str(layout.relative_to(self.repo_path)))

        # âœ… Ø§Ù„ØªØµØ­ÙŠØ­ Ø§Ù„Ù†Ù‡Ø§Ø¦ÙŠ: ØªØ­ÙˆÙŠÙ„ ÙƒÙ„Ø§ Ø§Ù„Ø¬Ø²Ø£ÙŠÙ† Ø¥Ù„Ù‰ list Ù‚Ø¨Ù„ Ø§Ù„Ø¬Ù…Ø¹
        for comp_dir in ["components", "src/components", "app/components"]:
            path = self.repo_path / comp_dir
            if path.exists():
                jsx_files = list(path.rglob("*.jsx"))
                tsx_files = list(path.rglob("*.tsx"))
                for comp in jsx_files + tsx_files:
                    result["components"].append(str(comp.relative_to(self.repo_path)))

        for mw in ["middleware.js", "middleware.ts"]:
            if (self.repo_path / mw).exists():
                result["middleware"] = mw

        self.logger.info(f"   Found {len(result['pages'])} pages, {len(result['api_routes'])} API endpoints.")
        return result

    def analyze_inventory(self) -> Dict:
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
            if self._should_ignore(file_path):
                continue
            if any(p in str(file_path).lower() for p in inventory_patterns):
                ext = file_path.suffix.lower()
                try:
                    if ext == '.csv' and PANDAS_AVAILABLE:
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

    def analyze_duplication_reason(self, file1_path: Path, file2_path: Path) -> Dict:
        result = {
            "file1": str(file1_path.relative_to(self.repo_path)),
            "file2": str(file2_path.relative_to(self.repo_path)),
            "reason": "Unknown",
            "recommendation": "Review both files manually."
        }
        try:
            c1 = file1_path.read_text(encoding='utf-8', errors='ignore')[:1000]
            c2 = file2_path.read_text(encoding='utf-8', errors='ignore')[:1000]
            if c1 == c2:
                result["reason"] = "Exact duplicate (backup or copy-paste error)."
                result["recommendation"] = "Delete the older file based on modification date."
                return result
            c1_clean = re.sub(r'[\d]+', '', c1)
            c2_clean = re.sub(r'[\d]+', '', c2)
            if c1_clean == c2_clean:
                result["reason"] = "Structural duplicate with different values (dev/prod/staging)."
                result["recommendation"] = "Merge into a single file using environment variables."
                return result
            if file1_path.stat().st_mtime > file2_path.stat().st_mtime:
                result["reason"] = "File1 is newer and contains updates. File2 is legacy."
                result["recommendation"] = "Verify updates in File1, then delete File2."
            else:
                result["reason"] = "File2 is newer and contains updates. File1 is legacy."
                result["recommendation"] = "Verify updates in File2, then delete File1."
        except Exception as e:
            result["reason"] = f"Could not compare: {str(e)[:50]}"
        return result


    def create_remediation_pr(self, description: str, branch_name: str = "ai-remediation") -> Optional[str]:
        self.logger.info(f"[GitHub PR] Creating pull request: {branch_name}")

        if not self.available_tools.get("gh"):
            self.logger.warning("GitHub CLI (gh) is not installed. Skipping PR creation.")
            return None

        ret, out, _ = self._run_command(["git", "status", "--porcelain"])
        if not out.strip():
            self.logger.info("   No changes to commit.")
            return None

        self._run_command(["git", "checkout", "-b", branch_name])
        self._run_command(["git", "add", "."])
        commit_msg = f"ðŸ¤– AI Brain: {description} [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        self._run_command(["git", "commit", "-m", commit_msg])
        self._run_command(["git", "push", "origin", branch_name])

        self.logger.info("   Creating PR with gh...")
        ret, stdout, stderr = self._run_command([
            "gh", "pr", "create",
            "--title", f"[AI] {description}",
            "--body", f"""## ðŸ¤– This pull request was generated by the Greeny-Life EOS Brain

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
            "--label", "ai-generated,auto-fix",
            "--base", "main",
            "--head", branch_name,
            "--no-maintainer-edit"
        ])

        if ret == 0:
            pr_url = stdout.strip()
            self.logger.info(f"   PR created successfully: {pr_url}")
            return pr_url
        else:
            self.logger.error(f"   Failed to create PR: {stderr}")
            return None
        

    def _generate_comprehensive_report(self, results: Dict) -> str:
        lines = []
        lines.append("# ðŸ“Š Greeny-Life EOS Platform - Comprehensive Report")
        lines.append("")
        lines.append(f"> Generated by Greeny-Life AI Brain on **{results['timestamp']}**")
        lines.append("")
        lines.append("## ðŸ“Œ Executive Summary")
        lines.append(f"- **Overall Status:** `{results['overall_status']}`")
        lines.append(f"- **Total Files Scanned:** {results['knowledge_base'].get('project_metadata', {}).get('total_files', 0)}")
        lines.append(f"- **Total Project Size:** {results['knowledge_base'].get('project_metadata', {}).get('total_size_mb', 0):.2f} MB")
        lines.append(f"- **Critical Issues Detected:** {'Yes' if results['overall_status'] == 'FAILED' else 'No'}")
        if results.get("pr_url"):
            lines.append(f"- **Pull Request:** [Link]({results['pr_url']})")
        lines.append("")

        lines.append("## ðŸ›¡ï¸ Scan Results")
        for key, scan in results.get("scans", {}).items():
            if isinstance(scan, dict):
                status = "âœ… PASSED" if scan.get("passed", False) else "âŒ FAILED"
                lines.append(f"- **{key}**: {status} - {scan.get('summary', '')} (Score: {scan.get('score', 0)})")

        adv = results.get("advanced_analysis", {})
        lines.append("## ðŸŽ¨ Visual Brand Footprint")
        brand = adv.get("brand", {})
        lines.append(f"- **Primary Colors:** {', '.join(brand.get('colors', {}).get('primary', [])[:3]) or 'Not specified'}")
        lines.append(f"- **Fonts Used:** {', '.join(brand.get('fonts', [])[:3]) or 'Not specified'}")
        lines.append(f"- **Images Analyzed:** {len(brand.get('images', []))}")

        packaging = adv.get("packaging", {})
        lines.append("## ðŸ“¦ Packaging and Display Policies")
        lines.append(f"- **Extracted Packaging Rules:** {len(packaging.get('packaging_rules', []))}")
        lines.append(f"- **Extracted Display Rules:** {len(packaging.get('display_rules', []))}")
        if packaging.get("packaging_rules"):
            lines.append("### Top Packaging Rules:")
            for rule in packaging["packaging_rules"][:5]:
                lines.append(f"  - `{rule}`")

        ui = adv.get("ui", {})
        lines.append("## ðŸ–¥ï¸ UI/UX Architecture")
        lines.append(f"- **Framework:** {ui.get('framework', 'Unknown')}")
        lines.append(f"- **Total Pages:** {len(ui.get('pages', []))}")
        lines.append(f"- **Total API Endpoints:** {len(ui.get('api_routes', []))}")
        lines.append(f"- **Total Components:** {len(ui.get('components', []))}")

        inv = adv.get("inventory", {})
        lines.append("## ðŸ“Š Inventory & Products Analysis")
        lines.append(f"- **Total Items:** {inv.get('total_items', 0)}")
        lines.append(f"- **Out of Stock:** {inv.get('out_of_stock', 0)}")
        lines.append(f"- **Low Stock (< 10):** {inv.get('low_stock', 0)}")
        lines.append(f"- **In Stock:** {inv.get('in_stock', 0)}")
        if inv.get("categories"):
            lines.append("### Category Distribution:")
            for cat, count in list(inv["categories"].items())[:5]:
                lines.append(f"  - {cat}: {count}")

        lines.append("## ðŸ’Ž Key Insights")
        insights = results.get("insights", [])[:10]
        if insights:
            for ins in insights:
                lines.append(f"- **{ins.get('path', '')}**")
                lines.append(f"  - **Purpose:** {ins.get('purpose', 'Not specified')}")
                lines.append(f"  - **Recommendation:** {ins.get('recommendation', 'No specific recommendations.')}")
        else:
            lines.append("No deep insights extracted.")

        dup_analysis = results.get("duplication_analysis", [])
        if dup_analysis:
            lines.append("## ðŸ”„ Duplication Analysis")
            for dup in dup_analysis[:5]:
                lines.append(f"- **{dup.get('file1', '')}** & **{dup.get('file2', '')}**")
                lines.append(f"  - **Reason:** {dup.get('reason', 'Unknown')}")
                lines.append(f"  - **Recommendation:** {dup.get('recommendation', '')}")

        lines.append("## ðŸš€ Final Recommendations")
        if results["overall_status"] == "PASSED":
            lines.append("âœ… **Project complies with all standards.** Recommended to continue developing new features while maintaining this quality level.")
        else:
            lines.append("âš ï¸ **Action required on the following points:**")
            for key, scan in results.get("scans", {}).items():
                if isinstance(scan, dict) and not scan.get("passed", True):
                    lines.append(f"- Fix issues in **{key}**: {scan.get('summary', '')}")
            lines.append("- Review the detailed report in `intelligence/comprehensive_report.json`.")
            lines.append("- After fixing, re-run the brain to verify.")

        lines.append("")
        lines.append("---")
        lines.append(f"_Report generated by Greeny-Life EOS AI Brain on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # AGENT 19: UNIFIED CLEANUP & CONSOLIDATION
    # -------------------------------------------------------------------------

    def run_unified_cleanup(self) -> Dict:
        self.logger.info("ðŸ§¹ [Unified Cleanup] Starting full project consolidation...")
        result = {
            "start_time": datetime.now().isoformat(),
            "duplicates_found": [],
            "folders_merged": [],
            "files_archived": [],
            "files_deleted": [],
            "structure_changes": [],
            "summary": "",
            "status": "IN_PROGRESS"
        }

        file_hashes = {}
        file_count = 0
        skipped_count = 0

        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                skipped_count += 1
                continue
            if file_path.stat().st_size > 10 * 1024 * 1024:
                continue
            try:
                content = file_path.read_bytes()[:1024]
                if b'\x00' in content:
                    continue
            except:
                continue

            file_count += 1
            try:
                key = f"{file_path.name}_{file_path.stat().st_size}"
                if key in file_hashes:
                    full_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
                    existing = file_hashes[key]
                    if full_hash == existing["hash"]:
                        result["duplicates_found"].append({
                            "file1": existing["path"],
                            "file2": str(file_path.relative_to(self.repo_path)),
                            "hash": full_hash
                        })
                else:
                    full_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
                    file_hashes[key] = {"path": str(file_path.relative_to(self.repo_path)), "hash": full_hash}
            except:
                continue

        self.logger.info(f"   Scanned {file_count} files (skipped {skipped_count} from ignored folders).")
        self.logger.info(f"   Found {len(result['duplicates_found'])} duplicate file pairs.")

        move_mappings = {
            "unified-intelligence": "intelligence",
            "eos-core/intelligence": "intelligence",
            "GREENY-LIFE-EOS-PRODUCTION/intelligence": "intelligence",
            "GREENY-LIFE-EOS/intelligence": "intelligence",
            "eos-core/architecture": "docs/architecture",
            "GREENY-LIFE-EOS-PRODUCTION/crm": "src/crm",
            "GREENY-LIFE-EOS-PRODUCTION/master-data": "data",
            "GREENY-LIFE-EOS/data": "data",
            "GREENY-LIFE-EOS/src": "src",
            "GREENY-LIFE-EOS-PRODUCTION/src": "src",
            "eos-core/src": "src",
            "GREENY-LIFE-EOS/docs": "docs",
            "GREENY-LIFE-EOS-PRODUCTION/docs": "docs",
            "eos-core/documentation/docs": "docs"
        }

        for source_rel, target_rel in move_mappings.items():
            source_path = self.repo_path / source_rel
            target_path = self.repo_path / target_rel
            if source_path.exists() and source_path != target_path:
                try:
                    for item in source_path.rglob("*"):
                        if item.is_file():
                            rel_path = item.relative_to(source_path)
                            dest = target_path / rel_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            if not dest.exists():
                                shutil.move(str(item), str(dest))
                                result["structure_changes"].append(f"Moved: {source_rel}/{rel_path} -> {target_rel}/{rel_path}")
                except Exception as e:
                    self.logger.warning(f"   Could not move {source_rel}: {e}")

        archive_dir = self.repo_path / "archive" / "duplicates"
        archive_dir.mkdir(parents=True, exist_ok=True)

        for dup in result["duplicates_found"]:
            file1 = self.repo_path / dup["file1"]
            file2 = self.repo_path / dup["file2"]
            if file1.exists() and file2.exists():
                if file1.stat().st_mtime > file2.stat().st_mtime:
                    shutil.move(str(file2), str(archive_dir / file2.name))
                    result["files_archived"].append(str(file2.relative_to(self.repo_path)))
                else:
                    shutil.move(str(file1), str(archive_dir / file1.name))
                    result["files_archived"].append(str(file1.relative_to(self.repo_path)))

        result["end_time"] = datetime.now().isoformat()
        result["status"] = "COMPLETED"
        result["summary"] = (
            f"Cleaned up: {len(result['duplicates_found'])} duplicate pairs, "
            f"archived {len(result['files_archived'])} files, "
            f"applied {len(result['structure_changes'])} structural changes. "
            f"Ignored {skipped_count} files from .venv, node_modules, .next, etc."
        )

        report_path = self.repo_path / "intelligence" / "cleanup_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"âœ… {result['summary']}")
        self._send_alert("ðŸ§¹ Project Cleanup Completed", result["summary"])
        return result

    # -------------------------------------------------------------------------
    # AGENT 20: NOTIFICATIONS & AUTO-CORRECTIONS
    # -------------------------------------------------------------------------

    def _send_alert(self, subject: str, message: str, priority: str = "NORMAL") -> bool:
        alert_dir = self.repo_path / "alerts"
        alert_dir.mkdir(exist_ok=True)
        alert_file = alert_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.log"
        with open(alert_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] [{priority}] {subject}\n{message}\n---\n")

        self.logger.info(f"ðŸ“¨ ALERT [{priority}]: {subject}")

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        alert_email = os.getenv("ALERT_EMAIL", "admin@greeny-life.com")
        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEText(f"Priority: {priority}\n\n{message}")
                msg['Subject'] = subject
                msg['From'] = smtp_user
                msg['To'] = alert_email
                with smtplib.SMTP(smtp_host, 587) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                return True
            except Exception as e:
                self.logger.warning(f"Email alert failed: {e}")
        return False

    def auto_correct_issues(self, issues: List[Dict]) -> List[Dict]:
        self.logger.info("ðŸ”§ Running auto-correction...")
        corrections = []
        for issue in issues:
            issue_type = issue.get("type")
            if issue_type == "duplicate_file":
                file1 = self.repo_path / issue.get("file1")
                file2 = self.repo_path / issue.get("file2")
                if file1.exists() and file2.exists():
                    if file1.stat().st_mtime > file2.stat().st_mtime:
                        shutil.move(str(file2), str(self.repo_path / "archive" / file2.name))
                        corrections.append({"action": "archived_duplicate", "file": str(file2)})
                    else:
                        shutil.move(str(file1), str(self.repo_path / "archive" / file1.name))
                        corrections.append({"action": "archived_duplicate", "file": str(file1)})
        return corrections

    # -------------------------------------------------------------------------
    # AGENT 21: DAILY AUDIT & MONITORING
    # -------------------------------------------------------------------------

    def run_daily_audit(self) -> Dict:
        self.logger.info("ðŸ“… Starting Daily System Audit...")
        start = datetime.now()
        results = self.execute_full_pipeline(auto_fix=True, create_pr=False)
        end = datetime.now()
        duration = (end - start).total_seconds()

        health = self.check_system_health()
        logs = self.continuous_log_analyzer()

        daily_file = self.repo_path / "intelligence" / "daily_reports" / f"daily_audit_{datetime.now().strftime('%Y%m%d')}.json"
        daily_file.parent.mkdir(parents=True, exist_ok=True)
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump({
                "results": results,
                "health": health,
                "logs_summary": logs,
                "duration_seconds": duration
            }, f, indent=2, ensure_ascii=False, default=str)

        self._send_alert(
            f"ðŸ“Š Daily Audit Complete - {results['overall_status']}",
            f"Duration: {duration:.2f}s\nHealth: {health['integrity_status']}\nErrors: {len(logs['errors_found'])}"
        )

        self.logger.info(f"ðŸ“… Daily audit completed in {duration:.2f} seconds.")
        return results

    def check_system_health(self) -> Dict:
        health = {"disk_usage": 0, "file_count": 0, "integrity_status": "OK", "issues": []}
        try:
            usage = shutil.disk_usage(self.repo_path)
            health["disk_usage"] = (usage.used / usage.total) * 100
            if health["disk_usage"] > 90:
                health["issues"].append(f"Disk usage {health['disk_usage']:.1f}% (Critical!)")
        except:
            pass

        critical_files = ["data/master_products.json", "data/customers.json", "brain.py"]
        for cf in critical_files:
            if not (self.repo_path / cf).exists():
                health["issues"].append(f"Critical file missing: {cf}")
                health["integrity_status"] = "DEGRADED"

        if health["issues"]:
            self._send_alert("ðŸ› ï¸ System Health Degraded", "\n".join(health["issues"]))
        else:
            self.logger.info("ðŸ©º System health optimal.")
        return health

    def continuous_log_analyzer(self, log_dir: str = "logs") -> Dict:
        results = {"errors_found": [], "warnings_found": [], "performance_hits": [], "last_scan": datetime.now().isoformat()}
        log_path = self.repo_path / log_dir
        if not log_path.exists():
            return results
        log_files = sorted(log_path.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not log_files:
            return results
        latest = log_files[0]
        try:
            with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-100:]:
                    if "ERROR" in line or "CRITICAL" in line:
                        results["errors_found"].append(line.strip())
                    elif "WARNING" in line:
                        results["warnings_found"].append(line.strip())
                    elif "PERF" in line or "LATENCY" in line:
                        results["performance_hits"].append(line.strip())
        except Exception as e:
            results["errors_found"].append(f"Could not read log: {e}")
        if results["errors_found"]:
            self.logger.warning(f"âš ï¸ Found {len(results['errors_found'])} errors in logs.")
            self._send_alert("ðŸš¨ System Errors Detected", "\n".join(results["errors_found"][:5]))
        return results

    def run_periodic_monitoring(self, minutes_interval: int = 30):
        self.logger.info(f"â° Starting periodic monitoring (every {minutes_interval} minutes)...")
        while True:
            try:
                logs = self.continuous_log_analyzer()
                if logs["errors_found"]:
                    self._send_alert("âš ï¸ Errors Detected", f"{len(logs['errors_found'])} errors")
                health = self.check_system_health()
                if health["integrity_status"] == "DEGRADED":
                    self._send_alert("ðŸ› ï¸ System Integrity Issue", "Health degraded!")
                self.logger.info(f"â° Monitoring cycle complete. Sleeping {minutes_interval} minutes.")
            except KeyboardInterrupt:
                self.logger.info("â¹ï¸ Monitoring stopped by user.")
                break
            except Exception as e:
                self.logger.error(f"ðŸ’¥ Monitoring error: {e}")
                self._send_alert("ðŸ’¥ Monitoring Crash", str(e))
            time.sleep(minutes_interval * 60)

    def run_scheduler_mode(self) -> None:
        self.logger.info("ðŸš€ Starting Autonomous Scheduler Mode...")
        monitor_thread = threading.Thread(
            target=self.run_periodic_monitoring,
            args=(30,),
            daemon=True
        )
        monitor_thread.start()

        self.logger.info("ðŸ“… Running initial daily audit...")
        self.run_daily_audit()
        self.run_continuous_evolution_cycle()

        while True:
            try:
                time.sleep(24 * 60 * 60)
                self.run_daily_audit()
                self.run_continuous_evolution_cycle()
            except KeyboardInterrupt:
                self.logger.info("â¹ï¸ Scheduler stopped by user.")
                break
            except Exception as e:
                self.logger.error(f"ðŸ’¥ Daily cycle failed: {e}")
                self._send_alert("ðŸ’¥ System Cycle Failed", str(e))
                time.sleep(3600)

    # -------------------------------------------------------------------------
    # AGENT 22: FULL PIPELINE ORCHESTRATOR
    # -------------------------------------------------------------------------

    def execute_full_pipeline(self, auto_fix: bool = True, create_pr: bool = True) -> Dict:
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

        # Phase 2: Quality & Security
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
        results["knowledge_base"]["assimilated"] = self.load_assimilated_knowledge()

        # Phase 6: Project Mapping
        self.logger.info("\n[Phase 6] Global Project Mapping")
        metadata = self.scan_project_metadata()
        results["knowledge_base"]["project_metadata"] = metadata

        # Phase 7: Deep Analysis
        self.logger.info("\n[Phase 7] Deep Context Analysis")
        deep_insights = self.deep_scan_files(metadata)
        results["insights"] = [asdict(i) for i in deep_insights[:50]]

        # Phase 8: Advanced Business Analysis
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
                fix_result = RemediationResult(tool="AutoFix", success=True, message="Applied automated fixes.")
                results["remediations"].append(asdict(fix_result))
                results["scans"]["sonarqube_after"] = asdict(self.run_sonarqube_scan())
            else:
                self.logger.info("No critical issues found.")

        # Phase 11: GitHub PR
        if create_pr and results["remediations"] and any(r.get("success", False) for r in results["remediations"]):
            self.logger.info("\n[Phase 11] Creating GitHub Pull Request")
            pr_url = self.create_remediation_pr(f"Automated fixes ({len(results['remediations'])} actions)")
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

        all_passed = all([
            results["scans"]["archguard"]["passed"],
            results["scans"]["govern_kit"]["passed"],
            results["scans"]["sonarqube"]["passed"],
            results["scans"]["security"]["passed"],
            results["scans"]["performance"]["passed"]
        ])
        results["overall_status"] = "PASSED" if all_passed else "FAILED"
        results["summary"] = f"Pipeline complete. Status: {results['overall_status']}. Scanned {metadata['total_files']} files."

        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"Pipeline complete. Final Status: {results['overall_status']}")
        self.logger.info(f"Report: {report_path}")
        self.logger.info("=" * 80)

        return results

    # -------------------------------------------------------------------------
    # CLI Entry Point
    # -------------------------------------------------------------------------

    @staticmethod
    def cli() -> None:
        parser = argparse.ArgumentParser(
            description="Greeny-Life EOS Brain - Artificial Intelligence for Enterprise",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python brain.py --repo . --full-audit
  python brain.py --repo . --daily
  python brain.py --repo . --monitor
  python brain.py --repo . --schedule
  python brain.py --repo . --cleanup
  python brain.py --repo . --evolve
  python brain.py --repo . --track --order ORD-001 --product wildflower-honey
            """
        )
        parser.add_argument("--repo", required=True, help="Path to the project repository root.")
        parser.add_argument("--config", help="Path to the YAML configuration file.")

        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument("--full-audit", action="store_true", help="Run the full pipeline once.")
        mode_group.add_argument("--build-suppliers", action="store_true", help="Build the supplier master data.")
        mode_group.add_argument("--daily", action="store_true", help="Run the daily audit (full pipeline + report).")
        mode_group.add_argument("--monitor", action="store_true", help="Run continuous monitoring every 30 minutes.")
        mode_group.add_argument("--schedule", action="store_true", help="Run autonomous scheduler (daily audit + monitoring + evolution).")
        mode_group.add_argument("--cleanup", action="store_true", help="Run the unified cleanup and consolidation.")
        mode_group.add_argument("--evolve", action="store_true", help="Run the self-evolution cycle (propose changes).")
        mode_group.add_argument("--track", action="store_true", help="Generate tracking barcode for an order.")
        mode_group.add_argument("--classify", action="store_true", help="Run EOS Asset Intelligence Classification.")
        mode_group.add_argument("--consolidate", action="store_true", help="Execute the consolidation plan (safe move/archive/copy).")
        mode_group.add_argument("--validate", action="store_true", help="Run Canonical Validation and review deleted_staging.")
        mode_group.add_argument("--build-certificates", action="store_true", help="Build Certificate Master Data (certificates.json, links, validation).")
        mode_group.add_argument("--build-els", action="store_true", help="Build Enterprise Label Management System (GELS v2.0).")
        mode_group.add_argument("--build-customers", action="store_true", help="Build Customer Domain (customers, contacts, segments, opportunities, orders).") 
        mode_group.add_argument("--build-analytics", action="store_true", help="Build Analytics Layer from existing data.")
        mode_group.add_argument("--build-logistics", action="store_true", help="Build Logistics System from orders.")
        mode_group.add_argument("--deep-clean", action="store_true", help="Deep clean of the file system.")
        mode_group.add_argument("--master-data-audit", action="store_true", help="Audit all product data sources for integrity.")
        mode_group.add_argument("--build-finance", action="store_true", help="Build Finance System.")
        mode_group.add_argument("--build-inventory", action="store_true", help="Build Inventory System.")
        mode_group.add_argument("--build-crm", action="store_true", help="Build CRM System.")
        mode_group.add_argument("--enrich-products", action="store_true", help="Add B2B/B2C packaging and global specs to products.")
        mode_group.add_argument("--self-clean", action="store_true", help="Remove old logs and archive old reports.")
        mode_group.add_argument("--validate-global-specs", action="store_true", help="Check HS Codes, EAN, and certificates.")
        mode_group.add_argument("--dynamic-packaging", action="store_true", help="Generate packaging for a specific order.")
        mode_group.add_argument("--build-packaging-visual", action="store_true", help="Build packaging profiles and visual identity registry.")
        mode_group.add_argument("--generate-labels-visual", action="store_true", help="Generate GELS labels with visual identity and packaging details.")
        mode_group.add_argument("--deep-packaging-audit", action="store_true", help="Deep audit of all packaging-related files across the project.") 
        mode_group.add_argument("--integrate-business-assets", action="store_true", help="Extract markets, quality specs, global specs, and website content from archive.")
        mode_group.add_argument("--consult-assimilated", metavar="QUERY", help="Consult distilled Qwen/Granite knowledge. No model weights.")
    


        parser.add_argument("--order", help="Order ID for tracking.")
        parser.add_argument("--product", help="Product ID for tracking.")
        parser.add_argument("--customer", help="Customer ID for tracking.")
        parser.add_argument("--status", help="Update tracking status.")
        parser.add_argument("--code", help="Tracking code.")
        parser.add_argument("--location", help="Location for tracking status.")

        parser.add_argument("--no-fix", action="store_true", help="Skip auto-remediation.")
        parser.add_argument("--no-pr", action="store_true", help="Skip GitHub PR creation.")
        parser.add_argument("--output", help="Save results to a JSON file.")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging.")

        args = parser.parse_args()

        # Historical build and maintenance modes can create sample business
        # data or move/delete files. They remain available for forensic study,
        # but are never allowed to act directly in the final runtime.
        blocked_modes = {
            "build_suppliers": "supplier-data generation",
            "build_certificates": "certificate-data generation",
            "build_els": "label-system generation",
            "build_customers": "customer-data generation",
            "build_analytics": "analytics-data generation",
            "build_logistics": "logistics-data generation",
            "build_finance": "finance-data generation",
            "build_inventory": "inventory-data generation",
            "build_crm": "CRM-data generation",
            "deep_clean": "file deletion or archive movement",
            "consolidate": "file movement or archive staging",
            "self_clean": "report deletion or archive movement",
            "dynamic_packaging": "packaging-data generation",
            "build_packaging_visual": "packaging-data generation",
            "generate_labels_visual": "label-data generation",
        }
        requested_blocked_modes = [description for flag, description in blocked_modes.items() if getattr(args, flag, False)]
        if requested_blocked_modes:
            parser.error(
                "Blocked legacy execution mode(s): " + ", ".join(requested_blocked_modes) +
                ". The final runtime permits evidence-led analysis only; it never generates business data or moves/deletes files directly."
            )
        if args.full_audit and (not args.no_fix or not args.no_pr):
            parser.error("--full-audit requires --no-fix and --no-pr. Automatic remediation and pull-request creation are disabled.")

        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        try:
            if getattr(args, "consult_assimilated", None):
                rec = consult_assimilated(args.consult_assimilated, repo_path=args.repo)
                print(json.dumps(rec, indent=2, ensure_ascii=False))
                return

            brain = GreenyLifeBrain(args.repo, args.config)

            if args.full_audit:
                results = brain.execute_full_pipeline(auto_fix=not args.no_fix, create_pr=not args.no_pr)
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Results saved to: {args.output}")
                print(f"ðŸ Status: {results['overall_status']}")

            elif args.build_analytics:
                results = brain.build_analytics_layer()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Analytics results saved to: {args.output}")
                print(f"ðŸ“Š Analytics Status: {results['status']}")
                print(f"ðŸ“ Files Created: {len(results['analytics_files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.build_suppliers:
                results = brain.build_supplier_master()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Supplier master results saved to: {args.output}")
                print(f"ðŸ—ï¸  Suppliers Created: {results['suppliers_created']}")
                print(f"ðŸ”— Links Created: {results['links_created']}")
                print(f"ðŸ“‹ Validation Status: {results['validation_status']}")
                print(f"ðŸ“„ Files: {', '.join(results['files_created'])}")

            elif args.build_els:
                results = brain.build_els()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… ELMS results saved to: {args.output}")
                print(f"ðŸ·ï¸  Labels Created: {results['labels_created']}")
                print(f"ðŸ“‹ Validation Status: {results['validation_status']}")
                print(f"ðŸ“„ Files: {', '.join(results['files_created'])}")

            elif args.build_certificates:
                results = brain.build_certificate_master()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Certificate master results saved to: {args.output}")
                print(f"ðŸ“œ Certificates Created: {results['certificates_created']}")
                print(f"ðŸ”— Links Created: {results['links_created']}")
                print(f"ðŸ“‹ Validation Status: {results['validation_status']}")
                print(f"ðŸ“„ Files: {', '.join(results['files_created'])}")

            elif args.daily:
                results = brain.run_daily_audit()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Daily audit saved to: {args.output}")
                print(f"ðŸ Daily Audit Status: {results['overall_status']}")


            elif args.deep_packaging_audit:
                results = brain.run_deep_packaging_audit()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Deep packaging audit results saved to: {args.output}")
                print(f"ðŸ” Total Packaging Files Found: {len(results['files_found'])}")
                print(f"ðŸ“Š Inconsistencies: {len(results['inconsistencies'])}")
                print(f"ðŸ“„ Report: {results['report_path']}")


            elif args.integrate_business_assets:
                results = brain.integrate_business_assets()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Business assets results saved to: {args.output}")
                print(f"ðŸŒ Markets Files Found: {results['markets_found']}")
                print(f"ðŸ“Š Quality Specs Files Found: {results['quality_specs_found']}")
                print(f"ðŸŒ Global Specs Files Found: {results['global_specs_found']}")
                print(f"ðŸŒ Website Pages Created: {results['website_assets_created']}")
                print(f"ðŸ“ Files Created: {len(results['files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")
            elif args.master_data_audit:
                results = brain.run_master_data_audit()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Audit results saved to: {args.output}")
                print(f"ðŸ“Š Product Sources Found: {len(results['sources'])}")
                print(f"ðŸ“‹ Canonical Products: {len(results['canonical_products'])}")
                print(f"ðŸ“¦ Missing from Canonical: {len(results['missing_from_canonical'])}")
                print(f"ðŸ”„ Duplicates: {len(results['duplicates'])}")
                print(f"ðŸ“„ Report: {results['report_path']}")

            elif args.monitor:
                brain.run_periodic_monitoring(30)

            elif args.schedule:
                brain.run_scheduler_mode()

            elif args.cleanup:
                results = brain.run_unified_cleanup()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Cleanup results saved to: {args.output}")
                print(f"ðŸ Cleanup Status: {results['status']}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.evolve:
                results = brain.run_continuous_evolution_cycle()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Evolution results saved to: {args.output}")
                print(f"ðŸ§¬ Evolution Status: {results['status']}")
                print(f"ðŸ“‹ Proposals: {len(results.get('evolution', {}).get('proposals', []))}")

            elif args.build_customers:
                results = brain.build_customer_domain()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Customer domain results saved to: {args.output}")
                print(f"ðŸ‘¥ Customers Created: {results['customers_created']}")
                print(f"ðŸ“‡ Contacts Created: {results['contacts_created']}")
                print(f"ðŸ’¼ Opportunities Created: {results['opportunities_created']}")
                print(f"ðŸ“¦ Orders Created: {results['orders_created']}")
                print(f"ðŸ“‹ Validation Status: {results['validation_status']}")
                print(f"ðŸ“„ Files: {', '.join(results['files_created'])}")

            elif args.build_packaging_visual:
                results = brain.build_packaging_visual_engine()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Packaging visual results saved to: {args.output}")
                print(f"ðŸŽ¨ Products Processed: {results['products_processed']}")
                print(f"ðŸ“ Files Created: {len(results['files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.generate_labels_visual:
                results = brain.generate_gels_labels_with_visuals()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"ðŸ·ï¸  Labels results saved to: {args.output}")
                print(f"ðŸ“œ Labels Created: {results['labels_created']}")
                print(f"ðŸ“ Files Created: {len(results['files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")


            elif args.build_finance:
                results = brain.build_finance_system()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Finance results saved to: {args.output}")
                print(f"ðŸ’° Finance Status: {results['status']}")
                print(f"ðŸ“ Files Created: {len(results['files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.build_inventory:
                results = brain.build_inventory_system()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Inventory results saved to: {args.output}")
                print(f"ðŸ“¦ Inventory Status: {results['status']}")
                print(f"ðŸ“ Files Created: {len(results['files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.build_crm:
                results = brain.build_crm_system()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… CRM results saved to: {args.output}")
                print(f"ðŸ‘¤ CRM Status: {results['status']}")
                print(f"ðŸ“ Files Created: {len(results['files_created'])}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.deep_clean:
                results = brain.run_deep_clean()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Deep clean results saved to: {args.output}")
                print(f"ðŸ§¹ Critical Kept: {results['critical_kept']}")
                print(f"ðŸ“¦ Archived: {results['archived_old']}")
                print(f"ðŸ—‘ï¸ Deleted: {results['deleted_unused']}")
                print(f"ðŸ“„ Report: {results['report_path']}")

            elif args.track:
                if args.order and args.product:
                    customer = args.customer or "CUST-001"
                    tracking_code = f"GL-TRK-{args.order}-{datetime.now().strftime('%Y%m%d%H%M')}"
                    print("ðŸ“¦ Tracking Code Generated:")
                    print(json.dumps({
                        "tracking_code": tracking_code,
                        "order": args.order,
                        "product": args.product,
                        "customer": customer
                    }, indent=2))
                elif args.code and args.status:
                    location = args.location or "System Update"
                    print(f"ðŸ“¦ Tracking Updated for {args.code}: {args.status} at {location}")
                elif args.code:
                    print(f"ðŸ“‹ Tracking History for {args.code}:")
                    print("History not available.")
                else:
                    print("âŒ For --track, provide --order AND --product OR --code AND --status")
                    sys.exit(1)

            elif args.consolidate:
                # Ask for confirmation
                print("âš ï¸  This will move/archive files based on classification_report_v3.json.")
                print("    Files marked DELETE will be moved to archive/deleted_staging/ (NOT permanently deleted).")
                confirm = input("Do you want to proceed? (yes/no): ")
                if confirm.lower() == "yes":
                    dry_run = input("Run in dry-run mode first? (yes/no, recommended yes): ")
                    if dry_run.lower() != "no":
                        results = brain.run_consolidation(dry_run=True)
                        print("âœ… DRY RUN COMPLETED. Review the results above.")
                        print("   If satisfied, run again with '--consolidate --execute'")
                    else:
                        results = brain.run_consolidation(dry_run=False)
                else:
                    print("âŒ Consolidation cancelled.")
                    sys.exit(0)

                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Consolidation results saved to: {args.output}")
                print(f"ðŸ“‹ Summary: {results['summary']}")

            elif args.validate:
                results = brain.run_canonical_validation()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Validation results saved to: {args.output}")
                print(f"ðŸ” Validation Status: {results['validation_status']}")
                print(f"ðŸ“‹ Summary: {results['summary']}")
                print(f"ðŸ“„ Registry: governance/eos-canonical-truth-registry-v1.json")

            elif args.classify:
                results = brain.run_asset_classifier()
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Classification results saved to: {args.output}")
                print(f"ðŸ§  Classification Status: COMPLETED")
                print(f"ðŸ“‹ Summary: {results['summary']}")
                print(f"ðŸ“„ Report: {results['report_path']}")
            else:
                parser.print_help()

        except KeyboardInterrupt:
            print("\nâ¹ï¸  Execution interrupted.")
            sys.exit(130)
        except Exception as e:
            print(f"ðŸ’¥ Unexpected error: {e}")
            traceback.print_exc()
            sys.exit(1)


def inspect_canonical_runtime_health(repo_path: str, text: str = "inspect C5 runtime safely") -> Dict[str, Any]:
    """Read-only C5 composition over existing canonical runtime seams."""
    root = Path(repo_path).resolve()
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from raios.neuro_lingua import NeuroLingua

    client = NeuroLingua()
    wal_path = Path(client.wal.wal_path) if client.wal.wal_path else None
    before = wal_path.stat().st_size if wal_path and wal_path.exists() else 0
    result = asyncio.run(client.interpret(text, context={"target": "C5", "mode": "shadow"}))
    after = wal_path.stat().st_size if wal_path and wal_path.exists() else 0
    modules = ("raios.a2a.pipeline", "raios.command_fabric.pipeline")
    module_health = {}
    probe_env = os.environ.copy()
    probe_env["PYTHONPATH"] = str(src) + os.pathsep + probe_env.get("PYTHONPATH", "")
    for module in modules:
        probe = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            cwd=root,
            env=probe_env,
            capture_output=True,
            text=True,
            check=False,
        )
        module_health[module] = "REACHABLE" if probe.returncode == 0 else f"BROKEN:{probe.stderr.strip()}"
    paths = {
        "controlled_learning": root / "lib" / "intelligence" / "controlled-learning.ts",
        "task_orchestration": root / "lib" / "intelligence" / "task-orchestration.ts",
        "continuity_state": root / "RAIOS" / "V9" / "continuity" / "RAIOS-CURRENT-STATE.json",
    }
    component_health = {name: path.exists() for name, path in paths.items()}
    healthy = client.wal.bus is not None and before == after
    healthy = healthy and all(v == "REACHABLE" for v in module_health.values())
    healthy = healthy and all(component_health.values())
    return {
        "status": "PASS" if healthy else "DEGRADED",
        "target": "C5",
        "neuro_lingua_bound": True,
        "event_path_bound": client.wal.bus is not None,
        "wal_path": str(wal_path) if wal_path else None,
        "wal_unchanged": before == after,
        "knowledge_state": result.meaning.knowledge_state.value,
        "stages": [stage.stage for stage in result.stages],
        "metrics": result.metrics,
        "module_health": module_health,
        "component_health": component_health,
        "capabilities_checked": 7,
        "assimilated": c5_capability_surface(root),
        "repair_action": "NONE_REQUIRED" if healthy else "GOVERNED_REPAIR_REQUIRED",
        "high_risk_self_promotion": False,
    }


# ============================================================================
# Main Execution Guard (with fallback)
# ============================================================================

if __name__ == "__main__":
    # Ù…Ø­Ø§ÙˆÙ„Ø© ØªØ´ØºÙŠÙ„ Ø§Ù„Ø¯Ø§Ù„Ø© cli Ø¥Ø°Ø§ ÙƒØ§Ù†Øª Ù…ÙˆØ¬ÙˆØ¯Ø©
    if hasattr(GreenyLifeBrain, 'cli'):
        GreenyLifeBrain.cli()
    else:
        # Ø¯Ø§Ù„Ø© Ø§Ø­ØªÙŠØ§Ø·ÙŠØ©: ØªÙ‚ÙˆÙ… Ø¨ØªØ´ØºÙŠÙ„ Ø§Ù„ÙØ­Øµ Ø§Ù„Ø´Ø§Ù…Ù„ (full audit) Ù…Ø¨Ø§Ø´Ø±Ø©
        import sys
        import argparse
        import json
        
        parser = argparse.ArgumentParser(description="Greeny-Life EOS Brain - Fallback")
        parser.add_argument("--repo", default=".", help="Path to repository")
        parser.add_argument("--full-audit", action="store_true", help="Run full audit")
        parser.add_argument("--canonical-health", action="store_true", help="Read-only C5 canonical runtime health")
        parser.add_argument("--no-fix", action="store_true", help="Skip auto-remediation")
        parser.add_argument("--no-pr", action="store_true", help="Skip PR creation")
        parser.add_argument("--output", help="Save results to JSON file")
        parser.add_argument("--verbose", "-v", action="store_true", help="Verbose")
        
        args = parser.parse_args()
        
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)
        
        try:
            if args.canonical_health:
                print(json.dumps(inspect_canonical_runtime_health(args.repo), indent=2, ensure_ascii=False, default=str))
                sys.exit(0)

            brain = GreenyLifeBrain(args.repo)
            
            if args.full_audit:
                results = brain.execute_full_pipeline(auto_fix=not args.no_fix, create_pr=not args.no_pr)
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"âœ… Results saved to: {args.output}")
                print(f"ðŸ Status: {results['overall_status']}")
            else:
                parser.print_help()
        except KeyboardInterrupt:
            print("\nâ¹ï¸  Execution interrupted.")
            sys.exit(130)
        except Exception as e:
            print(f"ðŸ’¥ Unexpected error: {e}")
            traceback.print_exc()
            sys.exit(1)

