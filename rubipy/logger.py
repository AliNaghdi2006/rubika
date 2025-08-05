import logging
from sys import stderr

logger = logging.getLogger('rubipy')

formatter = logging.Formatter(
    '%(asctime)s | (%(levelname)s | %(name)s | %(filename)s:%(lineno)d) | %(message)s'
)

console_output_handler = logging.StreamHandler(stderr)
console_output_handler.setFormatter(formatter)

logger.addHandler(console_output_handler)
logger.setLevel(logging.DEBUG)