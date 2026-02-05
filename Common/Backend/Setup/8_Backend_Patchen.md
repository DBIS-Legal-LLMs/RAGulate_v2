# Wie patcht/updatet man das Backend nachdem man eine neue Version hochgeladen hat ?

1. Server stoppen

```bash
sudo systemctl stop ragulate.service
```

2. Wechsel in Backend Ordner

```bash
cd Projekt/Ordner/Backend
```

3. Neue Version pullen

```bash
git pull
```

4. Server starten

```bash
sudo systemctl start ragulate.service
```

5. Live Logs

```bash
docker logs -f ragulate_backend_v2
```
