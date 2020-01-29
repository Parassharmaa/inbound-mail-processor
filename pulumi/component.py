import os
import pulumi
from pulumi import log
from pulumi_aws import route53, ses, lambda_, config, sns, iam
from utils import format_resource_name, filebase64sha256
from pathlib import Path
from zipfile import ZipFile


class InboundMailProcessor(pulumi.ComponentResource):
    """
    An InboundMailProcessor creates an email address for which emails get
    automatically processed by a Lambda.

    If a handler is specificied, custom logic can be added such as sending a
    POST request to a form after clicking the validation link in the email.

    Default behavior is to simply click the first link it finds.
    """
    def __init__(self, name, handler="handler.py", opts=None):
        """
        :name: name of the resource
        :handler: path to the Lambda handler module, if any
        """
        super().__init__('nuage:aws:InboundMailProcessor', name, None, opts)
        self.handler = handler

        # Get or create package directory
        archive_path = self.package_handler()

        pulumi_config = pulumi.Config()

        # dns stack reference
        dns_stack = self.stack_reference(pulumi_config.get('dns_stack'))
        self.domain = dns_stack.require_output('domain_name')
        self.zone = dns_stack.require_output('zone_name')

        # ses --> sns --> lambda pipeline
        sns_topic = self.add_sns_topic()
        lambda_function = self.add_lambda(archive_path, sns_topic)
        topic_sub = self.add_sns_topic_subscription(sns_topic, lambda_function)
        self.email_id = self.add_ses(sns_topic)

        self.register_outputs({'email_id': self.email_id})

    def package_handler(self):
        """
        Zip lambda function handler
        """
        package_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        package_path = Path(package_dir)
        if not package_path.exists():
            os.makedirs(package_path)

        # Define output path
        output_fname = 'lambda.zip'
        output_path = package_path / output_fname
        output_str = str(output_path.resolve())

        # Get handler path
        handler_path = package_path / self.handler
        handler_path_str = str(handler_path.resolve())

        # Create zip file
        with ZipFile(output_str, 'w') as z:
            z.write(filename=handler_path_str, arcname='handler.py')
        return output_str

    def stack_reference(self, stack_name: str):
        stack = pulumi.StackReference(stack_name)
        return stack

    def add_sns_topic(self):
        """
        Create sns topic to push mail content from SES
        """
        sns_imp_topic = sns.Topic(resource_name=format_resource_name("topic"))
        return sns_imp_topic

    def add_lambda(self, archive_path: str, sns_topic: sns.Topic):
        """
        Create lambda function with sns invoke permission
        """
        lambda_role = iam.Role(
            resource_name=format_resource_name("lambda-role"),
            assume_role_policy="""{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Effect": "Allow",
                        "Sid": ""
                    }
                ]
            }""")

        lambda_role_policy = iam.RolePolicy(
            resource_name=format_resource_name("lambda-policy"),
            role=lambda_role.id,
            policy="""{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }]
            }""")

        mail_processor_function = lambda_.Function(
            resource_name=format_resource_name("function"),
            role=lambda_role.arn,
            runtime="python3.7",
            handler="handler.lambda_handler",
            code=archive_path,
            source_code_hash=filebase64sha256(archive_path))
        allow_sns = lambda_.Permission(
            resource_name=format_resource_name("permissions"),
            action="lambda:InvokeFunction",
            function=mail_processor_function.name,
            principal="sns.amazonaws.com",
            source_arn=sns_topic.arn)
        return mail_processor_function

    def add_sns_topic_subscription(self, sns_topic: sns.Topic,
                                   lambda_fn: lambda_.Function):
        """
        Creates sns topic subscription to lambda function
        """
        sns_imp_lambda_sub = sns.TopicSubscription(
            resource_name=format_resource_name("subscription"),
            endpoint=lambda_fn.arn,
            protocol='lambda',
            topic=sns_topic.arn)
        return sns_imp_lambda_sub

    def add_ses(self, sns_topic: sns.Topic):
        """
        Creates ses receipt rule set and receipt rule
        """
        rule_set_name = f'{pulumi.get_stack()}-imp-set'

        email_id = pulumi.output.Output.concat('inbound-mail@', self.domain)

        ses_rule_set = ses.ReceiptRuleSet(
            resource_name=format_resource_name("rule-set"),
            rule_set_name=rule_set_name)

        # Make above receipt rule set active
        ses_active_rule_set = ses.ActiveReceiptRuleSet(
            resource_name=format_resource_name("active-rule-set"),
            rule_set_name=rule_set_name,
            opts=pulumi.ResourceOptions(depends_on=[ses_rule_set]))

        # Add receipt rule to the above set
        ses_confirmation_receipt_rule = ses.ReceiptRule(
            resource_name=format_resource_name("rule"),
            enabled=True,
            rule_set_name=ses_active_rule_set.rule_set_name,
            recipients=[email_id],
            sns_actions=[{
                'topic_arn': sns_topic.arn,
                'position': 0
            }])
        return email_id


class SesDNSConfig(pulumi.ComponentResource):
    """
    SesDNSConfig adds MX record to route53 and verifies the 
    ownership of configured domain name for SES.
    
    It requires domain_name and zone to be configured in the stack configuration.
    """
    def __init__(self, name, opts=None):
        """
        :name: name of the resource
        """
        super().__init__('nuage:aws:SesDNSConfig', name, None, opts)
        pulumi_config = pulumi.Config()
        self.zone_name = pulumi_config.require('zone_name')
        self.domain_name = pulumi_config.require('domain_name')
        zone = self.get_hosted_zone()
        mx_record = self.add_mx_record(zone)
        domain_identity = self.verify_domain(zone)

        self.register_outputs({
            'domain_name': self.domain_name,
            'zone_name': self.zone_name,
            'zone_id': zone.zone_id
        })

    def get_hosted_zone(self):
        """
        Get Route53 Hosted Zone
        """
        zone = route53.get_zone(name=self.zone_name)
        return zone

    def add_mx_record(self, zone: route53.Zone):
        """
        Adds MX record to route 53 zone for inbound emails
        """
        mx_record = route53.Record(
            resource_name=format_resource_name("mx-record"),
            name=self.domain_name,
            records=[f'10 inbound-smtp.{config.region}.amazonaws.com'],
            ttl=300,
            type="MX",
            zone_id=zone.zone_id)
        return mx_record

    def verify_domain(self, zone: route53.Zone):
        """
        Verifies the domain nam with SES
        """

        # Add TXT record to route53 zone to verify domain
        ses_domain = ses.DomainIdentity(
            resource_name=format_resource_name("domain-id"),
            domain=self.domain_name)

        ses_verification_record = route53.Record(
            resource_name=format_resource_name("verification-record"),
            name=pulumi.Output.concat('_amazonses.', ses_domain.id),
            records=[ses_domain.verification_token],
            ttl=600,
            type="TXT",
            zone_id=zone.zone_id)

        ses_domain_verification = ses.DomainIdentityVerification(
            resource_name=format_resource_name("domain-verification"),
            domain=ses_domain.id,
            opts=pulumi.ResourceOptions(depends_on=[ses_verification_record]))
        return ses_domain