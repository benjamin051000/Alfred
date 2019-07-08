import discord
import asyncio
from discord.ext import commands
from discord.voice_client import VoiceClient
import sys, traceback
import configloader as cfload

print("Loading config data...\n")
cfload.read("../config.ini")

#######################    Begin Loading Process   ################################
startup_extensions = cfload.configSectionMap("Startup")["startup_extensions"].split()
command_prefix = cfload.configSectionMap("Commands")["command_prefix"]

bot = commands.Bot(command_prefix = commands.when_mentioned_or(command_prefix), description = cfload.configSectionMap("Startup")["description"])

print(bot.description)

#Load extensions
if __name__ == "__main__":
    print("\nLoading extensions...")
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
            print(f"Extension \'{extension}\' loaded.")
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

@bot.event
async def on_ready():
    print("\nConnected to Discord as", bot.user.name, "- ID ", bot.user.id)
    print("Alfred II loaded successfully.\n______________________________\n")
    #await bot.change_presence(activity = discord.Activity(name = "", type = 2)) #type: 0-playing a game, 1-live on twitch, 2-listening, 3-watching

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author == bot.user and message.content.startswith(command_prefix):
        return
    #hello
    if not set(message.content.upper().split(' ')).isdisjoint(("HELLO", "HI", "HEY", "GREETINGS", "SALUTATIONS", "YO")): #Magically checks for any of the greetings in message
        await message.add_reaction("\U0001F44B") #waving hand

###################################################################################
bot.run(cfload.configSectionMap("Startup")["token"])
