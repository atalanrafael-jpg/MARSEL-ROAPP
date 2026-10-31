from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_FILE = ROOT / "web" / "index.html"
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class MarkupInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.titles = 0
        self.viewport_meta = 0
        self.nested_main = False
        self.mismatched_closings = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "title":
            self.titles += 1
        if tag == "meta" and attrs.get("name", "").lower() == "viewport":
            self.viewport_meta += 1
        if tag == "main" and "main" in self.stack:
            self.nested_main = True
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            self.mismatched_closings.append(tag)
            return
        if not self.stack or self.stack[-1] != tag:
            self.mismatched_closings.append(tag)
            if tag in self.stack:
                self.stack = self.stack[: self.stack.index(tag)]
            return
        self.stack.pop()


def inspect_markup():
    parser = MarkupInspector()
    parser.feed(HTML_FILE.read_text(encoding="utf-8"))
    parser.close()
    return parser


def test_html_ids_are_unique():
    parser = inspect_markup()
    duplicates = sorted(value for value, count in Counter(parser.ids).items() if count > 1)
    assert not duplicates, f"Duplicate HTML id values: {duplicates}"


def test_document_has_one_title_and_one_viewport_declaration():
    parser = inspect_markup()
    assert parser.titles == 1, f"Expected one title element, found {parser.titles}"
    assert parser.viewport_meta == 1, (
        f"Expected one viewport meta element, found {parser.viewport_meta}"
    )


def test_document_has_no_nested_main_elements():
    parser = inspect_markup()
    assert not parser.nested_main, "A main element must not be nested inside another main element"


def test_document_tags_are_balanced_and_well_nested():
    parser = inspect_markup()
    assert not parser.mismatched_closings, (
        f"Mismatched closing tags: {parser.mismatched_closings}"
    )
    assert not parser.stack, f"Unclosed HTML elements: {parser.stack}"
