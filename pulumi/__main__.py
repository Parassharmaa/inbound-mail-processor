import pulumi
import component

mail_processor = component.InboundMailProcessor(
    name='test', # name of the resource
    handler='handler.py' # lambda function to process inbound email
)