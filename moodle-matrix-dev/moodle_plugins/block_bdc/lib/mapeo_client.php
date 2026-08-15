<?php
/**
 * @file
 * Mapeo API Client.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */


defined('MOODLE_INTERNAL') || die();

require_once($CFG->libdir . '/filelib.php');

/**
 * Cliente HTTP para comunicarse con mapeo-api (Fase 2).
 */
class block_bdc_mapeo_client {
    
    /**
     * Endpoint base del microservicio
     */
    private $baseurl;
    
    /**
     * Token de autorización
     */
    private $token;

    /**
     * Constructor del cliente.
     */
    public function __construct() {
        // En un entorno de producción, estos valores deberían leerse de variables de entorno o config.
        $this->baseurl = getenv('MAPEO_API_URL_INTERNA') ?: 'http://mapeo-api:8000';
        $this->token = getenv('MAPEO_API_TOKEN') ?: 'changeme';
    }

    /**
     * Obtiene el mapeo para un usuario y curso dados.
     *
     * @param int $userid
     * @param int $courseid
     * @return array|null Null si no existe o hay error.
     */
    public function get_mapeo($userid, $courseid) {
        $curl = new \curl(['ignoresecurity' => true]);
        $curl->setHeader('Authorization: Bearer ' . $this->token);
        
        $url = $this->baseurl . '/mapeos?moodle_user_id=' . (int)$userid . '&moodle_course_id=' . (int)$courseid;
        $response = $curl->get($url);
        
        $status = $curl->get_info()['http_code'];
        if ($status === 200) {
            $data = json_decode($response, true);
            if (is_array($data) && count($data) > 0) {
                return $data[0]; // Retorna el primer y único mapeo
            }
        }
        
        return null;
    }

    /**
     * Llama al microservicio central para registrar un nuevo alumno-curso y aprovisionar en GitHub.
     *
     * @param int $userid ID de usuario en Moodle.
     * @param int $courseid ID del curso en Moodle.
     * @param string $github_url URL base de Github (ahora manejada por la API central, enviar vacío).
     * @param string $matrix_room ID de sala en Matrix generado por Synapse Admin API.
     * @param string $username Username del usuario en Moodle para generar el repositorio [asignatura]-[usuario].
     * @param string $course_shortname Nombre corto del curso para usar como base del repositorio template.
     * @param bool $is_teacher Indica si el usuario es un profesor.
     * @return array Resultado de la API devolviendo el mapeo generado.
     * @throws moodle_exception Si hay un error, como un 409 Conflict.
     */
    public function create_mapeo($userid, $courseid, $github_url, $matrix_room, $username = "", $course_shortname = "", $is_teacher = false) {
        $curl = new \curl(['ignoresecurity' => true]);
        $curl->setHeader('Authorization: Bearer ' . $this->token);
        $curl->setHeader('Content-Type: application/json');
        
        $payload = json_encode([
            'moodle_user_id' => (int)$userid,
            'moodle_course_id' => (int)$courseid,
            'github_repo_url' => $github_url,
            'matrix_room_id' => $matrix_room,
            'moodle_username' => $username,
            'moodle_course_shortname' => $course_shortname,
            'is_teacher' => $is_teacher
        ]);
        
        $url = $this->baseurl . '/mapeos';
        $response = $curl->post($url, $payload);
        
        $status = $curl->get_info()['http_code'];
        
        if ($status === 409) {
            throw new \moodle_exception('Conflict: Ya existe un mapeo para este usuario y curso (HTTP 409).', 'block_bdc');
        } else if ($status !== 201) {
            throw new \moodle_exception('Error creando mapeo (HTTP ' . $status . '): ' . $response, 'block_bdc');
        }
        
        return json_decode($response, true);
    }

    /**
     * Sincroniza la lista de alumnos matriculados con mapeo-api.
     *
     * @param int $courseid ID del curso en Moodle
     * @param array $students Array de objetos de usuario de Moodle
     * @param string $course_shortname Nombre corto del curso
     */
    public function sync_course_roster($courseid, $students, $course_shortname) {
        $curl = new \curl(['ignoresecurity' => true]);
        $curl->setHeader('Authorization: Bearer ' . $this->token);
        $curl->setHeader('Content-Type: application/json');

        $roster = [];
        foreach ($students as $student) {
            $roster[] = [
                'moodle_user_id' => (int)$student->id,
                'moodle_username' => $student->username,
                'is_teacher' => false
            ];
        }

        $payload = json_encode([
            'moodle_course_id' => (int)$courseid,
            'moodle_course_shortname' => $course_shortname,
            'students' => $roster
        ]);

        $url = $this->baseurl . '/mapeos/sync-roster';
        $response = $curl->post($url, $payload);
        $status = $curl->get_info()['http_code'];

        if ($status !== 200 && $status !== 201) {
            error_log("BLOCK_BDC SYNC ERROR: No se pudo sincronizar roster. Status: $status. Resp: $response");
        }
    }
}
