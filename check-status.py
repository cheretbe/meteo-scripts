#!/usr/bin/env python

import sys
import logging

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
#stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setLevel(logging.INFO)
logger.addHandler(stdout_handler)

# Stderr handler. Outputs warnings, errors and critical messages to stderr
stdout_handler = logging.StreamHandler(sys.stderr)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
stdout_handler.setLevel(logging.WARNING)
logger.addHandler(stdout_handler)

def main():
  logger.debug('debug message')
  logger.info('info message')
  logger.warning('warning message')
  logger.error('error message')
  logger.critical('critical message')

if __name__ == '__main__':
    exit(main())
