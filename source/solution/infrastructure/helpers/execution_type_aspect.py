"""
CDK Aspect to fix ExecutionType in all Step Functions state machines.
This runs during synthesis and modifies the CloudFormation template directly.
"""

import json
import re
from typing import Any, Dict
from aws_cdk import IAspect, CfnResource
from aws_cdk.aws_stepfunctions import CfnStateMachine
from constructs import IConstruct


class ExecutionTypeAspect(IAspect):
    """CDK Aspect that ensures all ProcessorConfig entries have ExecutionType."""
    
    def visit(self, node: IConstruct) -> None:
        """Visit each construct and fix Step Functions state machines."""
        if isinstance(node, CfnStateMachine):
            self._fix_state_machine(node)
    
    def _fix_state_machine(self, state_machine: CfnStateMachine) -> None:
        """Fix ExecutionType in a Step Functions state machine."""
        # Override the _render_properties method to fix the definition
        original_render = state_machine._render_properties
        
        def patched_render(properties):
            result = original_render(properties)
            if result and "DefinitionString" in result:
                result["DefinitionString"] = self._fix_definition_string(result["DefinitionString"])
            return result
        
        state_machine._render_properties = patched_render
    
    def _fix_definition_string(self, definition_string: Any) -> Any:
        """Fix ExecutionType in a definition string."""
        try:
            if isinstance(definition_string, str):
                # Parse JSON and fix
                data = json.loads(definition_string)
                self._fix_processor_configs(data)
                return json.dumps(data)
            
            elif isinstance(definition_string, dict) and "Fn::Join" in definition_string:
                # Handle CloudFormation Fn::Join
                parts = definition_string["Fn::Join"][1]
                for i, part in enumerate(parts):
                    if isinstance(part, str) and "ProcessorConfig" in part:
                        parts[i] = self._fix_string_part(part)
                return definition_string
            
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        
        return definition_string
    
    def _fix_string_part(self, part: str) -> str:
        """Fix ProcessorConfig entries in a string part."""
        def fix_processor_config(match):
            config = match.group(0)
            if '"ExecutionType"' not in config:
                if config.endswith('{}'):
                    config = config[:-1] + '"ExecutionType":"STANDARD"}'
                else:
                    config = config[:-1] + ',"ExecutionType":"STANDARD"}'
            return config
        
        # Fix ProcessorConfig entries
        fixed_part = re.sub(r'"ProcessorConfig":\{[^}]*\}', fix_processor_config, part)
        
        # Handle empty ProcessorConfig
        fixed_part = re.sub(r'"ProcessorConfig":\{\}', '"ProcessorConfig":{"ExecutionType":"STANDARD"}', fixed_part)
        
        return fixed_part
    
    def _fix_processor_configs(self, obj: Any) -> None:
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
                self._fix_processor_configs(value)
                
        elif isinstance(obj, list):
            for item in obj:
                self._fix_processor_configs(item)