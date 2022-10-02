# What is Satori CI?
Satori CI is an automated software testing as a service. 

# How to use it?
First, login at https://www.satori-ci.com using your Github account to be able to use our CI cappabilities. Github will ask for confirmation for us to access to your repositories of choice. After accepting the conditions, you can get a token fromus at https://www.satori-ci.com/user-settings/ 

You will use that token to setup your account with our CLI tool
```
git clone git@github.com:satorici/satori-cli.git
cd satori-cli/
apt install python3.10
pip3 install -f requirements.txt
# TBD: pip3 install satori-cli
satori-cli config default YOUR_TOKEN
```

## Check how your repositories are connected to our CI
`satori-cli ci`
This command will show you what is our visibility on your repositories. We will tell you which ones are connected, if they have a playbook associated and what is their status.
Example output:
```
TBC
```

### Add a playbook to be executed with your Github pushes
Adding a file named .satori.yml in your root directory, we will be reading your instructions to executed them. Lets suppose for example that you created a Hello World application, and you want to know that that will be the output every time you push new code:
- .satori.yml:
```
test:
    assertStdoutEqual: "Hello World"
    bash:
    - [ echo "Hello World" ]
```

### Import a playbook to be executed with your Github pushes

```
import:
    - satori://code/trufflehog.yml  # more playbooks at https://github.com/satorici/playbooks/

test:
    assertStdoutEqual: "Hello World"
    bash:
    - [ echo "Hello World" ]
```

## Monitor
Check that your assets are correctly monitored. This command will check on the playbooks that are running with a crontab to monitor resources:
`satori-cli monitor`
Example output:
```
TBC
```

### Add a playbook: 
Playbook that define a rate are automatically included within the monitor functionality:

- MonitorBlog.yml
```
settings:
  - name: Monitor Blog
  - rate: TBC

test:
  assertStdout: "Hello World"
  blog:
  - [ curl -s https://www.satori-ci.com/hello-world/ ]
```

This will be checked every X minutes once you execute it. Example:
```
$ satori-cli run MonitorBlog.yml`
TBC
```

### Stop
You will get a list with the `satori-cli monitor`, from where you will take the UUID. Example output:
```
$ satori-cli stop UUID
TBC
```

### Start:
You will get a list with the `satori-cli monitor`, from where you will take the UUID .
`satori-cli run UUID`

## Take a look at the playbooks:
`satori-cli playbooks`
You will see the list of public and private playbooks that you have

## Get information about your assets
`satori-cli`



## Monitor your assets
```
$ satori-cli monitor
TBC
```

## Scan all your commits
```
$ satori-cli scan GithubAccount/Repository -c 100
TBC
```

## Run playbooks

```
$ git clone git@github.com:satorici/playbooks.git
$ satori-cli run "../playbooks/devops/GitHub.yml"
TBC
```
