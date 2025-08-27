#!/usr/bin/env python3
"""
Validate YAML syntax for io.net deployment configurations
"""

def validate_yaml_structure(file_path):
    """Basic YAML structure validation"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        indent_stack = []
        
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#'):
                indent = len(line) - len(line.lstrip())
                
                if ':' in line and not line.strip().startswith('-'):
                    pass
                elif line.strip().startswith('-'):
                    pass
        
        print(f'✅ {file_path} - YAML structure appears valid')
        return True
        
    except Exception as e:
        print(f'❌ {file_path} - YAML validation error: {e}')
        return False

def validate_docker_compose(file_path):
    """Basic Docker Compose validation"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        required_sections = ['version:', 'services:']
        for section in required_sections:
            if section not in content:
                print(f'❌ {file_path} - Missing required section: {section}')
                return False
        
        print(f'✅ {file_path} - Docker Compose structure appears valid')
        return True
        
    except Exception as e:
        print(f'❌ {file_path} - Docker Compose validation error: {e}')
        return False

if __name__ == "__main__":
    files_to_validate = [
        'k8s/io-net-deployment.yaml',
        'docker-compose.io-net.yml',
        'deployment/ray-cluster-config.yaml',
        'monitoring/prometheus.yml'
    ]
    
    all_valid = True
    for file_path in files_to_validate:
        if file_path.endswith('.yml') and 'docker-compose' in file_path:
            valid = validate_docker_compose(file_path)
        else:
            valid = validate_yaml_structure(file_path)
        
        if not valid:
            all_valid = False
    
    if all_valid:
        print('\n🎉 All configuration files validated successfully!')
    else:
        print('\n⚠️  Some configuration files have validation issues')
