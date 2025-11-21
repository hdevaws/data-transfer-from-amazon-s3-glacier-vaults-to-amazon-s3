"""
Ultimate ExecutionType fix that patches at the CloudFormation template level.
This ensures ExecutionType is present in all ProcessorConfig entries.
"""

import json
import re
from typing import Any, Dict
from aws_cdk import App, CfnResource
from aws_cdk.aws_stepfunctions import CfnStateMachine


def fix_processor_configs_in_json_string(json_string: str) -> str:
    """Fix ProcessorConfig entries in a JSON string using regex."""
    # Pattern to match ProcessorConfig objects
    pattern = r'"ProcessorConfig"\s*:\s*\{[^}]*\}'
    
    def fix_config(match):
        config_str = match.group(0)
        if '"ExecutionType"' not in config_str:
            # Check if it's an empty config
            if config_str.endswith('{}'):
                return config_str[:-1] + '"ExecutionType":"STANDARD"}'
            else:
                # Insert ExecutionType before the closing brace
                return config_str[:-1] + ',"ExecutionType":"STANDARD"}'
        return config_str
    
    return re.sub(pattern, fix_config, json_string)


def fix_processor_configs_recursive(obj: Any) -> None:
    """Recursively fix all ProcessorConfig entries."""
    if isinstance(obj, dict):
        # Fix ProcessorConfig if found
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Fix ItemProcessor ProcessorConfig
        if "ItemProcessor" in obj:
            if not isinstance(obj["ItemProcessor"], dict):
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            else:
                if "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                else:
                    obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Special handling for Map states
        if obj.get("Type") == "Map":
            if "ItemProcessor" not in obj:
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
            elif "ProcessorConfig" not in obj["ItemProcessor"]:
                obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
            else:
                obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
        
        # Recursively process all values
        for value in obj.values():
            fix_processor_configs_recursive(value)
            
    elif isinstance(obj, list):
        for item in obj:
            fix_processor_configs_recursive(item)


# Store original App.synth method
_original_app_synth = App.synth

def ultimate_app_synth(self, **kwargs):
    """Ultimate App.synth that fixes all Step Functions definitions."""
    # Call original synth
    result = _original_app_synth(self, **kwargs)
    
    # Fix all Step Functions state machines in all stacks
    for stack in result.stacks:
        template = stack.template
        resources = template.get("Resources", {})
        
        for resource_name, resource in resources.items():
            if resource.get("Type") == "AWS::StepFunctions::StateMachine":
                properties = resource.get("Properties", {})
                definition_string = properties.get("DefinitionString")
                
                if definition_string:
                    if isinstance(definition_string, str):
                        # Direct JSON string
                        try:
                            definition = json.loads(definition_string)
                            fix_processor_configs_recursive(definition)
                            properties["DefinitionString"] = json.dumps(definition)
                        except (json.JSONDecodeError, TypeError):
                            # Try regex fix as fallback
                            properties["DefinitionString"] = fix_processor_configs_in_json_string(definition_string)
                    
                    elif isinstance(definition_string, dict) and "Fn::Join" in definition_string:
                        # CloudFormation Fn::Join
                        parts = definition_string["Fn::Join"][1]
                        for i, part in enumerate(parts):
                            if isinstance(part, str) and "ProcessorConfig" in part:
                                parts[i] = fix_processor_configs_in_json_string(part)
                    
                    elif isinstance(definition_string, dict):
                        # Direct object
                        fix_processor_configs_recursive(definition_string)
    
    return result

# Apply the ultimate fix
App.synth = ultimate_app_synth

print("Ultimate ExecutionType fix applied - all Step Functions will have ExecutionType in ProcessorConfig")