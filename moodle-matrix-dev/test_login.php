<?php
$data = json_encode(['type'=>'m.login.password', 'identifier'=>['type'=>'m.id.user', 'user'=>'admin'], 'password'=>'adminpass']);
$ch = curl_init('http://synapse:8008/_matrix/client/v3/login');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
echo curl_exec($ch);
