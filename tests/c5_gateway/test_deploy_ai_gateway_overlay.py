from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEPLOY=ROOT/"scripts"/"runtime"/"Deploy-RAIOS-C5.ps1"

def source():
    return DEPLOY.read_text(encoding="utf-8-sig")

def test_overlay_allowlist_supports_only_c5_and_ai_gateway():
    text=source()
    assert '@("src/raios/c5_gateway/","src/raios/ai_gateway/")' in text
    assert 'C5_LEASED_OVERLAY_INVALID' in text

def test_overlay_target_is_derived_from_allowed_package():
    text=source()
    assert '$overlayPackage' in text
    assert '$overlaySuffix' in text
    assert 'Join-Path $StageAppRoot ("raios\\" + $overlayPackage)' in text
