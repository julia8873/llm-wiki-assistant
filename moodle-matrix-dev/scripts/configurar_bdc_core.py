"""! @file configurar_bdc_core.py
@brief Script núcleo para aprovisionar el repositorio maestro de una asignatura en GitHub.

Este script interactúa con la API REST de GitHub usando el PAT centralizado en
`config/config.yaml` y propagado a la variable de entorno `GITHUB_PAT` por `instalar.sh` para:
1. Crear un repositorio privado para la asignatura a partir de BdC-template.
2. Marcar el repositorio resultante como "template".
3. Añadir a los profesores proporcionados como colaboradores con permisos "maintain".

@author LLM Wiki Assistant Team
@date 2026
"""

import sys
import yaml
import httpx
import os

def load_config():
    """!
    @brief Lee y procesa el archivo central de configuración config.yaml.
    @return dict Diccionario con los parámetros de configuración (e.g. organización, API base).
    """
    config_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    """!
    @brief Función principal del script.
    @details
    Lee los argumentos por línea de comandos (asignatura y profesores),
    obtiene la configuración y el Token de GitHub (GITHUB_PAT), e invoca
    los endpoints de GitHub API para crear la plantilla de curso oficial
    y configurar permisos.
    """
    if len(sys.argv) < 3:
        print("Uso: python configurar_bdc_core.py <Asignatura> <Profesor1,Profesor2>")
        sys.exit(1)

    asignatura = sys.argv[1]
    profesores = sys.argv[2].split(',')

    config = load_config()
    
    org = config['github']['organizacion']
    template_repo = config['github']['repo_plantilla']
    api_base = config['github']['api_base_url']
    
    pat = config['github'].get('pat') or os.getenv('GITHUB_PAT')
    if not pat:
        print("Error: GITHUB_PAT no está definido en el entorno.")
        sys.exit(1)

    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json"
    }

    repo_oficial = f"{asignatura}-Oficial"

    with httpx.Client(headers=headers, base_url=api_base) as client:
        # 1. Crear el repositorio maestro desde la plantilla
        print(f"Generando repositorio maestro {org}/{repo_oficial} a partir de {template_repo}...")
        res = client.post(
            f"/repos/{org}/{template_repo}/generate",
            json={
                "owner": org,
                "name": repo_oficial,
                "private": True,
                "include_all_branches": False
            }
        )

        if res.status_code not in (201, 200, 422):
            print(f"Error al generar repositorio: {res.status_code} {res.text}")
            sys.exit(1)
        elif res.status_code == 422:
            print("El repositorio ya existe. Procediendo a añadir colaboradores...")
        else:
            print("Repositorio generado exitosamente.")
            
        # 1.5. Marcar como plantilla para que los alumnos puedan generar sus repos desde él
        # NOTA: github generate requiere que el template esté marcado como is_template=True
        print(f"Marcando {org}/{repo_oficial} como template...")
        res_patch = client.patch(
            f"/repos/{org}/{repo_oficial}",
            json={"is_template": True}
        )
        if res_patch.status_code != 200:
            print(f"Aviso: No se pudo marcar como template ({res_patch.status_code})")

        # 2. Añadir profesores como colaboradores (maintain)
        for profe in profesores:
            profe = profe.strip()
            if not profe:
                continue

            if profe.lower() == org.lower():
                print(f"Saltando a {profe}: es el propietario del repositorio y ya tiene permisos.")
                continue
            
            print(f"Añadiendo a {profe} con permisos de maintain...")
            res_collab = client.put(
                f"/repos/{org}/{repo_oficial}/collaborators/{profe}",
                json={"permission": "maintain"}
            )
            
            if res_collab.status_code in (201, 204):
                print(f"  -> {profe} añadido exitosamente.")
            else:
                print(f"  -> Error al añadir a {profe}: {res_collab.status_code} {res_collab.text}")

if __name__ == "__main__":
    main()
