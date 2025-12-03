"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aws_cdk import aws_stepfunctions as sfn
from constructs import Construct


@dataclass
class ResultConfig:
    result_selector: Optional[Dict[str, Any]] = None
    result_writer: Optional[Dict[str, Any]] = None
    result_path: Optional[str] = None


@dataclass
class ItemReaderConfig:
    item_reader_resource: Optional[str] = None
    reader_config: Optional[Dict[str, Any]] = None
    item_reader_parameters: Optional[Dict[str, Any]] = None


class DistributedMap(sfn.CustomState):
    def __init__(
        self,
        scope: Construct,
        distributed_map_id: str,
        definition: sfn.IChainable,
        item_reader_config: ItemReaderConfig,
        result_config: ResultConfig,
        execution_type: Optional[str] = "STANDARD",
        max_concurrency: Optional[int] = None,
        items_path: Optional[str] = None,
        item_selector: Optional[Dict[str, Any]] = None,
        max_items_per_batch: Optional[int] = None,
        catch: Optional[List[Dict[str, Any]]] = None,
        retry: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        # Get states from definition
        inline_map = sfn.Map(scope, f"{distributed_map_id}InlineMap")
        inline_map.item_processor(definition)
        map_json = inline_map.to_state_json()
        
        # Create state JSON with proper ExecutionType
        state_json: Dict[str, Any] = {
            "Type": "Map",
            "ItemProcessor": map_json.get("ItemProcessor", {})
        }
        
        # Add optional parameters FIRST
        for key, value in {
            "MaxConcurrency": max_concurrency,
            "ItemSelector": item_selector,
            "ItemsPath": items_path,
            "ResultSelector": result_config.result_selector,
            "ResultWriter": result_config.result_writer,
            "ResultPath": result_config.result_path,
            "Catch": catch,
            "Retry": retry,
        }.items():
            if value is not None:
                state_json[key] = value
        
        # Set mode and distributed map features
        if item_reader_config.item_reader_resource is not None:
            state_json["ItemProcessor"]["ProcessorConfig"] = {
                "Mode": "DISTRIBUTED",
                "ExecutionType": "STANDARD"
            }
            state_json["ItemReader"] = {
                "Resource": item_reader_config.item_reader_resource,
                "ReaderConfig": item_reader_config.reader_config,
                "Parameters": item_reader_config.item_reader_parameters,
            }
            
            if max_items_per_batch is not None:
                state_json["ItemBatcher"] = {
                    "MaxItemsPerBatch": max_items_per_batch,
                }
        else:
            state_json["ItemProcessor"]["ProcessorConfig"] = {
                "Mode": "INLINE"
            }
            if "ResultWriter" in state_json:
                del state_json["ResultWriter"]
        
        super().__init__(scope, distributed_map_id, state_json=state_json)