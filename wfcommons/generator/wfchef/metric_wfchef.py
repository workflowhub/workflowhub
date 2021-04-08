import networkx as nx
from typing import Tuple, Optional, List
from wfchef.utils import create_graph, annotate, draw
from wfchef.duplicate import duplicate, NoMicrostructuresError
import argparse
import pathlib 
import numpy as np
import json
import pickle 
import pandas as pd

this_dir = pathlib.Path(__file__).resolve().parent

def compare_on(synth: nx.DiGraph, real: nx.DiGraph, attr: str) -> float:
    return next(nx.optimize_graph_edit_distance(
            real, synth, 
            node_match=lambda x, y: x[attr] == y[attr], 
            node_del_cost=lambda *x: 1.0, node_ins_cost=lambda *x: 1.0, 
            edge_del_cost=lambda *x: 1.0, edge_ins_cost=lambda *x: 1.0
        )
    )


def compare(synth: nx.DiGraph, real: nx.DiGraph):
    approx_num_edits = compare_on(synth, real, "type")
    print(synth.size())
    print(real.size())
    print(approx_num_edits)
    print(f"{approx_num_edits}/{real.size()}")
    print()
    return approx_num_edits / real.size()


def get_parser()-> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "workflow", 
        choices=[path.stem for path in this_dir.joinpath("microstructures").glob("*") if path.is_dir()],
        help="Workflow to duplicate"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="print logs")
    parser.add_argument("--no-cache", action="store_true", help="if set, everything is recomputed from scratch")

    return parser

def plot_metric(graph1: str, graph2: str, dist: float):
    pass


def main():
    parser = get_parser()
    args = parser.parse_args()
    verbose = args.verbose

    workflow = this_dir.joinpath("microstructures", args.workflow)
    metric_dir = workflow.joinpath('metric')
    metric_dir.mkdir(parents=True, exist_ok=True)
    results_path = metric_dir.joinpath("results.json")    
    summary = json.loads(workflow.joinpath("summary.json").read_text())
    sorted_graphs = sorted([name for name, _ in summary["base_graphs"].items()], key=lambda name: summary["base_graphs"][name]["order"])

    results = {}
    if not args.no_cache and results_path.is_file():
        results = json.loads(results_path.read_text())

    labels = [f"{graph} ({summary['base_graphs'][graph]['order']})" for graph in sorted_graphs]
    labels = [summary['base_graphs'][graph]['order'] for graph in sorted_graphs]
    rows = [[None for _ in range(len(sorted_graphs))] for _ in range(len(sorted_graphs))]
    
    for i, path in enumerate(sorted_graphs[1:], start=1):
        if verbose:
            print(f"TEST {i} ({path})")
        path = workflow.joinpath(path)
        wf_real = pickle.loads(path.joinpath("base_graph.pickle").read_bytes())
        results.setdefault(wf_real.name, {})

        for j, base in enumerate(sorted_graphs[:i+1]):           
            if verbose:
                print(f"Created real graph ({wf_real.order()} nodes)")
            
            try:
                wf_synth = duplicate(
                    path=workflow,
                    base=base,
                    num_nodes=wf_real.order(),
                    interpolate_limit=summary["base_graphs"][base]["order"]
                ) 
            except NoMicrostructuresError:
                print(f"No Microstructures Error")
                continue
            
            
            dist = results.get(wf_real.name, {}).get(wf_synth.name, {}).get("dist")
            not_in_cache = dist is None
            if not_in_cache:
                dist = compare(wf_synth, wf_real)
                results[wf_real.name][wf_synth.name] = {
                    "real": wf_real.order(),
                    "synth": wf_synth.order(),
                    "base": summary['base_graphs'][base]['order'],
                    "dist": dist
                }

            rows[j][i] = dist
            if verbose:
                print(f"Created synthetic graph with {wf_synth.order()} nodes from {summary['base_graphs'][base]['order']}-node graph ({base})")
                print(dist)
                print()

            if not_in_cache: # if it's cached, no need to write
                results_path.write_text(json.dumps(results, indent=2)) 
                df = pd.DataFrame(rows, columns=labels, index=labels)
                df = df.dropna(axis=1, how='all')
                df = df.dropna(axis=0, how='all')
                workflow.joinpath("results.csv").write_text(df.to_csv())

if __name__ == "__main__":
    main()