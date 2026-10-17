import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
s = importlib.util.spec_from_file_location('app', 'KanapaTV/app.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)

class Pairing(unittest.TestCase):
    def test_survives_restart_and_preserves_leading_zeros(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m.secrets, 'randbelow', return_value=7):
                first = m.load_pairing(d)
            self.assertEqual(first[0], '0007')
            self.assertEqual(first, m.load_pairing(d))
            self.assertGreaterEqual(len(first[1]), 40)
    def test_corrupt_state_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'pairing.json'
            for value in ['{broken', '[]', '{"code":"1234","token":"short"}']:
                p.write_text(value)
                with self.assertRaises(ValueError): m.load_pairing(d)
                self.assertEqual(p.read_text(), value)
    def test_revocation_changes_secret(self):
        with tempfile.TemporaryDirectory() as d:
            first = m.load_pairing(d)
            (Path(d)/'pairing.json').unlink()
            self.assertNotEqual(first[1], m.load_pairing(d)[1])
    def test_new_tab_mouse_button_is_released(self):
        control = object.__new__(m.Windows); control.u = Mock()
        with patch.object(m, 'CONTROL', control):
            m.execute({'action':'open_link_tab'})
        self.assertEqual([c.args[0] for c in control.u.mouse_event.call_args_list], [0x20, 0x40])

if __name__ == '__main__': unittest.main()
