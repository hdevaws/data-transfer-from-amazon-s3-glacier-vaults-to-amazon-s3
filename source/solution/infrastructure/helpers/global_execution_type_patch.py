"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import json
from typing import Any, Dict, Union
from aws_cdk.aws_stepfunctions import CfnStateMachine


def apply_global_execution_type_patch():
    """Apply a global patch to ensure all state machines have ExecutionType in ProcessorConfig."""
    
    # Store the original property setter
    original_definition_string_setter = CfnStateMachine.definition_string.fset
    
    def patched_definition_string_setter(self, value):
        if value:
            try:
                definition = json.loads(value)
                fix_processor_configs_recursive(definition)
                value = json.dumps(definition)
            except (json.JSONDecodeError, Exception):
                # If we can't parse, leave as is
                pass
        # Call the original setter
        original_definition_string_setter(self, value)
    
    # Apply the patch to the property setter
    CfnStateMachine.definition_string = CfnStateMachine.definition_string.setter(patched_definition_string_setter)


def fix_processor_configs_recursive(obj: Any) -> None:
    """Recursively fix all ProcessorConfig entries to include ExecutionType."""
    if isinstance(obj, dict):
        # Fix ProcessorConfig if found
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {}
            obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Special handling for Map states
        if "Type" in obj and obj["Type"] == "Map":
            if "ItemProcessor" in obj:
                if not isinstance(obj["ItemProcessor"], dict):
                    obj["ItemProcessor"] = {}
                if "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {}
                obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
                
                # Fix nested states within ItemProcessor
                if "States" in obj["ItemProcessor"]:
                    fix_processor_configs_recursive(obj["ItemProcessor"]["States"])
        
        # Recursively process all values
        for value in obj.values():
            fix_processor_configs_recursive(value)
            
    elif isinstance(obj, list):
        # Recursively process all list items
        for item in obj:
            fix_processor_configs_recursive(item)


# Apply the patch when this module is imported
apply_global_execution_type_patch()