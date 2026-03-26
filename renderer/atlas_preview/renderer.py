"""HTML rendering — doc rendering, research notes, preview generation."""

import hashlib
import html
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from atlas_preview.parser import (
    AtlasDoc, parse_atlas, normalize_body, find_doc_by_uuid,
    find_doc_by_number, find_ancestor_docs, build_hierarchy,
)
from atlas_preview.diff import (
    word_diff, line_diff, get_file_at_ref, get_changed_ranges,
    find_changed_docs,
)

ATLAS_PATH = "Sky Atlas/Sky Atlas.md"

_TEMPLATES_DIR = Path(__file__).parent / 'templates'


def _load_template(name: str) -> str:
    """Load a template file from the templates directory."""
    return (_TEMPLATES_DIR / name).read_text(encoding='utf-8')


def _apply_inline_formatting(text: str) -> str:
    """Apply markdown inline formatting to text that has already been HTML-escaped.

    Converts **bold**, *italic*, ~~strikethrough~~, `code`, __underline__,
    and [link](url) syntax to their HTML equivalents.

    This operates on plain text segments only — the caller must ensure it is
    not called on raw HTML that contains tags (use _apply_inline_formatting_to_html
    for diff output that contains <span> tags).
    """
    # Render inline code first (protect contents from other formatting)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Render bold (must come before italic since ** contains *)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Render underline (__text__) — must come before italic-like patterns
    text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)
    # Render italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Render strikethrough
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    # Render links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def _apply_inline_formatting_to_html(diff_html: str) -> str:
    """Apply markdown inline formatting to diff HTML without breaking diff markup.

    The diff output contains <span class="added/removed">...</span> and
    <div class="line ...">...</div> tags. We must only apply inline formatting
    to the text content between/within these tags, not to the tags themselves.

    Strategy: split the HTML into tag vs text segments, apply formatting only
    to text segments, then rejoin.
    """
    # Split into HTML tags and text segments
    parts = re.split(r'(<[^>]+>)', diff_html)
    result = []
    for part in parts:
        if part.startswith('<'):
            # HTML tag — pass through unchanged
            result.append(part)
        else:
            # Text content — apply inline formatting
            result.append(_apply_inline_formatting(part))
    return ''.join(result)


def render_clean_body(doc: AtlasDoc) -> str:
    """Render doc body as clean text (no diff markup), with basic markdown rendering."""
    body = html.escape(doc.body)
    body = _apply_inline_formatting(body)
    return f'<div class="line context">{body}</div>'


def _inject_line_numbers(diff_body: str, doc: AtlasDoc) -> str:
    """Post-process diff HTML to add data-line attributes for inline commenting.

    For lines that exist in the new version of the file (context, added, changed),
    we compute the 1-indexed file line number from the doc's body position.
    Removed-only lines get no data-line (they don't exist in the new file).
    """
    # Body text starts at line_start + 1 in the file (line_start is the heading)
    # The body lines in the new file are line_start+1, line_start+2, ...
    # But diff output interleaves removed lines (which don't count in the new file).
    new_line_num = doc.line_start + 1  # 0-indexed in parser, but we want 1-indexed for GitHub API
    # parser uses 0-indexed line_start, so file line 1 = index 0
    # GitHub API uses 1-indexed, so we need line_start + 1 + 1 for the first body line
    # Actually: line_start is 0-indexed. First body line in file = line_start + 1 (0-indexed) = line_start + 2 (1-indexed)
    new_line_num = doc.line_start + 2  # 1-indexed line number of first body line

    def replace_line_div(match):
        nonlocal new_line_num
        classes = match.group(1)
        rest = match.group(2)
        if 'removed-line' in classes:
            # Removed lines don't exist in new file — no data-line
            return match.group(0)
        else:
            # context, added-line, changed-line — all exist in new file
            line_attr = f' data-line="{new_line_num}"'
            new_line_num += 1
            return f'<div class="line {classes}"{line_attr}>{rest}</div>'

    # Match <div class="line ...">...</div> — non-greedy
    return re.sub(
        r'<div class="line ([^"]*)">(.*?)</div>',
        replace_line_div,
        diff_body,
    )


# Set by generate_preview() before rendering — used by render_doc_html for child detection
_renumbered_uuids: set[str] = set()
_deleted_uuids: set[str] = set()


def render_doc_html(doc: AtlasDoc, old_docs: list[AtlasDoc], is_new: bool = False,
                    is_renumbered: bool = False, is_deleted: bool = False) -> str:
    """Render a single doc as HTML with both diff and clean views."""
    # Handle deleted docs — show everything as removed
    if is_deleted:
        change_badge = '<span class="badge deleted">DELETED</span>'
        diff_body = f'<div class="line removed-line"><span class="removed">{html.escape(doc.body)}</span></div>'
        diff_body = _apply_inline_formatting_to_html(diff_body)
        title_html = html.escape(f'{doc.number} - {doc.name}' if doc.number else doc.name)
        diff_title = f'<span class="removed">{title_html}</span>'
        type_badge = f'<span class="type-badge">{html.escape(doc.doc_type)}</span>' if doc.doc_type else ''
        uuid_display = f'<span class="uuid">{doc.uuid}</span>' if doc.uuid else ''
        section_class = f'doc-section level-{doc.level} deleted-doc'

        # Render deleted children
        children_html = ""
        if doc.children:
            child_parts = []
            for child in doc.children:
                child_parts.append(render_doc_html(child, old_docs, is_deleted=True))
            children_html = '\n'.join(child_parts)

        if children_html:
            toggle = f'<span class="toggle-arrow" data-doc="{doc.number}" onclick="event.stopPropagation(); const ct = this.closest(\'.doc-section\').querySelector(\'.children\'); const open = ct.style.display !== \'none\'; ct.style.display = open ? \'none\' : \'block\'; this.textContent = open ? \'\\u25B6\' : \'\\u25BC\';">&#9660;</span>'
            return f'''
    <div class="{section_class}">
        <div class="doc-header">
            {toggle}
            <span class="markup-only">{change_badge}</span> {type_badge}
            <span class="doc-title markup-only">{diff_title}</span>
            <span class="doc-title clean-only">{diff_title}</span>
            {uuid_display}
        </div>
        <div class="doc-body markup-only">
            {diff_body}
        </div>
        <div class="doc-body clean-only">
            {diff_body}
        </div>
        <div class="children">{children_html}</div>
    </div>
    '''
        else:
            return f'''
    <div class="{section_class}">
        <div class="doc-header">
            <span class="markup-only">{change_badge}</span> {type_badge}
            <span class="doc-title markup-only">{diff_title}</span>
            <span class="doc-title clean-only">{diff_title}</span>
            {uuid_display}
        </div>
        <div class="doc-body markup-only">
            {diff_body}
        </div>
        <div class="doc-body clean-only">
            {diff_body}
        </div>
    </div>
    '''

    # Find the old version
    old_doc = None
    if not is_new and doc.uuid:
        old_doc = find_doc_by_uuid(old_docs, doc.uuid)
    if not is_new and not old_doc and doc.number:
        # Try by number (for renumbered docs, UUID match is better)
        pass

    # Determine change type
    if is_new or not old_doc:
        change_badge = '<span class="badge new">NEW</span>'
        diff_body = f'<div class="line added-line"><span class="added">{html.escape(doc.body)}</span></div>'
        title_changed = True
    elif is_renumbered:
        change_badge = '<span class="badge renumbered">RENUMBERED</span>'
        diff_body = line_diff(old_doc.body, doc.body)
        title_changed = (old_doc.name != doc.name or old_doc.number != doc.number)
    elif old_doc.body == doc.body and old_doc.name == doc.name and old_doc.number == doc.number:
        change_badge = '<span class="badge context">CONTEXT</span>'
        diff_body = f'<div class="line context">{html.escape(doc.body)}</div>'
        title_changed = False
    else:
        change_badge = '<span class="badge modified">MODIFIED</span>'
        diff_body = line_diff(old_doc.body, doc.body)
        title_changed = (old_doc.name != doc.name or old_doc.number != doc.number)

    # Inject line number attributes for inline commenting
    diff_body = _inject_line_numbers(diff_body, doc)

    # Apply inline markdown formatting to diff body (after diffing to avoid breaking diff algorithm)
    diff_body = _apply_inline_formatting_to_html(diff_body)

    # Clean body (always uses current version)
    clean_body = render_clean_body(doc)

    # Title — markup version
    type_badge = f'<span class="type-badge">{html.escape(doc.doc_type)}</span>' if doc.doc_type else ''

    if title_changed and old_doc:
        old_title = f'{old_doc.number} - {old_doc.name}' if old_doc.number else old_doc.name
        new_title = f'{doc.number} - {doc.name}' if doc.number else doc.name
        diff_title = word_diff(old_title, new_title)
    else:
        diff_title = html.escape(f'{doc.number} - {doc.name}' if doc.number else doc.name)

    # Title — clean version (always current)
    clean_title = html.escape(f'{doc.number} - {doc.name}' if doc.number else doc.name)

    # Build children HTML
    children_html = ""
    if doc.children:
        child_parts = []
        for child in doc.children:
            child_is_deleted = child.uuid in _deleted_uuids if child.uuid else False
            child_is_new = not find_doc_by_uuid(old_docs, child.uuid) if child.uuid and not child_is_deleted else False
            child_is_renum = child.uuid in _renumbered_uuids if child.uuid else False
            child_parts.append(render_doc_html(child, old_docs, is_new=child_is_new, is_renumbered=child_is_renum, is_deleted=child_is_deleted))
        children_html = '\n'.join(child_parts)

    uuid_display = f'<span class="uuid">{doc.uuid}</span>' if doc.uuid else ''
    copy_btn = f'<button class="copy-btn" onclick="event.stopPropagation(); navigator.clipboard.writeText(\'{doc.number}\').then(() => {{ this.textContent = \'\\u2713\'; setTimeout(() => this.textContent = \'\\u2398\', 800); }})" title="Copy {doc.number}">&#9112;</button>' if doc.number else ''
    section_class = f'doc-section level-{doc.level}'
    if is_renumbered:
        section_class += ' renumbered-doc'

    if children_html:
        toggle = f'<span class="toggle-arrow" data-doc="{doc.number}" onclick="event.stopPropagation(); const ct = this.closest(\'.doc-section\').querySelector(\'.children\'); const open = ct.style.display !== \'none\'; ct.style.display = open ? \'none\' : \'block\'; this.textContent = open ? \'\\u25B6\' : \'\\u25BC\';">&#9660;</span>'
        return f'''
    <div class="{section_class}">
        <div class="doc-header" data-line="{doc.line_start + 1}">
            {toggle}
            {copy_btn}
            <span class="markup-only">{change_badge}</span> {type_badge}
            <span class="doc-title markup-only">{diff_title}</span>
            <span class="doc-title clean-only">{clean_title}</span>
            {uuid_display}
        </div>
        <div class="doc-body markup-only">
            {diff_body}
        </div>
        <div class="doc-body clean-only">
            {clean_body}
        </div>
        <div class="children">{children_html}</div>
    </div>
    '''
    else:
        return f'''
    <div class="{section_class}">
        <div class="doc-header" data-line="{doc.line_start + 1}">
            {copy_btn}
            <span class="markup-only">{change_badge}</span> {type_badge}
            <span class="doc-title markup-only">{diff_title}</span>
            <span class="doc-title clean-only">{clean_title}</span>
            {uuid_display}
        </div>
        <div class="doc-body markup-only">
            {diff_body}
        </div>
        <div class="doc-body clean-only">
            {clean_body}
        </div>
    </div>
    '''


def categorize_changed_docs(changed_docs, base_by_uuid):
    """Categorize changed docs into substantive changes vs renumbering-only.

    Returns (substantive_docs, renumbered_docs).

    A doc is considered renumbered (not substantive) only when:
    - The name is exactly the same (case-sensitive)
    - The body differs only in cross-reference document numbers

    Any name change — even a case-only change — is a substantive edit that
    should be shown to reviewers with a title diff.
    """
    substantive_docs = []
    renumbered_docs = []
    for doc in changed_docs:
        if doc.uuid and doc.uuid in base_by_uuid:
            old = base_by_uuid[doc.uuid]
            if old.body == doc.body and old.name == doc.name:
                continue
            if normalize_body(old.body) == normalize_body(doc.body) and old.name == doc.name:
                renumbered_docs.append(doc)
                continue
        substantive_docs.append(doc)
    return substantive_docs, renumbered_docs


def generate_preview(base: str, include_context: bool = True,
                     serve_mode: bool = False) -> tuple[str, str]:
    """Generate the preview HTML and return (html_string, content_hash).

    This is the core pipeline extracted from main() so it can be reused
    by the serve mode (regenerated on each request).
    """
    # Get branch name
    branch = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True, text=True
    ).stdout.strip()

    # Get current and base file content
    with open(ATLAS_PATH, encoding='utf-8') as f:
        current_text = f.read()

    base_text = get_file_at_ref(base, ATLAS_PATH)
    if not base_text:
        return (f"<html><body><h1>Error</h1><p>Could not get {ATLAS_PATH} at ref '{base}'</p></body></html>", "error")

    # Parse both versions
    current_docs = parse_atlas(current_text)
    base_docs = parse_atlas(base_text)

    # Find changed line ranges
    changed_lines = get_changed_ranges(base, ATLAS_PATH)
    changed_docs = find_changed_docs(current_docs, changed_lines)

    # Categorize changed docs: substantive changes vs renumbering-only.
    base_by_uuid = {d.uuid: d for d in base_docs if d.uuid}
    substantive_docs, renumbered_docs = categorize_changed_docs(changed_docs, base_by_uuid)
    changed_docs = substantive_docs

    if not changed_docs and not renumbered_docs:
        return ('<html><body><h1>No changes detected</h1></body></html>', 'empty')

    # Also find docs that were deleted
    current_uuids = {d.uuid for d in current_docs if d.uuid}
    deleted_docs = [d for d in base_docs if d.uuid and d.uuid not in current_uuids]

    # Collect docs to display
    substantive_numbers = set()
    for doc in changed_docs:
        substantive_numbers.add(doc.number)
        if include_context:
            for ancestor in find_ancestor_docs(doc, current_docs):
                substantive_numbers.add(ancestor.number)

    renumbered_numbers = set()
    for doc in renumbered_docs:
        renumbered_numbers.add(doc.number)
        if include_context:
            for ancestor in find_ancestor_docs(doc, current_docs):
                if ancestor.number not in substantive_numbers:
                    renumbered_numbers.add(ancestor.number)

    display_numbers = substantive_numbers | renumbered_numbers

    renumbered_uuids = set()
    renumbered_number_set = renumbered_numbers - substantive_numbers
    for doc in current_docs:
        if doc.number in renumbered_number_set and doc.uuid:
            renumbered_uuids.add(doc.uuid)
    for doc in renumbered_docs:
        if doc.uuid:
            renumbered_uuids.add(doc.uuid)

    display_docs = [d for d in current_docs if d.number in display_numbers]

    # Add deleted docs and their context ancestors to the display
    deleted_uuids = {d.uuid for d in deleted_docs if d.uuid}
    for deleted_doc in deleted_docs:
        # Add context ancestors from current_docs (the parent should still exist)
        if deleted_doc.number and include_context:
            parts = deleted_doc.number.split('.')
            for i in range(len(parts) - 1, 0, -1):
                parent_num = '.'.join(parts[:i])
                parent = find_doc_by_number(current_docs, parent_num)
                if parent and parent.number not in display_numbers:
                    display_numbers.add(parent.number)
                    display_docs.append(parent)
                    # Also add ancestors of the parent
                    for ancestor in find_ancestor_docs(parent, current_docs):
                        if ancestor.number not in display_numbers:
                            display_numbers.add(ancestor.number)
                            display_docs.append(ancestor)
                break
        display_docs.append(deleted_doc)

    tree = build_hierarchy(display_docs, deleted_uuids=deleted_uuids)

    # Count stats
    base_uuids = {d.uuid for d in base_docs if d.uuid}
    new_count = sum(1 for d in changed_docs if d.uuid and d.uuid not in base_uuids)
    modified_count = len(changed_docs) - new_count
    removed_count = len(deleted_docs)
    renumbered_count = len(renumbered_docs)

    # Render each root
    global _renumbered_uuids, _deleted_uuids
    _renumbered_uuids = renumbered_uuids
    _deleted_uuids = deleted_uuids
    content_parts = []
    for root in tree:
        is_new = root.uuid and root.uuid not in base_uuids
        is_renum = root.uuid in renumbered_uuids
        content_parts.append(render_doc_html(root, base_docs, is_new=is_new, is_renumbered=is_renum))

    # Generate HTML
    content_str = '\n<hr class="separator">\n'.join(content_parts)
    content_hash = hashlib.md5(content_str.encode('utf-8')).hexdigest()[:12]
    renumbered_display = 'block' if renumbered_count > 0 else 'none'

    html_output = f"""<html><body>
    <div class="stats">
        <span>New: {new_count}</span>
        <span>Modified: {modified_count}</span>
        <span>Removed: {removed_count}</span>
        <span>Renumbered: {renumbered_count}</span>
    </div>
    <div class="content">{content_str}</div>
    </body></html>"""

    return html_output, content_hash
