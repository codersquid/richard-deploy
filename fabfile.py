"""deployment scripts for researchcompendia
with credit to scipy-2014 and researchcompendia fabric.py

fab <deploy|provision>[:<git ref>]

deploy: deploys a version of the site. if no git ref is provided, deploys HEAD.
provision: provisions a box to run the site. is not idempotent. do not rerun.
git ref: a git branch, hash, tag

example usages:

deploy new version of the site with an updated virtualenv.
$ fab deploy:1.1.1

"""
import string, random
from os.path import join, dirname, abspath
from fabric.api import run, task, env, cd, sudo
from fabric.contrib.files import sed, append
from fabtools import require, supervisor, postgres, files
from fabtools.files import upload_template
import fabtools

from fabtools.vagrant import vagrant

env.disable_known_hosts = True
# env.hosts = ['162.242.247.20:2222']
env.hosts = ['localhost']

FAB_HOME = dirname(abspath(__file__))
TEMPLATE_DIR = join(FAB_HOME, 'templates')

SITE_NAME = "ps1"
SITE_CLONE_NAME = SITE_NAME

SITE_DIR = join('/', 'srv', SITE_NAME) 
SITE_SETTINGS = {
    'repo_dir': join(SITE_DIR, SITE_CLONE_NAME),
    'setup_args': '.[postgresql]',
    'repo': 'https://github.com/willkg/richard.git',
    'user': SITE_NAME,  
    'group': SITE_NAME,
    'virtualenv': 'venv',
    'supervised_process': SITE_NAME,
    'settings_module': '{0}.richard.settings'.format(SITE_NAME) , 
    'wsgi_module': '{0}.richard.wsgi'.format(SITE_NAME), 
    'server_name': 'videos.pumpintstationone.org',
    'nginx_site': SITE_NAME,
}


@task
def uname():
    """call uname to check that we can do a simple command
    """
    run('uname -a')


@task
def deploy(version_tag=None):
    """deploys a new version of the site with a new virtualenv

    version_tag: a git tag, defaults to HEAD
    """
    supervised_process = SITE_SETTINGS['supervised_process']

    #dust()
    stop(supervised_process)
    update(commit=version_tag)
    setup()
    #collectstatic()
    start(supervised_process)
    #undust()


@task
def stop(process_name):
    """stops supervisor process
    """
    supervisor.stop_process(process_name)


@task
def start(process_name):
    """starts supervisor process
    """
    supervisor.start_process(process_name)


def clone_site():
    with cd(SITE_DIR):
        su('git clone %s %s' % (SITE_SETTINGS['repo'], SITE_CLONE_NAME))
    with cd(join(SITE_DIR, SITE_CLONE_NAME)):
        su('touch __init__.py') # janky way to treat the SITE_CLONE_NAME like a module name


@task
def update(commit='origin/master'):
    repo_dir = SITE_SETTINGS['repo_dir']
    with cd(repo_dir):
        su('git fetch')
        su('git checkout %s' % commit)


@task
def migrate(app):
    """ run south migration on specified app
    """
    with cd(SITE_SETTINGS['repo_dir']):
        vsu('./manage.py migrate %s' % app)



@task
def provision():
    """Run only once to provision a new host.
    This is not idempotent. Only run once!
    """
    install_packages()
    install_python_packages()
    lockdown_nginx()
    lockdown_ssh()
    setup_database()
    setup_site_user()
    setup_site_root()
    provision_django()
    provision_django_settings()
    setup_nginx_site()
    setup_supervisor()
    print("MANUAL STEPS: finish local settings, syncdb and migrate, collectstatic")


def setup_nginx_site():
    nginx_site = SITE_SETTINGS['nginx_site']
    static_dir = SITE_SETTINGS['repo_dir']
    upload_template('nginx_site.conf',
        '/etc/nginx/sites-available/%s' % nginx_site,
        context={
            'server_name': SITE_SETTINGS['server_name'],
            'path_to_static': join(static_dir, 'static'),
            'static_parent': '%s/' % static_dir,
        },
        use_jinja=True, use_sudo=True, template_dir=TEMPLATE_DIR)
    require.nginx.enabled(nginx_site)


def setup_supervisor():
    supervised_process = SITE_SETTINGS['supervised_process']
    bindir = join(SITE_DIR, 'bin')
    logdir = join(SITE_DIR, 'logs')
    upload_template('supervised_site.conf',
        '/etc/supervisor/conf.d/%s.conf' % supervised_process,
        context={
            'supervised_process': supervised_process,
            'command': join(bindir, 'gunicorn.sh'),
            'user': SITE_SETTINGS['user'],
            'group': SITE_SETTINGS['group'],
            'logfile': join(logdir, 'gunicorn.log'),
            'site_dir': bindir,
        },
        use_jinja=True, use_sudo=True, template_dir=TEMPLATE_DIR)
    supervisor.update_config()


def lockdown_nginx():
    # don't share nginx version in header and error pages
    sed('/etc/nginx/nginx.conf', '# server_tokens off;', 'server_tokens off;', use_sudo=True)
    sudo('service nginx restart')


def lockdown_ssh():
    sed('/etc/ssh/sshd_config', '^#PasswordAuthentication yes', 'PasswordAuthentication no', use_sudo=True)
    append('/etc/ssh/sshd_config', ['UseDNS no', 'PermitRootLogin no', 'DebianBanner no', 'TcpKeepAlive yes'], use_sudo=True)
    sudo('service ssh restart')


def provision_django():

    with cd(SITE_DIR):
        su('virtualenv {0}'.format(SITE_SETTINGS['virtualenv']))
    clone_site()
    setup()
    #collectstatic()
    #syncdb()


def provision_django_settings():

    upload_template('settings_local.py',
        join(SITE_DIR, SITE_SETTINGS['repo_dir'], 
            'richard', 'settings_local.py'),
        context={
            'db_name': SITE_NAME,
            'secret_key': ''.join(random.choice(string.ascii_letters + string.digits + '~@#%^&*-_') for x in range(64))
        },
        use_jinja=True, use_sudo=True, template_dir=TEMPLATE_DIR)


    # what is this?
    # sed('settings_local.py', 'http://127.0.0.1:8000', SITE_SETTINGS['django_site_url'])

def syncdb():
    with cd(SITE_SETTINGS['repo_dir']):
        vsu('./manage.py syncdb --noinput --migrate')


@task
def setup(virtualenv='venv'):
    with cd(SITE_SETTINGS['repo_dir']):
        # TODO: figure out how to escape .[postgresql], I keep getting: invalid command name
        #vsu("python setup.py '%s'" % SITE_SETTINGS['setup_args'], virtualenv=virtualenv)
        vsu("python setup.py install", virtualenv=virtualenv)
        vsu("pip install gunicorn", virtualenv=virtualenv)
        vsu("pip install psycopg2", virtualenv=virtualenv)


def setup_database():
    user = SITE_SETTINGS['user']
    require.postgres.server()
    # TODO: fabtools.require.postgres.user did not allow a user with no pw prompt? see if there is a better way
    if not postgres.user_exists(user):
        su('createuser -S -D -R -w %s' % user, 'postgres')
    if not postgres.database_exists(user):
        require.postgres.database(user, user, encoding='UTF8', locale='en_US.UTF-8')
    # TODO: change default port
    # port = 5432
    # /etc/postgresql/9.1/main/postgresql.conf


def setup_site_user():
    user = SITE_SETTINGS['user']
    if not fabtools.user.exists(user):
        sudo('useradd -s/bin/bash -d/home/%s -m %s' % (user, user))


def setup_site_root():
    bindir = join(SITE_DIR, 'bin')
    user = SITE_SETTINGS['user']
    sudo('mkdir -p %s' % SITE_DIR)
    sudo('chown %s:%s %s' % (user, user, SITE_DIR))

    with cd(SITE_DIR):
        su('mkdir -p logs bin {0}'.format(SITE_SETTINGS['virtualenv']))

    with cd(bindir):
        setup_gunicorn_script()
        sudo('chown -R %s:%s %s' % (user, user, SITE_DIR))
        su('chmod +x gunicorn.sh')


def setup_gunicorn_script():
    bindir = join(SITE_DIR, 'bin')
    python_path = SITE_SETTINGS['repo_dir']

    upload_template('gunicorn.sh',
        join(bindir, 'gunicorn.sh'),
        context={
            'settings_module': SITE_SETTINGS['settings_module'],
            'path_to_virtualenv': join(SITE_DIR, SITE_SETTINGS['virtualenv']),
            'user': SITE_SETTINGS['user'],
            'group': SITE_SETTINGS['group'],
            'site_dir': SITE_DIR,
            'wsgi_module': SITE_SETTINGS['wsgi_module'],
            'python_path': python_path,
        },
        use_jinja=True, use_sudo=True, template_dir=TEMPLATE_DIR)


def install_packages():
    require.deb.uptodate_index(max_age={'hour': 1})
    require.deb.packages([
        'python-software-properties',
        'python-dev',
        'build-essential',
        'git',
        'nginx-extras',
        'libxslt1-dev',
        'supervisor',
        'postgresql',
        'postgresql-server-dev-9.1',
        # useful but not strictly required
        'tig',
        'vim',
        'curl',
        'tmux',
        'htop',
        'ack-grep',
    ])


def install_python_packages():
    sudo('wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py')
    sudo('python get-pip.py')
    # install global python packages
    require.python.packages([
        'virtualenvwrapper',
        'setproctitle',
        'wheel',
    ], use_sudo=True)


def su(cmd, user=None):
    if user is None:
        user = SITE_SETTINGS['user']
    sudo("su %s -c '%s'" % (user, cmd))


def vsu(cmd, virtualenv='venv', user=None):
    if user is None:
        user = SITE_SETTINGS['user']
    activate = join(SITE_DIR, virtualenv, 'bin', 'activate')
    sudo("su {0} -c 'source {1}; {2}'".format(user, activate, cmd))


def collectstatic():
    with cd(SITE_SETTINGS['repo_dir']):
        vsu('./manage.py collectstatic --noinput')


def randomstring(n):
    return ''.join(random.choice(string.ascii_letters + string.digits + '~@#%^&*-_') for x in range(n))

