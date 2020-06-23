import asyncio
import enum
import json
import random

import discord
from discord.ext import commands

import configloader as cfload


class GameState(enum.Enum):
    init = 0
    lobby = 1
    startgame = 2
    ingame = 3
    voting = 4
    roundover = 5
    cleanup = 6


class Chameleon(commands.Cog):
    """ A discord remake of The Chameleon (card game). """

    MAX_PLAYERS = 8

    def __init__(self, bot, command_prefix):
        self.bot = bot
        self.command_prefix = command_prefix
        self.game_state: GameState = GameState.init
        self.lobby = []  # Holds the names of the people in the lobby.
        self.category = None  # Points to discord.categoryChannel created (NOT in-game category card).
        self.round_winner = None  # Used in voting stage
        self.points = {}  # key: name, val: points
        self.custom_cards = {}  # Holds custom-made cards. (key:category, val:words)
        self.use_custom_cards = False  # Whether or not to use the custom cards.

    @commands.Cog.listener('on_reaction_add')
    async def on_reaction_add(self, reaction: discord.Reaction, user):
        """ Main handler for reaction-based interactions with the game. """
        if user == reaction.message.author:  # which is the bot, or spectators
            return

        if self.game_state == GameState.lobby:
            if reaction.emoji == '➕':
                channel = reaction.message.channel
                if len(self.lobby) >= Chameleon.MAX_PLAYERS:
                    await channel.send(f"Sorry, {user}, the game is full.", delete_after=3)
                else:
                    self.lobby.append(user)
                    await channel.send(f'{user} is in!', delete_after=3)
                    await self.update_lobby_embed(reaction.message)

            elif reaction.emoji == '▶' and user in self.lobby:
                # Set up the game
                self.game_state = GameState.startgame

                guild = reaction.message.channel.guild
                self.category = await self.init_game_channels(guild)

                gametc = self.category.text_channels[0]
                await gametc.send('Welcome to the Chameleon! You have been moved to this private room to play.'
                                  '*NOTE: This game is still in development. Expect bugs and unexpected behavior!*')
                # await gametc.send('<TODO Rules>')  # TODO add rules
                sent_msg: discord.Message = await gametc.send('Once everyone is ready, press ▶ to start the game!')
                await sent_msg.add_reaction('▶')

        elif self.game_state == GameState.startgame and user in self.lobby:
            if reaction.emoji == '▶':
                self.game_state = GameState.ingame
                await self.game_loop()

        elif self.game_state == GameState.roundover and user in self.lobby:
            if reaction.emoji == '🛑':
                self.game_state = GameState.cleanup

                channel = reaction.message.channel
                await channel.send('Thanks for playing!')
                await asyncio.sleep(3)
                await channel.send('Deleting the text channels in 1 second.')
                await asyncio.sleep(1)
                self.lobby.clear()
                self.game_state = GameState.init
                await self.destroy_game_channels()
            elif reaction.emoji == '📝':
                channel = reaction.message.channel
                self.toggle_custom_cards()
                await channel.send('Custom cards enabled for next round.' if self.use_custom_cards
                                   else 'Custom cards disabled for next round.')

    @commands.Cog.listener('on_reaction_remove')
    async def on_reaction_remove(self, reaction: discord.Reaction, user):
        """ Handler for removing a reaction. """
        if user == reaction.message.author:  # which is the bot
            return

        if self.game_state == GameState.lobby:
            if reaction.emoji == '➕':
                # If this reaction is removed, remove user from the lobby.
                channel = reaction.message.channel
                try:
                    self.lobby.remove(user)
                    await channel.send(f'{user} left the lobby.', delete_after=3)
                    await self.update_lobby_embed(reaction.message)
                except ValueError:  # TODO does this need to have an exception clause?
                    pass

        elif self.game_state == GameState.roundover:
            if reaction.emoji == '📝':
                channel = reaction.message.channel
                self.toggle_custom_cards()
                await channel.send('Custom cards enabled for next round.' if self.use_custom_cards
                                   else 'Custom cards disabled for next round.')

    @commands.group(invoke_without_command=True)
    async def chameleon(self, ctx):
        """ Generate a lobby for players to join. """
        if self.game_state != GameState.init:
            await ctx.send("A game is already in play. Use a subcommand.")
        else:
            self.game_state = GameState.lobby
            embed = discord.Embed(title="The Chameleon", colour=discord.Colour(0xe7d066),
                                  description="Click the ➕ button below this message to join/leave the lobby."
                                              "Press ▶ to start the game with the players in the lobby.")

            embed.add_field(name="__Players in lobby__", value='-', inline=True)
            embed.set_footer(text='NOTE: This game is still in development. Expect bugs and unexpected behavior!')

            sent_msg = await ctx.send(embed=embed)
            await sent_msg.add_reaction('➕')
            await sent_msg.add_reaction('▶')

    async def update_lobby_embed(self, message: discord.Message):
        new_embed: discord.Embed = message.embeds[0]

        # Add player names. If a player has a custom nickname, display that and their username in parentheses.
        names = [f'{e.display_name} ({e.name})' if e.display_name != e.name else e.display_name for e in self.lobby]
        names = names or '-'

        new_embed.set_field_at(
            0,
            name=f"__Players in lobby__({len(self.lobby)}/{Chameleon.MAX_PLAYERS})",
            value='\n'.join(names), inline=True
        )
        await message.edit(embed=new_embed)

    @chameleon.command()
    async def join(self, ctx):
        """ Join the lobby for the chameleon game. """
        if self.game_state == GameState.lobby:
            if len(self.lobby) >= Chameleon.MAX_PLAYERS:
                await ctx.send(f"Sorry, {ctx.author}, the game is full.")
            else:
                self.lobby.append(ctx.author)
                await ctx.send(f'Added {ctx.author} to the lobby.')
                # TODO update embed or deprecate this command

    @chameleon.command()
    async def leave(self, ctx):
        """ Leave the lobby. """
        if self.game_state == GameState.lobby:
            try:
                self.lobby.remove(ctx.author)
                # TODO update embed here or deprecate this command
            except ValueError:
                pass

    @chameleon.command()
    async def start(self, ctx):
        """ Starts the game with the players in the lobby. """
        await ctx.send(f"Starting game...")
        self.game_state = GameState.startgame

    async def init_game_channels(self, guild: discord.Guild) -> discord.CategoryChannel:
        """ Create the game CategoryChannel and move players into it. Return the CategoryChannel. """
        category = await guild.create_category('The Chameleon')
        await guild.create_text_channel('chameleon-game', category=category)
        gamevc = await guild.create_voice_channel('The Chameleon', category=category)

        for player in self.lobby:
            # player is a User. Get it as a member.
            member: discord.Member = guild.get_member(player.id)
            try:
                await member.move_to(gamevc)
            except discord.errors.HTTPException:
                # This means the user was not connected to voice. No worries, just continue.
                pass

        return category

    async def destroy_game_channels(self):
        """ Destroys the category created, as well as all channels within it. """
        try:
            for channel in self.category.text_channels + self.category.voice_channels:
                await channel.delete()
            await self.category.delete()
        except discord.errors.NotFound:
            pass  # The channel was deleted before

    @chameleon.command()
    async def forcequit(self, ctx):
        """ Stops the game at any point. """
        self.game_state = GameState.cleanup
        await ctx.send('Stopping the game in 1 second.', delete_after=1)
        await asyncio.sleep(1)
        self.lobby.clear()
        self.game_state = GameState.init
        await self.destroy_game_channels()

    async def game_loop(self):
        """ The main game loop. """
        game_round = 0
        tc = self.category.text_channels[0]
        while self.game_state == GameState.ingame:
            game_round += 1
            self.round_winner = None
            await tc.send(f'__**Round {game_round}**__')
            await asyncio.sleep(2)
            category, words = await self.new_category_card(tc)

            first_half = '\n'.join(words[:len(words)//2])
            second_half = '\n'.join(words[len(words)//2:])

            embed = discord.Embed(title=category.capitalize(), colour=discord.Colour(0xe7d066), description=f'Round {game_round}')
            embed.add_field(name='-', value=first_half, inline=True)
            embed.add_field(name='-', value=second_half, inline=True)
            await tc.send('The card is:', embed=embed)

            await asyncio.sleep(2)
            word = random.choice(words)
            await tc.send('Check your Private Messages for the secret word. Then, come back and mark when you\'re ready to move on.')

            # Send private messages to tell people which one it is
            random.shuffle(self.lobby)
            # The chameleon will be the first user in the lobby.
            the_chameleon = self.lobby[0]  # Used for voting stage later on
            for user in self.lobby:
                if user == the_chameleon:
                    await user.send('**You are the chameleon!** Try to blend in so you are not suspected, '
                                    'and determine the secret word.')
                else:
                    await user.send(f'You are not the chameleon. The secret word is **{word}**.')

            await asyncio.sleep(10)

            # Send player order
            random.shuffle(self.lobby)
            names = [e.name for e in self.lobby]
            colors = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪']
            fnames = [i + ' ' + j for i, j in zip(colors, names)]
            embed = discord.Embed(title='Player Order', colour=discord.Colour(0xe7d066), description='\n'.join(fnames))
            poll = await tc.send('In the following order, describe the secret word with one descriptor word.', embed=embed)

            await asyncio.sleep(45)
            await tc.send('Once everyone has said their word, debate who you think the Chameleon is.')
            await asyncio.sleep(15)
            await tc.send('Vote on who the Chameleon is. If the Chameleon is voted out, try to guess what the word is.\n'
                          '*Voting ends immediately after every player casts a vote.*')

            self.game_state = GameState.voting
            for i in range(len(fnames)):
                await poll.add_reaction(colors[i])

            await self.bot.wait_for('reaction_add', check=self.tally)

            # Declare the winner(s) of the round. The winner is self.round_winner
            if self.round_winner == the_chameleon:
                desc = f'You discovered the chameleon to be {self.round_winner}! ' \
                       f'Now, {self.round_winner} gets a chance to guess the right word.'

                embed = discord.Embed(title='You did it!', description=desc, colour=discord.Colour(0x00cc00))
                await tc.send(embed=embed)
            elif self.round_winner is None:
                desc = f'There was a tie, and the chameleon was not found. The chameleon was {the_chameleon}!'
                embed = discord.Embed(title='Tie!', description=desc, colour=discord.Colour(0xc5c5c5))
                await tc.send(embed=embed)
            else:
                desc = f'{self.round_winner} is not the chameleon! The chameleon was {the_chameleon}!'
                embed = discord.Embed(title='Wrong!', description=desc, colour=discord.Colour(0xff0000))
                await tc.send(embed=embed)

            # Send round over message
            await asyncio.sleep(5)
            round_over_msg = await tc.send('Once the round is over, click 🔁 to play another round, or 🛑 to finish the game.'
                                           'If you play another round, click 📝 to enable/disable custom deck.')
            self.game_state = GameState.roundover
            await round_over_msg.add_reaction('🔁')
            await round_over_msg.add_reaction('🛑')
            await round_over_msg.add_reaction('📝')
            # Current state of use_custom_cards
            await tc.send('Custom cards are enabled for next round.' if self.use_custom_cards
                          else 'Custom cards are disabled for next round.')

            await self.bot.wait_for('reaction_add', check=lambda reaction, _: str(reaction.emoji) == '🔁')
            # If we get here, go back and do it again!
            self.game_state = GameState.ingame

    def tally(self, reaction: discord.Reaction, _):
        """ Returns the user voted on the most in the voting stage once voting is complete. """
        message: discord.Message = reaction.message
        all_reacts = message.reactions
        totals = [r.count for r in all_reacts]  # Maps directly to self.lobby
        if sum(totals) - len(self.lobby) < len(self.lobby):  # Subtract the reactions the bot added
            return False

        m = totals.index(max(totals))

        # Look for a tie. m is leftmost max.
        for i in range(m, len(totals)):
            if totals[i] == max(totals):
                return True  # Do not assign a winner this round.

        self.round_winner = self.lobby[m]
        return True

    async def new_category_card(self, channel):
        if self.use_custom_cards:
            if len(self.custom_cards) > 0:
                return random.choice(list(self.custom_cards.items()))  # Returns a tuple of (key, val)
            else:
                await channel.send('No custom cards! Using normal deck instead. '
                                   'To add a custom card, use the `chameleon custom` command.')

        with open('chameleon_assets/batch1.json', 'r') as f:
            cards: dict = json.load(f)
        return random.choice(list(cards.items()))

    @chameleon.command()
    async def custom(self, ctx, *data: str):
        """ Create a custom card. The first word is the category,
        the following words are words in the category. Usage:
        '/chameleon custom foods apple banana pineapple orange'

        *data, which is a tuple of strings, is separated into a dict, which
        follows convention of the other cards."""
        self.custom_cards.update({data[0]: data[1:]})
        await ctx.send(f'\'{data[0]}\' card added to custom cards.')

    def toggle_custom_cards(self):
        """ Invoked via reaction event handler. """
        self.use_custom_cards = not self.use_custom_cards


def setup(bot):
    prefix = cfload.configSectionMap('Commands')['command_prefix']
    bot.add_cog(Chameleon(bot, prefix))
