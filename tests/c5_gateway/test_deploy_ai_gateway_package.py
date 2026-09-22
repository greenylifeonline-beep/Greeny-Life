from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "runtime" / "Deploy-RAIOS-C5.ps1"


def source() -> str:
    return DEPLOY.read_text(encoding="utf-8-sig")


def test_c5_runtime_packages_existing_ai_gateway():
    text = source()
    assert '"src/raios/ai_gateway"' in text
    assert '$PackageNames = @("c5_gateway","search_cortex","neuro_lingua","ai_gateway")' in text


def test_head_archive_contains_existing_ai_gateway():
    text = source()
    archive = next(line for line in text.splitlines() if "git -C $Repo archive" in line)
    assert "src/raios/ai_gateway" in archive


def test_ai_gateway_is_not_a_second_router_copy():
    text = source()
    assert 'Copy-Item -Path (Join-Path $SourceRoot ("src\\raios\\" + $PackageName + "\\*"))' in text
