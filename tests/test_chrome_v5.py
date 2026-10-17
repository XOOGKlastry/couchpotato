import importlib.util,unittest
from unittest.mock import patch,Mock
spec=importlib.util.spec_from_file_location('app','KanapaTV/app.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
class Tests(unittest.TestCase):
 def setUp(self):app.CONTROL=Mock()
 def test_new_chrome_tab_and_omnibox(self):
  with patch.object(app.Path,'is_file',return_value=False),patch.object(app.shutil,'which',return_value='C:/Google/Chrome/chrome.exe'),patch.object(app.subprocess,'Popen') as launch:
   app.execute({'action':'new_chrome_tab'})
   launch.assert_called_once_with(['C:/Google/Chrome/chrome.exe','--new-tab','chrome://newtab/'],shell=False)
   self.assertEqual([c[0] for c in app.CONTROL.method_calls],['focus_chrome','shortcut'])
   app.CONTROL.shortcut.assert_called_once_with('address_bar')
 def test_chrome_missing(self):
  with patch.object(app.Path,'is_file',return_value=False),patch.object(app.shutil,'which',return_value=None),self.assertRaises(app.ActionError):app.chrome_new_tab()
  self.assertEqual(app.CONTROL.method_calls,[])
 def test_search_targets_chrome_before_typing(self):
  app.execute({'action':'chrome_search','text':'coś do obejrzenia'})
  self.assertEqual([c[0] for c in app.CONTROL.method_calls],['focus_chrome','shortcut','text','key'])
  app.CONTROL.key.assert_called_with('enter')
 def test_no_typing_when_focus_denied(self):
  app.CONTROL.focus_chrome.side_effect=app.ActionError('Denied')
  with self.assertRaises(app.ActionError):app.execute({'action':'chrome_search','text':'hello'})
  app.CONTROL.text.assert_not_called();app.CONTROL.shortcut.assert_not_called()
 def test_validate_search(self):
  for text in [[],None,'','x'*501]:
   with self.assertRaises(ValueError):app.execute({'action':'chrome_search','text':text})
  self.assertEqual(app.CONTROL.method_calls,[])
 def test_separate_fullscreen(self):self.assertEqual(app.KEYS['fullscreen'],70);self.assertEqual(app.KEYS['browser_fullscreen'],122)
if __name__=='__main__':unittest.main(verbosity=2)
