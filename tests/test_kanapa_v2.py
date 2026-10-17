import importlib.util, json, threading, unittest, urllib.error, urllib.request
from unittest.mock import patch
s=importlib.util.spec_from_file_location('app','KanapaTV/app.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Mock:
 def __init__(self):self.calls=[]
 def key(self,v):self.calls.append(('key',v))
 def text(self,v):self.calls.append(('text',v))
 def move(self,*v):self.calls.append(('move',v))
 def click(self):self.calls.append(('click',))
 def scroll(self,v):self.calls.append(('scroll',v))
 def shutdown(self):self.calls.append(('shutdown',))
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=m.ThreadingHTTPServer(('127.0.0.1',0),m.Handler)
  cls.host='127.0.0.1:'+str(cls.server.server_port)
  cls.server.allowed_hosts={cls.host};cls.server.addresses=[]
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def setUp(self):
  m.CONTROL=Mock();m.POWER=m.PowerManager();m.ATTEMPTS.clear()
 def tearDown(self):
  if m.POWER.timer:m.POWER.timer.cancel()
 def req(self,path,data=None,token=None,origin=None):
  headers={}
  if data is not None:headers['Content-Type']='application/json'
  if token:headers['Authorization']='Bearer '+token
  if origin:headers['Origin']=origin
  r=urllib.request.Request('http://'+self.host+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(r) as v:return v.status,v.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def test_code_and_pairing(self):
  self.assertEqual(len(m.CODE),4);self.assertTrue(m.CODE.isdigit())
  with patch.object(m,'CODE','0007'):
   self.assertEqual(self.req('/pair',{'code':'0007'})[0],200)
   self.assertEqual(self.req('/pair',{'code':'7'})[0],403)
   self.assertEqual(self.req('/pair',{'code':'😀'})[0],403)
 def test_pair_rate_limit(self):
  for _ in range(5):self.assertEqual(self.req('/pair',{'code':'bad'})[0],403)
  self.assertEqual(self.req('/pair',{'code':m.CODE})[0],429)
  m.ATTEMPTS[:]=[t-301 for t in m.ATTEMPTS]
  self.assertEqual(self.req('/pair',{'code':m.CODE})[0],200)
 def test_authentication_and_confirmation(self):
  self.assertEqual(self.req('/action',{'action':'shutdown','confirmed':True})[0],401)
  self.assertEqual(self.req('/action',{'action':'shutdown'},m.TOKEN)[0],400)
  self.assertEqual(self.req('/action',{'action':'shutdown','confirmed':'true'},m.TOKEN)[0],400)
  self.assertEqual(self.req('/action',{'action':'shutdown','confirmed':True},m.TOKEN,'https://evil.example')[0],403)
  self.assertEqual(m.POWER.status()['state'],'idle')
 def test_shutdown_countdown_cancel_and_stale_timer(self):
  code,body=self.req('/action',{'action':'shutdown','confirmed':True},m.TOKEN)
  self.assertEqual(code,200);self.assertEqual(json.loads(body)['power']['state'],'countdown')
  self.assertGreaterEqual(m.POWER.status()['seconds'],29)
  generation=m.POWER.generation
  self.assertEqual(m.CONTROL.calls,[])
  self.assertEqual(self.req('/action',{'action':'cancel_shutdown'},m.TOKEN)[0],200)
  m.POWER.finish(generation)
  self.assertEqual(m.CONTROL.calls,[])
  m.POWER.schedule()
  m.POWER.finish(generation)
  self.assertEqual(m.CONTROL.calls,[])
  m.POWER.finish(m.POWER.generation)
  self.assertEqual(m.CONTROL.calls,[('shutdown',)])
  m.POWER.finish(m.POWER.generation)
  self.assertEqual(len(m.CONTROL.calls),1)
 def test_shutdown_error_reported(self):
  m.POWER.schedule()
  with patch.object(m.CONTROL,'shutdown',side_effect=OSError()):m.POWER.finish(m.POWER.generation)
  self.assertEqual(m.POWER.status()['state'],'error')
 def test_shutdown_does_not_force_close(self):
  control=object.__new__(m.Windows)
  with patch.dict(m.os.environ,{'SystemRoot':'C:\\Windows'}),patch.object(m.subprocess,'run') as run:
   run.return_value.returncode=0;control.shutdown()
   args=run.call_args.args[0]
   self.assertEqual(args[1:],['/s','/t','0']);self.assertFalse(run.call_args.kwargs['shell'])
 def test_controls_and_validation(self):
  for data in [{'action':'key','key':'enter'},{'action':'text','text':'Zażółć 😀'},{'action':'move','dx':-12,'dy':17},{'action':'click'},{'action':'scroll','delta':120}]:
   self.assertEqual(self.req('/action',data,m.TOKEN)[0],200)
  self.assertEqual(len(m.CONTROL.calls),5)
  for data in [{'action':'key','key':[]},{'action':'open','service':[]},{'action':'move','dx':100000,'dy':0},{'action':'text','text':'x'*501},{'action':'shell','command':'anything'}]:
   self.assertEqual(self.req('/action',data,m.TOKEN)[0],400)
 def test_static_files(self):
  for path in ['/','/style.css','/app.js']:self.assertEqual(self.req(path)[0],200)
  self.assertEqual(self.req('/../app.py')[0],404)
if __name__=='__main__':unittest.main(verbosity=2)
