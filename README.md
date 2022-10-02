# Install satori-cli
1. `git clone git@github.com:satorici/satori-cli.git`
2. `cd satori-cli/`
3. `apt install python3.10` # Optional step
4. `pip3 install -f requirements.txt` # Optional step
5. Register at https://www.satori-ci.com
6. Get a token from https://www.satori-ci.com/user-settings/

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
satori-cli scan GithubAccount/Repository -c 100
```

## Run playbooks

```
$ git clone git@github.com:satorici/playbooks.git
$ python3 satori-cli config default {user_token} # Set user token
$ satori-cli run "../playbooks/devops/GitHub.yml"
```
