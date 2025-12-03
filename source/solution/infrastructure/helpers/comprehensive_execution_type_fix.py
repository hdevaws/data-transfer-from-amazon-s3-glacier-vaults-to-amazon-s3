"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import json
from typing import Any
from aws_cdk import aws_stepfunctions as sfn


def apply_comprehensive_execution_type_fix():
    """Apply a comprehensive fix to ensure all Map states have ExecutionType in ProcessorConfig."""
    
    # Store the original to_state_json method
    original_to_state_json = sfn.Map.to_state_json
    
    def patched_to_state_json(self):
        # Get the original state JSON
        state_json = original_to_state_json(self)
        
        # Fix all ProcessorConfigs recursively
        fix_processor_configs_recursive(state_json)
        
        return state_json
    
    # Apply the patch to Map class
    sfn.Map.to_state_json = patched_to_state_json
    
    # Also patch CustomState to fix any manually created state JSON
    original_custom_state_init = sfn.CustomState.__init__
    
    def patched_custom_state_init(self, scope, construct_id, **kwargs):
        # Fix state_json if provided
        if "state_json" in kwargs and kwargs["state_json"]:
            fix_processor_configs_recursive(kwargs["state_json"])
        
        # Call original init
        original_custom_state_init(self, scope, construct_id, **kwargs)
    
    # Apply the patch to CustomState class
    sfn.CustomState.__init__ = patched_custom_state_init


def fix_processor_configs_recursive(obj: Any) -> None:
    """Recursively fix all ProcessorConfig entries to include ExecutionType."""
    if isinstance(obj, dict):
        # Fix ProcessorConfig if found
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {}
            if "ExecutionType" not in obj["ProcessorConfig"]:
                obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Special handling for Map states
        if "Type" in obj and obj["Type"] == "Map":
            if "ItemProcessor" in obj:
                if not isinstance(obj["ItemProcessor"], dict):
                    obj["ItemProcessor"] = {}
                if "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {}
                if "ExecutionType" not in obj["ItemProcessor"]["ProcessorConfig"]:
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


# Apply the fix when this module is imported
apply_comprehensive_execution_type_fix()