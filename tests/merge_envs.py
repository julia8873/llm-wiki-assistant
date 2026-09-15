import os

def parse_env(file_path):
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('=', 1)
                if len(parts) == 2:
                    env_vars[parts[0]] = parts[1]
    return env_vars

def merge_files(base_path, fallback_path, out_path):
    # Read the exact content of base_path to preserve comments and structure
    base_content = ""
    if os.path.exists(base_path):
        with open(base_path, 'r', encoding='utf-8') as f:
            base_content = f.read()
    
    base_vars = parse_env(base_path)
    fallback_vars = parse_env(fallback_path)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(base_content)
        f.write("\n\n# --- Variables from root .env ---\n")
        for key, val in fallback_vars.items():
            if key not in base_vars:
                f.write(f"{key}={val}\n")

if __name__ == "__main__":
    # Merge .env
    merge_files('moodle-matrix-dev/.env', '.env', '.env.new')
    os.replace('.env.new', '.env')
    
    # Merge .env.example
    merge_files('moodle-matrix-dev/.env.example', '.env.example', '.env.example.new')
    os.replace('.env.example.new', '.env.example')
    
    # Remove the inner envs
    if os.path.exists('moodle-matrix-dev/.env'):
        os.remove('moodle-matrix-dev/.env')
    if os.path.exists('moodle-matrix-dev/.env.example'):
        os.remove('moodle-matrix-dev/.env.example')
    
    print("Envs merged successfully.")
