This repo is a document which will guide you to install [EcoPAD](https://ecolab.nau.edu/ecopad) in [Dr. Yiqi Luo's EcoLAB](https://www2.nau.edu/luo-lab/).

## Preparation

### Windows

For Windows users, you may install either **[VirtualBox](https://www.virtualbox.org/)** or **[VMware WorkStation](https://www.vmware.com/products/workstation-pro/workstation-pro-evaluation.html)** on your computer and set up a **Ubuntu 20.04** virtual machine to do the following steps.

### Linux

For Linux users, you may install **Docker** on your computer.

### MacOS

For MacOS users, you may try to apply for a personal use license for **[VMware Fusion](https://www.vmware.com/products/fusion.html)** and install a **install Ubuntu 20.04** virtual machine to do the following steps.

## Download the essential files

All the files can be downloaded [here](https://drive.google.com/file/d/1kDOSnQFzHOhcRhrey65lWKaSdBddNUlz/view?usp=sharing), you need to extract it and put the folder **images_saved** under your home folder (**/home/your_user_name**).

## Install all the docker images

Locate to the images_saved folder under your home:
```Bash
cd /home/YOUR_USER_NAME/images_saved
```

Run the following commands to install all the images:

```
docker load -i api.tar
docker load -i celery.tar
docker load -i memcached.tar
docker load -i mongo.tar
docker load -i rabbitmq.tar
docker load -i test.tar
```
## Modify the configuration

Once you have installed all the docker images, you need to make some modification to the **restart_docker** file. Open it with a text editor and replace the **host_ip**
 with your own ip address. Once you down, save and close the file.
 
## Use Key instead of password to log in to your computer

First, locate to the folder:

```Bash
cd /home/YOUR_USER_NAME/.ssh
```

Run the following command to create a new key:

```Bash
ssh-keygen # You don't have to input anything, just use Enter to continue
```

If you didn't change the name of the key, the path of the private key should be:

```
/home/YOUR_USER_NAME/.ssh/id_rsa
```

And the public key should be:

```
/home/YOUR_USER_NAME/.ssh/id_rsa.pub
```

Open the ssh service config file:

```
sudo vim /etc/ssh/sshd_config
```

Add the following 3 lines:

```
RSAAuthentication yes 
PubkeyAuthentication yes
AuthorizedKeysFile  .ssh/id_rsa.pub
```

## Launch the docker containers

Locate to the folder and run the script:

```Bash
cd /home/YOUR_USER_NAME/images_saved
touch thisisfirstrun
bash restart_docker
```

## Test EcoPAD

Open [this link](http://127.0.0.1/api/queue) and login use the username and password you already know. At this time you may follow the PDF file we used before to
 test the **test** api. 
