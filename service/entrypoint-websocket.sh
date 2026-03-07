#!/bin/sh
set -e

exec daphne -e ssl:8443:privateKey=/etc/certificates/avocado-messenger.key:certKey=/etc/certificates/avocado-messenger.pem backend.asgi:application