import importlib.util
import unittest

class DeploymentTests(unittest.TestCase):
    def test_deployment_config_requires_https_origin_and_safe_port(self):
        self.assertIsNotNone(importlib.util.find_spec('deploy'), 'deployment launcher required')
        from deploy import configuration
        origin, port = configuration({'PUBLIC_ORIGIN': 'https://demo.example', 'PORT': '10000'})
        self.assertEqual((origin, port), ('https://demo.example', 10000))
        for env in [{}, {'PUBLIC_ORIGIN': 'http://demo.example'},
                    {'PUBLIC_ORIGIN': 'https://demo.example/'},
                    {'PUBLIC_ORIGIN': 'https://demo.example', 'PORT': '8765'},
                    {'PUBLIC_ORIGIN': 'https://demo.example', 'PORT': '0'},
                    {'PUBLIC_ORIGIN': 'https://demo.example', 'PORT': '10000;bad'}]:
            with self.subTest(env=env), self.assertRaises(ValueError):
                configuration(env)
