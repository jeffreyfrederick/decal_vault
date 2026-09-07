"""Helpers for Hunter's icon set (app/static/icons) - 294 icons, each
pre-rendered in four brand colors as SVG. Files are laid out
<Color>/SVG/icon-<name>[-<suffix>].svg, where Black is unsuffixed and
Gray/Red/White carry a -gray/-red/-white suffix.
"""
from flask import url_for

COLORS = {"black", "gray", "red", "white"}

# Equipment category -> product icon, matched on a lowercase substring; falls back to "tools".
_CATEGORY_ICONS = (
    ("tire changer", "product-tire-changer"),
    ("align", "product-alignment-equipment"),
    ("balanc", "product-wheel-balancer"),
    ("brake lathe", "product-brake-lathe"),
    ("lift", "product-lift-rack"),
    ("rack", "product-lift-rack"),
    ("inspection", "product-inspection"),
)
_CATEGORY_ICON_FALLBACK = "tools"


def icon_url(name, color="black"):
    if color not in COLORS:
        raise ValueError(f"unknown icon color: {color!r} (expected one of {sorted(COLORS)})")
    suffix = "" if color == "black" else f"-{color}"
    return url_for("static", filename=f"icons/{color.capitalize()}/SVG/icon-{name}{suffix}.svg")


def category_icon_name(category):
    category_lower = (category or "").lower()
    for needle, icon_name in _CATEGORY_ICONS:
        if needle in category_lower:
            return icon_name
    return _CATEGORY_ICON_FALLBACK
