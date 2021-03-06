import networkx as nx 
import matplotlib.pyplot as plt
from networkx.algorithms import bipartite
from networkx.algorithms import components
from networkx.algorithms import connectivity
from networkx import bipartite
from networkx.algorithms.connectivity import minimum_st_node_cut
from networkx.algorithms.connectivity import minimum_st_edge_cut
from itertools import product, combinations
 
from networkx.algorithms.connectivity import (
    build_auxiliary_node_connectivity)
from networkx.algorithms.flow import build_residual_network
 
from networkx.algorithms.flow import edmonds_karp
from collections import OrderedDict
import sys
from itertools import product
from itertools import combinations
from string import ascii_lowercase
from copy import deepcopy




#two-mode graph class
class TM_Graph(object):
	def __init__(self, data=[]):
		self.G = nx.Graph()
		self.data = data
		self.parents = []
		self.chain = []

	def populate_data(self):
		num_cols = len(self.data[0])
		num_rows = len(self.data)

		keywords = [''.join(x) for x in product(ascii_lowercase, repeat = 2)]

		for i in range(num_rows):
			self.G.add_nodes_from([i], bipartite=0)

		for j in range(num_cols):
			self.G.add_nodes_from([keywords[j]], bipartite=1)

		for i in range(num_rows):
			for j in range(num_cols):
				if self.data[i][j] == 1:
					tup = (i, keywords[j])
					self.G.add_edges_from([tup])

	def remove_circular_refs(self, ob, _seen=None):
		if _seen is None:
			_seen = set()
		if id(ob) in _seen:
			# circular reference, remove it.
			return None
		_seen.add(id(ob))
		res = ob
		if isinstance(ob, dict):
			res = {
				remove_circular_refs(k, _seen): remove_circular_refs(v, _seen)
				for k, v in ob.items()}
		elif isinstance(ob, (list, tuple, set, frozenset)):
			res = type(ob)(self.remove_circular_refs(v, _seen) for v in ob)

		# remove id again; only *nested* references count
		_seen.remove(id(ob))
		return res

	def get_removed_edges(self, comp, removed_nodes, G_original):
		removed_edges = []
		nodes_in_comp = list(comp.nodes()) + list(removed_nodes)

		for edge in G_original.edges():
			if (edge[0] in nodes_in_comp) and (edge[1] in nodes_in_comp):
				removed_edges.append(edge)

		return removed_edges

		
	def get_node_sets(self, G):
		A = set(n for n,d in G.nodes(data=True) if d['bipartite']==0)
		B = set(G) - A

		return A, B

	def get_pendants(self, G):
		to_remove = []
		for n in G.nodes():
			if G.degree(n) == 1:
				to_remove.append(n)	
		return to_remove

	def draw(self, G):

		A, B = self.get_node_sets(G)

		#draw network
		pos = dict()
		pos.update( (x, (1, i)) for i, x in enumerate(A) ) # put nodes from A at x=1
		pos.update( (x, (2, i)) for i, x in enumerate(B) ) # put nodes from B at x=2
		labels = {x:x for x in range(len(G.nodes()))}
		nx.draw_networkx(G, pos=pos)
		nx.draw_networkx_labels(G, pos)
		plt.show()


	def get_os_conn(self, G, A, B):
		os_cut = self.get_os_cut(G, A, B)

		if (not os_cut) or (len(A) <= 1):
			return 0

		return len(os_cut)

	#Takes a connected component, G, and connectivity, conn
	def cohesive_blocking(self, G, conn, emb = 0, blocks = [], i = 0, highest_conn = 1):

		#get the node sets and a single minimal os cut
		A, B = self.get_node_sets(G)
		cut = self.get_os_cut(G, A, B)


		#if component has the highest conn seen so far, append to blocks
		if conn == highest_conn:
			blocks.append([G, conn, emb])

		#if the current graph component is complete, return that component, 
		#its connectivity, and its nestedness
		if (conn == len(B)) or (conn == 0):
			# component terminated. Going back..
			return 
			

		#create copy of current graph component before node removal
		G_original = G.copy()

		#remove the nodes in the cut
		for node in cut:
			if node in G.nodes():
				G.remove_node(node)

		#get all of the new components as a result of the removed cut
		comps = list(components.connected_component_subgraphs(G))

		#iterate over new components
		for c in comps:

			#get every component with the latest cut added back in
			removed_edges = self.get_removed_edges(c, cut, G_original)
			c.add_nodes_from(list(cut), bipartite = 1)
			c.add_edges_from(removed_edges)

			#remove pendants chains
			to_remove = self.get_pendants(c)

			while to_remove:
				for n in to_remove:
					c.remove_node(n)
				to_remove = self.get_pendants(c)


			A, B = self.get_node_sets(c)	
			cur_conn = self.get_os_conn(c, A, B)

			#Recurse:
			#if current component has a higher connectivity that all of its
			#ancestors, increase embeddedness and append to parents list. 
			#Otherwise, just recurse normally
			if cur_conn > highest_conn:
				self.parents.append(G_original)
				self.cohesive_blocking(c, cur_conn, emb + 1, blocks, i + 1, cur_conn)
			else:
				self.cohesive_blocking(c, cur_conn, emb, blocks, i + 1, highest_conn)


		return blocks

	def rest_build_auxiliary_node_connectivity(self,G,A,B):
	    directed = G.is_directed()
	 
	    H = nx.DiGraph()
	 
	    for node in A:
	        H.add_node('%sA' % node, id=node)
	        H.add_node('%sB' % node, id=node)
	        H.add_edge('%sA' % node, '%sB' % node, capacity=1)
	 
	    for node in B:
	        H.add_node('%sA' % node, id=node)
	        H.add_node('%sB' % node, id=node)
	        H.add_edge('%sA' % node, '%sB' % node, capacity=1)        
	 
	    edges = []
	    for (source, target) in G.edges():
	        edges.append(('%sB' % source, '%sA' % target))
	        if not directed:
	            edges.append(('%sB' % target, '%sA' % source))
	    H.add_edges_from(edges, capacity=1)
	 
	    return H
	       
	def rest_minimum_st_node_cut(self, G, A, B, s, t, auxiliary=None, residual=None, flow_func=edmonds_karp):
	 
	    if auxiliary is None:
	        H = self.rest_build_auxiliary_node_connectivity(G, A, B)
	    else:
	        H = auxiliary
	 
	    if G.has_edge(s,t) or G.has_edge(t,s):
	        return []
	    kwargs = dict(flow_func=flow_func, residual=residual, auxiliary=H)
	 
	    for node in [x for x in A if x not in [s,t]]:
	        edge = ('%sA' % node, '%sB' % node)
	        num_in_edges = len(H.in_edges(edge[0]))
	        H[edge[0]][edge[1]]['capacity'] = num_in_edges
	 
	    edge_cut = minimum_st_edge_cut(H, '%sB' % s, '%sA' % t,**kwargs)
	 
	    node_cut = set([n for n in [H.nodes[node]['id'] for edge in edge_cut for node in edge] if n not in A])
	 
	    return node_cut - set([s,t])

	def get_os_cut(self, G, A, B):

		#if trivial graph, return no cut
		if len(G.nodes()) <= 1:
			return []

		seen = []
		os_cuts = []

		l = list(combinations(A,2))

		#lower bound for cut-set size (normal om connectivity)
		min_node_cuts = list(connectivity.all_node_cuts(G))
		minimum_conn = len(min_node_cuts[0])

		for cut in min_node_cuts:
			if set(cut).issubset(B):
				return cut

		minimum_conn += 1

		for x in l:
			s = x[0]
			t = x[1]

			cut = self.rest_minimum_st_node_cut(G, A, B, s, t)

			if (set(cut).issubset(B)) and (cut) and (cut not in seen):

				#if cut of minimum length, save time and return right away
				if len(cut) == minimum_conn:
					return cut

				#otherwise, simply add to all os cuts
				os_cuts.append(cut)

			seen.append(cut)

		if not os_cuts:
			#if no cuts found, return neigbors of node in A with minimal degree

			#establish the minimum degree of all nodes in A
			min_degree = float("inf")
			for node in G.nodes():
				if (G.degree(node) < min_degree) and (node in A):
					min_degree = G.degree(node)

			#return the neighbors of the first node found of that degree in A
			for node in G.nodes():
				if (G.degree(node) == min_degree) and (node in A):
					return set(G.neighbors(node))

		else:
			cur_min = float("inf")
			for cut in os_cuts:
				if len(cut) < cur_min:
					cur_min = len(cut)

			for cut in os_cuts:
				if len(cut) == cur_min:
					return cut




