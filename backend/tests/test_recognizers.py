"""Tests for custom Presidio recognizers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.processing.recognizers.legal_pii import (
    CaseNumberRecognizer,
    LegalRoleNameRecognizer,
)
from backend.processing.recognizers.government_id import (
    DriversLicenseRecognizer,
    EnhancedSSNRecognizer,
    PassportRecognizer,
)
from backend.processing.recognizers.financial_pii import (
    BankAccountRecognizer,
    RoutingNumberRecognizer,
)
from backend.processing.recognizers.medical_pii import MedicalRecordRecognizer
from backend.processing.recognizers.digital_pii import (
    DeviceIDRecognizer,
    MACAddressRecognizer,
)


def _run_pattern_recognizer(recognizer, text):
    """Helper to run a pattern recognizer and return results."""
    return recognizer.analyze(text, recognizer.supported_entities)


class TestCaseNumberRecognizer:
    """Tests for legal case number detection."""

    @pytest.fixture
    def recognizer(self):
        return CaseNumberRecognizer()

    def test_dashed_case_number(self, recognizer):
        text = "Filed under 24-CV-12345 in district court."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1
        assert any(r.entity_type == "CASE_NUMBER" for r in results)

    def test_case_no_prefix(self, recognizer):
        text = "Case No. 2024-567890 was filed on Monday."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_docket_number(self, recognizer):
        text = "Docket No. 23-456789 pending review."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_criminal_case(self, recognizer):
        text = "Regarding case 2024-CR-123456 in the matter of."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_no_false_positive_on_regular_numbers(self, recognizer):
        text = "The total was 12345 dollars."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) == 0


class TestLegalRoleNameRecognizer:
    """Tests for legal role name detection."""

    @pytest.fixture
    def recognizer(self):
        return LegalRoleNameRecognizer()

    def _make_nlp_artifacts(self, entities):
        artifacts = MagicMock()
        artifacts.entities = entities
        return artifacts

    def _make_spacy_entity(self, text, start, end, label="PERSON"):
        entity = MagicMock()
        entity.label_ = label
        entity.start_char = start
        entity.end_char = end
        entity.text = text
        return entity

    def test_judge_name(self, recognizer):
        text = "The Honorable Judge John Smith presided over the case."
        entity = self._make_spacy_entity("John Smith", 25, 35)
        artifacts = self._make_nlp_artifacts([entity])

        results = recognizer.analyze(text, ["LEGAL_ROLE_NAME"], nlp_artifacts=artifacts)
        assert len(results) == 1
        assert results[0].entity_type == "LEGAL_ROLE_NAME"

    def test_attorney_name(self, recognizer):
        text = "Attorney Sarah Johnson filed the motion."
        entity = self._make_spacy_entity("Sarah Johnson", 9, 22)
        artifacts = self._make_nlp_artifacts([entity])

        results = recognizer.analyze(text, ["LEGAL_ROLE_NAME"], nlp_artifacts=artifacts)
        assert len(results) == 1

    def test_victim_name(self, recognizer):
        text = "The victim Jane Doe reported the incident."
        entity = self._make_spacy_entity("Jane Doe", 11, 19)
        artifacts = self._make_nlp_artifacts([entity])

        results = recognizer.analyze(text, ["LEGAL_ROLE_NAME"], nlp_artifacts=artifacts)
        assert len(results) == 1

    def test_no_keyword_no_match(self, recognizer):
        text = "John Smith went to the store."
        entity = self._make_spacy_entity("John Smith", 0, 10)
        artifacts = self._make_nlp_artifacts([entity])

        results = recognizer.analyze(text, ["LEGAL_ROLE_NAME"], nlp_artifacts=artifacts)
        assert len(results) == 0

    def test_no_nlp_artifacts(self, recognizer):
        text = "Judge John Smith presided."
        results = recognizer.analyze(text, ["LEGAL_ROLE_NAME"], nlp_artifacts=None)
        assert results == []

    def test_non_person_entity_ignored(self, recognizer):
        text = "Judge Apple Inc ruled on the matter."
        entity = self._make_spacy_entity("Apple Inc", 6, 15, label="ORG")
        artifacts = self._make_nlp_artifacts([entity])

        results = recognizer.analyze(text, ["LEGAL_ROLE_NAME"], nlp_artifacts=artifacts)
        assert len(results) == 0


class TestEnhancedSSNRecognizer:
    """Tests for SSN pattern detection."""

    @pytest.fixture
    def recognizer(self):
        return EnhancedSSNRecognizer()

    def test_full_ssn_with_dashes(self, recognizer):
        text = "His SSN is 123-45-6789."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_ssn_no_dashes_with_keyword(self, recognizer):
        text = "SSN: 123456789 on file."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_ssn_last4(self, recognizer):
        text = "SSN ending in 6789 was verified."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_invalid_ssn_000_prefix(self, recognizer):
        text = "Number 000-12-3456 is not valid."
        results = _run_pattern_recognizer(recognizer, text)
        # Should not match (000 prefix is invalid)
        ssn_results = [r for r in results if r.score > 0.7]
        assert len(ssn_results) == 0


class TestDriversLicenseRecognizer:
    """Tests for driver's license pattern detection."""

    @pytest.fixture
    def recognizer(self):
        return DriversLicenseRecognizer()

    def test_letter_digits_format(self, recognizer):
        text = "Driver's license: A1234567 issued in CA."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_dl_abbreviation(self, recognizer):
        text = "DL# B9876543 on record."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1


class TestPassportRecognizer:
    """Tests for passport number detection."""

    @pytest.fixture
    def recognizer(self):
        return PassportRecognizer()

    def test_passport_number(self, recognizer):
        text = "Passport 123456789 was presented at the border."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_passport_number_prefix(self, recognizer):
        text = "Passport number: 987654321 is expired."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1


class TestRoutingNumberRecognizer:
    """Tests for ABA routing number detection."""

    @pytest.fixture
    def recognizer(self):
        return RoutingNumberRecognizer()

    def test_valid_routing_number_with_keyword(self, recognizer):
        # 021000021 is a known valid ABA routing number (JPMorgan Chase)
        text = "Bank routing number: 021000021 for wire transfer."
        results = recognizer.analyze(text, ["ROUTING_NUMBER"])
        assert len(results) >= 1
        assert results[0].score >= 0.8

    def test_valid_routing_without_keyword(self, recognizer):
        text = "Please use 021000021 for the deposit."
        results = recognizer.analyze(text, ["ROUTING_NUMBER"])
        # Should still match but with lower confidence
        matching = [r for r in results if r.entity_type == "ROUTING_NUMBER"]
        assert len(matching) >= 1
        assert matching[0].score < 0.8

    def test_invalid_check_digit(self, recognizer):
        text = "Routing: 123456789 is not valid."
        results = recognizer.analyze(text, ["ROUTING_NUMBER"])
        assert len(results) == 0  # Fails ABA check


class TestBankAccountRecognizer:
    """Tests for bank account number detection."""

    @pytest.fixture
    def recognizer(self):
        return BankAccountRecognizer()

    def test_account_number(self, recognizer):
        text = "Account# 12345678901 for direct deposit."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_bank_account_keyword(self, recognizer):
        text = "Bank account 9876543210 is active."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1


class TestMedicalRecordRecognizer:
    """Tests for medical record number detection."""

    @pytest.fixture
    def recognizer(self):
        return MedicalRecordRecognizer()

    def test_mrn_keyword(self, recognizer):
        text = "MRN: 12345678 on patient chart."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_medical_record_no(self, recognizer):
        text = "Medical record number 98765432 filed."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_patient_id(self, recognizer):
        text = "Patient ID: 11223344 assigned."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1


class TestMACAddressRecognizer:
    """Tests for MAC address detection."""

    @pytest.fixture
    def recognizer(self):
        return MACAddressRecognizer()

    def test_colon_format(self, recognizer):
        text = "Device MAC: AA:BB:CC:DD:EE:FF was logged."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_dash_format(self, recognizer):
        text = "MAC address 11-22-33-44-55-66 on record."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_no_false_positive(self, recognizer):
        text = "The total was 1234 and the count was 5678."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) == 0


class TestDeviceIDRecognizer:
    """Tests for device ID detection."""

    @pytest.fixture
    def recognizer(self):
        return DeviceIDRecognizer()

    def test_imei(self, recognizer):
        text = "IMEI: 123456789012345 for the phone."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_serial_number(self, recognizer):
        text = "Serial number: ABC123DEF456 on the device."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1

    def test_device_id_keyword(self, recognizer):
        text = "Device ID: A1B2C3D4E5F6 was registered."
        results = _run_pattern_recognizer(recognizer, text)
        assert len(results) >= 1
