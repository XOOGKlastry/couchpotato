"""A separate, rate-only capability for the local browser extension."""
import time, math, hmac, hashlib
RATES=(1,1.25,1.5,1.75,2,3,4)
class Bridge:
 def __init__(self):
  self.seen=0;self.client='';self.actual=None;self.has_video=False;self.serial=0;self.pending=None;self.error=''
 def state(self):
  now=time.monotonic()
  if self.pending and now-self.pending['created']>8:
   self.pending=None;self.error='Nie potwierdzono zmiany. Otwórz kartę YouTube i spróbuj ponownie.'
  connected=bool(self.client) and now-self.seen<5
  return {'connected':connected,'has_video':self.has_video if connected else False,'actual':self.actual if connected else None,'pending':self.pending['rate'] if self.pending else None,'error':self.error}
 def set_rate(self,rate):
  if type(rate) not in (int,float) or rate not in RATES:raise ValueError('Nieprawidlowa predkosc')
  state=self.state()
  if not state['connected'] or not state['has_video']:raise OSError('Otwórz film YouTube w przeglądarce z połączonym dodatkiem couchpotato.')
  self.serial+=1;self.error='';self.pending={'id':self.serial,'rate':rate,'client':self.client,'created':time.monotonic()}
 def poll(self,data):
  client=data.get('client');actual=data.get('actual');ack=data.get('ack',0);has=data.get('has_video')
  if not isinstance(client,str) or not 8<=len(client)<=64 or not client.isalnum() or type(has) is not bool or type(ack) is not int or ack<0:raise ValueError()
  if actual is not None and (type(actual) not in (int,float) or not math.isfinite(actual) or not .0625<=actual<=16):raise ValueError()
  self.state();self.seen=time.monotonic();self.client=client;self.actual=actual;self.has_video=has
  if self.pending and self.pending['client']==client and ack==self.pending['id']:
   if actual is None or abs(actual-self.pending['rate'])>.001:self.error='Odtwarzacz nie potwierdził wybranej prędkości.'
   self.pending=None
  p=self.pending
  return {'command':{'id':p['id'],'rate':p['rate']} if p and p['client']==client else None}

def extension_token(token):return hmac.new(token.encode('ascii'),b'couchpotato-youtube-rate-only-v1',hashlib.sha256).hexdigest()
