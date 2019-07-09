import logging
import datetime

#Use logger variable to log stuff
#TODO abstract some of this. Maybe into a class, or a group of methods

class Logger:  #TODO add a guild tag in log_format. Figure it out later i guess

    logger = None

    @classmethod
    def setup_logger(cls):
        log_format = '[%(levelname)s] (%(asctime)s) - %(message)s'  #TODO add guild ID
        logging.basicConfig(filename='../logs/{}.log'.format(datetime.date.today()),
                            level=logging.WARNING,
                            format=log_format,
                            filemode='w')
        cls.logger = logging.getLogger()
        cls.logger.info('Logger set up successfully.')

    @classmethod
    def debug(cls, *msg):
        for m in msg:
            cls.logger.debug(m)

    @classmethod
    def info(cls, *msg):
        for m in msg:
            cls.logger.info(m)

    @classmethod
    def warning(cls, *msg):
        for m in msg:
            cls.logger.warning(m)

    @classmethod
    def error(cls, *msg):
        for m in msg:
            cls.logger.error(m)

    @classmethod
    def critical(cls, *msg):
        for m in msg:
            cls.logger.critical(m)

Logger.setup_logger()
