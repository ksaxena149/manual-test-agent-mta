"""Semantic anchor extraction for cache entries.

SemanticAnchor.extract(page, selector) captures the DOM context around an
element so drift detection can re-locate it when its selector changes.
"""

from __future__ import annotations

from playwright.async_api import Page

_MAX_FIELD_LEN = 200

_JS = """
(el) => {
    if (!el) return {parent_text: '', sibling_text: '', nearby_labels: ''};

    // parent_text: parent's text minus this element's own text
    const parent = el.parentElement;
    let parentText = '';
    if (parent) {
        const own = el.textContent || '';
        const full = parent.textContent || '';
        // Remove the element's own text (first occurrence) from parent text
        parentText = full.replace(own, ' ').replace(/\\s+/g, ' ').trim();
    }

    // sibling_text: text of immediate siblings (not the element itself)
    let siblingParts = [];
    if (parent) {
        for (const child of parent.children) {
            if (child === el) continue;
            const t = (child.textContent || '').trim();
            if (t) siblingParts.push(t);
        }
    }
    const siblingText = siblingParts.join(' ').trim();

    // nearby_labels: label[for=id], aria-labelledby targets, nearest heading ancestor
    let labelParts = [];

    // label[for=id]
    const id = el.id;
    if (id) {
        const lbl = document.querySelector('label[for="' + id + '"]');
        if (lbl) {
            const t = (lbl.textContent || '').trim();
            if (t) labelParts.push(t);
        }
    }

    // aria-labelledby
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
        for (const refId of labelledBy.split(/\\s+/)) {
            const ref = document.getElementById(refId);
            if (ref) {
                const t = (ref.textContent || '').trim();
                if (t) labelParts.push(t);
            }
        }
    }

    // nearest heading ancestor
    const headingTags = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6']);
    let anc = el.parentElement;
    while (anc) {
        // look for a heading child before looking higher
        for (const child of anc.children) {
            if (headingTags.has(child.tagName)) {
                const t = (child.textContent || '').trim();
                if (t) { labelParts.push(t); anc = null; break; }
            }
        }
        if (anc) anc = anc.parentElement;
    }

    return {
        parent_text: parentText,
        sibling_text: siblingText,
        nearby_labels: labelParts.join(' ').trim(),
    };
}
"""


class SemanticAnchor:
    @staticmethod
    async def extract(page: Page, selector: str) -> dict[str, str]:
        try:
            raw: dict[str, str] = await page.locator(selector).first.evaluate(_JS)
        except Exception:
            raw = {}
        return {
            "parent_text": (raw.get("parent_text") or "")[:_MAX_FIELD_LEN],
            "sibling_text": (raw.get("sibling_text") or "")[:_MAX_FIELD_LEN],
            "nearby_labels": (raw.get("nearby_labels") or "")[:_MAX_FIELD_LEN],
        }
