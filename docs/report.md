#Intro
## Reports

The following satori-cli commands will help:

- `satori-cli report`: list all your reports
- `satori-cli report id`: show the report id
- `satori-cli report id stop`: stop the execution of the report id
- `satori-cli report id delete`: stop the execution of the report id

The filter parameter allows you to specify:
- repo: which repo is associated (ie, satorici/satori-cli)
- playbook: the playbook URLs (ie, satori://code/semgrep.yml)
- status: what is the status (ie, completed or running)
- result: was the report a pass or a fail?
- **Marian TBC**: **Fernando TBC** 

Then this parameters can be used to check specific reports that you are looking for:

- Example: _"I want to see all failed reports for the repositories of the account satorici"_

  `satori-cli report --filter="repo=satorici/*,result=fail"`

- Example: _"I want to see a list of reports related to the playbook trufflehog"_

  `satori-cli report --filter="playbook=satori://code/trufflehog"`
