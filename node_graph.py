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
apls = [[nameString.strip() for nameString in ap] for ap in apListList]

for apl in apls:
    print apl

#  --------   DATA  ----------- #


def populate_nodes():
    nodes = {apl[0] : {} for apl in apls}
    friendly_macs = []
    neighbor_nodes = []
    rogue_nodes = []

    for ip in nodes.keys():
        nodes[ip]['json'] = get_json(ip)
        node_json = nodes[ip]['json']
        nodes[ip]['macs'] = get_macs(node_json)
        nodes[ip]['neighbors'] = get_neighbors(node_json)
    
    for node in nodes.values():
        friendly_macs.extend(node['macs'])
        neighbor_nodes.extend(node['neighbors'])

    rogue_nodes = find_rogues(neighbor_nodes, friendly_macs)
    return nodes, rogue_nodes

def get_json(node_ip):
    try:
        node_json = requests.get('http://' + node_ip + '/nodewatcher/feed').json()
        return node_json
    except Exception as e:
        print("Exception in get_json " + str(e))


def get_macs(node_json):
    """
    Returns a list of mac addresses belonging to the node in the network.
    """
    return [interface[1]['mac'] for interface in node_json['core.interfaces'].items() if interface[0] != '_meta']


def find_rogues(node_list, friendly_macs):
    """
    returns a list of nodes which have mac addresses which are not registered with the list of mac addresses in the network.

    Arguments: 
    node_list - list of all nodes (bssid, ssid, signal) that are detected by cloyne ap radios
    friendly_macs - list of mac addresses registered with network. 
    """
    return [node for node in node_list if (node[0].lower() not in friendly_macs)]

def get_neighbors(node_json):
    """
    Return a list of node tuples (bssid, ssid, signal) which are neighbors to node.

    Arguments:
    node_json - feed.json from the nodewatcher dir. 
    """
    radio_neighbors = []
    radio_json = node_json['core.wireless']['radios']
    radio_survey = []
    for radio in radio_json.values():
        if 'survey' in radio.keys():
            radio_survey.extend(radio['survey'])
    for r_node in radio_survey:
        try:
            radio_neighbors.append((r_node['bssid'], r_node['ssid'], r_node['signal']))
        except KeyError as e:
            print("Key Error " + node_json['core.general']['hostname'] + str(e))
    return radio_neighbors


test_ip = apls[0][0]
nodes, rogue_nodes = populate_nodes()
