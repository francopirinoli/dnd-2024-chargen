"""Regression tests: game-content selections must not escape data/ directories.

Player-supplied class / species / lineage / background / subclass identifiers
address JSON files on disk. They must resolve to a canonical content id inside
the expected content directory, and anything else must be rejected without
touching the filesystem.
"""

import pytest

from modules.character_builder import CharacterBuilder, content_slug


TRAVERSAL_IDENTIFIERS = [
    "../general_feats",              # real JSON one level up from a content dir
    "../../app",                     # outside data/ entirely
    "../../../../etc/passwd",
    "/etc/passwd",                   # absolute path
    "..%2f..%2fgeneral_feats",       # encoded traversal
    "..\\..\\general_feats",         # windows-style traversal
    "fighter/../../general_feats",
    "sub/dir/fighter",               # nested path
    "fighter\x00.json",              # NUL byte
    "",
    "   ",
]


class TestContentSlug:
    def test_canonical_names_slugify(self):
        assert content_slug("Fighter") == "fighter"
        assert content_slug("Wood Elf") == "wood_elf"
        assert content_slug(" Half-Elf ") == "half-elf"

    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS)
    def test_malformed_identifiers_rejected(self, identifier):
        assert content_slug(identifier) is None

    @pytest.mark.parametrize("identifier", [None, 3, ["fighter"], {"name": "fighter"}])
    def test_non_string_identifiers_rejected(self, identifier):
        assert content_slug(identifier) is None


class TestBuilderContentLoading:
    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS)
    def test_species_traversal_loads_nothing(self, identifier):
        builder = CharacterBuilder()
        assert builder._load_species_data(identifier) is None
        assert builder.set_species(identifier) is False
        assert builder.character_data["species"] is None

    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS)
    def test_class_traversal_loads_nothing(self, identifier):
        builder = CharacterBuilder()
        assert builder._load_class_data(identifier) is None
        assert builder.set_class(identifier) is False
        assert builder.character_data["class"] is None

    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS)
    def test_background_traversal_loads_nothing(self, identifier):
        builder = CharacterBuilder()
        assert builder._load_background_data(identifier) is None
        assert builder.set_background(identifier) is False
        assert builder.character_data["background"] is None

    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS)
    def test_lineage_traversal_loads_nothing(self, identifier):
        builder = CharacterBuilder()
        assert builder.set_species("Elf") is True
        assert builder._load_lineage_data("Elf", identifier) is None
        assert builder.set_lineage(identifier) is False
        assert builder.character_data["lineage"] is None

    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS)
    def test_subclass_traversal_loads_nothing(self, identifier):
        builder = CharacterBuilder()
        assert builder._load_subclass_data("Fighter", identifier) is None
        assert builder._load_subclass_data(identifier, "Champion") is None

    def test_spell_definition_traversal_returns_placeholder(self):
        builder = CharacterBuilder()
        definition = builder._load_spell_definition("../../general_feats")
        assert definition["description"] == "Spell definition not available."

    def test_canonical_content_still_loads(self):
        builder = CharacterBuilder()
        assert builder._load_species_data("Elf")["name"] == "Elf"
        assert builder._load_class_data("Fighter")["name"] == "Fighter"
        assert builder._load_background_data("Sage")["name"] == "Sage"
        assert builder._load_lineage_data("Elf", "Wood Elf")["name"] == "Wood Elf"
        assert builder._load_subclass_data("Fighter", "Champion") is not None


class TestContentSelectionExists:
    def test_known_identifiers(self):
        builder = CharacterBuilder()
        assert builder.content_selection_exists("species", "Elf")
        assert builder.content_selection_exists("class", "Fighter")
        assert builder.content_selection_exists("background", "Sage")
        assert builder.content_selection_exists("lineage", "Wood Elf")

    @pytest.mark.parametrize("identifier", TRAVERSAL_IDENTIFIERS + ["NotARealClass"])
    def test_unknown_or_malformed_identifiers(self, identifier):
        builder = CharacterBuilder()
        assert builder.content_selection_exists("class", identifier) is False

    def test_unknown_kind_raises(self):
        builder = CharacterBuilder()
        with pytest.raises(ValueError):
            builder.content_selection_exists("weapons", "Longsword")


class TestBuildApiRejectsTraversal:
    """The API must answer with a sanitized 400 — never a 500 or file content."""

    BASE_CHOICES = {
        "species": "Elf",
        "class": "Fighter",
        "background": "Sage",
        "level": 1,
    }

    def _post(self, client, overrides):
        choices = dict(self.BASE_CHOICES)
        choices.update(overrides)
        return client.post("/api/v1/character/build", json={"choices_made": choices})

    @staticmethod
    def _assert_sanitized_rejection(response, identifier, field):
        """A rejection is a 400 that names the field but never echoes the value."""
        assert response.status_code == 400
        body = response.get_json()
        assert body["error"]["field"] == field
        assert identifier not in response.get_data(as_text=True)

    def test_valid_build_still_succeeds(self, client):
        r = self._post(client, {})
        assert r.status_code == 200
        assert r.get_json()["character"]["species"] == "Elf"

    # A bare `class` selection is normalized into `classes[0]` before the
    # identifier is resolved, so that is the field reported back.
    @pytest.mark.parametrize(
        "key,field",
        [
            ("species", "choices_made.species"),
            ("class", "choices_made.classes[0].class_name"),
            ("background", "choices_made.background"),
        ],
    )
    @pytest.mark.parametrize(
        "identifier",
        ["../general_feats", "/etc/passwd", "..%2f..%2fapp", "NotRealContent"],
    )
    def test_traversal_and_unknown_identifiers_rejected(self, client, key, field, identifier):
        r = self._post(client, {key: identifier})
        self._assert_sanitized_rejection(r, identifier, field)

    def test_lineage_traversal_rejected(self, client):
        identifier = "../../general_feats"
        r = self._post(client, {"lineage": identifier})
        self._assert_sanitized_rejection(r, identifier, "choices_made.lineage")

    def test_subclass_traversal_rejected(self, client):
        identifier = "../../general_feats"
        r = self._post(client, {"level": 3, "subclass": identifier})
        self._assert_sanitized_rejection(r, identifier, "choices_made.classes[0].subclass")

    def test_traversal_in_classes_payload_rejected(self, client):
        identifier = "../../general_feats"
        r = client.post(
            "/api/v1/character/build",
            json={
                "choices_made": {
                    "species": "Elf",
                    "background": "Sage",
                    "classes": [{"class_name": identifier, "level": 1}],
                }
            },
        )
        self._assert_sanitized_rejection(
            r, identifier, "choices_made.classes[0].class_name"
        )

    def test_validate_endpoint_rejects_traversal(self, client):
        identifier = "../../general_feats"
        r = client.post(
            "/api/v1/character/validate",
            json={"choices_made": {"species": identifier}},
        )
        self._assert_sanitized_rejection(r, identifier, "choices_made.species")

    def test_preview_step_endpoint_rejects_traversal(self, client):
        identifier = "../../general_feats"
        r = client.post(
            "/api/v1/character/preview-step",
            json={"choices_made": {"species": identifier}, "step": "species"},
        )
        self._assert_sanitized_rejection(r, identifier, "choices_made.species")

    def test_derived_endpoint_rejects_traversal(self, client):
        identifier = "../../general_feats"
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": {"class": identifier}, "view": "spell_management"},
        )
        self._assert_sanitized_rejection(
            r, identifier, "choices_made.classes[0].class_name"
        )
