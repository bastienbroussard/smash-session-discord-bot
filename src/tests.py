import unittest

from main import *
from actions import *


me = User({
    'id': 240179781205753857,
    'name': 'BB',
    'discriminator': '9422',
    'consoles': 1,
    'screens': 1,
    'adapters': 0
})


class Join(unittest.TestCase):
    def test_join_session_already_host(self):
        pass

    def test_join_session_already_participant(self):
        pass

    def test_join_session_full(self):
        pass


if __name__ == '__main__':
    unittest.main()
