
import pathlib
import json
from workflowhub.generator.workflow.abstract_recipe import WorkflowRecipe, Workflow
from typing import Optional, Union, Dict, Any
import argparse
import shutil
from stringcase import camelcase, snakecase
import pickle
from wfchef.duplicate import duplicate, NoMicrostructuresError
import pandas as pd
import networkx as nx
import math
import subprocess
import numpy as np

this_dir = pathlib.Path(__file__).resolve().parent
skeleton_path = this_dir.joinpath("skeletons")

def compare_rmse(synth_graph: nx.DiGraph, real_graph: nx.DiGraph):
    synthetic = {}
    real = {}
    
    for node in synth_graph.nodes:
        _type = synth_graph.nodes[node]['type_hash']
        synthetic.setdefault(_type, 0)
        synthetic[_type] +=1 

    for node in real_graph.nodes:
        _type = real_graph.nodes[node]['type_hash']
        real.setdefault(_type, 0)
        real[_type] +=1 
    
    _types = ({*synthetic.keys(), *real.keys()})

    mse = math.sqrt(sum([
        (real.get(_type, 0) - synthetic.get(_type, 0))**2
        for _type in _types
    ]) / len(_types))
    return mse / real_graph.order()

def find_err(workflow: Union[str, pathlib.Path], 
             err_savepath: Optional[Union[str, pathlib.Path]] = None,
             always_update: bool = False,
             runs: int = 1) -> None:
    summary = json.loads(workflow.joinpath("summary.json").read_text())
    sorted_graphs = sorted([name for name, _ in summary["base_graphs"].items()], key=lambda name: summary["base_graphs"][name]["order"])
    
    if err_savepath:
        err_savepath = pathlib.Path(err_savepath)
        err_savepath.parent.mkdir(exist_ok=True, parents=True)
        
    labels = [graph for graph in sorted_graphs]
    rows = [[None for _ in range(len(sorted_graphs))] for _ in range(len(sorted_graphs))]
    df = None 
    for i, path in enumerate(sorted_graphs[1:], start=1):
        path = workflow.joinpath(path)
        wf_real = pickle.loads(path.joinpath("base_graph.pickle").read_bytes())

        for j, base in enumerate(sorted_graphs[:i+1]):             
            try:
                dists = []
                for _ in range(runs):
                    wf_synth = duplicate(
                        path=workflow,
                        base=base,
                        num_nodes=wf_real.order(),
                        interpolate_limit=summary["base_graphs"][base]["order"]
                    )
                    dists.append(compare_rmse(wf_synth, wf_real))
                rows[j][i] = np.median(dists)
            except NoMicrostructuresError:
                print(f"No Microstructures Error")
                continue  

            if err_savepath is not None and always_update:
                df = pd.DataFrame(rows, columns=labels, index=labels)
                df = df.dropna(axis=1, how='all')
                df = df.dropna(axis=0, how='all')
                err_savepath.write_text(df.to_csv())

    df = pd.DataFrame(rows, columns=labels, index=labels)
    df = df.dropna(axis=1, how='all')
    df = df.dropna(axis=0, how='all')
    if err_savepath:
        err_savepath.write_text(df.to_csv())
    return df

def create_recipe(path: Union[str, pathlib.Path], dst: Union[str, pathlib.Path], runs: int = 1) -> WorkflowRecipe:
    err_savepath = path.joinpath("metric", "err.csv")
    err_savepath.parent.mkdir(exist_ok=True, parents=True)
    df = find_err(path, runs=runs)

    err_savepath.write_text(df.to_csv())
    
    path = pathlib.Path(path).resolve(strict=True)
    wf_name = f"Workflow{camelcase(path.stem)}"
    dst = pathlib.Path(dst, snakecase(wf_name)).resolve()
    dst.mkdir(exist_ok=True, parents=True)

    dst_metric_path = dst.joinpath("metric", "err.csv")
    dst_metric_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(path.joinpath("metric", "err.csv"), dst_metric_path)
    
    summary_path = dst.joinpath("microstructures", "summary.json")
    summary_path.parent.mkdir(exist_ok=True, parents=True)
    shutil.copy(path.joinpath("summary.json"), summary_path)
    for filename in ["base_graph.pickle", "microstructures.json"]:
        for p in path.glob(f"*/{filename}"):
            dst_path = dst.joinpath("microstructures", p.parent.stem, filename)
            dst_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(p, dst_path)

    # Recipe 
    with skeleton_path.joinpath("recipe.py").open() as fp:
        skeleton_str = fp.read() 

    skeleton_str = skeleton_str.replace("Skeleton", wf_name)
    skeleton_str = skeleton_str.replace("skeleton", snakecase(wf_name))
    with this_dir.joinpath(dst.joinpath("__init__.py")).open("w+") as fp:
        fp.write(skeleton_str)

    # setup.py 
    with skeleton_path.joinpath("setup.py").open() as fp:
        skeleton_str = fp.read() 
        
    skeleton_str = skeleton_str.replace("Skeleton", wf_name)
    skeleton_str = skeleton_str.replace("skeleton", snakecase(wf_name))
    with this_dir.joinpath(dst.parent.joinpath("setup.py")).open("w+") as fp:
        fp.write(skeleton_str)

    # MANIFEST
    with skeleton_path.joinpath("MANIFEST.in").open() as fp:
        skeleton_str = fp.read() 
        
    skeleton_str = skeleton_str.replace("Skeleton", wf_name)
    skeleton_str = skeleton_str.replace("skeleton", snakecase(wf_name))
    with this_dir.joinpath(dst.parent.joinpath("MANIFEST.in")).open("w+") as fp:
        fp.write(skeleton_str)

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w", "--workflow", 
        choices=[path.stem for path in this_dir.joinpath("microstructures").glob("*") if path.is_dir()],
        required=True,
        help="Workflow to duplicate"
    )
    parser.add_argument(
        "-i", "--install",
        action="store_true",
        help="if set, automatically installs the package"
    )
    parser.add_argument(
        "-r", "--runs",
        default=1, type=int,
        help="number of runs to compute mean RMSE"
    )
    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()
    src = this_dir.joinpath("microstructures", args.workflow)
    dst = src.joinpath("recipe")
    create_recipe(src, dst, runs=args.runs)

    if args.install:
        proc = subprocess.Popen(["pip", "install", str(dst)])
        proc.wait()
    else:
        print("Done! To install the package, run: \n")
        print(f"  pip install {dst}")
        print("\nor, in editable mode:\n")
        print(f"  pip install -e {dst}")


if __name__ == "__main__":
    main()

