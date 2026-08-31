"""Unit tests for the correction-verification script (stdlib only).

    python3 scripts/test_verify_correction.py
"""
import unittest

import verify_correction as vc


BODY = """### Company domain

acme.io

### Field to correct

founded

### Corrected value

2016

### Public evidence URL

https://acme.io/about

### Anything else?

_No response_
"""


class ParseTests(unittest.TestCase):
    def test_parses_issue_form_sections(self):
        d = vc.parse_issue_body(BODY)
        self.assertEqual(d["Company domain"], "acme.io")
        self.assertEqual(d["Field to correct"], "founded")
        self.assertEqual(d["Corrected value"], "2016")
        self.assertEqual(d["Public evidence URL"], "https://acme.io/about")

    def test_no_response_becomes_empty(self):
        d = vc.parse_issue_body(BODY)
        self.assertEqual(d.get("Anything else?", ""), "")


class ValidateTests(unittest.TestCase):
    def test_domain_validation(self):
        self.assertTrue(vc.valid_domain("acme.io"))
        self.assertTrue(vc.valid_domain("sub-brand.co.uk"))
        self.assertFalse(vc.valid_domain("../../etc/passwd"))
        self.assertFalse(vc.valid_domain("acme"))
        self.assertFalse(vc.valid_domain("ACME.IO/path"))

    def test_field_allowlist(self):
        self.assertTrue(vc.valid_field("founded"))
        self.assertFalse(vc.valid_field("slug"))
        self.assertFalse(vc.valid_field("trustUrl"))

    def test_evidence_must_be_https(self):
        self.assertTrue(vc.valid_evidence("https://acme.io/about"))
        self.assertFalse(vc.valid_evidence("http://acme.io/about"))
        self.assertFalse(vc.valid_evidence("file:///etc/passwd"))


class CoerceTests(unittest.TestCase):
    def test_founded_becomes_int(self):
        self.assertEqual(vc.coerce_value("founded", "2016"), 2016)

    def test_bad_founded_is_none(self):
        self.assertIsNone(vc.coerce_value("founded", "twenty16"))

    def test_frameworks_become_list(self):
        self.assertEqual(
            vc.coerce_value("frameworks", "SOC 2 Type II, ISO 27001"),
            ["SOC 2 Type II", "ISO 27001"],
        )

    def test_plain_string_fields_pass_through(self):
        self.assertEqual(vc.coerce_value("name", " Acme, Inc. "), "Acme, Inc.")


class PresenceTests(unittest.TestCase):
    PAGE = "<html><body>Acme, Inc. was founded in 2016. We hold SOC 2 Type II and ISO 27001.</body></html>"

    def test_value_present(self):
        self.assertTrue(vc.evidence_supports(self.PAGE, 2016))
        self.assertTrue(vc.evidence_supports(self.PAGE, "Acme, Inc."))

    def test_every_list_item_must_appear(self):
        self.assertTrue(vc.evidence_supports(self.PAGE, ["SOC 2 Type II", "ISO 27001"]))
        self.assertFalse(vc.evidence_supports(self.PAGE, ["SOC 2 Type II", "HITRUST"]))

    def test_case_insensitive(self):
        self.assertTrue(vc.evidence_supports(self.PAGE, "acme, inc."))

    def test_absent_value(self):
        self.assertFalse(vc.evidence_supports(self.PAGE, 1999))


class OverrideTests(unittest.TestCase):
    def test_render_override(self):
        data = vc.render_override(
            domain="acme.io", field="founded", value=2016,
            evidence="https://acme.io/about", issue=47, today="2026-08-31",
        )
        self.assertEqual(data["domain"], "acme.io")
        self.assertEqual(data["founded"], 2016)
        self.assertEqual(data["evidence"], "https://acme.io/about")
        self.assertEqual(data["method"], "evidence-presence-check")
        self.assertEqual(data["issue"], 47)
        self.assertEqual(data["verifiedAt"], "2026-08-31")


if __name__ == "__main__":
    unittest.main()
