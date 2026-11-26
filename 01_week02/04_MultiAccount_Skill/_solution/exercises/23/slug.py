import re
import unicodedata


def slugify(title: str, default: str | None = None) -> str:
    """Convert an English article title into a filename-safe slug.

    Args:
        title: The article title to convert.
        default: Optional fallback string to return if the resulting slug is empty.
                 If None (default), raises ValueError when the slug is empty.

    Returns:
        A lowercase, hyphen-separated filename-safe slug string.

    Raises:
        ValueError: If title produces an empty slug and no default is provided.
    """
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)  # drop special characters
    text = re.sub(r"[\s-]+", "-", text)  # whitespace/dashes -> single hyphen
    slug = text.strip("-")

    if not slug:
        if default is not None:
            return default
        raise ValueError(f"Cannot generate a valid filename slug from title: {title!r}")

    return slug


if __name__ == "__main__":
    print(slugify("Hello, World! My First Article #1"))
