from typing import Any

from markdown_it import MarkdownIt

md = MarkdownIt()


def markdown_to_html(text: str) -> Any:
    return md.render(text)
