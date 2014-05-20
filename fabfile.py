"""deployment scripts for researchcompendia
with credit to scipy-2014 and researchcompendia fabric.py

fab <deploy|provision>[:<git ref>]

deploy: deploys a version of the site. if no git ref is provided, deploys HEAD.
provision: provisions a box to run the site. is not idempotent. do not rerun.
git ref: a git branch, hash, tag

provision: provisions a new box.

example usages:

deploy new version of the site with an updated virtualenv.
$ fab deploy:1.1.1


WARNINGS

This does not set up elasticsearch or the cron jobs for indexing and running
the link checker.

deploy has never been properly tested

provision is no longer properly tested, Carl wanted an vagrant example
and I don't have time to finish this today. It's a start for him to pick
up, unless I get to it first.

"""
import string, random
from os.path import join, dirname, abspath
from fabric.api import run, task, env, cd, sudo, local
from fabric.contrib.files import sed, append
from fabtools import require, supervisor, postgres, files
from fabtools.files import upload_template
import fabtools

env.disable_known_hosts = True
env.user = 'vagrant'
env.hosts = ['127.0.0.1:2222']
# for vagrant
env.key_filename = local('vagrant ssh-config | grep IdentityFile | cut -f4 -d " "', capture=True)

FAB_HOME = dirname(abspath(__file__))
TEMPLATE_DIR = join(FAB_HOME, 'templates')
SITE_DIR = join('/', 'srv', 'writethedocs')

SITE_SETTINGS = {
    'repo_dir': join(SITE_DIR, 'richard'),
    'setup_args': '.[postgresql]',
    #'repo': 'https://github.com/willkg/richard.git',
    'repo': 'https://github.com/paulcollinsiii/richard.git',
    'user': 'richard',
    'group': 'richard',
    'supervised_process': 'writethedocs',
    'virtualenv': 'venv',
    #'settings_module': 'wtd.richard.settings',
    'settings_module': 'richard.settings',
    #'wsgi_module': 'wtd.richard.wsgi',
    'wsgi_module': 'richard.wsgi',
    'server_name': 'writethedocs.org',
    'django_site_url': 'http://video.writethedocs.org',
}


@task
def uname():
    """call uname to check that we can do a simple command
    """
    run('uname -a')


@task
def deploy(version_tag=None):
    """deploys a new version of the site

    version_tag: a git tag, defaults to HEAD
    """
    supervised_process = SITE_SETTINGS['supervised_process']

    #dust()
    stop(supervised_process)
    update(commit=version_tag)
    setup()
    collectstatic()
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


@task
def update(commit='origin/master'):
    repo_dir = SITE_SETTINGS['repo_dir']

    if not files.is_dir(repo_dir):
        with cd(SITE_DIR):
            su('git clone %s' % SITE_SETTINGS['repo'])

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
def provision(commit='origin/master'):
    """Run only once to provision a new host.
    This is not idempotent. Only run once!
    """
    install_packages()
    install_python_packages()
    lockdown_nginx()
    lockdown_ssh()
    # Use if you want a postgres db rather than sqlite
    # TODO you'll also need to change the django settings
    #setup_database()
    setup_site_user()
    setup_site_root()
    provision_django(commit)
    setup_nginx_site()
    setup_supervisor()


def setup_nginx_site():
    nginx_site = 'richard'
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


def provision_django(commit='origin/master'):
    with cd(SITE_DIR):
        su('virtualenv %s' % SITE_SETTINGS['virtualenv'])
        update(commit)
        setup()
        provision_django_settings()
        collectstatic()
        syncdb()

def provision_django_settings():
    #cpy settings_local.py-dist
    secret = randomstring(64)
    with cd(join(SITE_SETTINGS['repo_dir'], 'richard')):
        su('cp settings_local.py-dist settings_local.py')
        # TODO inadequately secure. it will get echoed to stdout
        # one thing I've seen people do is
        # echo export SECRET_KEY=\"`dd if=/dev/urandom bs=512 count=1 | tr -dc 'a-zA-Z0-9~@#%^&*-_'`\" >> bin/environment.sh
        sed('settings_local.py', 'secret', secret)
        # TODO sed: couldn't open temporary file ./sedrMyp5L: Permission denied
        # I screwed up permissions. fix this. I'm checking it in for Carl to look at for now.
        sed('settings_local.py', 'http://127.0.0.1:8000', SITE_SETTINGS['django_site_url'])


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
        #vsu("pip install psycopg2", virtualenv=virtualenv)


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
        su('mkdir -p logs bin')

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
        'libxml2',
        'libxslt-dev',
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
    sudo("su %s -c 'source %s; %s'" % (user, activate, cmd))


def collectstatic():
    with cd(SITE_SETTINGS['repo_dir']):
        vsu('./manage.py collectstatic --noinput')


def randomstring(n):
    return ''.join(random.choice(string.ascii_letters + string.digits + '~@#%^&*-_') for x in range(n))
