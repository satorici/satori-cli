# Intro

Satori is an automated testing platform to assert the behavior of command executions. You can test software and systems using simple oneliners of our Playbook marketplace.

## [Install](install.md)

We test synchronously or asynchronously on multiple ways:
- With our [Github Application](https://github.com/apps/satorici) to analyze your [repositories](repo.md).
- With our [CLI tool](https://github.com/satorici/satori-cli), which can be installed with `pip install satori-ci`
- With our [Website](https://www.satori-ci.com)
- Within a [GitHub action](action.md) using Satori CLI
- Or on demand with [Satori CLI Run](run.md)

## [Language](language.md)

Using our YAML [language](language.md) that allows you to define [executions](language_execution.md), how their [inputs](language_inputs.md) should be and [assert](language_asserts.md) if their behavior is what you would expect. Tests are encapsulated within files called [playbooks](language_playbooks.md) with different [settings](language_settings.md) depending on the [execution mode](execution.md): [Run](execution_run.md), [CI](execution_ci.md) and/or [Monitor](execution_monitor.md)

All our tests are stored on what we called playbooks. You can check our online playbooks [Github repository](https://github.com/satorici/playbooks/) for our public marketplace.

## [Repo](repo.md)

We provide a comprehensive approach to test code repositories on Github, whether you have your repositories attached to our CI process or not. You can perform tests from the command line in one or all your repositories to assert that they are how you expect (ie, without passwords stored, that are being built appropriately, with secure coding standards, etc). You can visualize the results using our [Web](https://www.satori-ci.com) or with our CLI (`satori-cli repo`) 

## [Monitor](monitor.md)

It is important to note that you can define a `cron` or a `rate` to your playbooks. The frequency may be important for different types of tests. Then the results can be later checked using our [Web](https://www.satori-ci.com), CLI (`satori-cli monitor`) or [Grafana](TBC)

## [Notifications](notifications.md)

We will notify you when you want, the way that you prefer. We support a variety of different ways of communicating results:
- Slack
- Discord
- Email
- Telegram
- Github Issues

## [Reports](reports.md)

We process the [output](output.md) to produce [reports](reports.md) based on the [files](files.md) that were generated. We can let you know about the [deltas](delta.md) between your reports whenever you need to know how the execution time and results are changing.

