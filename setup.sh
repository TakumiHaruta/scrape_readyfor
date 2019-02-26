#!/bin/bash

sudo apt-get -y -q update
sudo apt-get upgrade -y -q
sudo apt-get -y -q install python3 python3-pip python3-setuptools git
pip3 install requests lxml slackclient

git clone https://github.com/TakumiHaruta/crowdfunding_crawler
timedatectl set-timezone Asia/Tokyo
crontab -e #30 6 * * * python3 ~/crowdfunding_crawler/scrape_ready_for.py >> ~/srf.log
touch ~/srf.log
