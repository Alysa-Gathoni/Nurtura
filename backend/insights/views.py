"""Admin dashboard and search-index endpoints for the app (#122)."""

from io import StringIO

from django.core.management import call_command
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.permissions import IsAdministrator

from .overview import api_overview, parse_range, stale_embeddings


class AdminOverviewView(APIView):
    """GET the operations overview (?range=7, 30 or 90 days)."""

    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(
            api_overview(days=parse_range(request.query_params.get("range")))
        )


class AdminSearchIndexView(APIView):
    """POST makes Published activities searchable (embed_activities), so an
    administrator on a phone doesn't need the command line. It loads the AI
    model if it isn't loaded, which can take about 15 seconds."""

    permission_classes = [IsAdministrator]

    def post(self, request):
        out = StringIO()
        call_command("embed_activities", stdout=out)
        return Response(
            {
                "message": (
                    out.getvalue().strip().splitlines()[-1]
                    if out.getvalue().strip()
                    else ""
                ),
                "not_searchable": stale_embeddings(),
            }
        )
