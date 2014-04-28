
This repo contains yet another refactoring of some fabric scripts for Carl
to play with for a pyvideo site.

* provision still requires manual steps
  * need to make a settings\_local.py with SECRET\_KEY and database info
  * need to run syncdb --migrate
  * need to run collectstatic

* haven't tested the deploy/update steps yet
