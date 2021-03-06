import json
import requests
import networkx as nx
import matplotlib.pyplot as plt
import os
import Queue
import random

# ------ TESTING -------- #

test_json = set()

# ------ END TESTING ----- #


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
apListList = [[ap[0]] + ap[1].split(",") for ap in apIPList]
apls = [[nameString.strip() for nameString in ap] for ap in apListList]

for apl in apls:
    print(apl)

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


class Device: #Better Idea for a name here? Anyone?
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



def populate_nodes(ip_list, test = True):
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
        if not test:
            node_json  = get_json(ip)
        if test:
            test_file = None
            for test_file in os.listdir("./test_data"):
                node_json = None
                with open("./test_data/" + test_file, "r") as my_file:
                    node_json = json.loads(my_file.read())
                if test_file not in test_json:
                    test_json.add(test_file)
                    break

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
    print ("List of Friendly macs below:")
    print (friendly_macs)
    for node in nodes:
        for neighbor in node.neighbors:
            mac = neighbor.bssid.lower()
            print("Neighbor with bssid: " + mac)
            if mac not in friendly_macs:
                print ("Not in friendly macs")
                if mac not in all_macs:
                    all_macs.extend(mac)
                    rogue_macs.extend(mac)
                    mac_rogue_match[mac] = neighbor.ssid
                real_edges.append((node.hostname, neighbor.ssid, neighbor.distance))
                rogue_edges.append((node.hostname, neighbor.ssid, neighbor.distance))
            else:
                friend_edges.append((node.hostname, mac_host_match[mac], neighbor.distance))
                real_edges.append((node.hostname, mac_host_match[mac], neighbor.distance))
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

    Frontier is last element in coloring
    """

    start_nodes = graph.nodes()
    start_edges = graph.edges(data = True)
    colors = ['red', 'green', 'blue']
    complete = False

    colored_graph = graph.copy()

    for node in start_nodes:
        while True :
            if len(colored_graph.neighbors(node)) <= len(colors) + 1:
                break
            weakest_edge = min(colored_graph.edges(node, data = True), key = lambda edge: edge[2]['weight'])
            if weakest_edge in start_edges:
                start_edges.remove(weakest_edge)
            else:
                start_edges.remove((weakest_edge[1], weakest_edge[0], weakest_edge[2]))
            colored_graph.remove_edges_from(colored_graph.edges())
            colored_graph.add_edges_from(start_edges)
            
    while len(start_edges) > 0:
        print(len(start_edges))
        bfs_q = Queue.Queue()
        start_node = random.choice(start_nodes)
        for color in colors:
            bfs_q.put([(start_node, color)])

        colored_graph.remove_edges_from(colored_graph.edges())
        colored_graph.add_edges_from(start_edges)

        # BFS to determine if a coloring exists given current number of edges, not currently working. 
        while not bfs_q.empty():
            print(bfs_q.qsize())
            
            coloring = bfs_q.get()

            check_condition = check_graph(colored_graph, coloring)

            if not check_condition[0]:
                continue

            if check_condition[1] == "complete":
                return colored_graph

            colored_set = set()
            for node in coloring:
                colored_set.add(node[0]) 
            checked_neighbors = 0

            for point in coloring:
                for neighbor in colored_graph.neighbors(point[0]):
                    if neighbor in colored_set:
                        print("don't add")
                        continue
                    for color in colors:
                        bfs_q.put(coloring + [(neighbor, color)])
                        colored_set.add(neighbor)

        start_edges.remove(min(start_edges, key = lambda edge:edge[2]['weight']))



def check_node_color_ok(graph, node):
    """ 
    returns False if a node has the same color as one of its neighbors, True otherwise

    takes a graph and a node (node_name, data(as dictionary)) 

    """
    if node[1]['color'] == None:
        return (True, "incomplete")
    for neighbor in graph.neighbors(node[0]):
        if neighbor == node[0]:
            continue
        if node[1]['color'] == graph.node[neighbor]['color']:
            return (False, "false")
    return (True, "complete")

def check_graph(graph, coloring):
    """
    Takes a graph, and a list of of (node, color) tuples, assigns the nodes to colors, 
    and checks to see if it is a valid three coloring. returns True if it is, False otherwise. 

    """
    checked_set = set()
    nodes = []
    complete = "complete"
    bfs_q = Queue.Queue()

    for node in graph.node:
        nodes.append(node)
        graph.node[node]['color'] = None

    for node in coloring:
        graph.node[node[0]]['color'] = node[1]

    for check_node in graph.nodes():
        checked_result = check_node_color_ok(graph, (check_node, graph.node[check_node]))
        if not checked_result[0]:
            return (False, "bad graph")
        if checked_result[1] == "incomplete":
            complete = "incomplete"

    return (True, complete)



    
test_ip = apls[0][0]

#Test with hardcoded in (Cloyne) Access Point IPs
nodes, rogue_nodes = populate_nodes([apl[0] for apl in apls])
#graph = node_graph(nodes)
graph = all_graph(nodes)
print("Edges")
print(graph.edges(None,1))
print("Nodes")
print(graph.nodes(1))
#nx.draw_networkx(graph, pos=nx.circular_layout(graph), node_color=[node[1]['color'] for node in graph.nodes(1)], edge_color=[edge[2]['color'] for edge in graph.edges(None,1)])
#nx.draw_networkx_nodes(graph, pos=nx.spring_layout(graph), node_color=[node[1]['color'] for node in graph.nodes(1)])
#nx.draw_networkx_edges(graph, pos=nx.spring_layout(graph), edge_color=[edge[2]['color'] for edge in graph.edges(None,1)])
#plt.show()
