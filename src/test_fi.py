import requests
import re
url = 'https://animalcrossing.fandom.com/api.php?action=query&prop=revisions&rvprop=content&rvslots=*&format=json&titles='
fish_title = 'Fish_(New_Horizons)'

r = requests.get(url + fish_title).json()  # TODO use aiohttp (even though this is fast enough on its own)
data = r['query']['pages']['143083']['revisions'][0]['*']  # TODO parse this for individual fish information
table_contents = re.findall('{{TableContent(.+?)}}', data, re.DOTALL)  # DOTALL flag includes \n
print(data)
print('\n'*5, '='*100)
print(table_contents[1])
