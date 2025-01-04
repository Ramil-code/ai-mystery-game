import os
import json
import logging
import requests
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

# Env variables
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'default-bucket')
DYNAMOTABLE_NAME = os.environ.get('DYNAMOTABLE_NAME', 'default-table')
FOLDER_NAME = os.environ.get('FOLDER_NAME', 'photos/')
API_KEY_PARAM = os.environ.get('API_KEY_PARAM', 'ChatGPT')

# File names
IMAGE_NAME_1 = FOLDER_NAME + '1.png'
IMAGE_NAME_2 = FOLDER_NAME + '2.png'
IMAGE_NAME_3 = FOLDER_NAME + '3.png'
TEMP_IMAGE_NAME = FOLDER_NAME + 'temp.png'

def get_api_key(parameter_name):
    try:
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Error retrieving API key: {e}")
        raise

def get_description(situation_id):
    try:
        table = dynamodb.Table(DYNAMOTABLE_NAME)
        resp = table.query(KeyConditionExpression=Key('Situation_id').eq(situation_id))
        items = resp.get('Items')
        if items:
            return items[0].get('Description')
        return None
    except Exception as e:
        logger.error(f"Error retrieving description: {e}")
        raise

def generate_image(api_key, description):
    api_url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "dall-e-3",
        "prompt": description,
        "n": 1,
        "quality": "standard",
        "size": "1024x1024"
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['data'][0]['url']
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise

def key_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise

def shift_images():
    # Shift 2.png -> 3.png (если 2.png существует)
    if key_exists(BUCKET_NAME, IMAGE_NAME_2):
        s3.copy_object(
            Bucket=BUCKET_NAME,
            CopySource={'Bucket': BUCKET_NAME, 'Key': IMAGE_NAME_2},
            Key=IMAGE_NAME_3
        )
        logger.info(f"Shifted {IMAGE_NAME_2} to {IMAGE_NAME_3}")
    else:
        logger.info(f"{IMAGE_NAME_2} does not exist, skipping 2->3.")
    
    # Shift 1.png -> 2.png (если 1.png существует)
    if key_exists(BUCKET_NAME, IMAGE_NAME_1):
        s3.copy_object(
            Bucket=BUCKET_NAME,
            CopySource={'Bucket': BUCKET_NAME, 'Key': IMAGE_NAME_1},
            Key=IMAGE_NAME_2
        )
        logger.info(f"Shifted {IMAGE_NAME_1} to {IMAGE_NAME_2}")
    else:
        logger.info(f"{IMAGE_NAME_1} does not exist, skipping 1->2.")

def process_situation(situation_id):
    logger.info(f"Processing Situation ID: {situation_id}")
    
    # Get description from DynamoDB
    description = get_description(situation_id)
    if not description:
        logger.warning(f"No description found for Situation ID: {situation_id}")
        raise ValueError('No description found')
    
    # Get API key
    api_key = get_api_key(API_KEY_PARAM)
    
    # Generate and store image
    image_url = generate_image(api_key, description)
    logger.info(f"Generated image URL: {image_url}")

    image_data = requests.get(image_url).content
    s3.put_object(Bucket=BUCKET_NAME, Key=TEMP_IMAGE_NAME, Body=image_data)

    # Shift existing images
    shift_images()

    # Move temp => 1.png
    s3.copy_object(
        Bucket=BUCKET_NAME,
        CopySource={'Bucket': BUCKET_NAME, 'Key': TEMP_IMAGE_NAME},
        Key=IMAGE_NAME_1
    )
    s3.delete_object(Bucket=BUCKET_NAME, Key=TEMP_IMAGE_NAME)
    logger.info(f"Image saved successfully as {IMAGE_NAME_1}")

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Handle API Gateway Events
    if 'httpMethod' in event:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
                },
                "body": ""
            }
        
        # Extract situation_id from the body
        situation_id = None
        if 'body' in event:
            try:
                body_data = json.loads(event['body'])
                situation_id = body_data.get('situation_id')
                logger.info(f"Situation ID from API Gateway body: {situation_id}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON in request body")
        
        if not situation_id:
            logger.error("Situation ID not found in the incoming API Gateway data")
            return {
                'statusCode': 400,
                'headers': {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
                },
                'body': json.dumps({'error': 'Situation ID not found'})
            }
        
        try:
            process_situation(situation_id)
        except ValueError as ve:
            return {
                'statusCode': 404,
                'headers': {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
                },
                'body': json.dumps({'error': str(ve)})
            }
        except Exception as e:
            logger.error(f"Exception while processing API Gateway event: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
                },
                'body': json.dumps({'error': str(e)})
            }
        
        return {
            'statusCode': 200,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
            },
            'body': json.dumps({'message': 'New image generated and successfully saved!'})
        }
    
    # Handle DynamoDB Stream Events
    elif 'Records' in event:
        for record in event['Records']:
            event_name = record.get('eventName')
            if event_name in ['MODIFY', 'INSERT']:
                try:
                    situation_id = int(record['dynamodb']['Keys']['Situation_id']['N'])
                    logger.info(f"Situation ID from DynamoDB Stream ({event_name}): {situation_id}")
                    process_situation(situation_id)
                except KeyError:
                    logger.error("Situation_id key not found in the DynamoDB record")
                except ValueError:
                    logger.error("Invalid Situation_id format in the DynamoDB record")
                except Exception as e:
                    logger.error(f"Exception while processing DynamoDB Stream event: {e}")
            else:
                logger.info(f"Ignoring event type: {event_name}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'DynamoDB Stream event processed'})
        }
    
    else:
        logger.error("Unsupported event source")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Unsupported event source'})
        }
