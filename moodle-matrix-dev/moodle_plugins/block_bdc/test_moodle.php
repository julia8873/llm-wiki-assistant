<?php
require_once('/var/www/html/config.php');
$ctx = context_course::instance(7);
$roles = get_user_roles($ctx, 4);
foreach($roles as $role) { echo $role->shortname . ' '; }
var_dump(
    has_capability('moodle/course:update', $ctx, 4),
    has_capability('moodle/course:viewhiddenactivities', $ctx, 4),
    has_capability('moodle/grade:edit', $ctx, 4)
);
