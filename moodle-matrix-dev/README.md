# Local Moodle & Matrix Dev/Testing Stack

This directory contains a pre-configured Docker Compose stack to quickly set up a local development and testing environment for Moodle's Matrix integration.

## Services Included

1.  **Moodle (`localhost:8000`)**: The learning management system (runs Bitnami Moodle).
2.  **MariaDB**: Database backend for Moodle.
3.  **Synapse (`localhost:8008`)**: The reference Matrix homeserver implementation written in Python.
4.  **Element Web (`localhost:8081`)**: The Matrix web chat client, configured to point to your local Synapse server.

---

## Quick Start

### 1. Launch the Services
Start the containers using Docker Compose (or Podman Compose):
```bash
docker compose up -d
```
*Note: The first startup of Moodle can take 1–2 minutes as it bootstraps the database and sets up the files.*

### 2. Create the Matrix Admin Account
Since Synapse is used, you must register the administrator account using the command-line tool inside the container:
1. Run the following command to register an administrator user:
   ```bash
   docker exec -it matrix-synapse register_new_matrix_user -c /data/homeserver.yaml --user admin --password adminpass123 --admin http://localhost:8008
   ```
2. Log into Element Web (`http://localhost:8081`) with the username `admin` and password `adminpass123`.

### 3. Retrieve the Matrix Access Token
Moodle requires this token to manage rooms and users via the Matrix API.
1. In Element Web, click on your profile icon in the top-left corner.
2. Select **All settings** (or **Settings**).
3. Go to the **Help & About** tab.
4. Scroll down to the **Advanced** section.
5. Locate the **Access Token** field and copy it.

### 4. Enable Communication Providers in Moodle
1. Open Moodle at: **`http://localhost:8000`**
2. Log in using the default admin credentials:
   - **Username:** `admin`
   - **Password:** `adminpass123`
3. Navigate to: **Site Administration > Development > Experimental > Experimental settings**
4. Check the box for **Enable communication providers** (`enablecommunication`).
5. Click **Save changes**.

### 5. Configure the Matrix Provider in Moodle
1. Navigate to: **Site Administration > Plugins > Communication > Matrix** (or **Site Administration > Plugins > Communication providers > Matrix**).
2. Enter the following settings:
   - **Matrix Homeserver URL:** `http://matrix-synapse:8008` *(This is the internal docker container network name, allowing the Moodle container to communicate with Synapse).*
   - **Access Token:** Paste the access token you copied from Element in Step 3.
   - **Element Web URL:** `http://localhost:8081` *(The host-accessible URL users will open to chat).*
3. Click **Save changes**.

### 6. Enable Matrix on a Course
1. Create a course or go to an existing course in Moodle.
2. Click on the **Settings** tab.
3. Scroll down and click to expand the **Communication** section.
4. Set the **Communication provider** to **Matrix**.
5. Set a room name.
6. Click **Save and display**.

Moodle will trigger background ad-hoc tasks (via cron) to create the Matrix room and sync course participants automatically!

---

## Development Utilities

### Inspect Logs
To see Moodle's output or database logs:
```bash
docker compose logs -f moodle
docker compose logs -f synapse
```

### Stop the Environment
To stop the services and retain all data:
```bash
docker compose down
```

To stop the services and **delete all data** (for a clean restart):
```bash
docker compose down -v
```
