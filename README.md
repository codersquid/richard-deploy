
## WARNINGS

I am not maintaining this repo. For deploying pyvideo, I maintain
* https://github.com/pyvideo/pyvideo-deploy
* https://github.com/pyvideo/richard-ansible

## Directory structure

Provision will set up the project's directoy tree as follows:

```
/srv/writethedocs/
├── bin
│   ├── gunicorn.sh     runs the site
├── logs
│   └── gunicorn.log    gunicorn stdout and stderr log
├── venv                virtualenv
└── wtd                 clone of richard with the additional files below
    ├── __init__.py
    ├── richard
    │   ├── settings_local.py

```
