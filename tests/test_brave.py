import importlib.util,unittest
from unittest.mock import patch
s=importlib.util.spec_from_file_location('app','KanapaTV/app.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_url_validation(self):
  for url in ['file:///x','javascript:alert(1)','--command','http://example.com','https://user:pass@example.com','https://example.com/\n',None,[], 'https://']:
   with self.subTest(url=url),self.assertRaises(ValueError):m.brave_open(url)
 def test_brave_only(self):
  with patch.object(m.Path,'is_file',return_value=False),patch.object(m.shutil,'which',return_value='C:/Brave/brave.exe'),patch.object(m.subprocess,'Popen') as p:
   m.brave_open('https://example.com/watch?q=test')
   p.assert_called_once_with(['C:/Brave/brave.exe','--new-tab','https://example.com/watch?q=test'],shell=False)
 def test_missing_brave(self):
  with patch.object(m.Path,'is_file',return_value=False),patch.object(m.shutil,'which',return_value=None),self.assertRaises(FileNotFoundError):m.brave_open('https://example.com')
 def test_shortcuts_release_modifiers(self):
  control=object.__new__(m.Windows)
  class User:
   def __init__(self):self.events=[]
   def keybd_event(self,*args):self.events.append(args)
  control.u=User()
  for name,keys in m.SHORTCUTS.items():
   control.u.events=[];control.shortcut(name)
   self.assertEqual(control.u.events,[(k,0,0,0) for k in keys]+[(k,0,2,0) for k in reversed(keys)])
if __name__=='__main__':unittest.main(verbosity=2)
