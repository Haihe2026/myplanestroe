"""Entry composition: new wrapper retains the previously deployed entry."""
import importlib.util
from pathlib import Path
import runpy
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

class EntryTests(unittest.TestCase):
    def test_entry_hooks_prior_listing_wrapper_then_chains_metered_entry(self):
        from gemini_support import Support
        called=[]
        listing=ModuleType('listing_gateway')
        listing.wrap=lambda parent,store,server:(called.append(('old',parent,store,server)) or 'prior-parent')
        fake_support=ModuleType('gemini_support')
        fake_support.install=lambda parent,store,server:(called.append(('new',parent,store,server)) or 'support-parent')
        old_path=list(sys.path)
        try:
            with patch.dict(sys.modules,{'listing_gateway':listing,'gemini_support':fake_support}),patch('runpy.run_path') as tail:
                spec=importlib.util.spec_from_file_location('entry_under_test',Path(__file__).with_name('run_shared.py'))
                entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
                tail.assert_called_once_with('/opt/skill-platform/metered-page-20261105/run_shared.py',run_name='__main__')
                self.assertEqual(listing.wrap('original-parent','store','server'),'support-parent')
                self.assertEqual(called,[('old','original-parent','store','server'),('new','prior-parent','store','server')])
        finally:sys.path[:]=old_path

if __name__=='__main__':unittest.main()
