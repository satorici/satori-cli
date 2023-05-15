# 1. Five Ws (and one H)

## 1.1 What is Satori CI?

Satori CI is an automated software testing as a service. It asserts what the outputs of the programs will be. Consider the following example "Hello World" program in Python:

```py
print("Hello World")
```

If we execute this program, we will see the following:

```py
$ ./hello_world.py
Hello World
```

We can assert that the return code will be 0 and the standard output of this program will be Hello World:

```yml
test:
    assertReturnCode: 0
    assertStdoutEqual: Hello World
    python:
    - [ ./hello_world.py ]
```

## 1.2 Why

This no code testing language will help you test your software throughout different stages of its development lifecycle. Playbooks can look both at source code and execution (more examples of this in the "CI: Import" section)

## 1.3 Who

Test engineers, software developers and security testers.

## 1.4 When

You can attach it to your CI process (Satori CI), you can launch them manually (Satori Run), and you can launch them periodically (Satori Monitor)

## 1.5 Where

Satori can be used on your continuous integration, deployment and delivery tests.

## 1.6 How to use it?

First, login at https://www.satori-ci.com using your Github account to be able to use our CI cappabilities. Github will ask for confirmation for us to access to your repositories of choice. After accepting the conditions, you can get a token fromus at https://www.satori-ci.com/user-settings/ 

You will use that token to setup your account with our CLI tool

```sh
git clone git@github.com:satorici/satori-cli.git
cd satori-cli/
apt install python3.10
pip3 install -f requirements.txt
# TBD: pip3 install satori-cli
satori-cli config default YOUR_TOKEN
```

# 2. Playbooks

Are used to assert software behaviors, wether they are source code files or live systems.

## 2.1 Playbooks: Hello World

TBC

## 2.2 Playbooks: Import

Playbooks can import other local or remote playbooks. We keep at TBC a list of playbooks that can be referenced with the

```yml
import:
    - satori://code/trufflehog.yml

test:
    assertStdoutEqual: "Hello World"
    bash:
    - [ echo "Hello World" ]
```

Is there a playbook that you would like us to incluide? Drop us a line at support@satori-ci.com

# 3. CI

Check how your repositories are connected to our CI with. This command will show you what is our visibility on your repositories. We will tell you which ones are connected, if they have a playbook associated and what is their status.
Example output:

```sh
$ satori-cli ci
TBC
```

## 2.1 CI: Add a playbook file
Adding a file named .satori.yml in your root directory, we will be used by your Github pushes to test your code. Lets suppose for example that you created a Hello World application, and you want to know that that will be the output every time you push new code:

- .satori.yml:

```yml
test:
    assertStdoutEqual: "Hello World"
    bash:
    - [ echo "Hello World" ]
```

# Monitor

Check that your assets are correctly monitored. This command will check on the playbooks that are running with a crontab to monitor resources:
`satori-cli monitor`
Example output:

```sh
TBC
```

## Monitor: add a playbook to be executed at a certain rate

Playbook that define a rate are automatically included within the monitor functionality:

- MonitorBlog.yml

```yml
settings:
  - name: Monitor Blog
  - rate: TBC

test:
  assertStdout: "Hello World"
  blog:
  - [ curl -s https://www.satori-ci.com/hello-world/ ]
```

This will be checked every X minutes once you execute it. Example:

```sh
$ satori-cli run MonitorBlog.yml`
TBC
```

## Monitor: stopping and running again a playbook

You will get a list with the `satori-cli monitor`, from where you will take the UUID. You can use that UUID with the `stop` and `run` subcommands

```sh
$ satori-cli stop UUID
TBC
```

# Scan 
TBC

### Scan all your commits

```sh
$ satori-cli scan GithubAccount/Repository -c 100
TBC
```

# Playbooks:

You can see a list of public playbooks when at https://github.com/satorici/playbooks/

```sh
$ satori-cli playbook
Private playbooks:
Public Playbooks:
```

## Public playbooks:

They can be imported by playbooks that you have in your CI or on assets being Monitored.

```sh
$ satori-cli playbook --public
URI                          | Name                                            
satori://code/trufflehog.yml | Trufflehog will search for secrets in your code 
...
```

## Private Playbooks:

We will store a copy of the playbooks that you have executed and show them to you whenever you execute the command:

```sh
$ satori-cli playbooks private
Type    | URI                                                     | Name           | Imports
CI      | github://satorici/satori-cli/.satori.yml                |                |
Monitor | github://satorici/playbooks/test/satori/monitor.yml     | Monitor Assets | monitorBlog.yml
Run     | github://satorici/playbooks/test/satori/monitorBlog.yml | Monitor Blog   |
...
```
