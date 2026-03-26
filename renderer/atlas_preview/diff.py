"""Diff utilities — word-level and line-level diffing, git change detection."""

import difflib
import html
import re
import subprocess
from typing import Optional

from atlas_preview.parser import AtlasDoc


def word_diff(old_text: str, new_text: str) -> str:
    """Generate word-level HTML diff."""
    if not old_text and not new_text:
        return ""
    if not old_text:
        return f'<span class="added">{html.escape(new_text)}</span>'
    if not new_text:
        return f'<span class="removed">{html.escape(old_text)}</span>'

    # Split into words while preserving whitespace/newlines
    def tokenize(text):
        return re.findall(r'\S+|\s+', text)

    old_tokens = tokenize(old_text)
    new_tokens = tokenize(new_text)

    sm = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    result = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            result.append(html.escape(''.join(old_tokens[i1:i2])))
        elif op == 'replace':
            result.append(f'<span class="removed">{html.escape("".join(old_tokens[i1:i2]))}</span>')
            result.append(f'<span class="added">{html.escape("".join(new_tokens[j1:j2]))}</span>')
        elif op == 'insert':
            result.append(f'<span class="added">{html.escape("".join(new_tokens[j1:j2]))}</span>')
        elif op == 'delete':
            result.append(f'<span class="removed">{html.escape("".join(old_tokens[i1:i2]))}</span>')

    return ''.join(result)


def line_diff(old_text: str, new_text: str) -> str:
    """Generate line-by-line diff with word-level highlighting within changed lines."""
    old_lines = old_text.split('\n') if old_text else []
    new_lines = new_text.split('\n') if new_text else []

    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    result_lines = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for line in new_lines[j1:j2]:
                result_lines.append(f'<div class="line context">{html.escape(line)}</div>')
        elif op == 'replace':
            # Word-diff each pair of old/new lines
            old_chunk = old_lines[i1:i2]
            new_chunk = new_lines[j1:j2]
            max_len = max(len(old_chunk), len(new_chunk))
            for k in range(max_len):
                old_l = old_chunk[k] if k < len(old_chunk) else ""
                new_l = new_chunk[k] if k < len(new_chunk) else ""
                if old_l and not new_l:
                    result_lines.append(f'<div class="line removed-line"><span class="removed">{html.escape(old_l)}</span></div>')
                elif new_l and not old_l:
                    result_lines.append(f'<div class="line added-line"><span class="added">{html.escape(new_l)}</span></div>')
                else:
                    diff_html = word_diff(old_l, new_l)
                    result_lines.append(f'<div class="line changed-line">{diff_html}</div>')
        elif op == 'insert':
            for line in new_lines[j1:j2]:
                result_lines.append(f'<div class="line added-line"><span class="added">{html.escape(line)}</span></div>')
        elif op == 'delete':
            for line in old_lines[i1:i2]:
                result_lines.append(f'<div class="line removed-line"><span class="removed">{html.escape(line)}</span></div>')

    return '\n'.join(result_lines)


def get_file_at_ref(ref: str, path: str) -> Optional[str]:
    """Get file content at a git ref."""
    try:
        result = subprocess.run(
            ['git', 'show', f'{ref}:{path}'],
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def get_changed_ranges(base: str, path: str) -> set[int]:
    """Get set of line numbers (0-indexed) changed in working tree vs base."""
    result = subprocess.run(
        ['git', 'diff', '-U0', base, '--', path],
        capture_output=True, text=True, encoding='utf-8'
    )
    changed = set()
    for line in result.stdout.split('\n'):
        m = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', line)
        if m:
            start = int(m.group(1)) - 1  # 0-indexed
            count = int(m.group(2)) if m.group(2) else 1
            changed.update(range(start, start + count))
    return changed


def find_changed_docs(docs: list[AtlasDoc], changed_lines: set[int]) -> list[AtlasDoc]:
    """Find docs whose line ranges overlap with changed lines."""
    changed_docs = []
    for doc in docs:
        doc_range = set(range(doc.line_start, doc.line_end + 1))
        if doc_range & changed_lines:
            changed_docs.append(doc)
    return changed_docs
