import logging
import json
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class RestAuthProvider:
    def __init__(self, config, account_handler):
        self.api = account_handler
        self.endpoint = config.get("endpoint")
        self.host_header = config.get("host_header", "localhost:8000")

    @staticmethod
    def parse_config(config):
        return config

    async def check_password(self, user_id, password):
        if not self.endpoint:
            return False
            
        logger.info("Moodle auth check started for user_id=%s", user_id)
        
        if user_id.startswith('@'):
            localpart = user_id.split(":", 1)[0][1:]
        else:
            localpart = user_id
            user_id = f"@{localpart}:localhost"
        
        payload = json.dumps({
            "user": {
                "id": localpart,
                "password": password
            }
        }).encode('utf-8')

        headers = {'Content-Type': 'application/json'}
        if self.host_header:
            headers['Host'] = self.host_header

        req = urllib.request.Request(self.endpoint, data=payload, headers=headers)
        
        try:
            # Petición síncrona simple, ideal para entornos con bajo volumen de accesos
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    res_body = json.loads(response.read().decode('utf-8'))
                    if res_body.get('auth') is True:
                        logger.info("Moodle auth successful for %s", localpart)
                        
                        # Auto-registro en Synapse si no existe
                        try:
                            # Account handler legacy support check
                            if not (await self.api.check_user_exists(user_id)):
                                logger.info("User %s does not exist yet, auto-creating", user_id)
                                await self.api.register_user(localpart=localpart)
                        except Exception as reg_err:
                            logger.error("Failed to auto-register user %s: %s", user_id, str(reg_err))
                            
                        return True
        except urllib.error.HTTPError as e:
            logger.info("Moodle auth failed for %s with HTTP %s", localpart, e.code)
        except Exception as e:
            logger.warning("Error communicating with Moodle auth endpoint: %s", str(e))
            
        return False
