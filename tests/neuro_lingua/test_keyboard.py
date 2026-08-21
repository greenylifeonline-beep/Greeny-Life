import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_keyboard import decode_flipped_keyboard, teach_text  # noqa: E402

FOUNDER_FLIPPED = (
    "DULG AHAM .D HGD F;GL; TDIH ]D GGK.HL UAHK HJ;GL LKIH GLH HPF UHD. "
    "OHPI HPVHTDM ,HDJO]L HGH],HJ HG[IH.M LYJ,PM HGLW]V"
)

WORKS = "\u064a\u0639\u0645\u0644"  # يعمل
SCREEN = "\u0634\u0627\u0634\u0629"  # شاشة


def test_flipped_keyboard_decodes_founder_arabic():
    rec = decode_flipped_keyboard(FOUNDER_FLIPPED)
    assert rec["flipped"] is True
    assert rec["applied"] is True
    text = rec["decoded"]
    assert WORKS in text
    assert SCREEN in text
    assert "بكلمك" in text
    assert "عشان" in text
    assert "المصدر" in text


def test_protected_seat_codes_survive():
    rec = decode_flipped_keyboard("C5 DULG")
    assert rec["decoded"].startswith("C5")
    assert WORKS in rec["decoded"]


def test_arabic_is_not_transliterated():
    rec = decode_flipped_keyboard("خذ C5 وعلمه")
    assert rec["flipped"] is False
    assert teach_text("خذ C5 وعلمه") == "خذ C5 وعلمه"


def test_english_sentence_is_not_flipped():
    rec = decode_flipped_keyboard("who are you")
    assert rec["flipped"] is False
    assert rec["decoded"] == "who are you"
