import importlib.util, unittest, struct, zlib
from unittest.mock import patch, Mock
import test_kanapa_v2 as base
m=base.m
class ExtraEndpoints(base.Tests):
 def test_preview_requires_auth_and_never_writes_files(self):
  with patch.object(m.desktop_features,'bounds',return_value=[0,0,1920,1080]), patch.object(m.desktop_features,'capture',return_value=b'png') as capture:
   self.assertEqual(self.req('/preview',{})[0],401)
   capture.assert_not_called()
   self.assertEqual(self.req('/preview',{},m.TOKEN),(200,b'png'))
   capture.assert_called_once()
 def test_preview_error_and_preferences(self):
  with patch.object(m.desktop_features,'bounds',return_value=[0,0,1920,1080]), patch.object(m.desktop_features,'capture',side_effect=OSError()):
   self.assertEqual(self.req('/preview',{},m.TOKEN)[0],503)
  with patch.object(m.desktop_features,'startup',return_value=(True,True)) as startup:
   self.assertEqual(self.req('/preferences',{'startup':True})[0],401)
   self.assertEqual(self.req('/preferences',{'startup':'yes'},m.TOKEN)[0],400)
   startup.assert_not_called()
   self.assertEqual(self.req('/preferences',{'startup':False},m.TOKEN)[0],200)
   startup.assert_called_once_with(False)
class PNG(unittest.TestCase):
 def test_rgb_and_dimensions(self):
  raw=m.desktop_features.png_rgb(2,1,b'\xff\0\0\0\xff\0')
  self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n');self.assertEqual(struct.unpack('!II',raw[16:24]),(2,1))
  offset=8
  while offset<len(raw):
   n=struct.unpack('!I',raw[offset:offset+4])[0];kind=raw[offset+4:offset+8];data=raw[offset+8:offset+8+n]
   self.assertEqual(zlib.crc32(kind+data)&0xffffffff,struct.unpack('!I',raw[offset+8+n:offset+12+n])[0])
   if kind==b'IDAT':self.assertEqual(zlib.decompress(data),b'\0\xff\0\0\0\xff\0')
   offset+=n+12
if __name__=='__main__':unittest.main()
