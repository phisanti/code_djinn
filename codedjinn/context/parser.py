"""XML parsing and formatting utilities for prompt construction."""


def escape_xml_content(text: str) -> str:
    """
    Escape special XML characters in content.

    Args:
        text: Raw text that may contain XML special characters

    Returns:
        Text with XML special characters escaped

    Note:
        Order matters: & must be escaped first to avoid double-escaping
    """
    return (text
            .replace('&', '&amp;')   # Must be first
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def wrap_xml_tag(tag: str, content: str, indent: int = 0) -> str:
    """
    Wrap content in XML opening and closing tags.

    Args:
        tag: Tag name (without angle brackets)
        content: Content to wrap
        indent: Number of spaces to indent (default: 0)

    Returns:
        Content wrapped in XML tags
    """
    indent_str = ' ' * indent
    return f"{indent_str}<{tag}>\n{content}\n{indent_str}</{tag}>"


def simple_xml_tag(tag: str, content: str) -> str:
    """
    Create a simple single-line XML tag.

    Args:
        tag: Tag name (without angle brackets)
        content: Content (should not contain newlines)

    Returns:
        Single-line XML element
    """
    return f"<{tag}>{content}</{tag}>"
