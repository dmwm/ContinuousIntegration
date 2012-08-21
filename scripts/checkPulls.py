#!/usr/bin/env python2.6

import time
import pprint
import sys
import os
import json
import urllib
import inspect
import logging
import subprocess
import multiprocessing
import os.path
import fcntl
import shutil

from restkit import Resource, BasicAuth, Connection, request
from socketpool import ConnectionPool
logging.basicConfig( level = logging.DEBUG )
_, jobName, repo, inputfile = sys.argv

pullList   = json.load( open(inputfile) )
secrets    = json.load( open("secrets.json" ) )
try:
    status     = json.load( open("status.json",'r') )
except ValueError:
    raise
    status = {"pulls" : {}}
# jenkinsObj = json.load( urllib.urlopen("http://localhost:8080/job/%s/api/json?depth=1" % jobName) )
#lastBuild = jenkinsObj['lastCompletedBuild']['number']
#lastGood  = jenkinsObj['lastSuccessfulBuild']['number']
#lastBad   = jenkinsObj['lastFailedBuild']['number']
githubUrl = "https://github.com/dmwm/%s" % repo
pool = ConnectionPool(factory=Connection)
serverurl="https://api.github.com"
githubToken = secrets['token']
headers = {'Content-Type' : 'application/json' }
headers['Authorization'] = 'token %s' % githubToken

def doGithub( url, method = 'GET', payload = None ):
    # screw it
    global headers, pool, serverurl
    url = serverurl + url
    resource = Resource(url, pool=pool)
    if payload:
        payload = json.dumps(payload)
    print "getting %s" % url
    response = resource.request(headers = headers,
                             payload = payload,
                                method = method)

    return json.loads(response.body_string())

def getRevision( user, repo, ref ):
    return doGithub("/repos/%s/%s/git/refs/%s" % (user, repo, ref))

# dev id is 188953
# commit id is 231676

if not 'devList' in status or\
    status['devList']['time'] + 3600 < time.time():
    logging.info("Updating authorized users")
    # update the group memberships every hour
    status['devList'] = { 'time' : 0,
                          'committers' : [],
                          'developers' : [] }

    devList = doGithub("/teams/188953/members")
    commitList = doGithub("/teams/231676/members")
    for user in devList:
        status['devList']['developers'].append(user['login'])

    for user in commitList:
        status['devList']['committers'].append(user['login'])

    status['devList']['time'] = time.time()
    json.dump( status, open('status.json', 'w'))

##response = resource.get(headers = headers)
#repos = json.loads(response.body_string())
#print repos

# get the github requests
myPulls = doGithub('/repos/dmwm/%s/pulls' % repo )
json.dump( myPulls, open('pull.json', 'w'))

#myPulls = pullList
pullsToBuild = []
for pull in myPulls:
    pullSHA      = pull['head']['sha']
    baseSHA      = pull['base']['sha']
    updateTime   = pull['head']['repo']['updated_at']
    baseTime     = pull['base']['repo']['updated_at']
    pullID       = u'%s' % pull['id']
    pullNum      = pull['number']
    pullUser     = pull['head']['user']['login']
    targetBranch = pull['base']['ref']
    headRepo     = pull['head']['repo']['clone_url']
    baseRepo     = pull['base']['repo']['clone_url']
    if pullNum == 4023:
        pass
        #pprint.pprint( pull )

#    if pullUser not in [ "PerilousApricot", "ericvaandering", "dballesteros7" ]:
#        continue

    logging.info("Examining pull %s" % pullNum)

    pullUpdated = False
    headUpdated = False
    if not status['pulls'].get(pullID, None):
        logging.debug("Found a new pull: %s (%s)" % (pullNum, pullID))
        status['pulls'][pullID] = {}
        status['pulls'][pullID]['pullUpdate'] = "DUMMY"
        status['pulls'][pullID]['baseUpdate'] = "DUMMY"
        status['pulls'][pullID]['gitstatus']  = "new"
        status['pulls'][pullID]['teststatus'] = "new"
        pullUpdated = True

    elif status['pulls'][pullID]['pullUpdate'] != updateTime:
        # we need to test the job
        pullUpdated = True
        logging.info("Pull request was updated. Building")
        status['pulls'][pullID]['pullUpdate'] = updateTime
        status['pulls'][pullID]['baseUpdate'] = baseTime

    elif status['pulls'][pullID]['baseUpdate'] != baseTime:
        # the branched-against repo changed rerun
        # tests after a timeout (to keep from flooding jenkins
        # when someone makes several commits)
        headUpdated = True
        logging.info("Upstream branch was changed. Building")
        status['pulls'][pullID]['pullUpdate'] = updateTime
        status['pulls'][pullID]['baseUpdate'] = baseTime

    # keep random people from writing code
    if pullUser not in status['devList']['developers']:
        logging.info("User %s has no permission to commit here..." % pullUser)
        if status['pulls'][pullID]['gitstatus'] != 'unauthorized':
            # only complain once
            status['pulls'][pullID]['gitstatus'] = 'unauthorized'
            issueMessage  = "# Unauthorized #\n\n"
            issueMessage += "The user %s isn't in the developers group\n"
            issueMessage += "Thanks,\nJenkins :cop:"
            doGithub("/repos/dmwm/%s/issues/comments/%s" % (repo, pullNum),
                     method = 'POST', payload={'body':issueMessage})
            logging.info("Posted a notice to GH about the permissions")

        continue


    if headUpdated or pullUpdated:
        # run jenkins!
        logging.info("Running jenkins on pull request %s" % pullNum)
        if not os.path.exists('/tmp/jenkins-github/%s/SHAREDOBJ' % repo):
            command  = "mkdir -p /tmp/jenkins-github/%(repo)s/SHAREDOBJ; "
            command += "cd /tmp/jenkins-github/%(repo)s/SHAREDOBJ ; "
            command += "git clone --bare %(baseRepo)s .;"
        else:
            command  = "cd /tmp/jenkins-github/%(repo)s;"

        command += "git --git-dir SHAREDOBJ remote add user_%(pullUser)s %(headRepo)s ;"
        command += "git --git-dir SHAREDOBJ fetch origin ;"
        command += "git --git-dir SHAREDOBJ fetch user_%(pullUser)s ;"
        command += "rm -rf %(pullNum)s ; "
        command += "git clone --reference SHAREDOBJ %(baseRepo)s %(pullNum)s ;"
        command += "cd %(pullNum)s;"
        command += "git checkout %(pullSHA)s;"
        command += "git rebase remotes/origin/%(targetBranch)s;"
        command = command % { 'pullUser': pullUser,
                              'headRepo': headRepo,
                              'baseRepo': baseRepo,
                              'pullNum': pullNum,
                              'pullSHA': pullSHA,
                              'baseSHA': baseSHA,
                              'repo' : repo,
                              'targetBranch' : targetBranch}
        gitCommands = subprocess.Popen( command, shell=True, stdout = subprocess.PIPE,
                                        stderr = subprocess.STDOUT )
        #print command
        gitout, _ = gitCommands.communicate()
        #print gitout
        if gitCommands.returncode:
            if status['pulls'][pullID]['gitstatus'] == u'fail':
                logging.info("Git stuff failed, but they already know that")
                continue
            logging.error("Failed git commands for %s. Reporting." % pullNum)
            issueMessage  = "# Pull Request doesn't apply cleanly! #\n\n"
            if pullUpdated:
                issueMessage += "Before pushing your pull request, please remember to:\n"
                issueMessage += "    git fetch upstream\n"
                issueMessage += "    git rebase upstream/master\n\n"
                issueMessage += "To make a cleanly-applying pull request.\n\n"
            else:
                issueMessage += "It looks like upstream changed and now your patch doesn't apply. Sorry :sad:\n"

            #issueMessage += "## Log ##\n%s\n" % gitout
            issueMessage += "Thanks,\nJenkins :cop:\n"
            status['pulls'][pullID]['gitstatus'] = 'fail'
            doGithub("/repos/dmwm/%s/issues/%s/comments" % (repo, pullNum),
                     method = 'POST', payload={'body':issueMessage})
            continue

        # The git stuff succeeded. Nice.
        status['pulls'][pullID]['gitstatus'] = 'win'
        logging.info("Git passed for %s, moving to build" % pullNum)
        pullsToBuild.append( (pullNum, pullID, pullSHA, baseSHA ) )

# to make things faster, run all the pulls at the same time in different
# subprocesses
pullDict = {}
for pullNum, pullID, pullSHA, baseSHA in pullsToBuild:
    logging.info("Spawning build for %s" % pullNum)
    jenkins_try = subprocess.Popen([os.path.join(os.getcwd(),"try_patch.py"), "--job-name", "WMCore-UnitTests-try", "--upstream-repo", "origin"],
                     stdout = subprocess.PIPE,
                     stderr = subprocess.STDOUT,
                     cwd = "/tmp/jenkins-github/%s/%s" % (repo, pullNum))
    fcntl.fcntl(jenkins_try.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
    pullDict[pullID] = {}
    pullDict[pullID]['subprocess'] = jenkins_try
    pullDict[pullID]['pullNum'] = pullNum
    pullDict[pullID]['logging'] = ""

nextDict = {}
# now poll them all
while pullDict:
    #logging.info("Beginning outer loop")
    time.sleep(1)
    logging.info("Waiting on these requests: %s" % " ".join(pullDict.keys()))
    for pullID in pullDict:
        jenkins_try = pullDict[pullID]['subprocess']
        pullNum = pullDict[pullID]['pullNum']
        #logging.info("Examining %s" % pullNum)
        stillReading = True
        while stillReading:
            try:
                #fcntl.fcntl(jenkins_try.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
                bytesRead = jenkins_try.stdout.read()
                if len(bytesRead) == 0:
                    stillReading = False
                    break
                pullDict[pullID]['logging'] +=  bytesRead
            except IOError:
                stillReading = False
                break

        jenkins_try.poll()

        if jenkins_try.returncode != None:
            jenkins_try.wait()
            build_link = "ERROR"
            try:
                for line in pullDict[pullID]['logging'].split("\n"):
                    if line.find("Job URL: ") != -1:
                        build_link = line.split("Job URL: ")[1]
                        break
            except:
                build_link = "ERROR"

            # got a return value, it ended!
            if jenkins_try.returncode == 0:
                #shutil.rmtree( "/tmp/jenkins-github/%s/%s" % (repo, pullNum) )
                # victory, this is good to go!
                if status['pulls'][pullID]['teststatus'] != 'win':
                    issueMessage  = "# Commit passes Jenkins! #\n"
                    issueMessage += "Congrats, this pull request passes Jenkins [report](%s)\n\n" % build_link
                    issueMessage += "Thanks,\nJenkins :cop:\n\n"
                    issueMessage += "p.s. there are still \"known failing\" tests [here](https://github.com/dmwm/WMCore/blob/master/standards/allowed_failing_tests.txt). "
                    issueMessage += "So, it's possible a test is failing that we're ignoring...."
                    doGithub("/repos/dmwm/%s/issues/%s/comments" % (repo, pullNum),
                                                                     method = 'POST', payload={'body':issueMessage})

                logging.info("Pull requst %s passes CI" % pullNum)
                status['pulls'][pullID]['teststatus'] = 'win'
            else:
                if status['pulls'][pullID]['teststatus'] != 'fail':
                    issueMessage  = "# Commit fails Jenkins #\n"
                    issueMessage += "This request fails testing. Check [here](%s) for more info\n\n" % build_link
                    issueMessage += "Thanks,\nJenkins :cop:\n\n"
                    issueMessage += "p.s. there are still \"known failing\" tests [here](https://github.com/dmwm/WMCore/blob/master/standards/allowed_failing_tests.txt). "
                    issueMessage += "So, it's possible a test is failing that we're ignoring...."
                    doGithub("/repos/dmwm/%s/issues/%s/comments" % (repo, pullNum),
                                                                     method = 'POST', payload={'body':issueMessage})
                logging.info("Pull request %s fails CI" % pullNum)
                status['pulls'][pullID]['teststatus'] = 'fail'
        else:
            # still processing
            nextDict[pullID] = pullDict[pullID]

    # set variables for next loop
    pullDict = nextDict
    nextDict = {}

logging.info("Done processing PR")
json.dump(status, open('status.json', 'w'))
