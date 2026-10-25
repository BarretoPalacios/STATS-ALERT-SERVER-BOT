# Server Stats Bot

Bot de Telegram que reporta el estado de un servidor (CPU, RAM y disco) y de sus
contenedores Docker. Esta preparado para correr 24/7 con Docker Compose y
reiniciarse automaticamente si el servidor se reinicia.

## Comandos

| Comando | Descripcion |
| --- | --- |
| `/start` | Mensaje de bienvenida. |
| `/stats` | Estado del servidor y de los contenedores Docker. Solo responde al chat autorizado. |

Ejemplo de respuesta:

```text
ESTADO DEL SERVIDOR
- CPU: 7.4%
- RAM: 41.2% (3.28 GB / 7.96 GB)
- Disco: 23.8% (11.1 GB / 46.6 GB)

CONTENEDORES DOCKER
- server-stats-bot - running
- nginx - running
- postgres - exited
```

## Estructura del proyecto

```text
.
├── bot.py                # Codigo del bot
├── Dockerfile            # Imagen de Python 3.12
├── docker-compose.yml    # Despliegue con acceso al host y a Docker
├── requirements.txt      # Dependencias de Python
├── .env.example          # Plantilla de configuracion
├── .dockerignore
├── .gitignore
└── README.md
```

## Requisitos

- Un servidor Linux con Docker Engine y Docker Compose v2.
- Un usuario con permiso para ejecutar Docker (grupo `docker` o `sudo`).
- Una cuenta de Telegram.
- No hace falta abrir puertos en el firewall: el bot usa long polling saliente.

## Puesta en marcha

### 1. Crear el bot en Telegram

1. Abre Telegram y busca `@BotFather`.
2. Envia `/newbot` y sigue las instrucciones.
3. Guarda el token que te entrega (formato `123456789:AA...`).

> Si ya tenias un token real en tu `.env` y lo compartiste o subiste a algun
> sitio, revocalo con `/revoke` en BotFather y genera uno nuevo.

### 2. Obtener tu chat ID

1. Envia `/start` a tu bot desde tu cuenta (o anadelo a un grupo y envia
   `/start@TuBot` alli).
2. Abre en el navegador:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
3. Busca el campo `"chat":{"id":...}`. Usa ese numero como
   `TELEGRAM_CHAT_ID`.

Tambien puedes escribir a `@userinfobot` para obtener tu ID personal. En grupos
el ID suele ser negativo (por ejemplo `-1001234567890`).

### 3. Crear la carpeta en el servidor

Conectate por SSH y crea el directorio:

```bash
sudo mkdir -p /opt/server-stats-bot
sudo chown "$USER":"$USER" /opt/server-stats-bot
```

### 4. Copiar los archivos

Desde tu equipo local, dentro de la carpeta del proyecto:

```bash
scp bot.py requirements.txt Dockerfile docker-compose.yml .dockerignore .env.example \
  usuario@IP_DEL_SERVIDOR:/opt/server-stats-bot/
```

No copies tu `.env` local: crea uno nuevo en el servidor en el siguiente paso.

### 5. Configurar las variables de entorno

En el servidor:

```bash
cd /opt/server-stats-bot
cp .env.example .env
chmod 600 .env
nano .env
```

Rellena al menos:

```env
TELEGRAM_TOKEN=123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
```

Guarda el archivo (`Ctrl+O`, `Enter`, `Ctrl+X` en nano).

### 6. Arrancar el bot

```bash
docker compose up -d --build
```

Si tu usuario no esta en el grupo `docker`, usa `sudo docker compose ...` o
anade el usuario con:

```bash
sudo usermod -aG docker "$USER"
```

Cierra y vuelve a abrir la sesion SSH despues de ejecutar ese comando.

### 7. Verificar

```bash
docker compose ps
docker compose logs -f
```

Deberias ver `Bot corriendo...`. Envia `/stats` al bot para comprobar que
responde con las metricas.

## Operacion diaria

| Accion | Comando |
| --- | --- |
| Ver estado | `docker compose ps` |
| Ver logs en vivo | `docker compose logs -f` |
| Reiniciar | `docker compose restart` |
| Detener | `docker compose down` |
| Arrancar de nuevo | `docker compose up -d` |
| Actualizar tras cambiar archivos | `docker compose up -d --build` |

### Arranque automatico tras reiniciar el servidor

La politica `restart: unless-stopped` reinicia el contenedor automaticamente.
Asegurate de que Docker tambien arranca con el sistema:

```bash
sudo systemctl enable --now docker
```

### Actualizar la imagen base

```bash
cd /opt/server-stats-bot
docker compose build --pull
docker compose up -d
docker image prune -f
```

## Configuracion

| Variable | Obligatoria | Descripcion |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | Si | Token del bot de BotFather. |
| `TELEGRAM_CHAT_ID` | Si | ID del chat autorizado a usar `/stats`. |
| `DISK_PATH` | No | Ruta del disco a mostrar. Por defecto `/host` con Compose. |

Notas:

- `DISK_PATH=/host` funciona porque `docker-compose.yml` monta la raiz del host
  en `/host` en modo solo lectura.
- Si ejecutas el bot sin Docker, `DISK_PATH` vale `/` por defecto.
- El bot no expone puertos ni necesita un dominio.

## Como obtiene las metricas

`docker-compose.yml` habilita tres cosas necesarias para ver el servidor real y
no solo el contenedor:

- `pid: host`: psutil lee el `/proc` del host, por lo que CPU y RAM reflejan el
  servidor completo.
- `/:/host:ro`: el disco del host se monta en `/host` (solo lectura) y
  `DISK_PATH` apunta ahi.
- `/var/run/docker.sock:ro`: el SDK de Docker se conecta al daemon del host para
  listar los contenedores.

El contenedor no se ejecuta en modo `privileged`, pero montar el socket de
Docker equivale a tener control de root sobre el host. Ejecuta solo codigo de
confianza.

## Seguridad

- No subas nunca `.env` a Git. Ya esta incluido en `.gitignore`.
- Manten permisos restrictivos: `chmod 600 .env`.
- Rota el token con BotFather si crees que se ha filtrado.
- El bot solo atiende `/stats` desde el `TELEGRAM_CHAT_ID` configurado; el resto
  de chats recibe "No tienes autorizacion".
- Revisa los cambios antes de actualizar el bot en produccion.
- Manten Docker actualizado.

## Problemas comunes

### "No tienes autorizacion para usar este bot"

`TELEGRAM_CHAT_ID` no coincide con el chat desde el que escribes. Verifica el
valor con `getUpdates` y reinicia: `docker compose restart`.

### "Error al conectar con Docker"

Comprueba que el socket existe y que el volumen esta montado:

```bash
ls -l /var/run/docker.sock
docker compose config
```

Si usas Docker rootless, el socket suele estar en
`/run/user/1000/docker.sock`; ajusta el volumen en `docker-compose.yml`.

### Las metricas parecen las del contenedor

- Asegurate de ejecutar en Linux; Docker Desktop (Windows/macOS) no soporta
  `pid: host` igual que Linux.
- Verifica que `DISK_PATH=/host` y que el montaje `/:/host:ro` existe.

### "Faltan configurar TELEGRAM_TOKEN o TELEGRAM_CHAT_ID"

El archivo `.env` no existe, esta mal nombrado o las variables estan vacias.
Debe estar en la misma carpeta que `docker-compose.yml`.

### Error 409 Conflict en Telegram

Hay otra instancia del mismo bot haciendo polling (por ejemplo, tu copia local).
Detenla y deja solo la del servidor.

### Ver mas detalles

```bash
docker compose logs --tail=100
docker compose config
```

## Desarrollo local

```bash
python -m venv .venv
```

En Linux/macOS:

```bash
source .venv/bin/activate
```

En Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Instala dependencias y ejecuta:

```bash
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Para desarrollo en Windows, `docker.from_env()` puede encontrar Docker Desktop,
pero las metricas del host y el montaje `/host` solo funcionan como se espera en
Linux. Usa el servidor o una maquina virtual Linux para probar el despliegue
real.

## Personalizacion

- Cambia los textos de `/stats` en `bot.py`.
- Anade comandos con `CommandHandler` y registralos en `main()`.
- Despues de cualquier cambio, reconstruye:

```bash
docker compose up -d --build
```
