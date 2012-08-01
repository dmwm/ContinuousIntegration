#!/usr/bin/env python2.6


import sys
import os
import json
import urllib
import inspect
from restkit import Resource, BasicAuth, Connection, request
from socketpool import ConnectionPool

_, jobName, repo, inputfile = sys.argv

secrets    = json.load( open("secrets.json" ) )
jenkinsObj = json.load( urllib.urlopen("http://localhost:8080/job/%s/api/json?depth=1" % jobName) )
lastBuild = jenkinsObj['lastCompletedBuild']['number']
lastGood  = jenkinsObj['lastSuccessfulBuild']['number']
lastBad   = jenkinsObj['lastFailedBuild']['number']
githubUrl = "https://github.com/dmwm/%s" % repo
pool = ConnectionPool(factory=Connection)
serverurl="https://api.github.com"
githubToken = secrets['token']
headers = {'Content-Type' : 'application/json' }
headers['Authorization'] = 'token %s' % githubToken

def doGithub( url, method = 'GET', payload = None ):
    # screw it
    global headers, pool
    resource = Resource(url, pool=pool)
    if payload:
        payload = json.dumps(payload)

    response = resource.request(headers = headers,
                             payload = payload,
                                method = method)

    return json.loads(response.body_string())


##response = resource.get(headers = headers)
#repos = json.loads(response.body_string())
#print repos

if (lastBuild == lastGood):
    # check github to see if we already opened a ticket
    myIssues = doGithub('https://api.github.com/repos/dmwm/%s/issues' % repo, payload =\
                               { 'filter' : 'created',
                                 'labels' : ['JenkinsFail'] } )

    issueTitle = "%s is failing on %s" % (jobName, repo)
    for issue in myIssues:
        if issue['title'] == issueTitle:
            # close the issue
            toClose = issue['number']
            doGithub('https://api.github.com/repos/dmwm/%s/issues/%s/comments' %\
                            ( repo, toClose ),
                     payload = { 'body' : "Test is passing again. Closing." },
                     method = 'POST')

            doGithub('https://api.github.com/repos/dmwm/%s/issues/%s' % \
                            ( repo, toClose ),
                     payload = { 'state' : 'closed' },
                     method  = 'PATCH')
            print "%s is now passing!" % jobName
            sys.exit(0)
    # build looks good, go back to see if we were previously failing
    pass
else:
    # Oh no, a job failed. Investigate
    continuingFailure = True

    # now, find the failing build
    failingBuild = jenkinsObj['builds'][0]
    for build in jenkinsObj['builds']:
        if build['result'] == 'SUCCESS':
            break
        elif build['result'] in [u'FAILURE', u'ABORTED']:
            failingBuild = build

    # check github to see if we already opened a ticket
    myIssues = doGithub('https://api.github.com/repos/dmwm/%s/issues' % repo, payload =\
                               { 'filter' : 'created',
                                 'labels' : ['JenkinsFail'] } )

    issueTitle = "%s is failing on %s" % (jobName, repo)
    for issue in myIssues:
        if issue['title'] == issueTitle:
            print "%s is still failing!" % jobName
            sys.exit(0)

    print "%s has started to fail!" % jobName
    issueTitle = "%s is failing on %s" % (jobName, repo)
    commitList = []
    for commit in failingBuild['changeSet']['items']:
        msg = commit['msg'][:40] + '..' if len(commit['msg']) > 38 else commit['msg']
        msg.replace('\n','')

        commitList.append( [commit['id'], msg ])

    issueMessage  = "# %s is now failing!#\n\n" % jobName
    issueMessage += "Someone broke jenkins!\n\n"
    issueMessage += "## Guilty Commits ##\n"
    for commit in commitList:
        issueMessage += "* [%s](%s/commit/%s)\n" % (commit[1], githubUrl,
                                                    commit[0])
    issueMessage += "\n\n## Jenkins Reference ##\n"
    issueMessage += "Build URL: %s\n" % failingBuild['url']
    issueMessage += "\n\nThanks, \nJenkins :cop:\n\n\n"
    issueMessage += "DMWMJENKINSMAGIC: %s!%s!%s" % (jobName,repo,lastBuild)
    resource = Resource('https://api.github.com/repos/dmwm/%s/issues' % repo, pool=pool)
    issueInfo = {"title" : issueTitle, 
                 "body" : issueMessage, \
                 "labels" : ['JenkinsFail']}
    response = resource.post(headers = headers, payload =
    json.dumps(issueInfo))
    repos = json.loads(response.body_string())
#
    print issueMessage




sys.exit(0)
{
      "actions" : [
        {
          "parameters" : [
            {
              "name" : "WMAGENT_VERSION",
              "value" : ""
            },
            {
              "name" : "SCRAM_ARCH",
              "value" : "slc5_amd64_gcc461"
            },
            {
              "name" : "branch",
              "value" : "master"
            },
            {
              "name" : "pathToTest",
              "value" : "test/python"
            },
            {
              "name" : "unused",
              "value" : ""
            }
          ]
        },
        {
          "causes" : [
            {
              "shortDescription" : "Started by an SCM change"
            }
          ]
        },
        {
          
        },
        {
          
        },
        {
          "buildsByBranchName" : {
            "origin/svnmaster" : {
              "buildNumber" : 681,
              "buildResult" : null,
              "revision" : {
                "SHA1" : "f222ab2f2ccf82a6f8539d78c4590cb2171a6e92",
                "branch" : [
                  {
                    "SHA1" : "f222ab2f2ccf82a6f8539d78c4590cb2171a6e92",
                    "name" : "origin/svnmaster"
                  }
                ]
              }
            },
            "origin/ignoretestfail" : {
              "buildNumber" : 556,
              "buildResult" : null,
              "revision" : {
                "SHA1" : "2480a8b0990a2ec45441936d45fe33e6c2d93f93",
                "branch" : [
                  {
                    "SHA1" : "2480a8b0990a2ec45441936d45fe33e6c2d93f93",
                    "name" : "origin/ignoretestfail"
                  }
                ]
              }
            },
            "origin/master" : {
              "buildNumber" : 715,
              "buildResult" : null,
              "revision" : {
                "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
                "branch" : [
                  {
                    "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
                    "name" : "origin/master"
                  }
                ]
              }
            }
          },
          "lastBuiltRevision" : {
            "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
            "branch" : [
              {
                "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
                "name" : "origin/master"
              }
            ]
          },
          "scmName" : "WMCore"
        },
        {
          
        },
        {
          "buildsByBranchName" : {
            "origin/master" : {
              "buildNumber" : 715,
              "buildResult" : null,
              "revision" : {
                "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
                "branch" : [
                  {
                    "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
                    "name" : "origin/master"
                  }
                ]
              }
            }
          },
          "lastBuiltRevision" : {
            "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
            "branch" : [
              {
                "SHA1" : "300acc4bfa4130407503ca23584d835a01d73a93",
                "name" : "origin/master"
              }
            ]
          },
          "scmName" : "Infrastructure"
        },
        {
          
        },
        {
          "failCount" : 170,
          "skipCount" : 0,
          "totalCount" : 1116,
          "urlName" : "testReport"
        },
        {
          
        },
        {
          
        }
      ],
      "artifacts" : [
        
      ],
      "building" : false,
      "description" : null,
      "duration" : 739224,
      "estimatedDuration" : 348210,
      "fullDisplayName" : "WMCore-UnitTests #715",
      "id" : "2012-07-31_22-21-49",
      "keepLog" : false,
      "number" : 715,
      "result" : "ABORTED",
      "timestamp" : 1343766109131,
      "url" : "http://dmwm.cern.ch:8080/job/WMCore-UnitTests/715/",
      "builtOn" : "slc5-64-09",
      "changeSet" : {
        "items" : [
          {
            "affectedPaths" : [
              "setup_test.py"
            ],
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "commitId" : "043da1fd6587ad5abdd5f53ef52bb549e2ea1316",
            "msg" : "Refines how to trap os._exit in testing mode",
            "timestamp" : 1343763352000,
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "comment" : "Refines how to trap os._exit in testing mode\n",
            "date" : "2012-07-31 21:35:52 -0500",
            "id" : "043da1fd6587ad5abdd5f53ef52bb549e2ea1316",
            "msg" : "Refines how to trap os._exit in testing mode",
            "paths" : [
              {
                "editType" : "edit",
                "file" : "setup_test.py"
              }
            ]
          },
          {
            "affectedPaths" : [
              "setup_test.py"
            ],
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "commitId" : "dca7bfc678263dcd345a18f08c0fc7a7a896a12d",
            "msg" : "Add cherrypy-slaying abilities to the test mode",
            "timestamp" : 1343765779000,
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "comment" : "Add cherrypy-slaying abilities to the test mode\n",
            "date" : "2012-07-31 22:16:19 -0500",
            "id" : "dca7bfc678263dcd345a18f08c0fc7a7a896a12d",
            "msg" : "Add cherrypy-slaying abilities to the test mode",
            "paths" : [
              {
                "editType" : "edit",
                "file" : "setup_test.py"
              }
            ]
          },
          {
            "affectedPaths" : [
              "setup_test.py"
            ],
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "commitId" : "043da1fd6587ad5abdd5f53ef52bb549e2ea1316",
            "msg" : "Refines how to trap os._exit in testing mode",
            "timestamp" : 1343763352000,
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "comment" : "Refines how to trap os._exit in testing mode\n",
            "date" : "2012-07-31 21:35:52 -0500",
            "id" : "043da1fd6587ad5abdd5f53ef52bb549e2ea1316",
            "msg" : "Refines how to trap os._exit in testing mode",
            "paths" : [
              {
                "editType" : "edit",
                "file" : "setup_test.py"
              }
            ]
          },
          {
            "affectedPaths" : [
              "setup_test.py"
            ],
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "commitId" : "dca7bfc678263dcd345a18f08c0fc7a7a896a12d",
            "msg" : "Add cherrypy-slaying abilities to the test mode",
            "timestamp" : 1343765779000,
            "author" : {
              "absoluteUrl" : "http://dmwm.cern.ch:8080/user/andrew.melo",
              "fullName" : "andrew.melo"
            },
            "comment" : "Add cherrypy-slaying abilities to the test mode\n",
            "date" : "2012-07-31 22:16:19 -0500",
            "id" : "dca7bfc678263dcd345a18f08c0fc7a7a896a12d",
            "msg" : "Add cherrypy-slaying abilities to the test mode",
            "paths" : [
              {
                "editType" : "edit",
                "file" : "setup_test.py"
              }
            ]
          }
        ],
        "kind" : null
      },
      "culprits" : [
        {
          "absoluteUrl" : "http://dmwm.cern.ch:8080/user/%231246",
          "fullName" : "#1246"
        },
        {
          "absoluteUrl" : "http://dmwm.cern.ch:8080/user/Daniele.Spiga",
          "fullName" : "Daniele.Spiga"
        },
      ],
      "runs" : [
        {
          "number" : 715,
          "url" : "http://dmwm.cern.ch:8080/job/WMCore-UnitTests/./jobSlice=0,label=wmcore-unit-test-slaves/715/"
        },
      ]
    },
