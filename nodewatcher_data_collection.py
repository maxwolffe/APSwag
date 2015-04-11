import requests

r = requests.get('http://10.20.8.41/nodewatcher/feed/')

node_json = r.json()

survey0 = node_json['core.wireless']['radios']

