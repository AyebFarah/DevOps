import json
import pulumi
import pulumi_aws as aws

# ---------- PART 1: Web server running Nginx in a Docker container ----------

# Latest Amazon Linux 2023 image
ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[aws.ec2.GetAmiFilterArgs(name="name", values=["al2023-ami-2023.*-x86_64"])],
)

# Firewall: allow incoming HTTP on port 80 from anywhere
web_sg = aws.ec2.SecurityGroup(
    "web-sg",
    description="Allow HTTP",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp", from_port=80, to_port=80, cidr_blocks=["0.0.0.0/0"])],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])],
)

# Script run on first boot: install Docker, start Nginx
user_data = """#!/bin/bash
dnf install -y docker
systemctl enable --now docker
docker run -d --restart always -p 80:80 nginx
"""

server = aws.ec2.Instance(
    "web-server",
    instance_type="t3.micro",
    ami=ami.id,
    vpc_security_group_ids=[web_sg.id],
    user_data=user_data,
    associate_public_ip_address=True,
    tags={"Name": "pulumi-nginx"},
)

# ---------- PART 2: S3 bucket hosting a static website ----------

bucket = aws.s3.BucketV2("static-site", force_destroy=True)  # force_destroy lets destroy empty it

website = aws.s3.BucketWebsiteConfigurationV2(
    "website",
    bucket=bucket.id,
    index_document=aws.s3.BucketWebsiteConfigurationV2IndexDocumentArgs(suffix="index.html"),
)

ownership = aws.s3.BucketOwnershipControls(
    "ownership",
    bucket=bucket.id,
    rule=aws.s3.BucketOwnershipControlsRuleArgs(object_ownership="BucketOwnerPreferred"),
)

# By default S3 blocks public access; we deliberately open it for a public website
public_access = aws.s3.BucketPublicAccessBlock(
    "public-access",
    bucket=bucket.id,
    block_public_acls=False,
    block_public_policy=False,
    ignore_public_acls=False,
    restrict_public_buckets=False,
)

# Policy: anyone may READ objects
policy = aws.s3.BucketPolicy(
    "bucket-policy",
    bucket=bucket.id,
    policy=bucket.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [f"{arn}/*"],
        }],
    })),
    opts=pulumi.ResourceOptions(depends_on=[public_access]),
)

index_page = aws.s3.BucketObject(
    "index.html",
    bucket=bucket.id,
    content="<h1>Hello from my Pulumi static site!</h1>",
    content_type="text/html",
    opts=pulumi.ResourceOptions(depends_on=[policy]),
)

# ---------- Outputs (printed after deployment) ----------
pulumi.export("web_server_url", server.public_ip.apply(lambda ip: f"http://{ip}"))
pulumi.export("static_site_url", website.website_endpoint.apply(lambda e: f"http://{e}"))