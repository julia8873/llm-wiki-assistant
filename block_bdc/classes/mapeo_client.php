<?php

class MapeoClient {
    private $apiUrl;
    private $token;

    public function __construct($apiUrl, $token) {
        $this->apiUrl = rtrim($apiUrl, '/');
        $this->token = $token;
    }

    private function request($method, $endpoint, $data = null) {
        $ch = curl_init($this->apiUrl . $endpoint);
        
        $headers = [
            'Authorization: Bearer ' . $this->token,
            'Content-Type: application/json',
            'Accept: application/json'
        ];

        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

        if ($data !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        return ['status' => $httpCode, 'data' => json_decode($response, true)];
    }

    public function createMapeo($userId, $courseId, $githubForkUrl, $matrixRoomId) {
        $data = [
            'moodle_user_id' => $userId,
            'moodle_course_id' => $courseId,
            'github_fork_url' => $githubForkUrl,
            'matrix_room_id' => $matrixRoomId
        ];
        return $this->request('POST', '/mapeos', $data);
    }

    public function getMapeo($userId, $courseId) {
        $endpoint = sprintf('/mapeos?moodle_user_id=%d&moodle_course_id=%d', $userId, $courseId);
        return $this->request('GET', $endpoint);
    }
}
