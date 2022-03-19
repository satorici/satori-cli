# Install playbooks examples
git clone git@github.com:satorici/playbooks.git

# Test upload satori-cli
git clone git@github.com:satorici/satori-cli.git

Generate a new token on https://www.satori-ci.com/user-settings/

./satori-cli --run-playbook="./playbooks/devops/GitHub.yml" --set-token="{my_token}"
