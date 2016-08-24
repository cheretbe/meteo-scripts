#!/usr/bin/env python

import sys
import signal
import os
import logging
import argparse
import time
import subprocess
import sqlite3

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
  db_check_result = False

  if os.path.isfile(weewx_db_file):
    with sqlite3.connect(weewx_db_file) as conn:
      last_record_time = conn.cursor().execute('SELECT MAX(dateTime) FROM archive').fetchone()
      #print(last_record_time)
      print(last_record_time[0])
      #datetime.datetime.utcfromtimestamp(1472046180)
      if last_record_time[0] != None:
        db_check_result = True
      #last_data = conn.cursor().execute('select datetime(dateTime, "unixepoch", "localtime") as dt, windSpeed, windGust from archive order by dt desc limit 10').fetchall()
      #print(type(last_data))
  else:
    logger.error('Weewx DB file {0} does not exist'.format(weewx_db_file))
  return(db_check_result)

def do_check():
  logger.debug('Starting check')
  #do_ping()
  do_check_db()
  #logger.debug(ping_targets)
  #1/0

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
