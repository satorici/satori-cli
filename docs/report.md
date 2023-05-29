# Intro

## Reports

The following satori-cli commands will help:

- `satori-cli report`: list all your reports
- `satori-cli report id`: show the report id
- `satori-cli report id stop`: stop the execution of the report id
- `satori-cli report id delete`: stop the execution of the report id

The filter parameter allows you to specify:

- **repo**: which repo is associated (ie, satorici/satori-cli)
- **playbook**: the playbook URLs (ie, satori*//code/semgrep.yml)
- **status**: what is the status (Pending, Running, Completed or Undefined)
- **result**: was the report a pass or a fail? (Pass or Fail)
- **from**: limit to commits from this specific date (format: year-month-day, ie: 2020-12-30)
- **to**: limit to commits until this specific date (format: year-month-day, ie: 2023-01-10)
- **satori_error**: an error occurred during report generation? (True or False)
- **email**: filter by pusher email
- **user**: filter by satori user name
- **type**: the report execution type (monitor, github or playbook_bundle)

Then this parameters can be used to check specific reports that you are looking for:

- Example: _"I want to see all failed reports for the repositories of the account satorici"_

  `satori-cli report --filter="repo=satorici/*,result=fail"`

- Example: _"I want to see a list of reports related to the playbook trufflehog"_

  `satori-cli report --filter="playbook=satori://code/trufflehog"`
