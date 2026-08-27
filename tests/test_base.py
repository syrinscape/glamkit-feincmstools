import os
import sys
import types
import unittest

import django
from django.conf import settings


TESTS_DIR = os.path.dirname(__file__)


if not settings.configured:
    settings.configure(
        SECRET_KEY='test-secret-key',
        TEMPLATE_DIRS=(os.path.join(TESTS_DIR, 'templates'),),
        TEMPLATE_LOADERS=('django.template.loaders.filesystem.Loader',),
        TEMPLATES=(
            {
                'BACKEND': 'django.template.backends.jinja2.Jinja2',
                'DIRS': (os.path.join(TESTS_DIR, 'jinja_templates'),),
            },
            {
                'BACKEND': (
                    'django.template.backends.django.DjangoTemplates'
                ),
                'DIRS': (os.path.join(TESTS_DIR, 'templates'),),
            },
        ),
    )

if hasattr(django, 'setup'):
    django.setup()

from django.db import models
from django.http import HttpRequest
from django.template import Context


class FeinCMSBase(models.Model):
    @classmethod
    def register_regions(cls, *regions):
        cls._feincms_all_regions = [
            type('Region', (), {'key': region[0]})()
            for region in regions
        ]

    @classmethod
    def create_content_type(cls, content_type, **kwargs):
        cls.registrations.append((content_type, kwargs))
        return type(content_type.__name__, (), {})

    class Meta:
        abstract = True
        app_label = 'tests'


class MPTTModelBase(models.base.ModelBase):
    pass


class MPTTModelMeta:
    abstract = True
    app_label = 'tests'


MPTTModel = MPTTModelBase('MPTTModel', (models.Model,), {
    '__module__': __name__,
    'Meta': MPTTModelMeta,
})


feincms = types.ModuleType('feincms')
feincms_models = types.ModuleType('feincms.models')
feincms_models.create_base_model = lambda: FeinCMSBase
feincms.models = feincms_models
sys.modules['feincms'] = feincms
sys.modules['feincms.models'] = feincms_models

mptt = types.ModuleType('mptt')
mptt_models = types.ModuleType('mptt.models')
mptt_models.MPTTModel = MPTTModel
mptt_models.MPTTModelBase = MPTTModelBase
mptt.models = mptt_models
sys.modules['mptt'] = mptt
sys.modules['mptt.models'] = mptt_models

from feincmstools.base import (
    Content,
    FeinCMSDocument,
    HierarchicalFeinCMSDocument,
)


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
        supplied_context['content'] = 'caller-content'
        original_context_dicts = [
            dict(context_dict) for context_dict in supplied_context.dicts
        ]
        rendered = Content.render(
            RenderableContent(),
            request=HttpRequest(),
            context=supplied_context,
        )

        self.assertEqual('context-value:content-value', rendered.strip())
        self.assertEqual(original_context_dicts, supplied_context.dicts)

    def test_render_passes_a_plain_mapping_to_django(self):
        supplied_context = {
            'content': 'caller-content',
            'supplied': 'context-value',
        }
        original_context = dict(supplied_context)
        rendered = Content.render(
            RenderableContent(),
            request=HttpRequest(),
            context=supplied_context,
        )

        self.assertEqual('context-value:content-value', rendered.strip())
        self.assertEqual(original_context, supplied_context)

    def test_render_skips_templates_from_incompatible_backends(self):
        content = RenderableContent()
        content.render_template = None
        content.region = 'main'
        content._render_template_paths = lambda region: iter((
            'jinja-only.html',
            'django-only.html',
        ))

        rendered = Content.render(
            content,
            request=HttpRequest(),
            context={'supplied': 'context-value'},
        )

        self.assertEqual('context-value:content-value', rendered.strip())


class DocumentRegistrationTests(unittest.TestCase):
    def test_concrete_documents_register_regions_and_content_types(self):
        class ExampleContent:
            pass

        document_bases = (
            HierarchicalFeinCMSDocument,
            FeinCMSDocument,
        )
        for document_base in document_bases:
            class RegisteredDocument(document_base):
                feincms_regions = (
                    ('main', 'Main'),
                )
                registrations = []

                @classmethod
                def content_types_by_region(cls, region):
                    return ((None, (ExampleContent,)),)

                class Meta:
                    app_label = 'tests'

            self.assertEqual([
                (ExampleContent, {
                    'class_name': None,
                    'optgroup': None,
                    'regions': {'main'},
                }),
            ], RegisteredDocument.registrations)


class ContentTemplateDetectionTests(unittest.TestCase):
    def test_detects_an_existing_template(self):
        self.assertEqual(
            'content.html',
            Content._detect_template('content.html'),
        )

    def test_returns_none_for_a_missing_template(self):
        self.assertIsNone(Content._detect_template('missing-content.html'))


class ContentTemplateParameterTests(unittest.TestCase):
    def test_uses_model_name_on_django_17_and_later(self):
        params = Content._template_params(
            RenderableContent,
            Content,
            region='main',
        )

        self.assertEqual('content', params['content_model_name'])
        self.assertEqual(
            'renderablecontent',
            params['content_type_using_model'],
        )

    def test_falls_back_to_module_name(self):
        class LegacyOptions(object):
            def __init__(self, app_label, module_name):
                self.app_label = app_label
                self.module_name = module_name

        class LegacyBase(object):
            _meta = LegacyOptions('defining-app', 'legacy-base')

        class LegacyContent(object):
            _meta = LegacyOptions('using-app', 'legacy-content')

        params = Content._template_params(
            LegacyContent,
            LegacyBase,
            region='main',
        )

        self.assertEqual({
            'content_type_defining_app': 'defining-app',
            'content_model_name': 'legacy-base',
            'content_type_using_app': 'using-app',
            'content_type_using_model': 'legacy-content',
            'content_type_using_region': 'main',
        }, params)


if __name__ == '__main__':
    unittest.main()
