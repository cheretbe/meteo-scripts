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

def datetime_as_timestamp(dt):
  unix_epoch = datetime.datetime.fromtimestamp(0)
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
    """It logs an error an returns False if DB file does not exist"""
    with mock.patch.object(check_status, 'weewx_db_file', 'sqlite_db_file') as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertEqual(ret_val, False)
    mock_logger_error.assert_called_with('Weewx DB file sqlite_db_file does not exist')

  def test_data_table_is_empty(self, mock_logger_error, mock_logger_debug):
    """It logs an error and returns False if DB file exists, but contains no records"""
    db_file_path = self.create_test_db('test1.sdb')
    with mock.patch.object(check_status, 'weewx_db_file', db_file_path) as mock_db_file:
      ret_val = check_status.do_check_db()
    self.assertEqual(ret_val, False)

  def test_data_table_no_recent_records(self, mock_logger_error, mock_logger_debug):
    db_file_path = self.create_test_db('test2.sdb', (
        (datetime_as_timestamp(datetime.datetime.now() - datetime.timedelta(minutes=30)), 14.2, 15.6),
        (datetime_as_timestamp(datetime.datetime.now() - datetime.timedelta(minutes=20)), 14.1, 15.5)
      ))
    with mock.patch.object(check_status, 'weewx_db_file', db_file_path) as mock_db_file:
      ret_val = check_status.do_check_db()
    #self.assertEqual(ret_val, False)
    #print(datetime_as_timestamp(datetime.datetime.now()))
