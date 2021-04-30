import networkx as nx
from hashlib import sha256
from typing import Iterable, Union, Set, Optional, Tuple, Dict, Hashable, List
from uuid import uuid4
import pathlib
import os
import json
import traceback
from itertools import product
from networkx.readwrite import read_gpickle, write_gpickle
import numpy as np 
from itertools import chain, combinations
import argparse
from .utils import create_graph, string_hash, type_hash, combine_hashes, annotate, draw
import math 

this_dir = pathlib.Path(__file__).resolve().parent

def comb(n: int, k: int) -> int:
    return math.factorial(n) / (math.factorial(k) * math.factorial(n - k))

class ImbalancedMicrostructureError(Exception):
    pass 

def get_children(graph: nx.DiGraph, node: str) -> List[str]:
    return [child for _, child in graph.out_edges(node)]
    
def get_parents(graph: nx.DiGraph, node: str) -> List[str]:
    return [parent for parent, _ in graph.in_edges(node)]

def get_relatives(graph: nx.DiGraph, node: str) -> Set[str]:
    return set(chain(get_children(graph, node), get_parents(graph, node)))

def find_microstructure(graph: nx.DiGraph, n1: str, n2: str):
    n1_new_friends = get_relatives(graph, n1)
    n2_new_friends = get_relatives(graph, n2)

    n1_friends = {n1}
    n2_friends = {n2}
    common_friends = set()
    all_friends = {n1, n2}
    n1_new_friends = {n1}
    n2_new_friends = {n2}

    while n1_new_friends or n2_new_friends:
        if not n1_new_friends or not n2_new_friends:
            raise ImbalancedMicrostructureError()

        n1_new_friends = set.union(set(), *[get_relatives(graph, friend) for friend in n1_new_friends]) - all_friends
        n2_new_friends = set.union(set(), *[get_relatives(graph, friend) for friend in n2_new_friends]) - all_friends
        common_friends.update(n1_new_friends.intersection(n2_new_friends))
        all_friends.update(n1_new_friends.union(n2_new_friends))

        n1_new_friends -= common_friends
        n2_new_friends -= common_friends

        n1_friends.update(n1_new_friends)
        n2_friends.update(n2_new_friends)

    return n1_friends, n2_friends, common_friends, all_friends

def find_microstructures(graph: nx.DiGraph, verbose: bool = False):
    if verbose:
        print("Sorting nodes by type hash and parent")
    nodes_by_type_hash: Dict[str, Set[str]] = {}
    for node in graph.nodes:
        for child in get_children(graph, node):
            th = graph.nodes[child]["type_hash"]
            nodes_by_type_hash.setdefault((node, th), set())
            nodes_by_type_hash[(node, th)].add(child)

    if verbose:
        print("Finding microstructures for typehashes")
    microstructures = {}
    for (th, _), nodes in nodes_by_type_hash.items():
        if len(nodes) < 2:
            continue
        # if verbose:
        #     print(f"{th:5}: {len(nodes)} siblings ({comb(len(nodes), 2)} combos)")
        for n1, n2 in combinations(nodes, r=2):
            try:
                ms1, ms2, _, _ = find_microstructure(graph, n1, n2)
                if len(ms1) > len(ms2):
                    ms1, ms2 = ms2, ms1
                    n1, n2 = n2, n1
                key = combine_hashes(*{graph.nodes[node]["type_hash"] for node in ms1})
                microstructures.setdefault(key, set())
                microstructures[key].update({frozenset(ms1), frozenset(ms2)})
            except ImbalancedMicrostructureError:
                continue

    return microstructures

def sort_graphs(workflow_path: Union[pathlib.Path],
                verbose: bool = False):
    
    if verbose:
        print(f"Working on {workflow_path}")
    graphs = []

    for path in workflow_path.glob("*.json"):
        graph = create_graph(path)
        annotate(graph)
        graph.graph["name"] = path.stem
        graphs.append(graph)
    
    if not graphs:
        raise ValueError(f"No graphs found in {workflow_path}")

    if verbose:
        print("Constructed graphs")

    sorted_graphs = sorted(graphs, key=lambda graph: len(graph.nodes))
    return sorted_graphs

def save_microstructures(workflow_path: Union[pathlib.Path], 
                         savedir: pathlib.Path, 
                         verbose: bool = False, 
                         img_type: Optional[str] = 'png',
                         cutoff: int = 4000,
                         highlight_all_instances: bool = False
                        ):
    summary = {
        "frequencies": {},
        "base_graphs": {}
    }
    

    for graph in sort_graphs(workflow_path, verbose):
        if graph.order() > cutoff:
            print(f'This and the next workflows have more than {cutoff} tasks')
            break
    
        if verbose:
            print(f"Running for {graph.name}")
        g_savedir = savedir.joinpath(graph.name)
        g_savedir.mkdir(exist_ok=True, parents=True)

        base_graph_path = g_savedir.joinpath("base_graph.pickle")
        write_gpickle(graph, str(base_graph_path))
        summary["base_graphs"][graph.name] = {
            "size": graph.size(),
            "order": graph.order()
        }

        if img_type:
            base_graph_image_path = g_savedir.joinpath(f"base_graph")
            if verbose:
                print(f"Drawing base graph to {base_graph_image_path}")
            draw(graph, close=True, legend=False, extension= img_type, save=str(base_graph_image_path))

        if verbose:
            print("Finding microstructures")

        microstructures = find_microstructures(graph, verbose=verbose)
        mdatas = {}
        for _, (ms_hash, instances) in enumerate(microstructures.items()):
            ms_name = f"microstructure_{ms_hash}"

            summary["frequencies"].setdefault(ms_name, [])
            summary["frequencies"][ms_name].append((graph.order(), len(instances)))
            mdatas[ms_name] = {
                "name": ms_name,
                "nodes": list(map(list, instances)),
                "frequency": len(instances),
                "base_graph_path": str(base_graph_path),
            }
            if img_type:
                print(f"Drawing {ms_name}")
                draw(
                    graph, 
                    subgraph=list(instances)[0] if not highlight_all_instances else set.union(*instances),
                    with_labels=False, 
                    extension=img_type,
                    save=str(g_savedir.joinpath(ms_name)), 
                    close=True
                )
            
        if verbose:
            print()
                
        g_savedir.joinpath("microstructures").with_suffix(".json").write_text(json.dumps(mdatas, indent=2)) 

    savedir.joinpath("summary").with_suffix(".json").write_text(json.dumps(summary, indent=2)) 
        
def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help="Directory of workflow JSONs", type=pathlib.Path)
    parser.add_argument("-v", "--verbose", action="store_true", help="print logs")
    parser.add_argument("-n", "--name", help="name for workflow")
    parser.add_argument("-d", "--draw", default='png', help="output types for images. anything that matplotlib supports (png, jpg, pdf, etc.). Default is None.")
    parser.add_argument("-c", "--cutoff", type=int, default=4000, help="max order of workflow")
    parser.add_argument("-l", "--highlight-all-instances", action="store_true", help="if set, highlights all instances of the microstructure")

    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()
    outpath = this_dir.joinpath("microstructures", args.name)

    save_microstructures(
        args.path, outpath, args.verbose, img_type=args.draw, cutoff=args.cutoff,
        highlight_all_instances=args.highlight_all_instances
    )

if __name__ == "__main__":
    main()
    