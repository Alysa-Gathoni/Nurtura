from django import template

from ..metrics import dashboard

register = template.Library()


@register.inclusion_tag("admin/insights/dashboard.html")
def nurtura_dashboard():
    """The analytics dashboard on the admin home page (#116)."""
    return {"d": dashboard()}


@register.filter
def stars(rating):
    """3 -> '★★★☆☆'."""
    rating = int(rating)
    return "★" * rating + "☆" * (5 - rating)
