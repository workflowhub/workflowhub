import networkx as nx
import pathlib
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.patches as mpatches
from typing import Iterable, Type, Union, Set, Optional, Tuple, Dict, Hashable, List
import argparse
import json
from hashlib import sha256


def string_hash(obj: Hashable) -> str:
    return sha256(str(obj).encode("utf-8")).hexdigest()

def type_hash(_type: str, parent_types: Iterable[str]) -> str:
    return string_hash((_type, sorted(set(parent_types))))

def combine_hashes(*hashes: str) -> str:
    return string_hash(sorted(hashes))

def create_graph(path: Union[str, pathlib.Path]) -> nx.DiGraph:
    path = pathlib.Path(path)
    with path.open() as fp:
        content = json.load(fp)

        graph = nx.DiGraph()

        # Add src/dst nodes
        graph.add_node("SRC", label="SRC", type="SRC", id="SRC")
        graph.add_node("DST", label="DST", type="DST", id="DST")

        id_count = 0

        for job in content['workflow']['jobs']:

            #specific for epigenomics -- have to think about how to do it in general
            if "genome-dax" in content['name']:
                _type, *_ = job['name'].split('_')
                graph.add_node(job['name'], label=_type, type=_type, id=str(id_count))
                id_count += 1
            else:
                try:
                    _type, _id = job['name'].split('_ID')
                except ValueError:
                    _type, _id = job['name'].split('_0')
                graph.add_node(job['name'], label=_type, type=_type, id=_id)

    
        # for job in content['workflow']['jobs']:
            for parent in job['parents']:
                graph.add_edge(parent, job['name'])

        for node in graph.nodes:
            
            if node in ["SRC", "DST"]:
                continue
            if graph.in_degree(node) <= 0:
                
                graph.add_edge("SRC", node)
            if graph.out_degree(node) <= 0:
                graph.add_edge(node, "DST")
        
        
        return graph

def annotate(g: nx.DiGraph) -> None:
    visited = set()
    queue = [(node, 1) for node in g.nodes if g.in_degree(node) <= 0]
    while queue:
        cur, level = queue.pop(0)
        g.nodes[cur]["level"] = level
        g.nodes[cur]["label"] = g.nodes[cur]["id"]
        parent_ths = [
            g.nodes[p]["top_down_type_hash"]
            for p, _ in g.in_edges(cur)
        ]
        g.nodes[cur]["top_down_type_hash"] = type_hash(g.nodes[cur]["type"], parent_ths)

        visited.add(cur)
        queue.extend([
            (child, level + 1) for _, child in g.out_edges(cur)
            if child not in visited and 
            {sib for sib, _ in g.in_edges(child)}.issubset(visited)
        ])

    # REVERSE 
    visited = set()
    queue = [node for node in g.nodes if g.out_degree(node) <= 0]
    while queue:
        cur = queue.pop(0)
        parent_ths = [
            g.nodes[p]["bottom_up_type_hash"]
            for _, p in g.out_edges(cur)
        ]
        g.nodes[cur]["bottom_up_type_hash"] = type_hash(g.nodes[cur]["type"], parent_ths)
        g.nodes[cur]["type_hash"] = combine_hashes(g.nodes[cur]["top_down_type_hash"], g.nodes[cur]["bottom_up_type_hash"])

        visited.add(cur)
        queue.extend([
            child for child, _ in g.in_edges(cur)
            if child not in visited and 
            {sib for _, sib in g.out_edges(child)}.issubset(visited)
        ])

def draw(g: nx.DiGraph, 
         extension: Optional[str] = 'png',
         with_labels: bool = False, 
         ax: Optional[plt.Axes] = None,
         show: bool = False,
         save: Optional[Union[pathlib.Path, str]] = None,
         close: bool = False,
         legend: bool = False,
         node_size: int = 500,
         linewidths: int = 5,
         subgraph: Set[str] = set()) -> Tuple[plt.Figure, plt.Axes]:
    fig: plt.Figure
    ax: plt.Axes
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 10))
    else:
        fig = ax.get_figure()

    node_border_colors = {}
    if isinstance(subgraph, dict):
        for color, nodes in subgraph.items():
            for node in nodes:
                node_border_colors[node] = color 
    else:
        for node in subgraph:
            node_border_colors[node] = "green"

    pos = nx.nx_agraph.pygraphviz_layout(g, prog='dot')
    type_set = sorted({g.nodes[node]["type_hash"] for node in g.nodes})
    types = {
        t: i for i, t in enumerate(type_set)
    }
    node_color = [types[g.nodes[node]["type_hash"]] for node in g.nodes]
    for node in g.nodes:
        if node in subgraph:
            g.nodes[node]["node_shape"] = "s"
        else:
            g.nodes[node]["node_shape"] = "c"
    edgecolors = [node_border_colors.get(node, "white") for node in g.nodes]
    edge_color = [
        node_border_colors.get(src) if node_border_colors.get(src,-1) == node_border_colors.get(dst, 1) else "black"
        for src, dst in g.edges
    ]
    cmap = cm.get_cmap('rainbow', len(type_set))
    nx.draw(g, pos, node_size=node_size, node_color=node_color, edgecolors=edgecolors, edge_color=edge_color, linewidths=linewidths, cmap=cmap, ax=ax, with_labels=with_labels)
    color_lines = [mpatches.Patch(color=cmap(types[t]), label= t) for t in type_set]
   
    if legend:
        legend = ax.legend(handles = color_lines , loc='lower right')

    # for handle in legend.legendHandles:
    #     handle.set_color(cmap(types[t]))

    if show:
        plt.show()

    if save is not None:
        if extension == 'dot':
            nx.drawing.nx_agraph.write_dot(g, save)
        else:
            fig.savefig(str(save))

    if close:
        plt.close(fig)

    return fig, ax
