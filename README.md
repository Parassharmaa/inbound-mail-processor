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
__Output__
```
Updating (core):


     Type                                   Name                                             Status      
 +   pulumi:pulumi:Stack                    inbound-mail-processor-core                      created     
 +   ├─ nuage:aws:SesDNSConfig              inbound-mail-dns-test                            created     
 +   ├─ aws:ses:DomainIdentity              inbound-mail-processor-core-domain-id            created     
 +   ├─ aws:route53:Record                  inbound-mail-processor-core-mx-record            created     
 +   ├─ aws:route53:Record                  inbound-mail-processor-core-verification-record  created     
 +   └─ aws:ses:DomainIdentityVerification  inbound-mail-processor-core-domain-verification  created     
 
Resources:
    + 6 created                                                                                    
Outputs:
  + domain_name: "dev.kidaura.in"
  + zone_name  : "dev.kidaura.in"

Resources:
    6 unchanged

Duration: 11s
```

4. Configure and deploy [dev | prod] stack
```
$ pulumi stack select dev
$ pulumi config set aws:region <region>
$ pulumi config set dns_stack <organisation>/<project>/core

$ pulumi up
```

Output:

```
Updating (dev):                        
     Type                               Name                                        Status                                                            +   pulumi:pulumi:Stack                inbound-mail-processor-dev                  created                                                           +   ├─ nuage:aws:InboundMailProcessor  inbound-mail-processor-test                 created                                                           +   ├─ aws:iam:Role                    inbound-mail-processor-dev-lambda-role      created                                                           +   ├─ aws:sns:Topic                   inbound-mail-processor-dev-topic            created                                                           +   ├─ aws:ses:ReceiptRuleSet          inbound-mail-processor-dev-rule-set         created                                                           +   ├─ aws:iam:RolePolicy              inbound-mail-processor-dev-lambda-policy    created                                                           +   ├─ aws:lambda:Function             inbound-mail-processor-dev-function         created                                                           +   ├─ aws:ses:ActiveReceiptRuleSet    inbound-mail-processor-dev-active-rule-set  created                                                           +   ├─ aws:ses:ReceiptRule             inbound-mail-processor-dev-rule             created                                                           +   ├─ aws:sns:TopicSubscription       inbound-mail-processor-dev-subscription     created                                                           +   └─ aws:lambda:Permission           inbound-mail-processor-dev-permissions      created                                                                                                                                                                                           Outputs:                                                                                                                                                 email_id: "inbound-mail@example.in"                                                                                                                                                                                                                                                               Resources:                                                                                                                                               + 11 created                                                                                                                                                                                                                                                                                          Duration: 36s     
```

## Clean up

Destroy all the stack i.e: core, dev, prod.

```
$ pulumi destroy
$ pulumi stack rm
```
