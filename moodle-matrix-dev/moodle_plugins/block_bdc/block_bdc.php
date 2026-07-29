<?php
/**
 * Block for LLM Wiki Assistant (BdC).
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

class block_bdc extends block_base {
    
    /**
     * Initialize the block properties.
     */
    public function init() {
        $this->title = get_string('pluginname', 'block_bdc');
    }

    /**
     * Define the formats where this block can be added.
     *
     * @return array
     */
    public function applicable_formats() {
        return [
            'all' => true,
        ];
    }

    /**
     * Allow multiple instances of this block.
     *
     * @return bool
     */
    public function instance_allow_multiple() {
        return true;
    }

    /**
     * Get the block content.
     *
     * @return stdClass|string
     */
    public function get_content() {
        if ($this->content !== null) {
            return $this->content;
        }

        $this->content = new stdClass;
        $this->content->text   = '';
        $this->content->footer = '';

        if (empty($this->instance) || !isloggedin() || isguestuser()) {
            return $this->content;
        }

        $courseid = $this->page->course->id;

        $url = new moodle_url('/blocks/bdc/view.php', ['courseid' => $courseid]);
        $btn_text = get_string('btn_access', 'block_bdc');

        $this->content->text = \html_writer::tag('div',
            \html_writer::link($url, $btn_text, ['class' => 'btn btn-primary w-100']),
            ['class' => 'text-center p-3']
        );

        return $this->content;
    }
}
