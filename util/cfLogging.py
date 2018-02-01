import logging


LOGGING_LEVEL = "DEBUG"

LOG_IN_STDOUT = True
LOG_IN_FILE = False
LOG_PATH = "..."
LOG_FILENAME = "..."

class CfLogger(object):

    @staticmethod
    def get_logger(name):
        logger = logging.getLogger(name)
        logger.setLevel(LOGGING_LEVEL)
        formatter = logging.Formatter('[%(asctime)s]  [%(levelname)5s]  [%(threadName)10s]  [%(name)10s]  %(message)s')

        if LOG_IN_FILE and LOG_PATH and LOG_FILENAME:
            file_handler = logging.FileHandler("{0}/{1}.log".format(LOG_PATH, LOG_FILENAME), mode="a")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if LOG_IN_STDOUT:
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        return logger
