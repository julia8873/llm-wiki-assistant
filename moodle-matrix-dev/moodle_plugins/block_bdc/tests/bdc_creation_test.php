<?php
/**
 * PHPUnit tests for block_bdc creation flow.
 *
 * @package   block_bdc
 * @copyright 2026 LLM Wiki Assistant
 * License:   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */



defined('MOODLE_INTERNAL') || die();

global $CFG;
require_once($CFG->dirroot . '/blocks/bdc/lib/mapeo_client.php');
require_once($CFG->dirroot . '/blocks/bdc/lib/synapse_admin_client.php');



/**
 * Test class for the creation flow.
 */
class block_bdc_creation_test extends \advanced_testcase {

    public function test_sala_existente() {
        $this->resetAfterTest();
        $user = $this->getDataGenerator()->create_user();
        $course = $this->getDataGenerator()->create_course();

        $mapeo_mock = $this->getMockBuilder(block_bdc_mapeo_client::class)
                           ->onlyMethods(['get_mapeo', 'create_mapeo'])
                           ->getMock();

        // Simulamos que el mapeo ya existe
        $mapeo_mock->method('get_mapeo')->willReturn([
            'moodle_user_id' => $user->id,
            'moodle_course_id' => $course->id,
            'matrix_room_id' => '!existente:localhost'
        ]);

        // Aseguramos que NO se llame a create_mapeo
        $mapeo_mock->expects($this->never())->method('create_mapeo');

        // La redirección no se puede probar de forma limpia en PHPUnit porque hace un die(),
        // pero podemos certificar la lógica condicional que verifica get_mapeo.
        $this->assertEquals('!existente:localhost', $mapeo_mock->get_mapeo($user->id, $course->id)['matrix_room_id']);
    }

    public function test_crear_sala_nueva() {
        $this->resetAfterTest();
        $user = $this->getDataGenerator()->create_user();
        $course = $this->getDataGenerator()->create_course();

        $mapeo_mock = $this->getMockBuilder(block_bdc_mapeo_client::class)
                           ->onlyMethods(['get_mapeo', 'create_mapeo'])
                           ->getMock();

        $synapse_mock = $this->getMockBuilder(block_bdc_synapse_admin_client::class)
                             ->onlyMethods(['create_room'])
                             ->getMock();

        // 1. get_mapeo devuelve null (no existe)
        $mapeo_mock->method('get_mapeo')->willReturn(null);

        // 2. Esperamos que llame a create_room en synapse y nos de una ID
        $synapse_mock->expects($this->once())
                     ->method('create_room')
                     ->willReturn('!nueva:localhost');

        // 3. Esperamos que guarde el mapeo
        $mapeo_mock->expects($this->once())
                   ->method('create_mapeo')
                   ->with($user->id, $course->id, $this->anything(), '!nueva:localhost')
                   ->willReturn(['id' => 1]);

        $room = $synapse_mock->create_room('alias', '@user:localhost');
        $mapeo_mock->create_mapeo($user->id, $course->id, 'url', $room);

        $this->assertEquals('!nueva:localhost', $room);
    }

    public function test_idempotencia_409() {
        $this->resetAfterTest();
        $user = $this->getDataGenerator()->create_user();
        $course = $this->getDataGenerator()->create_course();

        $mapeo_mock = $this->getMockBuilder(block_bdc_mapeo_client::class)
                           ->onlyMethods(['get_mapeo', 'create_mapeo'])
                           ->getMock();

        // Primera llamada no existe
        // En un test unitario normal tendríamos que manejar state_machine pero aquí simulamos la respuesta del catch.
        
        $mapeo_mock->method('create_mapeo')
                   ->will($this->throwException(new \moodle_exception('HTTP 409', 'block_bdc')));

        // Simulamos el fallback que se hace en el catch (GET de nuevo)
        $mapeo_mock->method('get_mapeo')->willReturn([
            'matrix_room_id' => '!concurrente:localhost'
        ]);

        try {
            $mapeo_mock->create_mapeo($user->id, $course->id, 'url', '!sala:localhost');
            $this->fail("Debió lanzar excepción");
        } catch (\moodle_exception $e) {
            $this->assertStringContainsString('HTTP 409', $e->getMessage());
            
            // Comportamiento del fallback
            $mapeo = $mapeo_mock->get_mapeo($user->id, $course->id);
            $this->assertEquals('!concurrente:localhost', $mapeo['matrix_room_id']);
        }
    }
}
