# Intro

Satori is a language and a testing platform. Using our language you can test software and systems to assert their behavior from oneliners to more complex scenarios.

We use a [language](language.md) that allows you to define executions, how their inputs should be and [assert](asserts.md) if their behavior is what you would expect. We store the tests in files called [playbooks](playbooks.md) with different [settings](settings.md) depending on the [execution mode](execution.md): [Run](execution_run.md), [CI](execution_ci.md) and/or [Monitor](execution_monitor.md)

## UI

We offer multiples interfaces:
- [CLI](ui_cli.md)
- [Web](ui_web.md)

## Notifications

We will [notify](notifications.md) you whenever you want. 

## Run

## CI

We have a [Github Application](https://github.com/apps/satorici) to analyze your [repositories](repo.md).

You can automatically scan your latest pushes when connected to the Github CI process. We can also be connected using our CLI tool within your [Github Actions](execution_github_action.md)

## Monitor

You can define a [schedule](settings.md) for your playbook that will run with a certain frequency. You can then [monitor](execution_monitor.md) the behavior of them with a predefined frequency: 5 minutes, weekly, etc. 

## Reports

We process the [output](output.md) to produce [reports](reports.md) based on the [files](files.md) that were generated. We can let you know about the [deltas](delta.md) between your reports whenever you need to know how the execution time and results are changing.
