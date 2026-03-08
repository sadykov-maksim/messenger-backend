#!/bin/sh
set -e

exec daphne -e ssl:8443:privateKey=/etc/certificates/live/avocado-messenger.host/privkey.pem:certKey=/etc/certificates/live/avocado-messenger.host/fullchain.pem backend.asgi:application