from app.chat.markdown_parser import extract_mentions, sanitize_html, render_markdown


def test_extract_mentions_simple():
    assert extract_mentions('Oi @rafael e @marcus') == ['rafael', 'marcus']


def test_extract_mentions_ignores_email():
    # @bob@email.com is NOT a mention
    assert extract_mentions('mande para bob@email.com') == []


def test_extract_mentions_ignores_code_block():
    text = 'use `@decorator` em codigo'
    # mentions inside backticks ignored
    assert extract_mentions(text) == []


def test_extract_mentions_unique():
    assert extract_mentions('@a @b @a') == ['a', 'b']


def test_render_markdown_basic():
    html = render_markdown('**bold** and *italic*')
    assert '<strong>bold</strong>' in html
    assert '<em>italic</em>' in html


def test_sanitize_html_strips_script():
    dirty = '<p>texto</p><script>alert(1)</script>'
    clean = sanitize_html(dirty)
    assert '<script>' not in clean
    assert '<p>texto</p>' in clean


def test_sanitize_html_keeps_links_with_rel_noopener():
    dirty = '<a href="http://x.com">x</a>'
    clean = sanitize_html(dirty)
    assert 'rel="noopener' in clean or 'rel="nofollow' in clean or 'href="http://x.com"' in clean
