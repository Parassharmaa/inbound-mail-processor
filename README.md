[![Deploy](https://get.pulumi.com/new/button.svg)](https://app.pulumi.com/new)

# Overview

Creates an email address for which emails get automatically processed by a Lambda.

Route53 & domain verification is handled in *core* stack, and contains common configuration.


## Getting started

1. Create a Python virtualenv, activate it, and install dependencies:

```
$ virtualenv -p python3 venv
$ virtualenv -p python3 venv
$ source venv/bin/activate
$ pip3 install -r requirements.txt
```
2. Create the required stacks

```
$ pulumi stack init core
$ pulumi stack init dev
```

3. Configure & Deploy core stack

```
$ pulum stack select core
$ pulumi config set aws:region <region>
$ pulumi config set zone_name <example.com>
$ pulumi config set domain_name <example.com>

$ pulumi up
```

4. Configure and deploy [dev | prod] stack
```
$ pulumi stack select dev
$ pulumi config set aws:region <region>
$ pulumi config set dns_stack <organisation>/<project>/core

$ pulumi up
```


## Clean up

Destroy all the stack i.e: core, dev, prod.

```
$ pulumi destroy
$ pulumi stack rm
```
