# Install playbooks examples
1. [git clone git@github.com:satorici/playbooks.git]

# Test upload satori-cli
1. Generate a new token on https://www.satori-ci.com/user-settings/
1. git clone git@github.com:satorici/satori-cli.git
2. cd satori-cli/
3. [pip3 install requests]
4. ./satori-cli --run-playbook="./playbooks/devops/GitHub.yml" --set-token="{my_token}"
