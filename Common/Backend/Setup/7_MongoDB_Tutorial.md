# Anleitung zur Nutzung der MongoDB

## Mit der laufenden MongoDB verbinden

Da die MongoDB über den DockerContainer läuft zuerst:
```bash
docker exec -it ragulate_mongodb bash
```

_In der Docker Shell_ - Starten der MongoShell (Standardmäßig auf Port 27017):
```bash
mongosh
```

(Optional) Falls mongosh nicht installiert ist, das -> dann wiederholen:
```bash
sudo apt install mongosh
```

_In der Mongo-Shell_ - Datenbanken auflisten:
```bash
show dbs
```

liefert bspw.:
```bash
admin     40.00 KiB
local     72.00 KiB
gdpr_chatbot   5.23 MiB
test      12.00 KiB
```

Schaue in bestimme DB hinein:
```bash
use gdpr_chatbot
```

Collections in der DB anzeigen:
```bash
show collections
```

liefert bspw.:
```bash
users
logs
sessions
documents
```

Inhalte einer Collection anschauen (_bspw. die ersten 20 User_):
```bash
db.users.find().limit(20)
```


```bash

```