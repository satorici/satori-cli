# Intro
## Execution Mode
### Monitor

Monitors are playbooks that contain a `cron` in `settings`. They will be executed to return the number of fails that were found. Consider for example that you want to monitor all the services of your IP range:

```yml
settings:
    name: "Nmap: did any service changed?"
    cron: "*/10 * * * *"
    logOnFail: slack
install:
    assertReturnCode: 0
    nmap:
    - [ apt install -y nmap ]
nmap:
    assertReturnCode: 0
    run:
    - [ "nmap -n 1.1.1.1/24 -Pn -p 21,22,23,80,443 -sT -oG nmap" ]
services:
    assertStdoutSHA256:
    - "d34db33f93ac1c149afbf4c8996fb924271e41e4649b933ca495991b7852b854"
    running:
    - [ "grep Ports nmap | sort -u" ]
```

The following satori-cli commands will help:

- `satori-cli monitor`: list all your monitors
- `satori-cli monitor id`: show the reports of the monitor id
- `satori-cli monitor id stop`: stop the monitor id
- `satori-cli monitor id delete`:delete the monitor id

If you need any help, please reach out to us on [Discord](https://discord.gg/F6Uzz7fc2s) or via [Email](mailto:support@satori-ci.com)
