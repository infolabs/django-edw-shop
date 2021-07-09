# -*- coding: utf-8 -*-
from rest_framework_filters import CharFilter

#from nash_region.models.entity import Entity
#from nash_region.models.problem import ParticularProblem


class stateFilter(CharFilter):
    """
    Фильтрует ответственных только у кого есть проблемы в работе
    """
    def filter(self, qs, value):
        if value:
            parent = getattr(self, 'parent', None)
            if parent is not None:
                terms_ids = parent.data.get("_terms_ids", None)
                if terms_ids:
                    responsible_person_ids = Entity.objects.instance_of(ParticularProblem).active().semantic_filter(
                        terms_ids, use_cached_decompress=True, fix_it=False
                    ).filter(forward_relations__term__slug='responsibleperson').values_list(
                        "forward_relations__to_entity_id", flat=True).distinct()
                    qs = qs.filter(id__in=responsible_person_ids)
            if self.distinct:
                    qs = qs.distinct()
        return qs
