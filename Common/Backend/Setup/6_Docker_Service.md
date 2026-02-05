# Eine kleine Anleitung, wie man über das Terminal mit dem Service umgeht und Live-Logs ausliest

## Dateistandort für Service
sudo nano /etc/systemd/system/ragulate.service

## Live-Logs und mehr...

Alle laufenden docker container anzeigen:
```bash
docker ps
```

(Optional) Falls 'permission denied':
```bash
newgrp docker
```

Shell inside backend
```bash
docker exec -it ragulate_backend_v2 bash
```

Shell inside MongoDB
```bash
docker exec -it ragulate_mongodb bash
```

Logs in Echtzeit sehen
```bash
docker logs -f ragulate_backend_v2
```

Compose-Namen statt Container-Namen nutzen
```bash
docker compose exec backend bash
docker compose exec mongodb bash
```

```bash

```