<?php
/**
 * Event observers for block_bdc.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

$observers = array(
    array(
        'eventname'   => '\\core\\event\\course_created',
        'callback'    => 'block_bdc\\observer::course_created',
    ),
);
