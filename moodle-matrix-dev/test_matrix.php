<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once('/bitnami/moodle/blocks/bdc/lib/synapse_admin_client.php');
try {
    $c = new block_bdc_synapse_admin_client();
    $c->ensure_user_exists('student1');
    $c->create_room('test_alias_4', '@student1:localhost', 'test', 'test');
    echo "OK";
} catch (Exception $e) {
    if (isset($e->a)) {
        var_dump($e->a);
    }
    var_dump($e->getMessage());
}
