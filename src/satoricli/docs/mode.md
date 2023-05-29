# Intro
## Execution Mode

Satori is a testing platform that can run on demand, on CI/CD and scheduled also known as monitoring

### Run

You can run your playbooks on demand with Satori CLI. You can:
- Run a playbook that is not related to a repository: stress testing
- Upload a directory with a playbook to test its content when you are not developing on a repository.

### CI

Whenever you want to test your software automatically, you can attach Satori to the GitHub CI/CD pipeline with:
- [Satori GitHub App](mode_ci_github.md)
- [Satori CLI running on Github Actions](mode_ci_action.md)

You would normally use this to perform static or dynamic testing of your repository code.

### Monitor

Certain tests must be executed with a certain frequency. For example:
- Every 5 minutes when you are testing if your live systems are working as expected
- Daily when you are monitoring the security of an AWS environment
