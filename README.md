# Install playbooks examples
1. [git clone git@github.com:satorici/playbooks.git]

# Test upload satori-cli
2. Generate a new token on https://www.satori-ci.com/user-settings/
3. git clone git@github.com:satorici/satori-cli.git
4. cd satori-cli/
5. [pip3 install requests]
6. ./satori-cli --run-playbook="../playbooks/devops/GitHub.yml" --set-token="{my_token}"
