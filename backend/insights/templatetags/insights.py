from django import template

from ..metrics import dashboard
from ..overview import outcomes_donut, overview, parse_range

register = template.Library()


@register.inclusion_tag("admin/insights/dashboard.html", takes_context=True)
def nurtura_dashboard(context):
    """The operations overview on the admin home page (#116, #120).

    `app_list` is the admin's own list of sections the user may see, used
    for the sidebar; `?range=` picks the trend chart's period.
    """
    request = context.get("request")
    days = parse_range(request.GET.get("range") if request else None)
    d = dashboard()
    o = overview(days=days)
    return {
        "d": d,
        "o": o,
        "outcomes": outcomes_donut(d["done"], d["partly"], d["recommended"]),
        "stat_cards": STAT_CARDS,
        "spark_totals": o["spark_totals"],
        "app_list": context.get("app_list", []),
    }


# The four gradient summary cards: key into the daily series, and label.
STAT_CARDS = (
    ("signups", "New caregivers"),
    ("ideas", "Idea batches"),
    ("milestones", "Milestones recorded"),
    ("feedback", "Feedback received"),
)


@register.filter
def stars(rating):
    """3 -> '★★★☆☆'."""
    rating = int(rating)
    return "★" * rating + "☆" * (5 - rating)


@register.filter
def get_item(mapping, key):
    """{{ values|get_item:'ideas' }} in templates."""
    return mapping.get(key, 0)
