from playwright.async_api import async_playwright

from mta.anchor import SemanticAnchor


async def test_extract_returns_three_string_fields() -> None:
    """Basic shape: extract returns dict with parent_text, sibling_text, nearby_labels as strings."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<div><button id='btn'>Submit</button></div>")
            anchor = await SemanticAnchor.extract(page, "#btn")
            assert isinstance(anchor, dict)
            assert set(anchor.keys()) == {"parent_text", "sibling_text", "nearby_labels"}
            assert isinstance(anchor["parent_text"], str)
            assert isinstance(anchor["sibling_text"], str)
            assert isinstance(anchor["nearby_labels"], str)
        finally:
            await browser.close()


async def test_parent_text_excludes_element_own_text() -> None:
    """parent_text is parent's textContent minus the element's own text."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                "<div>Section title <button id='btn'>Click me</button> trailing</div>"
            )
            anchor = await SemanticAnchor.extract(page, "#btn")
            assert "Section title" in anchor["parent_text"]
            assert "trailing" in anchor["parent_text"]
            assert "Click me" not in anchor["parent_text"]
        finally:
            await browser.close()


async def test_sibling_text_from_adjacent_elements() -> None:
    """sibling_text contains text from immediate siblings, not the element itself."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                "<div>"
                "<span>Before</span>"
                "<input id='inp' type='text' />"
                "<span>After hint</span>"
                "</div>"
            )
            anchor = await SemanticAnchor.extract(page, "#inp")
            assert "Before" in anchor["sibling_text"]
            assert "After hint" in anchor["sibling_text"]
        finally:
            await browser.close()


async def test_nearby_labels_from_label_for_attribute() -> None:
    """nearby_labels includes text of <label for=id> pointing at the element."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                "<form>"
                "<label for='email'>Email address</label>"
                "<input id='email' type='email' />"
                "</form>"
            )
            anchor = await SemanticAnchor.extract(page, "#email")
            assert "Email address" in anchor["nearby_labels"]
        finally:
            await browser.close()


async def test_nearby_labels_from_aria_labelledby() -> None:
    """nearby_labels includes text referenced by aria-labelledby."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                "<div>"
                "<span id='lbl'>Username</span>"
                "<input id='user' aria-labelledby='lbl' />"
                "</div>"
            )
            anchor = await SemanticAnchor.extract(page, "#user")
            assert "Username" in anchor["nearby_labels"]
        finally:
            await browser.close()


async def test_nearby_labels_from_heading_ancestor() -> None:
    """nearby_labels includes nearest heading ancestor's text."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                "<section>"
                "<h2>Payment Details</h2>"
                "<div><button id='pay'>Pay now</button></div>"
                "</section>"
            )
            anchor = await SemanticAnchor.extract(page, "#pay")
            assert "Payment Details" in anchor["nearby_labels"]
        finally:
            await browser.close()


async def test_deeply_nested_element_parent_text() -> None:
    """Deeply nested element: parent_text reflects immediate parent, not root."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                "<div>"
                "<section>"
                "<article>"
                "<div class='inner'>Inner context <button id='deep'>Go</button></div>"
                "</article>"
                "</section>"
                "</div>"
            )
            anchor = await SemanticAnchor.extract(page, "#deep")
            assert "Inner context" in anchor["parent_text"]
        finally:
            await browser.close()


async def test_fields_bounded_at_200_chars() -> None:
    """All returned fields are at most 200 characters."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            long_text = "x" * 500
            await page.set_content(
                f"<div>{long_text} <button id='btn'>OK</button> {long_text}</div>"
            )
            anchor = await SemanticAnchor.extract(page, "#btn")
            assert len(anchor["parent_text"]) <= 200
            assert len(anchor["sibling_text"]) <= 200
            assert len(anchor["nearby_labels"]) <= 200
        finally:
            await browser.close()


async def test_empty_strings_not_none_for_missing_fields() -> None:
    """When context is absent, fields are empty string, not None."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            # Minimal structure: no label, no siblings, minimal parent text
            await page.set_content("<div><button id='lone'>Lone</button></div>")
            anchor = await SemanticAnchor.extract(page, "#lone")
            # All fields must be str (even if empty)
            for v in anchor.values():
                assert v is not None
                assert isinstance(v, str)
        finally:
            await browser.close()
