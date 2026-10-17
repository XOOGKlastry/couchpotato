import unittest,sys,time
sys.path.insert(0,'KanapaTV')
from youtube_bridge import Bridge,extension_token
class Tests(unittest.TestCase):
 def test_confirmation(self):
  b=Bridge()
  with self.assertRaises(OSError):b.set_rate(2)
  p=dict(client='client123',actual=1,has_video=True,ack=0)
  b.poll(p)
  for rate in (1,1.25,1.5,1.75,2,3,4):
   b.set_rate(rate);cmd=b.poll(p)['command'];self.assertEqual(cmd['rate'],rate)
   self.assertIsNone(b.poll({**p,'client':'another123'})['command'])
   b.poll({**p,'actual':rate,'ack':cmd['id']});self.assertIsNone(b.state()['pending']);self.assertEqual(b.state()['actual'],rate)
 def test_rejection_and_timeout(self):
  b=Bridge();p=dict(client='client123',actual=1,has_video=True,ack=0);b.poll(p)
  for rate in (True,0,2.5,float('nan')):
   with self.assertRaises(ValueError):b.set_rate(rate)
  b.set_rate(4);b.poll({**p,'ack':b.serial});self.assertTrue(b.state()['error'])
  b.set_rate(3);b.pending['created']-=10;self.assertIsNone(b.state()['pending']);self.assertTrue(b.state()['error'])
  with self.assertRaises(ValueError):b.poll({**p,'actual':float('nan')})
 def test_capability(self):
  t='a'*64;self.assertNotEqual(t,extension_token(t));self.assertEqual(extension_token(t),extension_token(t));self.assertNotEqual(extension_token(t),extension_token('b'*64))
if __name__=='__main__':unittest.main()

import test_kanapa_v2 as base,json
class Endpoints(base.Tests):
 def test_extension_is_rate_only(self):
  m=base.m;origin='chrome-extension://'+'a'*32
  status,body=self.req('/extension/pair',{'code':m.CODE},origin=origin)
  self.assertEqual(status,200);token=json.loads(body)['token'];self.assertNotEqual(token,m.TOKEN)
  self.assertEqual(self.req('/action',{'action':'key','key':'enter'},token)[0],401)
  p=dict(client='client123',actual=1,has_video=True,ack=0)
  self.assertEqual(self.req('/extension/poll',p,m.TOKEN,origin)[0],401)
  self.assertEqual(self.req('/extension/poll',p,token,origin)[0],200)
  self.assertEqual(self.req('/extension/poll',p,token,'https://example.com')[0],403)
