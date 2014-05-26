#!/bin/bash

set -e
export DJANGO_SETTINGS_MODULE={{ settings_module }}

VIRTUALENV={{ path_to_virtualenv }}
NUM_WORKERS=2

# user/group to run as
USER={{ user }}
GROUP={{ group }}

cd {{ site_dir }}
source ${VIRTUALENV}/bin/activate

test -d $LOGDIR || mkdir -p $LOGDIR

exec ${VIRTUALENV}/bin/gunicorn {{ wsgi_module }}:application \
    -w $NUM_WORKERS \
    --user=$USER \
    --group=$GROUP \
    --pythonpath {{ python_path }} \
    --bind localhost:{{ gunicorn_port }} \
    --log-level=debug
