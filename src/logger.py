import discord
from discord.ext import commands
import logging
import datetime

class Logger:#(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setupLogger()

    def setupLogger(self):
        '''Creates a log in INFO mode, overwrites file unless the day changes.'''
        LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig( filename = "..\\logs\\{}.log".format(datetime.date.today()),
        level = logging.INFO, format = LOG_FORMAT, filemode = "w" )
        logger = logging.getLogger()
        logger.info("Logger set up successfully.")





# def setup(bot):
#     bot.add_cog(Logger(bot))
