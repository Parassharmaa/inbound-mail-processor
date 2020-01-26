import pulumi
import compute

mail_processor = compute.InboundMailProcessor(
    name='test', 
    zone_name='dev.example.in', 
    domain="dev.example.in",
    recipients=['test@dev.example.in'],
    handler='handler.py'
)