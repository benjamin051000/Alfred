import datetime
import logging


class Logger:

    logger = None
    output_logs = True

    @classmethod
    def setup_logger(cls):
        log_format = '[%(levelname)s] (%(asctime)s) - %(message)s'  # TODO add guild ID
        date = datetime.datetime.now().strftime('%Y-%m-%d-%H.%M.%S')  # TODO clean up
        logging.basicConfig(filename=f'../logs/{date}.log',
                            level=logging.INFO,  # specify in config.ini?
                            format=log_format,
                            filemode='w')
        cls.logger = logging.getLogger()
        cls.logger.info('Logger set up successfully.')

    @classmethod
    def debug(cls, *msg):  # TODO review this logging style
        for m in msg:
            cls.logger.debug(m)
        if cls.output_logs:  # TODO This is jank. Fix at some point
            print(' '.join(msg))

    @classmethod
    def info(cls, *msg):
        for m in msg:
            cls.logger.info(m)
        if cls.output_logs:
            print(' '.join(msg))

    @classmethod
    def warning(cls, *msg):
        for m in msg:
            cls.logger.warning(m)
        if cls.output_logs:
            print(' '.join(msg))

    @classmethod
    def error(cls, *msg):
        for m in msg:
            cls.logger.error(m)
        if cls.output_logs and type(msg) is str:
            print(' '.join(msg))

    @classmethod
    def critical(cls, *msg):
        for m in msg:
            cls.logger.critical(m)
        if cls.output_logs:
            print(' '.join(msg))

Logger.setup_logger()
