import asyncio
import enum
import random

import discord
from discord.ext import commands

import configloader as cfload


class GameState(enum.Enum):
    init = 0
    lobby = 1
    startgame = 2
    ingame = 3


class Chameleon(commands.Cog):
    """ A discord remake of The Chameleon (card game). """

    MAX_PLAYERS = 8

    def __init__(self, bot, command_prefix):
        self.bot = bot
        self.command_prefix = command_prefix
        self.gamestate: GameState = GameState.init
        self.lobby = []  # Holds the names of the people in the lobby.
        self.category = None  # Points to category created.

    # @commands.Cog.listener('on_message')
    # async def on_message(self, message: discord.Message):
    #     if message.author == self.bot.user or message.content.startswith(self.command_prefix):
    #         return

    @commands.Cog.listener('on_reaction_add')
    async def on_reaction_add(self, reaction: discord.Reaction, user):
        if user == reaction.message.author:  # which is the bot
            return

        if self.gamestate == GameState.lobby:
            if reaction.emoji == '➕':
                channel = reaction.message.channel
                if self.gamestate == GameState.lobby:
                    if len(self.lobby) >= Chameleon.MAX_PLAYERS:
                        await channel.send(f"Sorry, {user}, the game is full.")
                    else:
                        self.lobby.append(user)
                        await channel.send(f'{user} is in!', delete_after=3)
                        await self.update_lobby_embed(reaction.message)

            elif reaction.emoji == '▶':
                # Set up the game
                self.gamestate = GameState.startgame

                guild = reaction.message.channel.guild
                self.category = await self.init_game_channels(guild)

                gametc = self.category.text_channels[0]
                await gametc.send('Welcome to the Chameleon! You have been moved to a private room to play.')
                await gametc.send('<TODO Rules>')
                sent_msg: discord.Message = await gametc.send('Once everyone is ready, press ▶ to start the game!')
                await sent_msg.add_reaction('▶')

        elif self.gamestate == GameState.startgame:
            if reaction.emoji == '▶':
                self.gamestate = GameState.ingame
                await self.gameloop()




    @commands.Cog.listener('on_reaction_remove')
    async def on_reaction_remove(self, reaction: discord.Reaction, user):
        if user == reaction.message.author:  # which is the bot
            return

        if self.gamestate == GameState.lobby:
            if reaction.emoji == '➕':
                channel = reaction.message.channel
                try:
                    # self.lobby.remove(user)
                    await channel.send(f'{user} left the lobby.', delete_after=3)
                    await self.update_lobby_embed(reaction.message)
                except ValueError:
                    pass

    @commands.group(invoke_without_command=True)
    async def chameleon(self, ctx):
        """ Generate a lobby for players to join. """
        if self.gamestate != GameState.init:
            await ctx.send("A game is already in play. Use a subcommand.")
        else:
            self.gamestate = GameState.lobby
            embed = discord.Embed(title="The Chameleon", colour=discord.Colour(0xe7d066),
                                  description="Click the \'➕\' button below this message to join/leave the lobby."
                                              "Press \'▶\' to start the game with the people in the lobby.")

            embed.add_field(name="__Players in lobby__", value='-', inline=True)
            # embed.add_field(name=f'{len(self.lobby)}/{Chameleon.MAX_PLAYERS}\n', value='-', inline=True)

            sent_msg = await ctx.send(embed=embed)
            await sent_msg.add_reaction('➕')
            await sent_msg.add_reaction('▶')

    async def update_lobby_embed(self, message: discord.Message):
        new_embed: discord.Embed = message.embeds[0]

        # Add player names
        names = [e.name for e in self.lobby]

        # half = len(self.lobby) // 2
        # first_half = '\n'.join(names[:half // 2]) or '-'
        # second_half = '-' if len(self.lobby) < 2 else '\n'.join(names[half // 2:])

        new_embed.set_field_at(
            0,
            name=f"__Players in lobby__({len(self.lobby)}/{Chameleon.MAX_PLAYERS})",
            value='\n'.join(names), inline=True
        )
        # new_embed.set_field_at(1, name=f'{len(self.lobby)}/{Chameleon.MAX_PLAYERS}\n', value=second_half, inline=True)

        await message.edit(embed=new_embed)

    @chameleon.command()
    async def join(self, ctx):
        """ Join the lobby for the chameleon game. """
        if self.gamestate == GameState.lobby:
            if len(self.lobby) >= Chameleon.MAX_PLAYERS:
                await ctx.send(f"Sorry, {ctx.author}, the game is full.")
            else:
                self.lobby.append(ctx.author)
                await ctx.send(f'Added {ctx.author} to the lobby.')
                # TODO update embed or deprecate this command

    @chameleon.command()
    async def leave(self, ctx):
        """ Leave the lobby. """
        if self.gamestate == GameState.lobby:
            try:
                self.lobby.remove(ctx.author)
                # TODO update embed here or deprecate this command
            except ValueError:
                pass

    @chameleon.command()
    async def start(self, ctx):
        """ Starts the game with the players in the lobby. """
        await ctx.send(f"Starting game...")
        self.gamestate = GameState.startgame

    async def init_game_channels(self, guild: discord.Guild):
        category = await guild.create_category('The Chameleon')
        await guild.create_text_channel('chameleon-general', category=category)
        gamevc = await guild.create_voice_channel('The Chameleon', category=category)
        for player in self.lobby:
            # player is a User. Get it as a member.
            member: discord.Member = guild.get_member(player.id)
            await member.move_to(gamevc)
        return category

    async def destroy_game_channels(self):
        """ Destroys the category created, as well as all channels within it. """
        for channel in self.category.text_channels + self.category.voice_channels:
            await channel.delete()
        await self.category.delete()

    @chameleon.command()
    async def forcequit(self, ctx):
        """ Stops the game at any point. """
        await ctx.send('Quitting the game in 1 second.')
        await asyncio.sleep(1)
        self.lobby.clear()
        self.gamestate = GameState.init
        await self.destroy_game_channels()


    async def gameloop(self):
        """ The main game loop. """
        game_round = 0
        tc = self.category.text_channels[0]
        while self.gamestate == GameState.ingame:
            game_round += 1
            await tc.send(f'__**Round {game_round}**__')
            await asyncio.sleep(2)
            card, words = self.new_category_card()
            await tc.send('The card is:', embed=card)
            await asyncio.sleep(2)
            word = random.choice(words)
            await tc.send('Check your Private Messages for the secret word. Then, come back and mark when you\'re ready to move on.')
            # Send private messages to tell people which one it is
            await tc.send(f'<PM> The word is: {word}.')



    def new_category_card(self):
        words = ['Apple', 'Banana', 'Grape', 'Lemon', 'Pineapple']
        embed = discord.Embed(title='Fruits', colour=discord.Colour(0xc77681), description='\n'.join(words))
        return embed, words


def setup(bot):
    prefix = cfload.configSectionMap('Commands')['command_prefix']
    bot.add_cog(Chameleon(bot, prefix))
