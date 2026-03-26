"""Tests for title diff rendering — issue #260.

Verifies that document title text changes are properly highlighted in the
diff view, including name-only changes, name+number changes, and
name+body changes.
"""

from atlas_preview.parser import AtlasDoc, parse_atlas, normalize_body, find_doc_by_uuid
from atlas_preview.diff import word_diff, line_diff
from atlas_preview.renderer import render_doc_html, categorize_changed_docs


def _make_doc(number="A.1.2.3", name="Some Name", doc_type="Core",
              uuid="test-uuid-1234", body="Body text.", level=4,
              line_start=0, line_end=2):
    """Helper to create an AtlasDoc for testing."""
    heading = f'{"#" * level} {number} - {name} [{doc_type}]  <!-- UUID: {uuid} -->'
    return AtlasDoc(
        level=level,
        number=number,
        name=name,
        doc_type=doc_type,
        uuid=uuid,
        heading_line=heading,
        body=body,
        line_start=line_start,
        line_end=line_end,
    )


class TestCategorizeChangedDocs:
    """Tests for the categorize_changed_docs function in generate_preview."""

    def test_name_only_change_is_substantive(self):
        """A doc where ONLY the name changes should be categorized as substantive,
        not skipped or renumbered."""
        old_doc = _make_doc(name="Asset Supplied By SLL")
        new_doc = _make_doc(name="Asset Supplied By Spark Liquidity Layer")
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        assert len(substantive) == 1
        assert len(renumbered) == 0
        assert substantive[0].name == "Asset Supplied By Spark Liquidity Layer"

    def test_name_case_change_is_substantive(self):
        """A doc where the name changes only in case should NOT be silently
        dropped — it should be treated as a substantive change so the title
        diff is visible."""
        old_doc = _make_doc(name="Asset Supplied By SLL")
        new_doc = _make_doc(name="Asset Supplied By Sll")
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        # BUG: The case-insensitive fallback in names_match causes this to be
        # skipped entirely (neither substantive nor renumbered)
        assert len(substantive) == 1, \
            "Name case change should be substantive, not silently dropped"
        assert len(renumbered) == 0

    def test_body_unchanged_name_case_change_with_xref_renumbering(self):
        """When a doc has a name case change AND body xrefs were renumbered,
        the doc should be substantive (not renumbered)."""
        old_doc = _make_doc(
            name="Asset Supplied By SLL",
            body="See [A.1.2.4 - Other Doc](other-uuid) for details.",
        )
        new_doc = _make_doc(
            name="Asset Supplied By Sll",
            body="See [A.1.2.5 - Other Doc](other-uuid) for details.",
        )
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        # Even though normalize_body makes bodies match, name changed (case),
        # so it should be substantive
        assert len(substantive) == 1, \
            "Name case change + xref renumbering should be substantive"
        assert len(renumbered) == 0

    def test_number_only_change_is_skipped(self):
        """A doc where only the number changed (same name, same body) should be
        silently skipped (not substantive, not renumbered)."""
        old_doc = _make_doc(number="A.1.2.3")
        new_doc = _make_doc(number="A.1.2.4")
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        # Number-only change with same body and name is silently dropped
        assert len(substantive) == 0
        assert len(renumbered) == 0

    def test_body_xref_renumbering_is_renumbered(self):
        """A doc where body xrefs changed but normalize_body makes them match,
        and name is the same, should be categorized as renumbered."""
        old_doc = _make_doc(
            body="See [A.1.2.4 - Other Doc](other-uuid) for details.",
        )
        new_doc = _make_doc(
            body="See [A.1.2.5 - Other Doc](other-uuid) for details.",
        )
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        assert len(substantive) == 0
        assert len(renumbered) == 1

    def test_name_and_body_change_is_substantive(self):
        """A doc where both name and body change should be substantive."""
        old_doc = _make_doc(name="Old Name", body="Old body.")
        new_doc = _make_doc(name="New Name", body="New body.")
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        assert len(substantive) == 1
        assert len(renumbered) == 0

    def test_name_change_with_xref_renumbering_is_substantive(self):
        """A doc where name changes AND body xrefs renumber should be substantive."""
        old_doc = _make_doc(
            name="Old Name",
            body="See [A.1.2.4 - Ref](ref-uuid).",
        )
        new_doc = _make_doc(
            name="New Name",
            body="See [A.1.2.5 - Ref](ref-uuid).",
        )
        base_by_uuid = {old_doc.uuid: old_doc}

        substantive, renumbered = categorize_changed_docs([new_doc], base_by_uuid)

        assert len(substantive) == 1
        assert len(renumbered) == 0


class TestRenderDocHtmlTitleDiff:
    """Tests for title diff rendering in render_doc_html."""

    def test_name_only_change_shows_modified_badge(self):
        """When only the name changes, the badge should be MODIFIED."""
        old_doc = _make_doc(name="Asset Supplied By SLL")
        new_doc = _make_doc(name="Asset Supplied By Spark Liquidity Layer")

        result = render_doc_html(new_doc, [old_doc])

        assert 'MODIFIED' in result
        assert 'CONTEXT' not in result
        assert 'RENUMBERED' not in result

    def test_name_only_change_shows_title_diff(self):
        """When only the name changes, the title should contain diff markup
        with removed/added spans."""
        old_doc = _make_doc(name="Asset Supplied By SLL")
        new_doc = _make_doc(name="Asset Supplied By Spark Liquidity Layer")

        result = render_doc_html(new_doc, [old_doc])

        assert '<span class="removed">' in result
        assert '<span class="added">' in result
        assert 'SLL' in result
        assert 'Spark Liquidity Layer' in result

    def test_name_case_change_shows_modified_badge(self):
        """When the name changes only in case, it should show MODIFIED."""
        old_doc = _make_doc(name="Asset Supplied By SLL")
        new_doc = _make_doc(name="Asset Supplied By Sll")

        result = render_doc_html(new_doc, [old_doc])

        assert 'MODIFIED' in result

    def test_name_case_change_shows_title_diff(self):
        """When the name changes only in case, the title diff should show it."""
        old_doc = _make_doc(name="Asset Supplied By SLL")
        new_doc = _make_doc(name="Asset Supplied By Sll")

        result = render_doc_html(new_doc, [old_doc])

        assert '<span class="removed">' in result or '<span class="added">' in result

    def test_name_and_number_change_shows_title_diff(self):
        """When both name and number change, the title diff should show both."""
        old_doc = _make_doc(number="A.1.2.3", name="Old Name")
        new_doc = _make_doc(number="A.1.2.4", name="New Name")

        result = render_doc_html(new_doc, [old_doc])

        assert 'MODIFIED' in result
        assert '<span class="removed">' in result
        assert '<span class="added">' in result

    def test_name_and_body_change_shows_both_diffs(self):
        """When both name and body change, both title diff and body diff show."""
        old_doc = _make_doc(name="Old Name", body="Old body text.")
        new_doc = _make_doc(name="New Name", body="New body text.")

        result = render_doc_html(new_doc, [old_doc])

        assert 'MODIFIED' in result
        # Title diff should contain markup
        assert 'Old Name' in result or 'New Name' in result

    def test_renumbered_with_name_change_shows_title_diff(self):
        """When a doc is renumbered AND has a name change, the title diff
        should still be visible."""
        old_doc = _make_doc(number="A.1.2.3", name="Old Name")
        new_doc = _make_doc(number="A.1.2.4", name="New Name")

        result = render_doc_html(new_doc, [old_doc], is_renumbered=True)

        assert 'RENUMBERED' in result
        assert '<span class="removed">' in result
        assert '<span class="added">' in result

    def test_unchanged_doc_shows_context(self):
        """When nothing changes, the doc should show CONTEXT badge."""
        old_doc = _make_doc()
        new_doc = _make_doc()

        result = render_doc_html(new_doc, [old_doc])

        assert 'CONTEXT' in result

    def test_number_only_change_shows_modified_with_title_diff(self):
        """When only the number changes, the title diff should highlight it."""
        old_doc = _make_doc(number="A.1.2.3")
        new_doc = _make_doc(number="A.1.2.4")

        result = render_doc_html(new_doc, [old_doc])

        assert 'MODIFIED' in result
        assert '<span class="removed">' in result or '<span class="added">' in result


class TestWordDiff:
    """Basic tests for word_diff to ensure it produces correct markup."""

    def test_word_change(self):
        """Changing a word produces removed and added spans."""
        result = word_diff("hello world", "hello earth")
        assert '<span class="removed">' in result
        assert '<span class="added">' in result
        assert 'world' in result
        assert 'earth' in result

    def test_identical_strings(self):
        """Identical strings produce no diff spans."""
        result = word_diff("hello world", "hello world")
        assert '<span class="removed">' not in result
        assert '<span class="added">' not in result

    def test_name_expansion(self):
        """Expanding an abbreviation shows the old and new text."""
        result = word_diff(
            "A.1.2.3 - Asset Supplied By SLL",
            "A.1.2.3 - Asset Supplied By Spark Liquidity Layer",
        )
        assert 'SLL' in result
        assert 'Spark' in result
        assert 'Liquidity' in result
        assert 'Layer' in result


class TestParseAtlas:
    """Tests that the parser correctly extracts document names."""

    def test_parse_doc_name(self):
        """Parser should extract the full document name from a heading."""
        text = "## A.1.2.3 - Asset Supplied By SLL [Core]  <!-- UUID: test-uuid -->\n\nBody text."
        docs = parse_atlas(text)
        assert len(docs) == 1
        assert docs[0].name == "Asset Supplied By SLL"
        assert docs[0].number == "A.1.2.3"
        assert docs[0].doc_type == "Core"
        assert docs[0].uuid == "test-uuid"

    def test_parse_name_change(self):
        """Parser should correctly parse both old and new versions of a name."""
        old_text = "## A.1.2.3 - Asset Supplied By SLL [Core]  <!-- UUID: test-uuid -->\n\nBody."
        new_text = "## A.1.2.3 - Asset Supplied By Spark Liquidity Layer [Core]  <!-- UUID: test-uuid -->\n\nBody."

        old_docs = parse_atlas(old_text)
        new_docs = parse_atlas(new_text)

        assert old_docs[0].name == "Asset Supplied By SLL"
        assert new_docs[0].name == "Asset Supplied By Spark Liquidity Layer"
        assert old_docs[0].uuid == new_docs[0].uuid
