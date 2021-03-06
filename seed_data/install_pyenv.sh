#!/bin/bash
source ~/.bashrc

env

sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
     libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
     libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl \
     git

curl https://pyenv.run | bash

echo -e '\neval "$(pyenv init -)"' | sudo tee --append /etc/profile
echo -e '\neval "$(pyenv init -)"' >> /home/codegrade/.bash_profile
echo -e '\neval "$(pyenv init -)"' >> /home/codegrade/.bashrc
pyenv update

exit 0
