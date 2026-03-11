import base64
import json
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class ScholarshipCursorPagination(CursorPagination):
    """
    Cursor pagination ordered by (-created_at, -id).

    - page_size: 12 cards per load (fills a 4-col grid neatly, leaves room for
      a partial row which signals "more content below").
    - ordering: newest first, with id as tiebreaker for stability.
    - page_size_query_param: allows ?page_size=N for power users / the admin
      dashboard (capped at 50 to prevent abuse).
    - max_page_size: hard cap.
    """
    page_size              = 12
    ordering               = ("-created_at", "-id")
    cursor_query_param     = "cursor"
    page_size_query_param  = "page_size"
    max_page_size          = 50

    def get_paginated_response(self, data):
        return Response({
            "next":     self.get_next_link(),
            "previous": self.get_previous_link(),
            # Omit count — cursor pagination doesn't need a full table scan.
            # The frontend infers "no more pages" from next == null.
            "results":  data,
        })

    def get_paginated_response_schema(self, schema):
        # For drf-spectacular / OpenAPI docs
        return {
            "type": "object",
            "required": ["results"],
            "properties": {
                "next":     {"type": "string",  "nullable": True, "format": "uri"},
                "previous": {"type": "string",  "nullable": True, "format": "uri"},
                "results":  schema,
            },
        }