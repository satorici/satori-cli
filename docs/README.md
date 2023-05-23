# Intro

Satori is a language and a testing platform. Using our language you can test software and systems to assert their behavior from oneliners to more complex scenarios.

## Language
We use a [language](language.md) that allows you to defines, executions, how their inputs should be and [assert](asserts.md) if their behavior is what you would expect. We store the tests in files called [playbooks](playbooks.md) with different [settings](settings.md) depending on the [execution mode](execution.md): [Run](execution_run.md), [CI](execution_ci.md) and/or [Monitor](execution_monitor.md)

### [Executions](execution.md)

### [Inputs](inputs.md)


### [Asserts](asserts.md)

### [Settings](settings.md)

### [Playbooks](playbooks)

Public, private, imports

## Mode

### [Run](execution_run.md)

TBC

#### Playbook

TBC

#### Bundle

TBC

### [Repo](execution_repo.md)

#### [CI](execution_ci.md)
We have a [Github Application](https://github.com/apps/satorici) to analyze your [repositories](repo.md).
You can automatically scan your latest pushes when connected to the Github CI process. We can also be connected using our CLI tool within your [Github Actions](execution_github_action.md)

#### Scan

TBC

### [Monitor](execution_monitor.md)

You can define a [schedule](settings.md) for your playbook that will run with a certain frequency. You can then [monitor](execution_monitor.md) the behavior of them with a predefined frequency: 5 minutes, weekly, etc.

## UI

We offer multiples interfaces:

### [CLI](ui_cli.md)

TBC


### [Web](ui_web.md)

TBC

### Notifications

We will [notify](notifications.md) you whenever you want. 

### API

Please refer to http://api.satori-ci.com/schema/swagger

## [Reports](reports.md)

We process the [output](output.md) to produce [reports](reports.md) based on the [files](files.md) that were generated. We can let you know about the [deltas](delta.md) between your reports whenever you need to know how the execution time and results are changing.

### Delta

Between consecutive reports you can measure on the time that it took to execute and the test results to understand if bugs were fixed or introduced.

### [Output](output.md)

Get the output of your executions

### [Files](files.md)

Get the files of your executions
