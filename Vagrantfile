# -*- mode: ruby -*-
# vi: set ft=ruby :

#$script = <<SCRIPT
#SCRIPT

VAGRANTFILE_API_VERSION = "2"
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "chef/debian-7.4"
  # uncomment if your version of vagrant does not pull from https://vagrantcloud.com/chef/debian-7.4 automatically
  #config.vm.box_url = http://opscode-vm-bento.s3.amazonaws.com/vagrant/virtualbox/opscode_debian-7.4_chef-provisionerless.box
  config.vm.network "forwarded_port", guest: 8000, host: 8000

  config.ssh.forward_agent = true

  #config.vm.provision "shell", inline: $script
  #config.vm.provision "shell", path: "bootstrap.sh"

end
