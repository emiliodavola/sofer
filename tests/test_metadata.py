"""Tests for sofer.metadata — the deterministic ``metadata.yaml`` schema.

Covers the Phase 4 (WU4) document model: the ``METADATA_VERSION`` constant
(MTA-02), the skeleton sections (MTA-01), deterministic byte-identical
serialization (MTA-03), lossless round-trip (MTA-03), the per-column contract
(MTA-06), ``missing_fields`` derivation (PRF-04), and the ``generated``
provenance (tool/version/timestamp).
"""

from __future__ import annotations

import yaml

from sofer import __version__
from sofer.metadata import (
    METADATA_VERSION,
    ColumnMetadata,
    DatasetMetadata,
    FileMetadata,
    GeneratedMetadata,
    Metadata,
    SemanticType,
    StructureMetadata,
    load,
    missing_fields,
    serialize,
)
from sofer.model import InferenceStatus
from sofer.pii import PiiDetection


def _make_email_metadata() -> Metadata:
    """Build a fully-populated email-column document for round-trip tests."""
    return Metadata(
        dataset=DatasetMetadata(
            name="contacts",
            description="Customer contact list",
            license="CC-BY-4.0",
            source="Acme Inc.",
        ),
        file=FileMetadata(path="contacts.csv", format="csv", delimiter=";"),
        structure=StructureMetadata(
            schema=[
                ColumnMetadata(
                    name="user_email",
                    storage_type="categorical/text",
                    nullable=True,
                    missing_pct=12.5,
                    unique=4,
                    example="a@b.co",
                    semantic_type=SemanticType(
                        type="email",
                        status=InferenceStatus.INFERRED,
                        confidence=0.72,
                        basis="email",
                    ),
                    pii=[PiiDetection(label="email", confidence=0.72)],
                )
            ]
        ),
    )


class TestMetadataVersionConstant:
    """METADATA_VERSION is the string "1", never an inline literal (MTA-02)."""

    def test_metadata_version_equals_one(self):
        assert METADATA_VERSION == "1"

    def test_metadata_version_is_a_string(self):
        assert isinstance(METADATA_VERSION, str)


class TestSkeletonSections:
    """Top-level sections and their required shapes (MTA-01, MTA-02)."""

    def test_skeleton_sections_present(self):
        data = yaml.safe_load(serialize(Metadata()))
        for section in (
            "dataset",
            "file",
            "structure",
            "quality",
            "documentation",
            "generated",
        ):
            assert section in data

    def test_structure_schema_is_a_list(self):
        data = yaml.safe_load(serialize(Metadata()))
        assert isinstance(data["structure"]["schema"], list)

    def test_documentation_missing_fields_is_a_list(self):
        data = yaml.safe_load(serialize(Metadata()))
        assert isinstance(data["documentation"]["missing_fields"], list)

    def test_metadata_version_field_equals_constant(self):
        data = yaml.safe_load(serialize(_make_email_metadata()))
        assert data["metadata_version"] == METADATA_VERSION
        assert data["metadata_version"] == "1"


class TestDeterministicSerialization:
    """Same input produces byte-identical YAML (MTA-03)."""

    def test_same_document_serializes_byte_identical(self):
        meta = _make_email_metadata()
        assert serialize(meta) == serialize(meta)

    def test_equal_documents_serialize_byte_identical(self):
        assert serialize(_make_email_metadata()) == serialize(_make_email_metadata())

    def test_keys_are_sorted(self):
        text = serialize(_make_email_metadata())
        # The first line of a sorted document is the alphabetically-smallest key.
        assert text.splitlines()[0].startswith("dataset:")


class TestRoundTrip:
    """serialize -> load -> serialize is lossless and idempotent (MTA-03)."""

    def test_round_trip_is_lossless(self, tmp_path):
        meta = _make_email_metadata()
        path = tmp_path / "metadata.yaml"
        path.write_text(serialize(meta), encoding="utf-8")
        assert load(path) == meta

    def test_round_trip_is_idempotent(self, tmp_path):
        meta = _make_email_metadata()
        path = tmp_path / "metadata.yaml"
        path.write_text(serialize(meta), encoding="utf-8")
        reloaded = load(path)
        assert serialize(reloaded) == serialize(meta)


class TestColumnContract:
    """Per-column schema entry carries the MTA-06 contract."""

    def test_column_entry_fully_rendered(self):
        data = yaml.safe_load(serialize(_make_email_metadata()))
        col = data["structure"]["schema"][0]
        assert col["name"] == "user_email"
        assert col["storage_type"] == "categorical/text"
        assert col["nullable"] is True
        assert col["missing_pct"] == 12.5
        assert col["unique"] == 4
        assert col["example"] == "a@b.co"
        assert col["semantic_type"] == {
            "type": "email",
            "status": "inferred",
            "confidence": 0.72,
            "basis": "email",
        }
        assert col["pii"] == [{"label": "email", "confidence": 0.72, "note": "possible_pii"}]

    def test_no_match_semantic_type_is_unknown_with_null_fields(self):
        meta = Metadata(
            structure=StructureMetadata(
                schema=[ColumnMetadata(name="city", storage_type="categorical/text")]
            )
        )
        col = yaml.safe_load(serialize(meta))["structure"]["schema"][0]
        assert col["semantic_type"]["status"] == "unknown"
        assert col["semantic_type"]["type"] is None
        assert col["semantic_type"]["confidence"] is None
        assert col["semantic_type"]["basis"] is None

    def test_no_pii_serializes_as_empty_list(self):
        meta = Metadata(
            structure=StructureMetadata(
                schema=[ColumnMetadata(name="city", storage_type="categorical/text")]
            )
        )
        col = yaml.safe_load(serialize(meta))["structure"]["schema"][0]
        assert col["pii"] == []


class TestMissingFields:
    """missing_fields surfaces the human-input gaps (PRF-04)."""

    def test_lists_description_license_source_and_column_descriptions(self):
        meta = Metadata(
            dataset=DatasetMetadata(name="d"),
            structure=StructureMetadata(
                schema=[
                    ColumnMetadata(name="user_email", storage_type="categorical/text"),
                    ColumnMetadata(name="age", storage_type="numeric", description="age in years"),
                ]
            ),
        )
        assert missing_fields(meta) == [
            "description",
            "license",
            "source",
            "user_email.description",
        ]

    def test_empty_when_all_human_input_present(self):
        meta = Metadata(
            dataset=DatasetMetadata(description="x", license="MIT", source="org"),
            structure=StructureMetadata(
                schema=[ColumnMetadata(name="age", storage_type="numeric", description="age")]
            ),
        )
        assert missing_fields(meta) == []


class TestGeneratedProvenance:
    """generated carries tool, version, and timestamp."""

    def test_generated_defaults_to_sofer_and_package_version(self):
        data = yaml.safe_load(serialize(Metadata()))
        assert data["generated"]["tool"] == "sofer"
        assert data["generated"]["version"] == __version__

    def test_generated_timestamp_round_trips(self):
        meta = Metadata(generated=GeneratedMetadata(timestamp="2026-08-17T00:00:00+00:00"))
        gen = yaml.safe_load(serialize(meta))["generated"]
        assert gen["tool"] == "sofer"
        assert gen["version"] == __version__
        assert gen["timestamp"] == "2026-08-17T00:00:00+00:00"
