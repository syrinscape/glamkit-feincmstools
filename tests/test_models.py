import unittest

from feincmstools.models import create_content_types


class ContentTypeRegistrationTests(unittest.TestCase):
    def test_registers_content_types_in_first_seen_order(self):
        class Region:
            def __init__(self, key):
                self.key = key

        class Alpha:
            pass

        class Beta:
            pass

        class FeinCMSModel:
            _feincms_all_regions = [Region('first'), Region('second')]
            registrations = []

            @classmethod
            def create_content_type(
                    cls, content_type, regions, class_name, optgroup,
                    **kwargs):
                cls.registrations.append((
                    content_type.__name__,
                    sorted(regions),
                    class_name,
                    optgroup,
                    kwargs,
                ))
                return type('Registered%s' % content_type.__name__, (), {})

        def content_types_by_region(region):
            if region == 'first':
                return [('primary', (Alpha, Beta))]
            return [('secondary', (Alpha,))]

        create_content_types(FeinCMSModel, content_types_by_region)

        self.assertEqual([
            ('Alpha', ['first', 'second'], None, 'primary', {}),
            ('Beta', ['first'], None, 'primary', {}),
        ], FeinCMSModel.registrations)


if __name__ == '__main__':
    unittest.main()
