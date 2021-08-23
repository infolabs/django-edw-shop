# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from edw.models.term import TermModel

_default_system_flags_restriction = (TermModel.system_flags.delete_restriction |
                                     TermModel.system_flags.change_parent_restriction |
                                     TermModel.system_flags.change_slug_restriction)


ENTITY_CLASS_WRAPPER_TERM_SLUG_PATTERN = "{}_wrapped"

def get_or_create_term_wrapper(original_term,
                               default_name = _("Type"),
                               rule = TermModel.AND_RULE,
                               wrapped_rule = TermModel.XOR_RULE,
                               specification = TermModel.SPECIFICATION_MODES[0][0],
                               system_flags = _default_system_flags_restriction):
    """
    RUS: Получает или создает термин обертку.
    """

    term_parent = original_term.parent

    # Compose new entity model class term slug
    new_term_slug = ENTITY_CLASS_WRAPPER_TERM_SLUG_PATTERN.format(original_term.slug)
    if (term_parent is None) or (term_parent.slug != new_term_slug):
        with transaction.atomic():
            try:  # get or create model class root term
                root_term = TermModel.objects.get(slug=new_term_slug, parent=term_parent)
            except TermModel.DoesNotExist:
                root_term = TermModel(
                    slug=new_term_slug,
                    parent=term_parent,
                    name=original_term.name,
                    semantic_rule=rule,
                    specification_mode=specification,
                    system_flags=system_flags
                )
                root_term.save()

            # set original entity model class term to new parent
            if original_term.parent != root_term:
                original_term.parent = root_term
                original_term.name = default_name
                original_term.semantic_rule = wrapped_rule
                original_term.save()
    else:
        root_term = term_parent

    return root_term
