#!/usr/bin/env python3
"""
Greeny-Life EOS - Master Enterprise Brain V5.0 (Full English & All Agents)
Integrates all agents (Next.js, SST, Logistics, Knowledge Mapper, Intelligence)
with interactive manual approval for file optimization, duplication management, and secure archiving.
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

import importlib

try:
    Image = importlib.import_module("PIL.Image")
except ImportError:
    Image = None

try:
    pd = importlib.import_module("pandas")
except ImportError:
    pd = None

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/brain-master-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============================================================================
# 1. Intelligence Integrator Agent (Self-Discovery)
# ============================================================================
class IntelligenceIntegrator:
    def __init__(self, brain_instance):
        self.brain = brain_instance
        self.intel_path = brain_instance.repo_path / "intelligence"
        self.tools_manifest = {}
        self._discover_tools()

    def _discover_tools(self):
        if not self.intel_path.exists():
            self.intel_path.mkdir(parents=True, exist_ok=True)
            return
        for item in self.intel_path.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower()
                if ext in [".py", ".ps1", ".sh", ".bat", ".exe", ".jar"]:
                    self.tools_manifest[str(item)] = {"name": item.stem, "type": ext[1:]}


# ============================================================================
# 2. Master Enterprise Brain Core
# ============================================================================
class GreenyLifeBrain:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.logger = logging.getLogger("GreenyLifeBrain")
        self.integrator = IntelligenceIntegrator(self)

    def _is_ignored(self, path: Path) -> bool:
        ignored = [".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode", ".next", "brain_archive"]
        return any(part in ignored for part in path.parts)

    # ------------------------------------------------------------------------
    # Specialized Domain Agents (Next.js, SST, Logistics, Compliance)
    # ------------------------------------------------------------------------
    def analyze_nextjs_structure(self) -> Dict:
        self.logger.info("Analyzing Next.js structure...")
        result = {"has_next": False, "pages": [], "api_routes": []}
        app_dir = self.repo_path / "app"
        if app_dir.exists():
            result["has_next"] = True
            for page_file in app_dir.rglob("page.js"):
                result["pages"].append(str(page_file.relative_to(self.repo_path)))
            for api_file in app_dir.rglob("api/**/route.js"):
                result["api_routes"].append(str(api_file.relative_to(self.repo_path)))
        return result

    def analyze_sst_files(self) -> Dict:
        self.logger.info("Analyzing SST files...")
        result = {"sst_files": [], "total_size_mb": 0}
        for f in self.repo_path.rglob("*.sst"):
            if not self._is_ignored(f):
                result["sst_files"].append(str(f.relative_to(self.repo_path)))
                result["total_size_mb"] += f.stat().st_size / (1024 * 1024)
        return result

    def validate_product_compliance(self, product_data: Dict) -> bool:
        """Validates product compliance against packing policies."""
        if product_data.get("weight_kg", 0) > 20:
            self.logger.warning(f"Product exceeds weight limit: {product_data.get('id')}")
            return False
        return True

    def track_shipment(self, tracking_id: str) -> Dict:
        """Simulates product shipment tracking."""
        return {"tracking_id": tracking_id, "status": "active_simulated"}

    # ------------------------------------------------------------------------
    # Deep Inspection & Interactive Proposal Engine
    # ------------------------------------------------------------------------
    def scan_and_propose(self) -> List[Dict]:
        self.logger.info("Running deep comprehensive scan across all project files and agents...")
        all_files = [f for f in self.repo_path.rglob("*") if f.is_file() and not self._is_ignored(f)]
        hashes = {}
        proposals = []

        for f in all_files:
            rel_path = str(f.relative_to(self.repo_path))
            size = f.stat().st_size

            # Absolute duplication check via MD5 Hash of file content
            try:
                with open(f, "rb") as file:
                    file_hash = hashlib.md5(file.read()).hexdigest()
                if file_hash in hashes and size > 0:
                    proposals.append({
                        "type": "DELETE_DUPLICATE",
                        "target": rel_path,
                        "original": hashes[file_hash],
                        "reason": f"100% identical content match with: {hashes[file_hash]}"
                    })
                else:
                    hashes[file_hash] = rel_path
            except:
                pass

            # Archival proposal for old large audit reports or log files
            if f.suffix.lower() in [".log", ".tmp"] or "legacy_audit_reports" in rel_path:
                if size > 1024 * 500:
                    proposals.append({
                        "type": "ARCHIVE_OR_CLEAN",
                        "target": rel_path,
                        "reason": "Large or legacy audit report/log file, suggested for safe archiving."
                    })

        return proposals

    def interactive_execution(self):
        next_info = self.analyze_nextjs_structure()
        sst_info = self.analyze_sst_files()
        proposals = self.scan_and_propose()

        print(f"\n" + "="*65)
        print(f" 👑 GREENY-LIFE EOS - MASTER BRAIN V5.0 (FULL AGENT ORCHESTRATION)")
        print(f" 🌐 Next.js Detected: {next_info['has_next']} | ☁️ SST Files: {len(sst_info['sst_files'])}")
        print(f" 🛠️ Total Improvement & Optimization Proposals: {len(proposals)}")
        print(f" NOTICE: No action will be executed without your explicit manual approval.")
        print(f"=====================================================\n")

        if not proposals:
            print("✅ The project workspace is completely clean! No interventions required.")
            return

        for idx, prop in enumerate(proposals, 1):
            print(f"\n[{idx}/{len(proposals)}] Action Type: {prop['type']}")
            print(f"📁 Target File: {prop['target']}")
            print(f"💡 Reason: {prop['reason']}")
            
            choice = input("❓ Do you approve executing this action? (y = approve to archive / n = skip / q = quit): ").strip().lower()
            
            if choice == 'q':
                print("🛑 Operation aborted by user.")
                break
            elif choice == 'y':
                self._execute_action(prop)
            else:
                print("⏭️ Action skipped.")

    def _execute_action(self, prop: Dict):
        target_path = self.repo_path / prop['target']
        if not target_path.exists():
            print("⚠️ File not found or already processed.")
            return

        try:
            archive_dir = self.repo_path / "brain_archive"
            archive_dir.mkdir(exist_ok=True)
            
            dest_path = archive_dir / Path(prop['target']).name
            # Preserve folder structure inside archive if needed or flat move
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target_path), str(dest_path))
            print(f"✅ [Safely Archived]: {prop['target']} -> brain_archive/")
        except Exception as e:
            print(f"❌ Error executing action: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Greeny-Life Master Enterprise Brain")
    parser.add_argument("--repo", default=".", help="Path to repository")
    args = parser.parse_args()

    brain = GreenyLifeBrain(args.repo)
    brain.interactive_execution()