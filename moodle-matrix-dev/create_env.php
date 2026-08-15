<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once($CFG->dirroot.'/user/lib.php');
require_once($CFG->dirroot.'/course/lib.php');

// Create or update users
$users = [
    ['username' => 'profesor1', 'firstname' => 'Profesor', 'lastname' => 'Uno', 'email' => 'profe@test.com', 'pass' => 'profesor1'],
    ['username' => 'alumno1', 'firstname' => 'Alumno', 'lastname' => 'Uno', 'email' => 'alumno@test.com', 'pass' => 'alumno1']
];

$user_ids = [];
foreach ($users as $u) {
    if ($existing = $DB->get_record('user', ['username' => $u['username']])) {
        $user_ids[$u['username']] = $existing->id;
        // Update password
        $existing->password = hash_internal_user_password($u['pass']);
        $DB->update_record('user', $existing);
        continue;
    }
    $user = new stdClass();
    $user->username = $u['username'];
    $user->password = hash_internal_user_password($u['pass']);
    $user->firstname = $u['firstname'];
    $user->lastname = $u['lastname'];
    $user->email = $u['email'];
    $user->auth = 'manual';
    $user->confirmed = 1;
    $user->mnethostid = $CFG->mnet_localhost_id;
    $user_ids[$u['username']] = user_create_user($user);
}

// Create course
if (!($course = $DB->get_record('course', ['shortname' => 'EDII-Oficial']))) {
    $c = new stdClass();
    $c->fullname = 'EDII Oficial';
    $c->shortname = 'EDII-Oficial';
    $c->category = 1;
    $c->visible = 1;
    $course = create_course($c);
}

// Enroll users
$teacher_role = $DB->get_record('role', ['shortname' => 'editingteacher'])->id;
$student_role = $DB->get_record('role', ['shortname' => 'student'])->id;

$enrol = enrol_get_plugin('manual');
$instances = enrol_get_instances($course->id, true);
$manual_instance = null;
foreach ($instances as $instance) {
    if ($instance->enrol === 'manual') {
        $manual_instance = $instance;
        break;
    }
}
if (!$manual_instance) {
    $manual_instance = $enrol->add_default_instance($course);
}

$enrol->enrol_user($manual_instance, $user_ids['profesor1'], $teacher_role);
$enrol->enrol_user($manual_instance, $user_ids['alumno1'], $student_role);

echo "E2E Env created successfully.\nprofesor1 ID: {$user_ids['profesor1']}\nalumno1 ID: {$user_ids['alumno1']}\ncourse ID: {$course->id}\n";
