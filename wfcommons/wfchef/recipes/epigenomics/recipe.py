#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 The WfCommons Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import json
import pathlib

from logging import Logger
from typing import Dict, Optional, Set

from wfcommons.wfgen.abstract_recipe import WorkflowRecipe

this_dir = pathlib.Path(__file__).resolve().parent


class EpigenomicsRecipe(WorkflowRecipe):
    """A Epigenomics workflow recipe class for creating synthetic workflow instances.

    :param data_footprint: The upper bound for the workflow total data footprint (in bytes).
    :type data_footprint: int
    :param num_tasks: The upper bound for the total number of tasks in the workflow.
    :type num_tasks: int
    :param exclude_graphs:
    :type exclude_graphs: Set
    :param runtime_factor: The factor of which tasks runtime will be increased/decreased.
    :type runtime_factor: float
    :param input_file_size_factor: The factor of which tasks input files size will be increased/decreased.
    :type input_file_size_factor: float
    :param output_file_size_factor: The factor of which tasks output files size will be increased/decreased.
    :type output_file_size_factor: float
    :param logger: The logger where to log information/warning or errors (optional).
    :type logger: Logger
    """

    def __init__(self,
                 data_footprint: Optional[int] = 0,
                 num_tasks: Optional[int] = 3,
                 exclude_graphs: Set[str] = set(),
                 runtime_factor: Optional[float] = 1.0,
                 input_file_size_factor: Optional[float] = 1.0,
                 output_file_size_factor: Optional[float] = 1.0,
                 logger: Optional[Logger] = None,
                 **kwargs) -> None:
        super().__init__("Epigenomics", data_footprint, num_tasks, exclude_graphs, runtime_factor,
                         input_file_size_factor, output_file_size_factor, logger, this_dir)

    @classmethod
    def from_num_tasks(cls,
                       num_tasks: int,
                       exclude_graphs: Set[str] = set(),
                       runtime_factor: Optional[float] = 1.0,
                       input_file_size_factor: Optional[float] = 1.0,
                       output_file_size_factor: Optional[float] = 1.0
                       ) -> 'EpigenomicsRecipe':
        """
        Instantiate a Epigenomics workflow recipe that will generate synthetic workflows up to
        the total number of tasks provided.

        :param num_tasks: The upper bound for the total number of tasks in the workflow (at least 3).
        :type num_tasks: int
        :param exclude_graphs:
        :type exclude_graphs: Set
        :param runtime_factor: The factor of which tasks runtime will be increased/decreased.
        :type runtime_factor: float
        :param input_file_size_factor: The factor of which tasks input files size will be increased/decreased.
        :type input_file_size_factor: float
        :param output_file_size_factor: The factor of which tasks output files size will be increased/decreased.
        :type output_file_size_factor: float

        :return: A Epigenomics workflow recipe object that will generate synthetic workflows up
                 to the total number of tasks provided.
        :rtype: EpigenomicsRecipe
        """
        return EpigenomicsRecipe(num_tasks=num_tasks, exclude_graphs=exclude_graphs, runtime_factor=runtime_factor,
                                 input_file_size_factor=input_file_size_factor,
                                 output_file_size_factor=output_file_size_factor)

    def _workflow_recipe(self) -> Dict:
        """
        Recipe for generating synthetic instances of the Epigenomics workflow. Recipes can be
        generated by using the :class:`~wfcommons.wfinstances.instance_analyzer.InstanceAnalyzer`.

        :return: A recipe in the form of a dictionary in which keys are task prefixes.
        :rtype: Dict[str, Any]
        """
        return json.loads(this_dir.joinpath("task_type_stats.json").read_text())
