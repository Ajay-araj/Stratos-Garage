"""
Standard pagination for all list endpoints.
Returns:
    {
        "count": <total>,
        "page": <current>,
        "page_size": <size>,
        "total_pages": <n>,
        "next": <url|null>,
        "previous": <url|null>,
        "results": [...]
    }
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math


class StandardResultsPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'required': ['count', 'page', 'page_size', 'total_pages', 'results'],
            'properties': {
                'count': {'type': 'integer'},
                'page': {'type': 'integer'},
                'page_size': {'type': 'integer'},
                'total_pages': {'type': 'integer'},
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': schema,
            },
        }
