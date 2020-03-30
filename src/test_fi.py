import requests
import re
import mwparserfromhell as mwp

query = 'GolDfish'.lower()

url = 'https://animalcrossing.fandom.com/api.php?action=query&prop=revisions&rvprop=content&rvslots=*&format=json&titles=Fish_(New_Horizons)'

r = requests.get(url).json()  # TODO use aiohttp (or is this is fast enough on its own?)
data = r['query']['pages']['143083']['revisions'][0]['*']

wikitext = mwp.parse(data)
templates = wikitext.filter_templates()
filtered_list = list(
    filter(lambda template: template.name.matches('TableContent') or template.name.matches('roundyR'),
           templates))

# Remove first roundyR. The second one separates north and south hemispheres.
roundyR = filtered_list.pop(0)
idx = filtered_list.index(roundyR)

n_hemisphere = filtered_list[:idx]  # Fish name is at element.params[1]
s_hemisphere = filtered_list[idx + 1:]

results = list(filter(lambda temp: temp.params[1].strip('\n []').lower() == query, n_hemisphere)) + list(
    filter(lambda temp: temp.params[1].strip('\n []').lower() == query, s_hemisphere))

icon_name = results[0].params[2].strip('\n []').replace('File: ', '').replace(' ', '_')

html_url = 'https://animalcrossing.fandom.com/api.php?action=parse&page=Fish_(New_Horizons)&prop=text&format=json'
html_r = requests.get(html_url).json()
html_data = html_r['parse']['text']['*']

pic_url = re.search(f'href="(?P<URL>(.*?){icon_name}(.*?))"', html_data).group('URL')
print(pic_url)
