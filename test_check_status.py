import mock
import unittest
import shutil
import tempfile

import check_status

@mock.patch('check_status.logger.debug')
@mock.patch('check_status.logger.error')
class do_check_db_FunctionalTest(unittest.TestCase):
  """Functional tests for 'do_check_db' function"""

  def setUp(self):
    # Create a temporary directory
    self.test_dir = tempfile.mkdtemp()

  def tearDown(self):
    # Remove the directory after the test
    shutil.rmtree(self.test_dir)

  def test_db_file_does_not_exist(self, mock_logger_error, mock_logger_debug):
    """It logs an error an returns False if DB file does not exist"""
    with mock.patch.object(check_status, 'weewx_db_file', 'sqlite_db_file') as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertEqual(ret_val, False)
    mock_logger_error.assert_called_with('Weewx DB file sqlite_db_file does not exist')
