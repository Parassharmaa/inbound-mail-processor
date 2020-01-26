import os
import pulumi
from pulumi_aws import route53, ses, lambda_, config, sns, iam
from utils import format_resource_name, filebase64sha256
from pathlib import Path
from zipfile import ZipFile

pulumi_config = pulumi.Config()

class InboundMailProcessor(pulumi.ComponentResource):
    """
    An InboundMailProcessor creates an email address for which emails get
    automatically processed by a Lambda.

    If a handler is specificied, custom logic can be added such as sending a
    POST request to a form after clicking the validation link in the email.

    Default behavior is to simply click the first link it finds.
    """
    def __init__(self,
                 name,
                 zone_name,
                 domain,
                 recipients,
                 handler="handler.py",
                 opts=None):
        """
        :name: name of the resource
        :zone_name: name of the route53 zone
        :domain: domain name for email
        :recipients: list of emails
        :handler: path to the Lambda handler module, if any
        """
        super().__init__('nuage:aws:InboundMailProcessor', name, None, opts)
        # Get or create package directory
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
        handler_path = package_path / handler
        handler_path_str = str(handler_path.resolve())

        # Create zip file
        with ZipFile(output_str, 'w') as z:
            z.write(filename=handler_path_str, arcname='handler.py')
        archive = pulumi.FileArchive(path=output_str)

        # Get Route53 Zone
        zone = route53.get_zone(name=zone_name)

        # Add SES SMTP mx record for inbound emails
        mx_record = route53.Record(
            resource_name=format_resource_name("mx-record"),
            name=domain,
            records=[f'10 inbound-smtp.{config.region}.amazonaws.com'],
            ttl=300,
            type="MX",
            zone_id=zone.zone_id)

        # Domain verification - Add TXT record to route53 zone to verify domain
        ses_domain = ses.DomainIdentity(
            resource_name=format_resource_name("domain-id"), domain=domain)

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

        # Create sns topic to push mail content from SES
        sns_imp_topic = sns.Topic(resource_name=format_resource_name("topic"))

        # Lambda IAM role and policy
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

        # Create Mail processing lambda function & invoke permission
        mail_processor_function = lambda_.Function(
            resource_name=format_resource_name("function"),
            role=lambda_role.arn,
            runtime="python3.7",
            handler="handler.lambda_handler",
            code=archive)

        # Add Lambda invoke permission for SNS
        allow_sns = lambda_.Permission(
            resource_name=format_resource_name("permissions"),
            action="lambda:InvokeFunction",
            function=mail_processor_function.name,
            principal="sns.amazonaws.com",
            source_arn=sns_imp_topic.arn)

        # Add topic subscription to lambda function from sns
        sns_imp_lambda_sub = sns.TopicSubscription(
            resource_name=format_resource_name("subscription"),
            endpoint=mail_processor_function.arn,
            protocol='lambda',
            topic=sns_imp_topic.arn)

        # Add SES receipt rule set
        ses_rule_set = ses.ReceiptRuleSet(
            resource_name=format_resource_name("rule-set"),
            rule_set_name='rule-set')

        # Make above reciept rule set active
        ses_active_rule_set = ses.ActiveReceiptRuleSet(
            resource_name=format_resource_name("active-rule-set"),
            rule_set_name='rule-set',
            opts=pulumi.ResourceOptions(depends_on=[ses_rule_set]))

        # Add reciept rule to the above set
        ses_confirmation_reciept_rule = ses.ReceiptRule(
            resource_name=format_resource_name("rule"),
            enabled=True,
            rule_set_name=ses_active_rule_set.rule_set_name,
            recipients=recipients,
            sns_actions=[{
                'topic_arn': sns_imp_topic.arn,
                'position': 0
            }])
        self.register_outputs({
            'function_name': mail_processor_function.name,
            'sns_topic': sns_imp_topic.name,
            'reciept_rule_set': ses_active_rule_set
        })
