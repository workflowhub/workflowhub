from wfchef.find_microstructures import save_microstructures
from wfchef.chef import create_recipe
from wfchef.duplicate import duplicate, NoMicrostructuresError
from wfchef.utils import draw, create_graph
from typing import Iterable, Union, Set, Optional, Tuple, Dict, Hashable, List
from .workflow.abstract_recipe import WorkflowRecipe
import subprocess
import numpy as np
import json
import pickle 
import pandas as pd
import pathlib
import math

def graph_orders(path: pathlib.Path):
    return sorted([(g.stem, create_graph(g).order()) for g in path.glob("*.json")], key=lambda e: e[1])

def recipe_to_json(workflow_recipe: WorkflowRecipe, base_on: pathlib.Path, save: str = None, runs: int = 1):
    parent = pathlib.Path(__file__).resolve().parent
    _savedir = parent.joinpath(f"{workflow_recipe.name}-synth") if save is None else pathlib.Path(save)

    zpad = math.ceil(math.log(runs, 10))
    for run in range(runs):
        savedir = _savedir if runs <= 1 else _savedir.joinpath(f"wfchef_run_{str(run).zfill(zpad)}")
        savedir.mkdir(parents=True, exist_ok=True)

        Recipe = workflow_recipe
        for i, (name, order) in enumerate(graph_orders(base_on)):
            try:
                recipe = Recipe.from_num_tasks(order, exclude_graphs=[name])
            except ValueError:
                print(f"Skipping: {name}")
                continue
            wf = recipe.build_workflow()
            file = savedir.joinpath(f'wfchef_{workflow_recipe.name}_{order}_{i}.json')
            wf.write_json(str(file)) 


class RecipeCreator:
    #Taken from chef.py's main
    def create_recipe(self, name: str, r: int = 1, install: bool = False) -> None:
        parent = pathlib.Path(__file__).resolve().parent
        src = parent.joinpath("microstructures", name)
        dst = src.joinpath("recipe")
        create_recipe(src, dst, runs=r)
    
        if install:
            proc = subprocess.Popen(["pip", "install", str(dst)])
            proc.wait()
        else:
            print("Done! To install the package, run: \n")
            print(f"  pip install {dst}")
            print("\nor, in editable mode:\n")
            print(f"  pip install -e {dst}")
    
    #Taken from find_microstructurs.py's main
    def find_microstructures(self, filePath: str, name: str, verbose: bool = False, img_type: Optional[str] = 'png', cutoff: int = 4000, highlight_all_instances: bool = False) -> None:
        path = pathlib.Path(filePath).resolve()
        parent = pathlib.Path(__file__).resolve().parent
        
        outpath = parent.joinpath("microstructures", name)
        
        save_microstructures(path, outpath, verbose, img_type, cutoff, highlight_all_instances)
        
    
    def duplicate(self, name: str, base: Union[str, pathlib.Path], size: int, outpath: pathlib.Path, extension: str = "png") -> None:
        parent = pathlib.Path(__file__).resolve().parent
        path = parent.joinpath("microstructures", name)
        graph = duplicate(path, base, num_nodes=size)
        
        duplicated = {node for node in graph.nodes if "duplicate_of" in graph.nodes[node]}
    
        draw(graph, save=outpath, extension=extension, close=True, subgraph=duplicated)
        
    
    

        