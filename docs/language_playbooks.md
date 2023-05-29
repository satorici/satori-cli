# [Intro](README.md)
## [Language](language.md)
### Playbooks

Playbooks can have undefined inputs that will be considered to be parameters to be supplied for them to be executed. Consider the following example:

echo.yml:
```yml
test:
    - [ echo $(VAR) ]
```

The previous playbook would be executed on the following way by Satori CLI:

```sh
$ satori-cli run echo.yml --data="{'VAR':'Hello World'}"
```

#### Public Playbooks

You can check the list of public playbooks with the command:

`satori-cli playbook --public`

Here is a sample output:

-------------------------------------------------------------------------------------------------------------------------------------------
| Filename                         | Name                                                                            |         Parameters |
|----------------------------------|---------------------------------------------------------------------------------|--------------------|
| satori://attack/bombardment.yml  | Run siege with an ever-increasing number of users                               |                URL |
| satori://attack/siege.yml        | Siege - Load testing web servers                                                |                URL |
| satori://attack/slowhttptest.yml | SlowHTTPTest - Common low-bandwidth application layer Denial of Service attacks |                URL |
| satori://aws/scoutsuite.yml      | Scout suite for AWS                                                             | KEY_SECRET, KEY_ID |
| satori://code/cloc.yml           | Count the lines of code                                                         |                    |
| ...                              |                                                                                 |                   ||

If you notice, some playbooks have predefined parameters that will be expected to be executed. Parameters try to be self descriptive, so a URL is expected whenever the parameter is called `URL`.

#### Private Playbooks

Your playbooks are private by default. The following command prints the playbooks executed by run, ci and/or monitor:
`satori-cli playbook`


#### Examples

Playbooks can be imported by other playbooks. Local files or publicly available playbooks from Satori can be imported by other playbooks. They are executed on the order that they were introduced on the YAML file.

##### Import of Local Playbooks

The reserved word `import` can be used in playbooks to import local and public playbooks:

PositiveHelloWorldTest.yml
```yml
PositiveHelloWorldTest:
    assertStdoutEquals: "Hello World"
    run:
    - [ echo Hello World ]
```

NegativeHelloWorldTest.yml
```yml
NegativeHelloWorldTest:
    assertStdoutNotEquals: "Hello World"
    input:
      - "Hello World"
      mutate_qty: 1
    run:
    - [ echo $(input) ]
```

Then you can execute:

HelloWorldTest.yml
```yml
import:
    - "PositiveHelloWorldTest.yml"
    - "NegativeHelloWorldTest.yml"
```

`satori-cli run HelloWorldTest.yml`

##### Import of Public Playbooks

Include on the root folder of your GitHub repository a file named `.satori.yml` with the following line to automatically verify for secrets in the code:
```yml
import:
    - "satori://code/trufflehog.yml"
```

##### Run Local Playbook

HelloWorld.yml:
```
test:
    assertStdoutEqual: "Hello World"
    run:
    - [ echo Hello World ]
```

`satori-cli run HelloWorld.yml --report"`

##### Run Public Playbook

`satori-cli repo satorici/satori-cli run --playbook "satori://code/trufflehog.yml" --report`