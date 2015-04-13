import json
import requests
import networkx as nx


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
    """
    Generates a dictionary with node information, 
    and a list of nodes which are not registered with the network. 

    """
    nodes = {apl[0] : {} for apl in apls}
    friendly_bssids = []
    neighbor_nodes = []
    rogue_nodes = []

    for ip in nodes.keys():
        nodes[ip]['json'] = get_json(ip)
        node_json = nodes[ip]['json']
        nodes[ip]['bssid'] = get_bssid(node_json)
        nodes[ip]['neighbors'] = get_neighbors(node_json)
        nodes[ip]['hostname'] = node_json['core.general']['hostname']
    
    for node in nodes.values():
        friendly_bssids.extend(node['bssid'])
        neighbor_nodes.extend(node['neighbors'])

    rogue_nodes = find_rogues(neighbor_nodes, friendly_bssids)
    return nodes, rogue_nodes

def get_json(node_ip):
    try:
        node_json = requests.get('http://' + node_ip + '/nodewatcher/feed').json()
        return node_json
    except Exception as e:
        print("Exception in get_json " + str(e))


def get_bssid(node_json):
    """
    Returns a list of mac addresses belonging to the node in the network.
    """
    return [interface[1]['mac'].lower() for interface in node_json['core.interfaces'].items() if interface[0] != '_meta']
    #This may be a problem. Assuming bssid is always a mac defined in the interfaces. Where else would I find bssid?


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
    Return a list of node tuples (bssid [mac], ssid, signal) which are neighbors to node.

    Arguments:
    node_json - feed.json from the nodewatcher dir. 
    """
    radio_neighbors = []
    radio_json = {}
    try:
        radio_json = node_json['core.wireless']['radios']
    except KeyError as e:
        print("Whoops! No Radio! " + str(e))
    radio_survey = []
    for radio in radio_json.values():
        if 'survey' in radio.keys():
            radio_survey.extend(radio['survey'])
    for r_node in radio_survey:
        try:
            # Here we could keep track of the interface that this neighbor is on to better construct the graph. 
            radio_neighbors.append((r_node['bssid'], r_node['ssid'], r_node['signal']))  
        except KeyError as e:
            print("Key Error " + node_json['core.general']['hostname'] + str(e))
    return radio_neighbors

def node_graph(nodes, friendly_only = True):
    """ Returns a networkx graph of nodes in the network, with signal between them as edges. 

    Arguments:
    nodes - node dictionary returned by populate nodes
    friendly_macs - a list of mac addresses that are registered with the network. 
    friendly_only - optional argument, if true, will construct a graph with only friendly nodes, otherwise includes rogue nodes. 
    """
    G = nx.DiGraph()
    friendly_macs = []
    mac_host_match = {}

    for node in nodes.values():
        friendly_macs.extend(node['macs'])
        G.add_node(node['hostname'])
        for mac in node['macs']:
            mac_host_match[mac] = node['hostname']

    for node in nodes.values():
        # right now I'm just going to match MAC to host name, and then make a hostname graph. (Maybe not useful for rogue_detect.)
        for neighbor in node['neighbors']:
            print(neighbor)
            ip = neighbor[0].lower() 
            if ip in friendly_macs:
                G.add_edge(node['hostname'], mac_host_match[ip], weight = neighbor[2])

    return G

test_ip = apls[0][0]
nodes, rogue_nodes = populate_nodes()
graph = node_graph(nodes)

