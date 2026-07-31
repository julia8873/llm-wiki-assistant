<?php
require_once('/var/www/html/config.php');
\ = context_course::instance(7);
\ = get_user_roles(\, 4);
foreach(\ as \) { echo \->shortname . ' '; }
var_dump(
    has_capability('moodle/course:update', \, 4),
    has_capability('moodle/course:viewhiddenactivities', \, 4),
    has_capability('moodle/grade:edit', \, 4)
);
