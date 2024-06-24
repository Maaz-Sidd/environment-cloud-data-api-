import json
import boto3
import logging
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime
from urllib.parse import unquote

# Set up logging for cloudwatch debugging
logger = logging.getLogger()
logger.setLevel(logging.INFO) 



# Initialize the DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def lambda_handler(event, context):

    try:
        current_date = datetime.now()
        
        current_month = current_date.month
        current_year = current_date.year
        
        table_name = f"environment-{current_month}-{current_year}" 
        dynamodb_table = dynamodb.Table(table_name)

        http_method = event.get('httpMethod')
        path = event.get('path')
        query_params = event.get('queryStringParameters', {})

        
        if http_method == 'GET' and path == '/environment_data':
            return get_data(query_params, dynamodb_table)
        elif http_method == 'POST' and path == '/environment_data':
            return post_data(json.loads(event['body']), dynamodb_table)
        else:
            return build_response(400, {'message': 'Unsupported HTTP method or path'})
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return build_response(500, {'message': 'Internal server error'})
        
def post_data(request_body, dynamodb_table):
    try:
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M")
        
        request_body['date'] = current_time
        
        
        dynamodb_table.put_item(Item=request_body)
        body = {
            'Operation': 'POST',
            'Message': 'SUCCESS',
            'Item': request_body
        }
        return build_response(200, body)
    except ClientError as e:
        print('Error:', e)
        return build_response(400, e.response['Error']['Message'])
        
        
def get_data(query_params, dynamodb_table):
    try:
        
        logger.info(f"Scanning DynamoDB table: {query_params}")
        
        if query_params and 'month' in query_params:
            month = query_params['month'].split('-')[0]
            year = query_params['month'].split('-')[1]
            table_name = f"environment-{month}-{year}"
            
            dynamodb_table = dynamodb.Table(table_name)
        
        if query_params and 'habitatid' in query_params:
            habitatid = query_params['habitatid']
            key_condition = boto3.dynamodb.conditions.Key('habitat_id').eq(habitatid)
            
            if 'date' in query_params:
                date = query_params['date']
                key_condition &= boto3.dynamodb.conditions.Key('date').eq(unquote(date))
            
            response = dynamodb_table.query(
                KeyConditionExpression=key_condition
            )
        elif query_params and 'date' in query_params:
            date = query_params['date']
            response = dynamodb_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('date').eq(unquote(date))
            )
            
        else:
            response = dynamodb_table.scan()
            
        if query_params and 'type' in query_params:
            data_type = query_params['type']
            filtered_items = get_type_data(response, data_type)
            return build_response(200, filtered_items)
        
        return build_response(200, response['Items'])
    except ClientError as e:
        logger.error(f"DynamoDB ClientError: {e.response['Error']['Message']}")
        return build_response(400, {'message': e.response['Error']['Message']})
    except Exception as e:
        logger.error(f"Error scanning DynamoDB table: {e}", exc_info=True)
        return build_response(500, {'message': 'Internal server error'})
        
def get_type_data(data, data_type):
    try:
        logger.info(f"Scanning DynamoDB table for temp data: {table_name}")
        
        
        filtered_items = [
            {
                data_type: item[data_type],
                'date': item['date'],
                'habitat_id': item['habitat_id']
            }
            for item in data['Items']
        ]
        
        logger.info(f"Filtered items: {filtered_items}")
        return filtered_items
    except ClientError as e:
        logger.error(f"DynamoDB ClientError: {e.response['Error']['Message']}")
        return build_response(400, {'message': e.response['Error']['Message']})
    except Exception as e:
        logger.error(f"Error scanning DynamoDB table: {e}", exc_info=True)
        return build_response(500, {'message': 'Internal server error'})
        

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Check if it's an int or a float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        # Let the base class default method raise the TypeError
        return super(DecimalEncoder, self).default(obj)

def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }
