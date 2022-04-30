# Playbooks
1. git clone git@github.com:satorici/playbooks.git

# Playbook in satori-cli
2. Generate a token: https://www.satori-ci.com/user-settings/
3. `git clone git@github.com:satorici/satori-cli.git`
4. `cd satori-cli/`
5. `pip3 install requests` # Optional step, you may have it installed already
6. `python3 satori-cli config token {user_token}` # Set user token
7. `python3 satori-cli run --playbook "../playbooks/devops/GitHub.yml"`
8. Open the URL to check the report
 
