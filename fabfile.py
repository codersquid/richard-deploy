"""deployment scripts for researchcompendia
with credit to scipy-2014 and researchcompendia fabric.py

fab <deploy|provision>[:<git ref>]

deploy: deploys a version of the site. if no git ref is provided, deploys HEAD.

provision: provisions a box to run the site. is not idempotent. do not rerun.

git ref: a git branch, hash, tag


example usages:

deploy deploys a new version of the site with a new virtualenv.  it starts by
placing a maintenance page, stops the website, updates it to version 1.1.1,
restarts it, and brings back the main page.

$ fab deploy:1.1.1

the following combination of calls does the previous steps by hand except for
creating a new virtualenv.

$ fab dust
$ fab stop:researchcompendia
$ fab update:1.1.1
$ fab start:researchcompendia
$ fab undust

"""
import datetime, string, random, re
from os.path import join, dirname, abspath
from fabric.api import run, task, env, cd, sudo, put
from fabric.contrib.files import sed, append
from fabtools import require, supervisor, postgres, files
from fabtools.files import upload_template
from fabtools.user import home_directory
import fabtools

env.disable_known_hosts = True
env.hosts = ['162.242.247.20:2222']

FAB_HOME = dirname(abspath(__file__))
TEMPLATE_DIR = join(FAB_HOME, 'templates')

SITE_DIR = join('/', 'srv', 'richard')
SITE_SETTINGS = {
    'repo_dir': join(SITE_DIR, 'richard'),
    'manage_dir': join(SITE_DIR,'richard'),
    'settings_dir': join(SITE_DIR, 'richard', 'richard'),
    'config_dir': join(SITE_DIR, 'config'),
    'venvs_dir': join(SITE_DIR, 'venvs'),
    'setup_args': '\.\[postgresql\]',
    'repo': 'https://github.com/willkg/richard.git',
    'user': 'richard',
    'group': 'richard',
    'supervised_process': 'richard',
    'default_virtualenv': 'richard',
    'settings_module': 'richard.settings',
    'wsgi_module': 'richard.wsgi',
    'server_name': '.writethedocs.org',
    'nginx_site': 'writethedocs',
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
        su('git clone %s' % SITE_SETTINGS['repo'])


@task
def update(commit='origin/master'):
    repo_dir = SITE_SETTINGS['repo_dir']

    if not files.is_dir(repo_dir):
        clone_site()

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
    #setup_secrets()
    provision_django()
    setup_nginx_site()
    setup_supervisor()
    print("MANUAL STEPS: pip install psycopg2, finish local settings, syncdb and migrate, collectstatic")


def setup_nginx_site():
    nginx_site = SITE_SETTINGS['nginx_site']
    upload_template('nginx_site.conf',
        '/etc/nginx/sites-available/%s' % nginx_site,
        context={
            'server_name': SITE_SETTINGS['server_name'],
            'path_to_static': join(SITE_DIR, 'static'),
            'static_parent': '%s/' % SITE_DIR,
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
            'command': join(bindir, 'gunicorn.sh'),
            'user': SITE_SETTINGS['user'],
            'group': SITE_SETTINGS['group'],
            'logfile': join(logdir, 'gunicorn.log'),

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
    mkvirtualenv()
    clone_site()
    setup()
    #collectstatic()
    #syncdb()


def syncdb():
    with cd(SITE_SETTINGS['repo_dir']):
        vsu('./manage.py syncdb --noinput --migrate')


@task
def setup(virtualenv=None):
    if virtualenv is None:
        virtualenv = SITE_SETTINGS['default_virtualenv']
    with cd(SITE_SETTINGS['repo_dir']):
        # TODO: figure out how to escape .[postgresql], I keep getting: invalid command name
        #vsu("python setup.py '%s'" % SITE_SETTINGS['setup_args'], virtualenv=virtualenv)
        vsu("python setup.py install", virtualenv=virtualenv)


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


def setup_secrets():
    secret = randomstring(64)
    configdir = join(SITE_DIR, 'config')

    with cd(configdir):
        upload_template('secrets.py', 'secrets.py',
            context={
                'secret_key': secret,
            },
            template_dir=TEMPLATE_DIR,
            use_jinja=True, use_sudo=True, chown=True, user=SITE_SETTINGS['user'])


def setup_site_root():
    bindir = join(SITE_DIR, 'bin')
    user = SITE_SETTINGS['user']
    sudo('mkdir -p %s' % SITE_DIR)
    sudo('chown %s:%s %s' % (user, user, SITE_DIR))

    with cd(SITE_DIR):
        su('mkdir -p venvs logs bin config media static')

    with cd(bindir):
        setup_gunicorn_script()
        sudo('chown -R %s:%s %s' % (user, user, SITE_DIR))
        su('chmod +x gunicorn.sh')


def setup_gunicorn_script():
    bindir = join(SITE_DIR, 'bin')
    python_paths = '%s:%s' % (SITE_SETTINGS['repo_dir'], SITE_SETTINGS['config_dir'])

    upload_template('gunicorn.sh',
        join(bindir, 'gunicorn.sh'),
        context={
            'python_paths': python_paths,
            'settings_module': SITE_SETTINGS['settings_module'],
            'path_to_virtualenv': SITE_SETTINGS['default_virtualenv'],
            'user': SITE_SETTINGS['user'],
            'group': SITE_SETTINGS['group'],
            'site_dir': SITE_DIR,
            'wsgi_module': SITE_SETTINGS['wsgi_module'],
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


def vsu(cmd, virtualenv=None, user=None):
    if virtualenv is None:
        virtualenv = SITE_SETTINGS['default_virtualenv']
    if user is None:
        user = SITE_SETTINGS['user']
    activate = join(SITE_SETTINGS['venvs_dir'],  virtualenv, 'bin/activate')
    sudo("su %s -c 'source %s; %s'" % (user, activate, cmd))


def collectstatic():
    with cd(SITE_SETTINGS['repo_dir']):
        vsu('./manage.py collectstatic --noinput')


def randomstring(n):
    return ''.join(random.choice(string.ascii_letters + string.digits + '~@#%^&*-_') for x in range(n))


def template_path(filename):
    return join(FAB_HOME, 'templates', filename)


def mkvirtualenv(virtualenv=None):
    if virtualenv is None:
        virtualenv = SITE_SETTINGS['default_virtualenv']
    with cd(join(SITE_DIR, 'venvs')):
        su('virtualenv %s' % virtualenv)
