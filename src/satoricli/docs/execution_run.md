# [Intro](README.md)
## Run

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

## Para Repo:

satori-cli repo https://github.com/satorici/satori-cli --playbook satori://code/trufflehog.yml
satori-cli repo https://github.com/satorici/* --playbook satori://code/trufflehog.yml
satori-cli repo https://github.com/satorici/satori-cli/commit/96a654f9efb8962b20a514eccbe827518ca725b2 (e
