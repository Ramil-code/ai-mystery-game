import os
import json
import logging
import boto3
import requests
import random
import re

# Configure
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

# Configuration
CONFIG = {
    'aws_services': os.environ.get('MYSTERIES', "EC2,EBS,S3,RDS,DynamoDB,Lambda,CloudFront,Route53,VPC,IAM,CloudFormation,CloudWatch,SQS,SNS,ECS,Fargate,EKS,Aurora,Redshift,Quicksight,Kinesis,Athena,Glue,Snowball,SageMaker,Rekognition,Comprehend,Lex,Polly,Transcribe,CodeCommit,CodeBuild,CodeDeploy,CodePipeline,CodeStar,Cloud9,X-Ray,Cognito,SecretsManager,Macie,GuardDuty,WAF,Shield,Artifact,ControlTower,Backup,CloudTrail,ServiceCatalog,Outposts,WaveLength,VPN,Inspector,TrustedAdvisor,Marketplace,Amplify,CloudShell,DataSync,SnowFamily").split(","),
    'bucket_name': os.environ.get('BUCKET_NAME', 'default-bucket'),
    'photos_prefix': os.environ.get('FOLDER_NAME', 'photos/'),
    'html_file_key': os.environ.get('HTML_FILE_KEY', 'index.html'),
    'dynamodb_table': os.environ.get('DYNAMOTABLE_NAME', 'default-table'),
    'api_key_param': os.environ.get('API_KEY_PARAM', 'ChatGPT')
}

def get_api_key(parameter_name):
    response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    return response['Parameter']['Value']

def get_service_description(service_name, api_key, model="gpt-4", temperature=0.7, max_tokens=150):
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Create a visually striking and conceptually rich image that embodies the essence of the AWS service {service_name}. "
        f"Imagine a scene that combines elements of the real world and the abstract, the futuristic and the historical. "
        f"The composition should be dynamic and thought-provoking, with a clear focus on the literal or metaphorical "
        f"representation of the service name. Experiment with various art styles, such as surrealism, cyberpunk, or minimalism."
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    response = requests.post(api_url, headers=headers, json=payload)
    response_data = response.json()
    if response.status_code == 200:
        return response_data['choices'][0]['message']['content'].strip()
    else:
        logger.error(f"Error fetching description from API: {response_data}")
        return None

def save_to_dynamodb(situation_id, service_name, description):
    table = dynamodb.Table(CONFIG['dynamodb_table'])
    table.put_item(Item={
        'Situation_id': situation_id,
        'Service': service_name,
        'Description': description
    })
    logger.info(f"Saved {service_name} with description for situation_id {situation_id}.")

def clear_s3_photos():
    response = s3.list_objects_v2(Bucket=CONFIG['bucket_name'], Prefix=CONFIG['photos_prefix'])
    if 'Contents' in response:
        for item in response['Contents']:
            logger.info(f"Deleting {item['Key']} from S3")
            s3.delete_object(Bucket=CONFIG['bucket_name'], Key=item['Key'])

def modify_html_file(service_name, increment_solved_count=False):
    obj = s3.get_object(Bucket=CONFIG['bucket_name'], Key=CONFIG['html_file_key'])
    html_content = obj['Body'].read().decode('utf-8')

    # Обновляем correctAnswer
    html_content = re.sub(
        r'const correctAnswer = "(.*?)";',
        f'const correctAnswer = "{service_name}";',
        html_content
    )

    # questionsCount
    html_content = re.sub(
        r'let questionsCount = (\d+);',
        lambda match: f'let questionsCount = {int(match.group(1)) + 1};',
        html_content
    )

    # solvedCount
    if increment_solved_count:
        html_content = re.sub(
            r'let solvedCount = (\d+);',
            lambda match: f'let solvedCount = {int(match.group(1)) + 1};',
            html_content
        )

    s3.put_object(
        Bucket=CONFIG['bucket_name'],
        Key=CONFIG['html_file_key'],
        Body=html_content,
        ContentType='text/html'
    )
    logger.info("HTML file updated with new service name and counters.")

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")

    # 1) CORS preflight (OPTIONS)
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

    # 2) mic_value
    mic_value = None

    if 'body' in event:
        try:
            body_data = json.loads(event['body'])
            mic_value = body_data.get('mic')
        except:
            pass

    if not mic_value and 'mic' in event:
        mic_value = event['mic']

    if mic_value not in [2, 3]:
        logger.warning("Mic signal is not 2 or 3. Exiting.")
        return {
            'statusCode': 400,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
            },
            'body': json.dumps({'error': 'Invalid signal'}, ensure_ascii=False)
        }

    try:
        api_key = get_api_key(CONFIG['api_key_param'])
        service_name = random.choice(CONFIG['aws_services'])
        logger.info(f"Selected service: {service_name}")

        description = get_service_description(service_name, api_key)
        if not description:
            logger.error("Failed to get description for the service.")
            return {
                'statusCode': 500,
                'headers': {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
                },
                'body': json.dumps({'error': 'Failed to fetch description'}, ensure_ascii=False)
            }

        save_to_dynamodb(1, service_name, description)

        clear_s3_photos()

        modify_html_file(service_name, increment_solved_count=(mic_value == 3))

        return {
            'statusCode': 200,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
            },
            'body': json.dumps({
                'message': 'Service and description saved successfully!',
                'service': service_name,
                'description': description
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"Exception in main logic: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
            },
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }
