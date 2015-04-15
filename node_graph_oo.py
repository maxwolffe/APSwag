import json
import requests
import networkx as nx
import matplotlib.pyplot as plt


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
#print (apIPList)
apListList = [[ap[0]] + ap[1].split(",") for ap in apIPList]
apls = [[nameString.strip() for nameString in ap] for ap in apListList]

for apl in apls:
    print apl

#  --------   DATA  ----------- #


class Node:

    hostname  = ''
    json = ''
    bssid = ''
    neighbors = []

    def __init__(self, json):
        self.json = json
        self.hostname = json['core.general']['hostname']
        self.get_bssid()
        self.get_neighbors()


    def get_bssid(self):
        """
        Returns a list of mac addresses belonging to the node in the network.
        """
        try:
            self.bssid = [interface[1]['mac'].lower() for interface in self.json['core.interfaces'].items() if interface[0] != '_meta']
            #This may be a problem. Assuming bssid is always a mac defined in the interfaces. Where else would I find bssid?
        except Exception as e:
            print("Failure to find BSSID: " + str(e))

    
    def get_neighbors(self):
        """
        Return a list of node tuples (bssid [mac], ssid, signal) which are neighbors to node.

        """
        node_json = self.json
        radio_json = {}
        try:
            radio_json = node_json['core.wireless']['radios']
        except KeyError as e:
            print("Whoops! No Radio! " + str(e))
        radio_survey = [radio['survey'][0] for radio in radio_json.values() if 'survey' in radio.keys()]
        for r_node in radio_survey:
            try: 
                self.neighbors.append(Device(r_node['bssid'], r_node['ssid'], r_node['signal'], r_node['channel']))  
            except KeyError as e:
                print("Key Error " + node_json['core.general']['hostname'] + str(e))


class Device(): #Better Idea for a name here? Anyone?
    bssid = '' #Previously 0th element of device list
    ssid = '' #Previously 1st element of device list
    signal = 0 #Previously 2nd element of device list
    channel = 0 #Not Previously in device list
    distance = 100000

    def __init__(self, bssid, ssid, signal, channel):
        self.bssid = bssid
        self.ssid = ssid
        self.signal = signal
        print(signal)
        self.distance = (-1 * signal)
        self.channel = channel



def populate_nodes(ip_list):
    """
    Generates a dictionary with node information, 
    and a list of nodes which are not registered with the network. 

    """
    #nodes = {ap_ip : {} for ap_ip in ip_list}
    #nodes is a dictionary with AP IPs as keys, and a dictionary of features of that AP as values
    friendly_bssids = [] #list of friendly nodes?
    neighbor_nodes = [] #list of nodes who can hear eachother?
    rogue_nodes = [] #list of unfriendly nodes
    our_nodes = [] #list of all nodes

    for ip in ip_list:
        node_json  = get_json(ip)
        if not node_json:
            print("Failed to obtain json for IP address " + ip)


        else:
            print("Assigning values for " + ip)
            n = Node(node_json)
            our_nodes.append(n)
    
    for node in our_nodes:
        friendly_bssids.extend(node.bssid)
        neighbor_nodes.extend(node.neighbors)

    rogue_nodes = find_rogues(neighbor_nodes, friendly_bssids)
    return our_nodes, rogue_nodes

def get_json(node_ip):
    """
    Returns the json feed of the node found at IP address node_ip. 
    Will often error if a presumed access point is offline.
    """
    try:
        node_json = requests.get('http://' + node_ip + '/nodewatcher/feed', timeout=3).json()
        return node_json
    except Exception as e:
        print("Exception in get_json " + str(e))


def find_rogues(node_list, friendly_macs):
    """
    returns a list of nodes which have mac addresses which are not registered with the list of mac addresses in the network.

    Arguments: 
    node_list - list of all nodes (bssid, ssid, signal) that are detected by cloyne ap radios
    friendly_macs - list of mac addresses registered with network. 
    """
    return [node for node in node_list if (node.bssid.lower() not in friendly_macs)]


def node_graph(nodes, friendly_only = True):
    """ Returns a networkx graph of nodes in the network, with signal between them as edges. 

    Arguments:
    nodes - node dictionary returned by populate nodes
    friendly_macs - a list of mac addresses that are registered with the network. 
    friendly_only - optional argument, if true, will construct a graph with only friendly nodes, otherwise includes rogue nodes. 
    """
    G = nx.Graph() # Should this be directed?
    friendly_macs = []
    mac_host_match = {}

    for node in nodes:
        friendly_macs.extend(node.bssid)
        G.add_node(node.hostname)
        for mac in node.bssid:
            mac_host_match[mac] = node.hostname

    for node in nodes:
        # right now I'm just going to match MAC to host name, and then make a hostname graph. (Maybe not useful for rogue_detect.)
        for neighbor in node.neighbors:
            ip = neighbor.bssid.lower() 
            if ip in friendly_macs:
                G.add_edge(node.hostname, mac_host_match[ip], weight = neighbor.signal)
    return G


def all_graph(nodes):
    """
    Returns a graph containing every AP and all their neighbors, with edges between each.
    Stores lists of nodes and edges for later coloring.
    """
    G = nx.Graph()
    APs = []
    all_macs = []
    friendly_macs = []
    rogue_macs = []
    mac_host_match = {}
    mac_rogue_match = {}
    real_edges = []
    rogue_edges = []
    friend_edges = []
    fake_edges = []
    channel_dict = {}

    for node in nodes:
        friendly_macs.extend(node.bssid)
        all_macs.extend(node.bssid)
        G.add_node(node.hostname)
        for mac in node.bssid:
            mac_host_match[mac] = node.hostname
    for node in nodes:
        for neighbor in node.neighbors:
            if neighbor.bssid not in friendly_macs:
                if neighbor.bssid not in all_macs:
                    all_macs.extend(neighbor.bssid)
                    rogue_macs.extend(neighbor.bssid)
                    mac_rogue_match[neighbor.bssid] = neighbor.ssid
                real_edges.append((node.hostname, neighbor.ssid, neighbor.distance))
                rogue_edges.append((node.hostname, neighbor.ssid, neighbor.distance))
            else:
                friend_edges.append((node.hostname, mac_host_match[neighbor.bssid], neighbor.distance))
                real_edges.append((node.hostname, mac_host_match[neighbor.bssid], neighbor.distance))
    #Create fake edges to ensure that nodes which are not neighbors are farther apart in the graph


    #Create Graph
    G.add_nodes_from(list(set(mac_host_match.values())), color='blue')
    G.add_nodes_from(list(set(mac_rogue_match.values())), color='red')
    G.add_weighted_edges_from(rogue_edges, color='red')
    G.add_weighted_edges_from(friend_edges, color='blue')


    return G


def three_color(graph):
    """
    returns a best effort three coloring of the graph provided. 

    Algorithm idea: Attempt to three color graph. If successful return coloring.
    Else: Delete the edge that has the weakest signal and try again. 
    """

    "YOUR CODE HERE"

    
test_ip = apls[0][0]

#Test with hardcoded in (Cloyne) Access Point IPs
nodes, rogue_nodes = populate_nodes([apl[0] for apl in apls])
#graph = node_graph(nodes)
graph = all_graph(nodes)
nx.draw_networkx(graph)
plt.show()
