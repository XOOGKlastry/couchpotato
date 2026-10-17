import importlib.util
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = os.path.abspath('desktop/app')
sys.path.insert(0, APP)
spec = importlib.util.spec_from_file_location('couchpotato_app', os.path.join(APP, 'app.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
import desktop_features


class FakePower:
    def __init__(self): self.calls = 0
    def schedule(self): self.calls += 1


class IdleShutdownTests(unittest.TestCase):
    def test_preference_is_off_by_default_and_persists(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'LOCALAPPDATA': directory}):
            self.assertFalse(desktop_features.idle_shutdown())
            self.assertTrue(desktop_features.idle_shutdown(True))
            self.assertTrue(desktop_features.idle_shutdown())
            self.assertFalse(desktop_features.idle_shutdown(False))

    def test_fires_once_after_four_hours_and_rearms_after_activity(self):
        power = FakePower()
        idle = [14399]
        monitor = app.IdleShutdownMonitor(power, idle=lambda: idle[0])
        with patch.object(desktop_features, 'idle_shutdown', return_value=True):
            monitor.check(); self.assertEqual(power.calls, 0)
            idle[0] = 14400; monitor.check(); monitor.check(); self.assertEqual(power.calls, 1)
            idle[0] = 0; monitor.check()
            idle[0] = 14401; monitor.check(); self.assertEqual(power.calls, 2)

    def test_disabled_setting_never_fires(self):
        power = FakePower()
        monitor = app.IdleShutdownMonitor(power, idle=lambda: 99999)
        with patch.object(desktop_features, 'idle_shutdown', return_value=False): monitor.check()
        self.assertEqual(power.calls, 0)


if __name__ == '__main__': unittest.main()
