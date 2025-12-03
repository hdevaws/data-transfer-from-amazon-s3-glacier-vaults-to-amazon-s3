"""
Post-synthesis ExecutionType fix that processes the generated CloudFormation template
to ensure all ProcessorConfig entries have ExecutionType.
"""

import json
from typing import Any


def fix_processor_configs_in_template(template: dict) -> int:
    """
    Fix all ProcessorConfig entries in a CloudFormation template to include ExecutionType.
    Returns the number of fixes applied.
    """
    fixes_applied = 0
    
    resources = template.get("Resources", {})
    
    for resource_name, resource in resources.items():
        if resource.get("Type") == "AWS::StepFunctions::StateMachine":
            definition_string = resource.get("Properties", {}).get("DefinitionString")
            
            if definition_string:
                try:
                    # Parse the definition
                    if isinstance(definition_string, str):
                        definition = json.loads(definition_string)
                    elif isinstance(definition_string, dict) and "Fn::Join" in definition_string:
                        # Handle CloudFormation Fn::Join intrinsic function
                        parts = definition_string["Fn::Join"][1]
                        full_string = ""
                        for part in parts:
                            if isinstance(part, str):
                                full_string += part
                            else:
                                # Replace CloudFormation references with placeholders
                                full_string += "PLACEHOLDER"
                        
                        # Fix ProcessorConfig entries in the string
                        import re
                        def fix_processor_config(match):
                            config = match.group(0)
                            if '"ExecutionType"' not in config:
                                # Handle both empty and non-empty ProcessorConfig
                                if config.endswith('{}'):
                                    config = config[:-1] + '"ExecutionType":"STANDARD"}'
                                else:
                                    config = config[:-1] + ',"ExecutionType":"STANDARD"}'
                            return config
                        
                        # Match ProcessorConfig with any content including empty
                        fixed_string = re.sub(r'"ProcessorConfig":\{[^}]*\}', fix_processor_config, full_string)
                        
                        # Also handle cases where ProcessorConfig might be incomplete
                        if '"ProcessorConfig":' in fixed_string and '"ExecutionType"' not in fixed_string:
                            # Handle incomplete ProcessorConfig patterns
                            fixed_string = re.sub(r'"ProcessorConfig":\{\s*(?=\})', '"ProcessorConfig":{"ExecutionType":"STANDARD"', fixed_string)
                        
                        if fixed_string != full_string:
                            # Reconstruct the Fn::Join with fixed string
                            new_parts = []
                            remaining = fixed_string
                            for i, part in enumerate(parts):
                                if isinstance(part, str):
                                    if i == 0:
                                        # First string part
                                        new_parts.append(remaining[:len(part)])
                                        remaining = remaining[len(part):]
                                    else:
                                        # Find the next string part
                                        placeholder_end = remaining.find(part)
                                        if placeholder_end > 0:
                                            remaining = remaining[placeholder_end:]
                                        new_parts.append(remaining[:len(part)])
                                        remaining = remaining[len(part):]
                                else:
                                    new_parts.append(part)
                                    # Skip placeholder in remaining string
                                    placeholder_start = remaining.find("PLACEHOLDER")
                                    if placeholder_start >= 0:
                                        remaining = remaining[placeholder_start + len("PLACEHOLDER"):]
                            
                            # Update the definition string
                            resource["Properties"]["DefinitionString"]["Fn::Join"][1] = new_parts
                            fixes_applied += 1
                        continue
                    else:
                        definition = definition_string
                    
                    # Fix ProcessorConfigs for regular JSON definitions
                    count = fix_processor_configs_recursive(definition)
                    if count > 0:
                        # Update the definition string
                        resource["Properties"]["DefinitionString"] = json.dumps(definition)
                        fixes_applied += count
                        
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Warning: Could not parse DefinitionString in {resource_name}: {e}")
    
    return fixes_applied


def fix_processor_configs_recursive(obj: Any) -> int:
    """Recursively fix all ProcessorConfig entries to include ExecutionType."""
    fixes_applied = 0
    
    if isinstance(obj, dict):
        # Fix ProcessorConfig if found - always ensure ExecutionType is present
        if "ProcessorConfig" in obj:
            if not isinstance(obj["ProcessorConfig"], dict):
                obj["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                fixes_applied += 1
            elif "ExecutionType" not in obj["ProcessorConfig"]:
                obj["ProcessorConfig"]["ExecutionType"] = "STANDARD"
                fixes_applied += 1
        
        # Fix ItemProcessor ProcessorConfig - ensure it exists and has ExecutionType
        if "ItemProcessor" in obj:
            if not isinstance(obj["ItemProcessor"], dict):
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
                fixes_applied += 1
            else:
                if "ProcessorConfig" not in obj["ItemProcessor"]:
                    obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                    fixes_applied += 1
                else:
                    if not isinstance(obj["ItemProcessor"]["ProcessorConfig"], dict):
                        obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                        fixes_applied += 1
                    elif "ExecutionType" not in obj["ItemProcessor"]["ProcessorConfig"]:
                        obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
                        fixes_applied += 1
        
        # Special handling for Map states - ensure they have proper ProcessorConfig
        if obj.get("Type") == "Map":
            if "ItemProcessor" not in obj:
                obj["ItemProcessor"] = {"ProcessorConfig": {"ExecutionType": "STANDARD"}}
                fixes_applied += 1
            elif "ProcessorConfig" not in obj["ItemProcessor"]:
                obj["ItemProcessor"]["ProcessorConfig"] = {"ExecutionType": "STANDARD"}
                fixes_applied += 1
            elif "ExecutionType" not in obj["ItemProcessor"]["ProcessorConfig"]:
                obj["ItemProcessor"]["ProcessorConfig"]["ExecutionType"] = "STANDARD"
                fixes_applied += 1
        
        # Recursively process all values
        for value in obj.values():
            fixes_applied += fix_processor_configs_recursive(value)
            
    elif isinstance(obj, list):
        for item in obj:
            fixes_applied += fix_processor_configs_recursive(item)
    
    return fixes_applied