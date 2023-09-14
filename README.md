# What is Satori CI?

Satori allows you to assert how systems and software behave. Automatize software and system testing using three different approaches:
- On demand: you need to execute the test one time (ie, Security Testing, Stress Testing, etc)
- Scheduled: you need to know on a regular basis what is the status of something (ie, Monitoring live systems every five minutes, Auditing weekly/monthly/yearly systems, etc)
- CI/CD: you need to execute it every time you are pushing new code (ie, Security Testing, System Testing, etc)

## Setup Satori CLI
Three steps:
1. Execute on your command line terminal:

```console
pip3 install satori-ci
```

2. With Satori CLI installed, now we need to get a Satori Token to use it:

 * Log in the Satori website using Github credentials: https://www.satori-ci.com/login
 * On the Satori website go to User Settings
 * Copy your User API Token

3. Replace the string YOUR_TOKEN with your clipboard on the next command:

```console
satori config token YOUR_TOKEN
```

## Actions

You can take actions on:

  * **run**: whenever you are launching on demand scans for playbook files or directories
  * **repo**: whenever you are taking actions on repositories
  * **monitor**: visualize your scheduled playbooks
  * **team**: actions related to your team settings

Now, lets test software.

## satori run

Consider the following example "Hello World" program written in Python:

```py
print("Hello World")
```

If save that into a file named `hello_world.py` and we execute this program, we would see the following on the console:

```console
foo@bar:~$ python hello_world.py
Hello World
```

How can you test aumatically that that piece of software behaves according to specification? You can write a Satori Playbook using a simple and practical notation:

```console
foo@bar:~$ cat .satori.yml
test:
    assertStdoutEqual: "Hello World\n"
    python:
    - [ python hello_world.py ]
```

Lets test the code with the playbook
```console
foo@bar:~$ satori run ./ --sync
Satori CI 1.2.3 - Automated Software Testing Platform
Uploading... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331/331 bytes 0:00:00
UUID: AOQxDWDkXpZp
Report: https://www.satori-ci.com/report_details/?n=AOQxDWDkXpZp
- Report status: Completed | Result: Pass | Elapsed time: 62.6s
  • test: test > python
  • asserts:
      ░ assert: assertStdoutEqual
      ░ status: Pass
      ░ expected: Hello World
      - - - - - - - - - - - - - - - - - - - -
  • testcases: 1
  • test_status: Pass
  • total_fails: 0
  - - - - - - - - - - - - - - - - - - - -
```

The code and the Satori playbook instructions were executed on a new Docker instance hosted by AWS. Satori asserts that this piece of software output "Hello World". You can assert several things:

  * **assertStdout**: True|False

  Is output produced?

  * **assertStdoutEqual**: String*

  Is the output equal to the String?

  * **assertStdoutNotEquals**: String

  Is the output different than String?

  * **assertStdoutContains**: String

  Does the output contains the String?

  * **assertStdoutNotContains**: String

  Does the output not contain the String?
  * **assertStdoutSHA256**: SHA256Checksum

  Is the output equal to this SHA256 hash?

  * **assertStdoutRegex**: Regex

  Does the output matches your regexp?

  * **assertStdoutNotRegex**: Regex

  Does the output not match your regexp?

The previos can also be applied to *assertStderr*. Finally, you can assert the return code of your the execution using **assertReturnCode**.

Please let us know if you need to assert something else that we is not covered by them.

## Setup Satori CI Github App

We tested on demand. Now let's do it as part of your regular Github CI process.

1. Go to https://github.com/apps/satorici

2. Click on Install

3. Select the repositories where you will be installing it or select all repositories

By default you can get notifications via email and Github issues. If you want to get notified in slack, discord or telegram go to https://www.satori-ci.com/user-settings/ to define their details.


If you want to detail in your playbook to be notified when the scans are ready, add the following to them:

```yml
settings:
  log|logOnFail|logOnPass: slack|email|issue|discord|telegram
```

For example:
```yml
settings:
    logOnFail: slack

test:
    assertStdoutEqual: Hello World
    python:
    - [ python hello_world.py ]
```


and put it on a file named .satori.yml inside your repository.

## satori repo

You can check which repositories you connected with a playbook by running

```
foo@bar:~$ satori repo
```

You can scan all your commits from your repository to see if there were any discrepancies at some point:

```console
foo@bar:~$ satori repo githubusername/repository scan -c 100 --sync
```

## satori playbook

Are used to assert software behaviors, wether they are source code files or live systems. You can see a list of public playbooks by running


#### Public playbooks

They can be imported by playbooks that you have in your CI or on assets being Monitored.

```console
foo@bar:~$ satori playbook --public
URI                          | Name
satori://code/trufflehog.yml | Trufflehog will search for secrets in your code
satori://code/semgrep.yml    | Static source code analysis with semgrep

...
```

You can check your private playbooks executed just by running `satori playbook`

#### Import Playbooks

Playbooks can import other local or remote playbooks. We keep at TBC a list of playbooks that can be referenced with the

```yml
import:
    - satori://code/trufflehog.yml
    - satori://code/semgrep.yml

test:
    assertStdoutEqual: Hello World
    python:
    - [ python hello_world.py ]
```

#### Private Playbooks

We will store a copy of the playbooks that you have executed and show them to you whenever you execute the command:

```console
foo@bar:~$ satori playbooks private
Type    | URI                                                     | Name           | Imports
CI      | github://satorici/satori/.satori.yml                |                |
Monitor | github://satorici/playbooks/test/satori/monitor.yml     | Monitor Assets | monitorBlog.yml
Run     | github://satorici/playbooks/test/satori/monitorBlog.yml | Monitor Blog   |
...
```

Is there a playbook that you would like us to add? Drop us a line at support@satori-ci.com


## satori monitor

Assert that your systems are running as expected by setting a schedule for your playbook. Playbooks that define a schedule can be monitored with:

```console
satori monitor
```

For example, you can define schedule a crontab rate to a playbook just as in the following exmaple to verify the Hello World website from Satori every hour:

```yml
settings:
  - name: Monitor Blog
  - schedule: "0 * * * *"
  - logOnFail: slack

test:
  assertStdout: "Hello World"
  blog:
  - [ curl -s https://www.satori-ci.com/hello-world/ ]
```
