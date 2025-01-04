import os
import json
import boto3

BUCKET_NAME = os.environ.get('BUCKET_NAME', 'default-bucket')
PREFIX = os.environ.get('FOLDER_NAME', 'photos/')

def get_image_urls(bucket_name, prefix):
    s3 = boto3.client('s3')
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        # .png, .jpg, .jpeg, .gif
        image_urls = [
            f"https://{bucket_name}.s3.amazonaws.com/{item['Key']}"
            for item in response.get('Contents', [])
            if item['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
        ]
        return image_urls
    except Exception as e:
        print(f"Error accessing S3: {str(e)}")
        raise

def lambda_handler(event, context):
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

    try:
        # 2. 
        image_urls = get_image_urls(BUCKET_NAME, PREFIX)

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                "Content-Type": "application/json"
            },
            "body": json.dumps(image_urls)
        }

    except Exception as e:
        print(f"Exception: {str(e)}")
        # 3.
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": "Failed to list images"})
        }