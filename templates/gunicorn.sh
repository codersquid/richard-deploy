#!/bin/bash

set -e
export PYTHONPATH={{ python_paths }}:$PYTHONPATH
export DJANGO_SETTINGS_MODULE={{ settings_module }}
#export PYTHONPATH={{ python_paths }}/srv/pyvideo/richard:/srv/pyvideo/config:$PYTHONPATH
#export DJANGO_SETTINGS_MODULE=pyvideo_settings

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
    --bind localhost:8000 \
    --log-level=debug
