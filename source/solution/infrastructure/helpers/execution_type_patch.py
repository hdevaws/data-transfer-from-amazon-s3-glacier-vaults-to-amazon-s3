"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

from aws_cdk import aws_stepfunctions as sfn


def patch_map_execution_type():
    """Patch the CDK Map class to always include ExecutionType in ProcessorConfig"""
    
    # Store the original to_state_json method
    original_to_state_json = sfn.Map.to_state_json
    
    def patched_to_state_json(self):
        # Get the original state JSON
        state_json = original_to_state_json(self)
        
        # Recursively fix all ProcessorConfigs
        def fix_processor_configs(obj):
            if isinstance(obj, dict):
                if "ProcessorConfig" in obj:
                    if not isinstance(obj["ProcessorConfig"], dict):
                        obj["ProcessorConfig"] = {}
                    obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
                for value in obj.values():
                    fix_processor_configs(value)
            elif isinstance(obj, list):
                for item in obj:
                    fix_processor_configs(item)
        
        fix_processor_configs(state_json)
        return state_json
    
    # Apply the patch
    sfn.Map.to_state_json = patched_to_state_json


# Apply the patch immediately when this module is imported
patch_map_execution_type()