# -*- mode: ruby -*-
# vi: set ft=ruby :


$root_script = <<SCRIPT
apt-get --assume-yes update
apt-get --assume-yes install squid-deb-proxy-client
apt-get --assume-yes update
apt-get --assume-yes --force-yes install git python-virtualenv
apt-get --assume-yes --force-yes install python-paramiko
apt-get --assume-yes --force-yes install vim
SCRIPT

$user_script = <<SCRIPT
virtualenv --system-site-packages ps1
source ps1/bin/activate
printf "source ps1/bin/activate\n" >> .bashrc

if [ -d /vagrant ]; then
  mkdir richard-deploy
  cp -av /vagrant/* richard-deploy
else  
  git clone https://github.com/codersquid/richard-deploy.git
fi
cd richard-deploy

pip install -r requirements.txt

fab vagrant provision

SCRIPT

VAGRANTFILE_API_VERSION = "2"
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    config.vm.box = "chef/debian-7.4"
    config.vm.box_url = "http://opscode-vm-bento.s3.amazonaws.com/vagrant/virtualbox/opscode_debian-7.4_chef-provisionerless.box"

    config.vm.network "forwarded_port", guest: 80, host: 8081
    config.ssh.forward_agent = true

    config.vm.provision "shell", inline: $root_script
    # config.vm.provision "shell", privileged:false, inline: $user_script
end
