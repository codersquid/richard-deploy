This repo contains yet another refactoring of some fabric scripts for Carl
to play with for a pyvideo site.

* provision still requires manual steps
  * need to make a settings\_local.py with SECRET\_KEY and database info
  * need to run syncdb --migrate
  * need to run collectstatic

* haven't tested the deploy/update steps yet


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
