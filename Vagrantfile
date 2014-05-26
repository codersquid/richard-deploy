# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    config.vm.box = "chef/debian-7.4"
    config.vm.box_url = "http://opscode-vm-bento.s3.amazonaws.com/vagrant/virtualbox/opscode_debian-7.4_chef-provisionerless.box"

    config.vm.network "forwarded_port", guest: 80, host: 8081
    config.ssh.forward_agent = true

    # config.vm.provision "shell", inline: $root_script
    # config.vm.provision "shell", privileged:false, inline: $user_script
end
