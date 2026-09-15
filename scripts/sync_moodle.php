<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once($CFG->dirroot . '/blocks/bdc/lib/mapeo_client.php');
require_once($CFG->dirroot . '/blocks/bdc/lib/synapse_admin_client.php');

$courseid = 2;
$course = $DB->get_record('course', ['id' => $courseid]);

$users_to_sync = ['profesor1', 'alumno1'];

foreach ($users_to_sync as $username) {
    $USER = $DB->get_record('user', ['username' => $username]);
    if (!$USER) {
        echo "User $username not found.\n";
        continue;
    }
    $userid = $USER->id;
    
    $mapeo_client = new block_bdc_mapeo_client();
    $is_teacher = ($username === 'profesor1');
    $synapse_client = new block_bdc_synapse_admin_client();
    
    // Check if mapping already exists
    $mapeo = $mapeo_client->get_mapeo($userid, $courseid);
    if ($mapeo && !empty($mapeo['matrix_room_id'])) {
        echo "Mapping already exists for $username: Room {$mapeo['matrix_room_id']}\n";
        continue;
    }
    
    $matrix_user_id = '@' . $USER->username . ':localhost'; 
    $alias = 'bdc_u' . $userid . '_c' . $courseid . '_t' . time();
    
    $synapse_client->ensure_user_exists($USER->username);
    
    $room_name = $course->fullname . ($is_teacher ? ' (Profesor)' : '');
    $topic = 'Chat 1:1 conectado a tu repositorio de base de conocimiento para la asignatura ' . $course->fullname;
    
    try {
        $room_id = $synapse_client->create_room($alias, $matrix_user_id, $room_name, $topic);
        $synapse_client->join_user_to_room($room_id, $matrix_user_id);
        
        echo "Created Matrix room $room_id for $username.\n";
        
        $github_url = '';
        $mapeo_client->create_mapeo($userid, $courseid, $github_url, $room_id, $USER->username, $course->shortname, $is_teacher);
        
        echo "Sync for $username done: Room $room_id mapped successfully.\n";
    } catch (Exception $e) {
        echo "Error syncing $username: " . $e->getMessage() . "\n";
    }
}
