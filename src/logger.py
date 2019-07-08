import logging
import datetime

#Use logger variable to log stuff
#TODO abstract some of this. Maybe into a class, or a group of methods

class Logger:  #TODO add a guild tag in log_format. Figure it out later i guess

    logger = None

    @classmethod
    def setup_logger(cls):
        log_format = '%(levelname)s %(asctime)s - %(message)s'
        logging.basicConfig(filename='../logs/{}.log'.format(datetime.date.today()),
                            level=logging.INFO,
                            format=log_format,
                            filemode='w')
        cls.logger = logging.getLogger()
        cls.logger.info('Logger set up successfully.')

    @classmethod
    def debug(cls, msg):
        cls.logger.debug(msg)

    @classmethod
    def info(cls, msg):
        cls.logger.info(msg)

    @classmethod
    def warning(cls, msg):
        cls.logger.warning(msg)

    @classmethod
    def error(cls, msg):
        cls.logger.error(msg)

    @classmethod
    def critical(cls, msg):
        cls.logger.critical(msg)