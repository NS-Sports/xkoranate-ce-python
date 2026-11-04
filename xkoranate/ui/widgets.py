def discard(layout, widget):
    """Take widget out of layout and unparent it, deleting it once control
    returns to the event loop."""
    layout.removeWidget(widget)
    widget.setParent(None)
    widget.deleteLater()
