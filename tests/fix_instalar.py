import re

def fix_instalar():
    with open('instalar.sh', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replacements
    replacements = [
        ("${ROOT_DIR}/moodle-matrix-dev/maubot", "${ROOT_DIR}/src/bot"),
        ("moodle-matrix-dev/maubot", "src/bot"),
        ("${ROOT_DIR}/moodle-matrix-dev/.env.example", "${ROOT_DIR}/.env.example"),
        ("${ROOT_DIR}/moodle-matrix-dev/.env", "${ROOT_DIR}/.env"),
        ("${ROOT_DIR}/moodle-matrix-dev/docker-compose.yml", "${ROOT_DIR}/docker-compose.yml"),
        ("${ROOT_DIR}/moodle-matrix-dev/scripts", "${ROOT_DIR}/scripts"),
        ("moodle-matrix-dev/scripts", "scripts"),
        ("${ROOT_DIR}/moodle-matrix-dev/mapeo-api", "${ROOT_DIR}/src/api"),
        ("moodle-matrix-dev/mapeo-api", "src/api"),
        ('cd "${ROOT_DIR}/moodle-matrix-dev"', 'cd "${ROOT_DIR}"'),
        ('cd "${ROOT_DIR}/moodle-matrix-dev" || true', 'cd "${ROOT_DIR}" || true'),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    # Some lines like: inner_env="${ROOT_DIR}/moodle-matrix-dev/.env" were already covered.
    
    # Save it back
    with open('instalar.sh', 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)

if __name__ == "__main__":
    fix_instalar()
    print("instalar.sh paths fixed.")
