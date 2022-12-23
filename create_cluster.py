"""
Run this script to automatically spin up a Redshift cluster on AWS. 
A config file `dwh_035_access.cfg` is automatically generated to be used by `create_tables.py`.

Background: this script is created based on the MVP notebook: create_redshift_cluster_take_02.ipynb

What this script does:

- Load AWS Secret Parameters from: `dwh_010_secret.cfg`
- Load Redshift Dataware config Parameters from: `dwh_020_build.cfg`
- Create clients for IAM, EC2, S3 and Redshift
- Create an IAM Role that makes Redshift able to access S3 bucket (S3 Read Only)
- Create Redshift Cluster
- Describe Redshift Cluster and see its status once it is spun up on AWS
- Capture Redshift Cluster Endpoint and Role ARN
- Automatically create the Redshift Cluster access config file `dwh_035_access.cfg`
- Open an incoming TCP port to access the cluster ednpoint

TODO: refactor this script to make it more readable and testable in future!

The overall code concept is inspired by the Udacity Data Engineering Nanodegree course: 
Udacity Lesson 3 Exercise 2 - IaC (infrastructure as Code) - solution

Useful references:

- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/redshift.html
"""

import time
import json
import pandas as pd
import boto3
import configparser
from botocore.exceptions import ClientError



# Load AWS Secret Parameters
print("*******************************************")
print("Load AWS Secret Parameters")

config_secret = configparser.ConfigParser()
config_secret.read_file(open('dwh_010_secret.cfg'))
AWS_KEY = config_secret.get('AWS','ADMIN_KEY')
AWS_SECRET = config_secret.get('AWS','ADMIN_SECRET')

# Load Redshift Datawarehouse Parameters
print("*******************************************")
print("Load Redshift Datawarehouse Parameters")

config_dwh = configparser.ConfigParser()
config_dwh.read_file(open('dwh_020_build.cfg'))

AWS_REGION = config_dwh.get("AWS","REGION")

DWH_CLUSTER_TYPE = config_dwh.get("DWH","DWH_CLUSTER_TYPE")

if (DWH_CLUSTER_TYPE == 'multi-node'):
    DWH_NUM_NODES = config_dwh.get("DWH","DWH_NUM_NODES")
    assert DWH_NUM_NODES > 1
elif (DWH_CLUSTER_TYPE == 'single-node'):
    DWH_NUM_NODES = 1
    
DWH_NODE_TYPE          = config_dwh.get("DWH","DWH_NODE_TYPE")
DWH_CLUSTER_IDENTIFIER = config_dwh.get("DWH","DWH_CLUSTER_IDENTIFIER")
DWH_DB                 = config_dwh.get("DWH","DWH_DB")
DWH_DB_USER            = config_dwh.get("DWH","DWH_DB_USER")
DWH_DB_PASSWORD        = config_dwh.get("DWH","DWH_DB_PASSWORD")
DWH_PORT               = config_dwh.get("DWH","DWH_PORT")
DWH_IAM_ROLE_NAME      = config_dwh.get("DWH", "DWH_IAM_ROLE_NAME")
DWH_IAM_ROLE_POLICY    = config_dwh.get("DWH", "DWH_IAM_ROLE_POLICY")

S3_LOG_DATA            = config_dwh.get("S3", "LOG_DATA")
S3_LOG_JSONPATH        = config_dwh.get("S3", "LOG_JSONPATH")
S3_SONG_DATA           = config_dwh.get("S3", "SONG_DATA")

# Print Redshift Datawarehouse Parameters
print("*******************************************")
print("Print Redshift Datawarehouse Parameters")

print(pd.DataFrame(
    {
        "Param": [
            "AWS_REGION",
            "DWH_CLUSTER_TYPE", "DWH_NUM_NODES", "DWH_NODE_TYPE", "DWH_CLUSTER_IDENTIFIER",
            "DWH_DB", "DWH_DB_USER", "DWH_DB_PASSWORD", "DWH_PORT", "DWH_IAM_ROLE_NAME",
            "DWH_IAM_ROLE_POLICY"
        ],
        "Value": [
            AWS_REGION,
            DWH_CLUSTER_TYPE, DWH_NUM_NODES, DWH_NODE_TYPE, DWH_CLUSTER_IDENTIFIER,
            DWH_DB, DWH_DB_USER, DWH_DB_PASSWORD, DWH_PORT, DWH_IAM_ROLE_NAME,
            DWH_IAM_ROLE_POLICY
        ]
    }
))


# Create clients for IAM, EC2, S3 and Redshift
print("*******************************************")
print("Create clients for IAM, EC2, S3 and Redshift")

ec2 = boto3.resource(
    'ec2',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)

s3 = boto3.resource(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)

iam = boto3.client(
    'iam',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)

redshift = boto3.client(
    'redshift',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)


# Create an IAM Role that makes Redshift able to access S3 bucket (S3 Read Only)
print("*******************************************")
print("Create an IAM Role that makes Redshift able to access S3 bucket (S3 Read Only)")

# 1.1 Create the role, 
try:
    print("1.1 Creating a new IAM Role") 
    dwhRole = iam.create_role(
        Path='/',
        RoleName=DWH_IAM_ROLE_NAME,
        Description = "Allows Redshift clusters to call AWS services on your behalf.",
        AssumeRolePolicyDocument=json.dumps(
            {
                'Statement': [
                    {
                        'Action': 'sts:AssumeRole',
                        'Effect': 'Allow',
                        'Principal': {'Service': 'redshift.amazonaws.com'}
                    }
                ],
                'Version': '2012-10-17'
            }
        )
    )

except Exception as e:
    print(e)
    

# 1.2 Attach Policy to the role

print("1.2 Attaching Policy")

iam.attach_role_policy(
    RoleName=DWH_IAM_ROLE_NAME,
    PolicyArn=DWH_IAM_ROLE_POLICY
)['ResponseMetadata']['HTTPStatusCode']


# 1.3 Get the IAM role ARN

print("1.3 Get the IAM role ARN")
roleArn = iam.get_role(RoleName=DWH_IAM_ROLE_NAME)['Role']['Arn']

print(roleArn)


# Create the Redshift Cluster

redshift_cluster_config = {
    # Hardware
    "ClusterType": DWH_CLUSTER_TYPE,
    "NodeType": DWH_NODE_TYPE,
    
    #Identifiers & Credentials
    "DBName": DWH_DB,
    "ClusterIdentifier": DWH_CLUSTER_IDENTIFIER,
    "MasterUsername": DWH_DB_USER,
    "MasterUserPassword": DWH_DB_PASSWORD,
    
    #Roles (for s3 access)
    "IamRoles": [roleArn]
}

if DWH_CLUSTER_TYPE == 'multi-node':
    redshift_cluster_config["NumberOfNodes"] = int(DWH_NUM_NODES)
    
try:
    response = redshift.create_cluster(**redshift_cluster_config)
except Exception as e:
    print(e)
    

# Describe Cluster and see its status
print("*******************************************")
print("Describe Cluster and see its status")

def prettyRedshiftProps(props):
    """Pretty print the Redhift describe_clusters dictionary."""
    pd.set_option('display.max_colwidth', -1)
    keysToShow = ["ClusterIdentifier", "NodeType", "ClusterStatus", "MasterUsername", "DBName", "Endpoint", "NumberOfNodes", 'VpcId']
    x = [(k, v) for k,v in props.items() if k in keysToShow]
    return pd.DataFrame(data=x, columns=["Key", "Value"])


myClusterProps = redshift.describe_clusters(ClusterIdentifier=DWH_CLUSTER_IDENTIFIER)['Clusters'][0]
print(prettyRedshiftProps(myClusterProps))


# Retry every 5 seconds... is the cluster now available? (may take up to a minute ish for cluster to spin up)
print("*******************************************")
print("Retry every 5 seconds... is the cluster now available? (may take up to a minute ish for cluster to spin up)")


cluster_status = 'creating'
print("wait until cluster status becomes available.. (retry every 5 seconds)")
while (cluster_status != 'available'):
    print('|', end='')
    time.sleep(5)
    cluster_status = redshift.describe_clusters(ClusterIdentifier=DWH_CLUSTER_IDENTIFIER)['Clusters'][0].get("ClusterStatus")

print('\n')
    
    
# Cluster should now be available at this point
myClusterProps = redshift.describe_clusters(ClusterIdentifier=DWH_CLUSTER_IDENTIFIER)['Clusters'][0]
print(prettyRedshiftProps(myClusterProps))


# Capture Redshift Cluster Endpoint and Role ARN
DWH_ENDPOINT = myClusterProps['Endpoint']['Address']
DWH_ROLE_ARN = myClusterProps['IamRoles'][0]['IamRoleArn']
print("DWH_ENDPOINT :: ", DWH_ENDPOINT)
print("DWH_ROLE_ARN :: ", DWH_ROLE_ARN)


# Automatically create the Redshift Cluster access config file
print("*******************************************")
print(" Automatically create the Redshift Cluster access config file")

config_access_035 = (
f"""
[AWS]
REGION={AWS_REGION}

[CLUSTER]
HOST={DWH_ENDPOINT}
DB_NAME={DWH_DB}
DB_USER={DWH_DB_USER}
DB_PASSWORD={DWH_DB_PASSWORD}
DB_PORT={DWH_PORT}

[IAM_ROLE]
ARN={DWH_ROLE_ARN}
NAME={DWH_IAM_ROLE_NAME}
POLICY={DWH_IAM_ROLE_POLICY}

[S3]
LOG_DATA={S3_LOG_DATA}
LOG_JSONPATH={S3_LOG_JSONPATH}
SONG_DATA={S3_SONG_DATA}
""")


print(config_access_035)

with open('dwh_035_access.cfg', 'w') as f:
    f.write(config_access_035)


# Open an incoming TCP port to access the cluster ednpoint
print("*******************************************")
print("Open an incoming TCP port to access the cluster ednpoint")

try:
    vpc = ec2.Vpc(id=myClusterProps['VpcId'])
    defaultSg = list(vpc.security_groups.all())[0]
    print(defaultSg)
    defaultSg.authorize_ingress(
        GroupName=defaultSg.group_name,
        CidrIp='0.0.0.0/0',
        IpProtocol='TCP',
        FromPort=int(DWH_PORT),
        ToPort=int(DWH_PORT)
    )
except Exception as e:
    print(e)


# Done!
print("*******************************************")
print("Congrats! Redshift cluster is now available for use.")
print("New config file created: dwh_035_access.cgf")
print("You may now run create_tables.py")