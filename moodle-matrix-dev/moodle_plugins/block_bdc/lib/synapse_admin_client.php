<?php
/**
 * @file
 * Synapse Admin API Client.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */


defined('MOODLE_INTERNAL') || die();

require_once($CFG->libdir . '/filelib.php');

/**
 * Cliente HTTP para comunicarse con la API de Synapse.
 */
class block_bdc_synapse_admin_client {
    
    /**
     * URL interna de Synapse
     */
    private $baseurl;
    
    /**
     * Token de administrador de Matrix
     */
    private $token;

    /**
     * Constructor del cliente.
     */
    public function __construct() {
        $this->baseurl = getenv('SYNAPSE_URL_INTERNA') ?: 'http://synapse:8008';
        $this->token = getenv('MATRIX_ACCESS_TOKEN');
        if (empty($this->token)) {
            throw new moodle_exception('error_missing_token', 'block_bdc', '', 'MATRIX_ACCESS_TOKEN no está configurado en el entorno.');
        }
    }

    /**
     * Crea una sala en Matrix y devuelve el room_id.
     *
     * @param string $room_alias Alias deseado (opcional).
     * @param string $invite_user_id ID de Matrix del usuario a invitar.
     * @param string $room_name Nombre de la sala a crear (por defecto 'Sala de Asistente IA').
     * @param string $topic Tema o descripción de la sala (por defecto 'Chat 1:1 con tu asistente LLM').
     * @return string ID de la sala de Matrix creada (ej. !xyz:localhost).
     * @throws moodle_exception
     */
    public function create_room($room_alias, $invite_user_id, $room_name = 'Sala de Asistente IA', $topic = 'Chat 1:1 con tu asistente LLM') {
        $curl = new \curl(['ignoresecurity' => true]);
        $curl->setHeader('Authorization: Bearer ' . $this->token);
        $curl->setHeader('Content-Type: application/json');
        
        $payload = [
            'visibility' => 'private',
            'room_alias_name' => $room_alias,
            'name' => $room_name,
            'topic' => $topic,
            'invite' => [$invite_user_id]
        ];
        
        // Usamos el CS API estándar para crear la sala, ya que permite invitar.
        // Un token de admin/bot puede llamar a este endpoint.
        $url = $this->baseurl . '/_matrix/client/v3/createRoom';
        $response = $curl->post($url, json_encode($payload));
        
        $status = $curl->get_info()['http_code'];
        $data = json_decode($response, true);
        
        if ($status !== 200 || empty($data['room_id'])) {
            throw new moodle_exception('error_create_room', 'block_bdc', '', $response);
        }
        
        return $data['room_id'];
    }

    /**
     * Asegura que el usuario exista en Matrix. Si no existe, lo crea.
     * Utiliza la API de administración de Synapse.
     *
     * @param string $username Nombre de usuario de Moodle (ej. 'student1')
     * @return bool True si el usuario existe o fue creado, False en caso de error crítico.
     */
    public function ensure_user_exists($username) {
        $curl = new \curl(['ignoresecurity' => true]);
        $curl->setHeader('Authorization: Bearer ' . $this->token);
        $curl->setHeader('Content-Type: application/json');

        $user_id = '@' . $username . ':localhost';
        $url = $this->baseurl . '/_synapse/admin/v2/users/' . urlencode($user_id);

        // Generamos un password aleatorio muy largo. Nunca será usado por el alumno
        // porque el módulo REST Password Provider delega la validación de contraseñas a Moodle.
        $payload = [
            'password' => bin2hex(random_bytes(20)),
            'displayname' => $username,
            'admin' => false,
            'deactivated' => false
        ];

        $response = $curl->put($url, json_encode($payload));
        $status = $curl->get_info()['http_code'];

        if ($status === 200 || $status === 201) {
            return true;
        }

        return false;
    }
}
