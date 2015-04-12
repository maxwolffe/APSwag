import json
#import urllib.request
import requests


apString =     """ 10.20.8.40 - FamilyRoom, 04:18:d6:20:60:44, UniFi AP-Pro, channel 6, 140
    10.20.8.41 - W3J, e8:94:f6:68:87:51, TP-Link, channel 11
    10.20.8.42 - E2J, 04:18:d6:20:58:df, UniFi AP-Pro, channel 6, 132
    10.20.8.43 - W2C, 04:18:d6:20:5c:fe, UniFi AP-Pro, channel 6, 124
    10.20.8.44 - W3A, c0:4a:00:5d:c3:f3, TP-Link, channel 1
    10.20.8.45 - Hackerspace, c0:4a:00:40:e3:61, TP-Link, channel 1
    10.20.8.46 - E3StudyRoom, e8:94:f6:68:84:78, TP-Link, channel 1
    10.20.8.47 - GreatHall, 04:18:d6:20:59:c8, UniFi AP-Pro, channel 1, 116
    10.20.8.48 - E2D, 04:18:d6:20:5a:1f, UniFi AP-Pro, channel 11, 108
    10.20.8.49 - W2H, 04:18:d6:20:59:c7, UniFi AP-Pro, channel 1, 100
    10.20.8.50 - C2P, 04:18:d6:20:58:e4, UniFi AP-Pro, channel 11, 64
    10.20.8.51 - C2C, 04:18:d6:20:5f:e6, UniFi AP-Pro, channel 1, 56
    10.20.8.52 - W1E, 90:f6:52:ea:05:ec, TP-Link, channel 11
    10.20.8.53 - C3K, 90:F6:52:2A:08:54, TP-Link, channel 6 """

apList = apString.split('\n')
apIPList = [ap.split('-') for ap in apList]
print (apIPList)
apListList = [[ap[0]] + ap[1].split(",") for ap in apIPList]
accessPointLists = [[nameString.strip() for nameString in ap] for ap in apListList]

for apl in accessPointLists:
	print (apl)



def findRogues(jsonList):
	# Friendlist is a list containing the mac address (Equiv to BSSID) of every router for which we have a JSON feed
	friendList = []

	#Rogue list is a dictionary, whose key values are detected routers with BSSIDs not on the friend list, and whose values are a list of routers and signal strength pairs.
	rogueList = {}

	for router in jsonList:
		#routerMac = router['core.interfaces']['wlan0']['mac']
		#friendList.append(routerMac)
		# Add mac addresses of all services run by this router to our list of friendly mac addresses
		macList = [interface['mac'] for interface in router['core.interfaces'].values() if 'mac' in interface.keys()]
		friendList.append(macList[1])
	for router in jsonList:
		macList = [interface['mac'] for interface in router['core.interfaces'].values() if 'mac' in interface.keys()]
		routerMac = macList[1]
		print("finding rogues for mac: " + routerMac)
		try:
			encounters = [n for n in router['core.wireless']['radios']['radio0']['survey']]
			rogues = [[n['ssid'], n['signal']] for n in encounters if not(n['bssid'] in friendList)]
			for rogue in rogues:
				rogueName = rogue[0]
				print (rogueName)
				signalStrength = rogue[1]
				if rogueName in rogueList.keys():
					rogueList[rogueName].append((routerMac, signalStrength))
				else:
					rogueList[rogueName] = [(routerMac, signalStrength)]
		except KeyError:
			print("Nothing here, Kids. Just a Radios0 Key Error")
		try:
			encounters = [n for n in router['core.wireless']['radios']['radio1']['survey']]
			rogues = [[n['ssid'], n['signal']] for n in encounters if not(n['bssid'] in friendList)]
			for rogue in rogues:
				rogueName = rogue[0]
				print (rogueName)
				signalStrength = rogue[1]
				if rogueName in rogueList.keys():
					rogueList[rogueName].append((routerMac, signalStrength))
				else:
					rogueList[rogueName] = [(routerMac, signalStrength)]
		except KeyError:
			print("Nothing here, Kids. Just a Radios1 Key Error")
	return rogueList
			
def test(ipList):
	jsons = []
	for ip in ipList:
		print("IP is ~" + ip)
		try:
			ipString = "http://" + ip + "/nodewatcher/feed"
			jsonString = urllib.request.urlopen(ipString, timeout = 2).read()
			#print (jsonString)
			jsonDict= json.loads(jsonString.decode())
			jsons.append(jsonDict)
		except urllib.error.URLError:
			print ("!!Error opening this URL!!")
	print("##### " + str(len(jsons)) + " JSON Files Acquired #####")
	a =  findRogues(jsons)
	print(a)
	#return findRogues(jsons)


def node_neighbors(node):
	"""
	Return a list of node tuples ((bssid, ssid), signal) which are neighbors to node. (Can be detected by radio1)

	Arguments:
	node - (bssid [MAC Address], ssid, ip_address)
	"""
	node_ip = node[2] #Should I make nodes dictionaries instead?
	node_json = requests.get(node_ip + '/nodewatcher/feed/').json()
	radio1_neighbors = []
	try:
		radio1_json = node_json['core.wireless']['radios']['radio1']
		radio1_neighbors = [(r_node['bssid'], r_node['ssid'])]
	except KeyError as e:
		print("Key Error " + e)
	return radio1_neighbors


def node_graph(node_list):
	""" 
	Return a dictionary of node tuples (bssid, ssid, room_name, ip_address) as keys and a list of (node tuple, signal) that are neighbors as values. 
	"""
	node_graph = {}
	for node in node_list:
		node_graph[node] = node_neighbors(node)
	return node_graph


ips = ["192.168.0.44", "192.168.0.48", "192.168.0.50"]
test([ap[0] for ap in accessPointLists])
