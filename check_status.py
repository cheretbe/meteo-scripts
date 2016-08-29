#!/usr/bin/env python

import sys
import signal
import os
import logging
import argparse
import time
import subprocess
import sqlite3
import contextlib
import datetime
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser  # ver. < 3.0

# Filter class to log only messages with level lower than specified
# http://stackoverflow.com/questions/2302315/how-can-info-and-debug-logging-message-be-sent-to-stdout-and-higher-level-messag/31459386#31459386
class LevelLessThanFilter(logging.Filter):
    def __init__(self, exclusive_maximum, name=""):
        super(LevelLessThanFilter, self).__init__(name)
        self.max_level = exclusive_maximum

    def filter(self, record):
        # Non-zero return means we log this message
        return 1 if record.levelno < self.max_level else 0

# Root logger. Accepts all levels of messages, but doesn't output anything.
# Additional handlers will take care of that.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Stdout handler. By default echoes only info messages. Optionally outputs
# debug messages if --debug option is set
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
stdout_handler.addFilter(LevelLessThanFilter(logging.WARNING))
stdout_handler.setLevel(logging.INFO)
logger.addHandler(stdout_handler)

# Stderr handler. Outputs warnings, errors and critical messages to stderr
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
stderr_handler.setLevel(logging.WARNING)
logger.addHandler(stderr_handler)

data_file = os.path.expanduser('~/.check-status')
signals_to_handle = {signal.SIGTERM:'SIGTERM', signal.SIGINT:'SIGINT', signal.SIGHUP:'SIGHUP', signal.SIGQUIT:'SIGQUIT'}
weewx_db_file = '/var/lib/weewx/weewx.sdb'
reboot_timeouts_map = {
  # previous_timeout: current_timeout
  None: 15,
  15:   30,
  30:   180, # 3h
  180:  720, # 3h, 12h
  720:  720  # 12h
}

def get_system_uptime():
  # proc/uptime contains two numbers: the uptime of the system (seconds), and the
  # amount of time spent in idle process (seconds). We read the first number and
  # convert it to timedelta, rounding to seconds
  with open('/proc/uptime', 'r') as f:
    return(datetime.timedelta(seconds=round(float(f.readline().split()[0]))))

def read_reboot_timeout():
  reboot_timeout = None
  try:
    if os.path.isfile(data_file):
      config_data = ConfigParser()
      config_data.read(data_file)
      if config_data.has_section('check_status'):
        if config_data.has_option('check_status', 'reboot_timeout'):
          reboot_timeout = int(config_data.get('check_status', 'reboot_timeout'))
  except Exception as e:
    logger.warning('Error reading data from {0}: {1}'.format(data_file, str(e)))
  return(reboot_timeout)

def write_reboot_timeout(reboot_timeout):
  config_data = ConfigParser()
  config_data.add_section('check_status')
  config_data.set('check_status', 'reboot_timeout', str(reboot_timeout))
  with open(data_file, "w") as f:
    config_data.write(f)

def do_ping():
  """Pings several targets to check network connectivity.

     Fails only if all the targets have failed. Successful ping of even one of the targets
     is considered a success. Lost packets for one target considered as target fail.

     Returns:
       bool: The return value. True for success, False otherwise.
  """
  ping_result = False
  # We use DNS names instead of IPs for Google and OpenDNS NS to ensure that DNS resolution works
  for ping_target in ['google-public-dns-a.google.com', 'resolver1.opendns.com', 'ya.ru']:
    # Create ping subprocess
    ping_subproc = subprocess.Popen(["ping", "-c 3", ping_target], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # Wait for exit and get output
    for ping_output_line in ping_subproc.communicate()[0].splitlines():
      logger.debug(ping_output_line)
    logger.debug('ping return code: {0}'.format(ping_subproc.returncode))
    # Check exit code
    if ping_subproc.returncode == 0:
      ping_result = True
    else:
      logger.warning('{0}: ping attempt has failed'.format(ping_target))

  if not(ping_result):
    logger.error('All ping attempts have failed')
  return(ping_result)

def do_check_db():
  """Checks wind records presence in the Weewx DB.

     Returns True if there is at least one valid (non-NULL) wind record with
     timestamp within last 15 minutes.

     Returns:
       bool: The return value. True for success, False otherwise.
  """
  logger.debug('Querying Weewx DB file {0}'.format(weewx_db_file))
  if not(os.path.isfile(weewx_db_file)):
    logger.error('Weewx DB file {0} does not exist'.format(weewx_db_file))
    return(False)

  with sqlite3.connect(weewx_db_file) as conn:
    with contextlib.closing(conn.cursor()) as cursor:
      wind_records = cursor.execute(
        'SELECT windSpeed, datetime(dateTime, "unixepoch", "localtime") AS dt, ' \
        'dateTime FROM archive WHERE dt >= datetime("now", "-15 Minute", "localtime") ' \
        'ORDER BY dt DESC').fetchall()

      if len(wind_records) == 0:
        logger.error('No records in the Weewx DB file for the last 15min')
        return(False)

      has_wind_speed = False
      for wind_record in wind_records:
        logger.debug(wind_record)
        if wind_record[0] != None:
          has_wind_speed = True
          break
      if not(has_wind_speed):
        logger.error('No wind data for the last 15min in the Weewx DB file')
        return(False)

  return(True)

def do_reboot():
  previous_reboot_timeout = read_reboot_timeout()
  try:
    reboot_timeout_minutes = reboot_timeouts_map[previous_reboot_timeout]
  except:
    reboot_timeout_minutes = reboot_timeouts_map[None]
  logger.debug('previous_reboot_timeout: {0}, reboot_timeout_minutes: {1}'.format(
    previous_reboot_timeout, reboot_timeout_minutes))
  #print('previous_reboot_timeout: {0}, reboot_timeout_minutes: {1}'.format(
  #  previous_reboot_timeout, reboot_timeout_minutes))

  uptime = get_system_uptime()
  reboot_timeout = datetime.timedelta(minutes=reboot_timeout_minutes)
  if uptime > reboot_timeout:
    write_reboot_timeout(reboot_timeout_minutes)
    logger.warning('*** Rebooting the system ***')
    os.system('sudo reboot')
  else:
    logger.info('System uptime ({0}) is less then the minimum, allowed before ' \
      'reboot ({1}). Skipping reboot'.format(uptime, reboot_timeout))

  # with open(data_file, 'w') as config_file:
  #   config_data.write(config_file)

def do_check():
  logger.debug('-- Starting check --')
  uptime = get_system_uptime()
  if uptime < datetime.timedelta(minutes=5):
    logger.info("System uptime is less than 5 minutes ({0}). Skipping check".format(uptime))
    return()

  check_result = do_ping()
  # Can't use `and` here because of boolean short-circuit evaluation
  if not do_check_db():
    check_result = False

  if check_result:
    logger.debug('Check result: Ok')
    #TODO: Reset reboot cycle record in data_file
  else:
    logger.info('Check result: Failure')
    do_reboot()

# Interrupt signal handler. Does nothing, just logs interruption cause and exits.
# Handles the following signals:
# SIGTERM: process termintaion, SIGINT: terminal interruption, SIGHUP: terminal closing, SIGQUIT: process quit with dump
def signal_handler(signum = None, frame = None):
  logger.info('Caught signal {0} ({1}), exiting'.format(signum, signals_to_handle[signum]))
  sys.exit(0)

def main():
  exit_code = 0
  try:
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', default=False,
                        help='Increase logging verbosity')
    parser.add_argument('-s', '--sleep-time', dest='sleep_time', type=int, default=300,
			help='Sleep time between checks in seconds (default: %(default)d)')
    options = parser.parse_args()

    if options.debug:
      stdout_handler.setLevel(logging.DEBUG)

    logger.info('Starting monitoring script')
    logger.debug('Script location: {0}'.format(os.path.realpath(__file__)))
    logger.debug('Data file: {0}'.format(data_file))

    for sig in signals_to_handle:
      signal.signal(sig, signal_handler)

    while True:
      do_check()
      time.sleep(options.sleep_time)

  except Exception as e:
    logger.exception("Unhandled exception")
    exit_code = 1

  return (exit_code)

if __name__ == '__main__':
  sys.exit(main())
