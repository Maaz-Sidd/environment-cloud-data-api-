import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta


logger = logging.getLogger()
logger.setLevel(logging.INFO) 

dyn_resource = boto3.resource('dynamodb', region_name='us-east-1')
dyn_client = boto3.client('dynamodb', region_name='us-east-1')


def lambda_handler(event, context):
    create_new_table()
    
    change_provisioned_cap()
    
        
def create_new_table():
    try:
        current = datetime.now()
        current_month = current.month
        current_year = current.year
        
        table_name = f"environment-{current_month}-{current_year}"

        table = dyn_resource.create_table(
            TableName= table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "habitat_id", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "date", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "habitat_id", "AttributeType": "S"},
                {"AttributeName": "date", "AttributeType": "S"},
            ],
            
        )
        table.wait_until_exists()
        logger.info(f"Table {table_name} created successfully.")
    
        
        return {
            'statusCode': 200,
            'body': f"Table {table.name} created successfully."
        }
    except ClientError as e:
        logger.error(
            "Couldn't create table %s. Here's why: %s: %s",
            table_name,
            e.response["Error"]["Code"],
            e.response["Error"]["Message"],
        )
    except Exception as e:
        logger.error(
            "An error occurred: %s",
            str(e),
        )

def change_provisioned_cap():
    try:
        # Update table with new provisioned throughput
        new_rcu = 20
        new_wcu = 1
        
        now = datetime.now()
        
        previous_month = (now.month - 1) if now.month > 1 else 12
        previous_year = now.year if previous_month < 12 else now.year - 1
        
        table_name = f"environment-{previous_month}-{previous_year}"
        
        response = dyn_client.update_table(
            TableName=table_name,
            ProvisionedThroughput={
                'ReadCapacityUnits': new_rcu,
                'WriteCapacityUnits': new_wcu
            }
        )
        print(f"Table {table_name} updated successfully with RCU={new_rcu} and WCU={new_wcu}")
        return True
    except Exception as e:
        print(f"Error updating table {table_name}: {e}")
        return False