import html


def wrapped_tooltip(text, width=280):
    """A plain setToolTip(text) tooltip only wraps once it's nearly as wide
    as the whole screen -- Qt's tooltip layout otherwise assumes plain text
    is a single short line. A `<div>` with an explicit width is the
    reliable way to force a narrower wrap (a `<span>`'s inline max-width
    isn't honored by Qt's rich-text engine); wrap any tooltip longer than a
    short label in this."""
    return '<div style="width: %dpx;">%s</div>' % (width, html.escape(text))
