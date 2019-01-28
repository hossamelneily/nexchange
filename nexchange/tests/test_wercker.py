from django.test import TestCase
import yaml


class ValidateWerckerFile(TestCase):

    def setUp(self):
        super(ValidateWerckerFile, self).setUp()
        self.wercker_path = 'wercker.yml'

    def test_dev_fixtures_not_in_prod(self):
        with open(self.wercker_path) as f:
            yaml_data = yaml.load(f)
            forbidden_wercker_pipelines = ['build', 'deploy']
            for pipeline in forbidden_wercker_pipelines:
                for step in yaml_data.get(pipeline).get('steps'):
                    if 'python manage.py loaddata' in str(step):
                        self.assertFalse(
                            'fixtures/dev/' in str(step),
                            'dev fixture loaddata found in {} pipeline'.
                            format(pipeline, step)
                        )
