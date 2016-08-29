import mock
import unittest
import shutil
import tempfile
import os
import sqlite3
import contextlib
import datetime
import math

import check_status

# Returns current time as unix timestamp, floored to integer
# Optionally can add (or subtract) minutes to the result
def now_as_timestamp(minutes_offset=0):
  dt = datetime.datetime.now()
  if minutes_offset != 0:
    dt = dt +  datetime.timedelta(minutes=minutes_offset)
  # 01.01.1970
  unix_epoch = datetime.datetime.utcfromtimestamp(0)
  return(int(math.floor((dt - unix_epoch).total_seconds())))

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

  def create_test_db(self, db_file_name, data_records=()):
    db_file_full_path = os.path.join(self.test_dir, db_file_name)
    #print(os.path.join(self.test_dir, db_file_name))
    with sqlite3.connect(db_file_full_path) as conn:
      #c = conn.cursor()
      with contextlib.closing(conn.cursor()) as c:
        c.execute('CREATE TABLE archive (`dateTime` INTEGER NOT NULL UNIQUE PRIMARY KEY, `windSpeed` REAL, `windGust` REAL)')
        for data_record in data_records:
          #print(value)
          c.execute('INSERT INTO archive (dateTime, windSpeed, windGust) VALUES (?,?,?)', data_record)
      conn.commit()
    return(db_file_full_path)

  def test_db_file_does_not_exist(self, mock_logger_error, mock_logger_debug):
    """It logs an error and returns False if DB file does not exist"""
    with mock.patch.object(check_status, 'weewx_db_file', 'sqlite_db_file') as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertFalse(ret_val)
    mock_logger_error.assert_called_with('Weewx DB file sqlite_db_file does not exist')

  def test_data_table_is_empty(self, mock_logger_error, mock_logger_debug):
    """It logs an error and returns False if DB file exists, but contains no records"""
    db_file_path = self.create_test_db('test1.sdb')
    with mock.patch.object(check_status, 'weewx_db_file', db_file_path) as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertFalse(ret_val)
    mock_logger_error.assert_called_with('No records in the Weewx DB file for the last 15min')

  def test_data_table_no_recent_records(self, mock_logger_error, mock_logger_debug):
    """It logs an error and returns False if there are no records for the last 15min"""
    db_file_path = self.create_test_db('test2.sdb', (
        (now_as_timestamp(-30), 14.2, 15.6), # current time - 30min
        (now_as_timestamp(-20), 14.1, 15.5)  # current time - 20min
      ))
    with mock.patch.object(check_status, 'weewx_db_file', db_file_path) as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertFalse(ret_val)
    mock_logger_error.assert_called_with('No records in the Weewx DB file for the last 15min')

  def test_data_table_no_recent_wind_data(self, mock_logger_error, mock_logger_debug):
    """It logs an error and returns False if there is no wind data for the last 15min"""
    db_file_path = self.create_test_db('test3.sdb', (
        (now_as_timestamp(-30), None, 15.6), # current time - 30min
        (now_as_timestamp(-20), None, 15.5), # current time - 20min
        (now_as_timestamp(-10), None, 15.1), # current time - 10min
        (now_as_timestamp(),    None, 16.3)  # current time
      ))
    with mock.patch.object(check_status, 'weewx_db_file', db_file_path) as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertFalse(ret_val)
    mock_logger_error.assert_called_with('No wind data for the last 15min in the Weewx DB file')

  def test_data_table_recent_wind_data(self, mock_logger_error, mock_logger_debug):
    """It returns True if there is at least one wind record for the last 15min"""
    db_file_path = self.create_test_db('test4.sdb', (
        (now_as_timestamp(-30), None, 15.6), # current time - 30min
        (now_as_timestamp(-20), None, 15.5), # current time - 20min
        (now_as_timestamp(-10), 14.9, 15.1), # current time - 10min
        (now_as_timestamp(),    None, 16.3)  # current time
      ))
    with mock.patch.object(check_status, 'weewx_db_file', db_file_path) as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertTrue(ret_val)
    mock_logger_error.assert_not_called()

@mock.patch('check_status.logger.warning')
class read_reboot_timeout_FunctionalTest(unittest.TestCase):
  """Functional tests for 'read_reboot_timeout' function"""

  def setUp(self):
    # Create a temporary directory
    self.test_dir = tempfile.mkdtemp()

  def tearDown(self):
    # Remove the directory after the test
    shutil.rmtree(self.test_dir)

  def create_data_file(self, df_name, df_contents=()):
    df_full_path = os.path.join(self.test_dir, df_name)
    with open(df_full_path, 'w') as f:
      for df_line in df_contents:
        f.write(df_line)
    return(df_full_path)

  def test_file_doesnt_exist(self, mock_logger_warning):
    with mock.patch.object(check_status, 'data_file', 'non_existent_data_file') as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, None)
    mock_logger_warning.assert_not_called()

  def test_file_exists_empty(self, mock_logger_warning):
    df_full_path = self.create_data_file('test1')
    with mock.patch.object(check_status, 'data_file', df_full_path) as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, None)
    mock_logger_warning.assert_not_called()

  def test_file_exists_malformed(self, mock_logger_warning):
    df_full_path = self.create_data_file('test2', ('[section'))
    with mock.patch.object(check_status, 'data_file', df_full_path) as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, None)
    mock_logger_warning.assert_called_once()

  def test_file_exists_no_section(self, mock_logger_warning):
    df_full_path = self.create_data_file('test3', ('[section]'))
    with mock.patch.object(check_status, 'data_file', df_full_path) as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, None)
    mock_logger_warning.assert_not_called()

  def test_file_exists_no_value(self, mock_logger_warning):
    df_full_path = self.create_data_file('test4', (
        '[check_status]\n',
        'other_parameter=other_value'
      ))
    with mock.patch.object(check_status, 'data_file', df_full_path) as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, None)
    mock_logger_warning.assert_not_called()

  def test_file_exists_has_correct_value(self, mock_logger_warning):
    df_full_path = self.create_data_file('test5', (
        '[check_status]\n',
        'reboot_timeout=30'
      ))
    with mock.patch.object(check_status, 'data_file', df_full_path) as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, 30)
    mock_logger_warning.assert_not_called()

  def test_file_exists_has_incorrect_value(self, mock_logger_warning):
    df_full_path = self.create_data_file('test6', (
        '[check_status]\n',
        'reboot_timeout=wrong-int'
      ))
    with mock.patch.object(check_status, 'data_file', df_full_path) as mock_config_file:
      ret_val = check_status.read_reboot_timeout()
    self.assertEqual(ret_val, None)
    mock_logger_warning.assert_called_once()

@mock.patch('check_status.logger')
@mock.patch('check_status.read_reboot_timeout')
@mock.patch('check_status.get_system_uptime')
@mock.patch('check_status.os.system')
class do_reboot_UnitTest(unittest.TestCase):
  """Unit tests for 'do_reboot' function"""
  def test_reboot_is_allowed(self, mock_os_system, mock_get_system_uptime,
      mock_read_reboot_timeout, mock_logger):
    mock_read_reboot_timeout.return_value = 15
    mock_get_system_uptime.return_value = datetime.timedelta(minutes=31)
    check_status.do_reboot()
    mock_os_system.assert_called_with('sudo reboot')

    mock_read_reboot_timeout.return_value = None
    mock_get_system_uptime.return_value = datetime.timedelta(minutes=16)
    check_status.do_reboot()
    mock_os_system.assert_called_with('sudo reboot')

class reboot_sequence_IntegrationTest(unittest.TestCase):
  @mock.patch('check_status.logger')
  @mock.patch('check_status.read_reboot_timeout')
  @mock.patch('check_status.get_system_uptime')
  @mock.patch('check_status.os.system')
  def mock_reboot(self, prev_reboot_timeout, uptime, mock_os_system,
      mock_get_system_uptime, mock_read_reboot_timeout, mock_logger):
    mock_read_reboot_timeout.return_value = prev_reboot_timeout
    mock_get_system_uptime.return_value = datetime.timedelta(minutes=uptime)
    check_status.do_reboot()
    mock_os_system.assert_called_with('sudo reboot')
    # print(prev_reboot_timeout)

  def run_sequence(self, initial_reboot_timeout, call_sequence):
    for call in call_sequence:
      print(call['uptime'])


  def test_helper(self):
    # print("there you go")
    # self.mock_reboot(prev_reboot_timeout=None, uptime=122)
    # self.mock_reboot(None, 122)
    # self.run_sequence("aaa")
    self.run_sequence(initial_reboot_timeout=None, call_sequence=(
        {'uptime': 15, 'expect_reboot': False},
        {'uptime': 30, 'expect_reboot': False},
        {'uptime': 45, 'expect_reboot': True}
      ))
