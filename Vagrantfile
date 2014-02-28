# -*- mode: ruby -*-
# # vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure("2") do |config|
    config.vm.box = "precise64"
    config.vm.box_url = "http://files.vagrantup.com/precise64.box"
    config.vm.provision :shell, :path => "vagrant/bootstrap.sh"
end
