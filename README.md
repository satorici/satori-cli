# Install satori-cli
1. `git clone git@github.com:satorici/satori-cli.git`
2. `cd satori-cli/`
3. `pip3 install requests` # Optional step, you may have it installed already

# [Get some Satori Playbooks]
4. git clone git@github.com:satorici/playbooks.git

# Use Satori Playbooks with satori-cli
5. Generate a token: https://www.satori-ci.com/user-settings/
6. `python3 satori-cli config token {user_token}` # Set user token
7. `python3 satori-cli run "../playbooks/devops/GitHub.yml"`
8. Open the returned URL to visualize the report
