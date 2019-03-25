# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from ckeditor.widgets import CKEditorWidget

from edw.admin.entity.forms import EntityAdminForm as OriginalEntityAdminForm


class EntityAdminForm(OriginalEntityAdminForm):
    description = forms.CharField(
        widget=CKEditorWidget(),
        label=_('Description'),
        required=False
    )