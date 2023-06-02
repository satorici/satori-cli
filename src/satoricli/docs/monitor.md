# [Intro](README.md)
## Monitor

Monitors are playbooks that contain either a `cron` or a `rate` setting in the `settings` section. They will be executed to return the number of fails that were found. They are specially useful to assert that the behavior of live systems is working as expected, when running a playbook that will test them with a certain frequency.

### Cron

Consider the following example playbook that runs nmap every 10 minutes to identify any services that may have changed their port status, and you have a SHA256 hash on the initial valid state:

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

To install this playbook, you just need to run it:

```sh
$ satori-cli run nmap-cron.yml 
```

### Rate

Another terminology that may be easier than `cron` is the `rate` setting. You can define a time lapse such as `30 minutes` or 

**Rate expression examples**:

|Frequency             | Expression       |
|------------------|------------------|
| Every 10 minutes | rate: 10 minutes |
| Every hour       | rate: 1 hour     |
| Every seven days | rate: 7 days     |

For example, the beginning of the previous playbook could have been written with the `rate` setting instead of `cron` like this:

```yml
settings:
    name: "Nmap: did any service changed?"
    rate: 10 minutes
    ...
```

Again, to install this playbook, you just need to run it:

```sh
$ satori-cli run nmap-rate.yml 
```

### List your monitors

Once you have added a monitor, you can list them with the `monitor` command like this:

```sh
$ satori-cli monitor
```

**Stop Monitor**
Now, besides listing your monitors, you may want to stop them. - 

```sh
$ satori-cli monitor ID stop`: disable the monitor id

**Start Monitor**

You can start again your monitors when they are stopped by doing:

```sh
$ satori-cli monitor ID run
```

**Delete Monitor**

Delete a monitor id that is on a stopped state:
```sh
$ satori-cli monitor id delete
```

If you need any help, please reach out to us on [Discord](https://discord.gg/F6Uzz7fc2s) or via [Email](mailto:support@satori-ci.com)
