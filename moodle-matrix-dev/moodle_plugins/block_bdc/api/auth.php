<?php
/**
 * REST Password Provider endpoint for Matrix Synapse.
 * Verifies Moodle user credentials.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 */

define('AJAX_SCRIPT', true);
//
// Leer payload JSON de Synapse ANTES de config.php para evitar que se consuma php://input
$raw = file_get_contents('php://input');
$payload = json_decode($raw, true);

require_once(__DIR__ . '/../../../config.php');

header('Content-Type: application/json');

if (!isset($payload['user']['id']) || !isset($payload['user']['password'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing username or password', 'auth' => false, 'raw' => $raw]);
    exit;
}

$username = $payload['user']['id'];
$password = $payload['user']['password'];

// Validar credenciales usando los plugins de autenticación (sin iniciar sesión en Moodle)
$authenticated = false;
$auths = get_enabled_auth_plugins();
foreach ($auths as $auth) {
    $authplugin = get_auth_plugin($auth);
    if ($authplugin->user_login($username, $password)) {
        $authenticated = true;
        break;
    }
}

if ($authenticated) {
    http_response_code(200);
    echo json_encode(['auth' => true]);
} else {
    http_response_code(401);
    echo json_encode(['auth' => false]);
}
exit;
