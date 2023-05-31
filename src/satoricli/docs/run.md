# [Intro](README.md)
## Run

Satori is an automatic testing platform that can run tests on demand with the `run` command. By default, it works asynchronous by launching the process in background and providing a report ID that can be followed up to get the results of the test. If synchronous execution is required, either because the execution may block future actions or because you want to get the report or the output that will be generated, that can 

--sync: returns a short response
--report: TBC
--output: TBC

There are some general guidances on Run:
- Executions run asynchronous by default or synchronous with the parameter `--report` and `--output`

**Local Playbook**
Run allows you to run Satori Playbooks on demand. Whenever your playbook by itself is enough, you can simply run it with:

```sh
satori-cli run playbook.yml
```

**Local Directory with Playbook**
In case you are working on a directory with source code, where you are interested in understanding how the files behave with the code, you want to save your playbook as `.satori.yml` and then run:

```sh
satori-cli run ./
```

**Public Playbook**
You can run on demand public playbooks. You can see a list of the publicly available playbooks with:

```sh
satori-cli playbook --public
```

And then you can execute them like this:
```sh
satori-cli run --playbook satori://some/playbook.yml
```
