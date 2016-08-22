#!/usr/bin/env python

import sys
import signal
import os
import logging
import argparse
import time

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

def do_check():
  logger.debug('working')
  #1/0

# Interrupt signal handler. Does nothing, just logs interruption cause and exits.
# Handles the following signals:
# SIGTERM: process termintaion, SIGTERM: terminal interruption, SIGHUP: terminal closing, SIGQUIT: process quit with dump
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
