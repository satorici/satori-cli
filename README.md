# Install satori-cli
```
git clone git@github.com:satorici/satori-cli.git
cd satori-cli/`
apt install python3.10` # Optional step
pip3 install -f requirements.txt
```
- Register your account at https://www.satori-ci.com and get a token from https://www.satori-ci.com/user-settings/

# Example executions:

## Get information about your assets
```
$ satori-cli
TBC
```

## Check that your repositories are connected to CI
```
$ satori-cli ci
TBC
```

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
$ python3 satori-cli config default {user_token} # Set user token
$ satori-cli run "../playbooks/devops/GitHub.yml"
TBC
```
