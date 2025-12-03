"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

from typing import Any, Dict, List, Union
import json


def fix_execution_type_in_state_machine(state_machine_definition: Union[str, Dict[str, Any]], execution_type: str = "STANDARD") -> Union[str, Dict[str, Any]]:
    """
    Recursively fix all ProcessorConfig entries in a Step Functions state machine definition
    to ensure they have the ExecutionType field set.
    """
    is_string = isinstance(state_machine_definition, str)
    
    if is_string:
        definition = json.loads(state_machine_definition)
    else:
        definition = state_machine_definition
    
    def fix_processor_configs(obj: Any) -> None:
        if isinstance(obj, dict):
            # Fix ProcessorConfig if found
            if "ProcessorConfig" in obj:
                if not isinstance(obj["ProcessorConfig"], dict):
                    obj["ProcessorConfig"] = {}
                obj["ProcessorConfig"]["ExecutionType"] = execution_type
            
            # Special handling for Map states and ItemProcessor
            if "Type" in obj and obj["Type"] == "Map":
                if "ItemProcessor" in obj:
                    if not isinstance(obj["ItemProcessor"], dict):
                        obj["ItemProcessor"] = {}
                    if "ProcessorConfig" not in obj["ItemProcessor"]:
                        obj["ItemProcessor"]["ProcessorConfig"] = {}
                    obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = execution_type
            
            # Recursively process all values
            for value in obj.values():
                fix_processor_configs(value)
                
        elif isinstance(obj, list):
            # Recursively process all list items
            for item in obj:
                fix_processor_configs(item)
    
    # Apply the fix
    fix_processor_configs(definition)
    
    return json.dumps(definition) if is_string else definition