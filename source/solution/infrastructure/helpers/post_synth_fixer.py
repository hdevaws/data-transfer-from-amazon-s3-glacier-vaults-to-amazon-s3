"""
Post-synthesis fixer for ExecutionType in Step Functions.
"""

import json
import re
from pathlib import Path


def fix_processor_config_in_string(json_str: str) -> str:
    """Fix ProcessorConfig entries in a JSON string."""
    # Handle escaped JSON - only fix DISTRIBUTED mode
    def fix_escaped(match):
        config_str = match.group(0)
        if '\\\"ExecutionType\\\"' not in config_str:
            return config_str[:-1] + ',\\\"ExecutionType\\\":\\\"STANDARD\\\"}'
        return config_str
    
    # Fix escaped ProcessorConfig in Fn::Join strings - DISTRIBUTED only
    pattern_escaped = r'\\"ProcessorConfig\\":\{\\"Mode\\":\\"DISTRIBUTED\\"\}'
    fixed = re.sub(pattern_escaped, fix_escaped, json_str)
    
    # Handle regular JSON - DISTRIBUTED only
    def fix_regular(match):
        config_str = match.group(0)
        if '"ExecutionType"' not in config_str:
            return config_str[:-1] + ',"ExecutionType":"STANDARD"}'
        return config_str
    
    pattern_regular = r'"ProcessorConfig":\{"Mode":"DISTRIBUTED"\}'
    fixed = re.sub(pattern_regular, fix_regular, fixed)
    
    return fixed


def fix_cloudformation_template(template_path: str) -> None:
    """Fix a CloudFormation template to add ExecutionType to all ProcessorConfig entries."""
    with open(template_path, 'r', encoding='utf-8') as f:
        template = json.load(f)
    
    resources = template.get('Resources', {})
    modified = False
    
    for resource_name, resource in resources.items():
        if resource.get('Type') == 'AWS::StepFunctions::StateMachine':
            properties = resource.get('Properties', {})
            definition_string = properties.get('DefinitionString')
            
            if definition_string:
                if isinstance(definition_string, str):
                    # Direct JSON string
                    fixed = fix_processor_config_in_string(definition_string)
                    if fixed != definition_string:
                        properties['DefinitionString'] = fixed
                        modified = True
                        print(f"Fixed {resource_name}")
                
                elif isinstance(definition_string, dict) and 'Fn::Join' in definition_string:
                    # CloudFormation Fn::Join
                    parts = definition_string['Fn::Join'][1]
                    for i, part in enumerate(parts):
                        if isinstance(part, str) and 'ProcessorConfig' in part:
                            fixed = fix_processor_config_in_string(part)
                            if fixed != part:
                                parts[i] = fixed
                                modified = True
                                print(f"Fixed {resource_name} (Fn::Join part {i})")
    
    if modified:
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        print(f"Template {template_path} has been fixed")
    else:
        print(f"No fixes needed for {template_path}")


if __name__ == '__main__':
    # Fix the main template
    template_path = Path(__file__).parent.parent.parent.parent.parent / 'cdk.out' / 'data-transfer-from-amazon-s3-glacier-vaults-to-amazon-s3.template.json'
    if template_path.exists():
        fix_cloudformation_template(str(template_path))
    else:
        print(f"Template not found: {template_path}")
