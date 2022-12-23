"""
Run this script to delete Redshift cluster on AWS.

For future: refactor in future!
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

DWH_CLUSTER_TYPE = config_dwh.get("DWH","DWH_CLUSTER_TYPE")

if (DWH_CLUSTER_TYPE == 'multi-node'):
    DWH_NUM_NODES = config_dwh.get("DWH","DWH_NUM_NODES")
    assert DWH_NUM_NODES > 1
elif (DWH_CLUSTER_TYPE == 'single-node'):
    DWH_NUM_NODES = 1

AWS_REGION = config_dwh.get("AWS","REGION")

DWH_NODE_TYPE          = config_dwh.get("DWH","DWH_NODE_TYPE")
DWH_CLUSTER_IDENTIFIER = config_dwh.get("DWH","DWH_CLUSTER_IDENTIFIER")
DWH_DB                 = config_dwh.get("DWH","DWH_DB")
DWH_DB_USER            = config_dwh.get("DWH","DWH_DB_USER")
DWH_DB_PASSWORD        = config_dwh.get("DWH","DWH_DB_PASSWORD")
DWH_PORT               = config_dwh.get("DWH","DWH_PORT")
DWH_IAM_ROLE_NAME      = config_dwh.get("DWH", "DWH_IAM_ROLE_NAME")
DWH_IAM_ROLE_POLICY    = config_dwh.get("DWH", "DWH_IAM_ROLE_POLICY")

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


print("*******************************************")
print(f"Delete Redshift Cluster (instruction sent): {DWH_CLUSTER_IDENTIFIER}")


def prettyRedshiftProps(props):
    """Pretty print the Redhift describe_clusters dictionary."""
    
    pd.set_option('display.max_colwidth', -1)
    keysToShow = ["ClusterIdentifier", "NodeType", "ClusterStatus", "MasterUsername", "DBName", "Endpoint", "NumberOfNodes", 'VpcId']
    x = [(k, v) for k,v in props.items() if k in keysToShow]
    return pd.DataFrame(data=x, columns=["Key", "Value"])


myClusterProps = redshift.describe_clusters(ClusterIdentifier=DWH_CLUSTER_IDENTIFIER)['Clusters'][0]
prettyRedshiftProps(myClusterProps)


#### CAREFUL!!
#-- Uncomment & run to delete the created resources
redshift.delete_cluster( ClusterIdentifier=DWH_CLUSTER_IDENTIFIER,  SkipFinalClusterSnapshot=True)
#### CAREFUL!!


print("*******************************************")
print(f"Delete IAM Role (instruction sent): {DWH_IAM_ROLE_NAME}")


#### CAREFUL!!
#-- Uncomment & run to delete the created resources
iam.detach_role_policy(RoleName=DWH_IAM_ROLE_NAME, PolicyArn=DWH_IAM_ROLE_POLICY)
iam.delete_role(RoleName=DWH_IAM_ROLE_NAME)
#### CAREFUL!!


print("*******************************************")
print(f"Done. May take some time to complete. Monitor via AWS Console ({AWS_REGION} region)")