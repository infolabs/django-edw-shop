# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import (
    ValidationError,
    ObjectDoesNotExist,
    MultipleObjectsReturned
)
from django.db.models.fields import NOT_PROVIDED
from django.db.models.fields.related import RelatedField
from django.db.models.fields.reverse_related import ForeignObjectRel
from edw.models.entity import EntityModel

from edw.models.term import TermModel
from edw.rest.serializers.decorators import empty
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from edw.rest.serializers.entity import EntityValidator


# =========================================================================================================
# Publication validator
# =========================================================================================================
class ProductValidator(EntityValidator):

    def __call__(self, attrs):

        model = self.serializer.Meta.model
        # Determine the existing instance, if this is an update operation.
        instance = getattr(self.serializer, 'instance', None)

        validated_data = dict(attrs)
        request_method = self.serializer.request_method

        available_terms_ids = set(self.serializer.data_mart_available_terms_ids)
        attr_errors = {}

        # check update for POST method
        if request_method == 'POST':
            for id_attr in self.serializer.get_id_attrs():
                id_value = validated_data.get(id_attr, empty)
                if id_value != empty:

                    try:
                        instance = model.objects.get(**{id_attr: id_value})
                    except ObjectDoesNotExist:
                        pass
                    except MultipleObjectsReturned as e:
                        attr_errors[id_attr] = _("{} `{}`='{}'").format(str(e), id_attr, id_value)
                    else:
                        # try check data mart permissions
                        if (self.serializer.data_mart_from_request is not None and
                                not self.serializer.data_mart_permissions_from_request['can_change']):
                            self.serializer.permission_denied(self.serializer.context['request'])

                        # try check object permissions, see the CheckPermissionsSerializerMixin
                        self.serializer.check_object_permissions(instance)
                        if not validated_data.get('slug', None):
                            validated_data['slug'] = instance.slug
                    break

        # characteristics, marks
        for (attr_name, attribute_mode) in [
            ('characteristics', TermModel.attributes.is_characteristic),
            ('marks', TermModel.attributes.is_mark)
        ]:
            attributes = validated_data.pop(attr_name, None)
            if attributes is not None:
                errors = []
                terms = TermModel.objects.active().attribute_filter(attribute_mode)
                for attribute in attributes:
                    error = {}
                    path = attribute.get('path', None)
                    if path is not None:
                        # Try find Term by `slug` or `path`
                        field = 'slug' if path.find('/') == -1 else 'path'

                        try:
                            terms.get(**{field: path, 'id__in': available_terms_ids})
                        except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
                            error.update({'path': _("{} `{}`='{}'").format(str(e), field, path)})

                    else:
                        error.update({'path': [self.FIELD_REQUIRED_ERROR_MESSAGE]})
                    values = attribute.get('values', None)
                    if values is None:
                        error.update({'values': [self.FIELD_REQUIRED_ERROR_MESSAGE]})
                    errors.append(error)
                if any(errors):
                    attr_errors[attr_name] = errors

        # terms_paths
        terms_paths = validated_data.pop('terms_paths', None)
        if terms_paths is not None:
            errors = []
            terms = TermModel.objects.active().no_external_tagging_restriction()
            for path in terms_paths:
                # Try find Term by `slug` or `path`
                field = 'slug' if path.find('/') == -1 else 'path'
                try:
                    terms.get(**{field: path, 'id__in': available_terms_ids})
                except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
                    errors.append(_("{} `{}`='{}'").format(str(e), field, path))
            if errors:
                attr_errors['terms_paths'] = errors

        # terms_ids
        terms_ids = validated_data.pop('active_terms_ids', None)
        if terms_ids is not None:
            not_found_ids = list(set(terms_ids) - available_terms_ids)
            if not_found_ids:
                attr_errors['terms_ids'] = _("Terms with id`s [{}] not found.").format(
                    ', '.join(str(x) for x in not_found_ids))

        # relations
        relations = validated_data.pop('relations', None)
        if relations is not None:
            rel_subj, rel_f_ids, rel_r_ids = self.serializer.parse_relations(relations)
            rel_f_ids, rel_r_ids = set(rel_f_ids), set(rel_r_ids)
            errors = []

            # validate relations ids
            rel_b_ids = rel_f_ids | rel_r_ids
            not_found_ids = list(rel_b_ids - set(TermModel.objects.active().attribute_is_relation().filter(
                id__in=rel_b_ids).values_list('id', flat=True)))
            if not_found_ids:
                errors.append(_("Terms with id`s [{}] not found.").format(', '.join(str(x) for x in not_found_ids)))

            # validate subjects ids
            subj_ids = []
            for ids in rel_subj.values():
                subj_ids.extend(ids)
            not_found_ids = list(set(subj_ids) - set(EntityModel.objects.active().filter(
                id__in=subj_ids).values_list('id', flat=True)))
            if not_found_ids:
                errors.append(_("Entities with id`s [{}] not found.").format(', '.join(str(x) for x in not_found_ids)))

            if self.serializer.is_data_mart_has_relations:
                not_found = ["`{}f`".format(x) for x in list(
                    rel_f_ids - set(self.serializer.data_mart_rel_ids[0]))] + ["`{}r`".format(x) for x in list(
                    rel_r_ids - set(self.serializer.data_mart_rel_ids[1]))]
                if not_found:
                    errors.append(
                        _("The relations [{}] are forbidden.").format(', '.join(str(x) for x in not_found)))

                if self.serializer.is_data_mart_relations_has_subjects:
                    for rel_id, subj_ids in self.serializer.data_mart_relations_subjects.items():
                        if subj_ids:
                            not_found_ids = list(set(rel_subj.get(rel_id, [])) - set(subj_ids))
                            if not_found_ids:
                                errors.append(
                                    _("The subjects with id`s [{}] are forbidden.").format(
                                        ', '.join(str(x) for x in not_found_ids)))
                elif not subj_ids:
                    errors.append(_("The subjects cannot be the empty."))

            if errors:
                attr_errors['relations'] = errors
        elif instance is None and self.serializer.is_data_mart_has_relations and \
                not self.serializer.is_data_mart_relations_has_subjects:
            attr_errors['relations'] = _('This field is required.')

        if attr_errors:
            raise serializers.ValidationError(attr_errors)

        # model validation
        model_fields = model._meta.get_fields()
        validated_data_keys = set(validated_data.keys())
        # exclude fields from RESTMeta
        exclude = model._rest_meta.exclude
        # exclude not model fields from validate data
        for x in list(validated_data_keys - set([f.name for f in model_fields])):
            validated_data.pop(x)
        if request_method == 'PATCH':
            required_fields = [f.name for f in model_fields if not isinstance(f, (
                RelatedField, ForeignObjectRel)) and not getattr(f, 'blank', False) is True and getattr(
                f, 'default', NOT_PROVIDED) is NOT_PROVIDED]
            exclude = list((set(required_fields) - validated_data_keys) | set(exclude))

        validate_unique = instance is None
        # model full clean
        try:
            model(**validated_data).full_clean(validate_unique=validate_unique, exclude=exclude)
        except (ObjectDoesNotExist, ValidationError) as e:
            raise serializers.ValidationError(str(e))
        # side effect, return instance
        return instance
