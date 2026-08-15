<?php
/**
 * Entry point for block_bdc access link.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once('../../config.php');
require_once($CFG->dirroot . '/blocks/bdc/lib/mapeo_client.php');
require_once($CFG->dirroot . '/blocks/bdc/lib/synapse_admin_client.php');



$courseid = required_param('courseid', PARAM_INT);
$course = $DB->get_record('course', ['id' => $courseid], '*', MUST_EXIST);

require_login($course);
$context = context_course::instance($course->id);

$userid = $USER->id;

// Cliente de la API de mapeo
$mapeo_client = new block_bdc_mapeo_client();

$is_teacher = has_capability('moodle/course:update', $context) || has_capability('moodle/course:viewhiddenactivities', $context) || has_capability('moodle/grade:edit', $context);

if ($is_teacher) {
    // Sincronizar todos los alumnos matriculados
    $enrolled_users = get_enrolled_users($context, 'moodle/course:participate');
    $mapeo_client->sync_course_roster($courseid, $enrolled_users, $course->shortname);
}

// 1. Comprobación rápida sin bloqueo
$mapeo = $mapeo_client->get_mapeo($userid, $courseid);

if ($mapeo && !empty($mapeo['matrix_room_id'])) {
    // Ya existe la sala, redirigir a Element
    // Aseguramos que el usuario está dentro de la sala forzando el join
    $synapse_client = new block_bdc_synapse_admin_client();
    $matrix_user_id = '@' . $USER->username . ':localhost';
    $synapse_client->join_user_to_room($mapeo['matrix_room_id'], $matrix_user_id);
    
    $element_url = getenv('ELEMENT_URL_BASE') ?: 'http://localhost:8081';
    $redirect_url = $element_url . '/#/room/' . urlencode($mapeo['matrix_room_id']);
    redirect($redirect_url);
}

// 2. No existe, entramos en la zona crítica. 
// Usamos el API de lock de Moodle para evitar creaciones duplicadas por doble-clic.
$lockfactory = \core\lock\lock_config::get_lock_factory('block_bdc');
$lock = $lockfactory->get_lock('crear_sala_' . $userid . '_' . $courseid, 5);

if ($lock) {
    try {
        // Doble check dentro del lock
        $mapeo = $mapeo_client->get_mapeo($userid, $courseid);
        if ($mapeo && !empty($mapeo['matrix_room_id'])) {
            $lock->release();
            
            // Forzamos el join
            $synapse_client = new block_bdc_synapse_admin_client();
            $matrix_user_id = '@' . $USER->username . ':localhost';
            $synapse_client->join_user_to_room($mapeo['matrix_room_id'], $matrix_user_id);
            
            $element_url = getenv('ELEMENT_URL_BASE') ?: 'http://localhost:8081';
            redirect($element_url . '/#/room/' . urlencode($mapeo['matrix_room_id']));
        }
        
        // No existe. Crear la sala en Matrix.
        $synapse_client = new block_bdc_synapse_admin_client();
        
        // Determinamos el ID de matrix del alumno. 
        // Asumimos un mapeo simple: @user_{id}:localhost
        // Usamos el username de Moodle como ID en Matrix para asegurar la identidad.
        $matrix_user_id = '@' . $USER->username . ':localhost'; 
        $alias = 'bdc_u' . $userid . '_c' . $courseid . '_t' . time();
        
        // Fase 4.1: Asegurarnos de que el usuario exista en Matrix antes de invitarlo.
        $synapse_client->ensure_user_exists($USER->username);
        
        $room_name = $course->fullname . ($is_teacher ? ' (Profesor)' : '');
        $topic = 'Chat 1:1 conectado a tu repositorio de base de conocimiento para la asignatura ' . $course->fullname;
        $room_id = $synapse_client->create_room($alias, $matrix_user_id, $room_name, $topic);
        
        // Forzar al usuario a unirse a la sala para evitar 403
        $synapse_client->join_user_to_room($room_id, $matrix_user_id);
        
        // Ya no enviamos un placeholder, la API de mapeo lo provisiona
        $github_url = '';
        
        // Guardar mapeo en la BD central
        try {
            $mapeo_client->create_mapeo($userid, $courseid, $github_url, $room_id, $USER->username, $course->shortname, $is_teacher);
        } catch (\moodle_exception $e) {
            // Fallback (Capa 2 de idempotencia): Si el API devuelve 409 Conflict a pesar del lock
            // significa que la sala se creó, atrapamos el error, recuperamos la info real y avanzamos.
            if (strpos($e->getMessage(), 'HTTP 409') !== false) {
                $mapeo = $mapeo_client->get_mapeo($userid, $courseid);
                if ($mapeo) {
                    $room_id = $mapeo['matrix_room_id'];
                }
            } else {
                throw $e;
            }
        }
        
        $lock->release();
        
        // Redirigir
        $element_url = getenv('ELEMENT_URL_BASE') ?: 'http://localhost:8081';
        redirect($element_url . '/#/room/' . urlencode($room_id));
        
    } catch (\Exception $e) {
        $lock->release();
        error_log("BLOCK_BDC EXCEPTION: " . $e->getMessage() . " \nTRACE: " . $e->getTraceAsString());
        throw new \moodle_exception('error_mapping', 'block_bdc', '', $e->getMessage());
    }
} else {
    // Si no logramos obtener el candado, otro proceso está creándola. 
    // Mostramos mensaje de espera o reintento.
    throw new \moodle_exception('creating_room', 'block_bdc');
}
