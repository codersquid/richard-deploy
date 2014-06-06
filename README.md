This repo contains yet another refactoring of some fabric scripts for Carl
to play with for a pyvideo site.

## WARNINGS

* This does not set up elasticsearch or the cron jobs for indexing and running the link checker.
* `deploy` is not tested
* @codersquid does not enjoy writing fabfiles and is learning about ansible and enjoying writing playbooks. go see how things
  progress here https://github.com/codersquid/pyvideo-playbook

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
