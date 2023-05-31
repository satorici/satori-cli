# Intro
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
satori-cli config token YOUR_TOKEN`
```

## Actions

You can take actions on:

  * **run**: whenever you are launching on demand scans for playbook files or directories
  * **repo**: whenever you are taking actions on repositories
  * **monitor**: visualize your scheduled playbooks
  * **team**: actions related to your team settings

Now, lets test software.

## satori-cli run

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
    assertStdoutEqual: Hello World
    python:
    - [ python hello_world.py ]
```

Lets test the code with the playbook
```console
foo@bar:~$ satori-cli run ./ --sync
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
  
  * **assertStdoutEquals**: String*
  
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

