import pulumi
import component

stack = pulumi.get_stack()

if stack == "core":
    dns_config = component.SesDNSConfig('inbound-mail-dns-test')
    pulumi.export('domain_name', dns_config.domain_name)
    pulumi.export('zone_name', dns_config.zone_name)

else:
    mail_processor = component.InboundMailProcessor(
        name='inbound-mail-processor-test', # name of the resource
        handler='handler.py' # lambda function to process inbound email
    )
    pulumi.export('email_id', mail_processor.email_id)