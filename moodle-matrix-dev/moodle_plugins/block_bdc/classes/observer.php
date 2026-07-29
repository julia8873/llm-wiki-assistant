<?php
/**
 * Event observers for block_bdc.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

/// @cond DOXYGEN_IGNORE
namespace block_bdc;
/// @endcond

defined('MOODLE_INTERNAL') || die();

class observer {

    /**
     * Triggered when a course is created.
     * Calls the mapeo-api to provision the official repository.
     *
     * @param \core\event\course_created $event
     */
    public static function course_created(\core\event\course_created $event) {
        global $DB;
        
        $course = $event->get_record_snapshot('course', $event->objectid);
        if (!$course) {
            $course = $DB->get_record('course', array('id' => $event->objectid));
        }
        
        if ($course && !empty($course->shortname)) {
            $baseurl = getenv('MAPEO_API_URL_INTERNA') ?: 'http://mapeo-api:8000';
            $token = getenv('MAPEO_API_TOKEN') ?: 'changeme';
            
            $curl = new \curl(['ignoresecurity' => true]);
            $curl->setHeader('Authorization: Bearer ' . $token);
            $curl->setHeader('Content-Type: application/json');
            
            $payload = json_encode([
                'moodle_course_shortname' => $course->shortname
            ]);
            
            $url = $baseurl . '/cursos';
            
            // Llama a la API de forma síncrona. Si falla, Moodle podría mostrar error al crear el curso,
            // lo cual es útil para que el administrador sepa si la API está caída o el PAT falló.
            $response = $curl->post($url, $payload);
            $status = $curl->get_info()['http_code'];
            
            if ($status === 201 || $status === 200) {
                \core\notification::success('Repositorio oficial de la asignatura (' . $course->shortname . '-Oficial) creado correctamente en GitHub.');
            } else {
                \core\notification::error('Error al crear el repositorio oficial en GitHub. Por favor contacte con soporte técnico. (HTTP ' . $status . ')');
                // Registrar en el log de Moodle si falla
                debugging('Error al aprovisionar la plantilla oficial en mapeo-api. HTTP ' . $status . ': ' . $response, DEBUG_DEVELOPER);
            }
        }
    }
}
