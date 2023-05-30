# [Intro](README.md)
## CI

Each time you push code to your repository, there's a risk that it could affect the security of your project. Furthermore, should your data ever be compromised, it's crucial to minimize the exposure of sensitive information. Two primary areas of concern are:
- Secrets on your code
- Vulnerable code from yourself or third parties

With Satori CI Github App you can automatically test your GitHub repositories:

1. Go to https://github.com/apps/satorici
2. Click on Install
3. Select the repositories where you will be installing it or select all repositories

Then, you want to define a playbook named .satori.yml with the tests that you want to execute. For example, you can choose the most popular tools in the market for:
- search for secrets on your code: [Trufflehog](https://github.com/trufflesecurity/trufflehog)
- perform a static source code analysis: [Semgrep](https://github.com/returntocorp/semgrep)

And probably you may want to run some basic end to end test to confirm that your app is working as expected:

```yml
settings:
  name: CI Test for my Repo
  description: Test for secrets on the code, perform a static source code audit with semgrep and run the project asserting the expected output
  onLogFail: slack-monitor # Send a message to the monitor channel on Slack if the test Fails
# Importing public playbooks
import:
  - "satori://search/trufflehog.yml"
  - "satori://code/semgrep.yml"
# Install required software
install:
  assertReturnCode: 0
  - [ make ]
# System testing
execute:
  assertStdoutContains: "An expected output"
  - [ ./your_project ]
```

If you have any questions or doubts, we are happy to [support](mailto:support@satori-ci.com) you