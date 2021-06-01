#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 The WfCommons Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Dict, Optional, Set

from wfcommons.generator.workflow.abstract_recipe import WorkflowRecipe
from wfcommons.common.workflow import Workflow

from wfcommons.wfchef.duplicate import duplicate

import pathlib 
import pickle
import networkx as nx
import numpy as np
import pandas as pd
import json

this_dir = pathlib.Path(__file__).resolve().parent


class GenomeRecipe(WorkflowRecipe):
    """A Genome workflow recipe class for creating synthetic workflow traces.

    :param num_pairs: The number of pair of signals to estimate earthquake STFs.
    :type num_pairs: int
    :param data_footprint: The upper bound for the workflow total data footprint (in bytes).
    :type data_footprint: int
    :param num_tasks: The upper bound for the total number of tasks in the workflow.
    :type num_tasks: int
    """

    def __init__(self,
                 data_footprint: Optional[int] = 0,
                 num_tasks: Optional[int] = 3,
                 exclude_graphs: Set[str] = set(),
                 **kwargs) -> None:
        super().__init__("Genome", data_footprint, num_tasks)
        self.exclude_graphs = exclude_graphs

    def generate_nx_graph(self) -> nx.DiGraph:
        summary_path = this_dir.joinpath("microstructures", "summary.json")
        summary = json.loads(summary_path.read_text())

        metric_path = this_dir.joinpath("microstructures", "metric", "err.csv")
        df = pd.read_csv(str(metric_path), index_col=0)
        df = df.drop(self.exclude_graphs, axis=0, errors="ignore")
        df = df.drop(self.exclude_graphs, axis=1, errors="ignore")
        for col in df.columns:
            df.loc[col, col] = np.nan

        reference_orders = [summary["base_graphs"][col]["order"] for col in df.columns]
        idx = np.argmin([abs(self.num_tasks - ref_num_tasks) for ref_num_tasks in reference_orders])
        reference = df.columns[idx]

        base = df.index[df[reference].argmin()]
        graph = duplicate(this_dir.joinpath("microstructures"), base, self.num_tasks)
        return graph

    @classmethod
    def from_num_tasks(cls, num_tasks: int, exclude_graphs: Set[str] = set()) -> 'GenomeRecipe':
        """
        Instantiate a Genome workflow recipe that will generate synthetic workflows up to
        the total number of tasks provided.

        :param num_tasks: The upper bound for the total number of tasks in the workflow (at least 3).
        :type num_tasks: int

        :return: A Genome workflow recipe object that will generate synthetic workflows up
                 to the total number of tasks provided.
        :rtype: GenomeRecipe
        """
        return GenomeRecipe(num_tasks=num_tasks, exclude_graphs=exclude_graphs)

    def _load_base_graph(self) -> nx.DiGraph:
        return pickle.loads(this_dir.joinpath("base_graph.pickle").read_bytes())

    def _load_microstructures(self) -> Dict:
        return json.loads(this_dir.joinpath("microstructures.json").read_text())

    def build_workflow(self, workflow_name: Optional[str] = None) -> Workflow:
        """Generate a synthetic workflow trace of a Genome workflow.

        :param workflow_name: The workflow name
        :type workflow_name: int

        :return: A synthetic workflow trace object.
        :rtype: Workflow
        """
        workflow = Workflow(name=self.name + "-synthetic-trace" if not workflow_name else workflow_name, makespan=None)
        graph = self.generate_nx_graph()

        task_names = {}
        for node in graph.nodes:
            if node in ["SRC", "DST"]:
                continue
            node_type = graph.nodes[node]["type"]
            task_name = self._generate_task_name(node_type)
            task = self._generate_task(node_type, task_name)
            workflow.add_node(task_name, task=task)

            task_names[node] = task_name

        for (src, dst) in graph.edges:
            if src in ["SRC", "DST"] or dst in ["SRC", "DST"]:
                continue
            workflow.add_edge(task_names[src], task_names[dst])        
        
        workflow.nxgraph = graph
        self.workflows.append(workflow)
        return workflow

    def _workflow_recipe(self) -> Dict:
        """
        Recipe for generating synthetic traces of the Genome workflow. Recipes can be
        generated by using the :class:`~workflowhub.trace.trace_analyzer.TraceAnalyzer`.

        :return: A recipe in the form of a dictionary in which keys are task prefixes.
        :rtype: Dict[str, Any]
        """
        return json.loads(this_dir.joinpath("task_type_stats.json").read_text())
