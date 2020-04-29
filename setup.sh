#
# Script must be run as sudo
# run this inside smartShards dir (a.k.a dont move to run)
# some post install steps maybe necessary see https://docs.docker.com/engine/install/linux-postinstall/
#

# make sure old version is not present 
apt-get remove docker docker-engine docker.io containerd runc

# install docker and python3
apt-get update
apt-get -y \
    install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common \
    python3 \
    python3-pip

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

apt-get -y install docker-ce docker-ce-cli containerd.io

# add user to docker group (remove need for sudo access to use API)
groupadd docker
usermod -aG docker $USER

# install docker API
pip3 install docker

# build sawtooth image
docker build -t sawtooth:final -f  ./base-node.Dockerfile .

export PYTHONPATH=$PYTHONPATH:$PWD