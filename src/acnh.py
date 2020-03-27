from discord.ext import commands
import requests
import re

# Use https://www.mediawiki.org/wiki/API:Revisions#Sample_Code to GET from https://animalcrossing.fandom.com/wiki/Fish_(New_Horizons)
url = 'https://animalcrossing.fandom.com/api.php?action=query&prop=revisions&rvprop=content&rvslots=*&format=json&titles='

class ACNH(commands.Cog):
    """ Various helper commands for Animal Crossing: New Horizons game on the Nintendo Switch. """
    fish_title = 'Fish_(New_Horizons)'

    @commands.command(aliases=['fi'])
    async def fishinfo(self, ctx, *query):
        """ Retrieves fish information for AC:NH. """

        r = requests.get(url + self.fish_title).json()  # TODO use aiohttp (even though this is fast enough on its own)
        data = r['query']['pages']['143083']['revisions'][0]['*']  # TODO parse this for individual fish information
        table_contents = re.findall('{{TableContent|type=fish(.+)}}', data)  # maybe add re.DOTALL flag to include \n
        print(data)
        print('\n'*5, '='*100)
        print(table_contents[1])
        await ctx.send(table_contents[1][0:2000])

def setup(bot):
    bot.add_cog(ACNH(bot))
