# -*- coding: utf-8 -*-
from rest_framework_filters import CharFilter


class stateFilter(CharFilter):
    """
    Фильтрует по статусу
    """
    def filter(self, qs, value):
        if value:
            qs = qs.filter(order__status=value)

        return qs
