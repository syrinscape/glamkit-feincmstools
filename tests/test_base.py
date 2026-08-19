import os
import sys
import types
import unittest

import django
from django.conf import settings


if not settings.configured:
    settings.configure(
        SECRET_KEY='test-secret-key',
        TEMPLATE_DIRS=(os.path.join(os.path.dirname(__file__), 'templates'),),
        TEMPLATE_LOADERS=('django.template.loaders.filesystem.Loader',),
    )

if hasattr(django, 'setup'):
    django.setup()

from django.db import models
from django.http import HttpRequest
from django.template import Context


class FeinCMSBase(models.Model):
    class Meta:
        abstract = True
        app_label = 'tests'


class MPTTModel(models.Model):
    class Meta:
        abstract = True
        app_label = 'tests'


feincms = types.ModuleType('feincms')
feincms_models = types.ModuleType('feincms.models')
feincms_models.create_base_model = lambda: FeinCMSBase
feincms.models = feincms_models
sys.modules['feincms'] = feincms
sys.modules['feincms.models'] = feincms_models

mptt = types.ModuleType('mptt')
mptt_models = types.ModuleType('mptt.models')
mptt_models.MPTTModel = MPTTModel
mptt_models.MPTTModelBase = models.base.ModelBase
mptt.models = mptt_models
sys.modules['mptt'] = mptt
sys.modules['mptt.models'] = mptt_models

from feincmstools.base import Content


class RenderableContent(Content):
    render_template = 'content.html'
    value = 'content-value'

    class Meta:
        app_label = 'tests'

    def __init__(self):
        pass


class ContentRenderTests(unittest.TestCase):
    def test_render_accepts_django_context(self):
        supplied_context = Context({'supplied': 'shadowed-value'})
        supplied_context.push()
        supplied_context['supplied'] = 'context-value'
        rendered = Content.render(
            RenderableContent(),
            request=HttpRequest(),
            context=supplied_context,
        )

        self.assertEqual('context-value:content-value', rendered.strip())

    def test_render_passes_a_plain_mapping_to_django(self):
        rendered = Content.render(
            RenderableContent(),
            request=HttpRequest(),
            context={'supplied': 'context-value'},
        )

        self.assertEqual('context-value:content-value', rendered.strip())


if __name__ == '__main__':
    unittest.main()
