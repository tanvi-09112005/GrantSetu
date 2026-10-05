"""Pure-logic tests for Darpan verification (no PDFs, no network)."""

import sys
import types

import pytest

from app.services import darpan_verify as dv

CRY_TEXT = "Certificate of Enrolment To CHILD RIGHTS AND YOU (CRY) is enrolled ... Unique Id: DL/2009/0014766"


def _stub_vision(monkeypatch, result):
    mod = types.ModuleType("app.services.vision")
    mod.read_darpan_certificate = lambda _b: result
    monkeypatch.setitem(sys.modules, "app.services.vision", mod)


def test_regex_finds_ids_with_markup_and_spaces():
    assert dv.find_darpan_ids("Unique ID <b>RJ/2011/0234567</b>") == ["RJ/2011/0234567"]
    assert dv.find_darpan_ids("dl / 2009 / 0014766") == ["DL/2009/0014766"]
    assert dv.find_darpan_ids("No.DEL/CIT(E)/12A(a)/516/2013-14") == []


def test_match(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: CRY_TEXT)
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0014766", "Child Rights and You (CRY)")
    assert r.ok and r.method == "text"


def test_wrong_id_is_rejected(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: CRY_TEXT)
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0099999", "Child Rights and You (CRY)")
    assert not r.ok and r.reason == "id_mismatch" and r.found_id == "DL/2009/0014766"


def test_wrong_name_is_rejected(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: CRY_TEXT)
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0014766", "Some Other Trust")
    assert not r.ok and r.reason == "name_mismatch"


def test_wrong_document_has_no_id(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: "REGISTRATION UNDER SECTION 12AA ... AAATC1234A")
    _stub_vision(monkeypatch, None)
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0014766", "CRY")
    assert not r.ok and r.reason == "no_id_found"


def test_scanned_pdf_uses_vision(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: "")
    _stub_vision(monkeypatch, {"is_darpan_certificate": True, "darpan_id": "DL/2009/0014766",
                               "entity_name": "CHILD RIGHTS AND YOU (CRY)"})
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0014766", "Child Rights and You (CRY)")
    assert r.ok and r.method == "vision"


def test_blank_and_vision_down_is_unreadable(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: "")
    _stub_vision(monkeypatch, None)
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0014766", "CRY")
    assert not r.ok and r.reason == "unreadable"


def test_vision_says_not_a_darpan_certificate(monkeypatch):
    monkeypatch.setattr(dv, "_text_layer", lambda _b: "")
    _stub_vision(monkeypatch, {"is_darpan_certificate": False, "darpan_id": "DL/2009/0014766", "entity_name": None})
    r = dv.verify_darpan_certificate(b"x", "DL/2009/0014766", "CRY")
    assert not r.ok and r.reason == "no_id_found"
