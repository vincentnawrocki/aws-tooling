"""Specific logging Handler class relative to TQDM progress bar printing."""

import logging
import tqdm

class TqdmLoggingHandler(logging.Handler):
    """Special class to handle logging using tqdm progress bar.

    Arguments:
        logging {[type]} -- [description]

    """
    def emit(self, record):
        """Actually manages logs.

        Arguments:
            record {str} -- Record to print

        """
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
LOG.addHandler(TqdmLoggingHandler())
