# [Intro](README.md)
## [Language](language.md)
### Settings

#### Name, Description, Mitigation

```yml
settings:
    name: This is a short description
    description: This is a long description that details the functionality of the playbook
    mitigation: This is a help message associated on how a test would be fixed in case of an error
```

#### Schedule

If you define a cron schedule for a playbook, it will execute with the defined frequency:

```yml
settings:
    schedule: 5 8 * * 0 # Run this playbook every Sunday at 8:05am
```

#### Log

Choose between the different possibilities on how you want to be notified once the analysis is complete. You can choose to be notified:

- log: Always be notified
- logOnFail: Be notified in case the result is Fail
- logOnPass: Be notified in case the result is Pass

They can be used with the following parameters:
- slack: Define on the Web UI the channel
- email: This will send you an email with the notification
- telegram: Define on the Web UI your phone number
- discord: Define on the Web UI the channel
- issue: This will create a Github Issue on the repository

Example, be notified on Slack in case the result is a Fail:
```yml
settings:
    logOnFail: slack
```

#### Timeout

You can define a maximum amount of time that the execution will run for:

```yml
settings:
    timeout: 3600 # the default value is 3600 seconds
```

#### Example:

Run an nmap playbook every 5 minutes and get notified in case the results change:

```yml
settings:
    name: "Nmap: did any service changed?"
    mitigation: Verify the latest Pass execution to confirm what services changed their status
    cron: "*/10 * * * *"
    logOnFail:slack
install:
    assertReturnCode:0
    nmap:
    - [ apt install -y nmap]
    ips:
    - [ "echo -e \"hostname1\nhostname2\" > domains"]
nmap:
    assertReturnCode:0 
    run:
    - [ "nmap -n -iL domains -Pn -p21,22,80,443,3000,3306,5432 -sT -oG nmap" ]
    services: 
        assertStdoutSHA256:
        - "e3b0c44298fc1c149afbf4c7996fb92427ae41e4649b934ca495991b7852b855"
        running:
        - [ "grep Ports nmap | sort -u" ]
```