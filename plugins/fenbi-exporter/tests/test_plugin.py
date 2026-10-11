import json
import unittest
from pathlib import Path
PLUGIN = Path(__file__).resolve().parents[1]
ROOT = PLUGIN.parents[1]


class PackageTests(unittest.TestCase):
    def test_manifests_and_runtime_are_portable(self):
        portable = json.loads((PLUGIN / 'plugin.json').read_text('utf-8'))
        compat = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text('utf-8'))
        self.assertEqual(portable['name'], 'fenbi-exporter')
        self.assertEqual(portable['version'], compat['version'])
        self.assertEqual(portable['extensions']['com.openai']['interface'], compat['interface'])
        self.assertLessEqual(len(compat['interface']['shortDescription']), 30)
        self.assertTrue((PLUGIN / 'skills/fenbi-export/SKILL.md').exists())
        self.assertTrue((PLUGIN / compat['interface']['logo']).exists())
        self.assertNotIn('C:\\Users', json.dumps(portable))

    def test_catalog(self):
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text('utf-8'))
        entry = next(x for x in catalog['plugins'] if x['name'] == 'fenbi-exporter')
        self.assertEqual(entry['source']['path'], './plugins/fenbi-exporter')
