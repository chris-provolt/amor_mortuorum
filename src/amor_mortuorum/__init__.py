import logging

# Configure a default logger for the package.
# Applications embedding this package can override configuration as needed.
logging.getLogger(__name__).addHandler(logging.NullHandler())
