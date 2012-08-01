#!/bin/bash

echo "Starting at `date`"
./checkStatus.py WMCore-UnitTests WMCore success.json &
./checkStatus.py deploy-wmagent WMCore success.json
./checkStatus.py deploy-reqmgr WMCore success.json
./checkStatus.py deploy-workqueue WMCore success.json

