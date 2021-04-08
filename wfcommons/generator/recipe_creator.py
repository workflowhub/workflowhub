from wfchef.find_microstructures import save_microstructures
from wfchef.chef import create_recipe
from wfchef.metric_wfchef import compare
from wfchef.duplicate import duplicate, NoMicrostructuresError
import numpy as np
import json
import pickle 
import pandas as pd
import pathlib

class RecipeCreator:
    #Taken from chef.py's main
    def create_recipe(self, name: str) -> None:
        parent = pathlib.Path(__file__).resolve().parent
        src = parent.joinpath("microstructures", name)
        dst = src.joinpath("recipe")
        create_recipe(src, dst)
    
        print("Done! To install the package, run: \n")
        print(f"  pip install {dst}")
        print("\nor, in editable mode:\n")
        print(f"  pip install -e {dst}")
    
    #Taken from find_microstructurs.py's main
    def find_microstructures(self, filePath: str, name: str) -> None:
        path = pathlib.Path(filePath).resolve()
        parent = pathlib.Path(__file__).resolve().parent
        
        outpath = parent.joinpath("microstructures", name)
        
        save_microstructures(path, outpath)
    
    #Taken from mertric_wfchef.py's main    
    def metric(self, name: str, no_cache: bool = False) -> None:
        verbose = True
        this_dir = pathlib.Path(__file__).resolve().parent
        
        workflow = this_dir.joinpath("microstructures", name)
        metric_dir = workflow.joinpath('metric')
        metric_dir.mkdir(parents=True, exist_ok=True)
        results_path = metric_dir.joinpath("results.json")    
        summary = json.loads(workflow.joinpath("summary.json").read_text())
        sorted_graphs = sorted([name for name, _ in summary["base_graphs"].items()], key=lambda name: summary["base_graphs"][name]["order"])
    
        results = {}
        if not no_cache and results_path.is_file():
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

        